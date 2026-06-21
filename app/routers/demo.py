from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import authenticate_api, AuthContext

router = APIRouter(prefix="/demo", tags=["Demo 接口"])


class EchoRequest(BaseModel):
    message: str
    extra: dict | None = None


@router.get("/hello")
async def demo_hello(auth: AuthContext = Depends(authenticate_api)):
    return {
        "message": "Hello from API Audit Platform",
        "app_id": auth.app_id,
        "api_key": auth.api_key,
    }


@router.post("/echo")
async def demo_echo(body: EchoRequest, auth: AuthContext = Depends(authenticate_api)):
    return {
        "echo": body.message,
        "received_extra": body.extra,
        "caller": {"app_id": auth.app_id, "api_key": auth.api_key},
    }


@router.get("/whoami")
async def demo_whoami(auth: AuthContext = Depends(authenticate_api)):
    return {
        "app_id": auth.app_id,
        "api_key": auth.api_key,
        "credential_id": auth.credential.id,
        "credential_name": auth.credential.name,
    }
