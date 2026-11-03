"""Cliente HTTP compartido: cabeceras educadas, reintentos, timeout y rate-limit.

Centralizar aquí la red nos da un único punto donde controlar el comportamiento
"buen ciudadano" de la herramienta: identificarnos con un User-Agent honesto,
limitar la frecuencia de peticiones y no martillear a ninguna fuente.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import requests
from requests.adapters import HTTPAdapter

try:
    # urllib3 viaja dentro de requests; la ruta puede variar según versión.
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover
    from requests.packages.urllib3.util.retry import Retry  # type: ignore


# User-Agent honesto: nos identificamos como lo que somos.
USER_AGENT = f"RASTRO-OSINT/0.1 (+investigacion; respeta-robots)"

# Límite global de peticiones por segundo (cortesía con las fuentes).
_MIN_INTERVALO_S = 1.0


class _RateLimiter:
    """Separa cada petición saliente al menos _MIN_INTERVALO_S segundos."""

    def __init__(self, intervalo: float):
        self._intervalo = intervalo
        self._lock = threading.Lock()
        self._ultimo = 0.0

    def esperar(self) -> None:
        with self._lock:
            ahora = time.monotonic()
            delta = ahora - self._ultimo
            if delta < self._intervalo:
                time.sleep(self._intervalo - delta)
            self._ultimo = time.monotonic()


_limiter = _RateLimiter(_MIN_INTERVALO_S)


def nueva_sesion() -> requests.Session:
    """Devuelve una sesión con reintentos y cabeceras ya configuradas."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    })
    retry = Retry(
        total=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


# Sesión por defecto reutilizable.
SESION = nueva_sesion()


def get(url: str, *, params: Optional[dict] = None, timeout: int = 20,
        session: Optional[requests.Session] = None, **kwargs) -> Optional[requests.Response]:
    """GET con rate-limit y manejo de errores. Devuelve None si la red falla.

    Nunca lanza por un fallo de red: devolver None permite que un colector caído
    no tumbe toda la investigación.
    """
    s = session or SESION
    _limiter.esperar()
    try:
        resp = s.get(url, params=params, timeout=timeout, **kwargs)
        return resp
    except requests.RequestException:
        return None


def head(url: str, *, timeout: int = 15, allow_redirects: bool = True,
         session: Optional[requests.Session] = None, **kwargs) -> Optional[requests.Response]:
    """HEAD con rate-limit; cae a GET ligero si el servidor no soporta HEAD."""
    s = session or SESION
    _limiter.esperar()
    try:
        resp = s.head(url, timeout=timeout, allow_redirects=allow_redirects, **kwargs)
        # Algunos servidores devuelven 405/501 a HEAD: reintentamos con GET parcial.
        if resp.status_code in (405, 501):
            _limiter.esperar()
            resp = s.get(url, timeout=timeout, allow_redirects=allow_redirects,
                         stream=True, **kwargs)
        return resp
    except requests.RequestException:
        return None
