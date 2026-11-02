from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa de SQLAlchemy 2; los modelos se registran en su metadata."""
