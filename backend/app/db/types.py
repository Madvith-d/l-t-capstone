from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator


class VectorType(TypeDecorator):
    """Use pgvector in PostgreSQL and JSON in lightweight test databases."""

    impl = JSON
    cache_ok = True

    def __init__(self, dimensions: int = 384):
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(self.dimensions))
        return dialect.type_descriptor(JSON())
