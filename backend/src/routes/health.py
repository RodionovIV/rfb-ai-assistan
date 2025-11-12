from src.routes.router import base_router
from src.settings.params.api import API
from src.api.health import Health


@base_router.get(path=API.HEALTH)
async def health():
    return Health()