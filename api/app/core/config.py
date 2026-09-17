"""Configuracion de la aplicacion, leida del entorno o del archivo .env."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- General ---
    app_nombre: str = "AVISENA"
    entorno: str = "desarrollo"

    # --- Base de datos ---
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "avisena"
    db_password: str = ""
    db_name: str = "avisena"

    # --- Sesiones ---
    jwt_secret: str = ""
    jwt_algoritmo: str = "HS256"
    minutos_acceso: int = 30
    dias_refresco: int = 14
    cookie_segura: bool = False
    cookie_refresco: str = "avisena_refresco"

    # --- Cache ---
    redis_url: str = ""

    # --- Usuario inicial ---
    admin_email: str = "admin@avisena.com"
    admin_password: str = "Admin12345"
    admin_nombre: str = "Administrador AVISENA"
    cuenta_demo: str = "Granja de ejemplo"
    finca_demo: str = "Finca principal"

    # --- Correo ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_desde: str = ""

    # --- Navegador ---
    cors_origenes: str = "http://localhost:3000,http://127.0.0.1:3000"

    @field_validator("jwt_secret")
    @classmethod
    def _secreto_suficiente(cls, valor: str) -> str:
        if len(valor) < 32:
            raise ValueError(
                "JWT_SECRET debe tener al menos 32 caracteres. "
                'Genera uno con: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return valor

    @property
    def url_base_datos(self) -> URL:
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )

    @property
    def lista_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origenes.split(",") if o.strip()]

    @property
    def es_produccion(self) -> bool:
        return self.entorno.lower().startswith("prod")


@lru_cache
def obtener_config() -> Configuracion:
    return Configuracion()


config = obtener_config()
