from sqlalchemy import text
from typing import List
from app.schemas.users import UserOut
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db
from app.schemas.isolation import IsolationCreate, IsolationOut, IsolationUpdate, PaginatedIsolations
from app.crud import isolation as crud_isolation

router = APIRouter()
modulo = 23

@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_isolation(
    isolation: IsolationCreate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):    
    try:
        if isolation.id_galpon <= 0:
            raise HTTPException(status_code=400, detail="El ID del galpón debe ser mayor que cero")
    
        if isolation.id_incidente_gallina <= 0:
            raise HTTPException(status_code=400, detail="El ID del incidente debe ser mayor que cero")
        
        if isolation.id_galpon is None:
                raise HTTPException(status_code=422, detail="Debe ingresar un id galpón")
        # Validar galpón
        result = db.execute(text("SELECT id_galpon FROM galpones WHERE id_galpon = :id"), {"id": isolation.id_galpon}).first()
        if not result:
            raise HTTPException(status_code=404, detail="El id del galpón ingresado no existe")

        # Validar incidente
        result = db.execute(text("SELECT id_inc_gallina FROM incidentes_gallina WHERE id_inc_gallina = :id"), {"id": isolation.id_incidente_gallina}).first()
        if not result:
            raise HTTPException(status_code=404, detail="El id del incidente ingresado no existe")
            
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'insertar'):
                raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        crud_isolation.create_isolation(db, isolation)
        return {"message": "Aislamiento creado correctamente"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/by-id", response_model=IsolationOut)
def get_isolation(
    id: int, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    
    try:
        if  id <= 0:
            raise HTTPException(status_code=400, detail="El ID del aislamiento debe ser mayor que cero")
    
        # El rol de quien usa el endpoint
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        isolation = crud_isolation.get_isolation_by_id(db, id)
        if not isolation:
            raise HTTPException(status_code=404, detail="Aislamiento no encontrado")
        return isolation
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/all-isolation", response_model=List[IsolationOut])
def get_isolations(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol  # El rol del usuario actual

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        isolations = crud_isolation.get_all_isolations(db)
        return isolations

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/rango-fechas", response_model=PaginatedIsolations)
def obtener_isolation_por_rango_fechas(
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
        
        aislamientos = crud_isolation.get_aislamiento_by_date_range(db, fecha_inicio, fecha_fin)

        # Aplicar paginación manualmente a los resultados filtrados
        total = len(aislamientos)
        skip = (page - 1) * page_size
        end_index = skip + page_size
        
        # Obtener solo la página solicitada
        isolation_paginados = aislamientos[skip:end_index]
        
        return PaginatedIsolations(
            page=page,
            page_size=page_size,
            total_isolation=total,
            total_pages=(total + page_size - 1) // page_size,
            isolation=isolation_paginados
        )

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/all_isolations-pag", response_model=PaginatedIsolations)
def get_isolation_pag(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
): 
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        skip = (page - 1) * page_size
        data = crud_isolation.get_all_isolations_pag(db, skip=skip, limit=page_size)
        
        total = data["total"]
        isolation = data["isolation"]
        
        return PaginatedIsolations(
            page= page,
            page_size= page_size,
            total_isolation= total,
            total_pages= (total + page_size - 1) // page_size,
            isolation= isolation
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.put("/by-id/{isolation_id}")
def update_isolations(
    isolation_id: int, 
    isolation: IsolationUpdate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol  # El rol del usuario actual

        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        
        if isolation.id_galpon is not None:
            if isolation.id_galpon <= 0:
                raise HTTPException(status_code=400, detail="El ID del galpón debe ser mayor que cero")
        
        result = db.execute(text("SELECT id_galpon FROM galpones WHERE id_galpon = :id"), {"id": isolation.id_galpon}).first()
        if not result:
            raise HTTPException(status_code=404, detail="El id del galpón no existe")
        
        if isolation.id_incidente_gallina is not None:  
            if isolation.id_incidente_gallina <= 0:
                raise HTTPException(status_code=400, detail="El ID del incidente debe ser mayor que cero")

            result = db.execute(text("SELECT id_inc_gallina FROM incidentes_gallina WHERE id_inc_gallina = :id"), {"id": isolation.id_incidente_gallina}).first()
            if not result:
                raise HTTPException(status_code=404, detail="El id del incidente no existe")
    
        
        success = crud_isolation.update_isolation_by_id(db, isolation_id, isolation)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el aislamiento")
        return {"message": "Aislamiento actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
