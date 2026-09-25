from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.limiter import limiter

router = APIRouter(tags=["health"])


class HealthOut(BaseModel):
    status: str

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})


@router.get(
    "/health",
    response_model=HealthOut,
    summary="Health check",
    description="Liveness check. Returns ok as long as the server process is running -- does not verify database or LLM provider connectivity.",
)
@limiter.exempt
def health_check():
    return {"status": "ok"}
