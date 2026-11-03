"""Extracción de entidades (emails y teléfonos) de texto libre.

Se usa sobre el texto de páginas públicas y sobre los campos de los resultados.
Para teléfonos usamos el detector de phonenumbers (valida de verdad), no solo una
expresión regular, para reducir falsos positivos.
"""
from __future__ import annotations

import re
from typing import List, Set

_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Correos "basura" típicos de plantillas/imágenes que no son contactos reales.
_EMAIL_RUIDO = ("example.com", "example.org", "sentry.io", "@2x", "@3x",
                "domain.com", "email.com", "yourdomain", "wixpress.com")

try:
    import phonenumbers
    _PH = True
except Exception:
    _PH = False


def emails(texto: str) -> List[str]:
    if not texto:
        return []
    vistos: Set[str] = set()
    salida: List[str] = []
    for m in _RE_EMAIL.findall(texto):
        e = m.lower().strip(".")
        if any(r in e for r in _EMAIL_RUIDO):
            continue
        if e not in vistos:
            vistos.add(e)
            salida.append(e)
    return salida


def telefonos(texto: str, region: str = "ES") -> List[str]:
    """Devuelve teléfonos válidos en formato E.164 detectados en el texto."""
    if not texto or not _PH:
        return []
    vistos: Set[str] = set()
    salida: List[str] = []
    try:
        for match in phonenumbers.PhoneNumberMatcher(texto, region):
            num = match.number
            if phonenumbers.is_valid_number(num):
                e164 = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
                if e164 not in vistos:
                    vistos.add(e164)
                    salida.append(e164)
    except Exception:
        return salida
    return salida
