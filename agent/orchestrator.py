#!/usr/bin/env python3
"""
agent/orchestrator.py
Orquestador Agente ReAct optimizado y limpio.
"""

import logging
import json
import asyncio
from typing import AsyncIterator, Dict, Any, Optional

from agent.llm_client import get_llm_client
from agent.mcp_tools import MCPToolsManager
from agent.pdf_processor import PDFProcessor
from agent.models import AnalysisResult
from agent.prompts import AGENT_SYSTEM_PROMPT, format_user_initial_msg
from config.nebius_config import NEBIUS_MODEL

logger = logging.getLogger(__name__)

class OrchestratorWithLLM:
    def __init__(self):
        self.llm_client = get_llm_client()
        self.mcp_tools = MCPToolsManager()
        self.pdf_processor = PDFProcessor()

    async def analyze_contract_streaming(self, pdf_path: str) -> AsyncIterator[Dict]:
        """Bucle principal del Agente ReAct."""
        
        # 1. LEER PDF
        yield {"status": "extracting", "message": "Leyendo documento..."}
        try:
            contract_text = self.pdf_processor.extract_text(pdf_path)
            # Limitamos contexto para eficiencia (8000 chars es bastante seguro)
            contract_preview = contract_text[:8000] 
        except Exception as e:
            yield {"status": "error", "message": f"Error leyendo PDF: {str(e)}"}
            return

        # 2. PREPARAR CONVERSACIÓN (Usando prompts centralizados)
        messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": format_user_initial_msg(contract_preview)}
        ]

        # 3. BUCLE DE AGENTE (Thinking Loop)
        MAX_TURNS = 5  # Pasos máximos de pensamiento
        
        for turn in range(MAX_TURNS):
            yield {"status": "analyzing", "message": f"Paso {turn+1}: Analizando..."}
            
            # --- LLAMADA AL LLM (STREAMING) ---
            response_full = ""
            try:
                # Usamos el cliente raw para control total del streaming
                stream = self.llm_client.client.chat.completions.create(
                    model=NEBIUS_MODEL,
                    messages=messages,
                    temperature=0.1, # Precisión alta para tools
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        response_full += content
                        yield {"status": "analyzing_chunk", "chunk": content}
            
            except Exception as e:
                logger.error(f"LLM Error: {e}")
                yield {"status": "error", "message": "Error de conexión con la IA."}
                return

            # --- DETECCIÓN DE HERRAMIENTAS ---
            tool_call = self._parse_tool_call(response_full)
            
            if tool_call:
                # El LLM quiere usar una herramienta
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args")
                
                yield {"status": "mcp_calls", "message": f"🛠️ Usando: {tool_name} ('{tool_args}')..."}
                
                # Ejecutar Tool
                tool_result_str = self._execute_tool(tool_name, tool_args, contract_text)
                
                yield {"status": "mcp_done", "message": "Datos obtenidos."}
                
                # Añadir al historial para que el LLM lo vea en la siguiente vuelta
                messages.append({"role": "assistant", "content": response_full})
                messages.append({"role": "user", "content": f"RESULTADO HERRAMIENTA ({tool_name}): {tool_result_str}"})
                
            else:
                # Si no hay tool call, asumimos respuesta final o pensamiento intermedio
                if "INFORME FINAL" in response_full.upper():
                    result_obj = self._create_result_object(response_full)
                    yield {"status": "complete", "result": result_obj}
                    break
                
                # Si no es final, seguimos el bucle añadiendo contexto
                messages.append({"role": "assistant", "content": response_full})

    def _parse_tool_call(self, text: str) -> Optional[Dict]:
        """Busca JSONs válidos en la respuesta del LLM."""
        try:
            # Buscamos patrón simple de JSON { ... }
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = text[start:end]
                data = json.loads(json_str)
                if "tool" in data:
                    return data
        except json.JSONDecodeError:
            pass
        return None

    def _execute_tool(self, name: str, args: str, full_text: str) -> str:
        """Ejecuta la herramienta solicitada."""
        try:
            if name == "consultar_ley":
                res = self.mcp_tools.law_lookup(args)
                return json.dumps(res, ensure_ascii=False)
            elif name == "clasificar_texto":
                res = self.mcp_tools.classify_clauses(full_text[:2000])
                return json.dumps(res, ensure_ascii=False)
            else:
                return f"Error: Herramienta '{name}' no existe."
        except Exception as e:
            return f"Error ejecutando herramienta: {str(e)}"

    def _create_result_object(self, analysis_text: str) -> AnalysisResult:
        """
        Parsea el texto final para llenar el objeto AnalysisResult.
        """
        reasoning = analysis_text
        recommendations = ""
        
        # Separar secciones comunes
        separators = ["Conclusión", "Recomendaciones", "Resumen"]
        for sep in separators:
            if sep in analysis_text:
                parts = analysis_text.split(sep, 1)
                reasoning = parts[0]
                recommendations = f"**{sep}**" + parts[1]
                break
        
        if not recommendations:
            recommendations = "Ver detalles en el análisis principal."

        # Contar Riesgos (Heurística)
        keywords_high = ["ilegal", "fraude", "nula", "abusiva", "grave", "infracción"]
        keywords_medium = ["incorrecto", "revisar", "duda", "riesgo"]
        
        text_lower = analysis_text.lower()
        high_risk = sum(text_lower.count(w) for w in keywords_high)
        medium_risk = sum(text_lower.count(w) for w in keywords_medium)
        
        # Ajuste de contadores
        high_risk = min(high_risk, 5)
        medium_risk = min(medium_risk, 5)
        
        return AnalysisResult(
            initial_analysis="Análisis ReAct Completo",
            llm_reasoning=reasoning,
            recommendations=recommendations,
            total_clauses=high_risk + medium_risk,
            high_risk_count=high_risk,
            medium_risk_count=medium_risk,
            low_risk_count=0
        )

# Instancia global necesaria para la UI
orchestrator = OrchestratorWithLLM()
