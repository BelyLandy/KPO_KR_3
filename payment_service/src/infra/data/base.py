from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """ Абстрактный базовый класс для всех ORM-моделей. """
    __abstract__ = True
