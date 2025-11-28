import os

# Carpetas y archivos a ignorar
IGNORE_DIRS = {'.git', '__pycache__', 'venv', 'env', '.vscode', 'node_modules', 'mcp_servers'}
IGNORE_FILES = {'.env', 'package-lock.json', 'image.jpg', '.DS_Store', 'exportar_codigo.py'}
EXTENSIONS = {'.py', '.json', '.md', '.txt', '.env.example'}

def export_project():
    output = []
    root_dir = os.getcwd()
    
    output.append("=== ESTRUCTURA DEL PROYECTO ===")
    for root, dirs, files in os.walk(root_dir):
        # Filtrar carpetas ignoradas
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        level = root.replace(root_dir, '').count(os.sep)
        indent = ' ' * 4 * (level)
        output.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if f not in IGNORE_FILES:
                output.append(f"{subindent}{f}")

    output.append("\n\n=== CONTENIDO DE LOS ARCHIVOS ===")
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if file in IGNORE_FILES: continue
            if not any(file.endswith(ext) for ext in EXTENSIONS): continue
            
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, root_dir)
            
            output.append(f"\n\n{'='*50}")
            output.append(f"ARCHIVO: {rel_path}")
            output.append(f"{'='*50}\n")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    output.append(f.read())
            except Exception as e:
                output.append(f"[Error leyendo archivo: {e}]")

    # Guardar resultado
    with open("proyecto_completo.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    
    print("✅ Listo! Se ha creado el archivo 'proyecto_completo.txt'")
    print("👉 Sube ese archivo al chat para que lo analice.")

if __name__ == "__main__":
    export_project()
