from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db
from app.schemas.detalle_huevos import DetalleHuevosCreate, DetalleHuevosOut, DetalleHuevosUpdate, StockProductosOut
from app.crud import detalle_huevos as crud_detalles_huevos


from app.schemas.users import UserOut

router = APIRouter()

@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_detalle_huevos(
    detalle_huevos: DetalleHuevosCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        modulo=7
        
        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail="usuario no autorizado")

        nuevo_detalle = crud_detalles_huevos.create_detalle_huevos(db, detalle_huevos)
        return nuevo_detalle
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    

@router.put("/by-id/{detalle_id}")
def update_detalle_huevos(
    detalle_id: int,
    detalle_huevos: DetalleHuevosUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        modulo=7
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="usuario no autorizado")
        
        success = crud_detalles_huevos.update_detalle_huevos_by_id(db, detalle_id, detalle_huevos)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el detalle de huevos")
        return {"message": "Detalle de huevos actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    

@router.get("/by-id_venta", response_model=list[DetalleHuevosOut])
def get_detalle_huevos(
    id_venta: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol=user_token.id_rol
        modulo=7
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="usuario no autorizado")

        detalle_huevos = crud_detalles_huevos.get_detalle_huevos_by_id_venta(db, id_venta)
        return detalle_huevos
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/by-id_detalle", response_model=DetalleHuevosOut)
def get_detalle_huevos_by_id_detalle(
    id_detalle: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol   
        modulo = 7  
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para ver detalle salvamento")

        detalle_huevos = crud_detalles_huevos.get_detalle_huevos_by_id(db, id_detalle)
        if not detalle_huevos:
            raise HTTPException(status_code=404, detail="Detalle huevos no encontrado")
        return detalle_huevos
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    
@router.get("/all-products-stock", response_model=list[StockProductosOut])
def get_all_products_stock(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol   
        modulo = 7  
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para todos los productos")

        detalle_huevos = crud_detalles_huevos.get_all_products_stock(db)
        return detalle_huevos
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.delete("/by-id/{detalle_id}")
def delete_detalle_huevos(
    detalle_id: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        modulo=7
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="usuario no autorizado")

        success = crud_detalles_huevos.delete_detalle_huevos_by_id(db, detalle_id)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo eliminar el detalle de huevos")
        return {"message": "Detalle de huevos eliminado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    

    
    




