"""
Test endpoint to generate a 500 error for logging verification
"""

from fastapi import APIRouter

test_router = APIRouter(prefix="/test", tags=["test"])


@test_router.get("/error")
async def trigger_error():
    """Endpoint to trigger a 500 error for testing logging"""
    raise Exception("This is a test error to verify logging works")


@test_router.get("/http-error")
async def trigger_http_error():
    """Endpoint to trigger an HTTP error for testing logging"""
    from fastapi import HTTPException

    raise HTTPException(status_code=500, detail="This is a test HTTP 500 error")
