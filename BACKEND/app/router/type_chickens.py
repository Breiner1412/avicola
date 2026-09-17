from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db
from app.schemas.type_chickens import TypeChickenCreate, TypeChickenUpdate, TypeChickenOut
from app.crud import type_chickens as crud_type_chicken
from app.schemas.users import UserOut


router = APIRouter()
modulo = 19

@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_type_chicken(
    type_chicken: TypeChickenCreate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # El rol de quien usa el endpoint
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        created = crud_type_chicken.create_type_chicken(db, type_chicken)

        if created is False:
            raise HTTPException(
                status_code=400,
                detail="El tipo de gallina con esa raza y descripción ya existe."
            )

        return {"message": "Registro de tipo de gallinas creado correctamente"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")



@router.get("/by-id", response_model=TypeChickenOut)
def get__type_chicken(
    id: int, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # El rol de quien usa el endpoint
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        type_chicken = crud_type_chicken.get_type_chicken_by_id(db, id)
        if not type_chicken:
            raise HTTPException(status_code=404, detail="Tipo de gallina no encontrado")
        return type_chicken
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/all-type-chickens", response_model=List[TypeChickenOut])
def get_type_chickens(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol  # El rol del usuario actual

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        type_chickens = crud_type_chicken.get_all_type_chickens(db)
        return type_chickens
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.put("/by-id/{id_ingreso}")
def update_chicken(
    id_ingreso: int, 
    type_chicken: TypeChickenUpdate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol  # El rol del usuario actual

        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        created = crud_type_chicken.update_type_chicken_by_id(db, id_ingreso, type_chicken)

        if created is False:
            raise HTTPException(
                status_code=400,
                detail="El tipo de gallina con esa raza y descripción ya existe."
            )

        if not created:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el registro")
        return {"message": "Registro actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

