from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


# Quy tắc đặt tên thống nhất cho constraint và index.
# Điều này giúp migration không sinh tên ngẫu nhiên giữa các máy.
NAMING_CONVENTION = {
    # Index
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",

    # Unique constraint
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",

    # Check constraint
    "ck": "ck_%(table_name)s_%(constraint_name)s",

    # Foreign key
    "fk": (
        "fk_%(table_name)s_"
        "%(column_0_N_name)s_"
        "%(referred_table_name)s"
    ),

    # Primary key
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Lớp cha của toàn bộ SQLAlchemy model.

    Các model như User, Patient và Prediction sẽ kế thừa Base.
    """

    metadata = MetaData(
        naming_convention=NAMING_CONVENTION
    )