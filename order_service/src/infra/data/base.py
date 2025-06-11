from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """ Базовый класс для всех декларативных ORM-моделей. """
    __abstract__ = True
