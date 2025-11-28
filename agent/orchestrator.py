#!/usr/bin/env python3
"""
agent/orchestrator_with_llm.py
ESTRATEGIA: AGENTE REACT (Reason + Act)
El LLM recibe el texto y DECIDE si llamar herramientas o responder.
"""

import logging
import json
import asyncio
from typing import AsyncIterator, Dict, Any

from agent.llm_client import get_llm_client
from agent.mcp_tools import MCPToolsManager
from agent.pdf_processor import PDFProcessor
from config.nebius_config import NEBIUS_MODEL

logger = logging.getLogger(__name__)

class OrchestratorWithLLM:
    def __init__(self):
        self.llm_client = get_llm_client()
        self.mcp_tools = MCPToolsManager()
        self.pdf_processor = PDFProcessor()

    async def analyze_contract_streaming(self, pdf_path: str) -> AsyncIterator[Dict]:
        """
        Bucle principal del Agente.
        1. Lee PDF
        2. Piensa (LLM)
        3. Si el LLM pide herramienta -> Ejecuta y vuelve a pensar.
        4. Si el LLM da respuesta final -> Termina.
        """
        
        # 1. LEER PDF
        yield {"status": "extracting", "message": "Leyendo documento..."}
        contract_text = self.pdf_processor.extract_text(pdf_path)
        contract_preview = contract_text[:3000] # Limitamos para no saturar contexto rápido

        # DEFINICIÓN DE HERRAMIENTAS PARA EL LLM (SISTEMA PROMPT)
        system_prompt = """Eres Contract Guardian, un auditor experto IA.
        
TIENES DISPONIBLES ESTAS HERRAMIENTAS EXTERNAS (MCP):
1. `consultar_ley(tema)`: Busca leyes oficiales españolas. Úsala ante dudas legales.
2. `clasificar_texto(texto)`: Detecta si un texto es abusivo/riesgoso.

TU PROCESO DE PENSAMIENTO:
1. Analiza el texto del usuario.
2. Si detectas posibles infracciones o dudas, DEBES usar las herramientas.
3. Para usar una herramienta, responde SOLO con este formato JSON:
   {"tool": "consultar_ley", "args": "fianza alquiler maximo"}
   
4. Si ya tienes la información, responde con tu análisis final empezando con "INFORME FINAL:".
"""

        # HISTORIAL DE CONVERSACIÓN
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analiza este documento y detecta infracciones:\n\n{contract_preview}..."}
        ]

        # BUCLE DE AGENTE (MÁXIMO 3 VUELTAS PARA NO ENTRAR EN LOOP INFINITO)
        for turn in range(3):
            
            # --- PENSAMIENTO DEL LLM ---
            yield {"status": "analyzing", "message": f"El Agente está pensando (Paso {turn+1})..."}
            
            # Llamada al LLM (No streaming aquí para poder procesar JSON)
            response_full = ""
            try:
                # Usamos el cliente raw de openai para tener control total aquí
                stream = self.llm_client.client.chat.completions.create(
                    model=NEBIUS_MODEL,
                    messages=messages,
                    temperature=0.1, # Precisión para tools
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        response_full += content
                        # Mostrar pensamiento en vivo
                        yield {"status": "analyzing_chunk", "chunk": content}
            
            except Exception as e:
                yield {"status": "error", "message": str(e)}
                return

            # --- DECISIÓN: ¿USAR HERRAMIENTA O TERMINAR? ---
            
            # Intentamos detectar si quiere usar una tool (buscamos JSON)
            tool_call = self._parse_tool_call(response_full)
            
            if tool_call:
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args")
                
                yield {"status": "mcp_calls", "message": f"🛠️ Ejecutando herramienta: {tool_name}..."}
                
                # EJECUTAR HERRAMIENTA MCP
                tool_result = ""
                if tool_name == "consultar_ley":
                    res = self.mcp_tools.law_lookup(tool_args)
                    tool_result = json.dumps(res, ensure_ascii=False)
                elif tool_name == "clasificar_texto":
                    res = self.mcp_tools.classify_clauses(contract_text[:1000]) # Muestra
                    tool_result = json.dumps(res, ensure_ascii=False)
                
                yield {"status": "mcp_done", "message": "Datos obtenidos."}
                
                # AÑADIR RESULTADO AL CONTEXTO Y SEGUIR
                messages.append({"role": "assistant", "content": response_full})
                messages.append({"role": "user", "content": f"RESULTADO DE HERRAMIENTA ({tool_name}): {tool_result}. Continúa tu análisis."})
                
            else:
                # Si no pide herramienta, asumimos que es la respuesta final
                yield {
                    "status": "complete", 
                    "result": self._create_dummy_result(contract_text, response_full)
                }
                break

    def _parse_tool_call(self, text):
        """Intenta encontrar un JSON de llamada a herramienta en el texto del LLM."""
        try:
            # Buscamos el primer { y el último }
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = text[start:end]
                return json.loads(json_str)
        except:
            return None
        return None

    def _create_dummy_result(self, text, analysis):
        """
        Crea un resultado estructurado analizando el texto generado por el LLM.
        Intenta separar el informe en secciones lógicas para la UI.
        """
        # 1. Intentar separar Recomendaciones
        recommendations = ""
        reasoning = analysis
        initial = "Análisis realizado mediante Agente ReAct con herramientas MCP."
        
        if "Recomendación" in analysis or "Conclusión" in analysis:
            # Buscamos dónde empieza la conclusión/recomendación
            parts = analysis.split("Conclusión")
            if len(parts) > 1:
                reasoning = parts[0]
                recommendations = "Conclusión" + parts[1]
            else:
                parts = analysis.split("Recomendaciones")
                if len(parts) > 1:
                    reasoning = parts[0]
                    recommendations = "Recomendaciones" + parts[1]

        # 2. Contar infracciones para los contadores (Heurística simple)
        # Contamos palabras clave como "Infracción", "Incorrecto", "Abusiva"
        keywords_high = ["ilegal", "fraude", "infracción", "abusiva", "grave"]
        keywords_medium = ["incorrecto", "error", "revisar"]
        
        analysis_lower = analysis.lower()
        high_risk = sum(analysis_lower.count(w) for w in keywords_high)
        medium_risk = sum(analysis_lower.count(w) for w in keywords_medium)
        
        # Ajuste para no contar demasiado (un texto puede repetir la misma palabra)
        high_risk = min(high_risk, 5) 
        medium_risk = min(medium_risk, 5)
        total_clauses = high_risk + medium_risk

        from dataclasses import dataclass
        @dataclass
        class Result:
            initial_analysis: str
            mcp_classification: dict
            mcp_laws: dict
            llm_reasoning: str
            recommendations: str
            total_clauses: int
            high_risk_count: int
            medium_risk_count: int
            low_risk_count: int

        return Result(
            initial_analysis=initial,
            mcp_classification={}, # No usado en modo ReAct
            mcp_laws={},           # No usado en modo ReAct
            llm_reasoning=reasoning,     # Aquí va el cuerpo del análisis
            recommendations=recommendations if recommendations else "Ver detalles en el razonamiento.",
            total_clauses=total_clauses,
            high_risk_count=high_risk,
            medium_risk_count=medium_risk,
            low_risk_count=0
        )


orchestrator = OrchestratorWithLLM()
