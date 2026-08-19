"""
devcore_engine.installers -- Client and environment integration installers.
"""

from devcore_engine.installers.claude_installer import (
    ClaudeInstaller,
    detect_environment,
)

__all__ = ["ClaudeInstaller", "detect_environment"]
