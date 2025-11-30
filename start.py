#!/usr/bin/env python3
"""
start.py
SCRIPT MAESTRO DE LANZAMIENTO
Ejecuta: python start.py
"""
import subprocess
import sys
import time
import signal
import os
import webbrowser

# Lista para guardar los procesos y poder cerrarlos luego
processes = []

def run_process(command, name):
    """Lanza un proceso en segundo plano"""
    print(f"🚀 Iniciando {name}...")
    # Usamos sys.executable para asegurar que usa el mismo Python del entorno virtual
    try:
        # shell=True en Windows a veces ayuda con los paths, pero subprocess directo es más seguro
        # Dividimos el comando en una lista para subprocess
        cmd_list = command.split()
        p = subprocess.Popen(cmd_list, cwd=os.getcwd())
        processes.append(p)
        return p
    except Exception as e:
        print(f"❌ Error al iniciar {name}: {e}")
        return None

def cleanup(signum, frame):
    """Cierra todo al pulsar Ctrl+C"""
    print("\n🛑 Cerrando todos los servidores...")
    for p in processes:
        try:
            p.terminate()
        except:
            pass
    sys.exit(0)

# Capturar Ctrl+C
signal.signal(signal.SIGINT, cleanup)

def main():
    print("\n🛡️  CONTRACT GUARDIAN - PREPARANDO DEMO 🛡️")
    print("============================================")

    # 1. INICIAR SERVIDORES MCP
    # Ajusta estas rutas si cambiaste nombres, pero según tu foto son estas:
    
    # Servidor de Leyes (Puerto 8001)
    run_process(f"{sys.executable} mcp_servers/law_retriever/laws_retriever_server.py", "Law Retriever (Port 8001)")
    
    # Servidor de Clasificación (Puerto 8002)
    run_process(f"{sys.executable} mcp_servers/clause_classifier/clause_classifier_server.py", "Clause Classifier (Port 8002)")

    print("⏳ Esperando 5 segundos a que los servidores arranquen...")
    time.sleep(5)

    # 2. INICIAR INTERFAZ DE USUARIO
    print("🎨 Iniciando Interfaz Gradio...")
    ui_process = run_process(f"{sys.executable} ui/app.py", "User Interface")

    # 3. ABRIR NAVEGADOR
    print("🌍 Abriendo navegador...")
    time.sleep(2)
    webbrowser.open("http://localhost:7860")

    print("\n✅ TODO LISTO. Presiona Ctrl+C para detener todo.\n")
    
    # Mantener el script vivo mientras la UI funcione
    if ui_process:
        ui_process.wait()
    
    cleanup(None, None)

if __name__ == "__main__":
    main()
