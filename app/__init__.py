from __future__ import annotations

import warnings

from authlib.deprecate import AuthlibDeprecationWarning


warnings.filterwarnings(
    "ignore",
    message=r"authlib\.jose module is deprecated, please use joserfc instead\.",
    category=AuthlibDeprecationWarning,
    module=r"authlib\._joserfc_helpers",
)
warnings.filterwarnings(
    "ignore",
    message=r"\[EXPERIMENTAL\] feature FeatureName\.PLUGGABLE_AUTH is enabled\.",
    category=UserWarning,
    module=r"google\.adk\.features\._feature_decorator",
)


__all__ = ["AgentFactory", "create_agent", "load_agent_prompt", "root_agent"]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module 'app' has no attribute {name!r}")

    from app.agent import AgentFactory, create_agent, load_agent_prompt, root_agent

    exports = {
        "AgentFactory": AgentFactory,
        "create_agent": create_agent,
        "load_agent_prompt": load_agent_prompt,
        "root_agent": root_agent,
    }
    return exports[name]
