#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CONVERSOR CLI Y LIBRERIA PRAXIS v10.0: MARKDOWN -> MICROSOFT WORD (.docx y .doc)
- Soporte dual para .docx: Pandoc (con OMML nativo) + motor fallback nativo python-docx con OMML 2D
- Soporte para bloques de código (```html, ```python, etc.) con formato de código fuente en Word
- Soporte para Word .doc: Formato HTML enriquecido con MathML nativo editable en Word
- Sanitización estricta de caracteres de control XML para estabilidad 100%
"""

import sys
import os
import glob
import subprocess
import shutil
import re
import html

def sanitize_xml(s):
    """Elimina caracteres de control no compatibles con el estándar XML de Word"""
    if not s: return ""
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', str(s))

def find_pandoc():
    p = shutil.which("pandoc")
    if p: return p
    candidates = [
        r"C:\Program Files\Pandoc\pandoc.exe",
        r"C:\Program Files (x86)\Pandoc\pandoc.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Pandoc\pandoc.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Pandoc\pandoc.exe"),
        os.path.expandvars(r"%USERPROFILE%\scoop\shims\pandoc.exe"),
        os.path.expandvars(r"%ProgramData%\chocolatey\bin\pandoc.exe")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def latex_to_omml(tex, is_block=False):
    tex = sanitize_xml(tex).strip()
    
    def parse_inner(t):
        t = t.strip()
        if not t: return ""

        # Matrices
        if r"\begin{pmatrix}" in t or r"\begin{bmatrix}" in t or r"\begin{matrix}" in t:
            m = re.search(r'\\begin\{(?:pmatrix|bmatrix|matrix)\}(.*?)\\end\{(?:pmatrix|bmatrix|matrix)\}', t, re.DOTALL)
            if m:
                rows = m.group(1).strip().split(r"\\")
                xml_rows = ""
                for r in rows:
                    cols = r.split("&")
                    xml_cols = "".join(["<m:e>" + parse_inner(c.strip()) + "</m:e>" for c in cols if c.strip()])
                    xml_rows += "<m:mr>" + xml_cols + "</m:mr>"
                mat_xml = "<m:m><m:mPr><m:baseJc m:val='center'/></m:mPr>" + xml_rows + "</m:m>"
                return "<m:d><m:dPr><m:begChr m:val='('/><m:endChr m:val=')'/></m:dPr><m:e>" + mat_xml + "</m:e></m:d>"

        # Fracciones
        frac_m = re.search(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', t)
        if frac_m:
            num = parse_inner(frac_m.group(1))
            den = parse_inner(frac_m.group(2))
            return "<m:f><m:num>" + num + "</m:num><m:den>" + den + "</m:den></m:f>"

        # Raiz
        sqrt_m = re.search(r'\\sqrt\{([^{}]+)\}', t)
        if sqrt_m:
            content = parse_inner(sqrt_m.group(1))
            return "<m:rad><m:radPr><m:degHide m:val='on'/></m:radPr><m:deg/><m:e>" + content + "</m:e></m:rad>"

        # Sub y Sup
        subsup_m = re.search(r'([a-zA-Z0-9\(\)]+)_([a-zA-Z0-9]+)\^([a-zA-Z0-9]+)', t)
        if subsup_m:
            return "<m:sSubSup><m:e><m:r><m:t>" + subsup_m.group(1) + "</m:t></m:r></m:e><m:sub><m:r><m:t>" + subsup_m.group(2) + "</m:t></m:r></m:sub><m:sup><m:r><m:t>" + subsup_m.group(3) + "</m:t></m:r></m:sup></m:sSubSup>"

        # Sup solo
        sup_m = re.search(r'([a-zA-Z0-9\(\)]+)\^\{?([a-zA-Z0-9\+\-]+)\}?', t)
        if sup_m:
            return "<m:sSup><m:e><m:r><m:t>" + sup_m.group(1) + "</m:t></m:r></m:e><m:sup><m:r><m:t>" + sup_m.group(2) + "</m:t></m:r></m:sup></m:sSup>"

        # Sub solo
        sub_m = re.search(r'([a-zA-Z0-9\(\)]+)_\{?([a-zA-Z0-9\+\-]+)\}?', t)
        if sub_m:
            return "<m:sSub><m:e><m:r><m:t>" + sub_m.group(1) + "</m:t></m:r></m:e><m:sub><m:r><m:t>" + sub_m.group(2) + "</m:t></m:r></m:sub></m:sSub>"

        safe = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return "<m:r><m:t>" + safe + "</m:t></m:r>"

    elem = parse_inner(tex)
    if is_block:
        return "<m:oMathPara xmlns:m=\"http://schemas.openxmlformats.org/officeDocument/2006/math\"><m:oMath>" + elem + "</m:oMath></m:oMathPara>"
    return "<m:oMath xmlns:m=\"http://schemas.openxmlformats.org/officeDocument/2006/math\">" + elem + "</m:oMath>"

def convert_with_pandoc(input_md, output_docx):
    p = find_pandoc()
    if not p: return False, "Pandoc no disponible en el sistema."
    try:
        res = subprocess.run([p, "-s", input_md, "-o", output_docx], capture_output=True, text=True, timeout=30)
        if res.returncode == 0 and os.path.exists(output_docx):
            return True, "Conversión con Pandoc completada exitosamente."
        return False, res.stderr or "Error en compilación Pandoc"
    except Exception as e:
        return False, str(e)

def convert_with_python_docx(input_md, output_docx):
    try:
        import docx
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import parse_xml
    except ImportError:
        return False, "python-docx no disponible."
    try:
        with open(input_md, "r", encoding="utf-8") as f:
            content = f.read()
        doc = docx.Document()
        for sec in doc.sections:
            sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Inches(1)
            fp = sec.footer.paragraphs[0]
            fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            r = fp.add_run("Praxis V10 · Laboratorio Matemático Avanzado")
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(140, 150, 160)

        lines = content.splitlines()
        in_eq_block = False
        in_code_block = False
        block_lines = []

        for line in lines:
            s = line.strip()

            # Bloques de código (```html, ```python, etc.)
            if s.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(1.5)
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.left_indent = Inches(0.2)
                r = p.add_run(sanitize_xml(line))
                r.font.name = "Consolas"
                r.font.size = Pt(8.5)
                r.font.color.rgb = RGBColor(30, 41, 59)
                continue

            # Bloques de ecuación $$ ... $$
            if s.startswith("$$") and s.endswith("$$") and len(s) > 4:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                try: p._p.append(parse_xml(latex_to_omml(s[2:-2], is_block=True)))
                except: p.add_run(sanitize_xml(s))
                continue
            elif s == "$$":
                if in_eq_block:
                    in_eq_block = False
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    try: p._p.append(parse_xml(latex_to_omml(" ".join(block_lines), is_block=True)))
                    except: p.add_run(sanitize_xml(" ".join(block_lines)))
                    block_lines = []
                else:
                    in_eq_block = True
                    block_lines = []
                continue
            elif in_eq_block:
                block_lines.append(s)
                continue

            if not s: continue

            # Encabezados
            if s.startswith("# "):
                h = doc.add_heading(sanitize_xml(s[2:]), level=1)
                h.paragraph_format.space_before = Pt(18)
                h.paragraph_format.space_after = Pt(8)
                for r in h.runs:
                    r.font.name = "Georgia"
                    r.font.size = Pt(20)
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(26, 115, 232)
            elif s.startswith("## "):
                h = doc.add_heading(sanitize_xml(s[3:]), level=2)
                h.paragraph_format.space_before = Pt(14)
                h.paragraph_format.space_after = Pt(6)
                for r in h.runs:
                    r.font.name = "Georgia"
                    r.font.size = Pt(15)
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(217, 48, 37)
            elif s.startswith("### "):
                h = doc.add_heading(sanitize_xml(s[4:]), level=3)
                h.paragraph_format.space_before = Pt(10)
                h.paragraph_format.space_after = Pt(4)
                for r in h.runs:
                    r.font.name = "Georgia"
                    r.font.size = Pt(13)
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(23, 29, 41)
            elif s.startswith("#### "):
                h = doc.add_heading(sanitize_xml(s[5:]), level=4)
                h.paragraph_format.space_before = Pt(8)
                h.paragraph_format.space_after = Pt(3)
                for r in h.runs:
                    r.font.name = "Georgia"
                    r.font.size = Pt(11)
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(70, 80, 95)
            elif s == "---":
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run("――――――――――――――――――――――――――――――――――――――")
                r.font.color.rgb = RGBColor(200, 205, 215)
            elif s.startswith("> "):
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.3)
                p.paragraph_format.line_spacing = 1.2
                p.paragraph_format.space_after = Pt(4)
                r = p.add_run(sanitize_xml(s[2:]))
                r.font.color.rgb = RGBColor(40, 50, 60)
            else:
                is_bullet = s.startswith("* ") or s.startswith("- ")
                raw_text = s[2:] if is_bullet else s
                p = doc.add_paragraph(style="List Bullet" if is_bullet else "Normal")
                p.paragraph_format.line_spacing = 1.25
                p.paragraph_format.space_after = Pt(4)
                parts = re.split(r'(\$[^$]+?\$)', raw_text)
                for part in parts:
                    if not part: continue
                    if part.startswith("$") and part.endswith("$") and len(part) >= 2:
                        try: p._p.append(parse_xml(latex_to_omml(part[1:-1], is_block=False)))
                        except: p.add_run(sanitize_xml(part))
                    else:
                        subparts = re.split(r'(\*\*.*?\*\*|\*.*?\*)', part)
                        for sp in subparts:
                            if not sp: continue
                            if sp.startswith("**") and sp.endswith("**") and len(sp) >= 4:
                                r = p.add_run(sanitize_xml(sp[2:-2]))
                                r.bold = True
                            elif sp.startswith("*") and sp.endswith("*") and len(sp) >= 2:
                                r = p.add_run(sanitize_xml(sp[1:-1]))
                                r.italic = True
                            else:
                                p.add_run(sanitize_xml(sp))
        doc.save(output_docx)
        return True, "Conversión con python-docx completada exitosamente."
    except Exception as e:
        return False, str(e)

def convert_markdown_to_doc(input_md, output_doc, title="Informe Matemático"):
    try:
        with open(input_md, "r", encoding="utf-8") as f:
            md = f.read()
        html_body = []
        lines = md.splitlines()
        in_eq_block = False
        in_code_block = False
        block_lines = []

        for line in lines:
            s = line.strip()

            if s.startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                safe_l = html.escape(line)
                html_body.append(f'<div style="font-family:Consolas,monospace;font-size:8.5pt;color:#1e293b;background:#f8fafc;padding:1pt 6pt;white-space:pre;">{safe_l}</div>')
                continue

            if s.startswith("$$") and s.endswith("$$") and len(s) > 4:
                eq = s[2:-2].strip()
                html_body.append("<div style='text-align:center;margin:14pt 0;'><math xmlns='http://www.w3.org/1998/Math/MathML' display='block'><mrow><mi>" + eq + "</mi></mrow></math></div>")
                continue
            elif s == "$$":
                if in_eq_block:
                    in_eq_block = False
                    eq = " ".join(block_lines).strip()
                    html_body.append("<div style='text-align:center;margin:14pt 0;'><math xmlns='http://www.w3.org/1998/Math/MathML' display='block'><mrow><mi>" + eq + "</mi></mrow></math></div>")
                    block_lines = []
                else:
                    in_eq_block = True
                    block_lines = []
                continue
            elif in_eq_block:
                block_lines.append(s)
                continue

            if not s:
                html_body.append("<br/>")
                continue

            if s.startswith("# "):
                html_body.append("<h1 style='font-family:Georgia,serif;font-size:20pt;color:#1a73e8;margin-top:18pt;margin-bottom:8pt;'>" + s[2:] + "</h1>")
            elif s.startswith("## "):
                html_body.append("<h2 style='font-family:Georgia,serif;font-size:15pt;color:#d93025;margin-top:14pt;margin-bottom:6pt;border-bottom:1px solid #cbd5e1;padding-bottom:3pt;'>" + s[3:] + "</h2>")
            elif s.startswith("### "):
                html_body.append("<h3 style='font-family:Georgia,serif;font-size:12.5pt;color:#171d29;margin-top:10pt;margin-bottom:4pt;'>" + s[4:] + "</h3>")
            elif s.startswith("#### "):
                html_body.append("<h4 style='font-family:Georgia,serif;font-size:11pt;color:#475569;margin-top:8pt;margin-bottom:3pt;'>" + s[5:] + "</h4>")
            elif s == "---":
                html_body.append("<hr style='border:none;border-top:1px solid #cbd5e1;margin:14pt 0;' />")
            elif s.startswith("> "):
                html_body.append("<div style='background:#f8fafc;border-left:4px solid #1a73e8;padding:8pt 12pt;margin:8pt 0;font-size:10.5pt;color:#1e293b;'>" + s[2:] + "</div>")
            elif s.startswith("* ") or s.startswith("- "):
                html_body.append("<li style='margin-left:18pt;margin-bottom:3pt;'>" + s[2:] + "</li>")
            else:
                formatted = re.sub(r'\$([^$]+?)\$', r"<math xmlns='http://www.w3.org/1998/Math/MathML'><mrow><mi>\1</mi></mrow></math>", s)
                formatted = re.sub(r'\*\*(.*?)\*\*', r"<b>\1</b>", formatted)
                formatted = re.sub(r'\*(.*?)\*', r"<i>\1</i>", formatted)
                html_body.append("<p style='margin:0 0 6pt 0;line-height:1.4;'>" + formatted + "</p>")

        body_str = "\n".join(html_body)
        doc_html = "<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns:m='http://schemas.openxmlformats.org/officeDocument/2006/math' xmlns='http://www.w3.org/TR/REC-html40'><head><meta charset='utf-8'><title>" + title + "</title><!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View><w:Zoom>100</w:Zoom><w:DoNotOptimizeForBrowser/></w:WordDocument></xml><![endif]--><style>@page { size: 21.59cm 27.94cm; margin: 2.54cm; } body { font-family: Calibri, sans-serif; font-size: 11pt; line-height: 1.35; color: #171d29; } h1, h2, h3, h4 { font-family: Georgia, serif; }</style></head><body>" + body_str + "</body></html>"
        with open(output_doc, "w", encoding="utf-8") as f:
            f.write(doc_html)
        return True, "Archivo Word .doc generado exitosamente."
    except Exception as e:
        return False, str(e)

def convert_file_to_both_words(input_md, docx_path, doc_path, title=None):
    t = title or os.path.splitext(os.path.basename(input_md))[0].replace("_", " ")
    p_ok, p_msg = convert_with_pandoc(input_md, docx_path)
    if not p_ok:
        convert_with_python_docx(input_md, docx_path)
    convert_markdown_to_doc(input_md, doc_path, title=t)
    return {
        "docx": os.path.exists(docx_path),
        "doc": os.path.exists(doc_path)
    }

def main():
    args = sys.argv[1:]
    target_files = args if args else [f for f in glob.glob("*.md") if not f.lower().startswith("readme")]
    if not target_files:
        print("No se encontraron archivos .md para convertir.")
        return
    for md in target_files:
        base, _ = os.path.splitext(md)
        docx = base + ".docx"
        doc = base + ".doc"
        print("Procesando: " + md)
        res = convert_file_to_both_words(md, docx, doc)
        print("  • DOCX: " + str(res["docx"]) + " | DOC: " + str(res["doc"]))

if __name__ == "__main__":
    main()
