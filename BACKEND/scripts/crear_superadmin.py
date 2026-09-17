"""
Crea (o actualiza) el usuario superadmin.

Uso:
    python -m scripts.crear_superadmin
Variables de entorno (o .env):
    ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_NOMBRE, ADMIN_DOCUMENTO, ADMIN_TELEFONO

Si el correo ya existe no cambia la contraseña (a menos que se pase --reset).
"""
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

from core.database import SessionLocal  # noqa: E402
from core.security import get_hashed_password  # noqa: E402

ROL_SUPERADMIN = 1


def main() -> int:
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    nombre = os.getenv("ADMIN_NOMBRE", "Administrador AVISENA")
    documento = os.getenv("ADMIN_DOCUMENTO", "1000000000")
    telefono = os.getenv("ADMIN_TELEFONO", "3000000000")
    reset = "--reset" in sys.argv

    if not email or len(password) < 8:
        print("Define ADMIN_EMAIL y ADMIN_PASSWORD (mínimo 8 caracteres).")
        return 1

    with SessionLocal() as db:
        existente = db.execute(
            text("SELECT id_usuario FROM usuarios WHERE email = :email"), {"email": email}
        ).scalar()

        if existente and not reset:
            print(f"El superadmin {email} ya existe (usa --reset para cambiar su contraseña).")
            return 0

        if existente:
            db.execute(
                text("UPDATE usuarios SET pass_hash = :h, estado = TRUE, id_rol = :rol WHERE id_usuario = :id"),
                {"h": get_hashed_password(password), "rol": ROL_SUPERADMIN, "id": existente},
            )
            print(f"Contraseña del superadmin {email} actualizada.")
        else:
            db.execute(
                text("""
                    INSERT INTO usuarios (nombre, documento, id_rol, email, telefono, pass_hash, estado)
                    VALUES (:nombre, :documento, :rol, :email, :telefono, :h, TRUE)
                """),
                {"nombre": nombre, "documento": documento, "rol": ROL_SUPERADMIN,
                 "email": email, "telefono": telefono, "h": get_hashed_password(password)},
            )
            print(f"Superadmin {email} creado.")
        db.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
