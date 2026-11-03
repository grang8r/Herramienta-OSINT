"""Interfaz de línea de comandos de RASTRO."""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .core import audit, report
from .core.model import Resultado
from .core.investigation import Investigacion
from .collectors.username import UsernameColector
from .collectors.phone import PhoneColector
from .collectors.email import EmailColector
from .collectors.exif import ExifColector

BANNER = r"""
  ____      _      ____   _____ ____   ___
 |  _ \    / \    / ___| |_   _|  _ \ / _ \
 | |_) |  / _ \   \___ \   | | | |_) | | | |
 |  _ <  / ___ \   ___) |  | | |  _ <| |_| |
 |_| \_\/_/   \_\ |____/   |_| |_| \_\\___/   v{v}
  OSINT para localización de personas — solo fuentes públicas
""".format(v=__version__)

NOTA_ETICA = ("Uso previsto: búsqueda de personas desaparecidas e investigación OSINT "
              "autorizada.\nSolo se consultan fuentes públicas. Cada consulta queda "
              "registrada en el log de auditoría.\nLos hallazgos son PISTAS que requieren "
              "verificación humana, no hechos confirmados.")


# --------------------------- helpers ----------------------------------------

def _emitir_simple(resultados: List[Resultado], args, meta: dict) -> None:
    print()
    report.mostrar_consola(resultados)
    if getattr(args, "json", None):
        print(f"\n[+] JSON: {report.exportar_json(resultados, args.json, meta)}")
    if getattr(args, "html", None):
        print(f"[+] HTML: {report.exportar_html(resultados, args.html, meta)}")
    print(f"\n[=] {len(resultados)} hallazgos. Verifica cada uno antes de darlo por bueno.")


def _auditar(accion: str, objetivo: str, fuentes: List[str], args) -> None:
    if getattr(args, "no_audit", False):
        return
    ruta = audit.registrar(accion, objetivo, fuentes, operador=getattr(args, "operador", None))
    print(f"[i] Consulta registrada en auditoría: {ruta}")


def _ejecutar_investigacion(inv: Investigacion, args, accion: str) -> int:
    inv.ejecutar(log=print)
    _auditar(accion, inv.objetivo(), inv.fuentes_usadas(), args)
    print()
    report.mostrar_consola(inv.resultados)
    corr = inv.grafo.correlaciones()
    if corr:
        print(f"\n[★] {len(corr)} correlación(es) (datos en 2+ fuentes):")
        for c in corr:
            print(f"    - {c['tipo']}: {c['valor']}  [{', '.join(c['fuentes'])}]")
    inv.exportar(json_ruta=getattr(args, "json", None),
                 html_ruta=getattr(args, "html", None),
                 pdf_ruta=getattr(args, "pdf", None),
                 grafo_ruta=getattr(args, "grafo", None), log=print)
    print(f"\n[=] {len(inv.resultados)} hallazgos. Verifica cada uno antes de darlo por bueno.")
    return 0


# --------------------------- subcomandos rich -------------------------------

def _inv_desde_args(args) -> Investigacion:
    return Investigacion(
        nombre_completo=getattr(args, "nombre_completo", None),
        nombre=getattr(args, "nombre", None), apellido=getattr(args, "apellido", None),
        nacionalidad=getattr(args, "nacionalidad", None),
        edad_min=getattr(args, "edad_min", None), edad_max=getattr(args, "edad_max", None),
        telefono=getattr(args, "telefono", None), email=getattr(args, "email", None),
        alias=getattr(args, "alias", None), imagen=getattr(args, "imagen", None),
        imagen_url=getattr(args, "imagen_url", None), region=getattr(args, "region", "ES"),
        incluir_rojos=getattr(args, "incluir_rojos", False),
        operador=getattr(args, "operador", None))


def cmd_persona(args) -> int:
    print(f"[*] Persona: {args.nombre_completo!r} (nac={args.nacionalidad})")
    return _ejecutar_investigacion(_inv_desde_args(args), args, "persona")


def cmd_buscar(args) -> int:
    inv = _inv_desde_args(args)
    if not any([inv.nombre_completo, inv.nombre, inv.apellido, inv.telefono,
                inv.email, inv.alias, inv.imagen]):
        print("[!] Indica al menos un dato: --nombre-completo, --telefono, --email, "
              "--alias o --imagen.")
        return 2
    print(f"[*] Investigación sobre: {inv.objetivo()!r}")
    return _ejecutar_investigacion(inv, args, "buscar")


def cmd_interactivo(args) -> int:
    print("\n=== Modo asistente ===")
    print("Responde a lo que tengas; deja en blanco y pulsa Enter para saltar un dato.\n")
    nombre = _preg("Nombre y apellidos")
    nacionalidad = _preg("Nacionalidad (ISO, p. ej. ES)") if nombre else None
    telefono = _preg("Teléfono (con prefijo, p. ej. +34...)")
    email = _preg("Email")
    alias = _preg("Alias / nombre de usuario")
    imagen = _preg("Ruta de una foto local (para EXIF)")
    imagen_url = _preg("URL pública de una foto (para búsqueda inversa)")
    incluir_rojos = _preg_si("¿Incluir también Avisos Rojos de INTERPOL? (s/N)")

    inv = Investigacion(nombre_completo=nombre or None, nacionalidad=nacionalidad or None,
                        telefono=telefono or None, email=email or None, alias=alias or None,
                        imagen=imagen or None, imagen_url=imagen_url or None,
                        incluir_rojos=incluir_rojos, operador=getattr(args, "operador", None))
    if not any([inv.nombre_completo, inv.telefono, inv.email, inv.alias, inv.imagen]):
        print("[!] No has introducido ningún dato. Fin.")
        return 2

    print(f"\n[*] Investigando: {inv.objetivo()!r} ...")
    inv.ejecutar(log=print)
    _auditar("interactivo", inv.objetivo(), inv.fuentes_usadas(), args)
    print()
    report.mostrar_consola(inv.resultados)
    corr = inv.grafo.correlaciones()
    if corr:
        print(f"\n[★] {len(corr)} correlación(es) (datos en 2+ fuentes):")
        for c in corr:
            print(f"    - {c['tipo']}: {c['valor']}  [{', '.join(c['fuentes'])}]")

    # Exportación guiada.
    print()
    formato = _preg("¿Generar informe? [html/pdf/ambos/no]", "pdf").lower()
    if formato in ("no", "n", ""):
        print("[=] Sin informe. Fin.")
        return 0
    base = _preg("Nombre base del fichero (sin extensión)", "informe_rastro")
    html_ruta = f"{base}.html" if formato in ("html", "ambos") else None
    pdf_ruta = f"{base}.pdf" if formato in ("pdf", "ambos") else None
    inv.exportar(html_ruta=html_ruta, pdf_ruta=pdf_ruta, log=print)
    print(f"\n[=] {len(inv.resultados)} hallazgos. Verifica cada uno antes de darlo por bueno.")
    return 0


def _preg(texto: str, defecto: str = "") -> str:
    suf = f" [{defecto}]" if defecto else ""
    try:
        r = input(f"  {texto}{suf}: ").strip()
    except EOFError:
        return defecto
    return r or defecto


def _preg_si(texto: str) -> bool:
    return _preg(texto).lower() in ("s", "si", "sí", "y", "yes")


# --------------------------- subcomandos rápidos ----------------------------

def cmd_usuario(args) -> int:
    print(f"[*] Enumerando alias: {args.alias!r}")
    resultados = UsernameColector().buscar(usuario=args.alias)
    _auditar("usuario", args.alias, ["usuario"], args)
    _emitir_simple(resultados, args, {"alias": args.alias})
    return 0


def cmd_telefono(args) -> int:
    print(f"[*] Analizando teléfono: {args.numero!r} (región: {args.region})")
    resultados = PhoneColector().buscar(numero=args.numero, region=args.region)
    _auditar("telefono", args.numero, ["telefono"], args)
    _emitir_simple(resultados, args, {"numero": args.numero})
    return 0


def cmd_email(args) -> int:
    print(f"[*] Analizando correo: {args.correo!r}")
    resultados = EmailColector().buscar(email=args.correo)
    _auditar("email", args.correo, ["email"], args)
    _emitir_simple(resultados, args, {"correo": args.correo})
    return 0


def cmd_imagen(args) -> int:
    print(f"[*] Extrayendo EXIF de: {args.ruta!r}")
    resultados = ExifColector().buscar(ruta=args.ruta)
    _auditar("imagen", args.ruta, ["exif"], args)
    _emitir_simple(resultados, args, {"ruta": args.ruta})
    return 0


# --------------------------- parser -----------------------------------------

def _globales(p, con_informe=False) -> None:
    p.add_argument("--json", metavar="RUTA", help="exportar resultados a JSON")
    p.add_argument("--html", metavar="RUTA", help="exportar informe HTML")
    if con_informe:
        p.add_argument("--pdf", metavar="RUTA", help="exportar informe PDF con grafo")
        p.add_argument("--grafo", metavar="RUTA.png", help="guardar el grafo como PNG")
    p.add_argument("--operador", help="analista (para el log de auditoría)")
    p.add_argument("--no-audit", action="store_true", help="no registrar la consulta")


def _args_persona(sp) -> None:
    sp.add_argument("--nombre", help="nombre (precisa la consulta a INTERPOL)")
    sp.add_argument("--apellido", help="apellido (precisa la consulta a INTERPOL)")
    sp.add_argument("--nacionalidad", help="código ISO de país, p. ej. ES, FR")
    sp.add_argument("--edad-min", type=int, dest="edad_min")
    sp.add_argument("--edad-max", type=int, dest="edad_max")
    sp.add_argument("--incluir-rojos", action="store_true",
                    help="incluir también Avisos Rojos (buscados)")
    sp.add_argument("--imagen-url", dest="imagen_url",
                    help="URL pública de una foto para búsqueda inversa")
    sp.add_argument("--region", default="ES", help="región telefónica por defecto (ISO)")


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rastro",
        description="RASTRO — herramienta OSINT de terminal para localizar personas "
                    "(fuentes públicas).",
        epilog="Ejemplos:\n"
               "  rastro interactivo\n"
               "  rastro persona \"Juan Pérez\" --nacionalidad ES --pdf informe.pdf\n"
               "  rastro buscar --telefono +34600111222 --pdf caso.pdf\n"
               "  rastro buscar --email alguien@dominio.com --html caso.html\n"
               "  rastro usuario juanperez\n"
               "  rastro imagen ./foto.jpg\n",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"RASTRO {__version__}")
    p.add_argument("--no-banner", action="store_true", help="no mostrar el banner")
    sub = p.add_subparsers(dest="comando", required=True)

    # interactivo
    si = sub.add_parser("interactivo", help="modo asistente: te pregunta qué datos tienes")
    si.add_argument("--operador")
    si.add_argument("--no-audit", action="store_true")
    si.set_defaults(func=cmd_interactivo)

    # persona
    sp = sub.add_parser("persona", help="buscar una persona por nombre (+informe/grafo)")
    sp.add_argument("nombre_completo", nargs="?", help="nombre y apellidos")
    _args_persona(sp)
    _globales(sp, con_informe=True)
    sp.set_defaults(func=cmd_persona)

    # buscar (todo-en-uno)
    sb = sub.add_parser("buscar", help="investigación combinada por cualquier dato")
    sb.add_argument("--nombre-completo", dest="nombre_completo")
    _args_persona(sb)
    sb.add_argument("--telefono")
    sb.add_argument("--email")
    sb.add_argument("--alias")
    sb.add_argument("--imagen", help="ruta de foto local (EXIF)")
    _globales(sb, con_informe=True)
    sb.set_defaults(func=cmd_buscar)

    # rápidos
    su = sub.add_parser("usuario", help="enumerar un alias en plataformas públicas")
    su.add_argument("alias"); _globales(su); su.set_defaults(func=cmd_usuario)

    st = sub.add_parser("telefono", help="validar/geolocalizar un número (rápido)")
    st.add_argument("numero"); st.add_argument("--region", default="ES")
    _globales(st); st.set_defaults(func=cmd_telefono)

    se = sub.add_parser("email", help="analizar un correo (rápido)")
    se.add_argument("correo"); _globales(se); se.set_defaults(func=cmd_email)

    sm = sub.add_parser("imagen", help="extraer EXIF/GPS de una imagen local")
    sm.add_argument("ruta"); _globales(sm); sm.set_defaults(func=cmd_imagen)

    return p


def main(argv=None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "no_banner", False):
        print(BANNER)
        print(NOTA_ETICA)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n[!] Interrumpido por el usuario.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
