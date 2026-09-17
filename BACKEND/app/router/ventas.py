from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from core.database import get_db
from app.router.dependencies import get_current_user
from app.crud.permisos import verify_permissions
from app.schemas.ventas import VentaCreate, VentaOut, VentaUpdate, ventaPag, VentaCreateResponse, DetalleVenta
from app.schemas.users import UserOut
from app.crud import ventas as crud_ventas
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

router = APIRouter()
modulo = 5

@router.post("/crear", response_model=VentaCreateResponse, status_code=status.HTTP_201_CREATED)
def create_venta(    
    venta: VentaCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail= 'Usuario no autorizado')
        
        # El vendedor siempre es el usuario autenticado
        venta.id_usuario = user_token.id_usuario
        venta_creada = crud_ventas.create_venta(db, venta)
        if not venta_creada:
            raise HTTPException(status_code=400, detail="No se pudo recuperar datos de la venta")
        
        respuesta =  {
                    "message": "Venta creada correctamente", 
                    "data_venta": venta_creada
                }
        return respuesta
    
    except IntegrityError as e:
        if "foreign key" in str(e.orig).lower():
            raise HTTPException(status_code=409, detail="Clave foranea inexistente")
        else:
            raise HTTPException(status_code=400, detail="Error de integridad en la base de datos")
    
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno en la base de datos")
    

@router.get("/all-ventas", response_model=List[VentaOut])
def get_all_ventas( 
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user) ):
    try:
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail= 'Usuario no autorizado')
        venta = crud_ventas.get_all_ventas(db)
        return venta
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/all-rango-fechas", response_model=List[VentaOut])
def get_ventas_by_date_range_sin_pag(
    fecha_inicio: str = Query(..., description="Fecha inicial en formato YYYY-MM-DD"),
    fecha_fin: str = Query(..., description="Fecha final en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        ventas = crud_ventas.get_ventas_by_date_range(db, fecha_inicio, fecha_fin)
        return ventas

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")      

        
@router.get("/all-ventas-pag", response_model=ventaPag)
def get_ventas(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    user_token: UserOut = Depends(get_current_user) 
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        skip = (page - 1) * page_size
        data = crud_ventas.get_all_ventas_pag(db, skip=skip, limit=page_size)
        
        total = data["cant_ventas"]
        ventas = data["ventas"]

        return {
            "page": page,
            "page_size": page_size,
            "total_ventas": total,
            "total_pages": (total + page_size - 1) // page_size,
            "ventas": ventas
        }
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/all-rango-fechas-pag", response_model=ventaPag)
def get_ventas_by_date_range(
    fecha_inicio: str = Query(..., description="Fecha inicial en formato YYYY-MM-DD"),
    fecha_fin: str = Query(..., description="Fecha final en formato YYYY-MM-DD"),
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
        data = crud_ventas.get_ventas_by_date_range_pag(db, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, skip=skip, limit=page_size)

        total = data["cant_ventas"]
        ventas = data["ventas"]

        return {
            "page": page,
            "page_size": page_size,
            "total_ventas": total,
            "total_pages": (total + page_size - 1) // page_size,
            "ventas": ventas
        }
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    

@router.get("/by-id-usuario-pag", response_model=ventaPag)
def get_ventas_by_usuario_pag(    
    usuario_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail= 'Usuario no autorizado')
        
        skip = (page - 1) * page_size
        data = crud_ventas.get_ventas_by_usuario_pag(db, usuario_id=usuario_id, skip=skip, limit=page_size)
        
        total = data["cant_ventas"]
        ventas = data["ventas"]

        return {
            "page": page,
            "page_size": page_size,
            "total_ventas": total,
            "total_pages": (total + page_size - 1) // page_size,
            "ventas": ventas
        }
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/by-tipo_pago-pag", response_model=ventaPag)
def get_ventas_by_tipo_pago_pag(
    tipo_id = int,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    user_token: UserOut = Depends(get_current_user) 
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        skip = (page - 1) * page_size
        data = crud_ventas.get_ventas_by_tipo_pago_pag(db, tipo_id=tipo_id, skip=skip, limit=page_size)
        
        total = data["cant_ventas"]
        ventas = data["ventas"]

        return {
            "page": page,
            "page_size": page_size,
            "total_ventas": total,
            "total_pages": (total + page_size - 1) // page_size,
            "ventas": ventas
        }
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")


@router.get("/by-id", response_model=VentaOut)
def get_venta_by_id(    
    venta_id: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user) ):
    try:
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail= 'Usuario no autorizado')
        venta = crud_ventas.get_venta_by_id(db, venta_id)
        if not venta:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        return venta
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    
     
@router.put("/by-id/{venta_id}")
def update_venta_by_id(
    venta_id: int,
    venta: VentaUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail= 'Usuario no autorizado')
        success = crud_ventas.update_venta_by_id(db, venta_id, venta)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar la venta")
        return {"message": "Venta actualizada correctamente"}
    
    except IntegrityError as e:
        if "foreign key" in str(e.orig).lower():
            raise HTTPException(status_code=409, detail="Clave foranea inexistente")
        else:
            raise HTTPException(status_code=400, detail="Error de integridad en la base de datos")
    
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error de base de datos al actualizar la venta")
    
    
@router.put("/cambiar-estado/{venta_id}", status_code=status.HTTP_200_OK)
def cambiar_venta_estado(
    venta_id: int,
    nuevo_estado: bool,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        success = crud_ventas.cambiar_venta_estado(db, venta_id, nuevo_estado)
        if not success:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        return {"message": f"Estado de la venta actualizada a {nuevo_estado}"}

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error de base de datos al cambiar el estado de la venta")
    

@router.delete("/by-id/{venta_id}")
def delete_venta_by_id(
    venta_id: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'borrar'):
            raise HTTPException(status_code=401, detail= 'Usuario no autorizado')
        success = crud_ventas.delete_venta_by_id(db, venta_id)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo eliminar la venta")
        return {"message": "Venta eliminada correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    
    
@router.get("/all-detalles-by-id", response_model=List[DetalleVenta])  
def get_all_detalle_by_id_venta(
    venta_id: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol  
        
        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")
        
        detalles_venta = crud_ventas.get_all_detalle_by_id_venta(db, venta_id)
        return detalles_venta
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
