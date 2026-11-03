"""Clase base para todos los colectores y utilidades de registro."""
from __future__ import annotations

from typing import Dict, List

from .model import Resultado


class Colector:
    """Interfaz común. Cada fuente OSINT implementa una subclase.

    Un colector NUNCA debe lanzar una excepción hacia arriba por un fallo de red o
    de parseo: debe capturarla y devolver los resultados que haya podido obtener
    (posiblemente una lista vacía). Así, una fuente caída no tumba la investigación.
    """
    nombre: str = "base"
    descripcion: str = ""

    def buscar(self, **kwargs) -> List[Resultado]:  # pragma: no cover - interfaz
        raise NotImplementedError
