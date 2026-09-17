from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db
from app.schemas.alimento import AlimentoCreate, AlimentoUpdate, AlimentoOut, PaginatedAlimento
from app.crud import alimento as crud_type_alimento
from app.schemas.users import UserOut


router = APIRouter()
modulo = 28

@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_type_alimento(
    alimento: AlimentoCreate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # El rol de quien usa el endpoint
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        

        crud_type_alimento.create_type_alimento(db, alimento)

        return {"message": "Registro de tipo de alimento creado correctamente"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/all-alimentos", response_model=List[AlimentoOut])
def get_alimentos(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol  # El rol del usuario actual

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        alimentos = crud_type_alimento.get_all_alimentos(db)
        return alimentos

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/by-id", response_model=AlimentoOut)
def get__type_alimento(
    id_alimento: int, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # El rol de quien usa el endpoint
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        type_alimento = crud_type_alimento.get_type_alimento_by_id(db, id_alimento)
        if not type_alimento:
            raise HTTPException(status_code=404, detail="Tipo de alimento no encontrado")
        return type_alimento
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/all-type-alimentos_pag", response_model=PaginatedAlimento)
def get_all_consumo_pag(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol  # El rol del usuario actual

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        skip = (page - 1) * page_size
        type_alimento = crud_type_alimento.get_all_type_alimentos_pag(db, skip=skip, limit=page_size)
        
        total = type_alimento["total"]
        tipo_alimento = type_alimento["alimento"]
        
        return PaginatedAlimento(
            page= page,
            page_size= page_size,
            total_alimento= total,
            total_pages= (total + page_size - 1) // page_size,
            alimento= tipo_alimento
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.put("/by-id/{id_alimento}")
def update_alimento(
    id_alimento: int, 
    type_alimento: AlimentoUpdate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol  # El rol del usuario actual

        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        success = crud_type_alimento.update_type_alimento_by_id(db, id_alimento, type_alimento)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el registro")
        return {"message": "Registro actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/rango-fechas", response_model=PaginatedAlimento)
def obtener_alimento_por_rango_fechas(
    fecha_inicio: str = Query(..., description="Fecha inicial en formato YYYY-MM-DD"),
    fecha_fin: str = Query(..., description="Fecha final en formato YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    """
    Obtiene todas las tareas que inician o terminan dentro de un rango de fechas.
    Ignora las horas y devuelve las tareas ordenadas por fecha_hora_init.
    """
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        alimentos = crud_type_alimento.get_alimento_by_date_range(db, fecha_inicio, fecha_fin)
        

        total = len(alimentos)
        skip = (page - 1) * page_size
        end_index = skip + page_size
        
        alimentos_paginados = alimentos[skip:end_index]
            
        return PaginatedAlimento(
            page=page,
            page_size=page_size,
            total_alimento=total,
            total_pages=(total + page_size - 1) // page_size,
            alimento=alimentos_paginados
        )

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
