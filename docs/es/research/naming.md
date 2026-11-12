<!-- translated from docs/research/naming.md @ 3e642cd20a29 -->
# Capa de nombres: códigos de colisión, objetos, sprites, lugares, diálogos, flags (TBS)

*Esta es una traducción del documento en inglés [naming.md](../../research/naming.md); si los dos difieren, el inglés es el vigente.*

> **Desde que se escribió esto:** las tablas de nombres descritas abajo ya no se distribuyen. `gsmap/names.py` lee los nombres en tiempo de ejecución desde la copia local (`en.po`, `flags.h`, `sprite_ids.h`, `item_table.c`, `scenes.s`, `scene_rules.s`). `gsmap/data` conserva solo los fotogramas de vista previa, los flags libres para cofres y nuestras propias descripciones de transitabilidad.

Árbol de fuentes: `alchemy/` (solo lectura), compilación en inglés `out/tbs-en`. Las rutas son relativas a `alchemy/games/tbs/` salvo que empiecen por `out/` o `tools/`. **VERIFICADO** significa leído en código o datos, o comprobado con un script sobre todos los archivos. **INFERIDO** significa deducido y no demostrado. Los datos generados están en `docs/research/names/`. Los scripts que los producen están copiados en `docs/research/names/scripts/`; los originales y los archivos intermedios están en el directorio de borrador `(a scratch folder)`.

## Resumen

1. Los **códigos de colisión** se dividen en tres grupos: significados globales del motor, disparadores de escena y marcadores. (VERIFICADO)
   - **Significados globales:**
     - 0 suelo
     - 240/241 suelo de encuentros
     - 242..247 puntos de búsqueda vacíos fijos: tinaja, barril, caja, tumba, libros, pozo
     - 249 salto encadenado
     - 250 peligro
     - 251 sombra de Cloak
     - 252 saliente
     - 253 escalada
     - 254 hueco de salto
     - 255 muro
   - **1..239 son disparadores de escena.** Su significado sale de las tablas de eventos de la escena: una salida, un script de contacto o una búsqueda.
   - **Los marcadores (cofres y piedras) solo pueden usar 100..239.**
   - El editor debería nombrar 1..239 por mapa a partir de los eventos. `collision_by_map.json` (borrador) es esa leyenda, ya resuelta: para las salidas, el lugar de destino; para los scripts, el nombre del script; para las búsquedas, el objeto o el texto.
2. **Objetos:**
   - Nombre = mensaje `MsgItemName` (386) + id.
   - Icono = columna `icon` de `items.tsv` → `graphics/ui/menu_icons/item_{icon:03d}.png` (16×16, paleta incrustada).
   - Valor del cofre = `FIND_ITEM(id)` = `0x100000|id`, `FIND_COINS(n)` = `0x200000|n`, mímico = `0x500000|slot` (huecos 0..7), o `FIND_PSYNERGY_STONE` = `0x300000`.
   - (VERIFICADO)
3. **Sprites:**
   - El id de sprite del actor colocado se usa directamente como fila de `graphics/sprite/sprites.tsv` (513 filas).
   - Sus gráficos son `graphics/sprite/spr_NNN.png`, una tira vertical de fotogramas de w×h dibujados con la paleta OBJ compartida de 224 colores.
   - El fotograma de vista previa es el primer fotograma de la animación 1 más el desplazamiento por orientación.
   - Se cubren 249 ids, incluidos los 219 usados. 71 nombres están VERIFICADOS (símbolos y comentarios de la decompilación); 178 están INFERIDOS a partir de la imagen y de las escenas que los usan.
4. **Lugares:**
   - `gScene_AreaNameRules` (`src/object/scene_rules.s:168`) da a cada escena o grupo (opcionalmente por entrada) un índice de área.
   - El texto es el mensaje `MsgDebugEntryName` (2459 en EN) + índice.
   - 199 de 201 escenas reciben nombre. (VERIFICADO)
5. **Diálogos:**
   - El `msgid` de `en.po` es el número de mensaje de 5 dígitos rellenado con ceros. `msgctxt` es el nombre del símbolo, o `message` cuando el mensaje no tiene.
   - Un valor de `SceneEvent` por debajo de 0x10000 es un número de mensaje. Por encima, es un script; sus líneas son los símbolos `Msg*` de su cuerpo.
   - El disparador de un evento de conversación es el número de actor, que es 8 + la fila del actor colocado.
   - (VERIFICADO)
6. **Flags:**
   - Hay 4,096 flags (0..0xfff).
   - Los cofres nuevos deberían tomar flags de **0xe00..0xfff**, usando solo flags que no referencie ninguna tabla, código ni literal. **Hay 251 libres** (`flags.json` `free_chest_flags`), siendo los más bajos 0xe01, 0xe03..0xe0f, etc.
   - Nunca uses 0x200..0x3ff: son temporales de escena y de grupo que se reinician.

---

## 1. Códigos de colisión

### 1.1 Significado en el motor (VERIFICADO salvo que se indique)

El código de una celda es `struct MapCell.collisionCode` (`include/map.h:13-22`), leído de la ventana de la capa del líder (`terrainId`), una celda de 16 px cada vez.

| Código | Nombre (para el jugador) | Comportamiento en el motor | Evidencia | Editor |
|---|---|---|---|---|
| 0 | **Suelo** | Transitable. Usa el suelo de encuentros 0, que no tiene encuentros salvo que el desplazamiento = 1 de la regla de ubicación de la escena mueva la primera zona a él. | `src/object/object/step.c:240-276`; `src/object/object/encounter.c:76-90`; `src/object/location_rules.s:1-7` | pincel |
| 1..239 | **Disparador** (salida / evento / búsqueda) | Pisar la celda pone `work->action = code` (`step.c:247`). `Scene_RunTouchOrExit` ejecuta primero el `EVENT_TOUCH` de la escena con ese disparador (mensaje o script); si no hay, usa `EVENT_EXIT`, cuyo valor es el tipo de salida (`events.c:333-380`). Pulsar A sobre la celda de delante busca un `EVENT_SEARCH` con el mismo código (`run_scene.c:440-450`). Los eventos `USE_ITEM` y `PSYNERGY_IN_AREA` también pueden basarse en él. Cualquier código distinto de cero comprueba además las regiones de salida (`step.c:244-245`). | según se indica | disparador: nombrado por mapa a partir de los eventos (§1.3) |
| 100..239 | **Id de cofre / piedra / búsqueda** | Todo lo de 1..239, y además: es el único rango que acepta `Field_PlaceMapMarkers` (`markers.c:57`). Un evento `SEARCH(SEARCH_CHEST)` muestra un cofre (objeto 20, `markers.c:70`); `FIND_PSYNERGY_STONE` muestra una piedra (objeto 28, `markers.c:105`). | | disparador; los marcadores son dueños de estos |
| 240 | **Suelo con monstruos** | Transitable. Los encuentros usan `encounterGroups[1]`, la primera zona de la regla, en lugar del suelo 0. Habitual como suelo de mazmorra: 23 mapas, p. ej., map_009 (133 celdas). | `step.c:22-23,264-267` | pincel |
| 241 | Suelo con monstruos 2 | Como 240, pero usa `encounterGroups[2]`. **Ningún mapa lo usa.** | `step.c:22-23` | pincel (avanzado) |
| 242 | Tinaja vacía | Al buscar, dice "checked the jar… but didn't find anything". Desplazamiento de mensaje 2 desde `MsgTileChecked` (2344) y `MsgTileResult` (2376). Solo se activa cuando el suelo de delante está entre 0 y 64 px por encima del líder. | `src/object/fxdata.c:22-31`; `events.c:439-448`; `run_scene.c:441-447` | pincel |
| 243 | Barril vacío | desplazamiento 3 | igual | pincel |
| 244 | Caja de madera vacía | desplazamiento 13 | igual | pincel |
| 245 | Tumba vacía | desplazamiento 8 | igual | pincel |
| 246 | Estantería (libros) | desplazamiento 30 | igual | pincel |
| 247 | Pozo | desplazamiento 31. Sin usar en los mapas. | igual | pincel |
| 248 | (sin usar) | No se encontró ningún lector, y ningún mapa lo usa (INFERIDO inerte). | — | no tocar |
| 249 | **Salto entre piedras** | `Field_ProcessStep` nunca lo lanza. Tras un salto hacia delante, aterrizar en 0xf9 vuelve a saltar (saltos encadenados). Se usa en 3 mapas (029, 098, 148). | `events.c:383-405`; `src/object/psynergy_effects/climbing.c:18-23,99-103` | pincel (avanzado) |
| 250 | **Suelo peligroso** | Mientras caminas, el contador de pasos de peligro sube y, al llegar a `hazardLimit`, el grupo recibe `hazardDamage`. La escena establece el modo, el límite y el daño. Mapas 063-067. | `step.c:24,293-327` | pincel |
| 251 | **Sombra (Cloak)** | Transitable. Cloak mantiene al grupo oculto solo sobre este código; salir de él termina Cloak (`CLOAK_TILE`). Mapas 111 y 130-142 (Lunpa Fortress, Altmiller Cave…). | `src/object/psynergy_effects/cloak.c:7-11,71` | pincel |
| 252 | **Saliente (saltar abajo)** | Empuja contra él durante más de 12 fotogramas manteniendo Abajo, y el líder salta hacia abajo. | `step.c:25-27,249`; `events.c:394-399` | pincel |
| 253 | **Pared escalable / escalera** | Empuja durante más de 12 fotogramas: Arriba trepa, Abajo desciende. Mientras trepa, solo se permite un paso hacia una celda con el mismo código. Llegar sobre dos celdas 0xfd apiladas con y≠0 hace que el grupo empiece en modo escalada. | `events.c:407-415`; `src/field/field/player_control.c:874-881`; `src/object/object/actors.c:250-262` | pincel |
| 254 | **Hueco de salto** | Empuja durante más de 12 fotogramas: el líder salta 2 celdas hacia delante si el aterrizaje lo permite (`Field_TryJumpForward`). 77 mapas. | `events.c:400-405`; `climbing.c:13-30` | pincel |
| 255 | **Muro** | Siempre bloquea (`Map_CheckObjectStep` devuelve 2). | `src/field/field/terrain.c:477,526` | pincel |

La transitabilidad también depende de la altura. Se rechaza un paso de más de 8 px hacia arriba o de más de 12 px hacia abajo (`terrain.c:494-497`), así que un código de "suelo" en un acantilado sigue bloqueado. La superposición de transitabilidad debería combinar el código con las alturas de `grid_shape`. El agua **no** es un código de colisión en los mapas locales de TBS: es muro o altura, y los charcos y similares son disparadores de escena (INFERIDO del histograma: no hay código dedicado).

El código de escena también cambia los códigos de las celdas en tiempo de ejecución (`SetMapCellCollision`, `terrain.c:422`), en Colosso, Altin Peak, Crossbone Isle, Venus Lighthouse, Tolbi y Sol Sanctum. Los códigos 96..99 de los mapas 078-083 (Altin Peak) no tienen evento estático, así que los lee algún script (INFERIDO).

### 1.2 Histograma de uso (VERIFICADO con `coll_hist.py`, 182 mapas, celdas en las 3 ventanas de capa)

| Código | Celdas | Mapas | Nota |
|---|---|---|---|
| 0 | 1,300,642 | 182 | suelo |
| 255 | 47,077 | 151 | muro |
| 240 | 4,308 | 23 | suelo con monstruos (mazmorras/bosques: 009, 016, 025-030, 043, 046, 050, 055, 056, 062, 064, 066, 067, 078, 133, 136, 137, 164, 166, 167) |
| 21 | 4,244 | 34 | p. ej., Lamakan Desert mapa 091: 2,677 celdas de `EVENT_TOUCH 21 → HeatGauge_CountStep` |
| 251 | 1,729 | 9 | sombra de Cloak |
| 10 / 30 / 11 / 1 / 2 | 963 / 683 / 357 / 340 / 255 | 96 / 23 / 78 / 150 / 140 | los códigos bajos son sobre todo salidas y scripts de contacto de puertas |
| 254 / 253 / 252 | 928 / 484 / 59 | 77 / 60 / 28 | salto / escalada / saliente |
| 243 / 244 / 242 / 245 / 246 | 500 / 482 / 388 / 32 / 18 | 29 / 29 / 28 / 6 / 3 | barriles/cajas/tinajas/tumbas/libros vacíos |
| 100..107 | 100, 67, 37, 21, 8, 5, 3, 4 | 95..3 | cofres (`SEARCH_CHEST` 66× en 100) y otras búsquedas |
| 200..212 | 2..35 | 14..1 | puntos de búsqueda que no son marcadores (objetos ocultos en tinajas/barriles…) |
| 250 | 77 | 4 | peligro |
| 249 | 3 | 3 | salto entre piedras |
| 241, 247, 248 | 0 | 0 | sin usar |

Los tipos de evento detrás de 1..239 en todos los mapas (cuenta = mapas): código 1 → EXIT 130, TOUCH 44; código 10 → TOUCH 65, EXIT 36; 100 → SEARCH_CHEST 66, SEARCH 36. Tabla completa: `coll_hist.json` (borrador). 136 pares (mapa, código) en 1..239 **no** tienen evento estático en las escenas que usan el mapa. Los usan scripts o son restos: muéstralos como "Con script / desconocido".

### 1.3 Leyenda por mapa (VERIFICADO, generado)

`collision_legend.py` escribe `collision_by_map.json` (borrador, 1 MB). Para cada mapa da:
- `scenes`;
- `cells_per_layer`, un histograma de códigos para cada ventana de capa;
- `events_by_code[code]`, una lista de `{scene, table, kind: exit|touch|search|use_item|raised, control, condition, …}`, donde:
  - una salida tiene `exit_kind, to_scene, to_entrance, to_name, to_symbol`;
  - un script tiene `script` (el símbolo ELF, p. ej., `Event_EnterSanctum`, `HeatGauge_CountStep`);
  - un mensaje tiene `message, text`;
  - una búsqueda tiene `search_target` (uno de los 32 nombres de `SearchTarget`, `include/field_scene.h:176-209`), `marker_chest` y `find_item/item_name | find_coins | psynergy_stone | mimic_slot`;
  - un contacto tiene `needs_push` (0x200) y `needs_facing` (0x400).

La regla de etiquetas para la interfaz es:
- "Salida → {to_name}"
- "Evento: {script humanizado}"
- "Cofre: {item}"
- "Buscar {target}: {item | text}"

Cuando no hay evento, la etiqueta es "Disparador sin usar". Varias tablas por escena se eligen según flags de la historia, así que la interfaz debería mostrar la unión y marcarla como "depende de la historia".

**Datos del editor:** `names/collision.json` (generado por `collision_json.py`):
```json
{"notes":[...],
 "ranges":[{"lo":0,"hi":0,"name":"Floor","category":"walk|block|move|search|trigger|unknown",
            "editor":"brush|trigger|trigger (markers own 100..239)|brush (advanced)|don't-touch",
            "meaning":"...","evidence":["src/...:lines"],"confidence":"VERIFIED","color":"#rrggbbaa"}],
 "codes":[{"code":240,"hex":"0xf0","range":"240-240","cells":4308,"maps":23}]}
```
Más una leyenda por mapa generada al cargar, con la forma de `collision_by_map.json` (`{map: {scenes, cells_per_layer[3]{code:count}, events_by_code{code:[event…]}}}`). El editor debería construirla en tiempo de ejecución a partir de los overlays compilados (`Scenes` de gsmap) en lugar de distribuirla.

Paleta de pinceles para los jugadores: Suelo, Suelo con monstruos, Muro, Saliente, Escalada, Hueco de salto, Sombra, Peligro, y Tinaja/barril/caja/tumba/libros vacíos. Los disparadores (1..239) nunca se pintan libremente. Se crean con acciones como "añadir puerta" o "añadir cofre", que asignan un código no usado en ese mapa (y por debajo de 100 para los que no son marcadores).

---

## 2. Objetos

- **Ids y símbolos.** `include/item_ids.h` nombra solo los ids que usa el código (VERIFICADO). La tabla de objetos `src/game/items.tsv` tiene una fila por id (id = línea − 2, 324 filas), una columna `label` con el nombre en inglés y las columnas price, type, flags, equip_mask, icon, … La estructura es `ItemDefinition`, de 0x2c bytes (`include/game/item.h:104-137`).
  - Tipos: 0 ninguno (consumible/clave), 1 arma, 2 armadura, 3 escudo, 4 casco, 5 botas, 6 objeto de Psinergía, 8 anillo, 9 camisa (`item.h:43-55`).
  - Flags: 1 maldito, 2 no se puede desequipar, 4 raro, **8 indispensable (objeto clave)**, 0x10 apilable (`item.h:26-32`).
- **Nombre en inglés** = mensaje de en.po `MsgItemName + id` = **386 + id** (`item_ids.h:7-8`, en.po:1579; usado en `src/shop/shop/buy.c:350`, `src/window/window/decode.c:541`). Quita el prefijo `{article_class:N}`. Solo los ids 0..268 tienen nombre: 655 es `MsgEnemyName`. Descripción = `MsgItemPlainName` (117) + id (`buy.c:68`). Comprobado: 1 Long Sword, 180 Herb, 181 Nut, 268 Cleric's Ring (VERIFICADO).
- **Iconos.** `src/graphics/ui/menu_icons/item_000.png`..`item_254.png`: PNG indexados de 16×16, cada uno con su propia paleta de 16 colores, índice 0 transparente. Tabla de punteros: `gUiIcon_ItemIconPointers` (`src/graphics/ui/menu_icons.s:4-261`). El icono de un objeto = `icon` de `items.tsv` (`ItemDefinition.icon`, `item.h:109`), dibujado por `ItemIcon_Compose` (`src/window/window/icons.c:114`); un índice ≥ cantidad pasa a ser 0 (`icons.c:63-64`). Herb → icono 117, Nut → 132.
  - **Regla del atlas:** el icono k en (k%16·16, k//16·16) en una hoja de 256×256.
  - El atlas se construyó y se comprobó a ojo (borrador `items/item_icon_atlas.png`, `items/item_preview.png`): espadas, armaduras, la hoja de Herb, llaves y orbes coinciden con sus nombres.
  - Las variantes solo JA `item_080_ja`/`item_098_ja` no las usa EN.
  - INFERIDO: la paleta en el juego es igual a la incrustada en el PNG.
- **Valores de cofre** (`include/field_scene.h:211-214`; `Field_SearchTile`, `src/object/object/events.c:429-560`), VERIFICADO:
  - `value & 0x0f000000 ≠ 0` → un script (puntero a función).
  - Si no, el tipo es `value & 0xfff00000`:
    - `0x100000` objeto: la mitad baja = id del objeto; todo lo que no sea 2/3/4/5 también sigue el camino de objeto.
    - `0x200000` monedas: `(u16)` → 0..65535; el juego usa 1..999.
    - `0x300000` Piedra de Psinergía: restaura todos los PP.
    - `0x400000` mensaje.
    - `0x500000` mímico: batalla `Encounter_GetEnemyGroupAtSlot(99, slot)`. La zona 99 es "Mimic chests" (`src/object/encounter.tsv` línea 101, grupos 350..357). Solo son válidos los huecos 0..7 (`encounter.c:244`).
  - `(value & 0xf0000) == 0x10000` → "Can't open it" para el grupo (sin usar).
  - La `condition` del evento es el flag de abierto: el cofre se muestra abierto mientras el flag está activado, y el flag se activa al coger el contenido. Si la bolsa del grupo está llena, el objeto se queda y el flag sigue sin activar (`events.c:565-590`).
  - Control `SEARCH(SEARCH_CHEST)` = 0x13. Los bits 4..8 eligen la línea "checked the X".
  - Revisión de 155 cofres marcadores: 130 objetos, 17 de monedas, 8 mímicos (0x500000..0x500007, cada uno una vez). Ningún cofre usa una Piedra de Psinergía ni un script.

**Datos del editor:** `names/items.json` (generado por `scripts/items/build_items.py`):
```json
[{"id":180,"symbol":"ITEM_HERB","symbol_in_header":true,"name":"Herb","description":"Replenishes 50 HP",
  "type":"none","type_id":0,"price":10,"flags":["stackable"],"key_item":false,"unused":false,
  "icon":117,"atlas":{"x":80,"y":112,"w":16,"h":16},"evidence":"items.tsv line 182; en.po msg 566"}]
```
La salida del selector es `{"kind":"item","id":180}` → `FIND_ITEM(ITEM_HERB)` (0x1000b4), `{"kind":"coins","n":50}` → `FIND_COINS(50)`, `{"kind":"mimic","slot":0..7}` → `0x500000|slot`, o `{"kind":"psynergy_stone"}` → `FIND_PSYNERGY_STONE`. Oculta las entradas con `unused` (nombre "?"/"???"/ninguno) y marca con un aviso las entradas `key_item`. El atlas se construye en tiempo de ejecución a partir de la copia de alchemy del jugador, nunca se distribuye.

---

## 3. Sprites / NPC

- **Id → objeto** (VERIFICADO):
  - `Event_SpawnObjectTable` (`src/object/object/actors.c:97-118`): los ids 0-7 = huecos del grupo, y `Party_RemapCharacterIdByFlags` (`actors.c:12-36`) cambia los sprites de niño 0x12/0x13 con `FLAG_CHILDHOOD`. Los demás ids ocupan huecos de actor 8+ en orden de fila (actor = 8 + fila).
  - Después `Object_CreateFar(id)`, se selecciona la animación 1 y se fija el ángulo a partir de `facing`.
  - `FieldObject_Create` (`src/field/field/objects.c:245-290`): `id>>12` es el tipo. Tipo 0 = un sprite `id & 0xfff`; tipo 2 (0x2000|n) = un grupo de dos sprites n, n+1; los demás tipos no tienen sprite, p. ej., 0x8000 = cámara (`actors.c:266`).
- **Tabla de sprites:** `gCharacter_DescriptorTable[id & 0xfff]` (`src/system/resource/metadata_get_record.c:7-9`) sale de `src/graphics/sprite/sprites.tsv` (513 filas; fila = id; columnas width, height, scale, drawKind, adjust, box, codec, frames, animations). Ancho 0 = sin imagen (`src/field/field/animation.c:512`).
- **Regla del PNG** (`tools/ags-graphics/sprite.c:120-160,295-330`):
  - `graphics/sprite/spr_NNN.png` de la fila dueña de los fotogramas; una fila alias se escribe `SPR_X=SPR_Y`.
  - La hoja es una tira vertical, con el fotograma k en y = k·height. Un `spr_NNN.tsv` opcional con `list` reasigna fotogramas, y sus líneas `anim` son las animaciones.
  - Paleta: 8bpp, usando la `gSystem_BasicColorPalette` compartida de 224 colores (`src/runtime/runtime/text.c:199`), que va incrustada en cada PNG, con el índice 0 transparente.
- **Fotograma de vista previa:** el primer comando de fotograma de la animación 1 (los valores < 239 son fotogramas; 240 fija el tipo de dibujo; 254 salta a otra animación; `src/field/field_internal.h:83-91`), más el desplazamiento por orientación para ese tipo de dibujo (`src/field/facing.c`, aplicado en `src/field/field/sprite_draw.c:150-185`; bit 7 = reflejado). Usa la orientación 0x3800 para una vista frontal recta. Exactamente en 0x4000, los tipos 3 y 5 dibujan base+0 reflejado.
- **Ids especiales:**
  - 20 cofre del tesoro (VERIFICADO, `markers.c:70`).
  - 28 Piedra de Psinergía (VERIFICADO, `markers.c:105`).
  - 22 marcador invisible de 16×16, usado 68× para mostradores y puntos de objetos.
  - 4 y 7 tienen filas vacías.
  - 261-279 y 504 son iconos del mapa del mundo.
  - Las tablas de actores colocados usan los ids 0..504.
- **Nombres.** No hay un enum global de sprites. Los nombres salen de:
  - `include/game/character_ids.h`;
  - enums `SPRITE_*` locales de archivo (`src/scene/lunpa.h`, `vault_jail.c`, `tunnel_ruins.c`, `altin.c`, `altin_peak.c`, `tret_tree_*.c`, …);
  - comentarios de fila.

  Eso da 71 nombres VERIFICADOS. Los otros 178 están INFERIDOS a partir de la imagen y de las escenas que usan el id (p. ej., "Townsperson A", "Dog"); `name_evidence` dice cuál es el caso.
- Las hojas de contactos se comprobaron a ojo: fotogramas frontales y colores correctos, sin basura. Son `sprites/contact_sheet_npc60.png` y `sprites/contact_sheet_all.png` en el borrador.

**Datos del editor:** `names/sprites.json` (generado por `scripts/sprites/build_sprites.py`, usando `spritelib.py`, `usage.py`, `names.py`, `names_manual.py` y `sheet.py`):
```json
[{"id":28,"hex":"0x1c","name":"Psynergy Stone","confidence":"VERIFIED","name_evidence":"...",
  "usage":1,"scenes":["MogallForest1"],"party_slot":false,"has_image":true,
  "png":"games/tbs/src/graphics/sprite/spr_028.png","frame":{"x":0,"y":0,"w":16,"h":16},
  "frame_index":0,"mirrored":false,"palette":{...},"draw_kind":11,"animation":1,"base_frame":0,
  "sheet_frames":11,"scale":256,"adjust":[0,2],"box":[20,16],"evidence":"sprites.tsv row 28 ..."}]
```
La interfaz recorta `png` en `frame` (reflejado si está indicado) en tiempo de ejecución. Se recomienda un archivo de sustituciones "editar nombre" del lado del editor para los nombres INFERIDOS.

---

## 4. Nombres de lugar

- `Scene_GetAreaNameIndex(scene, entrance)` (`src/object/object/encounter.c:326-350`) recorre `gScene_AreaNameRules` (`src/object/scene_rules.s:168-301`). Cada fila es `scene_name Scene, entrance, index` o `group_name group, entrance, index` (`scene_rules.s:12-20`). Gana la **primera** fila que coincide; la entrada -1 coincide con cualquier entrada. Grupo = `gField_SceneTable[scene].group` (`src/object/object/scene.c:157-159`; la columna en `src/field/scenes.s`). Si no hay coincidencia, el índice es 0. (VERIFICADO)
- Texto = mensaje **`MsgDebugEntryName` + índice** (`src/object/psynergy_effects/world_map.c:400`, `src/window/battle_command/debug.c:23`). En EN, `MsgDebugEntryName` = 2459 = `RENDER_RESOURCE_BASE` 0x99B para las ediciones parcheadas no europeas (`include/tbs_edition.h:264-271`, usado por `src/window/window/shortcuts.c:29`). Lee la base del `msgctxt "MsgDebugEntryName"` de en.po, no como constante. (VERIFICADO)
- Las filas `.if EDITION_INTERNATIONAL` (Altin Peak 4, entradas 6/7) están activas para EN (`include/game/ed_asm.h:11-16`).
- Resultado:
  - 199/201 escenas reciben nombre; Title (0) y LinkLobby (190, con nombre solo para la entrada 1) no.
  - 21 escenas no tienen símbolo en `scenes.s`, así que se etiquetan "Scene N" más su nombre de área.
  - Existen nombres específicos por entrada, p. ej., Sanctum: 1/2/20/21 Vale Sanctum, 10-12 Vault Sanctum, 35 Bilibin, 32 Xian, 29 Altin; VaultJail entrada 2 = "Lunpa".
  - Presentación: "{area_name} — {label}", p. ej., "Vale — Vale Home". Los nombres de área se repiten en muchas escenas, así que la etiqueta de la escena desambigua.

**Datos del editor:** `names/places.json` (generado por `scripts/places.py`):
```json
{"area_message_base":2459,
 "scenes":[{"id":5,"symbol":"ValeHome","label":"Vale Home","group":3,"variant":2,"overlay":"0x374",
            "layered_row":4,"map":"003","area_index":10,"area_name":"Vale",
            "area_name_by_entrance":{},"area_message":2469}]}
```

---

## 5. Diálogos

- **Esquema de en.po** (VERIFICADO). Cada entrada es `msgctxt "<symbol>|message"`, `msgid "NNNNN"` (el número de mensaje, rellenado con ceros hasta 5 dígitos) y `msgstr` (texto). Hay 10,723 entradas, 0..10722, sin huecos. Los símbolos salen como `out/tbs-en/text/msg_ids.h` (`#define TEXT_MESSAGE_NUMBER_<Sym> n`, `MSGNO(name)`). El C de las escenas escribe `MSGNO(MsgX)` en las tablas y `MsgX` a secas en el código (`src/scene/README.md:60-61`).
- **Marcado del texto:** `{page_break}` (nuevo cuadro), `{end_wait}` / `{end_now}` (fin), `{line_break}`, y argumentos `{protagonist_name}`, `{actor_name:N}`, `{argument_item_name:N}`, `{text_color:…}`, `{article_class:N}` (`tools/ags-text/symbols.c:28-60`). Un `\n` literal es una línea en pantalla. Muestra los nombres como marcadores tipo "[Isaac]".
- **Búsqueda de conversación** (`Scene_TalkToActor`, `src/object/object/events.c:197-290`; `Scene_FindEvent` `:111-165`):
  - Tipo 0 `EVENT_TALK`, con disparador = id de actor = 8 + fila del actor colocado.
  - Gana la primera fila cuya condición se cumple (-1 siempre; `flag|0x1000` = activado; si no, desactivado), así que un NPC puede tener varias filas elegidas según flags de la historia.
  - `value < 0x10000` → un mensaje. Los 881 mensajes de conversación directa terminan en `{end_*}` (revisión), así que un id es todo el parlamento.
  - Si no, el valor es un script. El tipo 7 es la línea que se dice cuando el grupo ha detenido al actor (`events.c:175-186`).
  - `talkFacing` controla el giro.
- En los scripts, el diálogo son los símbolos `Msg*` del cuerpo de la función. Ejemplo: `Event_TalkAboutTheMayorAndTremors` (`src/scene/vale.c:160`) muestra `MsgValeTheGroundStillShakes` o `MsgValeYourGrandpaIsTheMayor` según `FLAG_PARTY_LEFT_VALE`. Eso da una lista de líneas posibles, no su orden ni sus condiciones (INFERIDO suficiente para vistas previas).
- Los puntos de búsqueda muestran `MsgTileChecked + target` y luego el texto de `FIND_MESSAGE` o del resultado (`events.c:452-470`).

**Datos del editor:** `dialogue.json` (borrador, 650 KB, generado por `scripts/dialogue.py`; 152 escenas, 2,475 filas de conversación). Contiene texto del juego, así que el editor lo genera en tiempo de ejecución:
```json
{"4":{"symbol":"Vale","tables":{"gVale_Events":[
  {"actor":8,"placement_row":0,"kind":"talk|talk_paused","condition":null|{"flag":2069,"when":"set|clear"},
   "message":3967,"msgctxt":"MsgValeMtAlephLooksBeautifulTodayIts","text":"Mt. Aleph looks\nbeautiful today..."},
  {"actor":10,"placement_row":2,"kind":"talk","condition":null,"script":"Event_TalkAboutTheMayorAndTremors",
   "source":"src/scene/vale.c","script_messages":[{"message":4556,"text":"..."}]}]}}}
```
Editar texto significa editar el `msgstr` de `text/en.po` por msgid. Los otros 5 catálogos de idioma deben mantener el mismo conjunto de msgid (`src/game/README.md:97-110`).

---

## 6. Flags

- **Almacenamiento:** 4,096 bits en `gGameFlagBytes`. Los bits 0-2 del número de flag eligen el bit y los bits 3-11 el byte (`src/game/game/flags.c:7-24`, `include/game/game_flags.h:12`). Los accesores por byte tratan 8 flags consecutivos como un contador (`src/game/README.md:110-121`). Todos se guardan (README; la suma de comprobación de la partida cubre `gGameFlagBytes`, `include/save_state.h:55`).
- **Condiciones:** `-1` siempre, `flag|0x1000` = activado, en otro caso el flag está desactivado. 0 en un actor colocado = "a la vista" (`events.c:59-77`).
- **Rangos** (`src/scene/README.md:48-59`, `include/flags.h:7-20`):
  - 0x000-0x0ff: grupo (0-7) y Djinn (48-127).
  - 0x100-0x1ff: motor/sistema.
  - **0x200-0x2ff: temporales de escena, se borran en cada entrada.**
  - **0x300-0x3ff: flags de grupo, se reinician al entrar en otro grupo, números reutilizados por lugar.**
  - 0x400-0x7ff: no se encontró uso (una referencia, 0x400; INFERIDO sin usar, pero evítalo).
  - 0x800-0xdff: historia.
  - 0xe00-0xfff: flags de cofres/hallazgos.
- **Nombres:** `include/flags.h` (970 líneas) `#define FLAG_* value` con comentarios `///`, p. ej., `FLAG_ALTIN_PEAK_LUCKY_MEDAL 0xf78 ///< room 8's chest`. Los flags locales de escena se definen con `#define` en el propio archivo de la escena y no están en flags.h.
- **Revisión de uso** (`flags_survey.py`, VERIFICADO en la medida de sus fuentes):
  1. Cada condición, requiredFlag, flag de salida y condición de región en las tablas de los overlays compilados.
  2. Cada llamada a un accesor de flags con argumento constante en la salida de `clang -E` de cada `src/**/*.c`. La salida va solo a stdout y no se toca alchemy.
  3. Los campos de flag de las filas `scene_cue`/`group_cue`/`location` en `scene_rules.s` y `location_rules.s`.
  4. Todas las definiciones de flags.h.

  Encontrados en uso: 0xe00-0xfff 213/512; 0x800-0xdff 300; 0x300-0x3ff 108.
- **Lista conservadora de libres** (`flags_free.py`): excluye además cualquier valor 0xe00..0xfff (o su forma de condición 0x1e00) que aparezca como literal hexadecimal en cualquier parte de `src`/`include`, fuera de los datos de gráficos y mapas. Eso deja **251 libres**. Rachas: 0xe03-0xe0f, 0xe49-0xe58, 0xe61-0xe73, 0xe81-0xea1, 0xef8-0xeff, 0xf09-0xf12, 0xfdb-0xfe0, … (`flags.json` `free_chest_flags`).
- **Regla de asignación para un cofre nuevo:**
  1. Toma el flag más bajo de `free_chest_flags` que no usen ya las tablas de sustitución propias del mod (`games/tbs/src/mod/`) ni otras ediciones pendientes.
  2. Escríbelo como condición del evento `SEARCH(SEARCH_CHEST)`.
  3. Regístralo en el manifiesto del mod para que nunca se reutilice, ni siquiera después de borrar el cofre (las partidas antiguas pueden tenerlo activado).
  4. Vuelve a verificar en cada cambio de versión fijada de alchemy volviendo a ejecutar la revisión; la lista de libres depende del commit.
- **Comprobar que un flag no se usa**, en este orden:
  1. No está en `used` de una ejecución reciente de `flags_survey.py` (tablas + código + reglas).
  2. No hay coincidencia de literal hexadecimal (`flags_free.py`).
  3. No está en el byte de ningún flag con accesor por byte (la revisión marca los 8).
  4. No está en 0x200-0x3ff.
  5. Después de compilar, hacer `grep` de la media palabra en el `.bin` del overlay **no** es fiable (falsos positivos), así que confía en 1-4.

**Datos del editor:** `names/flags.json` (generado a partir de los dos scripts):
```json
{"total_flags":4096,
 "ranges":[{"lo":3584,"hi":4095,"meaning":"chest / find flags","editor":"allocate new chest flags here"}],
 "names":{"0xf78":["FLAG_ALTIN_PEAK_LUCKY_MEDAL"]},
 "used":{"0xf78":["flags.h","table 3a4:gAltinPeak_Events..."]},
 "free_chest_flags":[3585,3587,...]}
```

---

## Archivos generados y cómo se hicieron

Todos los scripts están en `names/scripts/` (copias) y en el directorio de borrador de arriba. Dependen de `gsmap` de gs-mapedit (Project, Scenes, grid) y de `out/tbs-en`.

| Archivo | Script | Entradas |
|---|---|---|
| `names/collision.json` | `collision_json.py` (después de `coll_hist.py`) | lectura del motor de arriba; histograma sobre `src/map/*/grid_collision.tsv` |
| borrador `collision_by_map.json` | `collision_legend.py` | cuadrículas + tablas de eventos/salidas compiladas + `places.json` + `items.json` + en.po |
| `names/items.json` | `items/build_items.py` | `src/game/items.tsv`, en.po, `item_ids.h`, `graphics/ui/menu_icons/` |
| borrador `items/search_events.json` | `items/survey_chests.py` | tablas de eventos compiladas |
| `names/sprites.json` | `sprites/build_sprites.py` (+ `spritelib.py`, `usage.py`, `names.py`, `names_manual.py`, `sheet.py`) | `graphics/sprite/sprites.tsv`, `spr_*.png`/`.tsv`, tablas de actores colocados compiladas, fuentes de escena |
| `names/places.json` | `places.py` (+ `po.py`) | `src/field/scenes.s`, `src/object/scene_rules.s`, en.po, `layered.tsv` vía gsmap |
| borrador `dialogue.json` | `dialogue.py` | tablas de eventos compiladas, símbolos ELF de los overlays, `src/scene/**`, `out/tbs-en/text/msg_ids.h`, en.po |
| `names/flags.json` | `flags_survey.py` → `flags_free.py` → fusión en línea | tablas compiladas, `clang -E` de `src/**/*.c`, archivos `.s` de reglas, flags.h |

Las imágenes (atlas de iconos, hojas de contactos) y el texto del juego no se suben a propósito; según la postura legal de PRODUCT.md, la aplicación los construye a partir de la copia local del jugador.

## Incógnitas

- Qué significa 248 (sin lector, sin usar), y si 241 funciona como se espera (ningún mapa lo usa).
- Los códigos 96..99 (Altin Peak) y 136 pares (mapa, código) en 1..239 no tienen evento estático. Presumiblemente los lee código de escena (llamadores de `GetMapCellCollision`) o son restos.
- La colisión en el **mapa del mundo** es un sistema aparte (byte de paso de `blocks.tsv`, `attributes.tsv`): ver `overworld.md`.
- Quién escribe `touched_trigger`, y los bits altos del control de evento en 22 cofres (0x400, 0x8400, 0xc400). El bit 0x400 del *disparador* omite la línea "checked"; el significado de los bits de control no está confirmado.
- El hueco de paleta en el juego para los iconos de objetos (se supone la paleta del PNG).
- Los 178 nombres de sprite INFERIDOS. Algunos son conjeturas (p. ej., 44 "Dodonpa", 66/67, 69 "Lady Layana"). El corte de índice de actor 0x2705 está marcado como XXX en la fuente. JA/IT usan `spriteja.tsv`/`spriteit.tsv`.
- Si un mensaje sin `{end_*}` continúa con el id siguiente. Ningún mensaje de conversación directa carece de él, así que no importa para las vistas previas.
- La revisión de flags no detecta los flags a los que solo se llega mediante variables o expresiones calculadas (5,191 llamadas a accesores no constantes, incluidas definiciones y bucles) ni los flags en arrays de datos de C. La pasada de literales hexadecimales cubre la mayoría; 0x400-0x7ff parece sin usar, pero no está demostrado.
- Si el hueco de mímico puede superar 7 sin problemas (lee en la zona siguiente, así que no es útil).
