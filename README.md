# Book Data Extractor Pro

Scraper de catálogos de libros con Python y Playwright. Extrae título, precio,
moneda, disponibilidad y URL, limpia los datos, elimina duplicados y exporta a
Excel (`.xlsx`) y CSV.

Está pensado para funcionar sobre sitios de práctica autorizados como
[books.toscrape.com](https://books.toscrape.com/), no para saltarse protecciones
ni para extraer datos privados.

## Qué demuestra este proyecto

- Separación clara entre extracción, limpieza, exportación y orquestación.
- Esperas reales de Playwright, sin `time.sleep`.
- Precios con `Decimal`, conservando la moneda original.
- Advertencias por datos faltantes en lugar de borrar filas en silencio.
- Registro de fichas fallidas con página, URL e índice; los libros válidos se
  exportan igualmente.
- Deduplicación por URL normalizada.
- Archivos con fecha y hora para no sobrescribir resultados anteriores.
- CSV compatible con Excel (`utf-8-sig`) y mitigación de inyección de fórmulas.
- Pruebas unitarias sin necesidad de internet.
- Mensajes de progreso y resumen final para personas no técnicas.

## Ejemplo de salida

| Título | Precio | Moneda | Disponibilidad | URL | Advertencias |
|---|---:|---|---|---|---|
| A Light in the Attic | 51.77 | £ | disponible | https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html | |
| Tipping the Velvet | 53.74 | £ | disponible | https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html | |
| Un libro sin precio |  | £ | desconocida | https://example.com/libro | precio ausente o inválido; disponibilidad ausente |

Puedes ver un archivo de ejemplo en [`examples/sample_books.csv`](examples/sample_books.csv).

## Requisitos

- Python 3.11, 3.12 o 3.13. El CI prueba 3.12 y 3.13; el entorno de referencia
  usa 3.13.
- Conexión a internet.
- Windows, macOS o Linux.

> Si usas una versión más nueva que 3.13, Playwright puede no tener ruedas
> precompiladas. Usa Python 3.11, 3.12 o 3.13.

## Instalación

### Obtener el código

Con Git:

```bash
git clone https://github.com/Gokublackssj/book-data-extractor-pro.git
cd book-data-extractor-pro
```

Si prefieres no usar Git, descarga el ZIP con **Code → Download ZIP**,
descomprímelo y abre una terminal dentro de la carpeta.

Todos los comandos siguientes se ejecutan desde la raíz del proyecto, donde está
`main.py`.

### Windows (PowerShell)

Los ejemplos usan Python 3.13. Si tienes 3.12 o 3.11, sustituye `3.13` por tu
versión. Para ver qué versiones tienes instaladas:

```powershell
py -0p
```

Si no tienes el lanzador `py`, comprueba `python --version` y usa
`python -m venv .venv` cuando sea 3.11, 3.12 o 3.13.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Si PowerShell bloquea la activación del entorno, ejecuta los comandos con la
ruta directa al Python del entorno, sin activarlo:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe main.py --limit 20
```

### macOS / Linux

Comprueba la versión antes de crear el entorno:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Si `python3` apunta a 3.14 o superior, usa `python3.13`, `python3.12` o
`python3.11` en su lugar.

## Uso

### La forma más fácil (Windows)

Haz doble clic en `iniciar.bat`. El archivo crea el entorno la primera vez,
instala las dependencias y ejecuta el programa con la configuración por defecto.
La ventana se queda abierta al terminar para que puedas leer el resultado.

Para pasarle opciones, abre una terminal en la carpeta y ejecuta:

```bat
iniciar.bat --limit 50
```

### Desde la terminal

Extrae los primeros 20 libros con la configuración por defecto:

```bash
python main.py
```

Extrae 50 libros:

```bash
python main.py --limit 50
```

Extrae sin límite de libros, respetando `--max-pages` (puede tardar varios minutos):

```bash
python main.py --limit 0
```

`--limit` controla cuántos libros se extraen; `--max-pages` controla cuántas
páginas se visitan. Con `--limit 0` no hay tope de libros, pero el recorrido se
detiene al llegar a `--max-pages` (50 por defecto).

Solo CSV, con punto y coma como separador (útil en Excel en español):

```bash
python main.py --limit 30 --format csv --csv-delimiter ";"
```

Muestra el navegador para depurar:

```bash
python main.py --limit 5 --headed --slow-mo 300
```

Guarda en otra carpeta y con otro prefijo:

```bash
python main.py --limit 40 --output-dir resultados --prefix catalogo_libros
```

### Opciones

| Opción | Valor por defecto | Qué hace |
|---|---|---|
| `--site` | `books_toscrape` | Perfil de sitio integrado. |
| `--profile` | — | Archivo JSON con los selectores de un sitio. |
| `--list-sites` | — | Muestra los perfiles integrados y termina. |
| `--url` | URL del perfil | Sobrescribe la URL inicial del perfil. |
| `--limit` | `20` | Máximo de libros. `0` no limita la cantidad, pero `--max-pages` sigue aplicando. |
| `--output-dir` | `output` | Carpeta de salida. |
| `--prefix` | `libros` | Prefijo de los archivos. |
| `--format` | `both` | `both`, `csv` o `xlsx`. |
| `--headed` | desactivado | Muestra el navegador. |
| `--slow-mo` | `0` | Retardo entre acciones de Playwright, en ms. |
| `--timeout` | `20000` | Tiempo máximo por página, en ms. |
| `--max-pages` | `50` | Límite de seguridad de páginas, incluso con `--limit 0`. |
| `--delay` | `500` | Pausa entre páginas, en ms. |
| `--csv-delimiter` | `,` | Separador del CSV. |
| `--verbose` | desactivado | Muestra logs detallados. |
| `--version` | — | Muestra la versión. |

## Adaptar el scraper a otro sitio

No existe un scraper universal: cada sitio tiene su HTML, sus clases y su forma
de paginar. Lo que sí hace este proyecto es separar el **motor** de los
**selectores**. Un perfil de sitio es un conjunto de selectores CSS y una URL
inicial.

### Ver los perfiles integrados

```bash
python main.py --list-sites
```

### Usar un perfil integrado

```bash
python main.py --site books_toscrape --limit 20
```

### Usar un perfil JSON

1. Copia `examples/site_profile.example.json` a un archivo nuevo, por ejemplo
   `mi_sitio.json`.
2. Abre el sitio en el navegador, inspecciona un producto y copia sus selectores.
3. Ejecuta:

```bash
python main.py --profile mi_sitio.json --limit 20
```

Ejemplo de perfil:

```json
{
  "name": "mi_catalogo",
  "description": "Catálogo de ejemplo",
  "start_url": "https://example.com/catalogo",
  "product_selector": ".producto",
  "title_selector": "h2",
  "title_attribute": null,
  "price_selector": ".precio",
  "availability_selector": ".stock",
  "link_selector": "a",
  "link_attribute": "href",
  "next_page_selector": "a.siguiente",
  "next_page_attribute": "href"
}
```

| Campo | Obligatorio | Qué significa |
|---|---|---|
| `name` | Sí | Nombre del perfil. |
| `start_url` | Sí | URL inicial del catálogo. |
| `product_selector` | Sí | Selector que se repite por cada producto. |
| `title_selector` | Sí | Selector del título dentro de cada producto. |
| `title_attribute` | No | Atributo donde está el título (por ejemplo `title`). Si se omite, se usa el texto. |
| `price_selector` | No | Selector del precio. Si falta, el precio queda vacío y se advierte. |
| `availability_selector` | No | Selector de disponibilidad. Si falta, queda `desconocida`. |
| `link_selector` | No | Selector del enlace. Si falta, se usa `title_selector`. |
| `link_attribute` | No | Atributo del enlace. Por defecto `href`. |
| `next_page_selector` | No | Selector del enlace a la página siguiente. Si falta, solo se extrae una página. |
| `next_page_attribute` | No | Atributo del enlace siguiente. Por defecto `href`. |

### Cómo encontrar los selectores

1. Abre el sitio en Chrome o Edge.
2. Pulsa `F12` y entra en **Elements**.
3. Inspecciona una tarjeta de producto.
4. Haz clic derecho sobre el elemento, elige **Copy** → **Copy selector**.
5. Prueba el selector en la consola:

```javascript
document.querySelectorAll("article.product_pod")
```

Debe devolver una lista con todos los productos de la página. Si devuelve una
lista vacía, el selector está mal.

### Limitaciones de este enfoque

- Solo funciona con sitios que muestran los productos en el HTML inicial.
- La paginación debe ser un enlace; no cubre scroll infinito ni botones
  “Cargar más”.
- No maneja login, cookies, captchas ni interacciones complejas.
- Si el sitio cambia sus clases, el perfil deja de funcionar y hay que
  actualizarlo.

Eso no es un defecto del proyecto: es la realidad del scraping. Prometer “sirve
para cualquier web” sin matices es vender humo.

## Formato de los datos

| Columna | Tipo | Notas |
|---|---|---|
| `Título` | Texto | Puede estar vacío si el sitio no lo entrega. |
| `Precio` | Número | Vacío si no se pudo interpretar. No se inventa. |
| `Moneda` | Texto | Símbolo original (`£`, `$`, `€`). No se convierte. |
| `Disponibilidad` | Texto | `disponible`, `agotado` o `desconocida`. |
| `URL` | Texto | URL absoluta del producto. |
| `Advertencias` | Texto | Problemas separados por `; `. Vacío si todo está bien. |

Los archivos se guardan como:

```text
output/libros_2026-10-18_143000.xlsx
output/libros_2026-10-18_143000.csv
```

Si ejecutas dos veces en el mismo segundo, se añade un sufijo (`_01`, `_02`…)
para no sobrescribir nada.

## Cómo funciona

```text
main.py
├── config.py      Valores por defecto y contrato de columnas
├── sites.py       Perfiles de sitio: selectores CSS y URL inicial
├── scraper.py     Motor genérico: Playwright, paginación, extracción y fallos
├── cleaning.py    Precios, moneda, disponibilidad, validación y duplicados
└── exporter.py    CSV y Excel, nombres con fecha, estilos y seguridad
```

Flujo:

1. `main.py` lee los argumentos y resuelve el perfil de sitio.
2. `main.py` construye un `Config` con la URL y los límites.
3. `scraper.py` abre Chromium, espera el selector de productos del perfil,
   recorre la paginación y registra las fichas que no pudo extraer.
4. `cleaning.py` convierte precios a `Decimal`, normaliza la disponibilidad y
   añade advertencias.
5. `cleaning.py` elimina duplicados por URL normalizada.
6. `exporter.py` escribe CSV y Excel con nombres únicos.
7. `main.py` muestra cuántas fichas se extrajeron y cuántas fallaron, además de
   la ruta absoluta de cada archivo.

La limpieza y la exportación no dependen de Playwright, así que se pueden probar
sin abrir un navegador.

## Pruebas

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Si no activaste el entorno en Windows, usa
`.\.venv\Scripts\python.exe -m pytest`.

Las pruebas cubren:

- precios con `£`, `$`, `€`, comas, puntos y valores vacíos;
- precios `0.00` (no se confunden con datos ausentes);
- disponibilidad en varios idiomas;
- títulos y URLs nulos;
- deduplicación por URL y por título;
- perfiles de sitio: campos obligatorios, campos desconocidos y carga de JSON;
- exportación CSV/XLSX, encabezados, filas vacías y delimitador `;`;
- mitigación de inyección de fórmulas;
- nombres de archivo que no se sobrescriben;
- fallos por ficha: página, URL, índice y mensaje corto;
- resumen de extracción con libros válidos y fichas fallidas;
- truncamiento por `--max-pages`: final exacto, página siguiente disponible y
  `--limit 0`.

La prueba de integración con el sitio real está desactivada por defecto. Para
ejecutarla:

```powershell
$env:RUN_INTEGRATION="1"
python -m pytest tests/test_scraper_integration.py
```

```bash
RUN_INTEGRATION=1 python -m pytest tests/test_scraper_integration.py
```

## Solución de problemas

| Problema | Solución |
|---|---|
| `playwright: command not found` | Usa `python -m playwright install chromium`. |
| `No module named playwright` | Estás usando otro Python. Activa `.venv` o ejecuta `.\.venv\Scripts\python.exe main.py`. |
| Error de timeout | Aumenta `--timeout 40000` y prueba `--headed` para ver qué carga. |
| No se encontraron libros | Revisa la URL, la conexión y si el HTML del sitio cambió. |
| La extracción parece incompleta con `--limit 0` | Revisa si el resumen avisó de `--max-pages` y súbelo con `--max-pages` si necesitas más páginas. |
| El Excel no se guarda | Ciérralo si está abierto en Excel y vuelve a intentar. |
| Los acentos se ven mal en CSV | Abre el `.xlsx` o importa el CSV como UTF-8. |
| Todo el CSV cae en una columna | Usa `--csv-delimiter ";"` o importa el CSV manualmente. |
| PowerShell no deja activar `.venv` | Usa `.\.venv\Scripts\python.exe ...` sin activar. |
| OneDrive va lento o sincroniza miles de archivos | Excluye `.venv/` de OneDrive o crea el entorno fuera de la carpeta sincronizada. |

## Seguridad y ética

- Usa el programa solo en sitios que autorices o que sean de práctica.
- Respeta `robots.txt`, los términos del sitio y el rate limiting. El valor por
  defecto espera 500 ms entre páginas; no lo bajes sin motivo.
- No uses cookies, sesiones personales ni credenciales reales dentro del
  navegador automatizado.
- El CSV neutraliza celdas que empiezan por `=`, `+`, `-` o `@` para evitar
  inyección de fórmulas al abrirlo con Excel.
- El prefijo de salida se sanea para evitar rutas como `../../archivo`.
- No subas secretos, tokens ni datos privados al repositorio.
- Revisa las licencias y los derechos de uso de los datos que extraigas.
- Si algún día expones esto como servicio web, no aceptes URLs arbitrarias sin
  validar el destino: podrías habilitar SSRF contra tu red interna.

## Decisiones técnicas

- **Perfiles de sitio en lugar de selectores hardcodeados:** cada web tiene su
  HTML. El motor es genérico; los selectores viven en `sites.py` o en un JSON.
- **Playwright en lugar de `requests`:** el sitio puede renderizar contenido con
  JavaScript y Playwright espera a los selectores de forma nativa.
- **`openpyxl` en lugar de `pandas`:** para este volumen de datos no hace falta
  una dependencia tan grande, y `openpyxl` permite dar formato al Excel.
- **`Decimal` en lugar de `float`:** evita errores de redondeo en dinero.
- **Advertencias en lugar de borrar filas:** el usuario ve qué falta y decide.
- **Deduplicación por URL normalizada:** es más estable que el título.
- **CSV con `utf-8-sig`:** Excel reconoce las tildes y la `ñ` al abrirlo.
- **Nombres con fecha y hora:** evita sobrescribir resultados anteriores.
- **Headless por defecto:** es más rápido y menos intrusivo; `--headed` queda
  para depurar.
- **Sin conversión de divisas:** limpiar un número no es convertir moneda.

## Estructura del proyecto

```text
book-data-extractor-pro/
├── main.py
├── sites.py
├── scraper.py
├── cleaning.py
├── exporter.py
├── config.py
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── iniciar.bat
├── README.md
├── LICENSE
├── .gitignore
├── .github/
│   └── workflows/
│       └── tests.yml
├── tests/
│   ├── test_cleaning.py
│   ├── test_config.py
│   ├── test_exporter.py
│   ├── test_main.py
│   ├── test_scraper.py
│   ├── test_scraper_integration.py
│   └── test_sites.py
├── examples/
│   ├── sample_books.csv
│   └── site_profile.example.json
├── docs/
│   └── decisiones.md
└── output/
    └── .gitkeep
```

## Roadmap

- Añadir reintentos con backoff para errores de red.
- Permitir configurar todo con un archivo `.env` o YAML.
- Añadir una interfaz gráfica sencilla para usuarios no técnicos.
- Soportar scroll infinito y botones “Cargar más”.
- Añadir un asistente que ayude a crear perfiles de sitio.
- Publicar una demo en video y capturas en el README.
- Añadir cobertura de pruebas y un badge de CI.

## Licencia

MIT. Consulta [`LICENSE`](LICENSE).

## Autor y portafolio

Autor: [Gokublackssj](https://github.com/Gokublackssj).

Book Data Extractor Pro es un proyecto personal de automatización con Python.
Este repositorio forma parte de mi portafolio. Extrae catálogos de libros con
Playwright, limpia los datos y los exporta a CSV y Excel. Está pensado para
sitios de práctica autorizados como `books.toscrape.com`.

- [Perfil de GitHub](https://github.com/Gokublackssj)
- [Repositorio](https://github.com/Gokublackssj/book-data-extractor-pro)
