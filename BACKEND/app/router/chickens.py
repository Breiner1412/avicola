from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db
from app.schemas.chickens import ChickenCreate, ChickenOut, ChickenPaginated, ChickenUpdate
from app.schemas.users import UserOut
from app.crud import chickens as crud_chickens
from app.crud import type_chickens as crud_types

router = APIRouter()
modulo = 20

@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_chicken(
    chicken: ChickenCreate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # El rol de quien usa el endpoint
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        if chicken.cantidad_gallinas <= 0:
            raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a cero")

        galpon = crud_chickens.get_galpon_info(db, chicken.id_galpon)
        if not galpon:
            raise HTTPException(status_code=404, detail="El galpón especificado no existe")
        
        nueva_cantidad = galpon['cant_actual'] + chicken.cantidad_gallinas

        if nueva_cantidad > galpon['capacidad']:
            raise HTTPException(status_code=400, detail="La cantidad de gallinas excede la capacidad  del galpón")

        tipo = crud_types.get_type_chicken_by_id(db, chicken.id_tipo_gallina)
        if not tipo:
            raise HTTPException(status_code=404, detail="El tipo de gallina especificado no existe")

        crud_chickens.create_chicken(db, chicken)
        return {"message": "Registro de gallinas creado correctamente"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/by-id/{id_ingreso}", response_model=ChickenOut)
def get_chicken(
    id_ingreso: int, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # El rol de quien usa el endpoint
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        chickens = crud_chickens.get_chicken_by_id(db, id_ingreso)
        if not chickens:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        return chickens
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/by-galpon", response_model=ChickenPaginated)
def get_chickens(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    id_galpon: int = Query(..., description="ID de galpón donde se hizo el registro"), 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # El rol de quien usa el endpoint
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        galpon = crud_chickens.get_galpon_info(db, id_galpon)
        if not galpon:
            raise HTTPException(status_code=404, detail="El galpón especificado no existe")

        skip = (page - 1) * page_size
        data = crud_chickens.get_chicken_by_galpon(db,skip=skip, limit=page_size, id_galpon=id_galpon)
        if not data or not data['total']:
            raise HTTPException(status_code=404, detail="Registro no encontrado")

        return ChickenPaginated(
            page=page,
            page_size=page_size,
            total_record_chickens=data['total'],
            total_pages=(data['total'] + page_size -1) // page_size,
            record_chickens=data['chickens']
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/all-chickens-pag", response_model=ChickenPaginated)
def get_chickens_pag(
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
        data = crud_chickens.get_all_chickens_pag(db, skip=skip, limit=page_size)
        if not data or not data['total']:
            raise HTTPException(status_code=404, detail="Registro no encontrado")

        return ChickenPaginated(
            page=page,
            page_size=page_size,
            total_record_chickens=data['total'],
            total_pages=(data['total'] + page_size -1) // page_size,
            record_chickens=data['chickens']
        )
    
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/by-fechas", response_model=ChickenPaginated)
def get_chickens_by_date(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    fecha_inicio: str = Query(..., description="Fecha inicial en formato YYYY-MM-DD"),
    fecha_fin: str = Query(..., description="Fecha final en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol  # El rol del usuario actual

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        skip = (page - 1) * page_size
        data = crud_chickens.get_chihckens_by_date_range(db, skip=skip, limit=page_size, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

        return ChickenPaginated(
            page=page,
            page_size=page_size,
            total_record_chickens=data['total'],
            total_pages=(data['total'] + page_size -1) // page_size,
            record_chickens=data['chickens']
        )

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.put("/by-id/{id_ingreso}")
def update_user(
    id_ingreso: int, 
    chicken: ChickenUpdate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol  # El rol del usuario actual

        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        registro_actual = crud_chickens.get_chicken_by_id(db, id_ingreso)
        if not registro_actual:
            raise HTTPException(status_code=404, detail="El registro de ingreso no existe")
        
        id_galpon = chicken.id_galpon or registro_actual["id_galpon"]

        galpon = crud_chickens.get_galpon_info(db, id_galpon)
        if not galpon:
            raise HTTPException(status_code=404, detail="El galpón especificado no existe")

        # Ocupación resultante: si el registro se queda en el mismo galpón,
        # se descuenta primero su cantidad anterior (el trigger hace el ajuste real).
        cantidad_nueva = chicken.cantidad_gallinas or registro_actual["cantidad_gallinas"]
        ocupacion = galpon['cant_actual'] + cantidad_nueva
        if id_galpon == registro_actual["id_galpon"]:
            ocupacion -= registro_actual["cantidad_gallinas"]
        if ocupacion > galpon['capacidad']:
            raise HTTPException(status_code=400, detail="La cantidad de gallinas excede la capacidad del galpón")
        
        if chicken.id_tipo_gallina is not None:
            tipo = crud_types.get_type_chicken_by_id(db, chicken.id_tipo_gallina)
            if not tipo:
                raise HTTPException(status_code=404, detail="El tipo de gallina especificado no existe")

        success = crud_chickens.update_chickens_by_id(db, id_ingreso, chicken)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el registro")
        return {"message": "Registro actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.delete("/eliminar/{id_ingreso}", status_code=status.HTTP_200_OK)
def delete_sale(
    id_ingreso: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'borrar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        sales = crud_chickens.delete_chicken_by_id(db, id_ingreso)
        if not sales:
            raise HTTPException(status_code=404, detail="Registro de gallinas no encontrada")
        return {"message": "Registro eliminado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
