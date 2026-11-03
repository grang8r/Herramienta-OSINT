# RASTRO  ·  v0.2

Herramienta OSINT de terminal orientada a la **localización de personas desaparecidas**,
con usos secundarios de OSINT general. Solo consulta **fuentes públicas y gratuitas**.

> **Uso previsto y responsable.** Pensada para la búsqueda de personas desaparecidas e
> investigaciones OSINT autorizadas. Trabaja exclusivamente con fuentes abiertas, respeta
> los límites de petición de cada servicio y registra cada consulta en un log de auditoría.
> No incorpora capacidades invasivas (volcados de brechas privadas, de-anonimización de
> cuentas privadas, fuerza bruta de SMTP ni geolocalización en tiempo real). Cada hallazgo
> es una **pista** que requiere verificación humana.

## Novedades v0.2

- **Entrada por teléfono o email** (búsqueda inversa): a partir de un número o correo,
  busca páginas públicas donde aparece y contactos que co-ocurren.
- **Cosecha de contactos**: extrae emails y teléfonos que aparecen en páginas públicas
  asociadas a la persona.
- **Modo asistente** (`interactivo`): te pregunta qué datos tienes y tú respondes.
- **Informe PDF** con **grafo de correlación** y sección de **datos corroborados por
  varias fuentes**.

## Instalación (Fedora / Kali / cualquier Linux con Python 3.9+)

```bash
cd rastro-osint
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m rastro --help
```

> En Kali, si no usas venv: `pip install --break-system-packages -r requirements.txt`

## Uso

### Modo asistente (recomendado para empezar)

```bash
python -m rastro interactivo
```

Te irá preguntando nombre, nacionalidad, teléfono, email, alias y foto (deja en blanco
lo que no tengas), ejecuta la investigación y te ofrece generar el informe (HTML/PDF).

### Investigación combinada por cualquier dato

```bash
# Por nombre, con informe PDF (grafo incluido)
python -m rastro persona "Nombre Apellido" --nacionalidad ES --pdf informe.pdf

# Entrando por teléfono o por email (búsqueda inversa)
python -m rastro buscar --telefono +34600111222 --pdf caso.pdf
python -m rastro buscar --email alguien@dominio.com --html caso.html

# Combinando varios datos en una sola investigación
python -m rastro buscar --nombre-completo "Nombre Apellido" \
    --telefono +34600111222 --alias nombreusuario --pdf caso.pdf --grafo caso.png
```

### Consultas rápidas (una sola fuente)

```bash
python -m rastro usuario nombredeusuario
python -m rastro telefono +34600111222
python -m rastro email alguien@example.com
python -m rastro imagen ./ultima_foto.jpg
```

### Opciones de salida

| Opción | Disponible en | Efecto |
|---|---|---|
| `--json RUTA` | todos | exporta a JSON |
| `--html RUTA` | todos | informe HTML autónomo |
| `--pdf RUTA` | `persona`, `buscar`, `interactivo` | informe PDF con grafo |
| `--grafo RUTA.png` | `persona`, `buscar` | guarda solo el grafo (PNG) |
| `--operador NOMBRE` | todos | registra el analista en auditoría |
| `--no-audit` | todos | no registra la consulta |

Log de auditoría: `~/.rastro/auditoria.jsonl` (configurable con `RASTRO_HOME`).

## Fuentes integradas

| Módulo | Fuente | Clave API |
|---|---|---|
| `interpol` | API pública de Avisos de INTERPOL (amarillos/rojos) | No |
| `noticias` | Google News RSS | No |
| `web` | DuckDuckGo HTML + extracción de contactos de páginas públicas | No |
| `usuario` | Perfiles públicos de ~24 plataformas | No |
| `telefono` | `phonenumbers` (libphonenumber), offline | No |
| `email` | Validación + Gravatar público | No |
| `exif` | Metadatos EXIF/GPS locales (Pillow), offline | No |
| `pivotes` | Dorks, registros oficiales/ONG, imagen inversa | No |

### Nota sobre España

España no expone una API pública consultable de personas desaparecidas. Para el ámbito
español la herramienta se apoya en el módulo de **noticias**, la **cosecha web** y los
enlaces-pivote a CNDES (Ministerio del Interior) y SOS Desaparecidos.

## Grafo y correlación

Cada investigación se modela como un grafo: en el centro el sujeto; alrededor las entidades
encontradas (emails, teléfonos, perfiles, páginas, ubicaciones). Un dato que aparece a
través de **dos o más fuentes distintas** se marca como **correlación**: es la señal más
fiable, porque está corroborada. El PDF incluye el grafo dibujado y la lista de
correlaciones.

## Niveles de confianza

- **alta** — dato estructurado de fuente oficial (p. ej. aviso de INTERPOL, GPS de EXIF).
- **media** — señal fuerte que exige verificación humana.
- **baja** — pista o enlace-pivote para investigación manual.

## Arquitectura

```
rastro/
├── cli.py                 # CLI: interactivo, persona, buscar, + rápidos
├── core/
│   ├── http.py            # sesión HTTP: UA honesto, reintentos, rate-limit
│   ├── model.py           # dataclass Resultado + niveles de confianza
│   ├── collector.py       # clase base Colector
│   ├── extract.py         # extracción de emails/teléfonos de texto
│   ├── graph.py           # grafo de correlación (networkx/matplotlib)
│   ├── investigation.py   # orquesta colectores + construye el grafo
│   ├── audit.py           # log de auditoría JSONL
│   ├── report.py          # salida consola / JSON / HTML
│   └── report_pdf.py      # informe PDF con grafo (reportlab)
└── collectors/
    ├── interpol.py  news.py  web.py  username.py
    ├── phone.py     email.py  exif.py  pivots.py
```

### Añadir una fuente nueva

1. Crea `rastro/collectors/mi_fuente.py` con una clase que herede de `Colector`.
2. Captura siempre errores de red/parseo y devuelve lo que tengas (una fuente caída
   nunca debe tumbar la investigación).
3. Enchúfala en `core/investigation.py` para que alimente el grafo.

## Limitaciones conocidas

- La detección de `usuario` se basa en el código HTTP: puede dar falsos positivos
  (homónimos) y negativos (plataformas que bloquean peticiones automáticas).
- Las redes sociales suelen eliminar el EXIF: si la foto pasó por una red, probablemente
  no tendrá GPS.
- La cosecha web y la búsqueda inversa dependen del buscador (DuckDuckGo HTML); si cambia
  su formato, el parser puede devolver menos resultados.
- Las fuentes abiertas cambian: si un módulo deja de devolver datos, probablemente la
  fuente modificó su formato.
