"""Esquemas que se repiten en toda la API."""

from typing import Generic, TypeVar

from pydantic import BaseModel

# Topes de los numeros que llegan en las peticiones: un valor enorme no debe
# llegar a la base (desbordaria Numeric(14,2) / Numeric(12,3) y daria un 500)
DINERO_MAXIMO = 999_999_999_999
CANTIDAD_MAXIMA = 999_999_999
LECTURA_MAXIMA = 1_000_000

T = TypeVar("T")


class Mensaje(BaseModel):
    mensaje: str


class Pagina(BaseModel, Generic[T]):
    total: int
    pagina: int
    tamano: int
    datos: list[T]
