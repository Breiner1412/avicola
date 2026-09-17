from app.schemas.sheds import ShedOut
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from core.database import get_db
from app.schemas.sheds import ShedCreate, ShedUpdate
from app.schemas.users import UserOut
from app.crud import sheds as crud_sheds
from app.router.dependencies import get_current_user
from app.crud.permisos import verify_permissions
from typing import List

router = APIRouter()
modulo = 12

@router.post("/crear-galpon", status_code=status.HTTP_201_CREATED)
def create_shed(
    shed: ShedCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")   
        crud_sheds.create_shed(db, shed)
        return {"message": "Galpón creado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    
@router.get("/by-id/{shed_id}", response_model = ShedOut)
def get_shed_by_id(
    shed_id: int, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        shed = crud_sheds.get_shed_by_id(db, shed_id)
        if not shed:
            raise HTTPException(status_code=404, detail="Galpón no encontrada")
        return shed
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/fincas/activas")
def listar_fincas_activas(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        lands = crud_sheds.get_active_lands(db)
        return lands
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    
@router.get("/galpones/por-finca")
def listar_galpones_por_finca(
    id_finca: int, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        sheds = crud_sheds.get_sheds_by_lands(db, id_finca)
        return sheds
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
        
@router.get("/activos")
def get_active_sheds(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        sheds_activos = crud_sheds.get_active_sheds(db)
        return sheds_activos
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
        
@router.get("/all", response_model=List[ShedOut])
def get_all_sheds(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        sheds = crud_sheds.get_all_sheds(db)
        return sheds
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.put("/by-id/{shed_id}")
def update_shed_by_id(
    shed_id: int, 
    shed: ShedUpdate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        success = crud_sheds.update_shed_by_id(db, shed_id, shed)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el galpón")
        return {"message": "Galpón actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    
@router.put("/cambiar-estado/{id_galpon}", status_code=status.HTTP_200_OK)
def change_shed_status(
    id_galpon: int,
    nuevo_estado: bool,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        success = crud_sheds.change_shed_status(db, id_galpon, nuevo_estado)
        if not success:
            raise HTTPException(status_code=404, detail="Galpón no encontrado")
        return {"message": f"Estado del galpón actualizado a {nuevo_estado}"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
