from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
import logging

from app.schemas.chicken_incident import incidentChickenCreate, incidentChickenUpdate
from app.crud.ocupacion import gallinas_retiradas_por_incidente, retirar_gallinas, devolver_gallinas

logger = logging.getLogger(__name__)

def create_incident(db: Session, incident_ch: incidentChickenCreate) -> Optional[bool]:
    try:
        query = text("""
            INSERT INTO incidentes_gallina (
                galpon_origen, tipo_incidente, cantidad, descripcion, fecha_hora, esta_resuelto
            ) VALUES (
                :galpon_origen, :tipo_incidente, :cantidad, :descripcion, :fecha_hora, :esta_resuelto
            )
        """)
        # Muertes y fugas sacan gallinas del galpón
        retirar_gallinas(
            db, incident_ch.galpon_origen,
            gallinas_retiradas_por_incidente(incident_ch.tipo_incidente, incident_ch.cantidad),
        )
        db.execute(query, incident_ch.model_dump())
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al crear el incidente de gallina: {e}")
        raise Exception("Error de base de datos al crear el incidente de gallina")


def get_incident_chicken_by_id(db: Session, id_incident_chicken: int):
    try:
        query = text("""
            SELECT id_inc_gallina, galpon_origen, tipo_incidente, cantidad, descripcion, fecha_hora, esta_resuelto, galpones.nombre
            FROM incidentes_gallina
            INNER JOIN galpones ON galpones.id_galpon = incidentes_gallina.galpon_origen
            WHERE id_inc_gallina = :id_inc_gallina
        """)
        result = db.execute(query, {"id_inc_gallina": id_incident_chicken}).mappings().first()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener incidente de gallina por id: {e}")
        raise Exception("Error de base de datos al obtener el incidente de gallina")


def get_all_chicken_incidents(db: Session):
    try:
        query = text("""
            SELECT id_inc_gallina, galpon_origen, tipo_incidente, cantidad, descripcion, fecha_hora, esta_resuelto, galpones.nombre
            FROM incidentes_gallina
            INNER JOIN galpones ON galpones.id_galpon = incidentes_gallina.galpon_origen
        """)
        result = db.execute(query).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los incidentes: {e}")
        raise Exception("Error de base de datos al obtener los incidentes")


def update_chicken_incident_by_id(db: Session, incident_chicken_id: int, chicken_incident: incidentChickenUpdate) -> Optional[bool]:
    try:
        chicken_incident_data = chicken_incident.model_dump(exclude_unset=True)
        if not chicken_incident_data:
            return False

        anterior = db.execute(text("""
            SELECT galpon_origen, tipo_incidente, cantidad FROM incidentes_gallina
            WHERE id_inc_gallina = :id FOR UPDATE
        """), {"id": incident_chicken_id}).mappings().first()
        if not anterior:
            db.rollback()
            return False

        # Deshacer el efecto anterior sobre el galpón y aplicar el nuevo
        retiradas_antes = gallinas_retiradas_por_incidente(anterior["tipo_incidente"], anterior["cantidad"])
        retiradas_ahora = gallinas_retiradas_por_incidente(
            chicken_incident_data.get("tipo_incidente", anterior["tipo_incidente"]),
            chicken_incident_data.get("cantidad", anterior["cantidad"]),
        )
        galpon_ahora = chicken_incident_data.get("galpon_origen", anterior["galpon_origen"])
        if retiradas_antes != retiradas_ahora or galpon_ahora != anterior["galpon_origen"]:
            devolver_gallinas(db, anterior["galpon_origen"], retiradas_antes)
            retirar_gallinas(db, galpon_ahora, retiradas_ahora)

        set_clauses = ", ".join([f"{key} = :{key}" for key in chicken_incident_data.keys()])
        sentencia = text(f"""
            UPDATE incidentes_gallina
            SET {set_clauses}
            WHERE id_inc_gallina = :id_inc_gallina
        """)

        chicken_incident_data["id_inc_gallina"] = incident_chicken_id
        result = db.execute(sentencia, chicken_incident_data)
        db.commit()
        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al actualizar el incidente gallina {incident_chicken_id}: {e}")
        raise Exception("Error de base de datos al actualizar el incidente gallina")


def get_incidentes_gallina_by_date_range(db: Session, fecha_inicio: str, fecha_fin: str):
    try:
        query = text("""
            SELECT id_inc_gallina, galpon_origen, tipo_incidente, cantidad, descripcion, fecha_hora, esta_resuelto, galpones.nombre
            FROM incidentes_gallina
            INNER JOIN galpones ON galpones.id_galpon = incidentes_gallina.galpon_origen
            WHERE DATE(fecha_hora) BETWEEN :fecha_inicio AND :fecha_fin
            ORDER BY fecha_hora ASC
        """)
        result = db.execute(query, {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin}).mappings().all()
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error al consultar los incidentes de gallinas por rango de fechas: {e}")
        raise Exception("Error de base de datos al consultar los incidentes de gallinas por rango de fechas")


def get_all_chicken_incidents_pag(db: Session, skip: int = 0, limit: int = 10):
    try:
        count_query = text("SELECT COUNT(id_inc_gallina) AS total FROM incidentes_gallina")
        total_result = db.execute(count_query).scalar() or 0

        data_query = text("""
            SELECT id_inc_gallina, galpon_origen, tipo_incidente, cantidad, descripcion, fecha_hora, esta_resuelto, galpones.nombre
            FROM incidentes_gallina
            LEFT JOIN galpones ON galpones.id_galpon = incidentes_gallina.galpon_origen
            ORDER BY id_inc_gallina DESC
            LIMIT :limit OFFSET :skip
        """)

        incidents = db.execute(data_query, {"skip": int(skip), "limit": int(limit)}).mappings().all()
        return {"total": total_result, "incidents": incidents}
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener los incidentes de gallinas: {e}", exc_info=True)
        raise Exception("Error de base de datos al obtener los incidentes de gallinas")

def change_chiken_status(db: Session, id_chiken: int, nuevo_estado: bool):
    try:
        sentencia = text("""
            UPDATE incidentes_gallina
            SET esta_resuelto = :estado
            WHERE id_inc_gallina = :id_chiken
        """)
        result = db.execute(sentencia, {"estado": nuevo_estado, "id_chiken": id_chiken})
        db.commit()

        return result.rowcount > 0

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error al cambiar el estado del usuario {id_chiken}: {e}")
        raise Exception("Error de base de datos al cambiar el estado del usuario")