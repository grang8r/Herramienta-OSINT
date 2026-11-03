"""Investigación unificada: orquesta los colectores y construye el grafo.

Una Investigacion reúne todos los datos de partida que el analista tenga (nombre,
teléfono, email, alias, foto), ejecuta los colectores pertinentes, acumula los
resultados y los vuelca en un grafo de correlación. Luego exporta a consola,
JSON, HTML, PNG (grafo) y PDF.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Optional

from . import report
from .graph import Grafo
from .model import Resultado
from ..collectors.interpol import InterpolColector
from ..collectors.news import NoticiasColector
from ..collectors.username import UsernameColector
from ..collectors.phone import PhoneColector
from ..collectors.email import EmailColector
from ..collectors.exif import ExifColector
from ..collectors.pivots import PivotesColector
from ..collectors.web import WebColector


class Investigacion:
    def __init__(self, *, nombre_completo: Optional[str] = None,
                 nombre: Optional[str] = None, apellido: Optional[str] = None,
                 nacionalidad: Optional[str] = None, edad_min: Optional[int] = None,
                 edad_max: Optional[int] = None, telefono: Optional[str] = None,
                 email: Optional[str] = None, alias: Optional[str] = None,
                 imagen: Optional[str] = None, imagen_url: Optional[str] = None,
                 region: str = "ES", incluir_rojos: bool = False,
                 operador: Optional[str] = None):
        self.nombre_completo = nombre_completo or " ".join(
            x for x in [nombre, apellido] if x) or None
        self.nombre = nombre
        self.apellido = apellido
        self.nacionalidad = nacionalidad
        self.edad_min, self.edad_max = edad_min, edad_max
        self.telefono = telefono
        self.email = email
        self.alias = alias
        self.imagen = imagen
        self.imagen_url = imagen_url
        self.region = region
        self.incluir_rojos = incluir_rojos
        self.operador = operador
        self.resultados: List[Resultado] = []
        self.grafo = Grafo()

    # ------------------------------------------------------------- utils
    def fuentes_usadas(self) -> List[str]:
        return sorted({r.fuente for r in self.resultados})

    def objetivo(self) -> str:
        return (self.nombre_completo or self.telefono or self.email
                or self.alias or self.imagen or "(sin objetivo)")

    # --------------------------------------------------------- ejecución
    def ejecutar(self, log=print) -> None:
        if self.nombre_completo or self.nombre or self.apellido:
            log("[*] INTERPOL (avisos)...")
            self.resultados += InterpolColector().buscar(
                nombre=self.nombre or (self.nombre_completo.split()[0]
                                       if self.nombre_completo else None),
                apellido=self.apellido, nacionalidad=self.nacionalidad,
                edad_min=self.edad_min, edad_max=self.edad_max,
                incluir_rojos=self.incluir_rojos)
            log("[*] Noticias...")
            self.resultados += NoticiasColector().buscar(nombre_completo=self.nombre_completo)
            log("[*] Cosecha de contactos en páginas públicas...")
            self.resultados += WebColector().cosechar_contactos(
                nombre_completo=self.nombre_completo, region=self.region)
            log("[*] Enlaces-pivote...")
            self.resultados += PivotesColector().buscar(
                nombre_completo=self.nombre_completo, imagen_url=self.imagen_url)

        if self.telefono:
            log("[*] Teléfono (análisis)...")
            self.resultados += PhoneColector().buscar(numero=self.telefono, region=self.region)
            log("[*] Teléfono (búsqueda inversa)...")
            self.resultados += WebColector().inversa(valor=self.telefono, region=self.region)

        if self.email:
            log("[*] Email (análisis)...")
            self.resultados += EmailColector().buscar(email=self.email)
            log("[*] Email (búsqueda inversa)...")
            self.resultados += WebColector().inversa(valor=self.email, region=self.region)

        if self.alias:
            log("[*] Alias en plataformas...")
            self.resultados += UsernameColector().buscar(usuario=self.alias)

        if self.imagen:
            log("[*] EXIF de la imagen...")
            self.resultados += ExifColector().buscar(ruta=self.imagen)

        self._construir_grafo()

    # ----------------------------------------------------------- grafo
    def _construir_grafo(self) -> None:
        self.grafo.sujeto(self.objetivo())
        for r in self.resultados:
            ent = _entidad_de(r)
            if ent is not None:
                tipo, etiqueta = ent
                self.grafo.entidad(tipo, etiqueta, r.fuente)

    # --------------------------------------------------------- export
    def exportar(self, *, json_ruta=None, html_ruta=None, pdf_ruta=None,
                 grafo_ruta=None, log=print) -> None:
        meta = {"objetivo": self.objetivo(), "operador": self.operador or "",
                "fuentes": ", ".join(self.fuentes_usadas())}
        if json_ruta:
            p = report.exportar_json(self.resultados, json_ruta, meta)
            log(f"[+] JSON: {p}")
        if html_ruta:
            p = report.exportar_html(self.resultados, html_ruta, meta)
            log(f"[+] HTML: {p}")

        png = None
        if grafo_ruta or pdf_ruta:
            destino = grafo_ruta or str(Path(tempfile.gettempdir()) / "rastro_grafo.png")
            png = self.grafo.render_png(destino)
            if png and grafo_ruta:
                log(f"[+] Grafo PNG: {png}")
            elif grafo_ruta and not png:
                log("[!] No se pudo generar el grafo (¿faltan networkx/matplotlib?).")

        if pdf_ruta:
            from .report_pdf import exportar_pdf
            p = exportar_pdf(self.resultados, pdf_ruta, meta=meta,
                             grafo_png=png, correlaciones=self.grafo.correlaciones(),
                             resumen=self.grafo.resumen())
            if p:
                log(f"[+] PDF: {p}")
            else:
                log("[!] No se pudo generar el PDF (¿falta reportlab?).")


def _entidad_de(r: Resultado):
    """Traduce un Resultado a un nodo del grafo, o None si no procede."""
    t = r.tipo
    if t == "email":
        return ("email", r.titulo)
    if t in ("número", "telefono"):
        return ("telefono", r.datos.get("e164") or r.titulo)
    if t in ("perfil", "gravatar"):
        return ("perfil", r.titulo)
    if t in ("aviso amarillo", "aviso rojo"):
        return ("aviso", r.titulo)
    if t == "gps":
        return ("ubicacion", r.titulo)
    if t == "noticia" or t == "pagina":
        return ("pagina", (r.url or r.titulo)[:60])
    return None
