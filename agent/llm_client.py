#!/usr/bin/env python3
"""
agent/llm_client.py

Cliente de Nebius LLM para Contract Guardian Agent
Usa OpenAI-compatible client con Qwen3-30B-A3B-Thinking-2507
"""

import logging
from typing import Iterator, Optional
from openai import OpenAI
from config.nebius_config import (
    NEBIUS_API_BASE_URL,
    NEBIUS_API_KEY,
    NEBIUS_CONFIG,
    validate_config,
)

# ============================================================
# CONFIGURACIÓN LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# CLIENTE NEBIUS LLM
# ============================================================

class NebiumLLMClient:
    """Cliente para Nebius API con Qwen3."""
    
    def __init__(self):
        """Inicializa cliente de Nebius."""
        try:
            validate_config()
        except ValueError as e:
            logger.error(f"Config validation failed: {e}")
            raise
        
        self.client = OpenAI(
            base_url=NEBIUS_API_BASE_URL,
            api_key=NEBIUS_API_KEY,
        )
        
        logger.info(f"✅ Nebius LLM Client initialized")
        logger.info(f"   Model: {NEBIUS_CONFIG['model']}")
        logger.info(f"   Base URL: {NEBIUS_API_BASE_URL}")
    

        # ... (métodos anteriores: analyze_contract, reason_about_clauses, etc.) ...

    def extract_search_terms(self, initial_analysis: str) -> str:
        """
        Pide al LLM que identifique los conceptos legales CLAVE para buscar en la base de datos.
        NO streaming, necesitamos la respuesta completa para procesarla.
        """
        system_prompt = """Eres un asistente legal experto en recuperación de información.
Tu tarea es identificar conceptos legales clave para buscar en una base de datos de leyes españolas (Estatuto de los Trabajadores, LAU, etc.).

SALIDA OBLIGATORIA: Solo una lista de 3 a 5 términos separados por comas. Sin explicaciones, sin puntos finales.
Ejemplo: "despido improcedente, fianza, duración del contrato, preaviso"."""

        user_prompt = f"""Basado en este análisis preliminar de un contrato, identifica los 3-5 términos legales más críticos que debemos verificar en la ley para confirmar si hay ilegalidades.

ANÁLISIS PRELIMINAR:
{initial_analysis[:2000]}  # Pasamos los primeros 2000 chars para contexto

TÉRMINOS DE BÚSQUEDA:"""

        try:
            logger.info("🔍 Asking LLM for search terms...")
            response = self.client.chat.completions.create(
                model=NEBIUS_CONFIG["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Baja temperatura para ser preciso
                max_tokens=50,
                stream=False      # No streaming, queremos el texto ya
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error extracting search terms: {e}")
            # Fallback por si falla el LLM
            return "terminación, responsabilidad, pago"



    def analyze_contract(self, contract_text: str) -> Iterator[str]:
        """
        Analiza un contrato con streaming.
        
        Args:
            contract_text: Texto del contrato a analizar
            
        Yields:
            Chunks de análisis del LLM (streaming)
        """
        
        if not contract_text or len(contract_text.strip()) < 50:
            logger.warning("Contract text too short")
            return
        
        system_prompt = """Eres un abogado experto en derecho español con 20 años de experiencia.

Tu tarea: Analizar contratos y identificar cláusulas riesgosas o ilegales.

ANÁLISIS A REALIZAR:
1. Identificar tipos de cláusulas (terminación, pago, privacidad, etc.)
2. Detectar nivel de riesgo (ALTO/MEDIO/BAJO)
3. Señalar potenciales violaciones legales
4. Sugerir artículos legales aplicables
5. Proporcionar recomendaciones

FORMATO RESPUESTA:
- Sé conciso pero preciso (máx 500 palabras)
- Estructura: Tipo | Riesgo | Problema | Artículos | Recomendación
- Usa markdown para claridad
- Números de cláusulas si las hay

TONO: Profesional, directo, sin alarmismo pero honesto sobre riesgos"""
        
        user_prompt = f"""Por favor, analiza este contrato e identifica cláusulas riesgosas o ilegales según la ley española.

CONTRATO:
────────
{contract_text}

Proporciona un análisis detallado de los riesgos legales encontrados."""
        
        try:
            logger.info("🤖 Sending analysis request to Nebius LLM (streaming)...")
            
            with self.client.chat.completions.create(
                model=NEBIUS_CONFIG["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=NEBIUS_CONFIG["temperature"],
                top_p=NEBIUS_CONFIG.get("top_p", 0.95),
                max_tokens=NEBIUS_CONFIG["max_tokens"],
                stream=True,
            ) as stream:
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
        except Exception as e:
            logger.error(f"Error in analyze_contract: {e}")
            raise
    
    def reason_about_clauses(self, 
                            clauses_summary: str,
                            mcp_results: str) -> Iterator[str]:
        """
        Razona sobre cláusulas basado en resultados de MCP tools.
        
        Args:
            clauses_summary: Resumen de cláusulas detectadas
            mcp_results: Resultados de law_lookup + classify_clauses
            
        Yields:
            Chunks de razonamiento legal (streaming)
        """
        
        system_prompt = """Eres un abogado especialista en analizar y razonar sobre la legalidad de cláusulas contractuales.

Tu tarea: Dado un análisis inicial y verificación legal, genera razonamiento profundo sobre violaciones.

ESTRUCTURA RESPUESTA:
- Por cada cláusula problemática:
  * Qué dice la cláusula
  * Qué dice la ley
  * Por qué es violación o ilegal
  * Impacto legal
  * Recomendación específica"""
        
        user_prompt = f"""Basándote en estos resultados de análisis legal, razona sobre por qué estas cláusulas son problemáticas:

RESUMEN CLÁUSULAS:
─────────────────
{clauses_summary}

VERIFICACIÓN LEGAL (de MCP tools):
──────────────────────────────────
{mcp_results}

Genera razonamiento detallado sobre la legalidad de cada cláusula."""
        
        try:
            logger.info("🧠 Requesting legal reasoning from Nebius LLM (streaming)...")
            
            with self.client.chat.completions.create(
                model=NEBIUS_CONFIG["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=NEBIUS_CONFIG["temperature"],
                top_p=NEBIUS_CONFIG.get("top_p", 0.95),
                max_tokens=NEBIUS_CONFIG["max_tokens"],
                stream=True,
            ) as stream:
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
        except Exception as e:
            logger.error(f"Error in reason_about_clauses: {e}")
            raise
    
    def generate_recommendations(self, analysis_data: str) -> Iterator[str]:
        """
        Genera recomendaciones personalizadas basadas en análisis.
        
        Args:
            analysis_data: Datos de análisis completo
            
        Yields:
            Chunks de recomendaciones (streaming)
        """
        
        system_prompt = """Eres un asesor legal experto en negociación de contratos.

Tu tarea: Basándote en análisis legal, generar recomendaciones prácticas y accionables."""
        
        user_prompt = f"""Basándote en este análisis, genera recomendaciones prácticas para el cliente:

ANÁLISIS:
────────
{analysis_data}

Por favor proporciona:
1. Cláusulas a RECHAZAR (críticas)
2. Cláusulas a NEGOCIAR (importantes)
3. Cláusulas ACEPTABLES (sin problemas)
4. Estrategia de negociación recomendada"""
        
        try:
            logger.info("💡 Requesting recommendations from Nebius LLM (streaming)...")
            
            with self.client.chat.completions.create(
                model=NEBIUS_CONFIG["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=NEBIUS_CONFIG["temperature"],
                top_p=NEBIUS_CONFIG.get("top_p", 0.95),
                max_tokens=NEBIUS_CONFIG["max_tokens"],
                stream=True,
            ) as stream:
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                        
        except Exception as e:
            logger.error(f"Error in generate_recommendations: {e}")
            raise


# ============================================================
# INSTANCIA GLOBAL
# ============================================================

llm_client: Optional[NebiumLLMClient] = None

def get_llm_client() -> NebiumLLMClient:
    """Obtiene o crea instancia del cliente LLM."""
    global llm_client
    if llm_client is None:
        llm_client = NebiumLLMClient()
    return llm_client


if __name__ == "__main__":
    # Test básico
    client = get_llm_client()
    print("✅ LLM Client initialized successfully")