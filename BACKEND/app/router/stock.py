from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from app.schemas.users import UserOut
from app.schemas.stock import StockOut, StockResumen
from core.database import get_db
from app.crud import crud_stock



router = APIRouter()
modulo = 26  # Ajusta el módulo correspondiente para stock


@router.get("/by-id/{id_producto}", response_model=StockOut)
def get_stock(

    id_producto: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        stock = crud_stock.get_stock_by_id(db, id_producto)
        if not stock:
            raise HTTPException(status_code=404, detail="Stock no encontrado")
        return stock
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/stock/all", response_model=List[StockResumen])
def get_all_stock(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        stocks = crud_stock.get_all_stock(db, skip=skip, limit=limit)
        return stocks

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


# @router.put("/by-id/{id_producto}")
# def update_stock(
#     id_producto: int,
#     stock: StockUpdate,
#     db: Session = Depends(get_db),
#     user_token: UserOut = Depends(get_current_user)
# ):
#     try:
#         id_rol = user_token.id_rol
#         if not verify_permissions(db, id_rol, modulo, 'actualizar'):
#             raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
#         success = crud_stock.update_stock_by_id(db, id_producto, stock)
#         if not success:
#             raise HTTPException(status_code=400, detail="No se pudo actualizar el stock")
#         return {"message": "Stock actualizado correctamente"}
#     except SQLAlchemyError as e:
#         raise HTTPException(status_code=500, detail="Error interno de base de datos")
