"""Extracción de metadatos EXIF de una foto local (offline).

En la búsqueda de desaparecidos, la última foto conocida puede llevar en sus
metadatos la fecha/hora exacta y, a veces, coordenadas GPS. Todo se procesa en
local: la imagen nunca se sube a ningún sitio.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..core.collector import Colector
from ..core.model import Resultado, CONF_ALTA, CONF_MEDIA, CONF_BAJA

try:
    from PIL import Image, ExifTags
    _OK = True
except Exception:
    _OK = False


class ExifColector(Colector):
    nombre = "exif"
    descripcion = "Metadatos EXIF/GPS de una imagen local"

    def buscar(self, *, ruta: Optional[str] = None, **_) -> List[Resultado]:
        if not ruta:
            return []
        if not _OK:
            return [Resultado(self.nombre, "error",
                              "Falta la dependencia 'Pillow' (pip install Pillow)",
                              confianza=CONF_BAJA)]
        p = Path(ruta)
        if not p.is_file():
            return [Resultado(self.nombre, "error", f"No existe el fichero: {ruta}",
                              confianza=CONF_BAJA)]
        try:
            img = Image.open(p)
            exif = img._getexif() or {}
        except Exception as e:
            return [Resultado(self.nombre, "error", f"No se pudo leer EXIF: {e}",
                              confianza=CONF_BAJA)]
        if not exif:
            return [Resultado(self.nombre, "info",
                              "La imagen no contiene metadatos EXIF",
                              detalle="Puede haber sido limpiada (redes sociales suelen borrarlos).",
                              confianza=CONF_BAJA)]

        tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        salida: List[Resultado] = []

        fecha = tags.get("DateTimeOriginal") or tags.get("DateTime")
        fabricante = " ".join(str(tags.get(x, "")).strip()
                              for x in ("Make", "Model")).strip()
        if fecha or fabricante:
            salida.append(Resultado(
                self.nombre, "metadato",
                f"Captura: {fecha or '—'}",
                detalle=f"Dispositivo: {fabricante or '—'}",
                confianza=CONF_MEDIA,
                datos={"fecha": fecha, "dispositivo": fabricante},
            ))

        coords = _gps_decimal(tags.get("GPSInfo"))
        if coords:
            lat, lon = coords
            osm = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=16/{lat}/{lon}"
            salida.append(Resultado(
                self.nombre, "gps",
                f"Coordenadas GPS: {lat:.6f}, {lon:.6f}",
                detalle="Ubicación donde se tomó la foto (abrir en mapa).",
                url=osm, confianza=CONF_ALTA,
                datos={"lat": lat, "lon": lon},
            ))
        else:
            salida.append(Resultado(self.nombre, "info",
                                    "EXIF presente, pero sin coordenadas GPS",
                                    confianza=CONF_BAJA))
        return salida


def _gps_decimal(gpsinfo):
    """Convierte el bloque GPSInfo de EXIF a (lat, lon) en grados decimales."""
    if not gpsinfo:
        return None
    try:
        from PIL import ExifTags
        g = {ExifTags.GPSTAGS.get(k, k): v for k, v in gpsinfo.items()}
        lat = _a_grados(g.get("GPSLatitude"), g.get("GPSLatitudeRef"))
        lon = _a_grados(g.get("GPSLongitude"), g.get("GPSLongitudeRef"))
        if lat is None or lon is None:
            return None
        return lat, lon
    except Exception:
        return None


def _a_grados(valor, ref):
    if not valor or not ref:
        return None
    try:
        d, m, s = [float(x) for x in valor]
        dec = d + m / 60.0 + s / 3600.0
        if str(ref).upper() in ("S", "W"):
            dec = -dec
        return dec
    except Exception:
        return None
