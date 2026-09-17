"""Esquemas que se repiten en toda la API."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Mensaje(BaseModel):
    mensaje: str


class Pagina(BaseModel, Generic[T]):
    total: int
    pagina: int
    tamano: int
    datos: list[T]
