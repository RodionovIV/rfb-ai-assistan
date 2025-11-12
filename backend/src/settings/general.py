from pydantic import BaseModel, Field
import pydantic_settings as ps


class BaseConfig(ps.BaseSettings):
    model_config = ps.SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


class AppConfig(BaseConfig):
    model_config = ps.SettingsConfigDict(env_prefix="APP_")

    host: str
    port: int


class ProjectConfig(BaseModel):
    name: str
    description: str


class GeneralConfig(ps.BaseSettings):
    app: AppConfig = Field(default_factory=AppConfig)
    project: ProjectConfig

    @classmethod
    def load(cls) -> "GeneralConfig":
        return cls()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[ps.BaseSettings],
        **kwargs
    ) -> tuple[ps.PydanticBaseSettingsSource, ...]:
        return (ps.TomlConfigSettingsSource(settings_cls, "pyproject.toml"), )

config = GeneralConfig.load()
