from fastapi import APIRouter

from app.api.v1 import auth, chat, threads

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(threads.router, prefix="/threads", tags=["threads"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
