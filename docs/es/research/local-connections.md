<!-- translated from docs/research/local-connections.md @ 9ab200ba52b5 -->
# Mapas locales: cómo se conectan y cómo se pueblan (TBS, con notas sobre TLA)

*Esta es una traducción del documento en inglés [local-connections.md](../../research/local-connections.md); si los dos difieren, el inglés es el vigente.*

Árbol de fuentes: `alchemy/` (solo lectura). Las rutas de abajo son relativas a `alchemy/games/tbs/` salvo que empiecen por `games/`, `tools/` u `out/`. "VERIFICADO" = leído en código/datos, o comprobado con un script sobre todos los archivos; "INFERIDO" = deducido, no demostrado.

## Resumen

1. Una **escena** es una fila de `gField_SceneTable` (`src/field/scenes.s`): id de recurso del overlay, grupo, variante, **fila del mapa por capas**. El id de escena es el índice de fila. 201 filas. (VERIFICADO)
2. La fila de mapa indexa `gMap_LayeredScenes` (`src/field/layered.tsv`, 186 filas). Cada fila contiene 6 offsets de recurso desde `ResourceId_Map001`: cabecera del mapa, paleta, 3 hojas de tiles, datos de capa. Así que la tabla de escenas elige el mapa **y** el conjunto de tiles a la vez, y el número de fila **no** es el número de `map_NNN`. (VERIFICADO)
3. El código de cada overlay (`scene/<place>.c`) devuelve cinco tablas mediante seis veneers de entrada: Entrances, Exits, Placements, Events, Regions, más Initialize. Las funciones getter pueden elegir entre tablas según flags o id de escena. (VERIFICADO)
4. **Las salidas funcionan mediante eventos.** El código de colisión de una celda (1..239) casa con un evento `EVENT_EXIT` (valor = tipo de salida), un script de evento de contacto llama a `Engine_EventRequestExit(kind)`, o se aplica una caja de región. Después, la tabla de salidas asigna (escena actual, tipo) a (escena, entrada). (VERIFICADO)
5. Al llegar, la primera fila de `SceneEntrance` cuya `entrance` coincide y cuyo flag está activado (o es -1) coloca al grupo y limita la cámara. Si ninguna fila coincide, se usa la fila 0. (VERIFICADO)
6. Los **marcadores** (`markers.tsv`: x, z, id) son las posiciones de cofres y Piedras de Psinergía. El id es igual al código de colisión de la celda en los 417 marcadores. Lo que contiene un marcador sale del evento `SEARCH` de la escena con ese disparador. (VERIFICADO)
7. Los **NPC** son filas de `ScenePlacement`. Número de actor = 8 + índice de fila, se cumpla o no la condición de la fila (el README de escenas dice otra cosa). Las posiciones son 16.16. 396 de 2,321 filas están en (0,0) y las posiciona el código; hay 405 llamadas en línea a `Engine_ActorSetPosition`. (VERIFICADO)
8. Cada tabla de conexiones es un inicializador C plano a nivel de archivo hecho de literales y macros. Todas pueden reescribirse si la herramienta edita en el sitio, conservando los bloques `#if`, los nombres simbólicos y `const`. Los ids de escena en las palabras de salida son **literales numéricos**. En el código son símbolos del enlazador `(s32)&SceneId_X`. (VERIFICADO)
9. TLA guarda las entradas, puntos y límites de cámara por mapa en un 7.º bloque del mapa (`scene_*.tsv`). Sus overlays llevan casi siempre un `SceneEntrance` de una sola fila. Es una diferencia del motor, así que TBS no puede pasar a los mismos archivos. (VERIFICADO disposición, INFERIDO semántica)
10. Para añadir un mapa o una escena nuevos, usa los 25 huecos `unused` del directorio y añade filas al final de las tablas de escenas y de mapas por capas. Las direcciones de banco fijas y **~3.5–43 KB de margen en la ROM por edición** (relleno de 8 MB) son los límites duros. (VERIFICADO)

---

## 1. Conexión escena ↔ mapa

### 1.1 Tabla de escenas (VERIFICADO)

`src/field/scenes.s:1-9`:

```
.macro scene name, code, area, kind, map
  .equiv SceneId_\name, (. - gField_SceneTable) / 8   ; id = row index
  .2byte \code   ; overlay resource id (= directory index, 0x36f..0x3ce)
  .byte \area, \kind  ; group, variant
  .2byte \map, 0      ; gMap_LayeredScenes row, reserved
```

- `struct SceneRecord` está en `include/field_runtime.h:18-26`: `resourceId, group, variant, mapIndex, reserved`, 8 bytes.
- La tabla tiene 201 filas (cuenta por script). Las filas sin nombre (`scene , 0x376, ...`) no reciben símbolo `SceneId_`.
- `Game_ResetForNewGame` (`src/object/object/scene.c:204-289`) hace `record = &table[gGameState.scene]`, luego `gGameState.map = record->mapIndex` (`:286`), luego `Scene_LoadOverlay` → `Resource_LoadCode(table[scene].resourceId, &gOverlayArea)` (`:294-298`), luego `Scene_TakeExit(Field_RunScene(entrance))` (`:288`).
- `group` se usa para:
  - reglas de música y de nombre de área (`src/object/scene_rules.s`, leídas por `Scene_ResolveInteractionResult` y `Scene_GetAreaNameIndex` en `src/object/object/encounter.c:279-345`);
  - borrar los flags 0x300-0x3ff al cambiar de grupo;
  - el flag de "visitado" `(group & 0x7f) + 0x180` (`scene.c:344`), así que un grupo debe ser ≤ 0x7f.
- `variant` 2 marca los pueblos. Desactiva la regeneración de PP por distancia recorrida y bloquea Retreat (`src/object/object/run_scene.c`, `sceneVariant == 2`).
- Varias escenas pueden compartir un overlay, por ejemplo Bilibin1/2/3 = 0x38b y AltinPeak1..11 = 0x3a4. También comparten un mismo archivo `.c`.
- **Los ids de escena en el código C son símbolos del enlazador.** `scene_ids.h` declara `extern char SceneId_X;` y el código compara `gGameState.scene == (s32)&SceneId_X`, que carga desde una palabra del literal pool. Hay 487 usos así en `src/scene/*.c`.
- Run_scene compara `gGameState.map == (s32)&SceneId_Clear`, que vale 1, para detectar el mapa del mundo (`run_scene.c:45`). (VERIFICADO)
- **Los ids de escena en las tablas de datos** (palabras de salida) son enteros simples o los pocos nombres de `enum SceneId` de `include/field_scene.h:13-24`. No son símbolos, así que **no** siguen una renumeración. (VERIFICADO)

### 1.2 Selección de mapa: tabla de mapas por capas (VERIFICADO)

`src/field/layered.s` hace `.incbin "layered.table"`, compilado a partir de `src/field/layered.tsv`. Sus columnas son `map0..map5:u16` y tiene 186 filas. El objeto se coloca en `rom_main_01` (objects.tsv:59).

`struct LayeredSceneEntry { u16 resources[6]; }` está en `src/field/field/map_layers.c:164`. `Map_LoadLayeredScene(index)` (`:211`) usa los seis recursos así:

| Columna | Recurso | Cómo se usa |
|---|---|---|
| [0] | cabecera del mapa | `Resource_GetTableEntry(resources[0] + ResourceId_Map001)` (`:233`) |
| [1] | paleta | decodificada; se conserva el color 0 (el fondo) (`:337`) |
| [2] | hoja de tiles | bloque de caracteres 1 (`:345-357`) |
| [3] | hoja de tiles | bloque de caracteres 2 |
| [4] | hoja de tiles | bloque de caracteres 3 |
| [5] | datos de capa | decodificados en `gMapLayerData` |

Todos los valores son offsets desde `ResourceId_Map001`. Expandir las macros del directorio los resuelve por nombre (script de borrador):

- las filas 0 y 1 son `Field_Map001` + `Blank*`. Las usan Title, Clear y WorldMap; el camino del mapa del mundo nunca las carga.
- la fila 2 es `Field_Map000` + `Set00{Palette,TilesA-D}`;
- la fila 5 es `Field_Map004` + `Set03*`;
- la fila 12 es `Field_Map010` + paleta/A/B/C de Set09 + **Set08TilesD**.

123 de 186 filas no son seis recursos consecutivos: una fila puede mezclar hojas de conjuntos distintos, y las recoloraciones reutilizan hojas. Así que el editor debe tratar la fila como seis referencias independientes.

`map_NNN/` se nombra según `Field_MapNNN` (la numeración del directorio, `src/map/README.md` "The map numbers are the directory's"). Por ejemplo, la escena ValeHome (id 5) tiene mapIndex 4 → `Field_Map003` = `src/map/map_003/`. El `markers.tsv` de ese mapa (13,44,100) casa con el evento `SEARCH(...)` de ValeHome con disparador 100 (`src/scene/vale_home.c`, eventos).

Dos mapas llevan nombres de lugar en lugar de números: `gondowan_passage/` (`Field_GondowanPassage`) y `venus_entrance/` (`Field_VenusEntrance`). De los 182 recursos de mapa distintos referenciados, 8 los usa más de una escena.

### 1.3 Directorio de recursos (VERIFICADO)

`src/system/resource/directory.s` contiene las macros `resource`, `group`, `area SET, sheets, maps...`, `recolor`, `overlays`, `unused` (`:1-51`).

- El id de una entrada es su **posición**: `ResourceId_X = (. - Resource_DirectoryTable)/4`.
- `area SetNN, ABCD, mmm` emite `Field_Mapmmm`, luego `Tileset_SetNNPalette`, luego `TilesA..D`.
- Los overlays van al final, `overlays 36F … 3CE` (96 entradas, `:299-306`), seguidos de `unused 25` (`:307`). Cada hueco sin usar es `.4byte 0`.
- `Resource_GetTableEntry(i)` es simplemente `Resource_DirectoryTable[i]` sin comprobación de límites (`src/runtime/runtime/system.c:150-152`).
- El directorio está al principio de `rom_tail_02`, que está **fijado** en 0x08320000 en EN (`main.ld`, último `ABSOLUTE`; `out/tbs-en/tbs-en.map:7353`).
- Los datos de mapa (`map_NNN/map.s`, que también lleva las hojas de tiles que le pertenecen) y luego `src/system/overlay/overlays` siguen en el orden de `rom_tail_02` (objects.tsv:436-631).
- Insertar una entrada de directorio antes de los overlays renumera todos los recursos posteriores. Eso rompe los ids de overlay en scenes.s (`0x36f`…) y todos los offsets de `layered.tsv` posteriores al punto de inserción. Usa los huecos `unused`: índices 0x3cf..0x3e7. (INFERIDO de la macro posicional; la aritmética está VERIFICADA).

### 1.4 Overlays: entry, import, objects.tsv, overlays.tsv, enlazador (VERIFICADO)

`src/scene/README.md` y `src/system/overlay/overlay.ld` describen los overlays.

- **Entry** (`scene/entry/<place>.s`) son seis líneas `overlay_veneer` en un orden fijo: Initialize, GetEntrances, GetExits, GetPlacements, GetEvents, GetRegions. Cada veneer es `ldr r4; bx r4; .4byte target` (`src/system/overlay.s:5-11`). El motor los lee como `struct SceneEntries` (`include/field_runtime.h:42-57`): una palabra de veneer más un puntero a función cada uno, 48 bytes. Llama a `gOverlayArea.entrances()`, etc.
- **Import** (`scene/import/<place>.s`) es `.set overlay_imports,1`, luego `.set import.NAME,1` por cada rutina del motor que llama el C, luego `.include overlay.inc`. `overlay.inc` contiene la lista maestra ordenada de ~405 filas `import NAME, TARGET`. Solo las filas activadas emiten un stub (`src/system/overlay.inc:9-25`). Los overlays no pueden llamarse entre sí.
- **objects.tsv** da a cada overlay tres filas `text` en orden (`entry/<place>`, `<place>`, `import/<place>`) con la primera columna = id del overlay en hexadecimal (p. ej., `374 text games/tbs/src/scene/vale_home`). Puede seguir una fila `bss` opcional (`.bss COMMON`, o `resource_<id>_overlay .bss` de `src/system/overlay/ovl_<id>.s`).
- **overlays.tsv** da la cabecera de la sección de salida `.bss` (p. ej., `.bss ALIGN(16)`) para los 36 overlays que tienen filas bss. `tools/ags-objects/ags-objects.c:165-205` falla con "bss header and rows disagree" si existe exactamente una de las dos.
- **Enlazado.**
  - Cada overlay se enlaza en 0x2008000 contra `symbols.elf` (Makefile:209-219).
  - Dentro de un overlay va primero todo el `.text`, luego todo el `.rodata`, luego todo el `.data`, en orden de objetos (pasadas de `render()` de `ags-objects.c`). Así que las tablas `const` van en `.rodata` y las no const en `.data`.
  - `tools/ags-overlays` empaqueta la imagen en `resource_<id>.lz` y `src/system/overlay/overlays.s` la incrusta (`Resource_Overlay36F: .incbin ...` más bytes residuales `PACKER:` por edición).
  - `Resource_LoadCode` la decodifica en `gOverlayArea` y parchea los BL de Thumb (`system.c:228`).
- El área de overlay es de 32 KB, y código + rodata + data + bss deben caber. Medido a partir de `out/tbs-en/overlays/*.map`, los más grandes son 0x3b1 con 32,648 B (120 B libres), 0x373 Vale con 30,764 y 0x3c8 con 30,732. (VERIFICADO a partir de la salida de compilación).

### 1.5 Otras tablas indexadas por escena (VERIFICADO)

Estas usan símbolos `SceneId_` o el grupo, así que siguen siendo correctas al añadir al final:

- `src/object/scene_rules.s`:
  - `gScene_InteractionRuleTable` (música: `scene_cue` / `group_cue`);
  - `gScene_AreaNameRules` (`scene_name` / `group_name`);
  - `gParty_PairResolveRules` (`return_to`, puntos de regreso tras una derrota);
  - `gBattle_BackdropScenes`.
- `src/object/location_rules.s` `gBattle_LocationRules`: zonas de encuentro por (escena, entrada, flag).
- `src/scene/world_map.c` `gWorldMapExits` (`SCENE_EXITS(2)`…) y sus eventos `EVENT_EXIT` (44): cómo el mapa del mundo entra en las escenas locales.

---

## 2. Salidas y entradas

### 2.1 `struct SceneEntrance` (24 bytes, `include/field_scene.h:54-70`) (VERIFICADO)

| # | Campo | Tipo | Significado |
|---|---|---|---|
| 1 | entrance | s16 | el número de entrada que nombra la palabra de salida; -1 termina la tabla |
| 2 | requiredFlag | s16 | -1, o un flag que debe estar **activado** (`GameFlag_TestFar` simple, sin la codificación 0x1000) |
| 3 | x | s16 | píxeles |
| 4 | y | s16 | píxeles (altura; distinta de cero en 20/1520 filas) |
| 5 | z | s16 | píxeles ("abajo" en el mapa) |
| 6 | facing | u16 | 1/65536 de vuelta (`enum Facing`, pasos de 0x2000) |
| 7 | unused1 | s16 | 0 en todas partes, no se lee |
| 8 | cameraLeft | s16 | píxeles, -1 = mantener el límite de la cabecera del mapa |
| 9 | cameraTop | s16 | igual |
| 10 | cameraRight | s16 | igual |
| 11 | cameraBottom | s16 | igual |
| 12 | unused2 | s16 | 0 en todas partes, no se lee |

`Scene_ApplyEntrance` (`src/object/object/run_scene.c:461-505`):

1. Busca `entrance == gGameState.entrance && (flag == -1 || flag set)`. Si nada coincide, usa la **fila 0**.
2. Salvo con `FLAG_KEEP_PARTY_POSITION`, escribe `gGameState.x/y/z = value << 16` y `heading = facing`.
3. Limita los bordes de la cámara, con una vista mínima de 240×160.

Estadísticas sobre 189 tablas / 1,520 filas:

- 3 filas usan un flag;
- 1,023 fijan límites de cámara;
- los dos campos sin usar son 0 en todas partes;
- la columna de entrada es una constante simbólica en 21 filas.

### 2.2 Cómo se activa una salida (VERIFICADO)

Hay tres formas de salir de una escena:

1. **Celda de salida.** `Field_ProcessStep` lee el código de colisión de la celda del líder (`src/object/object/step.c:240-249`).
   - Los códigos `1..239` (`STEP_EVENT_FIRST/LAST`, `:19-27`) ponen `work->action = code`.
   - `Scene_RunTouchOrExit(code)` (`src/object/object/events.c:333-385`) busca primero un evento `EVENT_TOUCH` con `trigger == code`. Si existe, ejecuta su mensaje o script, y el script recibe el código como argumento.
   - Si no, busca `EVENT_EXIT` con `trigger == code`: reproduce el sonido de salida (bits 5..4 del control: 0 normal, 0x20 → SE_128 + efecto 26, 0x30 → SE_129 + efecto 25, 0x10 ninguno) y pone `work->exit = event.value`, el **tipo de salida**.
2. **Script.** Un script de contacto/conversación/Psinergía llama a `Engine_EventRequestExit(kind)`. Se importa como `Event_SetExitRequestFar` (`src/system/overlay.inc:321`). Hay unos 200 puntos de llamada. Las puertas típicas usan `TOUCH_WALKING_INTO(FACING_NORTH)` sobre el código de colisión de la puerta, animan las celdas de la puerta, hacen entrar caminando al líder y luego piden la salida (`vale_home.c:444-471`). Las coordenadas de la animación de la puerta son **argumentos de llamada en línea** (`Event_OpenDoorAndWalkThrough(44, 7, 248, 279)`, `Map_CopyCellsTo(...)`) o arrays `u16 ...DoorCells[]` `MAP_CELL_STEP(srcX,srcY,w,h,frames)` (`include/field_event.h:59-61`).
3. **Región.**
   - `struct SceneRegion` (`include/field_runtime.h:30-37`, 16 B) es `minX,minY,minZ,maxX,maxY,maxZ` (píxeles; mínimo inclusivo, máximo exclusivo), `condition` y `value` = tipo de salida. minX -1 termina la tabla.
   - La comprueba `Field_CheckExitRegions` (`step.c:135-186`) siempre que el código de la celda del líder es distinto de cero.
   - Hay 14 tablas de regiones, 38 filas; la mayoría de las escenas devuelven NULL.

`Field_RunScene` devuelve `work->exit`. Después `Scene_TakeExit(kind)` (`src/object/object/scene.c:25-89`):

- recorre la tabla de salidas del overlay buscando la palabra de cabecera igual al id de la escena actual;
- toma la primera palabra de salida cuyo `kind == exitKind` o cuyo tipo es `0xff` (cualquiera), **y** cuyo flag no está activado (`SCENE_EXIT_IF`: le sigue la palabra de flag; la salida **se omite mientras el flag está activado**);
- recurre a la escena de la primera salida, con la entrada 0, si antes llega a una palabra con tipo 0 o al final (0x1ff).

### 2.3 Codificación de la palabra de salida (VERIFICADO)

`include/field_scene.h:72-77`:

```
SCENE_EXITS(scene)              = scene                         // header
SCENE_EXIT(kind, scene, ent)    = kind<<20 | ent<<12 | scene
SCENE_EXIT_IF(k, s, e, flag)    = SCENE_EXIT(k,s,e) | 0x10000000, flag   // two words
SCENE_EXITS_END                 = 0x1ff
```

| Campo | Bits |
|---|---|
| escena | 0..11 (la alternativa de reserva enmascara solo 9 bits, y 0x1ff es el final, así que los ids de escena deben ser < 511) |
| entrada | 12..19 (0..255) |
| tipo | 20..27 (1..254 reales, 0xff cualquiera, 0 = **cabecera**) |
| sigue flag | bit 28 |

**`SCENE_EXIT(0, N, 0)` es una cabecera de escena, idéntica a `SCENE_EXITS(N)`.** Las tablas de overlays compartidos la usan: `gAltinPeak_Exits` (`altin_peak.c:2671-2722`) contiene las listas de salidas de 11 escenas tras un único `SCENE_EXITS(77)`. Un script encontró cabeceras para 200 de las 201 escenas de overlay; solo la escena sin nombre 59 (overlay 0x39d) no tiene. TLA además trata una palabra de flag de -1 como "siempre" (`games/tla/src/field/common/take_exit.c`).

### 2.4 Catálogo de tablas en `src/scene/*.c` (+ `common/*.h`) (VERIFICADO por script)

| Tipo (identifícalo por el **tipo**, los nombres varían: `gX_Exits`, `gXExits`, `gXExits1`…) | Tablas | Filas | Tablas con `#if` dentro | `const` |
|---|---|---|---|---|
| `struct SceneEntrance` | 189 | 1,520 | 0 | 5 |
| tablas de salidas `u32` (`SCENE_EXITS`) | 99 | 1,479 palabras de salida | 1 | 5 |
| `struct ScenePlacement` | 274 | 2,321 | 4 | 18 |
| `struct SceneEvent` | 263 | 5,891 | 10 | 13 |
| `struct SceneRegion` | 14 | 38 | 3 | 1 |
| Arrays de pasos de puertas/celdas (`u16` `MAP_CELL_STEP`, celdas empaquetadas `u32`, `struct MapCellAnim`) | ~10 | — | — | — |

Tipos de evento por número de filas:

- `PSYNERGY_ON_ACTOR` 1585
- `EVENT_TALK` 1374
- `EVENT_EXIT` 903
- `EVENT_TOUCH` 531
- `SEARCH(..)` 506
- `TOUCH_WALKING_INTO` 493
- controles en hexadecimal en bruto como `0x31`/`0x21` (salida con bits de sonido), `0xc4f3`, `0x8413`: unos 220

Todas son arrays inicializados a nivel de archivo, una fila entre llaves por registro (salidas: una macro por palabra, a veces dos por línea con clang-format, p. ej., `world_map.c:2802`). Los getters las devuelven, posiblemente elegidas según flag o escena (`vale_home.c:104-160`, `bilibin.c:106-114`). Las tablas de actores colocados son en su mayoría **no const** porque `Scene_AssignViewFlags` escribe en tiempo de ejecución la `condition` de las filas cuya condición es 0 (`src/object/object/actors.c:325`).

---

## 3. Marcadores (cofres, Piedras de Psinergía)

- **Formato** (VERIFICADO). `markers.tsv` tiene la cabecera `x:u8	z:u8	event:u8`, filas de columna de celda, fila de celda e id, y termina con la fila `0xff 0xff 0xff`. Se codifica en bruto (`markers.table`, **no** LZ) y se incluye con incbin como 6.º bloque de la cabecera (`src/map/map_004/map.s:25`). Los valores pueden ser decimales o hexadecimales `0x`: `map_002/markers_es.tsv` solo difiere de `markers.tsv` en el formato de los números.
  - Hay 118 archivos de marcadores: 106 base y 12 variantes de edición (`*_ja/_de/_es.tsv`, elegidas con `.ifdef TBS_EDITION_*` en map.s).
  - 76 archivos map.s apuntan al `map_000/markers.table` vacío.
- **Cargador** (VERIFICADO). La lista de marcadores no se decodifica: `work->script = header + header->markers` (`map_layers.c:258`). `Field_PlaceMapMarkers` (`src/object/object/markers.c:30-131`), llamado desde `run_scene.c:73`, hace lo siguiente:
  - Solo se consideran los ids **100..239**.
  - Para cada uno toma el primer evento de escena con `trigger == id`:
    - `control & 0x1ff == 19` (`SEARCH(SEARCH_CHEST)`): crea el objeto **20** (cofre) en el centro de la celda `(col<<20)+0x80000`, ajustado al terreno. Si el flag de condición del evento está activado, el cofre se muestra abierto (animación 2); si el flag está activado y el valor es un mímico (`0x5xxxxx`), no se coloca.
    - otro `SEARCH` con valor `0x300000` (`FIND_PSYNERGY_STONE`) cuyo flag no está activado: crea el objeto **28** (piedra).
  - Se colocan como máximo `MARKER_MAX` = 10. Un marcador sin evento correspondiente no coloca nada.
- **Id = código de colisión** (VERIFICADO). Las 417 filas de marcadores de TBS tienen `grid_collision[x,z] == id` (script de borrador). La búsqueda en sí se basa en el código de colisión de la celda de delante (`Scene_FindEvent(EVENT_SEARCH, code)`, `events.c:111`, `Field_SearchTile` `events.c:429`). Un marcador sin el código de colisión correspondiente mostraría un cofre que no se puede abrir. **El editor debe escribir ambos.**
- **Contenido y flags** (VERIFICADO). El contenido vive en la tabla de eventos de la escena: `{ SEARCH(SEARCH_CHEST), <id>, <opened-flag>, FIND_ITEM(ITEM_X) | FIND_COINS(n) | FIND_PSYNERGY_STONE | FIND_MESSAGE(m) | 0x5xxxxx mimic | EVENT_SCRIPT(fn) }` (`include/field_scene.h:118-217`).
  - La condición es el flag de "abierto". Según el README, la mayoría de los flags de cofre son ≥ 0xe00. El flag se activa cuando se coge el cofre (`events.c:500-560`).
  - El bit 16 del valor significa "el grupo no puede abrirlo".
  - Hay 135 filas `SEARCH(SEARCH_CHEST)` y 17 filas `FIND_PSYNERGY_STONE`. Algunas piedras usan filas `SEARCH_FACING(...)` con una constante con nombre `TRIGGER_STONE`, y algunas piedras son scripts simples (el `Event_UsePsynergyStone` de ValeHome).
- Los códigos 242..247 son mensajes fijos de "punto de búsqueda", 250 es suelo peligroso y 252..254 son salientes/puntos de escalada (`step.c:19-27`, `events.c:387-418`). 0xff es un muro.

---

## 4. NPC y objetos

`struct ScenePlacement` (24 B, `include/field_scene.h:81-98`) (VERIFICADO):

| Campo | Tipo | Significado |
|---|---|---|
| sprite | s16 | tipo de objeto/sprite; 0-7 = personajes del grupo (huecos propios), -1 termina la tabla |
| condition | s16 | -1 siempre; `flag\|0x1000` = flag activado; si no, flag desactivado; 0 = "a la vista" (lo reescribe `Scene_AssignViewFlags`) |
| behavior | s32 | `ACTOR_STAND`=1, `ACTOR_WANDER`=2, enteros pequeños (p. ej., 3), o un puntero a un script de acciones SC_ `s32 ...[]` |
| x, y, z | s32 | píxeles 16.16 mediante `PIXELS(n)` |
| facing | u16 | 1/65536 de vuelta |
| talkFacing | u8 | TALK_FACE_PARTY 0, _AND_BACK 1, KEEP 2, 3 sigue al líder |
| flags | u8 | bit 0 `PLACEMENT_SHARE_PREVIOUS_SPRITE` |

**Generación** (`src/object/object/actors.c:75-180`, `ObjectTable_ResetForObject` `:217`) (VERIFICADO):

- El líder se genera a partir de `gGameState`, y luego la tabla desde el hueco 8.
- **`actorIndex = slot++` se ejecuta antes de la comprobación de la condición (`:105-107`)**, así que una fila omitida sigue consumiendo su número: **actor = 8 + índice de fila** para sprites > 7. Los disparadores `EVENT_TALK` y `PSYNERGY_ON_ACTOR` nombran estos números, así que reordenar o insertar filas renumera todos los eventos de conversación.
- Altura: fuera del mapa del mundo, el valor y se suma a la altura del terreno.
- El máximo es de 58 actores colocados (huecos 8..65).
- Las filas de flags de Djinn (48..127) también necesitan `condition+80`.

Recuento de la columna behavior sobre 2,321 filas: STAND 1,705, WANDER 132, entero 306, símbolo de script 178.

- 396 filas están en x=z=0. Son actores que el código de Initialize posiciona o mueve.
- El posicionamiento en línea es habitual:
  - `Engine_ActorSetPosition`: 405 llamadas
  - `OBJ_POS_SET(no,x,z)` (píxeles, `include/event.h:13`): 119
  - `Engine_ObjectCreate(kind,x,y,z)`: 53, para efectos y objetos adicionales
  - `Engine_ActorWalkTo`: 36

Así que la colocación estática de NPC son datos, pero la puesta en escena de las cinemáticas es código.

---

## 5. `scene_*.tsv` de TLA (bloque del mapa, no del overlay)

El `map.s` de TLA tiene **7** bloques: metatiles, shapes, grid, shape_grid, animation, blend, scene (`games/tla/src/map/map_008/map.s`). No hay bloque de marcadores y TLA no tiene `markers.tsv`.

El bloque scene es `scene.parts.lz`, empaquetado con LZ. `scene.tsv` enumera sus partes en orden: `SCENE_HEADER, SCENE_POINTS, SCENE_ENTRANCES, SCENE_PATCHES, SCENE_BOUNDS`. Está presente en 286 mapas.

| Archivo | Columnas | Notas |
|---|---|---|
| `scene_header.tsv` | `entrances:u16 patches:u16 bounds:u16 none:u16` | offsets en bytes desde el inicio del bloque; los puntos empiezan en 8. Comprobado en los 286: entrances = 8 + size(points), patches = entrances + size(entrances), bounds = patches + size(patches); `none` = 0 en todas partes (VERIFICADO) |
| `scene_points.tsv` | `id:u8 x:u16 z:u16` | termina con `0xff`; 579 puntos, ids mayormente 1..28, 99 ×10. Significado desconocido (INFERIDO: puntos de script o de cámara; no cofres, que en TBS se basan en celdas) |
| `scene_entrances.tsv` | `id:u8 x:u16 z:u16 flags:u8` | 1,970 filas. INFERIDO: equivalente al `SceneEntrance` de TBS (id, x, z). El nibble bajo de flags = facing>>12 (valores 4=S 1105×, 12=N 685×, 0=E, 8=O, 2/6/14 diagonales), y el bit 4 (16) es un flag adicional (28, 20) |
| `scene_patches.tsv` | `key:u16 source_x:u8 source_y:u8 x:u8 y:u8 width:u8 height:u8` | termina con `0xffff`; **vacío en los 286** |
| `scene_bounds.tsv` | `left:s8 top:s8 right:s8 bottom:s8` | normalmente una fila + `-1`. INFERIDO: límites de cámara en celdas de 16 px (map_008: 0,0,40,34) |

En el lado del overlay, las escenas de TLA siguen teniendo Exits/Placements/Events en C (`games/tla/src/scene/<place>/data.c`). 86 de 97 tablas `SceneEntrance` tienen una sola fila, la de reserva, lo que sugiere con fuerza que el motor de TLA toma las posiciones del bloque del mapa (INFERIDO; el lector no está decompilado). Un script que intentó casar los pares (escena, entrada) de las salidas de TLA con los ids de entrada del mapa mediante un offset fijo escena→mapa no fue concluyente, porque la tabla de mapas por capas de TLA no está en las fuentes.

**¿Migrará TBS?** INFERIDO **no**, al menos no a los mismos archivos. Los mapas de la ROM de TBS tienen 6 bloques con marcadores, y su motor lee las entradas de los overlays, así que los datos viven donde los pone la ROM. Historial de git:

- Archivos de mapa de TLA: "TLA: the four field maps still copied, from editable tables" (a20313083f) y otros.
- El trabajo reciente en escenas de TBS es humanización del C ("Align scene table getters with the engine contracts", db7167f0b0).

Ninguno menciona mover las tablas de escena a TSV.

---

## 6. Añadir un mapa o una escena nuevos (lista de comprobación)

Prefiere **añadir al final** en lugar de insertar, en todas partes.

1. **Datos del mapa.**
   - Crea `src/map/map_180/`: `map.s` (`.global Field_Map180`, `map_header`, 3×`map_layer`, 6×`map_block`, incbins) y los TSV.
   - Reutiliza un conjunto de tiles existente (sin hojas nuevas) o añade hojas y una paleta después.
   - Los bloques sin usar son `map_block Field_Map180` con un offset de 0. Para los marcadores, apunta a `map_000/markers.table` o a los tuyos.
2. **objects.tsv.** Añade `main rom_tail_02 games/tbs/src/map/map_180/map` **antes** de la fila `system/overlay/overlays` (objects.tsv:631). Esto da el orden en la ROM; no hay ninguna dirección fijada después de 0x08320000.
3. **directory.s.** Convierte un `unused` en `resource , Field_Map180`, y en paleta/tiles si son nuevos; reduce `unused 25` en consecuencia (`:307`). Los ids nuevos son 0x3cf+ y los existentes no se desplazan.
4. **layered.tsv.** Añade al final una fila de offsets desde `ResourceId_Map001`: mapa, paleta, tiles ×3, datos de capa. Su índice de fila es el `map` de la escena. Se coloca en `rom_main_01`, con espacio libre antes del inicio fijo de `rom_main_02`: EN 4,020 B, DE 1,204 B, ES/FR 1,972 B (12 B por fila).
5. **Overlay de escena** (para dar a la escena su propio código):
   - `src/scene/<place>.c`, `entry/<place>.s` (6 veneers), `import/<place>.s` (imports en el orden de `overlay.inc`);
   - prototipos en `include/unit/scene/<place>.h` (existen 91);
   - filas de objects.tsv `3cf text .../entry/<place>`, `3cf text .../<place>`, `3cf text .../import/<place>`, más un `3cf bss ...` opcional con una fila de cabecera en `overlays.tsv`;
   - `src/system/overlay/overlays.s`: `Resource_Overlay3CF: .incbin "overlays/resource_3cf.lz"` + `.balign 4`;
   - directorio: un hueco `unused` pasa a ser `resource , Resource_Overlay3CF`.
   - Otra opción: reutilizar un overlay existente como variante, como las salas de Altin Peak: añade una fila de escena con el mismo código y ramifica según `SceneId_` en los getters.
6. **scenes.s.** **Añade al final** `scene NewPlace, 0x3cf, <group>, <variant>, <layered row>`. El id nuevo es 201, así que todos los ids numéricos existentes siguen siendo válidos. La tabla está en `rom_main_04`, 8 B por fila; libre antes del banco fijo: EN 3,448 B, DE 1,040 B. Añade `extern char SceneId_NewPlace;` a `include/scene_ids.h`. El grupo debe ser ≤ 0x7f (flag de visitado). Los ids de escena deben ser < 0x1ff (alternativa de reserva de la palabra de salida).
7. **Conexiones.**
   - Añade una palabra de salida en la tabla de salidas de cada vecino bajo **su** cabecera: `SCENE_EXIT(kind, 201, entrance)`.
   - Añade una fila `EVENT_EXIT` (o un script de contacto) en los eventos del vecino para el código de colisión que pintes en las celdas de salida.
   - Pinta ese código en el `grid_collision.tsv` del vecino.
   - Haz lo mismo a la inversa en la escena nueva: cabecera `SCENE_EXITS(201)`, sus salidas, entradas cuyos números coincidan con lo que nombran las palabras de salida de los vecinos, actores colocados, eventos.
8. **Reglas.** Música (`scene_cue`/`group_cue`), nombre de área (`scene_name`/`group_name`), regreso tras derrota (`return_to`) y fondo de batalla en `src/object/scene_rules.s`; encuentros en `src/object/location_rules.s`. Sin filas obtienes MUS_018, ningún nombre, ningún encuentro y el último fondo de batalla.
9. **Texto.** Añade mensajes a `text/<lang>.po`, con un `msgctxt` por cada símbolo de mensaje.
10. **Presupuesto** (VERIFICADO, `out/tbs-*/tbs-*.map`).
    - La ROM está rellenada hasta 0x08800000 (Makefile:134). Espacio libre al final: EN 11,076 B, IT 11,040, DE 10,108, ES 4,128, FR 3,584, JA 43,100.
    - Un mapa nuevo más un overlay probablemente lo superarán, así que habrá que subir el `ROM_END_tbs` de 8 MB. `MEMORY ROM` ya permite 32M (`main.ld`). Esto hace que la ROM deje de coincidir. (INFERIDO: seguro; sin probar).
    - RAM de overlay ≤ 32 KB.

---

## 7. Viabilidad de la generación de código (por tabla)

Regla general: los valores se compilan a bytes fijos, así que el formato y los espacios en blanco son libres. La exactitud byte a byte depende de:

- el mismo orden de filas;
- los mismos valores, incluidos los simbólicos (`MSGNO(Msg…)` se resuelve en números de mensaje, `EVENT_SCRIPT(fn)` en reubicaciones, los nombres de flag de `flags.h`);
- el mismo `const`, que decide la colocación en `.rodata` o `.data`;
- los mismos bloques por edición y por parche `#if TBS_PATCH_n` / `LANGUAGE`;
- el mismo orden de tablas en el archivo.

| Tabla | ¿Segura de reescribir? | Cómo hacer la ida y vuelta |
|---|---|---|
| SceneEntrance | Sí, muy regular: 12 campos literales, 21 nombres de entrada simbólicos | edición conservando el CST de una fila `{...}`; mantener un símbolo cuando el valor no cambia |
| Salidas `u32[]` | Sí, con cuidado: solo macros, pero `#define` por escena (`ROOM_ENTRANCE(exit)`, `LUNPA_EXIT_TO_*`), cabeceras `SCENE_EXIT(0,N,0)`, `#if !TBS_PATCH_3` (vale_home.c) | analizar las llamadas a macros, evaluarlas a palabras, volver a emitir solo las llamadas tocadas; nunca fusionar `SCENE_EXIT(0,..)` y `SCENE_EXITS` |
| ScenePlacement | En su mayoría: `PIXELS(n)`, `FACING_X + FACING_STEP`, nombres de personaje (`GARET`), símbolos de script, 4 tablas con `#if` | editar los campos en el sitio; mantener el orden de filas (números de actor) |
| SceneEvent | La más difícil: macros de campos de bits más ~220 controles en hexadecimal en bruto, símbolos de mensaje y de función, 10 `#if` | tratarlo como tokens opacos salvo los campos editados (trigger, condition, valor FIND_) |
| SceneRegion | Sí, pequeña: 3 con `#if` | en el sitio |
| markers.tsv | Sí, archivo de datos | reescribir el TSV; se aceptan tanto decimal como hexadecimal |
| scenes.s / layered.tsv / directory.s | Sí, orientados a líneas | solo añadir al final |

Verificación:

- Recompila y ejecuta `make compare` / `compare-tbs` (Makefile:48-51).
- Para comprobaciones rápidas, compara las secciones de `out/tbs-<ed>/overlays/resource_<id>.elf` antes y después de una reescritura sin cambios. Un mero cambio de formato debe dar una salida `.bin` y `.lz` del overlay idéntica.
- Evita regenerar archivos enteros: contienen código, regiones `// clang-format off`, comentarios y bloques `#ifdef UBFIX`.

---

## 8. Incógnitas

- Qué escribe `EventWork.touchedTrigger` (`include/field/event_work.h:26`), que leen los scripts. No tiene un escritor con nombre en el código principal (INFERIDO: el código tocado).
- Los enteros pequeños de `ScenePlacement.behavior` distintos de 1 y 2 (3 es habitual): la semántica de `ObjectMotion_SetActionCallback` no se rastrea aquí.
- La tabla completa de tipos de sprite (los ids de objeto 20 = cofre, 28 = piedra y 0x8000 = cámara están VERIFICADOS en markers.c y actors.c).
- TLA: el significado de `scene_points`, el bit 4 de `scene_entrances.flags`, las unidades de los límites, la resolución escena→mapa y la 6.ª columna de la tabla de escenas (también XXX en `games/tla/src/field/README.md`).
- Si los huecos `unused` del directorio y una ROM de más de 8 MB funcionan en hardware y emuladores (INFERIDO sí).
- La escena 59 (sin nombre, 0x39d) no tiene cabecera de salidas. Las salidas allí dejan la escena sin cambios (`Scene_TakeExit` mantiene el estado cuando no encuentra cabecera).

---

## 9. Modelo de datos propuesto para el editor

```
Project
  scenes[id]            // from scenes.s (append-only ids)
    name, overlayId, group, variant, layeredRow
    overlay -> OverlaySource (.c path; shared by N scenes)
  layered[row]          // layered.tsv: {map, palette, tiles[3], layerData} as resource refs
  maps[NNN]             // map_NNN/: header, planes, metatiles, shapes, anim, blend,
    markers[]: {x,z,id}  //   + edition variants; id must == grid_collision[x,z]
  overlay tables (per C array, identified by type, with source span + #if context):
    Entrance  {entrance, requiredFlag, x,y,z, facing, camera{l,t,r,b}}
    ExitTable {segments: [{headerScene, exits:[{kind, scene, entrance, flag?}]}]}
    Placement {sprite, condition, behavior(enum|script ref), x,y,z (px), facing, talkFacing, flags}
              // derived: actorId = 8 + rowIndex
    Event     {kind+detail (decoded control), trigger, condition, value(msg|script|FIND_*)}
    Region    {min{x,y,z}, max{x,y,z}, condition, exitKind}
    getter    {which tables, chosen by which flags/scene ids}  // read-only, shown
  derived graph: Scene --(collision code / script / region)--> exitKind
                 --exit table--> (scene, entrance) --> Entrance row
```

Operaciones de edición:

- **Mover una celda de salida:** el código de grid_collision más la fila `EVENT_EXIT`.
- **Cambiar el destino:** editar la palabra de salida.
- **Añadir un cofre:** fila de marcador, código de colisión y un evento `SEARCH(SEARCH_CHEST)` con un flag nuevo ≥ 0xe00.
- **Mover un NPC:** editar x/z del actor colocado, y avisar si x=z=0 en la fila significa que lo posiciona el código.

Validar en todas ellas:

- que los números de entrada referenciados por cada palabra de salida existen en las Entrances del destino (si no, se usa la fila 0 de reserva);
- los desplazamientos de números de actor al insertar filas de actores colocados;
- el límite de 10 marcadores;
- los presupuestos de 32 KB del overlay y de la ROM.

---
