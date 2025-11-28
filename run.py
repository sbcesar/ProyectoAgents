#!/usr/bin/env python3
"""
run.py
Punto de entrada principal para Contract Guardian.
Maneja los imports correctamente.
"""
import os
import sys
from pathlib import Path

# Añadir el directorio raíz al path de Python
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

# Importar y lanzar la interfaz
try:
    from ui.app import demo
    print("🚀 Iniciando Contract Guardian Agent...")
    print("👉 Abre tu navegador en: http://127.0.0.1:7860")
    demo.queue().launch(server_name="0.0.0.0", server_port=7860, share=False)
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("Asegúrate de estar ejecutando desde la raíz del proyecto: python run.py")
except Exception as e:
    print(f"❌ Error inesperado: {e}")
