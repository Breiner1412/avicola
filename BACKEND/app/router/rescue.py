from datetime import date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from app.schemas.rescue import RescueCreate, RescueOut, RescuePaginatedResponse, RescueUpdate
from core.database import get_db
from app.schemas.users import UserOut
from app.crud import rescue as crud_rescue

router = APIRouter()
modulo = 21

@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_rescue(
    rescue: RescueCreate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # El rol de quien usa el endpoint
        id_rol = user_token.id_rol


        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail="Salvamento no autorizado")

        crud_rescue.create_rescue(db, rescue)
        return {"message": "Salvamento creado correctamente"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    

@router.get("/by-id/{id_salvamento}", response_model=RescueOut)
def get_rescue(
    id_salvamento: int, 
    db: Session = Depends(get_db), 
    user_token: UserOut = Depends(get_current_user)
    ):

    try:
        id_rol = user_token.id_rol 

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Salvamento no autorizado")
        

        rescue = crud_rescue.get_rescue_by_id(db, id_salvamento)
        if not rescue:
            raise HTTPException(status_code=404, detail="Salvamento no encontrado")
        return rescue
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")    

@router.get("/all", response_model=List[RescueOut])
def get_all_rescues(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # Verificar permisos
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Consulta de salvamentos no autorizada")

        rescues = crud_rescue.get_all_rescues(db)
        return rescues
        
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos") 

@router.put("/by-id/{id_salvamento}")
def update_rescue(
    id_salvamento: int, 
    rescue: RescueUpdate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        if not verify_permissions(db, user_token.id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        success = crud_rescue.update_rescue_by_id(db, id_salvamento, rescue)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el salvamento")
        return {"message": "salvamento actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.delete("/by-id/{id_salvamento}")
def delete_rescue(
    id_salvamento: int, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # Verificar permisos
        id_rol = user_token.id_rol
        
        if not verify_permissions(db, id_rol, modulo, 'borrar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizada")
        
        # Verificar si existe antes de eliminar
        existing_rescue = crud_rescue.get_rescue_by_id(db, id_salvamento)
        if not existing_rescue:
            raise HTTPException(status_code=404, detail="Salvamento no encontrado")
        
        # Eliminar
        success = crud_rescue.delete_rescue_by_id(db, id_salvamento)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo eliminar el salvamento")
        
        return {"message": "Salvamento eliminado correctamente"}
        
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")    

@router.get("/all-pag", response_model=RescuePaginatedResponse)
def get_rescues_pag(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # Verificar permisos
        if not verify_permissions(db, user_token.id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        skip = (page - 1) * page_size
        data = crud_rescue.get_all_rescues_pag(db, skip=skip, limit=page_size)

        total = data['total']
        rescues = data['rescues']

        return {
            "page": page,
            "page_size": page_size,
            "total_rescues": total,
            "total_pages": (total + page_size - 1) // page_size,
            "rescues": rescues
        }
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/all-pag-by-date", response_model=RescuePaginatedResponse)
def get_rescues_pag_by_date(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        if not verify_permissions(db, user_token.id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        
        if fecha_inicio > fecha_fin:
            raise HTTPException(
                status_code=400, 
                detail="La fecha de inicio no puede ser mayor que la fecha de fin"
            )

        skip = (page - 1) * page_size
        data = crud_rescue.get_rescues_by_date_range_pag(
            db, 
            fecha_inicio=fecha_inicio, 
            fecha_fin=fecha_fin, 
            skip=skip, 
            limit=page_size
        )

        total = data['total']
        rescues = data['rescues']

        return {
            "page": page,
            "page_size": page_size,
            "total_rescues": total,
            "total_pages": (total + page_size - 1) // page_size,
            "rescues": rescues
        }
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
