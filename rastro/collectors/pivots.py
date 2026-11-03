"""Generador de enlaces-pivote para investigación manual.

No consulta ninguna API: construye URLs listas para abrir en el navegador. Son el
punto de partida para el trabajo manual del analista (dorks, registros oficiales,
búsqueda inversa de imágenes).
"""
from __future__ import annotations

import urllib.parse
from typing import List, Optional

from ..core.collector import Colector
from ..core.model import Resultado, CONF_BAJA


def _q(s: str) -> str:
    return urllib.parse.quote_plus(s)


class PivotesColector(Colector):
    nombre = "pivotes"
    descripcion = "Enlaces para investigación manual (dorks, registros, imagen inversa)"

    def buscar(self, *, nombre_completo: Optional[str] = None,
               imagen_url: Optional[str] = None, **_) -> List[Resultado]:
        salida: List[Resultado] = []

        if nombre_completo:
            n = nombre_completo
            dorks = [
                ("Búsqueda exacta (DuckDuckGo)", f"https://duckduckgo.com/?q=%22{_q(n)}%22"),
                ("Redes sociales", f"https://duckduckgo.com/?q=%22{_q(n)}%22+(site:facebook.com+OR+site:instagram.com+OR+site:x.com+OR+site:linkedin.com)"),
                ("Documentos (PDF/DOC)", f"https://duckduckgo.com/?q=%22{_q(n)}%22+(filetype:pdf+OR+filetype:doc)"),
                ("Google (exacto)", f"https://www.google.com/search?q=%22{_q(n)}%22"),
            ]
            for etiqueta, url in dorks:
                salida.append(Resultado(self.nombre, "dork", etiqueta, url=url, confianza=CONF_BAJA))

            # Registros oficiales / ONG de desaparecidos para comprobación manual.
            registros = [
                ("INTERPOL — Avisos Amarillos (web)",
                 "https://www.interpol.int/How-we-work/Notices/View-Yellow-Notices"),
                ("NamUs (EE. UU.)", "https://www.namus.gov/MissingPersons/Search"),
                ("The Charley Project (EE. UU.)",
                 f"https://charleyproject.org/?s={_q(n)}"),
                ("SOS Desaparecidos (España)", "https://sosdesaparecidos.es/"),
                ("CNDES — Ministerio del Interior (España)",
                 "https://cndes-web.ses.mir.es/publico/Desaparecidos/"),
                ("Missing People (Reino Unido)", "https://www.missingpeople.org.uk/"),
            ]
            for etiqueta, url in registros:
                salida.append(Resultado(self.nombre, "registro", etiqueta, url=url,
                                        confianza=CONF_BAJA))

        # Búsqueda inversa de imagen: si tenemos una URL pública de la foto, la
        # pasamos a los motores que aceptan URL por parámetro.
        if imagen_url:
            iu = urllib.parse.quote(imagen_url, safe="")
            motores = [
                ("Google Lens", f"https://lens.google.com/uploadbyurl?url={iu}"),
                ("Yandex (imagen inversa)",
                 f"https://yandex.com/images/search?rpt=imageview&url={iu}"),
                ("Bing (imagen inversa)",
                 f"https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{iu}"),
                ("TinEye", f"https://tineye.com/search?url={iu}"),
            ]
            for etiqueta, url in motores:
                salida.append(Resultado(self.nombre, "imagen-inversa", etiqueta, url=url,
                                        confianza=CONF_BAJA))
        return salida
