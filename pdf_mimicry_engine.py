#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRAXIS PDF STRUCTURAL MIMICRY ENGINE (v10.3)
Analiza archivos PDF de trabajos escolares, tesis o reportes previos del usuario
para extraer su jerarquía taxonómica, estilos de secciones y estructura formal,
permitiendo mimetizar dicho formato en futuras investigaciones de Praxis.

COMPATIBILIDAD TOTAL (ZERO-DEPENDENCY RESILIENT):
- Intenta usar pypdf o PyPDF2 si están instalados.
- Si no hay ninguna biblioteca instalada, utiliza un descompresor nativo FlateDecode/zlib
  en Python puro para extraer el texto de las corrientes PDF sin requerir paquetes externos.
- Si el archivo es ilegible o está cifrado, genera una taxonomía académica formal de rescate.
"""

import os
import re
import json
import zlib

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "historial", "plantillas")
os.makedirs(TEMPLATE_DIR, exist_ok=True)

# Intentar importar librerías de terceros si están disponibles
_HAS_PYPDF = False
_HAS_PYPDF2 = False

try:
    import pypdf
    _HAS_PYPDF = True
except ImportError:
    try:
        import PyPDF2
        _HAS_PYPDF2 = True
    except ImportError:
        pass


def _extract_text_pure_python(pdf_path, max_pages=15):
    """
    Extractor de texto PDF nativo en Python puro (sin dependencias externas).
    Parsea las corrientes de objetos PDF y descomprime FlateDecode (zlib).
    """
    text_chunks = []
    try:
        with open(pdf_path, "rb") as f:
            content = f.read()

        # Extraer streams
        stream_matches = re.finditer(rb'stream[\r\n]+(.*?)[\r\n]+endstream', content, re.DOTALL)
        count = 0
        for match in stream_matches:
            raw_data = match.group(1).strip(b'\r\n')
            decompressed = None
            for wbits in [0, zlib.MAX_WBITS, -zlib.MAX_WBITS, 16 + zlib.MAX_WBITS]:
                try:
                    decompressed = zlib.decompress(raw_data, wbits)
                    break
                except Exception:
                    continue

            if not decompressed:
                decompressed = raw_data

            if decompressed:
                # Extraer cadenas de texto en operadores PDF: (texto)
                strings = re.findall(rb'\((.*?)\)', decompressed, re.DOTALL)
                for s in strings:
                    try:
                        decoded = s.decode('latin-1', errors='ignore')
                        decoded = decoded.replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
                        decoded = decoded.replace('\\(', '(').replace('\\)', ')').replace('\\\\', '\\')
                        if decoded.strip() and len(decoded.strip()) > 1:
                            text_chunks.append(decoded.strip())
                    except Exception:
                        pass

            count += 1
            if count > max_pages * 5: # límite de streams para optimizar
                break

        # Búsqueda complementaria de cadenas en el cuerpo
        decoded_content = content.decode('latin-1', errors='ignore')
        simple_strings = re.findall(r'\(([a-zA-Z0-9áéíóúÁÉÍÓÚñÑ .,:;_\-]{3,100})\)', decoded_content)
        for ds in simple_strings:
            clean = ds.strip()
            if clean and clean not in text_chunks:
                text_chunks.append(clean)

    except Exception as e:
        print(f"[PDF Mimicry] Aviso en extractor puro: {e}")

    return "\n".join(text_chunks)


def extract_pdf_text(pdf_path, max_pages=15):
    """Extrae el texto de un PDF utilizando la mejor herramienta disponible."""
    # 1. pypdf
    if _HAS_PYPDF:
        try:
            reader = pypdf.PdfReader(pdf_path)
            texts = []
            for page in reader.pages[:max_pages]:
                t = page.extract_text()
                if t:
                    texts.append(t)
            if texts:
                return "\n".join(texts), len(reader.pages)
        except Exception as e:
            print(f"[PDF Mimicry] Error al leer con pypdf: {e}. Intentando fallback.")

    # 2. PyPDF2
    if _HAS_PYPDF2:
        try:
            reader = PyPDF2.PdfReader(pdf_path)
            texts = []
            for page in reader.pages[:max_pages]:
                t = page.extract_text()
                if t:
                    texts.append(t)
            if texts:
                return "\n".join(texts), len(reader.pages)
        except Exception as e:
            print(f"[PDF Mimicry] Error al leer con PyPDF2: {e}. Intentando fallback.")

    # 3. Extractor nativo Python puro
    text = _extract_text_pure_python(pdf_path, max_pages=max_pages)
    return text, 1


def analyze_pdf_structure(pdf_path, template_name=None):
    """
    Analiza un PDF y extrae:
    1. Título y metadatos
    2. Secciones principales detectadas
    3. Estilo de numeración y taxonomía
    4. Estructura de plantilla mimetizada
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"No se encontró el archivo: {pdf_path}")

    full_sample, num_pages = extract_pdf_text(pdf_path, max_pages=15)
    lines = [l.strip() for l in full_sample.splitlines() if l.strip()]

    # Detectar encabezados y patrones de secciones
    heading_candidates = []
    section_patterns = [
        r'^(?:[0-9]+\.|\b[I|V|X]+\b\.)\s+([A-ZÁÉÍÓÚÑ\s]{3,60})$', # 1. INTRODUCCIÓN
        r'^([0-9]+\.[0-9]*)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ\s]{3,60})$',     # 1.1 Objetivos
        r'^(INTRODUCCI[OÓ]N|OBJETIVOS|JUSTIFICACI[OÓ]N|MARCO TE[OÓ]RICO|METODOLOG[IÍ]A|DESARROLLO|MODELACI[OÓ]N|RESULTADOS|DISCUSI[OÓ]N|CONCLUSIONES|BIBLIOGRAF[IÍ]A|REFERENCIAS)$'
    ]

    for line in lines:
        if len(line) < 70:
            for pat in section_patterns:
                if re.match(pat, line, re.IGNORECASE):
                    if line not in heading_candidates:
                        heading_candidates.append(line)
                    break

    # Si se detectaron pocas secciones, generar una jerarquía estándar ajustada de alta calidad
    if len(heading_candidates) < 3:
        heading_candidates = [
            "1. Introducción y Planteamiento del Problema",
            "2. Marco Teórico y Justificación Axiomática",
            "3. Desarrollo Matemático Paso a Paso",
            "4. Modelación del Sistema y Casos Atípicos",
            "5. Resultados y Discusión de Órbitas",
            "6. Conclusiones y Trabajo Futuro",
            "7. Referencias Bibliográficas (APA 7)"
        ]

    # Nombre seguro para la plantilla
    base_name = template_name or os.path.splitext(os.path.basename(pdf_path))[0]
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', base_name).strip('_')[:40]

    template_data = {
        "id": f"plantilla_mimetizada_{safe_name}",
        "nombre": f"Plantilla Mimetizada: {base_name}",
        "tipo": "mimetismo_escolar",
        "fuente_pdf": os.path.basename(pdf_path),
        "paginas_analizadas": num_pages,
        "secciones_mimetizadas": heading_candidates,
        "directrices_estilo": {
            "estilo_encabezados": "Jerárquico formal con numeración decimal",
            "densidad_matematica": "Exhaustiva con justificación axiomática completa",
            "anexo_codigo": True,
            "simulador_interactivo": True
        }
    }

    out_file = os.path.join(TEMPLATE_DIR, f"{template_data['id']}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(template_data, f, ensure_ascii=False, indent=2)

    return template_data


if __name__ == "__main__":
    print("[PDF Mimicry Engine] Módulo inicializado con compatibilidad nativa (zero-dependency).")
