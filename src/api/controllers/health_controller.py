from src.api.router_registry import SchulwareAPIRouter
from fastapi import HTTPException
from src.infrastructure.monitoring import capture_message, add_breadcrumb
import sentry_sdk

router = SchulwareAPIRouter(prefix="/health")


@router.get("/")
async def health_check():
    """
    Basic health check endpoint.
    """
    add_breadcrumb(
        message="Health check performed",
        category="health",
        level="info"
    )
    return {"status": "healthy", "message": "SchulwareAPI is running"}


@router.get("/sentry-test")
async def test_sentry():
    """
    Test endpoint to verify Sentry integration.
    """
    # Send a test message to Sentry
    capture_message(
        "Test message from SchulwareAPI",
        level="info",
        context={
            "test": True,
            "endpoint": "/api/health/sentry-test"
        }
    )

    return {
        "status": "success",
        "message": "Test message sent to Sentry/GlitchTip"
    }


@router.get("/sentry-error")
async def test_sentry_error():
    """
    Test endpoint to trigger an error for Sentry.
    """
    add_breadcrumb(
        message="About to trigger test error",
        category="test",
        level="warning"
    )

    # This will be caught by Sentry
    raise HTTPException(
        status_code=500,
        detail="This is a test error for Sentry/GlitchTip integration"
    )