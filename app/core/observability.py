import os
import logging
from typing import Optional, Dict, Any, List
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

def is_langfuse_enabled() -> bool:
    """
    Checks if Langfuse observability is enabled and properly configured with API keys.
    """
    if not settings.enable_langfuse:
        return False
    # Check settings or direct environment variables
    pub_key = settings.langfuse_public_key or os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sec_key = settings.langfuse_secret_key or os.getenv("LANGFUSE_SECRET_KEY", "")
    return bool(pub_key.strip() and sec_key.strip())


def sync_langfuse_environment():
    """
    Ensures Langfuse environment variables are populated from application settings.
    """
    if settings.langfuse_public_key and not os.getenv("LANGFUSE_PUBLIC_KEY"):
        os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
    if settings.langfuse_secret_key and not os.getenv("LANGFUSE_SECRET_KEY"):
        os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
    if settings.langfuse_host and not os.getenv("LANGFUSE_HOST"):
        os.environ["LANGFUSE_HOST"] = settings.langfuse_host


def get_langfuse_handler(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
):
    """
    Returns a configured Langfuse CallbackHandler for LangChain / LangGraph tracing.
    Returns None if Langfuse is not enabled or credentials are missing.
    """
    if not is_langfuse_enabled():
        return None

    try:
        sync_langfuse_environment()
        from langfuse.langchain import CallbackHandler
        handler = CallbackHandler()
        return handler
    except Exception as exc:
        logger.warning("Failed to initialize Langfuse CallbackHandler: %s", exc)
        return None


def get_trace_url_safe(trace_id: Optional[str]) -> Optional[str]:
    """
    Generates a direct dashboard URL to the trace in Langfuse UI.
    """
    if not trace_id or not is_langfuse_enabled():
        return None

    try:
        import langfuse
        client = langfuse.get_client()
        url = client.get_trace_url(trace_id=trace_id)
        if url:
            return url
    except Exception:
        pass

    host = (settings.langfuse_host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")).rstrip("/")
    return f"{host}/trace/{trace_id}"


def flush_langfuse():
    """
    Flushes queued Langfuse telemetry events.
    """
    if not is_langfuse_enabled():
        return
    try:
        import langfuse
        client = langfuse.get_client()
        client.flush()
    except Exception as exc:
        logger.debug("Langfuse flush warning: %s", exc)


def get_observability_status() -> Dict[str, Any]:
    """
    Returns current observability configuration status for health checks & UI badges.
    """
    configured = is_langfuse_enabled()
    pub_key = settings.langfuse_public_key or os.getenv("LANGFUSE_PUBLIC_KEY", "")
    masked_key = f"{pub_key[:6]}...{pub_key[-4:]}" if len(pub_key) > 10 else ("configured" if pub_key else "missing")

    return {
        "provider": "Langfuse",
        "enabled": settings.enable_langfuse,
        "configured": configured,
        "host": settings.langfuse_host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        "public_key_status": masked_key,
        "features": [
            "Agentic Step Waterfall Tracing",
            "Token & Cost Analytics Dashboard",
            "Latency Percentiles & Error Tracking",
            "User & Session Level Attribution",
        ]
    }

