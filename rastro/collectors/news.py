"""Colector de noticias vía Google News RSS (público, keyless).

Para una persona desaparecida, la cobertura periodística (fecha de desaparición,
última ubicación conocida, llamamientos policiales) suele ser la fuente abierta
más rica. Usamos el endpoint RSS de Google News, que devuelve XML y no requiere
clave ni scraping del HTML.
"""
from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Optional

from ..core import http
from ..core.collector import Colector
from ..core.model import Resultado, CONF_MEDIA, CONF_BAJA

_RSS = "https://news.google.com/rss/search"


class NoticiasColector(Colector):
    nombre = "noticias"
    descripcion = "Búsqueda de noticias (Google News RSS)"

    def buscar(self, *, consulta: Optional[str] = None, nombre_completo: Optional[str] = None,
               idioma: str = "es", pais: str = "ES", max_resultados: int = 15, **_) -> List[Resultado]:
        termino = consulta
        if not termino and nombre_completo:
            # Consulta orientada a desapariciones, en varios idiomas.
            termino = f'"{nombre_completo}" (desaparecido OR desaparecida OR missing)'
        if not termino:
            return []

        params = {
            "q": termino,
            "hl": f"{idioma}-{pais}",
            "gl": pais,
            "ceid": f"{pais}:{idioma}",
        }
        url = f"{_RSS}?{urllib.parse.urlencode(params)}"
        resp = http.get(url)
        if resp is None or resp.status_code != 200 or not resp.content:
            return []

        try:
            raiz = ET.fromstring(resp.content)
        except ET.ParseError:
            return []

        items = raiz.findall(".//item")
        salida: List[Resultado] = []
        for it in items[:max_resultados]:
            titulo = _texto(it, "title")
            enlace = _texto(it, "link")
            fecha = _texto(it, "pubDate")
            fuente = ""
            nodo_fuente = it.find("source")
            if nodo_fuente is not None and nodo_fuente.text:
                fuente = nodo_fuente.text
            # Más confianza si el titular menciona explícitamente desaparición.
            t_low = (titulo or "").lower()
            conf = CONF_MEDIA if any(k in t_low for k in
                                     ("desaparec", "missing", "búsqueda", "busqueda")) else CONF_BAJA
            salida.append(Resultado(
                fuente=self.nombre,
                tipo="noticia",
                titulo=titulo or "(sin título)",
                detalle=" · ".join(x for x in [fuente, fecha] if x),
                url=enlace,
                confianza=conf,
                datos={"pubDate": fecha, "source": fuente},
            ))
        return salida


def _texto(elem, tag: str) -> str:
    n = elem.find(tag)
    return (n.text or "").strip() if n is not None and n.text else ""
