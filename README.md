# 🛡️ Contract Guardian - Agente MCP Legal

> **Proyecto Dual-Track para Hackathon**
> *Track 1: Creación de Servidores MCP* + *Track 2: MCP in Action (Agente)*

Contract Guardian es un auditor legal autónomo que no solo "lee" contratos, sino que **razona sobre ellos**. Utiliza el protocolo MCP para conectar un cerebro IA (Qwen en Nebius) con bases de datos legales reales, permitiendo detectar fraudes, cláusulas abusivas y errores normativos con precisión jurídica.

---

## 🎯 ¿Por qué este proyecto?

La mayoría de las IAs alucinan cuando hablan de leyes. Contract Guardian soluciona esto mediante una arquitectura **RAG Agéntica**:
1.  **No inventa leyes**: Usa una herramienta MCP (`Law Retriever`) para consultar normativas reales.
2.  **No adivina riesgos**: Usa una herramienta MCP (`Clause Classifier`) para categorizar cláusulas.
3.  **Razona**: El modelo `Qwen-32B-Thinking` orquesta estas herramientas para verificar cada afirmación del documento.

---

## 🏗️ Arquitectura (Dual Track)

Este proyecto implementa el ciclo completo de MCP:

### 🔌 Track 1: Servidores MCP (Herramientas)
Hemos creado desde cero dos servidores MCP robustos en Python (`/mcp_servers`):
*   **⚖️ Law Retriever**: Un buscador semántico que consulta bases de datos legales (ej: LAU, Estatuto de los Trabajadores).
*   **🔍 Clause Classifier**: Un clasificador especializado que identifica tipos de cláusulas (Terminación, Pagos, Privacidad) y asigna niveles de riesgo iniciales.

### 🤖 Track 2: MCP in Action (El Agente)
El cerebro del sistema (`/agent`) implementa un bucle cognitivo **ReAct (Reason + Act)**:
1.  **Percibe**: Lee el PDF del usuario.
2.  **Piensa**: *"Veo una fianza de 6 meses. ¿Es esto legal en España?"*
3.  **Actúa**: Llama a la herramienta `consultar_ley("fianza alquiler maximo")`.
4.  **Resuelve**: Cruza el dato recuperado con el contrato y emite un veredicto.

---

## 📂 Estructura del Proyecto

PROYECTOAGENTS/
├── agent/                  # 🧠 Lógica del Agente (Orquestador + Cliente LLM)
│   ├── llm_client.py       # Cliente compatible con OpenAI para Nebius
│   ├── mcp_tools.py        # Conector con los servidores MCP
│   ├── models.py           # Definición de datos
│   ├── orchestrator.py     # Cerebro ReAct del agente
│   ├── pdf_processor.py    # Extracción de texto
│   └── prompts.py          # Ingeniería de prompts
├── config/                 # ⚙️ Configuración
│   └── nebius_config.py    # Configuración de modelo y API
├── examples/               # 📂 Documentos de prueba para demos
│   ├── contrato_alquiler.pdf
│   └── factura_fraude.pdf
├── mcp_servers/            # 🔌 SERVIDORES MCP (Track 1)
│   ├── clause_classifier/  # Servidor de análisis de riesgo
│   └── law_retriever/      # Servidor de búsqueda legal (+ JSONs)
├── ui/                     # 🎨 Interfaz gráfica
│   └── agent_interface.py  # UI en Gradio con streaming
├── .env                    # Variables de entorno (API Key)
├── .gitignore              # Archivos ignorados
├── README.md               # Documentación
├── requirements.txt        # Dependencias del proyecto
└── start.py                # 🚀 Lanzador maestro (Servers + UI)



---

## 🧪 Casos de Uso (Demos Incluidas)

En la carpeta `examples/` encontrarás dos casos de prueba diseñados para demostrar la flexibilidad del agente:

### 1. `contrato_alquiler.pdf` (Verificación Estricta)
*   **Escenario**: Un contrato de alquiler con cláusulas abusivas (fianza excesiva, negación de prórroga).
*   **Comportamiento**: El agente consulta el archivo `rental_law.json` a través del servidor MCP, recupera los artículos exactos de la Ley de Arrendamientos Urbanos (LAU) y señala la ilegalidad citando la fuente.

### 2. `factura_fraude.pdf` (Inteligencia General)
*   **Escenario**: Una factura con un IVA incorrecto (25%) y límites de pago en efectivo falsos.
*   **Comportamiento**: Aunque la base de datos local no tenga leyes fiscales específicas, **el LLM demuestra su inteligencia**: detecta la incongruencia, intenta buscar, y al no encontrar el dato específico en local, utiliza su conocimiento general entrenado para alertar del fraude con alta confianza, explicando la normativa vigente.

---

## ▶️ Cómo Ejecutar

1.  **Instalar dependencias**:
    ```
    pip install -r requirements.txt
    ```

2.  **Configurar API Key**:
    Crea un archivo `.env` en la raíz y añade tu clave de Nebius:
    ```
    NEBIUS_API_KEY=tu_clave_aqui
    ```

3.  **Lanzar todo el sistema**:
    Hemos creado un script unificado que levanta los servidores MCP y la UI automáticamente:
    ```
    python start.py
    ```
    *El navegador se abrirá automáticamente en `http://localhost:7860`*

---

## 🏆 Valor Diferencial

*   **Transparencia**: El usuario ve en tiempo real qué está "pensando" el agente y qué herramientas está usando.
*   **Modularidad**: Los servidores MCP son independientes; puedes conectarles cualquier otro cliente compatible.
*   **UX Profesional**: Interfaz limpia con modo oscuro y feedback visual claro.

---