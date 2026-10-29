from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict[str, str]:
    """Report API process responsiveness only, not database/dependency health."""
    return {"status": "ok"}
