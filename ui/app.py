"""
Contract Guardian - Auditor de Contratos con IA
Interfaz Gradio que analiza contratos usando el MCP Server de law_retriever

REQUISITOS:
    pip install gradio requests python-dotenv

USO:
    python ui/app.py

Asegúrate de que law_retriever está corriendo:
    python mcp_servers/law_retriever/server.py
"""

import gradio as gr
import requests
import json
import logging
from typing import List, Dict, Tuple
from pathlib import Path

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURACIÓN
# ============================================================

LAW_RETRIEVER_URL = "http://localhost:8001/law_lookup"
LAW_RETRIEVER_HEALTH = "http://localhost:8001/health"

# Palabras clave de riesgo automáticas a buscar
RISK_KEYWORDS = {
    "alto": ["cláusula abusiva", "limitación responsabilidad", "rescisión unilateral", 
             "despido", "terminación", "renuncia derechos", "confidencialidad perpetua"],
    "medio": ["modificación términos", "suspensión servicio", "cambio condiciones",
              "arbitraje obligatorio", "jurisdicción extranjera", "penalización"],
    "bajo": ["actualización anual", "revisión precios", "prórroga automática", "notificación"]
}

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def check_law_retriever_health() -> bool:
    """Verifica si el servidor law_retriever está disponible."""
    try:
        response = requests.get(LAW_RETRIEVER_HEALTH, timeout=2)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Law retriever no disponible: {e}")
        return False


def search_law_articles(topic: str) -> Dict:
    """
    Busca artículos legales en el servidor law_retriever.
    
    Args:
        topic: Palabra clave a buscar
        
    Returns:
        Dict con resultados o error
    """
    try:
        response = requests.post(
            LAW_RETRIEVER_URL,
            json={"topic": topic.lower().strip()},
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error en law_retriever: {response.status_code}")
            return {"status": "error", "results": []}
            
    except requests.exceptions.ConnectionError:
        logger.error("No se puede conectar a law_retriever")
        return {
            "status": "error",
            "message": "❌ No se puede conectar al servidor law_retriever. ¿Está ejecutándose en localhost:8001?"
        }
    except Exception as e:
        logger.error(f"Error buscando leyes: {e}")
        return {"status": "error", "results": []}


def extract_risk_keywords(contract_text: str) -> Dict[str, List[str]]:
    """
    Extrae palabras clave de riesgo encontradas en el contrato.
    
    Args:
        contract_text: Texto del contrato
        
    Returns:
        Dict con palabras encontradas por nivel de riesgo
    """
    text_lower = contract_text.lower()
    found_risks = {"alto": [], "medio": [], "bajo": []}
    
    for risk_level, keywords in RISK_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower and keyword not in found_risks[risk_level]:
                found_risks[risk_level].append(keyword)
    
    return found_risks


def analyze_contract(contract_text: str, search_mode: str = "auto") -> Tuple[str, str]:
    """
    Analiza un contrato buscando cláusulas legales relevantes.
    
    Args:
        contract_text: Texto del contrato
        search_mode: "auto" para búsqueda automática, "manual" para términos específicos
        
    Returns:
        Tuple con HTML de resultados y resumen
    """
    
    if not contract_text or not contract_text.strip():
        return (
            "<p style='color: red;'>❌ Por favor ingresa un contrato</p>",
            "Sin datos"
        )
    
    # Verificar conexión con law_retriever
    if not check_law_retriever_health():
        return (
            "<p style='color: red;'>❌ El servidor law_retriever no está disponible.</p>"
            "<p>Inicia el servidor con: <code>python mcp_servers/law_retriever/server.py</code></p>",
            "Error de conexión"
        )
    
    # Extraer palabras clave de riesgo
    risk_keywords = extract_risk_keywords(contract_text)
    
    # Determinar términos a buscar
    search_terms = []
    
    if search_mode == "auto":
        # Buscar automáticamente por palabras clave encontradas
        for level in ["alto", "medio", "bajo"]:
            search_terms.extend(risk_keywords[level])
        
        # Si no hay palabras clave, buscar términos generales
        if not search_terms:
            search_terms = ["contrato", "términos", "condiciones", "responsabilidad"]
    else:
        # Modo manual: buscar palabras generales
        search_terms = ["contrato", "cláusula", "términos", "responsabilidad", 
                       "confidencialidad", "cancelación", "terminación"]
    
    # Buscar cada término en law_retriever
    html_output = "<div style='font-family: Arial, sans-serif;'>"
    html_output += "<h2>📋 Análisis de Contrato</h2>"
    
    # Mostrar palabras de riesgo detectadas
    if any(risk_keywords.values()):
        html_output += "<h3>⚠️ Palabras de Riesgo Detectadas:</h3>"
        
        if risk_keywords["alto"]:
            html_output += "<p style='color: red;'><b>Alto riesgo:</b> " + ", ".join(risk_keywords["alto"]) + "</p>"
        if risk_keywords["medio"]:
            html_output += "<p style='color: orange;'><b>Riesgo medio:</b> " + ", ".join(risk_keywords["medio"]) + "</p>"
        if risk_keywords["bajo"]:
            html_output += "<p style='color: green;'><b>Bajo riesgo:</b> " + ", ".join(risk_keywords["bajo"]) + "</p>"
    
    # Buscar artículos legales relevantes
    html_output += "<h3>📚 Artículos Legales Encontrados:</h3>"
    
    total_results = 0
    results_by_term = {}
    
    for term in set(search_terms):  # Evitar duplicados
        result = search_law_articles(term)
        
        if result.get("status") == "ok" and result.get("results"):
            results_by_term[term] = result["results"]
            total_results += len(result["results"])
    
    if total_results == 0:
        html_output += "<p style='color: gray;'>No se encontraron artículos legales coincidentes.</p>"
    else:
        # Mostrar resultados agrupados por término
        for term, articles in sorted(results_by_term.items()):
            html_output += f"<h4>📌 Búsqueda: <i>{term}</i></h4>"
            
            for article in articles[:3]:  # Máximo 3 por término
                domain = article.get("domain", "?")
                title = article.get("title", "Sin título")
                text = article.get("text", "")[:200]  # Primeros 200 caracteres
                source = article.get("source_law", "N/A")
                
                html_output += f"""
                <div style='border-left: 4px solid #2196F3; padding-left: 10px; margin: 10px 0;'>
                    <p><b>[{domain}] {title}</b></p>
                    <p style='color: #666;'>{text}...</p>
                    <p style='font-size: 0.85em; color: #999;'><i>Fuente: {source}</i></p>
                </div>
                """
    
    html_output += """
    <div style='margin-top: 20px; padding: 10px; background: #f0f0f0; border-radius: 5px;'>
        <p style='font-size: 0.9em; color: #666;'>
            <b>⚠️ Nota:</b> Esta herramienta es informativa. No constituye asesoría legal. 
            Consulta con un abogado para interpretación legal.
        </p>
    </div>
    </div>
    """
    
    # Generar resumen
    summary = f"Términos buscados: {len(set(search_terms))} | Artículos encontrados: {total_results}"
    if risk_keywords["alto"]:
        summary += f" | ⚠️ Alto riesgo: {len(risk_keywords['alto'])}"
    
    return html_output, summary


def quick_search_article(topic: str) -> str:
    """
    Búsqueda rápida de un artículo específico.
    
    Args:
        topic: Término a buscar
        
    Returns:
        HTML con resultados formateados
    """
    
    if not topic or not topic.strip():
        return "<p style='color: red;'>Por favor ingresa un término de búsqueda</p>"
    
    result = search_law_articles(topic)
    
    if result.get("status") != "ok" or not result.get("results"):
        return f"<p style='color: orange;'>No se encontraron resultados para '<b>{topic}</b>'</p>"
    
    html = f"<h3>Resultados para: <i>{topic}</i></h3>"
    
    for article in result.get("results", []):
        domain = article.get("domain", "?")
        title = article.get("title", "Sin título")
        text = article.get("text", "")
        keywords = article.get("keywords", [])
        notes = article.get("notes", "")
        source = article.get("source_law", "N/A")
        
        html += f"""
        <div style='border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;'>
            <h4 style='margin: 0 0 10px 0; color: #2196F3;'>[{domain}] {title}</h4>
            <p><b>Texto:</b> {text}</p>
            <p><b>Keywords:</b> {', '.join(keywords) if keywords else 'N/A'}</p>
            <p style='font-size: 0.9em; color: #666;'><b>Notas:</b> {notes}</p>
            <p style='font-size: 0.85em; color: #999;'><b>Fuente:</b> {source}</p>
        </div>
        """
    
    return html


# ============================================================
# INTERFAZ GRADIO
# ============================================================

def create_interface():
    """Crea la interfaz Gradio."""
    
    with gr.Blocks(title="Contract Guardian", theme=gr.themes.Soft()) as demo:
        
        # Header
        gr.Markdown("""
        # 🛡️ Contract Guardian - Auditor de Contratos IA
        
        Herramienta que analiza contratos y destaca cláusulas riesgosas o abusivas, 
        ayudando a entender mejor antes de firmar.
        
        **⚠️ Aviso:** Esta herramienta es informativa y no constituye asesoría legal.
        """)
        
        with gr.Tabs():
            
            # ============================================================
            # TAB 1: ANÁLISIS COMPLETO
            # ============================================================
            with gr.Tab("📊 Análisis Completo"):
                gr.Markdown("""
                ### Analiza tu contrato
                Pega el texto completo del contrato para obtener un análisis automático
                de cláusulas riesgosas y referencias legales.
                """)
                
                with gr.Row():
                    with gr.Column():
                        contract_input = gr.Textbox(
                            label="📄 Contrato (pega aquí)",
                            placeholder="Pega el texto completo del contrato...",
                            lines=15,
                            max_lines=50
                        )
                        
                        search_mode = gr.Radio(
                            choices=["auto", "manual"],
                            value="auto",
                            label="Modo de búsqueda",
                            info="Auto: busca automáticamente palabras clave de riesgo"
                        )
                        
                        analyze_btn = gr.Button(
                            "🔍 Analizar Contrato",
                            variant="primary",
                            size="lg"
                        )
                    
                    with gr.Column():
                        output_html = gr.HTML(
                            label="📋 Resultados",
                            value="<p style='color: gray;'>Los resultados aparecerán aquí...</p>"
                        )
                        summary = gr.Textbox(
                            label="📊 Resumen",
                            interactive=False
                        )
                
                analyze_btn.click(
                    fn=analyze_contract,
                    inputs=[contract_input, search_mode],
                    outputs=[output_html, summary]
                )
            
            # ============================================================
            # TAB 2: BÚSQUEDA RÁPIDA
            # ============================================================
            with gr.Tab("🔎 Búsqueda Rápida"):
                gr.Markdown("""
                ### Busca un término legal específico
                Ingresa un concepto legal para obtener artículos relevantes
                de la base de datos de leyes españolas.
                """)
                
                with gr.Row():
                    with gr.Column():
                        search_input = gr.Textbox(
                            label="Término a buscar",
                            placeholder="ej: fianza, vacaciones, despido, privacidad",
                            lines=2
                        )
                        search_btn = gr.Button(
                            "🔎 Buscar",
                            variant="primary",
                            size="lg"
                        )
                    
                    with gr.Column():
                        search_output = gr.HTML(
                            label="Artículos Encontrados",
                            value="<p style='color: gray;'>Los resultados aparecerán aquí...</p>"
                        )
                
                search_btn.click(
                    fn=quick_search_article,
                    inputs=search_input,
                    outputs=search_output
                )
            
            # ============================================================
            # TAB 3: INFORMACIÓN
            # ============================================================
            with gr.Tab("ℹ️ Información"):
                gr.Markdown("""
                ## 📚 Sobre Contract Guardian
                
                ### ¿Cómo funciona?
                1. **Análisis de Contrato**: Identifica palabras clave de riesgo
                2. **Búsqueda Legal**: Encuentra artículos relevantes en la base de datos
                3. **Referencias**: Proporciona fuentes legales españolas
                
                ### Base de Datos
                - **Derecho Laboral**: Estatuto de los Trabajadores (15 artículos)
                - **Arrendamientos**: Ley de Arrendamientos Urbanos (15 artículos)
                - **Términos de Servicio**: LSSI y Derecho del Consumidor (15 artículos)
                
                **Total: 45 artículos legales españoles reales**
                
                ### Categorías de Riesgo
                
                **🔴 RIESGO ALTO**
                - Cláusulas abusivas
                - Limitación de responsabilidad injustificada
                - Rescisión unilateral
                - Terminación sin causa
                
                **🟠 RIESGO MEDIO**
                - Modificación unilateral de términos
                - Suspensión de servicios
                - Cambio de condiciones
                - Arbitraje obligatorio
                
                **🟢 RIESGO BAJO**
                - Actualización anual de precios
                - Revisión de condiciones
                - Prórroga automática
                - Notificación requerida
                
                ### ⚠️ Importante
                - **NO es asesoría legal**: Solo información
                - **Consulta a un abogado**: Para interpretación legal real
                - **Úsalo como referencia**: Como punto de partida para revisar
                
                ### 🚀 Tecnología
                - **Backend**: FastAPI + MCP Servers
                - **Frontend**: Gradio
                - **Datos**: Leyes españolas reales del BOE
                - **Análisis**: Búsqueda semántica + keywords
                """)
    
    return demo


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🛡️  CONTRACT GUARDIAN - Auditor de Contratos")
    print("="*70 + "\n")
    
    # Verificar que law_retriever está disponible
    if not check_law_retriever_health():
        print("⚠️  ADVERTENCIA: law_retriever no está disponible")
        print("Inicia el servidor con:")
        print("  python mcp_servers/law_retriever/server.py")
        print("\nContinuando... la app intentará conectar cuando sea necesario.\n")
    else:
        print("✅ law_retriever conectado en localhost:8001\n")
    
    # Crear y lanzar interfaz
    demo = create_interface()
    
    print("🚀 Iniciando interfaz en http://localhost:7860")
    print("Presiona CTRL+C para detener\n")
    
    demo.launch(
        share=False,
        server_name="localhost",
        server_port=7860,
        show_error=True
    )