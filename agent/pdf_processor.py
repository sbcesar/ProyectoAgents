#!/usr/bin/env python3
"""
agent/pdf_processor.py
Procesador robusto de PDF usando pypdf.
"""
import logging
from pathlib import Path
import pypdf

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        pass
    
    def extract_text(self, pdf_path: str) -> str:
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"No se encuentra el PDF: {pdf_path}")
            
        try:
            logger.info(f"📄 Extrayendo texto de: {path.name}")
            text = []
            with open(path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)
                        
            full_text = "\n".join(text)
            if len(full_text) < 50:
                raise ValueError("El PDF parece ser una imagen o estar vacío.")
                
            return full_text
            
        except Exception as e:
            logger.error(f"Error leyendo PDF: {e}")
            raise e

if __name__ == "__main__":
    print("✅ PDF Processor cargado")
