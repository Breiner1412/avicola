from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.crud import lands as crud_lands
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db
from app.schemas.lands import LandCreate, LandUpdate, LandOut
from app.schemas.users import UserOut

router = APIRouter()
modulo = 11  

# Crear finca
@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_finca(
    finca: LandCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "insertar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        crud_lands.create_land(db, finca)
        return {"message": "Finca creada correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Listar todas las fincas
@router.get("/all", response_model=list[LandOut])
def get_all_fincas(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        fincas = crud_lands.get_all_lands(db)
        return fincas
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Obtener finca por ID
@router.get("/get/{id_finca}", response_model=LandOut)
def get_land_by_id(
    id_finca: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol  
        if not verify_permissions(db, id_rol, modulo, "seleccionar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        land = crud_lands.get_land_by_id(db, id_finca)
        if not land:
            raise HTTPException(status_code=404, detail="Finca no encontrada")

        return land

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


# Actualizar finca
@router.put("/update/{id_finca}")
def update_finca(
    id_finca: int,
    finca: LandUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "actualizar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        actualizado = crud_lands.update_land_by_id(db, id_finca, finca)
        if not actualizado:
            raise HTTPException(status_code=404, detail="Finca no encontrada")

        return {"message": "Finca actualizada correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Cambiar estado (borrado lógico)
@router.put("/cambiar-estado/{id_finca}")
def cambiar_estado_finca(
    id_finca: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, "actualizar"):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        actualizado = crud_lands.toggle_estado_finca(db, id_finca)
        if not actualizado:
            raise HTTPException(status_code=404, detail="Finca no encontrada")

        return {"message": "Estado de la finca cambiado correctamente"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
