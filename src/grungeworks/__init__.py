"""GrungeWorks - Scanner-style noise and rasterization agent."""

try:
    # Try to use the full implementation
    from .grungeworks_agent import GrungeWorksAgent
except ImportError:
    # Fallback to stub if dependencies missing
    from .grunge_agent_stub import GrungeWorksAgent

__all__ = ["GrungeWorksAgent"]
