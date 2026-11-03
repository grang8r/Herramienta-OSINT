"""Colector de Avisos (Notices) públicos de INTERPOL.

API pública, sin autenticación:
  - Avisos Amarillos  (personas desaparecidas):  /notices/v1/yellow
  - Avisos Rojos      (buscados, uso secundario): /notices/v1/red
Base: https://ws-public.interpol.int

La respuesta es HAL+JSON: los avisos vienen en `_embedded.notices`. Parseamos con
.get() en todo momento para que un cambio de esquema degrade con elegancia en vez
de romper la ejecución o inventar campos.
"""
from __future__ import annotations

from typing import List, Optional

from ..core import http
from ..core.collector import Colector
from ..core.model import Resultado, CONF_ALTA, CONF_MEDIA

_BASE = "https://ws-public.interpol.int/notices/v1"
_UI_YELLOW = "https://www.interpol.int/How-we-work/Notices/View-Yellow-Notices"


class InterpolColector(Colector):
    nombre = "interpol"
    descripcion = "Avisos Amarillos (desaparecidos) y Rojos (buscados) de INTERPOL"

    def buscar(self, *, nombre: Optional[str] = None, apellido: Optional[str] = None,
               nacionalidad: Optional[str] = None, edad_min: Optional[int] = None,
               edad_max: Optional[int] = None, incluir_rojos: bool = False,
               max_resultados: int = 20, **_) -> List[Resultado]:
        resultados: List[Resultado] = []
        resultados += self._consultar("yellow", nombre, apellido, nacionalidad,
                                      edad_min, edad_max, max_resultados)
        if incluir_rojos:
            resultados += self._consultar("red", nombre, apellido, nacionalidad,
                                          edad_min, edad_max, max_resultados)
        return resultados

    def _consultar(self, tipo: str, nombre, apellido, nacionalidad,
                   edad_min, edad_max, limite: int) -> List[Resultado]:
        # La API usa `forename` (nombre) y `name` (apellido); `nationality` es
        # el código ISO de país (ES, FR, ...). Enviamos solo lo que tengamos.
        params = {"resultPerPage": max(1, min(limite, 160))}
        if nombre:
            params["forename"] = nombre
        if apellido:
            params["name"] = apellido
        if nacionalidad:
            params["nationality"] = nacionalidad.upper()
        if edad_min is not None:
            params["ageMin"] = edad_min
        if edad_max is not None:
            params["ageMax"] = edad_max

        resp = http.get(f"{_BASE}/{tipo}", params=params)
        if resp is None or resp.status_code != 200:
            return []
        try:
            data = resp.json()
        except ValueError:
            return []

        avisos = (((data or {}).get("_embedded") or {}).get("notices")) or []
        conf = CONF_ALTA if tipo == "yellow" else CONF_MEDIA
        etiqueta = "aviso amarillo" if tipo == "yellow" else "aviso rojo"
        salida: List[Resultado] = []
        for a in avisos[:limite]:
            nom = " ".join(x for x in [a.get("forename"), a.get("name")] if x).strip()
            nac = ", ".join(a.get("nationalities") or []) or "—"
            fnac = a.get("date_of_birth") or "—"
            entity = a.get("entity_id") or ""
            # Enlace directo al JSON del aviso (desde ahí cuelgan imágenes, etc.).
            enlace = (((a.get("_links") or {}).get("self") or {}).get("href")) or _UI_YELLOW
            salida.append(Resultado(
                fuente=self.nombre,
                tipo=etiqueta,
                titulo=nom or "(sin nombre)",
                detalle=f"Nac.: {nac} · Fecha nac.: {fnac} · ID: {entity}",
                url=enlace,
                confianza=conf,
                datos=a,
            ))
        return salida
