from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def saude() -> dict[str, str]:
    return {"status": "ok"}

