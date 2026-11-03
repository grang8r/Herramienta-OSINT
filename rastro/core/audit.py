"""Registro de auditoría de consultas.

En OSINT profesional, dejar constancia de qué se buscó, cuándo y con qué fuentes
es parte de la metodología y la diferencia entre una investigación legítima y un
abuso. Cada ejecución escribe una línea JSON (JSONL) en el log.
"""
from __future__ import annotations

import datetime as _dt
import getpass
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ubicación por defecto del log (sobreescribible con la variable de entorno).
_DIR = Path(os.environ.get("RASTRO_HOME", Path.home() / ".rastro"))
_LOG = _DIR / "auditoria.jsonl"


def _ahora_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def registrar(accion: str, objetivo: str, fuentes: List[str],
              operador: Optional[str] = None, extra: Optional[Dict[str, Any]] = None,
              ruta_log: Optional[Path] = None) -> Path:
    """Añade una entrada al log de auditoría y devuelve la ruta del fichero."""
    log = Path(ruta_log) if ruta_log else _LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    entrada = {
        "ts": _ahora_iso(),
        "operador": operador or _operador_por_defecto(),
        "accion": accion,
        "objetivo": objetivo,
        "fuentes": fuentes,
    }
    if extra:
        entrada["extra"] = extra
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    return log


def _operador_por_defecto() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return "desconocido"
