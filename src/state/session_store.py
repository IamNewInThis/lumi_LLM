# src/state/session_store.py
from typing import Dict

# WARNING: solo para desarrollo; usa Redis u otra capa en producción.
_LANG_BY_CONV: Dict[str, str] = {}

def get_lang(conv_id: str) -> str | None:
    return _LANG_BY_CONV.get(conv_id)

def set_lang(conv_id: str, lang: str) -> None:
    _LANG_BY_CONV[conv_id] = lang
