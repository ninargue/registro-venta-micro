import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.catalog import schemas
from app.modules.catalog.schemas import ProductCreate, ProductListQuery, ProductResponse


def test_product_create_validates_strict_decimals_and_trims_strings() -> None:
    payload = ProductCreate(
        code="  SKU-01  ",
        name="  Yerba Mate 1kg  ",
        sale_price="2500.5",
        cost_price="1800",
        stock="10.25",
    )
    assert payload.code == "SKU-01"
    assert payload.name == "Yerba Mate 1kg"
    assert payload.sale_price == Decimal("2500.50")
    assert payload.cost_price == Decimal("1800.00")
    assert payload.stock == Decimal("10.25")


@pytest.mark.parametrize(
    "bad_decimal",
    [
        10.5,
        True,
        "NaN",
        "Infinity",
        "10.123",
        "1e30",
        "1000000000000000000000000000",
        "10000000000.00",
        "",
        "   ",
        "10\x00",
    ],
)
def test_product_create_rejects_invalid_decimal_inputs(bad_decimal: object) -> None:
    with pytest.raises(ValidationError):
        ProductCreate(name="Producto", sale_price=bad_decimal)


@pytest.mark.parametrize(
    "field,val", [("sale_price", "0"), ("cost_price", "-1"), ("stock", "-0.01")]
)
def test_product_create_rejects_out_of_range_bounds(field: str, val: str) -> None:
    kwargs: dict[str, object] = {"name": "Producto", "sale_price": "10.00", field: val}
    with pytest.raises(ValidationError):
        ProductCreate(**kwargs)


def test_product_create_rejects_nul_byte_and_blank_strings() -> None:
    with pytest.raises(ValidationError):
        ProductCreate(name="   ", sale_price="10.00")
    with pytest.raises(ValidationError):
        ProductCreate(name="Prod\x00", sale_price="10.00")
    with pytest.raises(ValidationError):
        ProductCreate(code="   ", name="Prod", sale_price="10.00")


def test_product_list_query_bounds_and_sanitization() -> None:
    query = ProductListQuery(q="  yerba  ", limit=200, offset=2_147_483_647)
    assert query.q == "yerba"
    assert query.limit == 200
    assert query.offset == 2_147_483_647

    with pytest.raises(ValidationError):
        ProductListQuery(limit=0)
    with pytest.raises(ValidationError):
        ProductListQuery(limit=201)
    with pytest.raises(ValidationError):
        ProductListQuery(offset=-1)
    with pytest.raises(ValidationError):
        ProductListQuery(offset=2_147_483_648)
    with pytest.raises(ValidationError):
        ProductListQuery(q="a\x00b")


def test_product_response_allows_negative_stock_and_nullable_cost_price() -> None:
    now = datetime.now(UTC)
    resp = ProductResponse(
        id=uuid.uuid4(),
        code=None,
        name="Pan",
        sale_price=Decimal("500"),
        cost_price=None,
        stock=Decimal("-1.5"),
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    dumped = resp.model_dump(mode="json")
    assert dumped["sale_price"] == "500.00"
    assert dumped["cost_price"] is None
    assert dumped["stock"] == "-1.50"


def _get_product_update_schema() -> type:
    product_update = getattr(schemas, "ProductUpdate", None)
    assert product_update is not None, "ProductUpdate schema must be defined in catalog.schemas"
    return product_update


def test_product_update_partial_payload_and_exclude_unset() -> None:
    product_update_cls = _get_product_update_schema()
    payload = product_update_cls(
        sale_price="3500.5",
        cost_price="2200",
    )
    assert payload.sale_price == Decimal("3500.50")
    assert payload.cost_price == Decimal("2200.00")
    assert payload.model_dump(exclude_unset=True) == {
        "sale_price": Decimal("3500.50"),
        "cost_price": Decimal("2200.00"),
    }


def test_product_update_full_payload_and_explicit_null_code() -> None:
    product_update_cls = _get_product_update_schema()
    payload = product_update_cls(
        code=None,
        name="  Yerba Mate Despalada  ",
        sale_price="4100.00",
        cost_price="2500.00",
        stock="0.00",
    )
    assert payload.code is None
    assert payload.name == "Yerba Mate Despalada"
    assert payload.model_dump(exclude_unset=True) == {
        "code": None,
        "name": "Yerba Mate Despalada",
        "sale_price": Decimal("4100.00"),
        "cost_price": Decimal("2500.00"),
        "stock": Decimal("0.00"),
    }


def test_product_update_trims_code_and_ignores_extra_immutable_fields() -> None:
    product_update_cls = _get_product_update_schema()
    payload = product_update_cls(
        code="  SKU-999  ",
        business_id=str(uuid.uuid4()),
        id=str(uuid.uuid4()),
    )
    assert payload.code == "SKU-999"
    assert payload.model_dump(exclude_unset=True) == {"code": "SKU-999"}


def test_product_update_rejects_empty_payload_or_only_ignored_fields() -> None:
    product_update_cls = _get_product_update_schema()
    with pytest.raises(ValidationError):
        product_update_cls()
    with pytest.raises(ValidationError):
        product_update_cls(business_id=str(uuid.uuid4()), is_active=False)


@pytest.mark.parametrize("field", ["name", "sale_price", "cost_price", "stock"])
def test_product_update_rejects_explicit_null_on_non_nullable_fields(field: str) -> None:
    product_update_cls = _get_product_update_schema()
    with pytest.raises(ValidationError):
        product_update_cls(**{field: None})


@pytest.mark.parametrize(
    "bad_decimal",
    [
        10.5,
        True,
        "NaN",
        "Infinity",
        "-Infinity",
        "10.123",
        "1e30",
        "1000000000000000000000000000",
        "10000000000.00",
        "",
        "   ",
        "10\x00",
    ],
)
@pytest.mark.parametrize("field", ["sale_price", "cost_price", "stock"])
def test_product_update_rejects_invalid_decimal_inputs(
    field: str,
    bad_decimal: object,
) -> None:
    product_update_cls = _get_product_update_schema()
    with pytest.raises(ValidationError):
        product_update_cls(**{field: bad_decimal})


@pytest.mark.parametrize(
    "field,val",
    [
        ("sale_price", "0.00"),
        ("sale_price", "-1.00"),
        ("cost_price", "-0.01"),
        ("stock", "-0.01"),
    ],
)
def test_product_update_rejects_out_of_range_bounds(field: str, val: str) -> None:
    product_update_cls = _get_product_update_schema()
    with pytest.raises(ValidationError):
        product_update_cls(**{field: val})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": ""},
        {"name": "   "},
        {"name": "a" * 151},
        {"name": "Prod\x00"},
        {"code": ""},
        {"code": "   "},
        {"code": "c" * 51},
        {"code": "SKU\x00"},
    ],
)
def test_product_update_rejects_blank_oversized_and_nul_byte_strings(
    kwargs: dict[str, object],
) -> None:
    product_update_cls = _get_product_update_schema()
    with pytest.raises(ValidationError):
        product_update_cls(**kwargs)
