from __future__ import annotations

from src.api.dialog import Dialog
from src.routes.router import base_router
from src.services.agents import AgentService
from src.settings.params.api import API


agent_service = AgentService()


@base_router.post(path=API.DIALOG, response_model=Dialog)
async def dialog(request: Dialog) -> Dialog:
    result = await agent_service.process_dialog(request.conversationId, request.content)
    conversation_id = request.conversationId or result["project_id"]
    return Dialog(conversationId=conversation_id, content=result["response"])
