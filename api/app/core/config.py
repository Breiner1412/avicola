"""Configuracion de la aplicacion, leida del entorno o del archivo .env."""

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


# Valores de los archivos de ejemplo y de los valores por defecto: nunca en produccion
CLAVES_DE_EJEMPLO = {
    "cambia-esta-clave-por-una-larga-y-aleatoria-de-32-o-mas",
    "Admin12345",
    "CambiaEstaClave123",
    "CambiaEstaClaveMigra123",
    "CambiaEstaClaveRoot123",
    "cambia-esta-clave",
}


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- General ---
    app_nombre: str = "Avícola"
    entorno: str = "desarrollo"
    # Demo publica: bloquea contrasenas, correos, permisos, cuentas y desactivaciones
    # para que ningun visitante la rompa para los demas (los datos se reinician cada noche)
    demo: bool = False
    # Zona de la granja: define "hoy" y los dias de los reportes (las horas se guardan en UTC)
    zona_horaria: str = "America/Bogota"

    # --- Base de datos ---
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "avicola"
    db_password: str = ""
    db_name: str = "avicola"
    # Usuario duenio del esquema, solo para las migraciones. El de arriba (db_user)
    # es el de la aplicacion y no puede crear ni quitar tablas ni triggers.
    # Vacio = las migraciones usan db_user (desarrollo y pruebas).
    db_migra_user: str = ""
    db_migra_password: str = ""

    # --- Sesiones ---
    jwt_secret: str = ""
    jwt_algoritmo: str = "HS256"
    minutos_acceso: int = 30
    dias_refresco: int = 14
    cookie_segura: bool = False
    cookie_refresco: str = "avicola_refresco"

    # --- Cache ---
    redis_url: str = ""

    # --- Usuario inicial ---
    admin_email: str = "admin@avicola.com"
    admin_password: str = "Admin12345"
    admin_nombre: str = "Administrador Avicola"
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

    def _url(self, usuario: str, clave: str) -> URL:
        return URL.create(
            "mysql+pymysql",
            username=usuario,
            password=clave,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )

    @model_validator(mode="after")
    def _produccion_segura(self) -> "Configuracion":
        """En produccion no arranca con las claves de ejemplo ni sin cookie segura."""
        if not self.es_produccion:
            return self
        problemas = []
        if self.jwt_secret in CLAVES_DE_EJEMPLO:
            problemas.append("JWT_SECRET es el de ejemplo")
        if self.admin_password in CLAVES_DE_EJEMPLO or len(self.admin_password) < 12:
            problemas.append("ADMIN_PASSWORD es la de ejemplo o tiene menos de 12 caracteres")
        if self.db_password in CLAVES_DE_EJEMPLO or not self.db_password:
            problemas.append("DB_PASSWORD esta vacia o es la de ejemplo")
        if self.db_migra_password and self.db_migra_password in CLAVES_DE_EJEMPLO:
            problemas.append("DB_MIGRA_PASSWORD es la de ejemplo")
        if not self.cookie_segura:
            problemas.append("COOKIE_SEGURA debe ser true (la app va detras de HTTPS)")
        if problemas:
            raise ValueError("Configuracion insegura para produccion: " + "; ".join(problemas))
        return self

    @property
    def url_base_datos(self) -> URL:
        return self._url(self.db_user, self.db_password)

    @property
    def url_migraciones(self) -> URL:
        if self.db_migra_user:
            return self._url(self.db_migra_user, self.db_migra_password)
        return self.url_base_datos

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
