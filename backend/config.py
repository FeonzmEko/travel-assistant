from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    deepseek_api_key: str = "sk-xxx"
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-v4-pro"
    dashscope_api_key: str = ""
    dashscope_embedding_model: str = "text-embedding-v4"
    embedding_dimension: int = 1024
    milvus_uri: str = "http://localhost:19530"
    milvus_token: str = ""
    milvus_collection_name: str = "travel_knowledge"
    amap_api_key: str = "xxx"
    weather_api_key: str = "xxx"
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_expire_minutes: int = 1440
    database_url: str = "sqlite+aiosqlite:///./travel_assistant.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
