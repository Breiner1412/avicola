"""Configuración de la aplicación (se lee de variables de entorno / archivo .env)."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "AVISENA"
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = "Aplicación para gestionar granjas avícolas"

    # Base de datos
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "avisena"
    DB_PASSWORD: str = ""
    DB_NAME: str = "avisena"

    # JWT (sin valor por defecto: la app no arranca sin JWT_SECRET)
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Correo (recuperación de contraseña)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@avisena.com"
    FRONTEND_URL: str = "http://localhost:8080"

    # Orígenes permitidos por CORS (separados por coma)
    CORS_ORIGINS: str = "http://localhost:8080,http://127.0.0.1:8080,http://localhost:5500,http://127.0.0.1:5500"

    @property
    def DATABASE_URL(self) -> URL:
        # URL.create escapa correctamente contraseñas con caracteres especiales
        return URL.create(
            "mysql+pymysql",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
            query={"charset": "utf8mb4"},
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Alias en minúscula usados por core/security.py
    @property
    def jwt_secret(self) -> str:
        return self.JWT_SECRET

    @property
    def jwt_algorithm(self) -> str:
        return self.JWT_ALGORITHM

    @property
    def jwt_access_token_expire_minutes(self) -> int:
        return self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES


settings = Settings()

if len(settings.JWT_SECRET) < 32:
    raise RuntimeError(
        "JWT_SECRET no está configurado (o es muy corto). "
        "Defínelo en el archivo .env con al menos 32 caracteres aleatorios."
    )
