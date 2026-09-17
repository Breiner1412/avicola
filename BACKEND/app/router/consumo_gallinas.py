from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.crud.permisos import verify_permissions
from app.router.dependencies import get_current_user
from core.database import get_db
from app.schemas.consumo_gallinas import ConsumoCreate, ConsumoOut, ConsumoPaginated, ConsumoUpdate, ConsumoAllOut
from app.schemas.users import UserOut
from app.crud import consumo_gallinas as crud_consumo

router = APIRouter()
modulo = 27

@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_consumo(
    consumo: ConsumoCreate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # El rol de quien usa el endpoint
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        if consumo.cantidad_alimento <= 0:
            raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a cero")

        galpon = crud_consumo.get_galpon_info(db, consumo.id_galpon)
        alimento = crud_consumo.get_alimento_info(db, consumo.id_alimento)

        if not galpon and not alimento:
            raise HTTPException(status_code=404, detail="El galpón y el alimento especificados no existen")

        if not galpon:
            raise HTTPException(status_code=404, detail="El galpón especificado no existe")

        if not alimento:
            raise HTTPException(status_code=404, detail="El alimento especificado no existe")

        disponible = crud_consumo.get_cantidad_disponible(db, consumo.id_alimento)
        if disponible < consumo.cantidad_alimento:
            raise HTTPException(
                status_code=400,
                detail=f"No hay suficiente alimento disponible. Disponible: {disponible}, requerido: {consumo.cantidad_alimento}"
            )

        # El descuento del alimento lo hace el trigger trg_consumo_ai
        crud_consumo.create_consumo(db, consumo)
        return {"message": "Registro de consumo creado correctamente"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/by-id/{id_consumo}", response_model=ConsumoOut)
def get_chicken(
    id_consumo: int, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # El rol de quien usa el endpoint
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        consumo = crud_consumo.get_consumo_by_id(db, id_consumo)
        if not consumo:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        return consumo
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/all-consumos-pag", response_model=ConsumoPaginated)
def get_consumos_pag(
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
        data = crud_consumo.get_all_consumo_pag(db, skip=skip, limit=page_size)

        if data is None:
            raise HTTPException(status_code=404, detail="Registro no encontrado")

        return ConsumoPaginated(
            page=page,
            page_size=page_size,
            total_consumos=data['total'], 
            total_pages=(data['total'] + page_size - 1) // page_size if data['total'] > 0 else 0,
            consumos=data['consumo']  
        )
    
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/by-galpon", response_model=ConsumoPaginated)
def get_consumo(
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
        
        galpon = crud_consumo.get_galpon_info(db, id_galpon)
        if not galpon:
            raise HTTPException(status_code=404, detail="El galpón especificado no existe")

        skip = (page - 1) * page_size
        data = crud_consumo.get_consumo_by_galpon(db,skip=skip, limit=page_size, id_galpon=id_galpon)

        return ConsumoPaginated(
            page=page,
            page_size=page_size,
            total_consumos=data['total'],
            total_pages=(data['total'] + page_size -1) // page_size,
           consumos=data['consumo']
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/all-consumos", response_model=ConsumoAllOut)
def get_consumos_all(
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    id_rol = user_token.id_rol  

    if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
        raise HTTPException(status_code=401, detail="Usuario no autorizado")

    data = crud_consumo.get_all_consumo(db)

    return {"consumos": data}


@router.put("/by-id/{id_consumo}")
def update_consumo(
    id_consumo: int, 
    consumo: ConsumoUpdate, 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol  

        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        registro_actual = crud_consumo.get_consumo_by_id(db, id_consumo)
        if not registro_actual:
            raise HTTPException(status_code=404, detail="El consumo ingresado no existe")
        
        if consumo.cantidad_alimento is not None and consumo.cantidad_alimento <= 0:
            raise HTTPException(status_code=400, detail="La cantidad debe ser mayor a cero")

        id_galpon = consumo.id_galpon or registro_actual["id_galpon"]
        id_alimento = consumo.id_alimento or registro_actual["id_alimento"]

        galpon = crud_consumo.get_galpon_info(db, id_galpon)
        alimento = crud_consumo.get_alimento_info(db, id_alimento)
        
        if not galpon and not alimento:
            raise HTTPException(status_code=404, detail="El galpón y el alimento especificados no existen")

        if not galpon:
            raise HTTPException(status_code=404, detail="El galpón especificado no existe")
        
        if not alimento:
            raise HTTPException(status_code=404, detail="El alimento especificado no existe")
        
        cantidad_actual = registro_actual["cantidad_alimento"]
        nueva_cantidad = consumo.cantidad_alimento or cantidad_actual

        # Si cambia el alimento se necesita la cantidad completa del nuevo;
        # si es el mismo, solo la diferencia.
        if id_alimento != registro_actual["id_alimento"]:
            incremento = nueva_cantidad
        else:
            incremento = nueva_cantidad - cantidad_actual

        # Si el usuario aumenta la cantidad:
        if incremento > 0:
            # Obtener inventario disponible del alimento
            cantidad_disponible = crud_consumo.get_cantidad_disponible(db, id_alimento)

            if cantidad_disponible < incremento:
                raise HTTPException(
                    status_code=400,
                    detail="No hay suficiente alimento disponible. "
                           f"Disponible: {cantidad_disponible}, requerido: {incremento}"
                )

        success = crud_consumo.update_consumo_by_id(db, id_consumo, consumo)
        
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el Registro")

        return {"message": "Registro actualizado correctamente"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")

@router.get("/rango-fechas", response_model=ConsumoPaginated)
def obtener_consumos_por_rango_fechas(
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
        
        consumos_alimento = crud_consumo.get_consumo_by_date_range(db, fecha_inicio, fecha_fin)

        # Aplicar paginación manualmente a los resultados filtrados
        total = len(consumos_alimento)
        skip = (page - 1) * page_size
        end_index = skip + page_size
        
        # Obtener solo la página solicitada
        consumos_paginados = consumos_alimento[skip:end_index]
        
        return ConsumoPaginated(
            page=page,
            page_size=page_size,
            total_consumos=total,
            total_pages=(total + page_size - 1) // page_size,
            consumos=consumos_paginados
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.delete("/eliminar/{id_consumo}", status_code=status.HTTP_200_OK)
def delete_consumo(
    id_consumo: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'borrar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        consumo = crud_consumo.delete_consumo_by_id(db, id_consumo)
        if not consumo:
            raise HTTPException(status_code=404, detail="Consumo no encontrado")
        return {"message": "Registro eliminado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


