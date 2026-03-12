"""SDK configuration and selection logic.

This module provides a global setting to choose between claude-agent-sdk and opencode-ai.
"""

from typing import Literal

SDKType = Literal["claude", "opencode", "azure"]

# Global SDK selection (can be overridden via CLI arguments)
_current_sdk: SDKType = "claude"


def set_sdk(sdk: SDKType) -> None:
    """Set the current SDK to use globally."""
    global _current_sdk
    if sdk not in ("claude", "opencode", "azure"):
        raise ValueError(f"Invalid SDK type: {sdk}. Must be 'claude', 'opencode', or 'azure'")
    _current_sdk = sdk


def get_sdk() -> SDKType:
    """Get the currently configured SDK."""
    return _current_sdk


def is_claude_sdk() -> bool:
    """Check if claude-agent-sdk is the current SDK."""
    return _current_sdk == "claude"


def is_opencode_sdk() -> bool:
    """Check if opencode-ai is the current SDK."""
    return _current_sdk == "opencode"


def is_azure_sdk() -> bool:
    """Check if azure is the current SDK."""
    return _current_sdk == "azure"
