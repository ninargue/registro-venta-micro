from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa de SQLAlchemy 2; los modelos se registran en su metadata."""


# Importar modelos para registro en metadata
from app.modules.auth.models import Business, BusinessUser  # noqa: E402, F401
from app.modules.catalog.models import Product  # noqa: E402, F401
from app.modules.sales.models import Payment, Sale, SaleItem  # noqa: E402, F401
