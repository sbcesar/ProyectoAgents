#!/usr/bin/env python3
"""
agent/mcp_tools.py

Gestor de herramientas MCP.
Se encarga de hacer las llamadas HTTP a los servidores MCP (puertos 8001 y 8002).
"""

import requests
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURACIÓN MCP SERVERS
# ============================================================

# URLs de tus servidores MCP locales
MCP_LAW_RETRIEVER_URL = "http://localhost:8001/law_lookup"
MCP_CLASSIFIER_URL = "http://localhost:8002/classify_clauses"

# Tiempo máximo de espera por respuesta (segundos)
MCP_TIMEOUT = 10

# ============================================================
# GESTOR MCP TOOLS
# ============================================================

class MCPToolsManager:
    """Gestor de herramientas MCP."""
    
    def __init__(self):
        # Verificación básica de conexión (opcional)
        pass

    def classify_clauses(self, contract_text: str) -> Dict[str, Any]:
        """
        Llama a la herramienta 'classify_clauses' del servidor MCP (8002).
        
        Args:
            contract_text: Texto completo del contrato.
            
        Returns:
            Dict con la clasificación de cláusulas y riesgos.
        """
        try:
            logger.info("📞 MCP CALL: classify_clauses (Sending contract text...)")
            
            response = requests.post(
                MCP_CLASSIFIER_URL,
                json={"contract_text": contract_text},
                timeout=MCP_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                # A veces la respuesta viene anidada, intentamos normalizar
                clauses = result.get('clauses', [])
                logger.info(f"✅ MCP RESPONSE: Classified {len(clauses)} clauses")
                return result
            else:
                logger.error(f"❌ MCP ERROR (8002): Status {response.status_code} - {response.text}")
                return {"error": f"Status {response.status_code}", "clauses": []}
                
        except Exception as e:
            logger.error(f"❌ MCP CONNECTION ERROR (8002): {e}")
            return {"error": str(e), "clauses": []}
    
    def law_lookup(self, topic: str) -> Dict[str, Any]:
        """
        Llama a la herramienta 'law_lookup' del servidor MCP (8001).
        
        Args:
            topic: Término de búsqueda (ej: "fianza", "despido").
            
        Returns:
            Dict con los artículos legales encontrados.
        """
        try:
            # Limpieza básica del término
            topic = topic.strip().lower()
            if not topic:
                return {}

            logger.info(f"📞 MCP CALL: law_lookup ('{topic}')")
            
            response = requests.post(
                MCP_LAW_RETRIEVER_URL,
                json={"topic": topic},
                timeout=MCP_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                count = result.get('total_results', 0)
                logger.info(f"✅ MCP RESPONSE: Found {count} laws for '{topic}'")
                return result
            else:
                logger.error(f"❌ MCP ERROR (8001): Status {response.status_code} - {response.text}")
                return {"error": f"Status {response.status_code}", "results": []}
                
        except Exception as e:
            logger.error(f"❌ MCP CONNECTION ERROR (8001): {e}")
            return {"error": str(e), "results": []}

if __name__ == "__main__":
    # Test rápido si se ejecuta directamente
    manager = MCPToolsManager()
    print("🔍 Probando conexión con law_retriever...")
    res = manager.law_lookup("prueba")
    print(f"Resultado: {res}")
