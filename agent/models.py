"""
agent/models.py
Definición de modelos de datos para asegurar coherencia entre componentes.
"""
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class AnalysisResult:
    """
    Modelo que representa el resultado final de un análisis.
    Usado por el Orchestrator para enviar datos a la UI.
    """
    initial_analysis: str = ""
    llm_reasoning: str = ""
    recommendations: str = ""
    
    # Datos crudos de herramientas (para depuración o detalles futuros)
    mcp_classification: Dict[str, Any] = field(default_factory=dict)
    mcp_laws: Dict[str, Any] = field(default_factory=dict)
    
    # Contadores de riesgo para los widgets de colores
    total_clauses: int = 0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
