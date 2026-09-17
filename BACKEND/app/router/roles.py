from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from core.database import get_db
from app.router.dependencies import get_current_user
from app.crud.permisos import verify_permissions
from app.schemas.roles import RolCreate, RolOut, RolUpdate, RolPag
from app.schemas.users import UserOut
from app.crud import roles as crud_roles
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter()

modulo = 3

@router.post("/crear", status_code=status.HTTP_201_CREATED)
def create_rol(    
    rol: RolCreate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'insertar'):
            raise HTTPException(status_code=401, detail= 'Usuario no autorizado')
        crud_roles.create_rol(db, rol)
        return {"message": "Rol creado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    

@router.get("/by-nombre", response_model=RolOut)
def get_rol_by_nombre(    
    nombre_rol: str,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user) ):
    try:

        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail= 'Usuario no autorizado')
        rol = crud_roles.get_rol_by_nombre(db, nombre_rol)
        if not rol:
            raise HTTPException(status_code=404, detail="rol no encontrado")
        return rol
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    
    
@router.get("/by-id", response_model=RolOut)
def get_rol_by_id(    
    rol_id: int,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)):
    try:

        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'seleccionar'):
            raise HTTPException(status_code=401, detail= 'Usuario no autorizado')
        rol = crud_roles.get_rol_by_id(db, rol_id)
        if not rol:
            raise HTTPException(status_code=404, detail="Rol no encontrado")
        return rol
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    

@router.get("/all-roles-pag", response_model=RolPag)
def get_roles(
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
        data = crud_roles.get_all_roles_pag(db, skip=skip, limit=page_size)
        
        total = data["cant_roles"]
        roles = data["roles"]

        return {
            "page": page,
            "page_size": page_size,
            "total_roles": total,
            "total_pages": (total + page_size - 1) // page_size,
            "roles": roles
        }
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")  
    
    
@router.put("/by-id/{rol_id}")
def update_rol_by_id(
    rol_id: int,
    rol: RolUpdate,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        id_rol = user_token.id_rol

        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail= 'Usuario no autorizado')
        success = crud_roles.update_rol_by_id(db, rol_id, rol)
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el rol")
        return {"message": "rol actualizado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")
    
    
@router.put("/cambiar-estado/{rol_id}", status_code=status.HTTP_200_OK)
def cambiar_rol_estado(
    rol_id: int,
    nuevo_estado: bool,
    db: Session = Depends(get_db),
    user_token: UserOut = Depends(get_current_user)
):
    try:
        # Verificar permisos del usuario
        id_rol = user_token.id_rol
        if not verify_permissions(db, id_rol, modulo, 'actualizar'):
            raise HTTPException(status_code=401, detail="Usuario no autorizado")

        success = crud_roles.cambiar_rol_estado(db, rol_id, nuevo_estado)
        if not success:
            raise HTTPException(status_code=400, detail="No se puedo actualizar el estado del rol")
        return {"message": f"Estado del usuario actualizado a {nuevo_estado}"}
    
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Error interno de base de datos")