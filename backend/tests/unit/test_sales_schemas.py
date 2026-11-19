import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.main import app
from app.modules.sales.schemas import (
    SaleCreate,
    SaleItemCreate,
    SaleItemResponse,
    SalePaymentCreate,
    SalePaymentResponse,
    SaleResponse,
)


def test_sale_create_validates_strict_decimals_and_quantizes() -> None:
    product_id = uuid.uuid4()
    client_id = uuid.uuid4()
    payload = SaleCreate(
        client_id=client_id,
        items=[SaleItemCreate(product_id=product_id, quantity="2.5")],
        payments=[SalePaymentCreate(payment_method="cash", amount="5000")],
    )
    assert payload.client_id == client_id
    assert payload.items[0].quantity == Decimal("2.50")
    assert payload.payments[0].amount == Decimal("5000.00")


@pytest.mark.parametrize(
    "bad_decimal",
    [
        1.5,
        True,
        False,
        "NaN",
        "Infinity",
        "-Infinity",
        "1.234",
        "1e30",
        "10000000000.00",
        "0",
        "0.00",
        "-1.00",
        "",
        "   ",
        "10\x00",
    ],
)
def test_sale_item_and_payment_reject_invalid_decimals(bad_decimal: object) -> None:
    pid = uuid.uuid4()
    with pytest.raises(ValidationError):
        SaleItemCreate(product_id=pid, quantity=bad_decimal)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        SalePaymentCreate(payment_method="cash", amount=bad_decimal)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_method", ["other", "CASH", "crypto", "cash\x00", ""])
def test_sale_payment_rejects_invalid_payment_method(bad_method: object) -> None:
    with pytest.raises(ValidationError):
        SalePaymentCreate(payment_method=bad_method, amount="10.00")  # type: ignore[arg-type]


def test_sale_create_rejects_invalid_uuids_and_nul_bytes() -> None:
    valid_pid = uuid.uuid4()
    with pytest.raises(ValidationError):
        SaleCreate(
            client_id="not-a-uuid",  # type: ignore[arg-type]
            items=[SaleItemCreate(product_id=valid_pid, quantity="1.00")],
            payments=[SalePaymentCreate(payment_method="cash", amount="10.00")],
        )
    with pytest.raises(ValidationError):
        SaleItemCreate(product_id=f"{valid_pid}\x00", quantity="1.00")  # type: ignore[arg-type]


def test_sale_create_enforces_items_and_payments_bounds() -> None:
    pid = uuid.uuid4()
    with pytest.raises(ValidationError):
        SaleCreate(
            client_id=uuid.uuid4(),
            items=[],
            payments=[SalePaymentCreate(payment_method="cash", amount="10.00")],
        )
    with pytest.raises(ValidationError):
        SaleCreate(
            client_id=uuid.uuid4(),
            items=[SaleItemCreate(product_id=pid, quantity="1.00")],
            payments=[],
        )

    max_items = [SaleItemCreate(product_id=pid, quantity="1.00") for _ in range(500)]
    max_payments = [SalePaymentCreate(payment_method="cash", amount="1.00") for _ in range(20)]
    ok = SaleCreate(client_id=uuid.uuid4(), items=max_items, payments=max_payments)
    assert len(ok.items) == 500
    assert len(ok.payments) == 20

    with pytest.raises(ValidationError):
        SaleCreate(
            client_id=uuid.uuid4(),
            items=[SaleItemCreate(product_id=pid, quantity="1.00") for _ in range(501)],
            payments=[SalePaymentCreate(payment_method="cash", amount="1.00")],
        )
    with pytest.raises(ValidationError):
        SaleCreate(
            client_id=uuid.uuid4(),
            items=[SaleItemCreate(product_id=pid, quantity="1.00")],
            payments=[SalePaymentCreate(payment_method="cash", amount="1.00") for _ in range(21)],
        )


def test_sale_create_ignores_extra_business_id_field() -> None:
    pid = uuid.uuid4()
    payload = SaleCreate.model_validate(
        {
            "business_id": str(uuid.uuid4()),
            "client_id": str(uuid.uuid4()),
            "items": [{"product_id": str(pid), "quantity": "1.00"}],
            "payments": [{"payment_method": "cash", "amount": "10.00"}],
        }
    )
    assert not hasattr(payload, "business_id")
    assert "business_id" not in payload.model_dump()


def test_sale_response_serializes_quantized_decimals_without_unit_cost() -> None:
    now = datetime.now(UTC)
    resp = SaleResponse(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        total_amount=Decimal("300"),
        created_at=now,
        items=[
            SaleItemResponse(
                id=uuid.uuid4(),
                product_id=uuid.uuid4(),
                product_name="Pan",
                quantity=Decimal("1.5"),
                unit_price=Decimal("200"),
                subtotal=Decimal("300"),
            )
        ],
        payments=[
            SalePaymentResponse(
                id=uuid.uuid4(),
                payment_method="card",
                amount=Decimal("300"),
            )
        ],
    )
    dumped = resp.model_dump(mode="json")
    assert dumped["total_amount"] == "300.00"
    assert dumped["items"][0]["quantity"] == "1.50"
    assert dumped["items"][0]["unit_price"] == "200.00"
    assert dumped["items"][0]["subtotal"] == "300.00"
    assert "unit_cost" not in dumped["items"][0]
    assert dumped["payments"][0]["amount"] == "300.00"


def test_sales_input_json_schemas_declare_string_decimal_without_number() -> None:
    item_qty_schema = SaleItemCreate.model_json_schema()["properties"]["quantity"]
    assert item_qty_schema.get("type") == "string"
    assert item_qty_schema.get("format") == "decimal"
    assert "anyOf" not in item_qty_schema

    payment_amt_schema = SalePaymentCreate.model_json_schema()["properties"]["amount"]
    assert payment_amt_schema.get("type") == "string"
    assert payment_amt_schema.get("format") == "decimal"
    assert "anyOf" not in payment_amt_schema

    openapi_schemas = app.openapi()["components"]["schemas"]
    assert openapi_schemas["SaleItemCreate"]["properties"]["quantity"].get("type") == "string"
    assert openapi_schemas["SalePaymentCreate"]["properties"]["amount"].get("type") == "string"
