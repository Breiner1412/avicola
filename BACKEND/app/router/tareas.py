from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db

from app.schemas.tareas import TareaCreate, TareaOut, TareaUpdate
from app.schemas.users import UserOut
from app.crud import tareas as crud_tareas



router = APIRouter()
modulo = 6  # ID del módulo
ROL_OPERARIO = 4


# PARA VER TODAS LAS TAREAS REGISTRADAS 
@router.get("/pag", response_model=dict)
def get_tareas_pag(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    fecha_inicio: Optional[date] = Query(None, description="Filtrar desde esta fecha"),
    fecha_fin: Optional[date] = Query(None, description="Filtrar hasta esta fecha"),
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    """
    Obtiene las tareas paginadas y opcionalmente filtradas por fecha.
    (Solo se ejecuta si el usuario ya pasó verify_permissions con permisos de selección)
    """
    try:
        id_rol = user_token.id_rol

        # Validar permisos del usuario para ver tareas
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        skip = (page - 1) * page_size

        data = crud_tareas.get_tareas_pag(
            db=db,
            skip=skip,
            limit=page_size,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )

        total = data["total"]
        tareas = data["tareas"]

        return {
            "page": page,
            "page_size": page_size,
            "total_tareas": total,
            "total_pages": (total + page_size - 1) // page_size,
            "tareas": tareas
        }

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


# Crear una tarea
@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_tarea(
    tarea: TareaCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        # Validar permiso
        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para crear tareas")

        crud_tareas.create_tarea(db, tarea)
        return {"message": "Tarea creada correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# Obtener todas las tareas de un usuario
@router.get("/usuario/{id_usuario}", response_model=List[TareaOut])
def get_tareas_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        rol_actual = user_token.id_rol
        usuario_actual = user_token.id_usuario

        # Si es OPERARIO (id_rol = 4), solo puede ver sus propias tareas
        if rol_actual == ROL_OPERARIO:
            if id_usuario != usuario_actual:
                raise HTTPException(status_code=401, detail="No tienes permiso para ver tareas de otros usuarios")
            # No validamos verify_permissions, se salta esa parte
        else:
            # Otros roles sí pasan por el control de permisos normal
            if not verify_permissions(db, rol_actual, modulo, 'seleccionar'):
                raise HTTPException(status_code=401, detail="Usuario no autorizado para ver tareas")

        # Lista vacía si el usuario no tiene tareas (no es un error)
        return crud_tareas.get_tareas_by_user(db, id_usuario, usuario_actual, rol_actual)

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")




# Actualizar tarea por ID
@router.put("/{id_tarea}")
def update_tarea(
    id_tarea: int,
    tarea: TareaUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado para editar tareas")

        existente = crud_tareas.get_tarea_by_id(db, id_tarea)
        if not existente:
            raise HTTPException(status_code=404, detail="No se encontró la tarea")

        # Un operario solo puede actualizar el estado / fecha fin de SUS tareas
        if id_rol == ROL_OPERARIO:
            if existente["id_usuario"] != user_token.id_usuario:
                raise HTTPException(status_code=401, detail="Usuario no autorizado")
            campos = tarea.model_dump(exclude_unset=True)
            if set(campos) - {"estado", "fecha_hora_fin"}:
                raise HTTPException(status_code=401, detail="Usuario no autorizado")

        success = crud_tareas.update_tarea(db, id_tarea, tarea)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar la tarea")
        return {"message": "Tarea actualizada correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

# # Eliminar tarea por ID
# @router.delete("/{id_tarea}")
# def delete_tarea(
#     id_tarea: int,
#     db: Session = Depends(get_db),
#     user_token: UserOut = Depends(get_current_user)
# ):
#     try:
#         id_rol = user_token.id_rol
#         if not verify_permissions(db, id_rol, modulo, 'eliminar'):
#             raise HTTPException(status_code=401, detail="Usuario no autorizado para eliminar tareas")

#         crud_tareas.delete_tarea(db, id_tarea)
#         return {"message": "Tarea eliminada correctamente"}
#     except SQLAlchemyError as e:
#         raise HTTPException(status_code=500, detail="Error interno de base de datos")
