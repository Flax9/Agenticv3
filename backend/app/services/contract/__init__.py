"""
contract/__init__.py
Exposes the main public API of the contract module.
"""
from app.services.contract.schema import KontrakDefinitif, KONTRAK_JSON_SCHEMA
from app.services.contract.amendment_schema import DraftAmendemen, AMENDEMEN_JSON_SCHEMA

__all__ = [
    "KontrakDefinitif",
    "KONTRAK_JSON_SCHEMA",
    "DraftAmendemen",
    "AMENDEMEN_JSON_SCHEMA",
]
