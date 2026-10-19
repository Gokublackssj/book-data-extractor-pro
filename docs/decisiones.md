# Decisiones técnicas

Este documento explica el **por qué** de las decisiones importantes. Sirve para
que el proyecto no sea una caja negra y para que puedas defenderlo en una
entrevista o con un cliente.

## 1. Playwright en lugar de `requests` + BeautifulSoup

**Decisión:** usar Playwright con Chromium.

**Motivo:** Playwright espera a que los elementos existan y permite interactuar
con páginas que renderizan contenido con JavaScript. Además, su sistema de
esperas evita los `time.sleep` frágiles.

**Alternativa descartada:** `requests` es más liviano, pero no ejecuta
JavaScript y obliga a replicar la paginación a mano.

## 2. `openpyxl` en lugar de `pandas`

**Decisión:** escribir CSV con la librería estándar `csv` y Excel con
`openpyxl`.

**Motivo:** para decenas o cientos de filas, `pandas` es una dependencia grande.
`openpyxl` permite controlar estilos, anchos, filtros y formato numérico sin
cargar todo el ecosistema de análisis de datos.

**Alternativa descartada:** `pandas` sigue siendo válido si el proyecto crece
hacia análisis de datos, pero no es necesario para exportar.

## 3. `Decimal` en lugar de `float` para precios

**Decisión:** convertir los precios a `Decimal` y redondear a dos decimales.

**Motivo:** `float` representa algunos decimales de forma aproximada. Para
dinero, `Decimal` evita sorpresas como `0.1 + 0.2 != 0.3`.

**Importante:** no se convierte la moneda. Limpiar `£51.77` a `51.77` no es lo
mismo que convertir libras a euros.

## 4. Advertencias en lugar de eliminar filas

**Decisión:** conservar las filas con datos faltantes y añadir una columna
`Advertencias`.

**Motivo:** borrar una fila en silencio oculta un problema. El usuario necesita
saber si faltó el precio, el título o la URL. La especificación del proyecto
pide expresamente no inventar datos.

**Alternativa descartada:** descartar filas inválidas y mostrar solo un conteo.
Se pierde información útil para diagnosticar el sitio.

## 5. Deduplicación por URL normalizada

**Decisión:** usar la URL como identificador principal; si no existe, usar
título + precio + moneda.

**Motivo:** la URL del producto es más estable que el título, que puede repetirse
o cambiar de formato. Se normaliza para que `.../libro/1` y `.../libro/1/` se
consideren el mismo producto.

**Cuidado:** las filas sin URL ni título no se deduplican entre sí, porque no
hay forma segura de saber si son el mismo libro.

## 6. CSV con `utf-8-sig`

**Decisión:** escribir el CSV con BOM UTF-8.

**Motivo:** Excel en Windows reconoce así las tildes y la `ñ` al abrir el
archivo con doble clic.

**Contrapartida:** algunos parsers ven un carácter invisible al inicio. Es un
intercambio consciente a favor de la usabilidad para el cliente final.

## 7. Mitigación de inyección de fórmulas

**Decisión:** en CSV, prefijar con `'` las celdas que empiezan por `=`, `+`, `-`
o `@`. En Excel, forzar el tipo texto cuando una cadena empieza por `=`.

**Motivo:** Excel puede interpretar una celda como fórmula al abrir un CSV. Un
título malicioso como `=HYPERLINK(...)` no debe ejecutarse. Es una medida
sencilla y visible; se documenta para que el usuario sepa por qué aparece el
apóstrofo.

## 8. Nombres de archivo con fecha y hora

**Decisión:** generar nombres como `libros_20261018_143000.xlsx`.

**Motivo:** evita sobrescribir resultados anteriores por accidente y permite
comparar ejecuciones. Si dos ejecuciones coinciden en el mismo segundo, se añade
un sufijo numérico.

## 9. Headless por defecto

**Decisión:** el navegador no se muestra salvo que se use `--headed`.

**Motivo:** es más rápido, consume menos recursos y es lo que espera un usuario
que solo quiere el archivo. `--headed` y `--slow-mo` quedan para depurar.

## 10. Rate limiting y user-agent honesto

**Decisión:** esperar 500 ms entre páginas por defecto y identificarse con
`BookDataExtractorPro/1.0`.

**Motivo:** no martillar el servidor y no hacerse pasar por un navegador real.
El scraping debe ser respetuoso y autorizado.

## 11. Validación de URL y saneamiento del prefijo

**Decisión:** aceptar solo `http://` y `https://`, y limpiar el prefijo de salida.

**Motivo:** evitar entradas absurdas y rutas como `../../archivo` que escriban
fuera de la carpeta `output/`.

## 12. Perfiles de sitio en lugar de selectores hardcodeados

**Decisión:** mover los selectores CSS y la URL inicial a `sites.py`, con la
posibilidad de cargar un perfil desde JSON con `--profile`.

**Motivo:** cada sitio tiene su HTML. Si los selectores viven dentro de
`scraper.py`, adaptar el programa a otro catálogo obliga a tocar el motor y a
volver a probarlo todo. Con un perfil, el motor se mantiene igual y solo cambia
la configuración.

**Alternativa descartada:** intentar un scraper “universal” que adivine los
selectores. No es fiable: los sitios cambian, muchos cargan con JavaScript y no
hay una estructura HTML común.

**Limitación:** el perfil actual asume una lista de productos y paginación por
enlace. Scroll infinito, botones “Cargar más” o login quedan fuera de esta
versión.

## 13. Resultado de extracción con fallos

**Decisión:** `scraper.scrape_catalog()` devuelve un `ScrapeResult` con
`libros`, `fallos`, `paginas` y `truncado_por_max_pages`. Cada fallo es un
`FalloExtraccion` con `pagina`, `url_pagina`, `indice` (1-based) y un `mensaje`
corto. `scrape_books()` se mantiene como envoltorio compatible que devuelve solo
`list[dict]`.

**Motivo:** antes, un fallo por ficha se registraba en el log y se perdía. Ahora el
programa puede informar cuántas fichas fallaron sin romper la API que ya usan el
resto del código y las pruebas. Si hay libros válidos, se exportan igualmente; si
todas las fichas fallan, no se generan archivos vacíos y se devuelve código 1.
`paginas` y `truncado_por_max_pages` permiten distinguir un catálogo completo de
uno cortado por el límite de seguridad.

**Alternativa descartada:** añadir columnas o un archivo de fallos. Habría cambiado
el contrato de exportación y la estructura del CSV/XLSX. Los fallos quedan en el
resultado y en los logs; una exportación específica puede añadirse más adelante.

## 14. `--limit` y `--max-pages` son límites distintos

**Decisión:** `--limit 0` significa “sin límite de libros”, pero `--max-pages`
sigue aplicando como límite de seguridad de páginas. El aviso de extracción
incompleta se muestra solo cuando se alcanza `--max-pages` y todavía existía una
página siguiente.

**Motivo:** contar páginas y contar libros son cosas distintas. Un catálogo puede
terminar justo en la última página permitida; en ese caso no hay nada incompleto y
avisar sería un falso positivo. Antes se avisaba siempre que `paginas >= max_pages`,
aunque no hubiera más páginas.

**Alternativa descartada:** hacer que `--limit 0` desactivara también `max_pages`.
Eso eliminaría una protección contra recorrer un catálogo enorme por accidente y
haría impredecible el tiempo de ejecución.

**Efecto:** el resumen muestra las páginas recorridas, y solo avisa de posible
extracción incompleta cuando de verdad quedaban páginas por visitar.

## 15. Lo que se dejó fuera a propósito

- **Bypass de captchas o protecciones:** no es el objetivo y puede violar
  términos de uso.
- **Conversión de divisas:** requiere una fuente externa y cambia el significado
  del dato.
- **Base de datos:** para este volumen, archivos planos son suficientes.
- **GUI:** primero se valida el flujo por consola; la interfaz puede venir
  después.
- **Reintentos complejos:** se pueden añadir cuando el proyecto lo necesite, no
  antes.

## Cómo usar este documento

Cuando cambies una decisión, añade una entrada nueva con:

1. Qué cambiaste.
2. Por qué.
3. Qué alternativa descartaste.
4. Qué efecto tiene en los usuarios.

Eso es lo contrario del vibe coding: dejar rastro del criterio.
