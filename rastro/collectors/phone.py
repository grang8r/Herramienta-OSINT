"""Análisis de números de teléfono con la librería phonenumbers (offline).

phonenumbers es el port de libphonenumber de Google: valida el número y deduce
país, región, operador aproximado, zona horaria y tipo de línea. Todo en local,
sin ninguna petición de red. Añadimos además enlaces-pivote para investigación
manual.
"""
from __future__ import annotations

from typing import List, Optional

from ..core.collector import Colector
from ..core.model import Resultado, CONF_ALTA, CONF_BAJA

try:
    import phonenumbers
    from phonenumbers import carrier, geocoder, timezone as ph_tz
    _OK = True
except Exception:
    _OK = False


class PhoneColector(Colector):
    nombre = "telefono"
    descripcion = "Validación y geolocalización aproximada de un número"

    def buscar(self, *, numero: Optional[str] = None, region: str = "ES", **_) -> List[Resultado]:
        if not numero:
            return []
        if not _OK:
            return [Resultado(self.nombre, "error",
                              "Falta la dependencia 'phonenumbers' (pip install phonenumbers)",
                              confianza=CONF_BAJA)]
        try:
            num = phonenumbers.parse(numero, region)
        except phonenumbers.NumberParseException as e:
            return [Resultado(self.nombre, "error", f"No se pudo parsear: {e}", confianza=CONF_BAJA)]

        valido = phonenumbers.is_valid_number(num)
        e164 = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
        internac = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        pais = geocoder.description_for_number(num, "es") or "—"
        operador = carrier.name_for_number(num, "es") or "—"
        zonas = ", ".join(ph_tz.time_zones_for_number(num)) or "—"
        tipo = _tipo_linea(num)

        resultados = [Resultado(
            fuente=self.nombre,
            tipo="número",
            titulo=f"{internac} ({'válido' if valido else 'NO válido'})",
            detalle=(f"E.164: {e164} · Zona: {pais} · Operador: {operador} · "
                     f"Tipo: {tipo} · TZ: {zonas}"),
            confianza=CONF_ALTA if valido else CONF_BAJA,
            datos={"e164": e164, "valido": valido, "zona": pais,
                   "operador": operador, "tipo": tipo, "timezones": zonas},
        )]

        # Pivotes de búsqueda manual (WhatsApp, buscadores, apps de identificación).
        solo_mas = e164.replace("+", "")
        pivotes = [
            ("WhatsApp (ver si está registrado)", f"https://wa.me/{solo_mas}"),
            ("Búsqueda web del número", f"https://duckduckgo.com/?q=%22{e164}%22"),
            ("Búsqueda del número local", f"https://duckduckgo.com/?q=%22{internac.replace(' ', '%20')}%22"),
        ]
        for etiqueta, url in pivotes:
            resultados.append(Resultado(self.nombre, "pivote", etiqueta, url=url,
                                        confianza=CONF_BAJA))
        return resultados


def _tipo_linea(num) -> str:
    tipos = {
        phonenumbers.PhoneNumberType.MOBILE: "móvil",
        phonenumbers.PhoneNumberType.FIXED_LINE: "fijo",
        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fijo/móvil",
        phonenumbers.PhoneNumberType.VOIP: "VoIP",
        phonenumbers.PhoneNumberType.TOLL_FREE: "gratuito",
        phonenumbers.PhoneNumberType.PREMIUM_RATE: "tarificación especial",
    }
    return tipos.get(phonenumbers.number_type(num), "desconocido")
