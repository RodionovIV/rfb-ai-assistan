from fastapi import APIRouter

from src.settings.params.api import API


base_router = APIRouter(prefix=API.PREFIX)