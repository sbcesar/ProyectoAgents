#!/usr/bin/env python3
"""
agent/llm_client.py
Cliente de Nebius LLM para Contract Guardian Agent.
Ahora simplificado para usar solo configuración y cliente básico.
"""

import logging
from typing import Optional
from openai import OpenAI
from config.nebius_config import (
    NEBIUS_API_BASE_URL,
    NEBIUS_API_KEY,
    NEBIUS_CONFIG,
    validate_config,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NebiumLLMClient:
    """Cliente para Nebius API."""
    
    def __init__(self):
        try:
            validate_config()
        except ValueError as e:
            logger.error(f"Config validation failed: {e}")
            raise
        
        self.client = OpenAI(
            base_url=NEBIUS_API_BASE_URL,
            api_key=NEBIUS_API_KEY,
        )
        logger.info(f"✅ Nebius LLM Client initialized ({NEBIUS_CONFIG['model']})")

# Instancia global
llm_client: Optional[NebiumLLMClient] = None

def get_llm_client() -> NebiumLLMClient:
    """Singleton para obtener el cliente."""
    global llm_client
    if llm_client is None:
        llm_client = NebiumLLMClient()
    return llm_client
