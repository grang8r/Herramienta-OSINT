"""Análisis de una dirección de correo.

Sin servicios de pago ni volcados de brechas. Hacemos:
 - Validación sintáctica básica.
 - Comprobación de Gravatar (público y keyless): si existe un avatar/perfil
   asociado al hash del correo, puede revelar nombre, enlaces y foto.
 - Enlaces-pivote para buscadores.
"""
from __future__ import annotations

import hashlib
import re
from typing import List, Optional

from ..core import http
from ..core.collector import Colector
from ..core.model import Resultado, CONF_MEDIA, CONF_BAJA

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmailColector(Colector):
    nombre = "email"
    descripcion = "Validación, Gravatar y pivotes de un correo"

    def buscar(self, *, email: Optional[str] = None, **_) -> List[Resultado]:
        if not email:
            return []
        email = email.strip().lower()
        if not _RE_EMAIL.match(email):
            return [Resultado(self.nombre, "error", f"Sintaxis no válida: {email}",
                              confianza=CONF_BAJA)]

        salida: List[Resultado] = []
        h = hashlib.md5(email.encode("utf-8")).hexdigest()

        # Gravatar: ¿existe avatar? (d=404 -> 404 si no hay imagen asociada)
        av = http.get(f"https://www.gravatar.com/avatar/{h}?d=404&s=200")
        if av is not None and av.status_code == 200:
            salida.append(Resultado(
                self.nombre, "gravatar",
                "Existe un Gravatar asociado a este correo",
                detalle="Puede incluir foto y perfil público.",
                url=f"https://www.gravatar.com/avatar/{h}?s=400",
                confianza=CONF_MEDIA,
            ))
            # Perfil público en JSON (si el usuario lo configuró).
            perfil = http.get(f"https://www.gravatar.com/{h}.json")
            if perfil is not None and perfil.status_code == 200:
                try:
                    data = perfil.json()
                    entry = (data.get("entry") or [{}])[0]
                    nombre = (entry.get("displayName")
                              or (entry.get("name") or {}).get("formatted") or "")
                    url_perf = entry.get("profileUrl") or f"https://gravatar.com/{h}"
                    salida.append(Resultado(
                        self.nombre, "perfil",
                        f"Perfil Gravatar público: {nombre or '(sin nombre)'}",
                        detalle="Revisar enlaces y cuentas asociadas en el perfil.",
                        url=url_perf, confianza=CONF_MEDIA, datos=entry,
                    ))
                except ValueError:
                    pass

        # Pivotes de búsqueda manual.
        for etiqueta, url in [
            ("Búsqueda web exacta", f"https://duckduckgo.com/?q=%22{email}%22"),
            ("¿Filtrado en brechas? (HaveIBeenPwned, manual)",
             f"https://haveibeenpwned.com/account/{email}"),
        ]:
            salida.append(Resultado(self.nombre, "pivote", etiqueta, url=url, confianza=CONF_BAJA))
        return salida
