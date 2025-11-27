#!/usr/bin/env python3
"""
Clause Classifier MCP Server
Servidor MCP que expone el clasificador de cláusulas como herramienta
para que otros servicios (como Gradio) puedan usarlo

REQUISITOS:
    pip install mcp

USO:
    python mcp_servers/clause_classifier/server.py

Esto expondrá:
    - Tool: classify_clauses (clasifica cláusulas de un contrato)
    - Tool: analyze_clause_type (analiza un tipo de cláusula específica)
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from mcp.server.lowlevel.server import Server as MCPServer
from mcp.types import Tool
import mcp.types as types

# Importar el clasificador
import sys
sys.path.insert(0, str(Path(__file__).parent))
from classifier import ClauseClassifier, RiskLevel, ClauseType, ClassifiedClause

# ============================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# FASTAPI APP (HTTP wrapper)
# ============================================================

app = FastAPI(
    title="Clause Classifier MCP",
    description="MCP Server para clasificar cláusulas legales",
    version="0.1.0"
)

# ============================================================
# DEFINICIÓN DEL SERVIDOR MCP
# ============================================================

server = MCPServer(name="clause-classifier-mcp", version="0.1.0")


@server.list_tools()
async def list_tools(
    req: types.ListToolsRequest | None = None
) -> types.ListToolsResult:
    """
    Devuelve la lista de herramientas MCP disponibles.
    """
    tools = [
        Tool(
            name="classify_clauses",
            description=(
                "Clasifica automáticamente las cláusulas de un contrato. "
                "Detecta tipos de cláusulas (terminación, responsabilidad, etc.), "
                "asigna niveles de riesgo y proporciona artículos legales aplicables."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "contract_text": {
                        "type": "string",
                        "description": "Texto completo del contrato a analizar"
                    }
                },
                "required": ["contract_text"],
            },
        ),
        Tool(
            name="analyze_clause_type",
            description=(
                "Analiza un tipo específico de cláusula. "
                "Proporciona patrones comunes, red flags y recomendaciones."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "clause_type": {
                        "type": "string",
                        "description": "Tipo de cláusula a analizar (TERMINATION, LIABILITY, PRIVACY, etc.)"
                    }
                },
                "required": ["clause_type"],
            },
        )
    ]
    return types.ListToolsResult(tools=tools)


@server.call_tool()
async def call_tool(tool_name: str, params: dict | None = None) -> dict:
    """
    Ejecuta una herramienta MCP.
    """
    if tool_name == "classify_clauses":
        return await classify_clauses_handler(params)
    elif tool_name == "analyze_clause_type":
        return await analyze_clause_type_handler(params)
    else:
        return {
            "status": "error",
            "message": f"Unknown tool: {tool_name}"
        }


# ============================================================
# HANDLERS DE HERRAMIENTAS MCP
# ============================================================

async def classify_clauses_handler(params: dict | None = None) -> dict:
    """
    Handler para clasificar cláusulas de un contrato.
    """
    if not params:
        params = {}
    
    contract_text = str(params.get("contract_text", "")).strip()
    
    if not contract_text:
        return {
            "status": "error",
            "message": "contract_text parameter is required and cannot be empty",
            "results": []
        }
    
    try:
        # Clasificar contrato
        classified_clauses = ClauseClassifier.classify_contract(contract_text)
        
        # Generar resumen
        summary = ClauseClassifier.get_summary(classified_clauses)
        
        # Convertir a formato serializable
        clauses_data = []
        for clause in classified_clauses:
            clauses_data.append({
                "id": clause.id,
                "clause_text": clause.clause_text,
                "clause_type": clause.clause_type.value,
                "risk_level": clause.risk_level.value,
                "risk_score": clause.risk_score,
                "legal_issue": clause.legal_issue,
                "applicable_laws": clause.applicable_laws,
                "recommendations": clause.recommendations,
                "key_terms": clause.key_terms
            })
        
        logger.info(f"Contract analyzed: {len(clauses_data)} clauses classified")
        
        return {
            "status": "ok",
            "total_clauses": len(clauses_data),
            "summary": summary,
            "clauses": clauses_data
        }
        
    except Exception as e:
        logger.error(f"Error classifying clauses: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "results": []
        }


async def analyze_clause_type_handler(params: dict | None = None) -> dict:
    """
    Handler para analizar un tipo específico de cláusula.
    """
    if not params:
        params = {}
    
    clause_type_str = str(params.get("clause_type", "")).strip().upper()
    
    if not clause_type_str:
        return {
            "status": "error",
            "message": "clause_type parameter is required",
            "results": []
        }
    
    try:
        # Buscar el tipo de cláusula
        clause_type = None
        for ct in ClauseType:
            if ct.name == clause_type_str:
                clause_type = ct
                break
        
        if not clause_type:
            return {
                "status": "error",
                "message": f"Unknown clause type: {clause_type_str}. Valid types: " + 
                          ", ".join([ct.name for ct in ClauseType]),
                "results": []
            }
        
        # Obtener patrones
        patterns = ClauseClassifier.CLAUSE_PATTERNS.get(clause_type, {})
        laws = ClauseClassifier.APPLICABLE_LAWS.get(clause_type, [])
        
        result = {
            "status": "ok",
            "clause_type": clause_type.value,
            "description": f"Análisis del tipo de cláusula: {clause_type.value}",
            "keywords": patterns.get("keywords", []),
            "red_flags": patterns.get("red_flags", []),
            "applicable_laws": laws,
            "risk_indicators": {
                "high_risk": [flag for flag in patterns.get("red_flags", [])],
                "attention_needed": patterns.get("keywords", [])
            }
        }
        
        logger.info(f"Analyzed clause type: {clause_type.value}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing clause type: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "results": []
        }


# ============================================================
# ENDPOINTS HTTP
# ============================================================

@app.get("/")
async def root():
    """
    Endpoint raíz con información del servicio.
    """
    return {
        "service": "Clause Classifier MCP",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "classify": "POST /classify_clauses",
            "analyze": "POST /analyze_clause_type",
            "swagger": "/docs",
            "openapi": "/openapi.json"
        },
        "documentation": "http://localhost:8002/docs"
    }


@app.get("/health")
async def health():
    """
    Endpoint de health check.
    """
    return {
        "status": "ok",
        "service": "clause_classifier"
    }


@app.post("/classify_clauses")
async def http_classify_clauses(payload: dict):
    """
    Endpoint HTTP para clasificar cláusulas.
    
    Uso:
        POST /classify_clauses
        {"contract_text": "..."}
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    
    try:
        result = await classify_clauses_handler(payload)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in classify_clauses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze_clause_type")
async def http_analyze_clause_type(payload: dict):
    """
    Endpoint HTTP para analizar un tipo de cláusula.
    
    Uso:
        POST /analyze_clause_type
        {"clause_type": "TERMINATION"}
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    
    try:
        result = await analyze_clause_type_handler(payload)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in analyze_clause_type: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("CLAUSE CLASSIFIER MCP SERVER")
    print("="*70)
    print(f"✓ Clause types: {len(ClauseType)} tipos de cláusulas soportados")
    print("="*70)
    print("\n📍 SERVER ENDPOINTS:")
    print("   Raíz:        http://localhost:8002")
    print("   Health:      http://localhost:8002/health")
    print("   Swagger UI:  http://localhost:8002/docs")
    print("   Redoc:       http://localhost:8002/redoc")
    print("\n💾 CURL EXAMPLES:")
    print("   curl http://localhost:8002/")
    print("   curl http://localhost:8002/health")
    print("   curl -X POST http://localhost:8002/classify_clauses -H 'Content-Type: application/json' -d '{\"contract_text\": \"...\"}'")
    print("\n" + "="*70 + "\n")
    
    # Arrancar servidor
    logger.info("🚀 Starting Clause Classifier MCP Server...")
    logger.info("📍 Listening on http://localhost:8002")
    logger.info("📖 Documentation: http://localhost:8002/docs")
    logger.info("Press CTRL+C to stop the server")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8002,
        log_level="info"
    )