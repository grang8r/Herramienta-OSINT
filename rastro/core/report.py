"""Presentación de resultados: consola (rich), JSON y un informe HTML autónomo."""
from __future__ import annotations

import datetime as _dt
import html
import json
from pathlib import Path
from typing import List

from .model import Resultado, CONF_ALTA, CONF_MEDIA

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    _RICH = True
except Exception:  # rich es recomendable pero no imprescindible
    _RICH = False


_COLOR_CONF = {CONF_ALTA: "bold green", CONF_MEDIA: "yellow", "baja": "dim"}


def mostrar_consola(resultados: List[Resultado], titulo: str = "Resultados") -> None:
    """Imprime los resultados agrupados por fuente."""
    if not resultados:
        print("  (sin resultados)")
        return

    if not _RICH:
        _mostrar_plano(resultados)
        return

    console = Console()
    por_fuente: dict[str, List[Resultado]] = {}
    for r in resultados:
        por_fuente.setdefault(r.fuente, []).append(r)

    for fuente, items in por_fuente.items():
        tabla = Table(title=f"[bold]{fuente}[/] ({len(items)})",
                      box=box.SIMPLE_HEAVY, expand=True, title_justify="left")
        tabla.add_column("Conf.", width=6)
        tabla.add_column("Tipo", width=12)
        tabla.add_column("Hallazgo", overflow="fold")
        tabla.add_column("Enlace", overflow="fold", style="blue")
        for r in items:
            estilo = _COLOR_CONF.get(r.confianza, "dim")
            detalle = r.titulo
            if r.detalle:
                detalle += f"\n[dim]{r.detalle}[/]"
            tabla.add_row(f"[{estilo}]{r.confianza}[/]", r.tipo, detalle, r.url or "")
        console.print(tabla)


def _mostrar_plano(resultados: List[Resultado]) -> None:
    for r in resultados:
        linea = f"[{r.confianza:^5}] {r.fuente}/{r.tipo}: {r.titulo}"
        print(linea)
        if r.detalle:
            print(f"        {r.detalle}")
        if r.url:
            print(f"        -> {r.url}")


def exportar_json(resultados: List[Resultado], ruta: str, meta: dict | None = None) -> Path:
    p = Path(ruta)
    payload = {
        "generado": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "meta": meta or {},
        "total": len(resultados),
        "resultados": [r.to_dict() for r in resultados],
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def exportar_html(resultados: List[Resultado], ruta: str, meta: dict | None = None) -> Path:
    """Genera un informe HTML autónomo (sin dependencias externas)."""
    p = Path(ruta)
    meta = meta or {}
    filas = []
    for r in resultados:
        enlace = (f'<a href="{html.escape(r.url)}" target="_blank" rel="noreferrer">abrir</a>'
                  if r.url else "")
        filas.append(
            "<tr class='c-{conf}'>"
            "<td>{conf}</td><td>{fuente}</td><td>{tipo}</td>"
            "<td>{titulo}<div class='det'>{detalle}</div></td><td>{enlace}</td></tr>".format(
                conf=html.escape(r.confianza),
                fuente=html.escape(r.fuente),
                tipo=html.escape(r.tipo),
                titulo=html.escape(r.titulo),
                detalle=html.escape(r.detalle or ""),
                enlace=enlace,
            )
        )
    meta_rows = "".join(
        f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>"
        for k, v in meta.items()
    )
    doc = _PLANTILLA_HTML.format(
        generado=_dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
        total=len(resultados),
        meta_rows=meta_rows,
        filas="".join(filas) or "<tr><td colspan='5'>Sin resultados</td></tr>",
    )
    p.write_text(doc, encoding="utf-8")
    return p


_PLANTILLA_HTML = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Informe OSINT — RASTRO</title>
<style>
 :root{{--bg:#0f1419;--card:#1a212b;--fg:#e6e9ee;--mut:#8a94a3;--line:#2b3442;}}
 body{{font-family:system-ui,Segoe UI,Roboto,sans-serif;margin:0;background:var(--bg);color:var(--fg)}}
 .wrap{{max-width:1000px;margin:0 auto;padding:24px 16px}}
 h1{{font-size:20px;margin:0 0 4px}} .sub{{color:var(--mut);font-size:13px;margin-bottom:16px}}
 table{{width:100%;border-collapse:collapse;background:var(--card);border-radius:8px;overflow:hidden}}
 th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);font-size:13px;vertical-align:top}}
 thead th{{color:var(--mut);text-transform:uppercase;font-size:11px;letter-spacing:.04em}}
 .det{{color:var(--mut);font-size:12px;margin-top:2px;white-space:pre-wrap}}
 .meta{{margin:16px 0}} .meta th{{width:140px;color:var(--mut)}}
 .c-alta td:first-child{{color:#4ade80;font-weight:600}}
 .c-media td:first-child{{color:#fbbf24;font-weight:600}}
 .c-baja td:first-child{{color:var(--mut)}}
 a{{color:#60a5fa}}
 .aviso{{font-size:12px;color:var(--mut);margin-top:24px;border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<h1>Informe OSINT — RASTRO</h1>
<div class="sub">Generado: {generado} · {total} hallazgos</div>
<table class="meta"><tbody>{meta_rows}</tbody></table>
<table><thead><tr><th>Conf.</th><th>Fuente</th><th>Tipo</th><th>Hallazgo</th><th>Enlace</th></tr></thead>
<tbody>{filas}</tbody></table>
<p class="aviso">Hallazgos obtenidos de fuentes públicas y abiertas. Cada entrada es una
pista que requiere verificación humana; ninguna debe tratarse como hecho confirmado sin
contrastar. Uso previsto: localización de personas desaparecidas e investigación OSINT
autorizada.</p>
</div></body></html>"""
