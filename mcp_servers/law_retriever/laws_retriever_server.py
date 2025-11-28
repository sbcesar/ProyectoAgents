import json
import logging
from pathlib import Path
from typing import Optional
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from mcp.server.lowlevel.server import Server as MCPServer
from mcp.types import Tool
import mcp.types as types

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
    title="Law Retriever MCP",
    description="MCP Server para recuperar artículos legales por keywords",
    version="0.1.0"
)

# ============================================================
# VALIDACIÓN Y CARGA DE DATOS
# ============================================================

def validate_law_article(article: dict, filename: str) -> bool:
    """
    Valida que un artículo tenga los campos obligatorios.
    
    Campos requeridos: id, title, text
    Campos opcionales: keywords, notes, domain
    
    Args:
        article: diccionario del artículo
        filename: nombre del archivo para logging
        
    Returns:
        True si es válido, False si no
    """
    required_fields = {"id", "title", "text"}
    
    if not isinstance(article, dict):
        logger.warning(f"[{filename}] Article is not a dict: {type(article).__name__}")
        return False
    
    missing = required_fields - set(article.keys())
    if missing:
        logger.warning(f"[{filename}] Article missing required fields: {missing}")
        return False
    
    # Validar que los campos requeridos no sean vacíos
    for field in required_fields:
        if not article.get(field) or not str(article[field]).strip():
            logger.warning(f"[{filename}] Article field '{field}' is empty")
            return False
    
    return True


def load_laws_from_directory(laws_dir: Path) -> list[dict]:
    """
    Carga todos los artículos legales desde archivos JSON.
    
    Estructura soportada:
    1) Lista de artículos:
       [
         {"id": "LAU_1", "title": "...", "text": "..."},
         {"id": "LAU_2", "title": "...", "text": "..."}
       ]
    
    2) Objeto con "articles":
       {
         "domain": "LAU",
         "articles": [
           {"id": "LAU_1", "title": "...", "text": "..."}
         ]
       }
    
    Args:
        laws_dir: Path al directorio con archivos JSON
        
    Returns:
        Lista de artículos validados
    """
    laws = []
    
    if not laws_dir.exists():
        logger.error(f"Laws directory not found: {laws_dir}")
        return laws
    
    json_files = sorted(laws_dir.glob("*.json"))
    
    if not json_files:
        logger.warning(f"No JSON files found in: {laws_dir}")
        return laws
    
    for filepath in json_files:
        logger.info(f"Loading laws from: {filepath.name}")
        
        try:
            # Validar que el archivo no esté vacío
            if filepath.stat().st_size == 0:
                logger.warning(f"[{filepath.name}] File is empty, skipping")
                continue
            
            with filepath.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            loaded_count = 0
            
            # Caso 1: lista de artículos
            if isinstance(data, list):
                logger.info(f"[{filepath.name}] Detected list format")
                for article in data:
                    if validate_law_article(article, filepath.name):
                        # Añadir domain si no existe
                        if "domain" not in article:
                            article["domain"] = filepath.stem.upper()
                        laws.append(article)
                        loaded_count += 1
            
            # Caso 2: objeto con "articles"
            elif isinstance(data, dict):
                if "articles" in data and isinstance(data["articles"], list):
                    logger.info(f"[{filepath.name}] Detected dict with 'articles' key")
                    domain = data.get("domain", filepath.stem.upper())
                    
                    for article in data["articles"]:
                        if validate_law_article(article, filepath.name):
                            article["domain"] = domain
                            laws.append(article)
                            loaded_count += 1
                else:
                    # Objeto plano → validar y cargar
                    logger.info(f"[{filepath.name}] Detected flat object format")
                    if validate_law_article(data, filepath.name):
                        if "domain" not in data:
                            data["domain"] = filepath.stem.upper()
                        laws.append(data)
                        loaded_count += 1
            
            else:
                logger.warning(
                    f"[{filepath.name}] Unexpected JSON root type: {type(data).__name__}, "
                    f"expected list or dict"
                )
            
            logger.info(f"[{filepath.name}] ✓ Loaded {loaded_count} article(s)")
        
        except json.JSONDecodeError as e:
            logger.error(f"[{filepath.name}] Invalid JSON format: {e}")
        except Exception as e:
            logger.error(f"[{filepath.name}] Unexpected error: {e}", exc_info=True)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TOTAL: {len(laws)} law article(s) loaded successfully")
    logger.info(f"{'='*60}\n")
    
    return laws


# ============================================================
# CARGA DE LA BASE DE DATOS DE LEYES
# ============================================================

LAWS: list[dict] = []

try:
    base_dir = Path(__file__).parent
    laws_dir = base_dir / "laws"
    LAWS = load_laws_from_directory(laws_dir)
except Exception as e:
    logger.exception(f"Critical error during LAWS initialization: {e}")

# ============================================================
# DEFINICIÓN DEL SERVIDOR MCP
# ============================================================

server = MCPServer(name="law-retriever-mcp", version="0.1.0")


@server.list_tools()
async def list_tools(
    req: types.ListToolsRequest | None = None
) -> types.ListToolsResult:
    """
    Devuelve la lista de herramientas MCP disponibles.
    """
    tool = Tool(
        name="law_lookup",
        description=(
            "Busca artículos legales por keywords. "
            "Ej: topic='fianza' devuelve cláusulas sobre fianzas. "
            f"Base de datos: {len(LAWS)} artículos"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Palabra clave para buscar (ej: 'fianza', 'duración', 'depósito')"
                }
            },
            "required": ["topic"],
        },
    )
    return types.ListToolsResult(tools=[tool])


@server.call_tool()
async def call_tool(tool_name: str, params: dict | None = None) -> dict:
    """
    Ejecuta una herramienta MCP.
    """
    if tool_name != "law_lookup":
        return {
            "status": "error",
            "message": f"Unknown tool: {tool_name}"
        }
    
    return await law_lookup(tool_name, params)


# ============================================================
# TOOL MCP: law_lookup (MEJORADO)
# ============================================================

async def law_lookup(tool_name: str, params: dict | None = None) -> dict:
    """
    Busca artículos legales por keyword (Búsqueda inteligente).
    Rompe la frase en palabras clave y busca coincidencias.
    """
    if not params:
        params = {}
    
    topic = str(params.get("topic", "")).strip().lower()
    
    if not topic:
        return {
            "status": "error",
            "message": "Topic parameter is required",
            "results": []
        }
    
    # 1. Romper la frase en palabras clave (tokens)
    # Ignoramos palabras cortas (de, el, la, en...)
    query_tokens = [word for word in topic.split() if len(word) > 3]
    
    # Si no quedan tokens (ej: "el de la"), usamos la frase original
    if not query_tokens:
        query_tokens = [topic]

    scored_results = []
    
    for entry in LAWS:
        # Unir todo el texto del artículo para buscar
        title = str(entry.get("title", "")).lower()
        text = str(entry.get("text", "")).lower()
        keywords = [str(k).lower() for k in entry.get("keywords", [])]
        notes = str(entry.get("notes", "")).lower()
        
        full_content = f"{title} {text} {' '.join(keywords)} {notes}"
        
        # 2. Calcular puntuación de relevancia
        score = 0
        matches = []
        
        for token in query_tokens:
            if token in full_content:
                score += 1
                matches.append(token)
        
        # 3. Si hay coincidencia relevante, guardar
        if score > 0:
            # Bonus si está en el título
            if any(token in title for token in query_tokens):
                score += 2
                
            scored_results.append({
                "law": entry,
                "score": score,
                "matches": matches
            })
    
    # 4. Ordenar por relevancia (score más alto primero)
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    
    # 5. Quedarse solo con los datos de la ley (limpiar scores)
    final_results = [item["law"] for item in scored_results]
    
    logger.info(f"Query '{topic}' (Tokens: {query_tokens}) returned {len(final_results)} result(s)")
    
    return {
        "status": "ok",
        "query": topic,
        "tokens_used": query_tokens,
        "total_results": len(final_results),
        "results": final_results[:5] # Devolver solo el Top 5 para no saturar
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
        "service": "Law Retriever MCP",
        "version": "0.1.0",
        "status": "running",
        "laws_loaded": len(LAWS),
        "endpoints": {
            "health": "/health",
            "law_lookup": "POST /law_lookup",
            "swagger": "/docs",
            "openapi": "/openapi.json"
        },
        "documentation": "http://localhost:8001/docs"
    }


@app.get("/health")
async def health():
    """
    Endpoint de health check.
    """
    return {
        "status": "ok",
        "service": "law_retriever",
        "laws_available": len(LAWS)
    }


@app.post("/law_lookup")
async def http_law_lookup(payload: dict):
    """
    Endpoint HTTP para buscar artículos legales.
    
    Uso:
        POST /law_lookup
        {"topic": "fianza"}
    
    Respuesta:
        {
            "status": "ok",
            "query": "fianza",
            "total_results": 1,
            "results": [...]
        }
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")
    
    try:
        result = await law_lookup("law_lookup", payload)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in law_lookup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/laws")
async def list_laws():
    """
    Endpoint para listar todos los artículos legales cargados.
    """
    return {
        "total": len(LAWS),
        "laws": LAWS
    }


@app.get("/stats")
async def get_stats():
    """
    Endpoint con estadísticas de la base de datos.
    """
    domains = {}
    for law in LAWS:
        domain = law.get("domain", "unknown")
        domains[domain] = domains.get(domain, 0) + 1
    
    return {
        "total_articles": len(LAWS),
        "domains": domains,
        "domains_count": len(domains)
    }


# ============================================================
# MODO LOCAL / DEBUG
# ============================================================

async def _test_law_lookup():
    """Test manual del tool law_lookup."""
    test_queries = ["fianza", "duración", "depósito", "xyz"]
    
    print("\n" + "="*60)
    print("TESTING law_lookup TOOL")
    print("="*60 + "\n")
    
    for query in test_queries:
        print(f"Query: '{query}'")
        result = await law_lookup("law_lookup", {"topic": query})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("-" * 60 + "\n")


if __name__ == "__main__":
    # Ejecutar tests si está en modo debug
    print("\n" + "="*60)
    print("LAW RETRIEVER MCP SERVER")
    print("="*60)
    print(f"✓ Laws loaded: {len(LAWS)}")
    print("="*60)
    print("\n📍 SERVER ENDPOINTS:")
    print("   Raíz:        http://localhost:8001")
    print("   Health:      http://localhost:8001/health")
    print("   Swagger UI:  http://localhost:8001/docs")
    print("   Redoc:       http://localhost:8001/redoc")
    print("\n💾 CURL EXAMPLES:")
    print("   curl http://localhost:8001/")
    print("   curl http://localhost:8001/health")
    print("   curl http://localhost:8001/laws")
    print("   curl -X POST http://localhost:8001/law_lookup -H 'Content-Type: application/json' -d '{\"topic\": \"fianza\"}'")
    print("\n" + "="*60 + "\n")
    
    # Descomentar para ejecutar tests:
    # asyncio.run(_test_law_lookup())
    
    # Arrancar servidor
    logger.info("🚀 Starting Law Retriever MCP Server...")
    logger.info("📍 Listening on http://localhost:8001")
    logger.info("📖 Documentation: http://localhost:8001/docs")
    logger.info("Press CTRL+C to stop the server")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,
        log_level="info"
    )