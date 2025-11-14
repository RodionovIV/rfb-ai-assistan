import uvicorn
from fastapi import FastAPI

from src.routes import router
from src.settings.general import config

app = FastAPI(
    title=config.project.name,
    description=config.project.description,
)

app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=config.app.host,
        port=config.app.port,
        reload=True,
        workers=1,
    )
