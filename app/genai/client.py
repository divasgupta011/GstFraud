# app/genai/client.py

from functools import lru_cache
from typing import Optional

from langchain_groq import ChatGroq

from ..config import get_settings

_settings = get_settings()


@lru_cache
def get_llm() -> Optional[ChatGroq]:
    """
    Returns a singleton ChatGroq instance, or None if Groq isn't configured.
    """
    if not _settings.groq_api_key:
        return None

    llm = ChatGroq(
        groq_api_key=_settings.groq_api_key,
        model_name=_settings.groq_model,
        temperature=0.2,
    )
    return llm
