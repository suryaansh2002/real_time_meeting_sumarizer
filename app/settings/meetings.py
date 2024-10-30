from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
import torch


class Settings(BaseSettings):
    # MongoDB Settings
    mongo_connection_string: str
    mongo_database_name: str
    
    # Model Settings
    hf_model_name: str
    huggingface_auth_token: str
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    sm_model_name: str
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        frozen=True
    )

    def __hash__(self) -> int:
        return hash((
            self.mongo_connection_string,
            self.mongo_database_name,
            self.hf_model_name,
            self.huggingface_auth_token,
            self.device
        ))


@lru_cache
def settings_instance() -> Settings:
    """
    Creates a singleton instance of Fast API Settings
    
    """
    return Settings()