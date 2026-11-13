<!-- translated from docs/SPEC.md @ a658d8254020 -->
# gs-mapedit: especificación del editor y plan de construcción

*Esta es una traducción del documento en inglés [SPEC.md](../SPEC.md); si los dos difieren, el inglés es el actualizado.*

Alcance: un editor de mapas para **Golden Sun: The Broken Seal** construido sobre el árbol de código fuente de alchemy. Abarca los **mapas locales** (pueblos, mazmorras, interiores) y el **mapa del mundo**. The Lost Age comparte el formato de mapa local, así que vendrá después con poco coste. Su motor del mapa del mundo sigue siendo sobre todo ensamblador en alchemy.

El editor lee y escribe solo los archivos fuente de alchemy: TSV, PNG y zonas acotadas de tablas en C/asm. Nunca toca una ROM. Las pruebas detalladas, con referencias file:line, están en `docs/research/` (`rendering.md`, `local-connections.md`, `overworld.md`). Este archivo enuncia las decisiones.

## Reglas básicas

1. **Ida y vuelta idéntica byte a byte.** Cargar y guardar cualquier cosa sin editar debe reproducir el archivo byte a byte. Cada tipo de archivo tiene una prueba de ida y vuelta sobre todo el árbol. Una compilación sin editar debe seguir dando OK en `compare`.
2. **Editar en el sitio; añadir al final, no insertar.** Las posiciones de las filas de una tabla son identidades. Número de actor = 8 + fila de colocación. Id de escena = fila en `scenes.s`. Las tablas de salidas usan números de escena simples. Insertar una fila renumera cosas sin avisar, así que las filas nuevas van al final.
3. **Validar antes de guardar.** Cada operación tiene invariantes (abajo). El editor se niega a guardar un estado que rompa uno, o lo señala claramente.
4. **La compilación es el juez.** Después de guardar, ejecuta `make tbs-en`. El editor muestra los errores de compilación. Una prueba de juego en mGBA es la comprobación final.
5. **Fijar alchemy.** Trabajar con un commit conocido. Antes de pasar a uno nuevo, ejecuta `tests/roundtrip.py` y la comprobación de renderizar todo (unos 2 minutos). Detectaron de inmediato la reestructuración de rutas del 19 de octubre.

## Mapas locales

### Renderizado (implementado, verificado en los 182 mapas)

- **Recursos:** la paleta, los bloques de caracteres 1–3 y la hoja D de cada mapa vienen de su fila de `gMaps` (`map/maps.c`), resueltos mediante el `gamepak/resource_directory.s` expandido. Los mapas 001, 002, 108 y 110 tienen filas alternativas.
- **Marcadores de posición:** la k-ésima celda `0xfff`, en orden por filas sobre toda la cuadrícula de 128×128, es el bloque k con su nibble superior conservado (`field/map_grid_convert.s`). El número de marcadores de posición es igual al número de filas de `metatiles.tsv` en los 182 mapas.
- **Ventanas:** la ventana de cada capa empieza en el origen de la capa más los límites de la cabecera y da la vuelta en 128.
- **Pendiente:**
  - composición de mezcla (`blend.tsv`: BLDCNT/BLDALPHA/BLDY);
  - animación de tiles (`animation.tsv`, hoja D);
  - anclaje del paralaje para los mapas 047, 103, 104, 147 y 148;
  - límites de cámara opcionales a partir de las entradas de escena.

  Las reglas están en `rendering.md`.

### Datos editables e invariantes

| Cosa | Archivo | Edición | Invariantes / notas |
|---|---|---|---|
| Bloques por celda (3 capas) | `map.txt`, la imagen de cada celda | pintar ids de bloque resueltos | Se guarda con el **codificador de marcadores de posición**: recorre por filas con un contador k. Una celda cuyo bloque == k se escribe `0xfff` (con el nibble superior conservado) y k++; las demás celdas se escriben explícitamente. Verificado como el inverso exacto en los 182 mapas. |
| Definiciones de bloques | `cell_pictures.tsv` | añadir al final nuevas combinaciones de 2×2 tiles | Máximo 4.095 bloques. Número de fila = id de bloque. |
| Códigos de colisión | `map.txt`, el comportamiento de cada celda | pintar | Por ventana de capa. Los códigos 1–239 pueden llevar eventos (salidas, cofres). |
| Altura / forma | `map.txt`, la forma de cada celda, + `shapes.tsv` | pintar | Por ventana de capa. |
| Cofres / Piedras de Psinergía | líneas `treasure_spot x, z, id` en `map.s` | añadir/mover/quitar | **el id debe ser igual al código de colisión en (x, z)**: verificado 418/418. Máximo 10 por mapa. Fila marcadora final `ff ff ff`. El contenido necesita un evento `SEARCH(SEARCH_CHEST)` en la escena con un indicador nuevo. |
| Animación de tiles | `animation.tsv` | más adelante | 16 canales como máximo. |

Archivos compartidos: los bloques pueden venir de la carpeta de otro mapa, y las celdas y atributos de `default/` también se comparten. El editor muestra cuándo un archivo está compartido y avisa antes de editarlo.

### Tablas de escena: un gancho, sustituciones propias del editor

**Diseño (indicación del dueño): cambios mínimos en los archivos de alchemy.**
- El motor lee cada tabla de escena a través de `gOverlayArea`, la tabla de entrada del overlay de la escena en RAM. Los overlays se cargan en un único sitio: `Scene_LoadOverlay` (`system/main_routine.c`).
- El editor añade **una línea** ahí, `MOD_SCENE_LOADED(gMainRoutineWork.next, &gOverlayArea);`. Es una macro que no se expande a nada salvo que la compilación defina `GSMOD`, así que la compilación original sigue coincidiendo con la comercial.
- Con `GSMOD`, la macro llama a código generado por el editor en `games/tbs/src/mod/`. Ese código cambia los punteros a función de la tabla de entrada (entradas, salidas, colocaciones, eventos, regiones) por funciones que devuelven las tablas de sustitución del editor para esa escena, y deja el resto tal cual.
- El mapa del mundo también es un overlay de escena, así que el mismo gancho abarca los iconos, salidas y eventos del mapa del mundo.
- Los archivos `.c` de escena nunca se reescriben. Las tablas de sustitución viven en la carpeta del mod, en la ROM. Los archivos de datos puros (tablas de mapa, líneas de cofres) se siguen editando directamente.

Las tablas subyacentes, como referencia:

Las escenas están en `games/tbs/src/scene/<place>.c`. Contienen cinco tipos de tabla, todos arrays de C a nivel de archivo con literales y macros:

| Tabla | Cantidad | Campos de fila |
|---|---|---|
| Entradas | 189 | entrada, required_flag, x, y, z, orientación, límites de cámara |
| Salidas | 99 | tipo → (escena, entrada), indicador opcional |
| Colocaciones | 274 | sprite, condición, comportamiento, x, y, z, orientación, orientación al hablar, indicadores |
| Eventos | 263 | tipo/control, activador, condición, valor |
| Regiones | 14 | caja mín/máx, condición, tipo de salida |

El editor *lee* estos arrays de los archivos `.c` de escena, iniciando una sustitución con las filas originales de una escena, y *escribe* solo las copias de sustitución en `mod/`. Eventos: decodificar las palabras de control conocidas y conservar tal cual las desconocidas (unas 220 están en hexadecimal en bruto).

Validación:
- La entrada de destino de cada salida existe en la escena de destino.
- Las filas de colocación no se insertan a mitad de tabla (desplazamiento de números de actor).
- El tamaño del overlay se mantiene por debajo de 32 KB (al más grande le quedan 120 B libres).
- Las filas con x=z=0 las coloca el código; el editor las marca como de solo lectura.

El grafo de salidas es: código de colisión / script / región → tipo de salida → tabla de salidas → (escena, entrada) → fila de entrada. El editor lo muestra como enlaces clicables entre mapas.

### Mapas nuevos (última etapa)

La lista de comprobación está en `local-connections.md` §6:
- 25 huecos libres en el directorio de recursos, fijados en 0x08320000;
- añadir filas al final de `gMaps` (`map/maps.c`) y `scenes.s`;
- añadir la fila del mapa a `ld_script.ld` antes de los overlays, más el overlay, la música, el nombre de zona y las reglas de encuentros;
- grupo ≤ 0x7f, ids de escena < 511.

**El espacio en la ROM es el verdadero límite:** de 3,5 a 43 KB libres al final de los 8 MB, según la edición. Un mapa nuevo de verdad probablemente implique hacer crecer la ROM por encima de 8 MB, algo sin probar.

## Mapa del mundo

| Cosa | Archivo | Notas |
|---|---|---|
| Celdas de suelo + capa superpuesta | `map/world/blocks.tsv` | 320×512 u32. Los trozos son de 16×16 celdas, dispuestos de 32 en ancho en el TSV y de 16×16 en el mundo. Suelo = trozo c, capa superpuesta = c + 320. Alternativos 256–319 (conjunto de nieve, puente de la historia). Bits de celda: 0–15 bloque, 16–23 código de paso/evento, 24–30 tipo de terreno (= región de encuentros), 31 banco de comportamiento. |
| Bloques | `map/default/cells.tsv` | 4.386 × 4 bytes de tile. **Compartido con los mapas locales.** Mejor añadir al final. |
| Zonas de paso | `map/default/attributes.tsv` | Por tile de 8×8, 4×4 nibbles. Gana la capa superpuesta, luego el suelo, si no 7. Los valores 5–12 son transitables. También compartido. |
| Gráficos | `graphics/world_map/*.png` | 8bpp, 256 tiles por capa, 224 colores. El conjunto B es el norte nevado. Conservar el modo y los índices del PNG. |
| Iconos de pueblo / entrar | `scene/world_map.c` `gWorldMapPlacements`, `gWorldMapEvents`, `gWorldMapExits` | Icono = actor 8 + fila. Tocarlo dispara el activador 100 + actor → `EVENT_EXIT` → salida → (escena, entrada). Algunas entradas son códigos de paso en su lugar. Debe mantenerse alineado con `gWorldMap_PlaceMarkers` (actor 11 + i). |
| Salir al mundo | `gWorldMapEntrances` | El `SCENE_EXIT(n, 2, e)` de un pueblo coloca al grupo en la fila e. |
| Encuentros | reglas de `object/zonedata.c` → zonas de `object/encounter.tsv` | Tipo de terreno + comportamiento → regla → zona (104 filas fijas). |

Salvedades:
- El mapa de la pantalla de pausa (`picture.png`) es arte aparte, así que hay que repintarlo a mano después de editar la costa.
- No hay variantes del mapa del mundo por idioma en TBS.
- El mapa del mundo de The Lost Age es distinto (2048 trozos, 32×32) y su motor es sobre todo ensamblador, así que queda fuera del alcance hasta que alchemy lo reproduzca.

## Plan de construcción

| Etapa | Entrega | Verificación |
|---|---|---|
| **1. Visor** ✅ | Los 182 mapas locales renderizados correctamente; capas; información al pasar el ratón | ida y vuelta de 895 archivos; renderizar todo; comprobaciones visuales |
| **1b. Fidelidad del renderizado** | Composición de mezcla, tiles animados (reproducir/fotograma), anclaje del paralaje, recorte por límites de cámara | Comparar con los renderizados validados de `rendering.md`; idealmente capturas de mGBA |
| **2. Pintado local** ✅ salvo el compositor de bloques nuevos | Paleta de bloques a partir del atlas; pintar por capa; pinceles de colisión/altura; compositor de bloques nuevos (elegir 4 tiles); deshacer/rehacer; guardar con el codificador de marcadores de posición | Guardado sin editar idéntico byte a byte; guardado editado que compila (`make tbs-en`); arranca en mGBA |
| **3. Marcadores + tablas de escena** ✅ añadir, rellenar, mover y quitar cofres; puertas enlazadas con un clic (reenlazar, añadir, quitar, puertas con script incluidas); eventos en palabras con líneas nuevas, letreros, mensajes al pisar, personas y condiciones; zonas de salida; mover piedras; entradas, PNJ, salidas | Colocación de cofres/piedras (marcador + colisión + evento); edición de entradas/salidas/colocaciones; navegación del grafo de salidas entre mapas | Ida y vuelta de tablas idéntica byte a byte en las 201 escenas; compilación; probar en juego un cambio de salida |
| **4. Visor del mapa del mundo** ✅ | Mundo visto desde arriba con los conjuntos A/B, capa superpuesta, zonas de paso, capa de tipo de terreno/encuentros, iconos de pueblos y enlaces de salida | Portar el prototipo de investigación; comparar con `world_mixed_small.png` |
| **5. Edición del mapa del mundo** ✅ bloques de suelo/capa superpuesta, regiones, mover iconos y enlaces; códigos de paso, zonas de encuentros e iconos nuevos todavía pendientes | Pintar celdas (bloque, tipo de terreno, código de paso); editar iconos, salidas, entradas; zonas de encuentros | Ida y vuelta de `blocks.tsv` y de las tablas; compilación; prueba de juego |
| **6. Mapas / escenas nuevos** | Asistente para la lista de comprobación de mapas nuevos; medidor del espacio en la ROM | Compilación; prueba de juego |

Las etapas 2–3 hacen que el editor local sea realmente útil. Las 4–5 añaden el mapa del mundo. La 6 es la más arriesgada, porque depende del espacio en la ROM.

## Preguntas abiertas

- ~~¿La compilación exige número de marcadores de posición = número de bloques?~~ **No.** Probado: una edición que deja 56 marcadores de posición para 441 bloques compila y enlaza. El codificador escribe explícitamente los bloques posteriores en cuanto se pinta encima de una primera aparición, así que el diff es más grande pero válido. El aspecto dentro del juego todavía necesita una prueba de juego.
- Mapas cuyo `blend.tsv` nunca establece BLDCNT (039, 042, 043, 114, 125): probablemente la mezcla viene del código de escena.
- Qué son los `scene_points` de TLA; qué escribe `touched_trigger`; valores de comportamiento de colocación por encima de 2.
- Si una ROM de más de 8 MB arranca y guarda correctamente en los emuladores y el hardware de destino.
