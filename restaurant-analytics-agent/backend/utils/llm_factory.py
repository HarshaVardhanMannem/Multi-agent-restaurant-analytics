"""
LLM Factory
Creates LLM instances for different providers (NVIDIA, Grok/XAI)
"""

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


def create_llm(
    temperature: float = 0.1,
    top_p: float = 1,
    max_tokens: int = 1024,
    reasoning_budget: int | None = None,
    enable_thinking: bool = False,
) -> BaseChatModel:
    """
    Create an LLM instance based on configured provider.
    
    Args:
        temperature: Sampling temperature (0.0-2.0)
        top_p: Nucleus sampling parameter
        max_tokens: Maximum tokens to generate
        reasoning_budget: Reasoning budget for models that support it (NVIDIA only)
        enable_thinking: Enable thinking mode (NVIDIA only)
        
    Returns:
        BaseChatModel instance (NVIDIA or Grok)
    """
    settings = get_settings()
    provider = settings.llm_provider.lower()
    
    if provider == "grok":
        return _create_grok_llm(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
    elif provider == "nvidia":
        return _create_nvidia_llm(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            reasoning_budget=reasoning_budget,
            enable_thinking=enable_thinking,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'nvidia' or 'grok'")


def _create_nvidia_llm(
    temperature: float,
    top_p: float,
    max_tokens: int,
    reasoning_budget: int | None,
    enable_thinking: bool,
) -> BaseChatModel:
    """Create NVIDIA LLM instance"""
    from langchain_nvidia_ai_endpoints import ChatNVIDIA
    
    settings = get_settings()
    
    if not settings.nvidia_api_key:
        raise ValueError("NVIDIA_API_KEY is required when llm_provider='nvidia'")
    
    model = settings.nvidia_model
    
    llm_kwargs: dict[str, Any] = {
        "model": model,
        "nvidia_api_key": settings.nvidia_api_key,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    
    # Add reasoning budget and thinking if provided
    if reasoning_budget is not None:
        llm_kwargs["reasoning_budget"] = reasoning_budget
    
    if enable_thinking:
        llm_kwargs["chat_template_kwargs"] = {"enable_thinking": True}
    
    logger.info(f"Creating NVIDIA LLM: model={model}, temperature={temperature}")
    
    return ChatNVIDIA(**llm_kwargs)


def _create_grok_llm(
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> BaseChatModel:
    """Create Grok/XAI LLM instance using OpenAI-compatible API"""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise ImportError(
            "langchain-openai is required for Grok support. "
            "Install it with: pip install langchain-openai"
        )
    
    settings = get_settings()
    
    if not settings.grok_api_key:
        raise ValueError("GROK_API_KEY is required when llm_provider='grok'")
    
    # xAI API is OpenAI-compatible, so we can use ChatOpenAI
    # Model name for Grok - adjust based on actual xAI API model names
    model = settings.grok_model
    
    logger.info(f"Creating Grok LLM: model={model}, temperature={temperature}, base_url={settings.grok_base_url}")
    
    # top_p should be in model_kwargs to avoid warnings
    return ChatOpenAI(
        model=model,
        api_key=settings.grok_api_key,
        base_url=settings.grok_base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        model_kwargs={"top_p": top_p},
    )

