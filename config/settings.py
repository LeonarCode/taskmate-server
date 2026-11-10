from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DOCKER_DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    GOOGLE_CLIENT_ID: str
    # para sa forgot password; kung walang SMTP_HOST, ilalabas lang ang code sa log (dev lang)
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    # cloudinary://API_KEY:API_SECRET@CLOUD_NAME (Cloudinary dashboard, "API Keys"); kung wala, ang larawan ay itatabi sa database
    CLOUDINARY_URL: str | None = None


settings = Settings()