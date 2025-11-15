from __future__ import annotations

from typing import Any

from pydantic import Field
import pydantic_settings as ps


class BaseConfig(ps.BaseSettings):
    model_config = ps.SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class AppConfig(BaseConfig):
    model_config = ps.SettingsConfigDict(env_prefix="APP_", env_file=".env")

    host: str
    port: int


class ProjectConfig(BaseConfig):
    model_config = ps.SettingsConfigDict(env_prefix="PROJECT_", env_file=".env")

    name: str
    description: str


class DatabaseConfig(BaseConfig):
    model_config = ps.SettingsConfigDict(env_prefix="DB_", env_file=".env")

    dsn: str
    echo: bool = False


class RedisConfig(BaseConfig):
    model_config = ps.SettingsConfigDict(env_prefix="REDIS_", env_file=".env")

    url: str
    decode_responses: bool = False


class VectorIndexConfig(BaseConfig):
    model_config = ps.SettingsConfigDict(env_prefix="VECTOR_INDEX_", env_file=".env")

    name: str
    prefix: str
    dimension: int
    distance_metric: str
    algorithm: str


class ToolTomlSettingsSource(ps.TomlConfigSettingsSource):
    SECTION_PATH: tuple[str, ...] = ("tool", "ai_assistant_back")

    def __call__(self) -> dict[str, Any]:
        raw_data = super().__call__()
        section: dict[str, Any] = raw_data
        for key in self.SECTION_PATH:
            if not isinstance(section, dict):
                return {}
            section = section.get(key, {})
        if not isinstance(section, dict):
            return {}
        return section


class GeneralConfig(ps.BaseSettings):
    model_config = ps.SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app: AppConfig = Field(default_factory=AppConfig)
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    vector_index: VectorIndexConfig = Field(default_factory=VectorIndexConfig)

    @classmethod
    def load(cls) -> "GeneralConfig":
        return cls()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[ps.BaseSettings],
        init_settings: ps.PydanticBaseSettingsSource,
        env_settings: ps.PydanticBaseSettingsSource,
        dotenv_settings: ps.PydanticBaseSettingsSource,
        file_secret_settings: ps.PydanticBaseSettingsSource,
        **kwargs: Any,
    ) -> tuple[ps.PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            ToolTomlSettingsSource(settings_cls, "pyproject.toml"),
        )


config = GeneralConfig.load()
