import uvicorn
from fastapi import FastAPI

from src.database import init_models
from src.routes import router
from src.settings.general import config

app = FastAPI(
    title=config.project.name,
    description=config.project.description,
)

app.include_router(router)


@app.on_event("startup")
async def startup() -> None:
    await init_models()


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=config.app.host,
        port=config.app.port,
        reload=True,
        workers=1,
    )
