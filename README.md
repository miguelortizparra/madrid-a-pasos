# Madrid también se recorre con pausas

Autor: Miguel Ortiz Parra

Story Map independiente basada en el inventario de bancos y la estructura demográfica del Geoportal de Madrid. Los mapas incorporan extractos de la Ortofoto actualizada: cobertura general 2025, resolución de origen 10 cm; exterior municipal 2023.

## Abrir y publicar

Abre index.html en un navegador. Los mapas e interacciones funcionan sin conexión; los enlaces oficiales requieren conexión.

Para GitHub Pages, crea un repositorio público y sube el contenido de esta carpeta a la raíz, conservando las subcarpetas. En Settings > Pages, selecciona Deploy from a branch, rama main y carpeta / (root). La URL habitual es https://TU-USUARIO.github.io/madrid-a-pasos/.

## Documentación

La carpeta descargas contiene el resumen visual en PDF, resultados CSV, geometrías GeoJSON y resúmenes JSON. Los ZIP de entrada están en datos. Ortofoto conserva los extractos JPEG, la respuesta GetCapabilities y los parámetros WMS. Código y dependencias están en codigo.

## Reproducibilidad

Crea una carpeta entregable al mismo nivel que datos y copia codigo/analizar.py en ella. Instala las dependencias de codigo/requirements.txt y ejecuta python entregable/analizar.py. El código regenera mapas, CSV, GeoJSON, resumen y control de la malla. Si cambias entradas o parámetros, actualiza los resultados y la narración.

## Alcance y fuentes

La proximidad se calcula en línea recta sobre una muestra territorial. No equivale a tiempos andando ni habitantes atendidos. Los datos municipales y sus condiciones de reutilización se identifican en FUENTES.md. La autoría del análisis y la narración corresponde a Miguel Ortiz Parra. La publicación en GitHub no implica validación municipal del estudio.

## Navegación de los mapas
Cada mapa incluye botones +, − y restablecer vista. Zoom de 1× a 8×, arrastre, pellizco táctil y Ctrl + rueda. Teclado: +/−, flechas e Inicio. El zoom amplía la ortofoto incorporada; no descarga teselas de mayor resolución.

La cabecera incorpora el escudo y marca Madrid y el logotipo Geoportal de la web oficial. La historia conserva la autoría de Miguel Ortiz Parra.
