"""
app.py
Lanzador para Hugging Face Spaces.
"""
import os
import sys
import subprocess
import time

# Iniciar servidores MCP en segundo plano
subprocess.Popen([sys.executable, "mcp_servers/law_retriever/laws_retriever_server.py"])
subprocess.Popen([sys.executable, "mcp_servers/clause_classifier/clause_classifier_server.py"])

# Esperar a que los servidores arranquen
time.sleep(5)

# Importar e iniciar la interfaz de Gradio
from ui.app import demo

if __name__ == "__main__":
    demo.launch()
