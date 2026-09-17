from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db
from app.schemas.metodo_pago import MetodoPagoCreate, MetodoPagoOut, MetodoPagoUpdate
from app.schemas.users import UserOut
from app.crud import metodo_pago as crud_metodosPago
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()
modulo = 8
@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_metodoPago(    
    metodoPago: MetodoPagoCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:

        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail= 'Usuario no autorizado')
        crud_metodosPago.create_metodoPago(db, metodoPago)
        return {"message": "Metodo de pago creado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/by-id")
def get_metodoPago(    
    metodoPago_id: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user) ):
    try:

        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail= 'Usuario no autorizado')
        metodoPago = crud_metodosPago.get_metodoPago_by_id(db, metodoPago_id)
        if not metodoPago:
            raise HTTPException(status_code=404, detail="Metodo de pago no encontrado")
        return metodoPago
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    

@router.get("/all-metodosPago", response_model=List[MetodoPagoOut])
def get_metodosPago(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user) 
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        users = crud_metodosPago.get_metodosPago(db)
        return users
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.put("/by-id/{metodoPago_id}")
def update_metodosPago(
    metodoPago_id: int,
    metodoPago: MetodoPagoUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        success = crud_metodosPago.update_metodoPago_by_id(db, metodoPago_id, metodoPago)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el metodo de pago")
        return {"message": "Metodo de pago actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    

@router.put("/change-status/{metodoPago_id}", status_code=status.HTTP_200_OK)
def change_metodoPago_status(
    metodoPago_id: int,
    nuevo_estado: bool,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        success = crud_metodosPago.change_metodoPago_status(db, metodoPago_id, nuevo_estado)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo cambiar el estado del metodo de pago")
        return {"message": f"Estado del metodo de pago actualizado a {nuevo_estado}"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")