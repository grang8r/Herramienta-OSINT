"""Colector web: resultados de búsqueda y extracción de contactos públicos.

Funciones:
 - resultados(consulta): páginas públicas que coinciden con la consulta
   (DuckDuckGo HTML, keyless).
 - cosechar_contactos(consulta): abre las primeras páginas públicas y extrae los
   emails y teléfonos que APARECEN en ellas. Solo lee contenido público.
 - inversa(valor): búsqueda inversa de un teléfono o email -> páginas donde
   aparece + otros contactos que co-ocurren en ellas.

Todo se hace sobre contenido abierto, con límite de páginas y respetando el
rate-limit global. No hay fuerza bruta de SMTP ni generación masiva de correos.
"""
from __future__ import annotations

import re
import urllib.parse
from typing import List, Optional, Tuple

from ..core import http, extract
from ..core.collector import Colector
from ..core.model import Resultado, CONF_MEDIA, CONF_BAJA

_DDG = "https://html.duckduckgo.com/html/"
_MAX_PAGINAS = 5


def _buscar_ddg(consulta: str, limite: int = 10) -> List[Tuple[str, str, str]]:
    """Devuelve [(titulo, url, snippet)] de DuckDuckGo HTML."""
    resp = http.get(_DDG, params={"q": consulta}, headers={"Referer": _DDG})
    if resp is None or resp.status_code != 200 or not resp.text:
        return []
    html = resp.text
    salida: List[Tuple[str, str, str]] = []
    try:
        from bs4 import BeautifulSoup
        sopa = BeautifulSoup(html, "html.parser")
        for res in sopa.select(".result")[:limite]:
            a = res.select_one("a.result__a")
            if not a:
                continue
            url = _resolver_ddg(a.get("href", ""))
            titulo = a.get_text(" ", strip=True)
            snip_el = res.select_one(".result__snippet")
            snippet = snip_el.get_text(" ", strip=True) if snip_el else ""
            if url:
                salida.append((titulo, url, snippet))
    except Exception:
        # Reserva sin bs4: extraer enlaces uddg por regex.
        for m in re.findall(r'uddg=([^"&]+)', html)[:limite]:
            url = urllib.parse.unquote(m)
            salida.append((url, url, ""))
    return salida


def _resolver_ddg(href: str) -> str:
    """DuckDuckGo envuelve los enlaces: //duckduckgo.com/l/?uddg=<url real>."""
    if not href:
        return ""
    if "uddg=" in href:
        q = urllib.parse.urlparse(href).query
        params = urllib.parse.parse_qs(q)
        if "uddg" in params:
            return params["uddg"][0]
    if href.startswith("//"):
        return "https:" + href
    return href


def _texto_de(url: str) -> str:
    resp = http.get(url, timeout=12)
    if resp is None or resp.status_code != 200:
        return ""
    ctype = resp.headers.get("Content-Type", "")
    if "html" not in ctype and "text" not in ctype:
        return ""
    try:
        from bs4 import BeautifulSoup
        sopa = BeautifulSoup(resp.text, "html.parser")
        for t in sopa(["script", "style", "noscript"]):
            t.extract()
        return sopa.get_text(" ", strip=True)
    except Exception:
        return resp.text


class WebColector(Colector):
    nombre = "web"
    descripcion = "Búsqueda y extracción de contactos en páginas públicas"

    # --- páginas que coinciden con una consulta --------------------------
    def resultados(self, *, consulta: str, limite: int = 8) -> List[Resultado]:
        out = []
        for titulo, url, snippet in _buscar_ddg(consulta, limite):
            out.append(Resultado(self.nombre, "pagina", titulo or url,
                                  detalle=snippet, url=url, confianza=CONF_BAJA))
        return out

    # --- cosecha de emails/teléfonos de una persona ----------------------
    def cosechar_contactos(self, *, nombre_completo: str, region: str = "ES",
                           max_paginas: int = _MAX_PAGINAS) -> List[Resultado]:
        if not nombre_completo:
            return []
        consulta = f'"{nombre_completo}" (contacto OR email OR correo OR teléfono OR telefono)'
        paginas = _buscar_ddg(consulta, max_paginas)
        out: List[Resultado] = []
        for titulo, url, _ in paginas:
            texto = _texto_de(url)
            if not texto:
                continue
            for e in extract.emails(texto):
                out.append(Resultado(self.nombre, "email", e,
                                     detalle=f"Encontrado en: {url}", url=url,
                                     confianza=CONF_MEDIA, datos={"origen": url}))
            for t in extract.telefonos(texto, region):
                out.append(Resultado(self.nombre, "telefono", t,
                                     detalle=f"Encontrado en: {url}", url=url,
                                     confianza=CONF_MEDIA, datos={"origen": url}))
        return out

    # --- búsqueda inversa por teléfono o email ---------------------------
    def inversa(self, *, valor: str, region: str = "ES",
                max_paginas: int = _MAX_PAGINAS) -> List[Resultado]:
        if not valor:
            return []
        paginas = _buscar_ddg(f'"{valor}"', max_paginas + 3)
        out: List[Resultado] = []
        for titulo, url, snippet in paginas:
            out.append(Resultado(self.nombre, "pagina",
                                 f"Aparece en: {titulo or url}",
                                 detalle=snippet, url=url, confianza=CONF_MEDIA))
        # Contactos que co-ocurren en esas páginas (posibles vínculos).
        for titulo, url, _ in paginas[:max_paginas]:
            texto = _texto_de(url)
            if not texto:
                continue
            for e in extract.emails(texto):
                if e.lower() != valor.lower():
                    out.append(Resultado(self.nombre, "email", e,
                                         detalle=f"Co-ocurre con {valor} en {url}",
                                         url=url, confianza=CONF_BAJA, datos={"origen": url}))
            for t in extract.telefonos(texto, region):
                if t != valor:
                    out.append(Resultado(self.nombre, "telefono", t,
                                         detalle=f"Co-ocurre con {valor} en {url}",
                                         url=url, confianza=CONF_BAJA, datos={"origen": url}))
        return out
