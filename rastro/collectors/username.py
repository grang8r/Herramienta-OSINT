"""Enumeración de nombres de usuario en plataformas públicas.

Comprobamos si existe un perfil público para un alias dado consultando la URL
canónica de cada plataforma. Es el enfoque de herramientas tipo Sherlock, pero
reducido a un conjunto curado y fiable.

Limitaciones honestas (se reflejan en el nivel de confianza):
 - Un 200 no garantiza que el perfil sea de la persona buscada (homónimos).
 - Algunas plataformas devuelven 200 para perfiles inexistentes ("soft 404"),
   por eso además buscamos marcadores de "no encontrado" cuando los conocemos.
 - La detección es una PISTA para verificación manual, nunca una confirmación.
"""
from __future__ import annotations

import concurrent.futures as cf
from typing import List, Optional

from ..core import http
from ..core.collector import Colector
from ..core.model import Resultado, CONF_MEDIA, CONF_BAJA

# (plataforma, plantilla_url, marcador_de_no_encontrado_opcional)
PLATAFORMAS = [
    ("GitHub", "https://github.com/{u}", None),
    ("GitLab", "https://gitlab.com/{u}", None),
    ("Instagram", "https://www.instagram.com/{u}/", None),
    ("X/Twitter", "https://x.com/{u}", None),
    ("Facebook", "https://www.facebook.com/{u}", None),
    ("TikTok", "https://www.tiktok.com/@{u}", None),
    ("YouTube", "https://www.youtube.com/@{u}", None),
    ("Reddit", "https://www.reddit.com/user/{u}", "nobody on Reddit"),
    ("Telegram", "https://t.me/{u}", "tgme_page_additional"),  # presencia es ambigua
    ("Pinterest", "https://www.pinterest.com/{u}/", None),
    ("Twitch", "https://www.twitch.tv/{u}", None),
    ("Steam", "https://steamcommunity.com/id/{u}", "The specified profile could not be found"),
    ("SoundCloud", "https://soundcloud.com/{u}", None),
    ("Spotify", "https://open.spotify.com/user/{u}", None),
    ("Keybase", "https://keybase.io/{u}", None),
    ("Medium", "https://medium.com/@{u}", None),
    ("DeviantArt", "https://www.deviantart.com/{u}", None),
    ("Flickr", "https://www.flickr.com/people/{u}", None),
    ("VK", "https://vk.com/{u}", None),
    ("Linktree", "https://linktr.ee/{u}", None),
    ("About.me", "https://about.me/{u}", None),
    ("Gravatar", "https://gravatar.com/{u}", None),
    ("Mastodon (mastodon.social)", "https://mastodon.social/@{u}", None),
    ("Bluesky", "https://bsky.app/profile/{u}.bsky.social", None),
]


class UsernameColector(Colector):
    nombre = "usuario"
    descripcion = "Búsqueda de un alias en plataformas públicas"

    def buscar(self, *, usuario: Optional[str] = None, max_hilos: int = 8, **_) -> List[Resultado]:
        if not usuario:
            return []
        usuario = usuario.strip().lstrip("@")
        sesion = http.nueva_sesion()

        def _check(entrada):
            nombre_plat, plantilla, marcador = entrada
            url = plantilla.format(u=usuario)
            try:
                resp = sesion.get(url, timeout=12, allow_redirects=True)
            except Exception:
                return None
            if resp.status_code != 200:
                return None
            # Posible "soft 404": si hay marcador conocido y aparece, descartamos.
            if marcador and marcador.lower() in resp.text.lower():
                return None
            return Resultado(
                fuente=self.nombre,
                tipo="perfil",
                titulo=f"{nombre_plat}: posible perfil de '{usuario}'",
                detalle="Responde 200. Verificar manualmente (puede ser homónimo).",
                url=url,
                confianza=CONF_MEDIA if marcador else CONF_BAJA,
            )

        salida: List[Resultado] = []
        with cf.ThreadPoolExecutor(max_workers=max_hilos) as ex:
            for r in ex.map(_check, PLATAFORMAS):
                if r is not None:
                    salida.append(r)
        return salida
