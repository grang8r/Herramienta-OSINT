"""Modelo de datos común a todos los colectores."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


# Niveles de confianza. En OSINT nunca damos un hallazgo por "confirmado" sin
# verificación manual: distinguimos siempre hipótesis de hecho observado.
CONF_ALTA = "alta"      # dato estructurado de una fuente oficial (p. ej. Interpol)
CONF_MEDIA = "media"    # señal fuerte pero que requiere verificación humana
CONF_BAJA = "baja"      # pista / pivote para investigar manualmente


@dataclass
class Resultado:
    """Un hallazgo individual producido por un colector.

    No representa una verdad confirmada, sino una *pista* con su procedencia y un
    nivel de confianza. La verificación final siempre es responsabilidad del
    analista.
    """
    fuente: str                       # nombre del colector ("interpol", "noticias"...)
    tipo: str                         # categoría del hallazgo ("aviso", "perfil", "noticia"...)
    titulo: str                       # resumen en una línea
    detalle: str = ""                 # texto adicional legible
    url: Optional[str] = None         # enlace para verificar/pivotar
    confianza: str = CONF_BAJA        # CONF_ALTA | CONF_MEDIA | CONF_BAJA
    datos: Dict[str, Any] = field(default_factory=dict)  # datos crudos de la fuente

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
