import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, cast

from app.core.schemas import DECIMAL_QUANTIZER, MAX_NUMERIC_12_2, quantize_decimal
from app.core.security import CurrentUser
from app.modules.catalog.service import CatalogService
from app.modules.sales.models import Payment, Sale, SaleItem
from app.modules.sales.repository import SalesRepository
from app.modules.sales.schemas import (
    PaymentMethod,
    SaleCreate,
    SaleItemResponse,
    SalePaymentResponse,
    SaleResponse,
)


class SaleProductNotFoundError(Exception):
    """Error lanzado cuando uno o más productos no existen o pertenecen a otro comercio."""

    def __init__(self, missing_product_ids: list[uuid.UUID]) -> None:
        self.missing_product_ids = missing_product_ids
        super().__init__("One or more products were not found")


class SaleProductInactiveError(Exception):
    """Error lanzado cuando se intenta vender un producto desactivado."""

    def __init__(self, inactive_product_ids: list[uuid.UUID]) -> None:
        self.inactive_product_ids = inactive_product_ids
        super().__init__("Inactive products cannot be sold")


class SalePaymentMismatchError(Exception):
    """Error lanzado cuando la suma de pagos no coincide con el total calculado."""

    def __init__(self, *, expected_total: Decimal, payments_total: Decimal) -> None:
        self.expected_total = quantize_decimal(expected_total)
        self.payments_total = quantize_decimal(payments_total)
        super().__init__("Sum of payments must match server-calculated sale total")


class SaleTotalInvalidError(Exception):
    """Error lanzado cuando el subtotal o total calculado excede los límites válidos."""


class SaleStockOverflowError(Exception):
    """Error lanzado cuando la deducción o el stock resultante exceden numeric(12,2)."""


class SaleIdConflictError(Exception):
    """Error lanzado cuando un client_id existente se reutiliza con distinto contenido."""

    def __init__(self, client_id: uuid.UUID) -> None:
        self.client_id = client_id
        super().__init__("client_id already exists with different sale items or payments")


class SalesService:
    """Casos de uso transaccionales e idempotentes de ventas."""

    def __init__(
        self,
        repository: SalesRepository,
        catalog_service: CatalogService,
    ) -> None:
        self._repository = repository
        self._catalog_service = catalog_service

    @staticmethod
    def _calculate_subtotal(quantity: Decimal, unit_price: Decimal) -> Decimal:
        return (quantity * unit_price).quantize(DECIMAL_QUANTIZER, rounding=ROUND_HALF_UP)

    @classmethod
    def _build_sale_response(
        cls,
        sale: Sale,
        items: list[SaleItem],
        payments: list[Payment],
        product_names: dict[uuid.UUID, str],
    ) -> SaleResponse:
        item_responses = [
            SaleItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=product_names.get(item.product_id, ""),
                quantity=quantize_decimal(item.quantity),
                unit_price=quantize_decimal(item.unit_price),
                subtotal=cls._calculate_subtotal(
                    quantize_decimal(item.quantity),
                    quantize_decimal(item.unit_price),
                ),
            )
            for item in items
        ]
        payment_responses = [
            SalePaymentResponse(
                id=payment.id,
                payment_method=cast(PaymentMethod, payment.payment_method),
                amount=quantize_decimal(payment.amount),
            )
            for payment in payments
        ]
        return SaleResponse(
            id=sale.id,
            client_id=sale.client_id,
            total_amount=quantize_decimal(sale.total_amount),
            items=item_responses,
            payments=payment_responses,
            created_at=sale.created_at,
        )

    @staticmethod
    def _assert_idempotent_payload_matches(
        payload: SaleCreate,
        existing_items: list[SaleItem],
        existing_payments: list[Payment],
    ) -> None:
        incoming_items = sorted(
            (item.product_id, quantize_decimal(item.quantity)) for item in payload.items
        )
        persisted_items = sorted(
            (item.product_id, quantize_decimal(item.quantity)) for item in existing_items
        )
        incoming_payments = sorted(
            (payment.payment_method, quantize_decimal(payment.amount))
            for payment in payload.payments
        )
        persisted_payments = sorted(
            (cast(PaymentMethod, payment.payment_method), quantize_decimal(payment.amount))
            for payment in existing_payments
        )
        if incoming_items != persisted_items or incoming_payments != persisted_payments:
            raise SaleIdConflictError(payload.client_id)

    async def create_sale(
        self,
        current_user: CurrentUser,
        payload: SaleCreate,
    ) -> tuple[SaleResponse, bool]:
        """Registra una venta de forma atómica e idempotente; retorna (comprobante, created)."""
        if current_user.business_id is None:
            raise ValueError("Tenant business_id is required")

        business_id = current_user.business_id

        existing = await self._repository.get_sale_by_client_id(
            business_id=business_id,
            client_id=payload.client_id,
        )
        if existing is not None:
            sale, items, payments = existing
            self._assert_idempotent_payload_matches(payload, items, payments)
            product_names = await self._catalog_service.get_product_names_by_ids(
                business_id=business_id,
                product_ids=[item.product_id for item in items],
            )
            return self._build_sale_response(sale, items, payments, product_names), False

        unique_product_ids = sorted({item.product_id for item in payload.items})
        products_by_id = await self._catalog_service.lock_products_for_sale(
            business_id=business_id,
            product_ids=unique_product_ids,
        )

        existing_after_lock = await self._repository.get_sale_by_client_id(
            business_id=business_id,
            client_id=payload.client_id,
        )
        if existing_after_lock is not None:
            sale, items, payments = existing_after_lock
            self._assert_idempotent_payload_matches(payload, items, payments)
            existing_product_ids = [item.product_id for item in items]
            if all(pid in products_by_id for pid in existing_product_ids):
                product_names = {pid: products_by_id[pid].name for pid in existing_product_ids}
            else:
                product_names = await self._catalog_service.get_product_names_by_ids(
                    business_id=business_id,
                    product_ids=existing_product_ids,
                )
            return self._build_sale_response(sale, items, payments, product_names), False

        missing_ids = [pid for pid in unique_product_ids if pid not in products_by_id]
        if missing_ids:
            raise SaleProductNotFoundError(missing_ids)

        inactive_ids = [pid for pid in unique_product_ids if not products_by_id[pid].is_active]
        if inactive_ids:
            raise SaleProductInactiveError(inactive_ids)

        total_amount = Decimal("0.00")
        item_rows: list[dict[str, Any]] = []
        stock_deductions: dict[uuid.UUID, Decimal] = {}
        product_names = {pid: prod.name for pid, prod in products_by_id.items()}

        for item in payload.items:
            product = products_by_id[item.product_id]
            unit_price = quantize_decimal(product.sale_price)
            unit_cost = quantize_decimal(product.cost_price)
            subtotal = self._calculate_subtotal(item.quantity, unit_price)
            if subtotal <= Decimal("0.00"):
                raise SaleTotalInvalidError("Calculated line subtotal must be greater than zero")

            total_amount += subtotal
            if total_amount > MAX_NUMERIC_12_2:
                raise SaleTotalInvalidError("Calculated sale total exceeds numeric(12,2) range")

            new_deduction = stock_deductions.get(item.product_id, Decimal("0.00")) + item.quantity
            if new_deduction > MAX_NUMERIC_12_2:
                raise SaleStockOverflowError(
                    "Aggregated product stock deduction exceeds numeric(12,2) range"
                )
            stock_deductions[item.product_id] = new_deduction
            item_rows.append(
                {
                    "business_id": business_id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": unit_price,
                    "unit_cost": unit_cost,
                }
            )

        if total_amount <= Decimal("0.00") or total_amount > MAX_NUMERIC_12_2:
            raise SaleTotalInvalidError("Calculated sale total is out of valid range")

        for pid, total_qty in stock_deductions.items():
            resulting_stock = quantize_decimal(products_by_id[pid].stock) - total_qty
            if resulting_stock < -MAX_NUMERIC_12_2:
                raise SaleStockOverflowError(
                    "Resulting product stock falls below numeric(12,2) range"
                )

        payments_total = sum((p.amount for p in payload.payments), start=Decimal("0.00"))
        if payments_total != total_amount:
            raise SalePaymentMismatchError(
                expected_total=total_amount,
                payments_total=payments_total,
            )

        async with self._repository.transaction():
            inserted_sale = await self._repository.try_insert_sale_header(
                business_id=business_id,
                client_id=payload.client_id,
                total_amount=total_amount,
            )
            if inserted_sale is not None:
                for row in item_rows:
                    row["sale_id"] = inserted_sale.id
                payment_rows = [
                    {
                        "business_id": business_id,
                        "sale_id": inserted_sale.id,
                        "payment_method": payment.payment_method,
                        "amount": payment.amount,
                    }
                    for payment in payload.payments
                ]
                inserted_items = await self._repository.insert_sale_items(items=item_rows)
                inserted_payments = await self._repository.insert_payments(payments=payment_rows)
                await self._catalog_service.deduct_stock_batch(
                    business_id=business_id,
                    deductions=stock_deductions,
                )
                return (
                    self._build_sale_response(
                        inserted_sale,
                        inserted_items,
                        inserted_payments,
                        product_names,
                    ),
                    True,
                )

        existing_after_conflict = await self._repository.get_sale_by_client_id(
            business_id=business_id,
            client_id=payload.client_id,
        )
        if existing_after_conflict is None:
            raise RuntimeError("Concurrent sale conflict occurred but committed sale was not found")

        existing_sale, existing_items, existing_payments = existing_after_conflict
        self._assert_idempotent_payload_matches(payload, existing_items, existing_payments)
        existing_product_ids = [item.product_id for item in existing_items]
        if all(pid in products_by_id for pid in existing_product_ids):
            existing_names = {pid: products_by_id[pid].name for pid in existing_product_ids}
        else:
            existing_names = await self._catalog_service.get_product_names_by_ids(
                business_id=business_id,
                product_ids=existing_product_ids,
            )
        return (
            self._build_sale_response(
                existing_sale,
                existing_items,
                existing_payments,
                existing_names,
            ),
            False,
        )
