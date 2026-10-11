"""
DEV_CORE Engine Core Services
"""

def __getattr__(name):
    if name in {
        "SqliteKnowledgeProvider",
        "RepoWiseKnowledgeProvider",
        "CompositeKnowledgeProvider",
        "KnowledgeProviderError",
        "KnowledgeProjectMismatch",
    }:
        from . import knowledge_provider
        return getattr(knowledge_provider, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SqliteKnowledgeProvider",
    "RepoWiseKnowledgeProvider",
    "CompositeKnowledgeProvider",
    "KnowledgeProviderError",
    "KnowledgeProjectMismatch",
]
