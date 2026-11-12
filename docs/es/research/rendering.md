<!-- translated from docs/research/rendering.md @ 5cc75b0f23d8 -->
# Investigación del render: capas, mezcla, animación de tiles, celdas de relleno

*Esta es una traducción del documento en inglés [rendering.md](../../research/rendering.md); si los dos difieren, el inglés es el vigente.*

Fuente: alchemy (`games/tbs/...`). Las rutas son relativas a `games/tbs/` salvo que se indique otra cosa.
VERIFICADO significa que la afirmación se leyó en el código del motor y se confirmó renderizando. INFERIDO significa que es una suposición razonada.
Los scripts y renders de borrador están en
`(a scratch folder)`
(`r2.py` es el renderizador de referencia, `dirmap.py` resuelve la tabla de recursos de escena).

## Resumen

Los mapas "revueltos" no se deben al parallax. Los causan tres errores del visor, y dos de ellos afectan a casi todos los mapas:

1. **Las celdas de relleno (0xfff) son arte real.** Al cargar, la k-ésima celda 0xfff, contada por filas sobre toda la cuadrícula de 128×128, se convierte en el bloque k. En **los 182 mapas**, el número de celdas de relleno es exactamente el número de filas de `metatiles.tsv`. La tabla de bloques es en la práctica "bloques únicos en orden de lectura", y los valores de celda explícitos los reutilizan. Dibujar las celdas de relleno como vacías hace desaparecer la mayor parte de cada mapa. (VERIFICADO)
2. **El conjunto de tiles sale de la tabla equivocada.** El juego carga la paleta de un mapa, sus tres hojas de VRAM y su hoja D desde `src/field/layered.tsv` (`gMap_LayeredScenes`), no según el orden de `directory.s`. **117 de 182 mapas** usan una combinación de paleta u hojas distinta de la que supone el visor. Ejemplos: el bloque de caracteres 3 del mapa 034 es `Set02TilesC` y su hoja D es `Set26TilesC`. VenusEntrance usa hojas `Set07` con `Palette49`. (VERIFICADO)
3. **Los límites de la cabecera son solo los límites de cámara por defecto.** La tabla de entradas de una escena puede sustituirlos. El mapa 034 (escena Bilibin3) queda limitado a 16..400 px por sus entradas. Fuera de ese rango, el área de cabecera de 128×128 tiles es relleno de cuadrícula (bloque 3), que nunca se ve en el juego. (VERIFICADO)

El parallax y el desplazamiento continuo existen solo en 8 mapas (047, 103, 104, 147, 148; en 090/091/092/169 las máscaras no tienen efecto porque la velocidad es 0). La mezcla es BLDCNT/BLDALPHA establecidos por un pequeño script. El primer objetivo es casi siempre la capa 2 (BG1), a veces la capa 1 (BG2). La animación de tiles son copias DMA de tiles desde la hoja D a la VRAM. Los cuatro se implementaron en `r2.py` y se comprobaron renderizando.

## (a) Capas, ventanas y desplazamiento

**Estructuras.** `struct LayeredSceneLayer {u8 x, y; s8 scrollX, scrollY, speedX, speedY; u8 periodX, periodY;}` está en `src/field/field/map_layers.c:172-181`. El orden de la macro `map_layer` es el mismo: x, y, rate_x, rate_y, drift_x, drift_y, period_x, period_y (`src/map/map.inc`).

**Carga** (`map_layers.c:274-303`, VERIFICADO):
- `offset = x<<19` y `y<<19`, así que el origen es x×8 px en coma fija 16.16.
- `scale = scroll*4096`, así que rate/16 de la vista.
- `speed = speed*4096`, así que speed/16 px por fotograma.
- `mask = period`.
- `phase = 0`.

**Por fotograma** (`Map_UpdateLayerScroll`, `map_layers.c:474-566`; igual en `Map_SetCameraCenter` 572-630, VERIFICADO):
```
view   = followed point - focus, clamped to [min, max - 240x160]        (min/max = header bounds*8 px, or scene overrides)
base   = view * scale            (Q16 multiply → view * rate/16)
if speed: phase += speed; base = (base + phase) & ((period<<19) | 0x7ffff)   # wrap; only applied when speed != 0
pos    = base + offset           # layer's top-left in grid pixels
BG(3-li) scroll = pos
```
El dibujo lee las celdas en `((pos/16) & 0x7f)` en ambos ejes (`Map_RenderMetatileRow/Column`, 411-462). Así que **la ventana de una capa da la vuelta módulo 128 celdas (2048 px)**. Tamaño de la ventana = pantalla; no hay tamaño de ventana por capa.
La capa li se muestra en BG(3-li), con prioridad BGCNT = el byte de prioridad de la cabecera, base de caracteres = el byte char de la cabecera, y base de pantalla 5+li (314-322).

**Límites de cámara.** `work->min/max = header bounds << 19` (261-264). `Scene_ApplyEntrance` (`src/object/object/run_scene.c:488-499`) sustituye cada uno de minX/minY/maxX/maxY en píxeles cuando `cameraLeft/Top/Right/Bottom != -1` de la entrada (`struct SceneEntrance`, `include/field_scene.h`). Mapa 034 = escena `Bilibin3` (`src/field/scenes.s:50`, índice de mapa 0x24). Sus entradas 1 y 2 usan los límites 16,16,400,400 (`src/scene/bilibin.c:780-785`). Algunas escenas también escriben los límites directamente (`tolbi_ship_deck.c:1062`, `vale_babi.c:418-421`, `psynergy_effects/view.c:16`).

**Mapas con parámetros de capa no predeterminados** (todo lo demás es `16,16,0,0,255,255`):

| mapa | capa | parámetros | significado |
|---|---|---|---|
| 047 | 0 | rate 8,8 | parallax a media velocidad |
| 103 | 0 | drift_y −25, period 255 | el fondo fluye hacia arriba 25/16 px/fotograma, da la vuelta a los 2048 px |
| 104 | 0 en y=92 | rate 6,6 | parallax de cielo/mar (escena del mástil del barco) |
| 147, 148 | 2 | rate 20,20, drift −121/16, 35/16 px/f, period 31 | capa de tormenta de arena, da la vuelta cada 256 px |
| 090-092 (capa 0,1), 169 (capa 0) | | period 127/63, speed 0 | sin efecto (la máscara solo se usa cuando speed ≠ 0) |

**Orden de prioridad (GBA, VERIFICADO por render).** Dibuja de atrás hacia delante ordenando por `(-priority, layer index)`. A igual prioridad, el BG de número menor queda encima, así que la capa 2 (BG1) queda sobre la capa 0 (BG3). El `sorted(key=-priority)` del visor actual es estable, así que ya da el mismo resultado. Prioridad 0 = apagada.

**Regla de render para un visor en Python:**
- *Capas de campo* (rate 16, speed 0): `grid_px = (origin_px + map_px) mod 2048`, donde `map_px` se mide desde (0,0) del espacio de la cuadrícula, no desde bounds.left. Esto es exacto para cualquier cámara. El `render_layer` actual se comporta así para left=top=0, pero no da la vuelta módulo 128 celdas e ignora un bounds.left/top distinto de cero.
  - Forma correcta: `gx = (x*8/16 + bounds.left/2 + i) % 128` para la columna de pantalla i de la ventana de límites, y lo mismo para y.
- *Las capas con parallax/desplazamiento continuo* no tienen una única imagen estática. Regla recomendada para la vista del mapa: anclar en el centro del rango de la cámara.
  - `V = ((min + max(min, max-240))/2, same for y)` y `pos = layer_pos(V) + (map_px - V)`.
  - Es exacto para la cámara en V y continuo en el resto. Fase del desplazamiento = 0 (o speed×fotogramas).
  - Ofrece también una "vista previa de cámara" de 240×160 que use `layer_pos(view)` exactamente.
- *Recorta* a los límites de cámara de la escena cuando se conozcan; si no, usa los límites de la cabecera.

## (b) Mezcla

**Mecanismo** (`src/field/field/map_animation.c:163-255`, VERIFICADO):
- `blend.tsv` se compila a medias palabras: `control v` → v (un valor de BLDCNT, reconocible por el nibble alto 3); `level v wait` → v, wait; `jump n` → 0xfe00|n (cursor = script + 2n medias palabras); `stop` → 0xfeff; `end` → 0xffff (vuelve al inicio).
- En un `level`:
  - si los bits de efecto (7..6) del último BLDCNT son 01, entonces `REG_BLDALPHA = v`;
  - si no, `REG_BLDY = v`;
  - después espera `wait` fotogramas.
- Un script que es solo `end` no instala nada (`DisplayBlend_StartScript` 246).
- El cargador pone primero `REG_BLDCNT = 0` (`map_layers.c:365-367`).

**Semántica de la GBA:**
- Los bits 0-5 de BLDCNT son el 1.er objetivo (bit0 BG0, bit1 BG1 = capa 2, bit2 BG2 = capa 1, bit3 BG3 = capa 0, bit4 OBJ, bit5 fondo).
- Los bits 6-7 son el efecto (1 alfa, 2 aclarar, 3 oscurecer).
- Los bits 8-13 son el 2.º objetivo.
- BLDALPHA: EVA = bits 0-4 (peso de la capa objetivo 1), EVB = bits 8-12 (peso de lo que hay debajo), cada uno con tope en 16.
- `out = min(31, (top*EVA + below*EVB) >> 4)` por canal de 5 bits.
- BLDY: `I + (31-I)*Y/16` (aclarar) o `I - I*Y/16` (oscurecer).

**Valores encontrados en los mapas de TBS** (primer `level` tras `control`):

| BLDCNT | capa objetivo | efecto | mapas (ejemplos) |
|---|---|---|---|
| 0x3f42 | capa 2 (BG1) sobre todo | alfa | 005-007/032/076 (0x1006: 6/16 + 16/16 aditivo), 021, 022-024/136/137, 025-027/077-085 (0xa09: 9/16 + 10/16 = el agua de 080), 029, 033/040/062/115/144 (0x1003 resplandor, animado 3-4), 047 (0xc04), 053, 054-058/109/155/156/163, 063-067/100, 073, 075, 108, 113, 133, 139-142 (0xb0e), 154, 164-167 |
| 0x3f44 | capa 1 (BG2) | alfa | 009/145/146, 010/019, 012/013/016, 014/015, 018/038/052/094/095/099/102/120/121/151/160/161 (0x1008), 061, 086, 105, 124 |
| 0x3fc8 | capa 0 (BG3) | oscurecer, BLDY 3-6 | 046 |
| (ninguno) | — | solo BLDY, sin efecto | 039/042/043, 114, 125: el script escribe niveles con BLDCNT=0. Alguna escena debe establecer BLDCNT (INFERIDO) |
| solo `end` | — | — | 36 mapas (020, 028, 031, 036, 037, 048, 051, 060, 072, 074, 089, 093, … incl. 134 vía `map_020/blend`) |

La mayoría de los niveles con EVB=16 son **resplandor aditivo** (haces de luz, antorchas). Una espera de 43210 significa que el nivel es constante.

**Mezclas establecidas por la escena** (no están en `blend.tsv`; VERIFICADO en el código):
- `src/scene/altmiller_cave.c:195-222, 313-320`: BLDCNT 0x3f42 con BLDALPHA 0x1000..0x600, o 0xc04. El mapa 134 = escena AltmillerCave5 (`scenes.s:165`) tiene su capa de oscuridad mezclada de esta forma.
- También `tret_tree_branch.c:163` (BG1 4/12), `tolbi_spring.c`, `vale_babi.c`, `mercury_lighthouse*.c`, `crossbone_isle_platform_rooms.c`, `lemurian_ship.c`.

**Regla de render:**
- Analiza el script de mezcla y toma el BLDCNT y el primer nivel, o simúlalo hasta el fotograma t.
- Para cada capa dibujada de atrás hacia delante: si su bit de BG está en el objetivo 1 y effect==1, `rgb = min(31,(layer*EVA + below*EVB)>>4)` donde la capa es opaca. "Debajo" es el color ya compuesto (o el fondo); todos los controles de TBS usan el 2.º objetivo 0x3f.
- Para los efectos 2/3, aplica BLDY a los píxeles de esa capa.
- Usa color de 5 bits (valor del PNG >> 3) para obtener resultados exactos.
- Opcionalmente, mantén una pequeña tabla de sustituciones por mapa para las mezclas establecidas por la escena (134 → 0x3f42/0xc04).

## (c) Animación de tiles

**Mecanismo** (`src/field/field/map_animation.c:7-145`, VERIFICADO):
- `animation.tsv` se compila a medias palabras: `channel n` → 0xfd00|n, `frame src cnt dst wait` → 4 medias palabras, `jump n` → 0xfe00|n, `stop` → 0xfeff, `end` → 0xffff.
- `MapAnimation_StartChannels` recorre el flujo. Cada 0xfdNN inicia el canal NN&15 en la siguiente media palabra, en pausa si el bit 7 está activado (`channel 0x8N`; una escena lo reanuda con `Map_ClearLayerEntryFlag`).
- En cada fotograma, para cada canal no pausado:
  - si timer>0: timer−− y pasa al siguiente canal.
  - si no, ejecuta en el cursor:
    - 0xffff → cursor = inicio
    - 0xfeNN → cursor = inicio + 2·NN medias palabras
    - 0xfeff → sigue parado
    - en otro caso copia `cnt` tiles, pone timer = wait, cursor += 4, y vuelve a iterar en el mismo fotograma.
  - Así que **una copia con espera W permanece en pantalla W fotogramas**, y W=0 encadena con la siguiente copia en el mismo fotograma.
- Copia (4bpp, `wideTiles==0`), en tiles de 32 bytes contados desde el **bloque de caracteres 1**:
  - `src >= 0x600`: desde `Ram_DecodeBuffer (0x0201c000) + src*32`, que es `gMapLayerData` (0x02028000, `src/system/ewram.s:236-244`, `include/ram_buffer.h`) + (src−0x600)*32. Es decir, **el tile src−0x600 de la hoja D** (hoja D = columna 5 de `layered.tsv`, decodificada en gMapLayerData en `map_layers.c:357-359`).
  - `src < 0x600`: desde el tile de VRAM `512+src` (absoluto, desde el bloque 0).
  - Destino: tile absoluto de VRAM `512+dst`.
- El tile absoluto de una entrada del mapa es `charBase*512 + (entry & 0x3ff)`.

**Cómo producir el fotograma t:**
1. VRAM inicial: los bloques 1/2/3 de las columnas 2/3/4 de `layered.tsv`, y la hoja D de la columna 5.
2. Construye los canales como arriba; omite los canales pausados (`channel 0x8N`).
3. Ejecuta la actualización t+1 veces, modificando un array de tiles de VRAM.
4. Después renderiza normalmente con los tiles modificados.

Los bucles son cortos (el ciclo de agua de 34 dura 24 fotogramas; 127 salta tras 10+10 fotogramas). Un GIF/vista previa puede avanzar 1..N fotogramas. El atlas de metatiles debe reconstruirse en cada fotograma o, mejor, cachearse por tile.

## (d) Celdas de relleno 0xfff

**Mecanismo** (VERIFICADO):
- `Tilemap_ConvertBuffer` (`src/field/field/map_layers.c:110-122`) ejecuta `Tile_ConvertMap` (`src/graphics/tile/convert_map.s:8-50`) sobre el plano de bloques.
- r5 = 0xFFF00000 comprueba `(cell<<20) == 0xfff<<20`.
- r4 empieza en 0xFFFFF001; `cell + r4` (truncado a 16 bits) = `(cell & 0xf000) | k`, y r4 se incrementa con cada celda de relleno.
- El gemelo en C sin usar `Tilemap_NumberPlaceholderBlocks` (84-103) hace lo mismo.
- Resultado: **la k-ésima celda (empezando en 0, por filas sobre todas las 128×128 celdas, todas las capas juntas) cuyos 12 bits bajos son 0xfff se convierte en el bloque k. Su nibble alto se conserva.**
- Después el dibujo usa `Ram_MapBlocks[(cell<<20)>>19]` (solo los 12 bits bajos, 411-437).

**Validación.** En cada uno de los 182 mapas, el número de celdas de relleno es igual al número de filas de `metatiles.tsv` (`allph.py`). Los renders de 034 y VenusEntrance pasan a ser arte coherente (ver abajo). Así que las celdas de relleno no las rellena código desconocido: son los bloques únicos del mapa en orden de lectura. El `XXX` de `src/map/README.md` queda respondido. (Solo cuentan las celdas que contienen exactamente 0xfff al cargar; las copias de celdas en tiempo de ejecución `Map_CopyMetatileIndicesRect` ocurren después).

**Regla:** antes de renderizar, `n=0; for y in 0..127: for x in 0..127: if cell&0xfff==0xfff: cell=(cell&0xf000)|n; n+=1`.
Para un editor esto tiene consecuencias:
- Pintar una celda a 0xfff o desde 0xfff renumera todas las celdas de relleno posteriores.
- Al editar hay que mantener el número de celdas de relleno igual al número de bloques, o los bloques guardados se desplazan.
- Muestra el número de bloque resuelto y, al guardar, guarda 0xfff solo donde `resolved == running count`. Otra opción: dejar las celdas como están y tratar 0xfff como "siguiente bloque único".

## Renders validados

Todos en `(a scratch folder)`:
- `cur_034.png`, `cur_VenusEntrance.png`: el visor actual (roto).
- `ph_034.png`, `ph_VenusEntrance.png`: solo la corrección de celdas de relleno (034 coherente; Venus todavía con el conjunto de tiles equivocado).
- `new_034.png`: todas las correcciones. Río/bosque coherentes en las celdas 1..25. El resto es relleno fuera de cámara.
- `new_VenusEntrance.png`: todas las correcciones. Bosque correcto y entrada al Venus Lighthouse.
- `new_040.png` frente a `new_040_noblend.png`: resplandor aditivo de antorchas (0x3f42, 0x1003).
- `new_080.png` frente a `_noblend`: agua mezclada 9/16 + 10/16.
- `new_016.png`: salas del Sol Sanctum, 0x3f44 en la capa 1.
- `new_134.png`: oscuridad opaca. `new_134_sceneblend.png`: con el 0x3f42/0xc04 de Altmiller, oscuridad a 4/16.
- `new_104.png` (anclaje a mitad de cámara), `cam_104_0_0.png`, `cam_104_128_208.png`: cielo con parallax.
- `new_147.png`: capa de arena en movimiento.
- `new_047.png`, `new_103.png`.
- `anim_034_f00..f40.png`, `anim_034.gif`, `anim_034_compare.png`: los fotogramas 0 y 24 de la animación del agua difieren.

## Cambios exactos recomendados para gsmap/project.py

1. **Recursos de escena** (sustituye el emparejamiento de `_read_directory`):
   - Expande `directory.s` en una lista ordenada de entradas. Aplica las macros exactamente: `group K, a,b` → `K_a, K_b`; `area S, L, maps` → `Field_MapNN…, Tileset_SPalette, Tileset_STiles<L…>`; `recolor P, maps` → `Field_MapNN…, Tileset_PaletteP`; `overlays`; `unused N` → N entradas; `resource , X` → X.
   - Pon `base = index('Field_Map001')`.
   - Cada fila de `src/field/layered.tsv` es `[header, palette, blk1, blk2, blk3, sheetD]`; asigna cada una a `entries[base+v]`.
   - Indexa por la etiqueta de la cabecera (`Field_MapNNN` / `Field_<Name>`) y usa la primera fila. Los mapas 108 y 110 tienen dos filas con paletas distintas (45/58 y 15/18). Expón la alternativa.
   - Resuelve las etiquetas mediante el `self.symbols` existente. Implementación de referencia: `dirmap.py`.
2. **Atlas:** tile absoluto `a = char_base*512 + (e&0x3ff)`.
   - Bloque `a//512` 1..3 → `[blk1, blk2, blk3][a//512-1]`. El bloque 0 son los tiles de las ventanas, así que se omite. 4 o más no es válido.
   - Las filas 14/15 de la paleta no son del mapa (interfaz). Muéstralas como transparentes o con un color de depuración.
3. **Celdas de relleno:** resuelve 0xfff → ordinal acumulado (regla en d) en `load_grid` para renderizar. Quita la comprobación `== EMPTY → skip`. Conserva la cuadrícula en bruto para guardar.
4. **Ventanas:** `gx = (layer.x//2 + bounds.left//2 + i) % 128`, y lo mismo para y (dar la vuelta, no omitir). Para capas con rate≠16 o drift≠0, usa la regla de anclaje a mitad de cámara de (a).
5. **Mezcla:** analiza blend.tsv (`control`/`level`/`jump`/`stop`/`end`). Compón de atrás hacia delante con las fórmulas de BLDCNT/BLDALPHA/BLDY de (b). Pon por defecto el control deslizante de opacidad de la capa en EVA/16 solo como aproximación (el resultado exacto es aditivo: `top*EVA + below*EVB`).
6. **Animación:** mantén un array mutable de tiles `vram[2048]` más `sheetD[512]`. Avanza los canales según (c). Expón un número de fotograma o un control de reproducción.
7. **Límites de cámara (opcional):** por defecto, los límites de la cabecera. Ofrece "recortar al contenido" o los límites de entrada de la escena. La correspondencia escena → índice de mapa sale de `src/field/scenes.s` (`scene name, code, area, kind, map`, donde map = la fila de `layered.tsv`). Los límites están en las tablas `struct SceneEntrance` de `src/scene/*.c`.

## Incógnitas

- Cómo funcionan las mezclas en los mapas cuyo script no tiene `control` (039/042/043/114/125). INFERIDO: alguna escena establece BLDCNT; no rastreado.
- Mezclas establecidas por la escena y reanudaciones de animación (`channel 0x8N`) por mapa: solo se rastreó Altmiller (134).
- Qué fila de `layered.tsv` usa una escena cuando un mapa tiene dos (108, 110). Ambas paletas son válidas.
- Por qué solo el desplazamiento vertical continuo rellena las 32 filas BG (`map_layers.c:600-604`, un XXX de alchemy). No importa para un render estático.
- No se tabularon los límites de cámara de mapas distintos de 034. `scenes.s` + las tablas de entradas los darían.
- Solo se comprobó la rama de la edición EN; `layered.tsv` no tiene variantes por edición.
