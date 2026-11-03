"""Informe final en PDF con grafo de correlación (reportlab)."""
from __future__ import annotations

import datetime as _dt
import html as _html
from pathlib import Path
from typing import List, Optional

from .model import Resultado

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, Image, HRFlowable)
    _OK = True
except Exception:
    _OK = False

_AZUL = "#1f2a44"
_GRIS = "#5a6472"
_CONF_COLOR = {"alta": "#15803d", "media": "#b45309", "baja": "#64748b"}


def exportar_pdf(resultados: List[Resultado], ruta: str, *, meta: Optional[dict] = None,
                 grafo_png: Optional[str] = None, correlaciones: Optional[list] = None,
                 resumen: Optional[dict] = None) -> Optional[Path]:
    if not _OK:
        return None
    meta = meta or {}
    correlaciones = correlaciones or []
    resumen = resumen or {}
    p = Path(ruta)

    estilos = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=estilos["Heading1"], textColor=colors.HexColor(_AZUL),
                        fontSize=18, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=estilos["Heading2"], textColor=colors.HexColor(_AZUL),
                        fontSize=13, spaceBefore=14, spaceAfter=6)
    sub = ParagraphStyle("sub", parent=estilos["Normal"], textColor=colors.HexColor(_GRIS),
                         fontSize=9)
    cell = ParagraphStyle("cell", parent=estilos["Normal"], fontSize=8, leading=10)
    cell_link = ParagraphStyle("cl", parent=cell, textColor=colors.HexColor("#1d4ed8"))
    nota = ParagraphStyle("nota", parent=estilos["Normal"], fontSize=8,
                          textColor=colors.HexColor(_GRIS))

    doc = SimpleDocTemplate(str(p), pagesize=A4, topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            title="Informe OSINT — RASTRO")
    flow = []

    flow.append(Paragraph("Informe OSINT — RASTRO", h1))
    generado = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    flow.append(Paragraph(f"Generado: {generado}", sub))
    flow.append(Spacer(1, 6))
    flow.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#c9cdd6")))
    flow.append(Spacer(1, 8))

    # Metadatos
    if meta:
        filas = [[Paragraph(f"<b>{_esc(k)}</b>", cell), Paragraph(_esc(str(v)), cell)]
                 for k, v in meta.items()]
        t = Table(filas, colWidths=[4 * cm, 12.6 * cm])
        t.setStyle(TableStyle([
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        flow.append(t)

    # Resumen
    if resumen:
        flow.append(Paragraph("Resumen", h2))
        por_tipo = ", ".join(f"{k}: {v}" for k, v in (resumen.get("por_tipo") or {}).items())
        flow.append(Paragraph(
            f"{len(resultados)} hallazgos · {resumen.get('nodos', 0)} nodos / "
            f"{resumen.get('aristas', 0)} relaciones en el grafo. {por_tipo}", cell))

    # Correlaciones destacadas
    flow.append(Paragraph("Correlaciones destacadas", h2))
    if correlaciones:
        flow.append(Paragraph(
            "Datos corroborados por dos o más fuentes distintas (la señal más fiable):", sub))
        filas = [[Paragraph("<b>Tipo</b>", cell), Paragraph("<b>Valor</b>", cell),
                  Paragraph("<b>Fuentes</b>", cell)]]
        for c in correlaciones:
            filas.append([Paragraph(_esc(c["tipo"]), cell), Paragraph(_esc(c["valor"]), cell),
                          Paragraph(_esc(", ".join(c["fuentes"])), cell)])
        t = Table(filas, colWidths=[2.6 * cm, 8 * cm, 6 * cm], repeatRows=1)
        t.setStyle(_estilo_tabla())
        flow.append(t)
    else:
        flow.append(Paragraph("No se detectaron datos corroborados por varias fuentes "
                              "en esta ejecución.", cell))

    # Grafo
    if grafo_png and Path(grafo_png).is_file():
        flow.append(Paragraph("Grafo de información", h2))
        img = _imagen_ajustada(grafo_png, max_ancho=16.4 * cm, max_alto=11 * cm)
        if img:
            flow.append(img)

    # Hallazgos
    flow.append(Paragraph("Hallazgos", h2))
    filas = [[Paragraph("<b>Conf.</b>", cell), Paragraph("<b>Fuente</b>", cell),
              Paragraph("<b>Tipo</b>", cell), Paragraph("<b>Hallazgo</b>", cell),
              Paragraph("<b>Enlace</b>", cell)]]
    for r in resultados:
        color = _CONF_COLOR.get(r.confianza, "#64748b")
        conf = Paragraph(f"<font color='{color}'><b>{_esc(r.confianza)}</b></font>", cell)
        hall = _esc(r.titulo)
        if r.detalle:
            hall += f"<br/><font color='{_GRIS}'>{_esc(r.detalle)}</font>"
        enlace = (Paragraph(f"<a href='{_esc(r.url)}'>abrir</a>", cell_link)
                  if r.url else Paragraph("", cell))
        filas.append([conf, Paragraph(_esc(r.fuente), cell), Paragraph(_esc(r.tipo), cell),
                      Paragraph(hall, cell), enlace])
    t = Table(filas, colWidths=[1.5 * cm, 2.2 * cm, 2.3 * cm, 8.6 * cm, 1.8 * cm], repeatRows=1)
    t.setStyle(_estilo_tabla())
    flow.append(t)

    flow.append(Spacer(1, 10))
    flow.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#c9cdd6")))
    flow.append(Paragraph(
        "Hallazgos obtenidos de fuentes públicas y abiertas. Cada entrada es una pista que "
        "requiere verificación humana; ninguna debe tratarse como hecho confirmado sin "
        "contrastar. Uso previsto: localización de personas desaparecidas e investigación "
        "OSINT autorizada.", nota))

    doc.build(flow)
    return p


def _estilo_tabla():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef1f6")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7dbe3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ])


def _imagen_ajustada(ruta: str, max_ancho: float, max_alto: float):
    try:
        from reportlab.lib.utils import ImageReader
        iw, ih = ImageReader(ruta).getSize()
        escala = min(max_ancho / iw, max_alto / ih)
        return Image(ruta, width=iw * escala, height=ih * escala)
    except Exception:
        return None


def _esc(s: str) -> str:
    return _html.escape(str(s or ""))
