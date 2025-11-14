from src.api.dialog import Dialog
from src.routes.router import base_router
from src.settings.params.api import API


@base_router.post(path=API.DIALOG, response_model=Dialog)
async def dialog(request: Dialog):
    return Dialog(conversationId=request.conversationId, content="Ok")

