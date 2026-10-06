from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PGS Search Engine API Gateway"
    api_v1_prefix: str = "/api/v1"

    
    admin_grpc_host: str = "localhost"
    admin_grpc_port: int = 50052

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 28800
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()