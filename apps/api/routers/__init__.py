"""
Routers module initialization.
"""

# Only import light routers - avoid heavy dependencies
from . import health, explorer

# Heavy routers with spacy/etc disabled for now:
# from . import query, validate, visualizations

__all__ = ["health", "explorer"]
