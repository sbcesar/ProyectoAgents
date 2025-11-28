#!/usr/bin/env python3
"""
ui/agent_interface_v2.py

Interfaz gráfica profesional con Gradio
Soporta:
- Streaming en tiempo real (pensamiento del LLM)
- Upload de PDF
- Visualización de pasos del agente
- Reporte HTML final
"""

import gradio as gr
import asyncio
import json
import logging
import sys
from pathlib import Path

# Añadir directorio raíz al path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))

from agent.orchestrator import orchestrator

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# LÓGICA DE LA INTERFAZ
# ============================================================

# En ui/agent_interface_v2.py

async def run_analysis(pdf_file):
    """
    Ejecuta el análisis del contrato conectando con el Orchestrator.
    Es un generador asíncrono para streaming de datos a la UI.
    """
    if pdf_file is None:
        yield {
            status_md: "⚠️ **Por favor, sube un archivo PDF para comenzar.**",
            live_log: "",
            html_report: "",
            json_result: None
        }
        return

    # Estado inicial
    current_log = "🚀 **Iniciando Agente MCP...**\n\n"
    
    # Variables para acumular el texto de cada sección
    section_initial = ""
    section_reasoning = ""
    section_recommendations = ""
    
    # Texto completo que se mostrará en el log
    full_display_text = ""
    
    try:
        # Iterar sobre el stream del orchestrator
        async for event in orchestrator.analyze_contract_streaming(pdf_file.name):
            status = event.get("status")
            
            # --- LOGS DE ESTADO (MENSJES CORTOS) ---
            if status in ["extracting", "analyzing", "extracting_terms", "mcp_calls", 
                          "mcp_done", "reasoning", "recommendations", "generating_report"]:
                
                icon_map = {
                    "extracting": "📄", "analyzing": "🤖", "extracting_terms": "🧠",
                    "mcp_calls": "🌍", "mcp_done": "✅", "reasoning": "⚖️",
                    "recommendations": "💡", "generating_report": "📊"
                }
                icon = icon_map.get(status, "👉")
                current_log += f"{icon} {event['message']}...\n"
                
                # Si cambiamos de fase principal, añadimos cabecera al log visual
                if status == "analyzing":
                    full_display_text += "\n=== 🤖 ANÁLISIS INICIAL DEL LLM ===\n"
                elif status == "reasoning":
                    full_display_text += "\n\n=== ⚖️ RAZONAMIENTO LEGAL (VERIFICACIÓN) ===\n"
                elif status == "recommendations":
                    full_display_text += "\n\n=== 💡 RECOMENDACIONES ===\n"
                
                yield {status_md: current_log, live_log: full_display_text}

            # --- STREAMING DE CONTENIDO (CHUNKS) ---
            
            # 1. Chunk de Análisis Inicial
            elif status == "analyzing_chunk":
                chunk = event.get("chunk", "")
                if chunk:
                    section_initial += chunk
                    full_display_text += chunk
                    yield {live_log: full_display_text}

            # 2. Chunk de Razonamiento
            elif status == "reasoning_chunk":
                chunk = event.get("chunk", "")
                if chunk:
                    section_reasoning += chunk
                    full_display_text += chunk
                    yield {live_log: full_display_text}

            # 3. Chunk de Recomendaciones
            elif status == "recommendations_chunk":
                chunk = event.get("chunk", "")
                if chunk:
                    section_recommendations += chunk
                    full_display_text += chunk
                    yield {live_log: full_display_text}

            # --- FINALIZACIÓN ---
            elif status == "complete":
                current_log += "✨ **¡Análisis Completado!**"
                result = event["result"]
                
                # Generar HTML final
                final_html = generate_html(result)
                
                # Generar JSON final
                final_json = {
                    "summary": result.initial_analysis,
                    "classification": result.mcp_classification,
                    "laws": result.mcp_laws,
                    "reasoning": result.llm_reasoning,
                    "recommendations": result.recommendations,
                    "risks": {
                        "high": result.high_risk_count,
                        "medium": result.medium_risk_count,
                        "low": result.low_risk_count
                    }
                }
                
                yield {
                    status_md: current_log,
                    live_log: full_display_text, # Asegurar que el log final esté completo
                    html_report: final_html,
                    json_result: final_json
                }

            # ERROR HANDLING
            elif status == "error":
                current_log += f"\n❌ **ERROR:** {event['message']}"
                yield {status_md: current_log}

    except Exception as e:
        logger.error(f"UI Error: {e}", exc_info=True)
        yield {status_md: f"❌ Error crítico en UI: {str(e)}"}



def generate_html(result):
    """Genera el reporte visual HTML compatible con modo oscuro."""
    return f"""
    <div style="font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; color: inherit;">
        
        <!-- HEADER -->
        <div style="background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h1 style="margin: 0; font-size: 24px;">🛡️ Contract Guardian Report</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Análisis Legal Potenciado por Agente MCP + LLM</p>
        </div>

        <!-- STATS GRID -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin-bottom: 30px;">
            <div style="background: var(--background-fill-secondary); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid var(--border-color-primary);">
                <div style="font-size: 32px; font-weight: bold; color: var(--body-text-color);">{result.total_clauses}</div>
                <div style="font-size: 14px; opacity: 0.8; text-transform: uppercase; letter-spacing: 1px; margin-top: 5px;">Riesgos Detectados</div>
            </div>
            <div style="background: rgba(220, 38, 38, 0.1); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid rgba(220, 38, 38, 0.3);">
                <div style="font-size: 32px; font-weight: bold; color: #ef4444;">{result.high_risk_count}</div>
                <div style="font-size: 14px; color: #ef4444; text-transform: uppercase; letter-spacing: 1px; margin-top: 5px;">Riesgo Alto</div>
            </div>
            <div style="background: rgba(217, 119, 6, 0.1); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid rgba(217, 119, 6, 0.3);">
                <div style="font-size: 32px; font-weight: bold; color: #f59e0b;">{result.medium_risk_count}</div>
                <div style="font-size: 14px; color: #f59e0b; text-transform: uppercase; letter-spacing: 1px; margin-top: 5px;">Riesgo Medio</div>
            </div>
            <div style="background: rgba(22, 163, 74, 0.1); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid rgba(22, 163, 74, 0.3);">
                <div style="font-size: 32px; font-weight: bold; color: #22c55e;">{result.low_risk_count}</div>
                <div style="font-size: 14px; color: #22c55e; text-transform: uppercase; letter-spacing: 1px; margin-top: 5px;">Riesgo Bajo</div>
            </div>
        </div>

        <!-- SECTIONS -->
        <!-- Usamos variables CSS de Gradio para que se adapte al tema -->
        <div style="background: var(--background-fill-primary); border-radius: 12px; overflow: hidden; border: 1px solid var(--border-color-primary); margin-bottom: 30px;">
            <div style="background: var(--background-fill-secondary); padding: 15px 25px; border-bottom: 1px solid var(--border-color-primary); font-weight: bold; color: var(--body-text-color); display: flex; align-items: center;">
                🤖 ANÁLISIS COMPLETO
            </div>
            <div style="padding: 25px; line-height: 1.6; color: var(--body-text-color);">
                {markdown_to_html(result.llm_reasoning)}
            </div>
        </div>

        <div style="background: var(--background-fill-primary); border-radius: 12px; overflow: hidden; border: 1px solid var(--border-color-primary); margin-bottom: 30px;">
            <div style="background: rgba(234, 179, 8, 0.1); padding: 15px 25px; border-bottom: 1px solid rgba(234, 179, 8, 0.3); font-weight: bold; color: #eab308; display: flex; align-items: center;">
                💡 RECOMENDACIONES / CONCLUSIÓN
            </div>
            <div style="padding: 25px; line-height: 1.6; color: var(--body-text-color);">
                {markdown_to_html(result.recommendations)}
            </div>
        </div>

        <div style="text-align: center; margin-top: 40px; opacity: 0.6; font-size: 13px;">
            Generado por Contract Guardian Agent v2.0 • No constituye asesoría legal profesional.
        </div>
    </div>
    """


def markdown_to_html(text):
    """Convierte markdown básico a HTML para visualización simple."""
    if not text: return ""
    html = text.replace("\n", "<br>")
    html = html.replace("**", "<b>").replace("**", "</b>")
    return html


# ============================================================
# INTERFAZ GRADIO
# ============================================================

with gr.Blocks(title="Contract Guardian Agent", theme=gr.themes.Soft(primary_hue="blue", secondary_hue="indigo")) as demo:
    
    # HEADER
    gr.Markdown("""
    # 🛡️ Contract Guardian - Agente MCP
    ### 🤖 Análisis de Contratos con Inteligencia Artificial + Verificación Legal
    """)
    
    with gr.Tabs():
        
        # TAB 1: ANÁLISIS PRINCIPAL
        with gr.Tab("🚀 Análisis de Contrato"):
            
            with gr.Row():
                # COLUMNA IZQUIERDA: INPUTS Y ESTADO
                with gr.Column(scale=1):
                    gr.Markdown("### 1. Sube tu contrato")
                    pdf_input = gr.File(
                        label="📄 Archivo PDF",
                        file_types=[".pdf"],
                        file_count="single",
                        type="filepath"
                    )
                    
                    analyze_btn = gr.Button(
                        "🚀 Analizar Ahora", 
                        variant="primary", 
                        size="lg"
                    )
                    
                    gr.Markdown("### 📡 Estado del Agente")
                    status_md = gr.Markdown(
                        value="Esperando archivo...",
                        elem_classes="status-box"
                    )
                
                # COLUMNA DERECHA: RESULTADOS EN VIVO
                with gr.Column(scale=2):
                    gr.Markdown("### 💭 Pensamiento del Agente (En Vivo)")
                    live_log = gr.Textbox(
                        label="Streaming del LLM", 
                        interactive=False, 
                        lines=15,
                        elem_id="live-log",
                        autoscroll=True
                    )

            # SECCIÓN DE RESULTADOS FINALES
            gr.Markdown("---")
            gr.Markdown("### 📊 Resultados del Análisis")
            
            with gr.Tabs():
                with gr.Tab("📑 Reporte Visual"):
                    html_report = gr.HTML(label="Reporte Final")
                
                with gr.Tab("💾 JSON Estructurado"):
                    json_result = gr.JSON(label="Datos Crudos")

        # TAB 2: CÓMO FUNCIONA
        with gr.Tab("ℹ️ Cómo Funciona"):
            gr.Markdown("""
            ## 🧠 Arquitectura del Agente
            
            Este sistema utiliza una arquitectura **Agentic RAG (Retrieval-Augmented Generation)** potenciada por **MCP (Model Context Protocol)**.
            
            ### El Flujo de Trabajo:
            
            1.  **📄 Ingesta**: El agente lee tu PDF y extrae el texto crudo.
            2.  **🤖 Análisis Inicial (LLM)**: Un modelo de IA (Qwen/DeepSeek) lee el contrato y detecta estructura y cláusulas clave.
            3.  **🧠 Decisión**: El agente decide qué herramientas necesita para verificar la legalidad.
            4.  **⚡ Llamadas Paralelas (MCP)**:
                *   `classify_clauses`: Clasifica técnicamente cada cláusula.
                *   `law_lookup`: Busca leyes específicas (LAU, Estatuto Trabajadores) en tiempo real.
            5.  **⚖️ Razonamiento**: El LLM cruza la información del contrato con las leyes encontradas para detectar violaciones.
            6.  **💡 Recomendación**: Genera consejos prácticos de negociación.
            
            ### Tecnologías:
            *   **Orquestador**: Python Asyncio
            *   **LLM**: Nebius API (Qwen-32B / DeepSeek-67B)
            *   **Tools**: Protocolo MCP
            *   **Frontend**: Gradio Streaming
            """)

    # EVENTOS
    analyze_btn.click(
        fn=run_analysis,
        inputs=[pdf_input],
        outputs=[status_md, live_log, html_report, json_result]
    )

# Lauch the app
if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0", 
        server_port=7860,
        share=False,
        show_error=True
    )
