<!-- translated from docs/research/overworld.md @ 52c37110966a -->
# Investigación del overworld (mapa del mundo): Golden Sun TBS, a partir de las fuentes de alchemy

*Esta es una traducción del documento en inglés [overworld.md](../../research/overworld.md); si los dos difieren, el inglés es el vigente.*

Árbol de fuentes: `~/gs_project/alchemy` (solo lectura). Las rutas de abajo son relativas a
`games/tbs/` salvo que empiecen por `games/` o `tools/`. Etiquetas: **[V]** = VERIFICADO (leído en código o datos,
o confirmado por el render del prototipo), **[I]** = INFERIDO.

Scripts y renders del prototipo (borradores, no forman parte de este repositorio):
`(a scratch folder)`
(`render_world.py`, `render_area.py`, `render_gameplay.py`, `world_mixed.png`, `world_annotated.png`, `collision.png`, `terrain_kind.png`, `north_compare.png`).

## Resumen

1. Todo el suelo del overworld es una sola tabla: `src/map/world/blocks.tsv`, 320 filas x 512 columnas de **palabras de celda** u32 en hexadecimal, que `tools/ags-graphics` (forma `blocks`) compila en `blocks.blocks`, y que `src/map/map.s` incluye con incbin como `Field_PerspectiveDataA` [V].
2. La tabla contiene 640 **chunks** de 16x16 celdas (el código llama "tile" a un chunk). Los chunks 0-319 son la capa 0 (BG3, suelo) y los 320-639 la capa 1 (BG2, superpuesta: montañas, árboles, costa), con chunk de capa 1 = chunk de capa 0 + 320 [V].
3. El mundo mide 16x16 chunks = 256x256 celdas; una celda son 32 píxeles de mundo (16 píxeles de pantalla/BG), así que el mundo mide 8192x8192 px de mundo y da la vuelta (wrap) [V]. Los ids de chunk 0-255 están en el chunk de mundo (id%16, id//16); los 256-319 son alternativas que el código intercambia [V].
4. Una palabra de celda: bits 0-15 id de bloque, bits 16-23 código de paso/evento, bits 24-30 tipo de terreno (región de encuentros; 21 = conjunto gráfico de nieve), bit 31 flag de banco de comportamiento [V].
5. Un id de bloque indexa `src/map/default/cells.tsv` (4386 bloques de 4 bytes: números de tile 8x8 TL, TR, BL, BR) [V]. Los tiles son de 8bpp, 256 por capa: conjunto A = `tiles_a+b` (capa 0) y `tiles_c+d` (capa 1), paleta `palette_a.png` (224 colores); conjunto B (nieve) = `tiles_f..i`, `palette_b` [V].
6. El render usa el modo 2 (BG2+BG3 afines) con matrices por línea de escaneo vía HBlank-DMA para la perspectiva "modo 7"; un render plano desde arriba no necesita nada de eso. El prototipo renderiza correctamente el mapa completo de 4096x4096 píxeles BG [V].
7. La transitabilidad es por tile gráfico de 8x8, no por celda: `default/attributes.tsv` da a cada tile una cuadrícula de 4x4 valores de colisión de 4 bits (la capa superior gana a la inferior; 0 = ninguno; por defecto 7); 5-12 transitables [V].
8. Encuentros aleatorios: tipo de terreno (bits 24-30 de la celda) + comportamiento del terreno (del valor de colisión, banco según el bit 31 / tipo 21) -> `gWorldMap_EncounterRules` (`src/object/zonedata.c`) -> fila de zona de `src/object/encounter.tsv` [V].
9. Pueblos y mazmorras son actores colocados (sprites de icono) en `gWorldMapPlacements` (`src/scene/world_map.c`); tocar el actor N lanza el disparador 100+N, que casa con un `EVENT_EXIT` en `gWorldMapEvents` -> número de salida -> `gWorldMapExits` -> (escena, entrada). Algunas entradas son en cambio códigos de paso de celda (bits 16-23) [V]. Salir de un pueblo usa la tabla de salidas de ese pueblo `SCENE_EXIT(n, 2, e)` -> posición `gWorldMapEntrances[e]` [V].
10. En TBS no hay variantes por edición de ningún dato del mapa del mundo; las direcciones de inicio de la cola de la ROM difieren por edición, y cualquier cambio rompe la coincidencia byte a byte de "compare OK" [V].

## Archivos y formatos

| Dato | Archivo(s) fuente | Formato | Se compila como / se conecta en |
| --- | --- | --- | --- |
| Celdas de suelo, ambas capas | `src/map/world/blocks.tsv` | Sin cabecera. 320 líneas x 512 tokens separados por tabuladores; cada token en hexadecimal en minúsculas sin `0x`, sin ceros a la izquierda (`0`, `1b`, `9500014a`), fines de línea LF, LF final [V]. Lo lee `blocks()` en `tools/ags-graphics/tables.c:235-282`: el número de líneas debe ser múltiplo de 16, todas las filas del mismo ancho (múltiplo de 16) [V]. Un grupo de 16x16 puede ser todo `-` (omitido, offset 0) pero nunca en parte [V; TBS no tiene ninguno, TLA tiene 969]. | `blocks.blocks`: tabla de 640 offsets u32, y luego las 256 palabras u32 de cada chunk (1024 bytes) empaquetadas por separado con LZ de tipo `plz` (`tables.c:262-276`) [V]. `src/map/map.s:1-4` hace `.incbin` como `Field_PerspectiveDataA`, seguido de `.byte 0x01 @ PACKER` [V]. Entrada de directorio `group Field, PerspectiveDataA, ...` en `src/system/resource/directory.s:123` [V]. |
| Numeración de chunks en el TSV | el mismo | El chunk `i` ocupa las filas del TSV `(i//32)*16..+15`, columnas `(i%32)*16..+15` (chunks dispuestos de 32 en ancho, por filas) [V: `tables.c:257`]. Esto NO es la disposición del mundo: el mundo mide 16 chunks de ancho, así que una fila de chunks del TSV contiene dos filas de chunks del mundo una al lado de la otra [V por render]. | |
| Bloques (metatiles) | `src/map/default/cells.tsv` | Cabecera `cell0:u8 ... cell15:u8`; valores `0x6b`; 1097 filas, la última corta (8 valores) = 17544 bytes = 4386 bloques x 4 bytes [V]. El bloque b = bytes `4b..4b+3` = número de tile (u8) arriba-izquierda, arriba-derecha, abajo-izquierda, abajo-derecha [V: `src/field/field/world_map.c:71-91`, `444-451`]. Compartido por ambas capas; la capa selecciona el banco de tiles. | `cells.table.lz`; `map.s:5-7` como `Field_DefaultMapCells` (+1 byte PACKER); decodificado en `Ram_MapCellBuffer` (`gMapCellBuffer`, 0xc000 bytes, `src/system/ewram.s:223-226`) por `world_map.c:158-160` [V]. La misma tabla es también las "celdas por defecto" de los mapas por capas (fila `default/` del README `src/map/README.md`). |
| Colisión de tiles | `src/map/default/attributes.tsv` | Cabecera `attr0:u8..attr15:u8`; 256 filas = 4096 bytes [V]. Bytes 0x000-0x7ff: tiles 0-255 de la capa inferior (BG3), 8 bytes cada uno; 0x800-0xfff: tiles 0-255 de la capa superior (BG2) [V: `src/field/field/terrain.c:535-580`]. Por tile: 4 filas x 2 bytes; cada byte contiene dos valores de 4 bits, nibble bajo = izquierda; un valor = 2x2 px BG (4x4 px de mundo). | `attributes.table.lz`, `map.s:11-13` `Field_DefaultMetatileAttributes`; decodificado en `Ram_MapCollision` (`world_map.c:161-163`) [V]. |
| Animación de tiles | `src/map/default/animation.tsv` | Cabecera `word0:u16..word7:u16`, 465 medias palabras; script de canales (canal `0xfdNN`, grupos tile fuente/cantidad/tile destino/fotogramas, salto `0xfeNN`, parada `0xfeff`, bucle `0xffff`) [V: `src/field/field/map_animation.c:7-13`]. Los tiles fuente >= 0x600 vienen de `gMapLayerData` (= `tiles_e`/`tiles_j`) [V: `map_animation.c:57-61`]. | `animation.table.lz`, `map.s:8-10`; decodificado en `Ram_MapCollision+0x1000` e iniciado (`world_map.c:149-152`) [V]. |
| Gráficos de tiles | `src/graphics/world_map/tiles_{a..j}.png` | PNG indexado, valor de píxel = índice de color 8bpp en bruto, paleta del PNG = `palette_*.png` [V]. a-d, f-i: 128x64 (128 tiles cada uno); e, j: 128x128 (256 tiles, fuente de animación) [V]. | `tiles_X.8bpp.lz`, `src/graphics/world_map/worldmap.s` (cada uno seguido de bytes PACKER) [V]. Directorio `directory.s:124-135` (`WorldMapPaletteA`, `WorldMapTilesA..J`) [V]. |
| Paletas | `palette_a.png`, `palette_b.png` | PNG indexado de 16x14 = 224 colores [V]. Se cargan en la paleta BG 0-223, con el color 0 sustituido por el fondo actual (`world_map.c:331-335`) [V]. | `.gbapal.plz` (`worldmap.s:4`, `:26`) [V]. |
| Tabla de conjuntos gráficos | `src/field/world_map_resources.c:11-28` | `gWorldMap_GraphicsResources[2][6]` = {paleta, tiles x5} para el conjunto A (A..E) y el conjunto B (F..J) [V]. | C. |
| Reglas de encuentro por terreno | `src/object/zonedata.c:7-15` | `gWorldMap_EncounterRules[132]` s16: 32 reglas {tipo, comportamiento (-1 cualquiera), flag (-1 ninguno / la regla se desactiva una vez activado), zona} + terminador tipo -1 [V]. | C. |
| Zonas de encuentro | `src/object/encounter.tsv` | Cabecera `rate:u16 level:u16 group0..7:u16 weight0..7:u8 zone` (la última columna es una etiqueta, no se codifica); 104 zonas [V]. | `encounter.table`, `src/object/arcspark.s:10-13` [V]. |
| Comportamiento del terreno | `src/field/mapdata.c:37-41` | `gWorldMap_TerrainBehaviorTable[48]` u8, índice = valor de colisión + banco (0x10 si el bit 31 de la celda, 0x20 si tipo 21) [V]. | C. |
| Tablas de escena | `src/scene/world_map.c` | `gWorldMapEntrances` (`:2717`), `gWorldMapExits` (`:2802`), `gWorldMapPlacements` (`:2863`) + variantes de historia (`:2966-3058`), `gWorldMapEvents` (`:3060`) [V]. Formatos en `include/field_scene.h:54-150` [V]. | Overlay del mapa del mundo 0x371 (`objects.tsv:640-644`), enlazado en 0x2008000, límite de 32 KB (`src/scene/README.md` Limits) [V]. |
| Marcadores del mapa de la pantalla de pausa | `src/object/scripts.s:340-383` | `gWorldMap_PlaceMarkers`: pares {tile<<16 \| flag, nombre de lugar}; la fila i describe al actor 11+i; las filas 0 reservan un actor; -1 termina [V: `src/object/psynergy_effects/world_map.c:282-323`]. | asm `.4byte`. |
| Imagen de la pantalla de pausa | `src/graphics/world_map/picture.png` | 240x160 8bpp, cubre el mundo x 4096-8192, z 0-4096 [V: `psynergy_effects/world_map.c:10-11, 318-322`]. Dibujada a mano, no generada a partir de los bloques [I]. | `src/graphics/title/title.s:68-71` `Field_WorldMapPicture` [V]. |
| Fotogramas de la historia | `src/graphics/world_map/story.png`, `storymap.tsv`, `storypal.png` | Gráficos de las escenas intercaladas de la historia en el overlay del mapa del mundo [V: `story.s`]. No son datos de suelo. | `story.s`, objeto del overlay `objects.tsv:643` [V]. |

Id de escena del mapa del mundo: `scene WorldMap, 0x371, 0x02, 1, 0x01` es la escena 2 (`src/field/scenes.s:17`); id de escena = índice de fila de `gField_SceneTable` (`scenes.s:1-5`) [V]. Su índice de mapa 1 es igual a `SceneId_Clear`, que es lo que selecciona el modo perspectiva en `Field_RunScene` (`src/object/object/run_scene.c:45-49`) [V].

## Render

Jerarquía (TBS) [V]:

```
world (wraps)  16 x 16 chunks                      8192 x 8192 world px, 4096 x 4096 BG px
chunk          16 x 16 cells   (code: "tile")      512 world px, 256 BG px; 1 KB decoded
cell           u32 word, low 16 bits = block id    32 world px, 16 BG px
block          2 x 2 tiles (4 bytes in cells.tsv)  
tile           8 x 8, 8bpp, from bank per layer    16 world px, 8 BG px
```

- **Pantalla**: `Map_InitializePerspectiveScene` (`world_map.c:112-264`) establece BG3 = base de caracteres 2, base de pantalla 8; BG2 = base de caracteres 3, base de pantalla 10; ambos afines de 512x512 px, con wrap (`:164-174`); BG1 es la capa de texto para la vista fija; `DISPCNT_MODE_2` (`:249`) [V]. BG2 se dibuja sobre BG3, con el color 0 transparente (comentario en `view.c:66-69`: BG2 deja ver BG3 donde es transparente) [V].
- **Bancos de tiles**: tiles[1] del conjunto (A) -> bloque de caracteres 2, tiles[2] (B) -> bloque 2 + 0x2000, tiles[3] (C) -> bloque de caracteres 3, tiles[4] (D) -> bloque 3 + 0x2000, tiles[5] (E) -> `gMapLayerData` (`world_map.c:336-352`) [V]. Así, los números de tile 0-127 de la capa 0 = `tiles_a`, 128-255 = `tiles_b`; capa 1: `tiles_c`, `tiles_d` [V por render].
- **Streaming**: los mapas BG contienen una ventana de 2x2 chunks alrededor del jugador. `perspective->tileIds[256]` asigna a cada hueco de chunk del mundo un id de chunk, inicializado a la identidad (`world_map.c:262-263`). `Map_WriteLayerCellTile` decodifica con LZ el chunk `id` (la capa 1 usa `id + 320`, `:298`, `:640`) en el cuarto `(x&1, y&1)` de `Ram_MapBlocks` y escribe los bytes del mapa afín a partir de la tabla de bloques (`:38-95`) [V]. El índice de ventana usa `& 15`, por eso el mundo da la vuelta cada 16 chunks [V].
- **Perspectiva**: `WorldMap_BuildScanlineTable` (`src/field/field/view.c`) + la rutina ARM `Transform_UpdateVertices` construyen un par afín (BG2/BG3 PA..Y) por línea de escaneo; `MapAnimation_ApplyAffineFrame` carga la línea 0 y envía el resto con HBlank-DMA (`world_map.c:386-441`) [V]. Inclinación por defecto 0xe000 (-1/8 de vuelta), plano lejano 0x1fe0000, centro (120,96) (`:198-249`) [V]. Una vista de editor desde arriba ignora todo esto.
- **Conjunto gráfico B**: `WorldMap_LoadGraphics(x,z)` elige el conjunto B si la celda de capa 0 bajo el grupo tiene tipo 21, solo al cargar la escena (`world_map.c:323-329`, llamado desde `run_scene.c:76-78`) [V]. Con el conjunto B también apunta los huecos de chunk 10-12 y 26-28 a los chunks alternativos 0x10a-0x10c, 0x11a-0x11c (`:366-374`) [V]. El render confirma que el conjunto B es el norte nevado (zona de Imil); en el conjunto A esos huecos muestran un relleno blanco [V: `north_compare.png`].
- **Intercambio de chunk por la historia**: `FieldMap_SetWindowCellTile(128, 256, 176, 56)` (`src/scene/world_map.c:534`) pone el chunk 264 en el hueco 59 (chunk de mundo (11,3)) mientras `FLAG_LAMAKAN_SAND_MONSTER_BEATEN` no está activado; aritmética en `world_map.c:271-300` [V]. Visualmente, 264 y 59 se diferencian en un puente [V render; significado I]. Es la única llamada (grep) [V]. 57 de los 64 chunks alternativos (256-319, y sus gemelos de capa 1) no los referencia el código de TBS [I: grep no encontró otros usos; los 64 no están vacíos y son distintos de 0-255].
- **Animación**: los canales de animación de tiles copian de `gMapLayerData` (tiles E/J) a la VRAM; irrelevante para un render estático [V].

Algoritmo de render desde arriba (implementado en `render_world.py`, 7 s en Python puro) [V]:

```
for layer L in (0,1), world chunk (cx,cy) in 16x16:
    c = cy*16 + cx + 320*L                         # usa las sustituciones de tileIds para el conjunto B / intercambios de la historia
    for cell (x,y) in 16x16: word = tsv[(c//32)*16 + y][(c%32)*16 + x]
        b = word & 0xffff; t[0..3] = cells_bytes[4b..4b+3]
        draw tile t[k] from bank L at BG px ((cx*16+x)*16 + (k&1)*8, (cy*16+y)*16 + (k>>1)*8)
        (layer 1: skip pixel value 0)
palette: palette_a.png (or palette_b.png for kind-21 cells / set B)
```

Resultado: `world_mixed.png` (conjunto A, celdas de tipo 21 dibujadas con el conjunto B) muestra Angara y Gondowan en el cuadrante superior derecho (chunks x 8-15, y 0-7), y el resto es océano; tierra de relleno plana en el borde oeste del continente; tres islotes [V]. Superponer `gWorldMapEntrances` y las posiciones de los actores colocados a mundo/2 hace caer el icono de Vale (actor 11 en 5678,1200), las entradas 0-2 justo al sur de él, y el código de paso 90 (Flint) a su lado [V: `world_annotated_zoom.png`].

## Datos de juego

### Palabra de celda (capa 0) [V]

| Bits | Significado | Evidencia |
| --- | --- | --- |
| 0-15 | id de bloque en `cells.tsv` (los 16 bits completos, sin máscara de 12 bits en el mapa del mundo) | `world_map.c:82-86, 445` |
| 16-23 | código de paso (`struct MapCell.collisionCode`): 1-239 eventos de paso de la escena, 240-241 suelo de encuentros, 252-254 saltos/teletransportes, 0xff muro (significado en mapas por capas) | `include/map.h:13-22`, `src/object/object/step.c:20-25, 231-245` |
| 24-30 | tipo de terreno = región de encuentros (se usan 0 ninguno, 1-6, 21, 31) | `terrain.c:619-624`, `zonedata.c` |
| 31 | selecciona el banco de comportamiento 0x10 | `terrain.c:615-617` |

Las celdas de capa 1 solo usan los bits 0-15; todos sus bits altos son 0 en los datos [V: estadísticas]. Solo se leen los bits altos de la capa 0 (el código indexa las filas 0-31 de `Ram_MapBlocks`, que son la capa 0) [V]. El comentario del código `struct WorldMapCell {tile:24, kind:7, flag:1}` (`world_map.c:17-23`) mete el código de paso dentro de "tile"; los lectores usan los bytes por separado [V].

Censo de valores (capa 0, los 320 chunks): tipos 0 74215, 1 915, 2 1542, 3 1001, 4 771, 5 494, 6 1304, 21 1334, 31 156; bit 31 activado en 188 celdas; códigos de paso presentes: 13, 15, 18, 28, 29, 32, 42, 47, 50, 51, 55, 61, 74, 75, 90, 91, 92, 93, 95, 96, 100 [V].

### Transitabilidad / terreno [V]

- `GetWorldMapCollision` (`terrain.c:535-580`): toma el byte del mapa BG (el número de tile 8x8) en el bloque de pantalla 10 (capa superior) en esa posición y busca su nibble en `Ram_MapCollision + 0x800`; si es 0, hace lo mismo con el bloque de pantalla 8 (inferior) en `Ram_MapCollision`; si sigue siendo 0, devuelve 7. Nibble = fila `((y>>1)&3)`, byte `((x>>2)&1)`, `(x>>1)&1` selecciona el nibble alto, en unidades de 2 px de mundo.
- `CheckWorldMapWalkable` (`terrain.c:586-592`): transitable si y solo si el valor está en 5..12.
- Comportamiento = `gWorldMap_TerrainBehaviorTable[bank + value]` (`mapdata.c:37-41`): banco 0: 5->1, 6->7, 7/8/10-13->1, 9->2; banco 0x10 (bit 31): 5->4, 9->6; banco 0x20 (tipo 21): 5-13->5 salvo 9->6. El comportamiento también elige el fondo de batalla (`encounter.c:118`, `Battle_SelectTerrainBackdrop` `encounter.c:404-429`): 1 pradera, 2 bosque, 3 desierto, 4 y 7 playa, 5 y 6 campo nevado, el resto Sol Sanctum [V].
- Censo del mapa de colisión compuesto: aparecen los valores 1-4, 14, 15 (bloqueados; agua/montaña/acantilado) y 5-10 (transitables); 9 = bosque (comportamiento 2) según las etiquetas de encuentro [V datos; etiqueta "forest" de `encounter.tsv`].
- Altura: ninguna en el mapa del mundo (las celdas no tienen byte de forma; los actores se colocan con y=0 y sin altura de terreno, `src/object/object/actors.c:143-158`) [V].

### Encuentros aleatorios [V]

Por cada paso en el mapa del mundo: `Field_ProcessStep` -> `Encounter_RollWorldMap(&leader->x, speed)` (`step.c:261-263`) -> `Encounter_ResolveWorldMapZoneAndBackdrop` (`encounter.c:103-120`): la primera regla de `gWorldMap_EncounterRules` con tipo coincidente, comportamiento coincidente (o -1) y flag no activado da la zona; luego `Encounter_SelectEnemyGroup` (`encounter.c:130-218`) usa la fila de `encounter.tsv`: tasa (+5 por cada nivel del grupo por encima de `level`, máximo 5), sesgo, 8 grupos ponderados (filas de `src/battle/formatn.tsv`). Las reglas de las escenas de campo (`src/object/location_rules.s`) no se usan en el mapa del mundo (`Encounter_SelectSceneZones(0)`, `run_scene.c:49`).

Reglas (tipo: comportamiento -> zona): 1: 4,7,1->7, 2->8; 2: 4,7,1->13, 2->14; 21: 5->29, 6->30; 31: 1->37, 2->38; 3: 3,4,7,1->45, 2->46; 4: ...->54, 2->55; 5: ...->64, 2->65; 6: ...->80, 2->81. Zonas etiquetadas en `encounter.tsv` ("World map: terrain kind 1, grassland and beach", ...). El comportamiento 3 (desierto) aparece en las reglas, pero la tabla de comportamientos nunca lo produce, así que en el mapa del mundo de TBS el suelo de desierto cuenta como pradera/playa [V lectura de la tabla; efecto en el juego I]. Batallas de Djinn: zonas 100-103 vía `gEncounter_AreaEntryTable` (`zonedata.c:19-29`).

`terrain_kind.png` muestra regiones coherentes (tipo 1 alrededor de Vale, 2 Bilibin, 21 nieve del norte, ...) [V render; nombres de lugar I].

### Entrar en pueblos/mazmorras [V]

Dos mecanismos, ambos terminan en `gWorldMapEvents` (`src/scene/world_map.c:3060-3125`):

1. **Iconos de lugar (la mayoría de los pueblos)**: las filas de `gWorldMapPlacements` (`:2863-2964`) son los actores 8, 9, ... en orden de fila; una fila cuya condición falla igualmente consume su hueco (`actors.c:103-108`). `WorldMap_UpdateLocationContacts` (`world_map.c:416-466`) pone `touchedTrigger = actor + 100` cuando |dx|+|dz| del líder < suma de los radios escalados (y `FLAG_CONTACT_BLOCKED` 0x104 no activado). Un evento `{ EVENT_EXIT, 100+actor, cond, exitNo }` lo asigna a una salida; p. ej., fila 3 (actor 11, sprite 0x105 en 5678,1200) -> disparador 111 -> salida 1 -> `SCENE_EXIT(1, 5, 10)` = escena 5 (pueblo de Vale) entrada 10. Algunos disparadores ejecutan scripts en su lugar (los pasos 116/125/130/150/151 eligen una salida según el lado por el que te acercas, `:367-410`).
2. **Códigos de paso en el mapa**: bits 16-23 de la celda = código; `{ EVENT_EXIT, code, cond, exitNo }` (códigos 13, 15, 18, 28, 29, 32, 42, 47, 50, 51, 55, 61, 75) o scripts `EVENT_TOUCH`/`SEARCH` (90-96 Djinn, viaje, naufragio; 100 búsqueda de las Turtle Boots; 112 ruta de traslado; 74 borde este).

Codificación de salidas `SCENE_EXIT(exit, scene, entrance) = exit<<20 | entrance<<12 | scene`; la forma con flag añade 0x10000000 y una palabra de flag; la tabla empieza con `SCENE_EXITS(own scene)` y termina en 0x1ff (`include/field_scene.h:72-77`).

### Salir de los pueblos [V]

La tabla de salidas propia del pueblo nombra la escena 2: p. ej., `gValeHome_Exits` `SCENE_EXIT(10, 2, 1)` (`src/scene/vale_home.c:1903`); Bilibin `SCENE_EXIT(1, 2, 5)` (`bilibin.c:805`). La entrada `e` es una fila de `gWorldMapEntrances` (`struct SceneEntrance`, 24 bytes: entrada, requiredFlag, x, y, z (píxeles s16), orientación, sin usar, cámara L/T/R/B, sin usar; `field_scene.h:54-67`). Entrada 1 = (5680, 0, 1226) mirando al sur, justo debajo del icono de Vale. Las entradas especiales (33, 49, 64-80, 90, 91, 99) también eligen tablas de actores colocados y escenas cinemáticas (`world_map.c:308-342`, `496-560`).

## Límites y restricciones

- El número y la disposición de los chunks los fija el código: 640 chunks, offset de capa 320 (`0x140`, `world_map.c:298, 640`), cuadrícula de huecos de 16x16 (`& 15`), alternativas en ids fijos 0x10a-0x10c, 0x11a-0x11c, 264 [V]. Mantén `blocks.tsv` exactamente en 320x512.
- Cada chunk se decodifica en 1024 bytes dentro de un bloque de heap de 0x400 (`world_map.c:56-57`) [V].
- Tiles: 256 por capa (las entradas del mapa afín son bytes) [V]; 224 colores de paleta, índice 0 forzado al fondo [V]. Los bancos de tiles E/J (256 tiles) alimentan la animación [V].
- Bloques: el id de bloque es de 16 bits en la celda, pero `cells.tsv` se decodifica en `gMapCellBuffer` (0xc000 bytes, `ewram.s:225`) -> como mucho 12288 bloques [I]; el mismo búfer contiene la imagen de 240x160 de la vista fija durante los eventos (`world_map.c:711-712`) y se recarga después (`:766-767`) [V].
- Tabla de colisión fija de 4096 bytes (2 x 256 tiles x 8) [V]; el script de animación debe caber después de ella en `gMapCollision` (0x4000 en total, empieza en +0x1000) [I].
- Actores colocados: huecos de actor 8..65 (`actors.c:98`, `CONTACT_LAST_ACTOR = 65`); los disparadores de lugar 108..165 no deben chocar con códigos de paso usados para otros eventos [V/I]. La fila i de `gWorldMap_PlaceMarkers` debe seguir alineada con el actor 11+i [V].
- El overlay del mapa del mundo (código + tablas + gráficos de la historia) debe caber en 32 KB en 0x2008000 [V: README de escenas]. Las coordenadas de las entradas son s16 [V].
- Compresión: cada chunk es LZ `plz` (`tools/common/lz.c`, `LZ_PALETTE_UNTAGGED`, máquina `{4123, 485, 4126, 272}`); celdas/atributos/animación `.table.lz`, tiles `.8bpp.lz`, paletas `.gbapal.plz` [V]. La compilación vuelve a codificar a partir de TSV/PNG, así que un editor solo escribe fuentes; nunca escribas a mano `.blocks`/`.lz`.
- Coincidencia byte a byte: las fuentes sin cambios reproducen la ROM original (bytes literales PACKER y mecanismo `_patch.tsv`, `src/map/README.md` "How the build encodes a map"); cualquier edición hace que esa edición difiera, es decir, `make compare-editions` falla por diseño [V]. Los bytes `PACKER:` finales en `map.s`/`worldmap.s` son datos obsoletos inofensivos tras una edición [I].
- Disposición de la ROM: `rom_tail_02` (que contiene `map.s`, `objects.tsv:443`) empieza en una dirección fija por edición (`main.ld:122-126`) y es la última región; crecer solo desplaza los datos posteriores; fin del cartucho de TBS 0x08800000 (`Makefile` `ROM_END_tbs`) [V]; no he comprobado si se supera [I].
- Ediciones: no hay variantes `_ja/_de/...` ni `.ifdef TBS_EDITION_*` en `map/world`, `map/default`, `graphics/world_map`, `zonedata.c`, `mapdata.c`, `world_map_resources.c` [V grep]. `scene/world_map.c` solo tiene diferencias de código de `TBS_PATCH_3` (`:1657-1666`) [V]. Los nombres de lugar / mensajes son catálogos PO por idioma (`games/tbs/text/*.po`) [V README de escenas].

### Diferencias en TLA (resumen)

- `games/tla/src/map/world/blocks.tsv` mide 1024 filas x 512 = 2048 chunks; offset de capa 1 0x400 (`games/tla/src/field/common/map/perspective.c:42`) y una ventana de 32x32 chunks (`tiles[32][32]`, `:8`) -> mundo de 32x32 chunks (16384 px de mundo) [V]. Se omiten 969 chunks (`-`) [V].
- Lo coloca `games/tla/src/map/world/blocks.s` (archivo propio, `.balign 4, 0`) [V].
- Cuatro conjuntos gráficos A-D, cada uno con paleta + 6 hojas de tiles (`tiles_a1..d6.png`), más tablas de animación/atributos por conjunto (`anim_b/d.tsv`, `attr_b/c/d.tsv`) en `games/tla/src/graphics/world_map/`; directorio `games/tla/src/system/resource/directory.s:420-458` [V]. `cells.tsv` es más grande (2745 filas) [V].
- La mayor parte del código del motor del mapa del mundo de TLA sigue en ensamblador (`object_dispatch_5.s`); se supone que la semántica de tipo/flag es compartida [I].

## Incógnitas

Marcadas por alchemy:
- XXX `world_map.c:569`: `WorldMap_UpdateView` lee la posición seguida sin comprobar NULL.
- XXX `world_map.c:778`: si es intencionado que `Map_LoadDefaultCellsAndUpdateBlock` deje `animationActive` activado.
- XXX `src/scene/world_map.c:500-504`: los flags 0x161 y 0x85c (activados por las entradas 99 y 1) no los lee ningún código de TBS.
- XXX `actors.c:101-102`: el corte de sprites 0x2705 al generar los actores colocados.
- Flags de encuentro 351/353 sin nombre (`encounter.c:148-152`); regla "flag 5 / unit 5 experience > 130".
- Los XXX de los mapas por capas (bloque de relleno 0xfff, bytes de relleno de la cabecera) no se aplican: el mapa del mundo no usa máscara de 12 bits [V].

No resuelto por esta investigación:
- La intención de diseño del bit 31 de la celda: mecánicamente convierte la colisión 5 en el comportamiento 4 (fondo de playa) y la 9 en el 6 (fondo de campo nevado) [V]; no se sabe por qué lo llevan esas 188 celdas [I].
- Por qué el valor de colisión 6 se asigna al comportamiento 7 (un segundo id de playa) [I].
- El propósito de los 57 chunks alternativos que ningún código de TBS referencia (restos o de la época de TLA) [I].
- El significado exacto de cada valor de colisión 1-4, 14, 15 (agua frente a montaña frente a acantilado) y de 6, 8, 10 [I].
- Si `picture.png` (mapa de pausa) se derivó de los datos de suelo; un editor que cambie las costas debe redibujarlo a mano [I].
- A qué escena/entrada lleva cada `EVENT_EXIT` en términos humanos requiere cruzar con los nombres de `gField_SceneTable` (se sabe que algunos nombres de escena en alchemy no son correctos, p. ej., la escena 5 `ValeHome` es el pueblo de Vale) [V para el ejemplo].

## Modelo de datos propuesto para el editor

Capa en Python, toda la E/S solo sobre archivos fuente de alchemy. Conservar el formato de texto original para que los diffs sean limpios.

| Entidad | Campos | Archivo (lectura/escritura) | Notas de ida y vuelta |
| --- | --- | --- | --- |
| `WorldGrid` | `chunks[640][16][16]: u32` más vistas derivadas `cell(layer, gx, gy)` a través del mapa de huecos; `slot_map[256] = identity` | `src/map/world/blocks.tsv` | Escribir exactamente 320x512 tokens, `format(v, 'x')` (minúsculas, sin relleno, `0` para cero), separadores de tabulador, fines de línea `\n` + `\n` final. Nunca emitir `-` en TBS. Una reescritura byte a byte idéntica de un archivo sin modificar debe ser un test. |
| `Cell` | `block: u16`, `step_code: u8`, `kind: u7`, `bank_flag: bool` (capa 0); en la capa 1 solo `block` | empaquetado en `WorldGrid` | Conservar tal cual los bits altos de la capa 1 (todos 0) y cualquier bit desconocido. |
| `Alternates` | `set_b_swaps {10:0x10a, 11:0x10b, 12:0x10c, 26:0x11a, 27:0x11b, 28:0x11c}`, `story_swaps {59:264}` | constantes de `world_map.c:366-372`, `scene/world_map.c:534` (solo lectura) | El editor debería editar las alternativas junto con sus chunks base y mostrar ambas vistas. |
| `BlockTable` | `blocks[4386][4]: u8` | `src/map/default/cells.tsv` | Se mantiene la línea de cabecera; 16 valores por fila, `0x%02x`, se permite una última fila corta. Compartido con los mapas por capas: editar un bloque cambia todos los mapas que usan las celdas por defecto; mejor añadir bloques nuevos al final. |
| `TileCollision` | nibbles `lower[256][4][4]`, `upper[256][4][4]` | `src/map/default/attributes.tsv` | 16 bytes por fila, `0x%02x`, se mantiene la cabecera. También compartido con los datos por defecto de los mapas por capas [I]. |
| `Tileset` | por conjunto: paleta (224 RGB), bancos L0 (A+B), L1 (C+D), banco de animación (E/J) | `src/graphics/world_map/*.png` | Mantener el modo P del PNG, los tamaños exactos y la paleta idéntica a `palette_*.png` (índice = color). Reescribir los PNG no afecta a la compilación si se conservan los índices; comprobar que son idénticos píxel a píxel en lugar de archivo a archivo. |
| `Animation` | scripts de canales (lista u16) | `src/map/default/animation.tsv` | Tratarlo al principio como palabras opacas. |
| `Entrance` | `id, required_flag, x, y, z, facing, camera[4]` | `gWorldMapEntrances` en `src/scene/world_map.c:2717-2800` | Fuente en C: analizar/regenerar solo el bloque inicializador entre marcadores conocidos; mantener los nombres `CONDITION_ALWAYS`, `FACING_*`. |
| `Exit` | `exit_no, scene, entrance, flag?` | `gWorldMapExits` (`:2802-2839`) y los `*_Exits` de los pueblos | Igual; mantener la forma de macro `SCENE_EXIT(...)`. |
| `Placement` (icono de lugar) | `row/actor, sprite, condition, behavior, x, z, facing, talk, flags` | `gWorldMapPlacements` (`:2863-2964`) | Número de actor = 8 + fila; insertar/quitar filas renumera los disparadores (100+actor) y la alineación de `gWorldMap_PlaceMarkers` (actor 11+i). Mejor editar en el sitio. |
| `Event` | `kind/control, trigger, condition, value` | `gWorldMapEvents` (`:3060-3125`) | Salidas: `{ EVENT_EXIT, trigger, cond, exit_no }`; los scripts referencian funciones C (solo lectura en el editor). |
| `EncounterRule` | `kind, behavior, flag, zone` | `src/object/zonedata.c:7-15` | 132 s16 incluido el terminador; hay que actualizar el literal del tamaño del array si se añaden reglas. |
| `EncounterZone` | `rate, level, groups[8], weights[8], label` | `src/object/encounter.tsv` | Forma de tabla; 104 filas fijadas por las referencias (ids de zona en código/reglas). |
| `PlaceMarker` | `tile, flag, name_id` por actor 11+i | `src/object/scripts.s:340-383` | Líneas asm `.4byte`. |

Vistas recomendadas para el editor: (1) composición desde arriba con elección de conjunto por celda (tipo 21 -> conjunto B), (2) superposición de colisión a partir de `TileCollision` mediante los números de tile de las celdas (superior, luego inferior, luego 7), (3) superposiciones de tipo y de código de paso, (4) entradas/actores colocados a mundo/2. Funciones auxiliares de coordenadas: px de mundo = px BG x 2; celda = mundo // 32; hueco de chunk = celda // 16; (fila, columna) del TSV para la capa L = `((c//32)*16 + gy%16, (c%32)*16 + gx%16)` con `c = slot_map[(gy//16)*16 + gx//16] + 320*L`.
