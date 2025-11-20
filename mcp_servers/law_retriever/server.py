import json
import logging
import uvicorn
from pathlib import Path
import asyncio

from mcp.server.lowlevel.server import Server as MCPServer
from mcp.types import Tool
import mcp.types as types

logger = logging.getLogger(__name__)



# --------------------------------------------------------
# Load law database (LAU) from `laws/` directory next to this file
# --------------------------------------------------------
LAWS: list[dict] = []
try:
    base_dir = Path(__file__).parent
    laws_dir = base_dir / "laws"
    if not laws_dir.exists():
        raise FileNotFoundError(f"Laws directory not found: {laws_dir}")

    for p in sorted(laws_dir.glob("*.json")):
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    LAWS.extend(data)
                elif isinstance(data, dict):
                    # If the dict contains an "articles" list, flatten it
                    if "articles" in data and isinstance(data["articles"], list):
                        for art in data["articles"]:
                            art["domain"] = data.get("domain", "unknown")
                            LAWS.append(art)
                    else:
                        # Fallback: append the object directly
                        LAWS.append(data)
                else:
                    logger.warning("Ignored %s: unexpected JSON root type %s", p, type(data).__name__)
        except Exception as e:
            logger.exception("Failed to load %s: %s", p, e)

    if not LAWS:
        logger.warning("No laws loaded from %s", laws_dir)
except Exception as e:
    logger.exception("Error initializing LAWS: %s", e)

# --------------------------------------------------------
# Register server + tool handlers
# --------------------------------------------------------

# NOTE: The low-level `Server` registers tools via `list_tools()` and handles calls
# via `call_tool()` decorator. The `Tool` model contains the JSON schemas only;
# the actual handler implementation is provided separately.

server = MCPServer(name="law-rag-mcp", version="0.1.0")


@server.list_tools()
async def _list_tools(req: types.ListToolsRequest | None = None) -> types.ListToolsResult:
    tool = Tool(
        name="law_lookup",
        description="Devuelve artículos legales relacionados con un tema dado. Ej: topic='fianza'",
        inputSchema={
            "type": "object",
            "properties": {"topic": {"type": "string"}},
            "required": ["topic"],
        },
    )

    return types.ListToolsResult(tools=[tool])


@server.call_tool()
async def law_lookup(tool_name: str, params: dict | None):
    params = params or {}
    topic = str(params.get("topic", "")).lower()

    results = []

    for entry in LAWS:
        title = str(entry.get("title", "")).lower()
        text = str(entry.get("text", "")).lower()
        keywords = [k.lower() for k in entry.get("keywords", [])]

        if (
            topic in title
            or topic in text
            or topic in keywords
        ):
            results.append(entry)

    return {
        "status": "ok",
        "query": topic,
        "results": results
    }



# --------------------------------------------------------
# Run standalone (useful for local testing)
# --------------------------------------------------------
if __name__ == "__main__":
    #print("🚀 MCP Server running on http://localhost:8000")
    #uvicorn.run(server.app, host="0.0.0.0", port=8000)

    # Local quick test: report loaded laws and run a sample query
    print(f"Loaded {len(LAWS)} law entries from: {Path(__file__).parent / 'laws'}")

    async def _test():
        res = await law_lookup("law_lookup", {"topic": "fianza"})
        print(json.dumps(res, ensure_ascii=False, indent=2))

    asyncio.run(_test())
