<!-- translated from docs/research/local-connections.md @ 9ab200ba52b5 -->
# Mappe locali: come si collegano e come vengono popolate (TBS, con note su TLA)

*Questa è una traduzione dell'originale inglese [local-connections.md](../../research/local-connections.md); se i due testi differiscono, quello inglese è il più aggiornato.*

Albero dei sorgenti: `alchemy/` (sola lettura). I percorsi qui sotto sono relativi a `alchemy/games/tbs/` salvo quando iniziano con `games/`, `tools/` o `out/`. "VERIFICATO" = letto nel codice/nei dati, oppure controllato da uno script su tutti i file; "DEDOTTO" = ricavato, non dimostrato.

## Riepilogo

1. Una **scena** è una riga di `gField_SceneTable` (`src/field/scenes.s`): id della risorsa dell'overlay, gruppo, variante, **riga della mappa a livelli**. L'id della scena è l'indice della riga. 201 righe. (VERIFICATO)
2. La riga della mappa indicizza `gMap_LayeredScenes` (`src/field/layered.tsv`, 186 righe). Ogni riga contiene 6 offset di risorse a partire da `ResourceId_Map001`: intestazione della mappa, palette, 3 fogli di tile, dati dei livelli. Quindi la tabella delle scene sceglie insieme la mappa **e** il tileset, e il numero di riga **non** è il numero di `map_NNN`. (VERIFICATO)
3. Il codice di ogni overlay (`scene/<place>.c`) restituisce cinque tabelle attraverso sei veneer di ingresso: Entrances, Exits, Placements, Events, Regions, più Initialize. I getter possono scegliere tra tabelle in base a un flag o all'id della scena. (VERIFICATO)
4. **Le uscite funzionano tramite eventi.** Il codice di collisione di una cella (1..239) corrisponde a un evento `EVENT_EXIT` (valore = tipo di uscita), oppure uno script di un evento al contatto chiama `Engine_EventRequestExit(kind)`, oppure si applica un riquadro di regione. La tabella delle uscite mappa poi (scena corrente, tipo) su (scena, ingresso). (VERIFICATO)
5. All'arrivo, la prima riga `SceneEntrance` il cui `entrance` corrisponde e il cui flag è impostato (o -1) piazza il gruppo e limita la telecamera. Se nessuna riga corrisponde, si usa la riga 0. (VERIFICATO)
6. **I marcatori** (`markers.tsv`: x, z, id) sono le posizioni di forzieri e Psynergy Stone. L'id è uguale al codice di collisione della cella in tutti i 417 marcatori. Ciò che un marcatore contiene viene dall'evento `SEARCH` della scena con quel trigger. (VERIFICATO)
7. **Gli NPC** sono righe `ScenePlacement`. Numero dell'attore = 8 + indice della riga, che la condizione della riga sia vera o no (il README delle scene dice il contrario). Le posizioni sono in 16.16. 396 righe su 2.321 sono a (0,0) e vengono posizionate dal codice; ci sono 405 chiamate in linea a `Engine_ActorSetPosition`. (VERIFICATO)
8. Ogni tabella di collegamento è un semplice inizializzatore C a livello di file fatto di letterali e macro. Si possono riscrivere tutte se lo strumento modifica sul posto, mantenendo i blocchi `#if`, i nomi simbolici e `const`. Gli id delle scene nelle parole di uscita sono **letterali numerici**. Nel codice sono simboli del linker `(s32)&SceneId_X`. (VERIFICATO)
9. TLA tiene ingressi, punti e limiti della telecamera per mappa in un 7° blocco della mappa (`scene_*.tsv`). I suoi overlay hanno per lo più una `SceneEntrance` di una sola riga. È una differenza del motore, quindi TBS non può passare agli stessi file. (VERIFICATO la disposizione, DEDOTTA la semantica)
10. Per aggiungere una nuova mappa o scena, prendi i 25 slot `unused` della directory e aggiungi righe in coda alle tabelle delle scene e dei livelli. Gli indirizzi fissi dei banchi e **~3,5–43 KB di margine nella ROM per edizione** (riempimento a 8 MB) sono i limiti rigidi. (VERIFICATO)

---

## 1. Collegamento scena ↔ mappa

### 1.1 Tabella delle scene (VERIFICATO)

`src/field/scenes.s:1-9`:

```
.macro scene name, code, area, kind, map
  .equiv SceneId_\name, (. - gField_SceneTable) / 8   ; id = row index
  .2byte \code   ; overlay resource id (= directory index, 0x36f..0x3ce)
  .byte \area, \kind  ; group, variant
  .2byte \map, 0      ; gMap_LayeredScenes row, reserved
```

- `struct SceneRecord` si trova in `include/field_runtime.h:18-26`: `resourceId, group, variant, mapIndex, reserved`, 8 byte.
- La tabella ha 201 righe (conteggio dello script). Le righe senza nome (`scene , 0x376, ...`) non ricevono un simbolo `SceneId_`.
- `Game_ResetForNewGame` (`src/object/object/scene.c:204-289`) esegue `record = &table[gGameState.scene]`, poi `gGameState.map = record->mapIndex` (`:286`), poi `Scene_LoadOverlay` → `Resource_LoadCode(table[scene].resourceId, &gOverlayArea)` (`:294-298`), poi `Scene_TakeExit(Field_RunScene(entrance))` (`:288`).
- `group` si usa per:
  - le regole della musica e dei nomi delle aree (`src/object/scene_rules.s`, lette da `Scene_ResolveInteractionResult` e `Scene_GetAreaNameIndex` in `src/object/object/encounter.c:279-345`);
  - azzerare i flag 0x300-0x3ff a un cambio di gruppo;
  - il flag "visitato" `(group & 0x7f) + 0x180` (`scene.c:344`), quindi un gruppo deve essere ≤ 0x7f.
- `variant` 2 indica le città. Disattiva la rigenerazione dei PP camminando e blocca Retreat (`src/object/object/run_scene.c`, `sceneVariant == 2`).
- Più scene possono condividere un overlay, per esempio Bilibin1/2/3 = 0x38b e AltinPeak1..11 = 0x3a4. Condividono anche un unico file `.c`.
- **Gli id delle scene nel codice C sono simboli del linker.** `scene_ids.h` dichiara `extern char SceneId_X;` e il codice confronta `gGameState.scene == (s32)&SceneId_X`, che carica da una parola del literal pool. Ci sono 487 usi di questo tipo in `src/scene/*.c`.
- Run_scene confronta `gGameState.map == (s32)&SceneId_Clear`, che vale 1, per riconoscere la mappa del mondo (`run_scene.c:45`). (VERIFICATO)
- **Gli id delle scene nelle tabelle di dati** (parole di uscita) sono interi semplici o i pochi nomi di `enum SceneId` in `include/field_scene.h:13-24`. Non sono simboli, quindi **non** seguono una rinumerazione. (VERIFICATO)

### 1.2 Selezione della mappa: tabella dei livelli (VERIFICATO)

`src/field/layered.s` esegue `.incbin "layered.table"`, costruito da `src/field/layered.tsv`. Le sue colonne sono `map0..map5:u16` e ha 186 righe. L'oggetto è piazzato in `rom_main_01` (objects.tsv:59).

`struct LayeredSceneEntry { u16 resources[6]; }` si trova in `src/field/field/map_layers.c:164`. `Map_LoadLayeredScene(index)` (`:211`) usa le sei risorse così:

| Colonna | Risorsa | Come si usa |
|---|---|---|
| [0] | intestazione della mappa | `Resource_GetTableEntry(resources[0] + ResourceId_Map001)` (`:233`) |
| [1] | palette | decodificata; il colore 0 (lo sfondo) viene mantenuto (`:337`) |
| [2] | foglio di tile | char block 1 (`:345-357`) |
| [3] | foglio di tile | char block 2 |
| [4] | foglio di tile | char block 3 |
| [5] | dati dei livelli | decodificati in `gMapLayerData` |

Tutti i valori sono offset a partire da `ResourceId_Map001`. Espandendo le macro della directory si risolvono per nome (script di prova):

- le righe 0 e 1 sono `Field_Map001` + `Blank*`. Le usano Title, Clear e WorldMap; il percorso della mappa del mondo non le carica mai.
- la riga 2 è `Field_Map000` + `Set00{Palette,TilesA-D}`;
- la riga 5 è `Field_Map004` + `Set03*`;
- la riga 12 è `Field_Map010` + palette/A/B/C di Set09 + **Set08TilesD**.

123 righe su 186 non sono sei risorse consecutive: una riga può mescolare fogli di set diversi, e le ricolorazioni riutilizzano i fogli. Quindi l'editor deve trattare la riga come sei riferimenti indipendenti.

`map_NNN/` prende il nome da `Field_MapNNN` (la numerazione della directory, `src/map/README.md` "The map numbers are the directory's"). Per esempio, la scena ValeHome (id 5) ha mapIndex 4 → `Field_Map003` = `src/map/map_003/`. Il `markers.tsv` di quella mappa (13,44,100) corrisponde all'evento `SEARCH(...)` di ValeHome con trigger 100 (`src/scene/vale_home.c`, eventi).

Due mappe portano nomi di luogo invece di numeri: `gondowan_passage/` (`Field_GondowanPassage`) e `venus_entrance/` (`Field_VenusEntrance`). Delle 182 risorse di mappa distinte referenziate, 8 sono usate da più di una scena.

### 1.3 Directory delle risorse (VERIFICATO)

`src/system/resource/directory.s` contiene le macro `resource`, `group`, `area SET, sheets, maps...`, `recolor`, `overlays`, `unused` (`:1-51`).

- L'id di una voce è la sua **posizione**: `ResourceId_X = (. - Resource_DirectoryTable)/4`.
- `area SetNN, ABCD, mmm` emette `Field_Mapmmm`, poi `Tileset_SetNNPalette`, poi `TilesA..D`.
- Gli overlay vengono per ultimi, `overlays 36F … 3CE` (96 voci, `:299-306`), seguiti da `unused 25` (`:307`). Ogni slot non usato è `.4byte 0`.
- `Resource_GetTableEntry(i)` è semplicemente `Resource_DirectoryTable[i]` senza controllo dei limiti (`src/runtime/runtime/system.c:150-152`).
- La directory sta all'inizio di `rom_tail_02`, che è **fissata** a 0x08320000 in EN (`main.ld`, ultimo `ABSOLUTE`; `out/tbs-en/tbs-en.map:7353`).
- I dati delle mappe (`map_NNN/map.s`, che porta anche i fogli del tileset di sua proprietà), poi `src/system/overlay/overlays` seguono nell'ordine di `rom_tail_02` (objects.tsv:436-631).
- Inserire una voce di directory prima degli overlay rinumera ogni risorsa successiva. Questo rompe gli id degli overlay in scenes.s (`0x36f`…) e ogni offset di `layered.tsv` dopo il punto di inserimento. Usa gli slot `unused`: indici 0x3cf..0x3e7. (DEDOTTO dalla macro posizionale; l'aritmetica è VERIFICATA.)

### 1.4 Overlay: entry, import, objects.tsv, overlays.tsv, linker (VERIFICATO)

`src/scene/README.md` e `src/system/overlay/overlay.ld` descrivono gli overlay.

- **Entry** (`scene/entry/<place>.s`) sono sei righe `overlay_veneer` in un ordine fisso: Initialize, GetEntrances, GetExits, GetPlacements, GetEvents, GetRegions. Ogni veneer è `ldr r4; bx r4; .4byte target` (`src/system/overlay.s:5-11`). Il motore li legge come `struct SceneEntries` (`include/field_runtime.h:42-57`): una parola di veneer più un puntatore a funzione ciascuno, 48 byte. Chiama `gOverlayArea.entrances()` e così via.
- **Import** (`scene/import/<place>.s`) è `.set overlay_imports,1`, poi `.set import.NAME,1` per ogni routine del motore che il C chiama, poi `.include overlay.inc`. `overlay.inc` contiene l'elenco principale ordinato di ~405 righe `import NAME, TARGET`. Solo le righe impostate emettono uno stub (`src/system/overlay.inc:9-25`). Gli overlay non possono chiamarsi a vicenda.
- **objects.tsv** dà a ogni overlay tre righe `text` in ordine (`entry/<place>`, `<place>`, `import/<place>`) con la prima colonna = id dell'overlay in esadecimale (per esempio `374 text games/tbs/src/scene/vale_home`). Può seguire una riga `bss` facoltativa (`.bss COMMON`, oppure `resource_<id>_overlay .bss` da `src/system/overlay/ovl_<id>.s`).
- **overlays.tsv** dà l'intestazione della sezione di output `.bss` (per esempio `.bss ALIGN(16)`) per i 36 overlay che hanno righe bss. `tools/ags-objects/ags-objects.c:165-205` fallisce con "bss header and rows disagree" se esiste solo una delle due.
- **Collegamento.**
  - Ogni overlay viene collegato a 0x2008000 rispetto a `symbols.elf` (Makefile:209-219).
  - Dentro un overlay viene prima tutto il `.text`, poi tutto il `.rodata`, poi tutto il `.data`, nell'ordine degli oggetti (passate di `render()` in `ags-objects.c`). Quindi le tabelle `const` vanno in `.rodata` e quelle non const in `.data`.
  - L'immagine viene compressa da `tools/ags-overlays` in `resource_<id>.lz` e incorporata da `src/system/overlay/overlays.s` (`Resource_Overlay36F: .incbin ...` più byte residui `PACKER:` per edizione).
  - `Resource_LoadCode` la decodifica in `gOverlayArea` e corregge i BL Thumb (`system.c:228`).
- L'area degli overlay è di 32 KB, e codice + rodata + data + bss devono starci. Misurati da `out/tbs-en/overlays/*.map`, i più grandi sono 0x3b1 con 32.648 B (120 B liberi), 0x373 Vale con 30.764 e 0x3c8 con 30.732. (VERIFICATO dall'output della build.)

### 1.5 Altre tabelle legate alle scene (VERIFICATO)

Queste usano i simboli `SceneId_` o il gruppo, quindi restano corrette quando si aggiungono righe in coda:

- `src/object/scene_rules.s`:
  - `gScene_InteractionRuleTable` (musica: `scene_cue` / `group_cue`);
  - `gScene_AreaNameRules` (`scene_name` / `group_name`);
  - `gParty_PairResolveRules` (`return_to`, punti di ritorno dopo una sconfitta);
  - `gBattle_BackdropScenes`.
- `src/object/location_rules.s` `gBattle_LocationRules`: zone degli incontri per (scena, ingresso, flag).
- `src/scene/world_map.c` `gWorldMapExits` (`SCENE_EXITS(2)`…) e i suoi eventi `EVENT_EXIT` (44): come la mappa del mondo entra nelle scene locali.

---

## 2. Uscite e ingressi

### 2.1 `struct SceneEntrance` (24 byte, `include/field_scene.h:54-70`) (VERIFICATO)

| # | Campo | Tipo | Significato |
|---|---|---|---|
| 1 | entrance | s16 | il numero di ingresso che la parola di uscita nomina; -1 termina la tabella |
| 2 | requiredFlag | s16 | -1, oppure un flag che deve essere **impostato** (semplice `GameFlag_TestFar`, senza codifica 0x1000) |
| 3 | x | s16 | pixel |
| 4 | y | s16 | pixel (altezza; diverso da zero in 20/1520 righe) |
| 5 | z | s16 | pixel ("giù" sulla mappa) |
| 6 | facing | u16 | 1/65536 di giro (`enum Facing`, passi di 0x2000) |
| 7 | unused1 | s16 | 0 ovunque, non letto |
| 8 | cameraLeft | s16 | pixel, -1 = mantieni il limite dell'intestazione della mappa |
| 9 | cameraTop | s16 | idem |
| 10 | cameraRight | s16 | idem |
| 11 | cameraBottom | s16 | idem |
| 12 | unused2 | s16 | 0 ovunque, non letto |

`Scene_ApplyEntrance` (`src/object/object/run_scene.c:461-505`):

1. Cerca `entrance == gGameState.entrance && (flag == -1 || flag set)`. Se niente corrisponde, usa la **riga 0**.
2. Salvo `FLAG_KEEP_PARTY_POSITION`, scrive `gGameState.x/y/z = value << 16` e `heading = facing`.
3. Limita i bordi della telecamera, con una vista minima di 240×160.

Statistiche su 189 tabelle / 1.520 righe:

- 3 righe usano un flag;
- 1.023 impostano i limiti della telecamera;
- entrambi i campi non usati sono 0 ovunque;
- la colonna entrance è una costante simbolica in 21 righe.

### 2.2 Come scatta un'uscita (VERIFICATO)

Ci sono tre modi per lasciare una scena:

1. **Cella di uscita.** `Field_ProcessStep` legge il codice di collisione della cella del capogruppo (`src/object/object/step.c:240-249`).
   - I codici `1..239` (`STEP_EVENT_FIRST/LAST`, `:19-27`) impostano `work->action = code`.
   - `Scene_RunTouchOrExit(code)` (`src/object/object/events.c:333-385`) cerca prima un evento `EVENT_TOUCH` con `trigger == code`. Se esiste, esegue il suo messaggio o script, e lo script riceve il codice come argomento.
   - Altrimenti cerca `EVENT_EXIT` con `trigger == code`: riproduce il suono dell'uscita (bit 5..4 del control: 0 normale, 0x20 → SE_128 + effetto 26, 0x30 → SE_129 + effetto 25, 0x10 nessuno) e imposta `work->exit = event.value`, il **tipo di uscita**.
2. **Script.** Uno script di contatto/dialogo/Psicoenergia chiama `Engine_EventRequestExit(kind)`. Questo è importato come `Event_SetExitRequestFar` (`src/system/overlay.inc:321`). Ci sono circa 200 punti di chiamata. Le porte tipiche usano `TOUCH_WALKING_INTO(FACING_NORTH)` sul codice di collisione della porta, animano le celle della porta, fanno entrare il capogruppo e poi richiedono l'uscita (`vale_home.c:444-471`). Le coordinate dell'animazione delle porte sono **argomenti di chiamata in linea** (`Event_OpenDoorAndWalkThrough(44, 7, 248, 279)`, `Map_CopyCellsTo(...)`) oppure array `u16 ...DoorCells[]` `MAP_CELL_STEP(srcX,srcY,w,h,frames)` (`include/field_event.h:59-61`).
3. **Regione.**
   - `struct SceneRegion` (`include/field_runtime.h:30-37`, 16 B) è `minX,minY,minZ,maxX,maxY,maxZ` (pixel; min incluso, max escluso), `condition` e `value` = tipo di uscita. minX -1 termina la tabella.
   - Viene controllata da `Field_CheckExitRegions` (`step.c:135-186`) ogni volta che il codice della cella del capogruppo è diverso da zero.
   - Ci sono 14 tabelle di regioni, 38 righe; la maggior parte delle scene restituisce NULL.

`Field_RunScene` restituisce `work->exit`. `Scene_TakeExit(kind)` (`src/object/object/scene.c:25-89`) poi:

- scorre la tabella delle uscite dell'overlay cercando la parola di intestazione uguale all'id della scena corrente;
- prende la prima parola di uscita il cui `kind == exitKind` o il cui tipo è `0xff` (qualsiasi), **e** il cui flag non è impostato (`SCENE_EXIT_IF`: segue la parola del flag; l'uscita viene **saltata finché il flag è impostato**);
- ripiega sulla scena della prima uscita, con ingresso 0, se raggiunge prima una parola con tipo 0 o la fine (0x1ff).

### 2.3 Codifica delle parole di uscita (VERIFICATO)

`include/field_scene.h:72-77`:

```
SCENE_EXITS(scene)              = scene                         // header
SCENE_EXIT(kind, scene, ent)    = kind<<20 | ent<<12 | scene
SCENE_EXIT_IF(k, s, e, flag)    = SCENE_EXIT(k,s,e) | 0x10000000, flag   // two words
SCENE_EXITS_END                 = 0x1ff
```

| Campo | Bit |
|---|---|
| scene | 0..11 (il ripiego maschera solo 9 bit, e 0x1ff è la fine, quindi gli id delle scene devono essere < 511) |
| entrance | 12..19 (0..255) |
| kind | 20..27 (1..254 reali, 0xff qualsiasi, 0 = **intestazione**) |
| flag-follows | bit 28 |

**`SCENE_EXIT(0, N, 0)` è un'intestazione di scena, identica a `SCENE_EXITS(N)`.** Le tabelle degli overlay condivisi la usano: `gAltinPeak_Exits` (`altin_peak.c:2671-2722`) contiene gli elenchi di uscite di 11 scene dopo un unico `SCENE_EXITS(77)`. Uno script ha trovato le intestazioni per 200 delle 201 scene degli overlay; solo la scena senza nome 59 (overlay 0x39d) non ne ha. TLA tratta inoltre una parola di flag -1 come "sempre" (`games/tla/src/field/common/take_exit.c`).

### 2.4 Catalogo delle tabelle in `src/scene/*.c` (+ `common/*.h`) (VERIFICATO da script)

| Tipo (da identificare per **tipo**, i nomi variano: `gX_Exits`, `gXExits`, `gXExits1`…) | Tabelle | Righe | Tabelle con `#if` all'interno | `const` |
|---|---|---|---|---|
| `struct SceneEntrance` | 189 | 1,520 | 0 | 5 |
| tabelle di uscite `u32` (`SCENE_EXITS`) | 99 | 1,479 parole di uscita | 1 | 5 |
| `struct ScenePlacement` | 274 | 2,321 | 4 | 18 |
| `struct SceneEvent` | 263 | 5,891 | 10 | 13 |
| `struct SceneRegion` | 14 | 38 | 3 | 1 |
| Array di passi di porte/celle (`u16` `MAP_CELL_STEP`, celle impacchettate `u32`, `struct MapCellAnim`) | ~10 | — | — | — |

Tipi di evento per numero di righe:

- `PSYNERGY_ON_ACTOR` 1585
- `EVENT_TALK` 1374
- `EVENT_EXIT` 903
- `EVENT_TOUCH` 531
- `SEARCH(..)` 506
- `TOUCH_WALKING_INTO` 493
- control esadecimali grezzi come `0x31`/`0x21` (uscita con bit del suono), `0xc4f3`, `0x8413`: circa 220

Sono tutti array inizializzati a livello di file, una riga tra graffe per record (uscite: una macro per parola, a volte due per riga con clang-format, per esempio `world_map.c:2802`). I getter li restituiscono, eventualmente scelti per flag o scena (`vale_home.c:104-160`, `bilibin.c:106-114`). Le tabelle dei piazzamenti sono per lo più **non const** perché `Scene_AssignViewFlags` scrive durante l'esecuzione la `condition` delle righe la cui condizione è 0 (`src/object/object/actors.c:325`).

---

## 3. Marcatori (forzieri, Psynergy Stone)

- **Formato** (VERIFICATO). `markers.tsv` ha l'intestazione `x:u8	z:u8	event:u8`, righe di colonna della cella, riga della cella e id, e termina con la riga `0xff 0xff 0xff`. È codificato grezzo (`markers.table`, **non** LZ) e incluso con incbin come 6° blocco dell'intestazione (`src/map/map_004/map.s:25`). I valori possono essere decimali o esadecimali `0x`: `map_002/markers_es.tsv` differisce da `markers.tsv` solo nella formattazione dei numeri.
  - Ci sono 118 file di marcatori: 106 di base e 12 varianti per edizione (`*_ja/_de/_es.tsv`, scelte con `.ifdef TBS_EDITION_*` in map.s).
  - 76 file map.s puntano al `map_000/markers.table` vuoto.
- **Caricatore** (VERIFICATO). L'elenco dei marcatori non viene decodificato: `work->script = header + header->markers` (`map_layers.c:258`). `Field_PlaceMapMarkers` (`src/object/object/markers.c:30-131`), chiamata da `run_scene.c:73`, fa quanto segue:
  - Si considerano solo gli id **100..239**.
  - Per ciascuno prende il primo evento della scena con `trigger == id`:
    - `control & 0x1ff == 19` (`SEARCH(SEARCH_CHEST)`): crea l'oggetto **20** (forziere) al centro della cella `(col<<20)+0x80000`, agganciato al terreno. Se il flag della condizione dell'evento è impostato, il forziere è mostrato aperto (animazione 2); se il flag è impostato e il valore è un mimic (`0x5xxxxx`), non viene piazzato affatto.
    - altro `SEARCH` con valore `0x300000` (`FIND_PSYNERGY_STONE`) il cui flag non è impostato: crea l'oggetto **28** (pietra).
  - Se ne piazzano al massimo `MARKER_MAX` = 10. Un marcatore senza evento corrispondente non piazza nulla.
- **Id = codice di collisione** (VERIFICATO). Tutte le 417 righe di marcatori in TBS hanno `grid_collision[x,z] == id` (script di prova). La ricerca stessa si basa sul codice di collisione della cella davanti (`Scene_FindEvent(EVENT_SEARCH, code)`, `events.c:111`, `Field_SearchTile` `events.c:429`). Un marcatore senza il codice di collisione corrispondente mostrerebbe un forziere che non si può aprire. **L'editor deve scrivere entrambi.**
- **Contenuto e flag** (VERIFICATO). Il contenuto sta nella tabella degli eventi della scena: `{ SEARCH(SEARCH_CHEST), <id>, <opened-flag>, FIND_ITEM(ITEM_X) | FIND_COINS(n) | FIND_PSYNERGY_STONE | FIND_MESSAGE(m) | 0x5xxxxx mimic | EVENT_SCRIPT(fn) }` (`include/field_scene.h:118-217`).
  - La condizione è il flag di "aperto". Secondo il README, la maggior parte dei flag dei forzieri è ≥ 0xe00. Il flag viene impostato quando si prende il contenuto del forziere (`events.c:500-560`).
  - Il bit 16 del valore significa "il gruppo non può aprirlo".
  - Ci sono 135 righe `SEARCH(SEARCH_CHEST)` e 17 righe `FIND_PSYNERGY_STONE`. Alcune pietre usano righe `SEARCH_FACING(...)` con una costante con nome `TRIGGER_STONE`, e alcune pietre sono semplici script (`Event_UsePsynergyStone` di ValeHome).
- I codici 242..247 sono messaggi fissi di "punto di ricerca", 250 è terreno pericoloso e 252..254 sono sporgenze/punti di arrampicata (`step.c:19-27`, `events.c:387-418`). 0xff è un muro.

---

## 4. NPC e oggetti

`struct ScenePlacement` (24 B, `include/field_scene.h:81-98`) (VERIFICATO):

| Campo | Tipo | Significato |
|---|---|---|
| sprite | s16 | tipo di oggetto/sprite; 0-7 = personaggi del gruppo (slot propri), -1 termina la tabella |
| condition | s16 | -1 sempre; `flag\|0x1000` = flag impostato; altrimenti flag non impostato; 0 = "in vista" (riscritto da `Scene_AssignViewFlags`) |
| behavior | s32 | `ACTOR_STAND`=1, `ACTOR_WANDER`=2, piccoli interi (per esempio 3), oppure un puntatore a uno script di azioni SC_ `s32 ...[]` |
| x, y, z | s32 | pixel in 16.16 tramite `PIXELS(n)` |
| facing | u16 | 1/65536 di giro |
| talkFacing | u8 | TALK_FACE_PARTY 0, _AND_BACK 1, KEEP 2, 3 segue il capogruppo |
| flags | u8 | bit 0 `PLACEMENT_SHARE_PREVIOUS_SPRITE` |

**Generazione** (`src/object/object/actors.c:75-180`, `ObjectTable_ResetForObject` `:217`) (VERIFICATO):

- Il capogruppo viene generato da `gGameState`, poi la tabella dallo slot 8.
- **`actorIndex = slot++` viene eseguito prima del test della condizione (`:105-107`)**, quindi una riga saltata usa comunque il suo numero: **attore = 8 + indice della riga** per gli sprite > 7. I trigger `EVENT_TALK` e `PSYNERGY_ON_ACTOR` nominano questi numeri, quindi riordinare o inserire righe rinumera ogni evento di dialogo.
- Altezza: y viene aggiunta all'altezza del terreno fuori dalla mappa del mondo.
- Il massimo è 58 attori piazzati (slot 8..65).
- Le righe con flag dei Djinn (48..127) richiedono anche `condition+80`.

Conteggi della colonna behavior su 2.321 righe: STAND 1,705, WANDER 132, intero 306, simbolo di script 178.

- 396 righe sono a x=z=0. Sono attori che il codice di Initialize posiziona o sposta.
- Il posizionamento in linea è comune:
  - `Engine_ActorSetPosition`: 405 chiamate
  - `OBJ_POS_SET(no,x,z)` (pixel, `include/event.h:13`): 119
  - `Engine_ObjectCreate(kind,x,y,z)`: 53, per effetti e oggetti aggiuntivi
  - `Engine_ActorWalkTo`: 36

Quindi il piazzamento statico degli NPC è dato, ma la messa in scena dei filmati è codice.

---

## 5. `scene_*.tsv` di TLA (blocco della mappa, non overlay)

`map.s` di TLA ha **7** blocchi: metatiles, shapes, grid, shape_grid, animation, blend, scene (`games/tla/src/map/map_008/map.s`). Non c'è un blocco markers e TLA non ha `markers.tsv`.

Il blocco scene è `scene.parts.lz`, compresso con LZ. `scene.tsv` elenca le sue parti in ordine: `SCENE_HEADER, SCENE_POINTS, SCENE_ENTRANCES, SCENE_PATCHES, SCENE_BOUNDS`. È presente in 286 mappe.

| File | Colonne | Note |
|---|---|---|
| `scene_header.tsv` | `entrances:u16 patches:u16 bounds:u16 none:u16` | offset in byte dall'inizio del blocco; i punti iniziano a 8. Controllato per tutte le 286: entrances = 8 + size(points), patches = entrances + size(entrances), bounds = patches + size(patches); `none` = 0 ovunque (VERIFICATO) |
| `scene_points.tsv` | `id:u8 x:u16 z:u16` | termina con `0xff`; 579 punti, id per lo più 1..28, 99 ×10. Significato sconosciuto (DEDOTTO: punti di script o della telecamera; non forzieri, che in TBS sono basati sulle celle) |
| `scene_entrances.tsv` | `id:u8 x:u16 z:u16 flags:u8` | 1,970 righe. DEDOTTO: equivalente alla `SceneEntrance` di TBS (id, x, z). Il nibble basso dei flag = facing>>12 (valori 4=S 1105×, 12=N 685×, 0=E, 8=O, 2/6/14 diagonali), e il bit 4 (16) è un flag aggiuntivo (28, 20) |
| `scene_patches.tsv` | `key:u16 source_x:u8 source_y:u8 x:u8 y:u8 width:u8 height:u8` | termina con `0xffff`; **vuoto in tutte le 286** |
| `scene_bounds.tsv` | `left:s8 top:s8 right:s8 bottom:s8` | di solito una riga + `-1`. DEDOTTO: limiti della telecamera in celle da 16 px (map_008: 0,0,40,34) |

Dal lato degli overlay, le scene di TLA hanno ancora Exits/Placements/Events in C (`games/tla/src/scene/<place>/data.c`). 86 delle 97 tabelle `SceneEntrance` hanno una sola riga, quella di ripiego, il che suggerisce fortemente che il motore di TLA prenda le posizioni dal blocco della mappa (DEDOTTO; il lettore non è decompilato). Uno script che cercava di abbinare le coppie (scena, ingresso) delle uscite di TLA agli id degli ingressi delle mappe con uno scostamento fisso scena→mappa non è stato conclusivo, perché la tabella dei livelli di TLA non è nei sorgenti.

**TBS migrerà?** DEDOTTO **no**, almeno non verso gli stessi file. Le mappe nella ROM di TBS hanno 6 blocchi con i marcatori, e il suo motore legge gli ingressi dagli overlay, quindi i dati stanno dove li mette la ROM. Cronologia git:

- File delle mappe di TLA: "TLA: the four field maps still copied, from editable tables" (a20313083f) e altri.
- Il lavoro recente sulle scene di TBS è umanizzazione del C ("Align scene table getters with the engine contracts", db7167f0b0).

Nessuno di questi menziona lo spostamento delle tabelle delle scene in TSV.

---

## 6. Aggiungere una nuova mappa o scena (lista di controllo)

Preferisci **aggiungere in coda** invece di inserire, ovunque.

1. **Dati della mappa.**
   - Crea `src/map/map_180/`: `map.s` (`.global Field_Map180`, `map_header`, 3×`map_layer`, 6×`map_block`, incbin) e i TSV.
   - Riutilizza un tileset esistente (nessun nuovo foglio) oppure aggiungi fogli e una palette dopo di esso.
   - I blocchi non usati sono `map_block Field_Map180` con offset 0. Per i marcatori, punta a `map_000/markers.table` o al tuo.
2. **objects.tsv.** Aggiungi `main rom_tail_02 games/tbs/src/map/map_180/map` **prima** della riga `system/overlay/overlays` (objects.tsv:631). Questo dà l'ordine nella ROM; nessun indirizzo è fissato dopo 0x08320000.
3. **directory.s.** Trasforma un `unused` in `resource , Field_Map180`, e in palette/tile se sono nuovi; riduci `unused 25` di conseguenza (`:307`). I nuovi id sono 0x3cf+ e gli id esistenti non si spostano.
4. **layered.tsv.** Aggiungi in coda una riga di offset a partire da `ResourceId_Map001`: mappa, palette, tile ×3, dati dei livelli. Il suo indice di riga è il `map` della scena. È piazzata in `rom_main_01`, con spazio libero prima dell'inizio fisso di `rom_main_02`: EN 4.020 B, DE 1.204 B, ES/FR 1.972 B (12 B per riga).
5. **Overlay della scena** (per dare alla scena il proprio codice):
   - `src/scene/<place>.c`, `entry/<place>.s` (6 veneer), `import/<place>.s` (import nell'ordine di `overlay.inc`);
   - prototipi in `include/unit/scene/<place>.h` (ne esistono 91);
   - righe di objects.tsv `3cf text .../entry/<place>`, `3cf text .../<place>`, `3cf text .../import/<place>`, più un eventuale `3cf bss ...` con una riga di intestazione in `overlays.tsv`;
   - `src/system/overlay/overlays.s`: `Resource_Overlay3CF: .incbin "overlays/resource_3cf.lz"` + `.balign 4`;
   - directory: uno slot `unused` diventa `resource , Resource_Overlay3CF`.
   - In alternativa, riutilizza un overlay esistente come variante, come le stanze di Altin Peak: aggiungi una riga di scena con lo stesso codice e dirama in base a `SceneId_` nei getter.
6. **scenes.s.** **Aggiungi in coda** `scene NewPlace, 0x3cf, <group>, <variant>, <layered row>`. Il nuovo id è 201, quindi tutti gli id numerici esistenti restano validi. La tabella è in `rom_main_04`, 8 B per riga; spazio libero prima del banco fisso: EN 3.448 B, DE 1.040 B. Aggiungi `extern char SceneId_NewPlace;` a `include/scene_ids.h`. Il gruppo deve essere ≤ 0x7f (flag "visitato"). Gli id delle scene devono essere < 0x1ff (ripiego della parola di uscita).
7. **Collegamenti.**
   - Aggiungi una parola di uscita nella tabella delle uscite di ogni vicino sotto la **sua** intestazione: `SCENE_EXIT(kind, 201, entrance)`.
   - Aggiungi una riga `EVENT_EXIT` (o uno script al contatto) negli eventi del vicino per il codice di collisione che dipingi sulle celle di uscita.
   - Dipingi quel codice nel `grid_collision.tsv` del vicino.
   - Rispecchia lo stesso nella nuova scena: intestazione `SCENE_EXITS(201)`, le sue uscite, ingressi i cui numeri corrispondono a quelli nominati dalle parole di uscita dei vicini, piazzamenti, eventi.
8. **Regole.** Musica (`scene_cue`/`group_cue`), nome dell'area (`scene_name`/`group_name`), ritorno dopo una sconfitta (`return_to`) e sfondo in `src/object/scene_rules.s`; incontri in `src/object/location_rules.s`. Senza righe ottieni MUS_018, nessun nome, nessun incontro e l'ultimo sfondo.
9. **Testo.** Aggiungi i messaggi a `text/<lang>.po`, con un `msgctxt` per ogni simbolo di messaggio.
10. **Budget** (VERIFICATO, `out/tbs-*/tbs-*.map`).
    - La ROM è riempita fino a 0x08800000 (Makefile:134). Spazio libero alla fine: EN 11.076 B, IT 11.040, DE 10.108, ES 4.128, FR 3.584, JA 43.100.
    - Una nuova mappa più un overlay probabilmente supereranno questo spazio, quindi l'`ROM_END_tbs` di 8 MB andrà alzato. `MEMORY ROM` permette già 32M (`main.ld`). Questo rende la ROM non corrispondente. (DEDOTTO: sicuro; non provato.)
    - RAM dell'overlay ≤ 32 KB.

---

## 7. Fattibilità della generazione di codice (per tabella)

Regola generale: i valori si compilano in byte fissi, quindi formattazione e spazi sono liberi. L'esattezza byte per byte dipende da:

- lo stesso ordine delle righe;
- gli stessi valori, inclusi quelli simbolici (`MSGNO(Msg…)` si risolve in numeri di messaggio, `EVENT_SCRIPT(fn)` in rilocazioni, i nomi dei flag da `flags.h`);
- lo stesso `const`, che sceglie il piazzamento in `.rodata` o `.data`;
- gli stessi blocchi `#if TBS_PATCH_n` / `LANGUAGE` per edizione e per patch;
- lo stesso ordine delle tabelle nel file.

| Tabella | Sicura da riscrivere? | Come fare il round-trip |
|---|---|---|
| SceneEntrance | Sì, molto regolare: 12 campi letterali, 21 nomi di ingresso simbolici | modifica di una riga `{...}` che preserva il CST; mantieni un simbolo quando il valore non cambia |
| Uscite `u32[]` | Sì, con attenzione: solo macro, ma `#define` per scena (`ROOM_ENTRANCE(exit)`, `LUNPA_EXIT_TO_*`), intestazioni `SCENE_EXIT(0,N,0)`, `#if !TBS_PATCH_3` (vale_home.c) | analizza le chiamate di macro, valutale in parole, riemetti solo le chiamate toccate; non fondere mai `SCENE_EXIT(0,..)` e `SCENE_EXITS` |
| ScenePlacement | Per lo più: `PIXELS(n)`, `FACING_X + FACING_STEP`, nomi dei personaggi (`GARET`), simboli di script, 4 tabelle con `#if` | modifica i campi sul posto; mantieni l'ordine delle righe (numeri degli attori) |
| SceneEvent | La più difficile: macro a campi di bit più ~220 control esadecimali grezzi, simboli di messaggi e funzioni, 10 `#if` | tratta come token opachi tranne i campi modificati (trigger, condition, valore FIND_) |
| SceneRegion | Sì, piccola: 3 con `#if` | sul posto |
| markers.tsv | Sì, file di dati | riscrivi il TSV; decimale ed esadecimale sono entrambi accettati |
| scenes.s / layered.tsv / directory.s | Sì, orientati alle righe | solo aggiunte in coda |

Verifica:

- Ricompila ed esegui `make compare` / `compare-tbs` (Makefile:48-51).
- Per controlli rapidi, confronta le sezioni di `out/tbs-<ed>/overlays/resource_<id>.elf` prima e dopo una riscrittura che non cambia nulla. Una pura riformattazione deve dare un output `.bin` e `.lz` dell'overlay identico.
- Evita di rigenerare file interi: contengono codice, regioni `// clang-format off`, commenti e blocchi `#ifdef UBFIX`.

---

## 8. Incognite

- Chi scrive `EventWork.touchedTrigger` (`include/field/event_work.h:26`), che gli script leggono. Non ha uno scrittore con nome nel codice principale (DEDOTTO: il codice toccato).
- I piccoli interi di `ScenePlacement.behavior` diversi da 1 e 2 (3 è comune): la semantica di `ObjectMotion_SetActionCallback` non è tracciata qui.
- La tabella completa dei tipi di sprite (gli id di oggetto 20 = forziere, 28 = pietra e 0x8000 = telecamera sono VERIFICATI da markers.c e actors.c).
- TLA: il significato di `scene_points`, del bit 4 di `scene_entrances.flags`, le unità dei limiti, la risoluzione scena→mappa e la 6ª colonna della tabella delle scene (anch'essa XXX in `games/tla/src/field/README.md`).
- Se gli slot `unused` della directory e una ROM più grande di 8 MB funzionino su hardware ed emulatori (DEDOTTO sì).
- La scena 59 (senza nome, 0x39d) non ha un'intestazione di uscite. Le uscite lì lasciano la scena invariata (`Scene_TakeExit` mantiene lo stato quando non trova alcuna intestazione).

---

## 9. Modello di dati proposto per l'editor

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

Operazioni di modifica:

- **Spostare una cella di uscita:** codice in grid_collision più la riga `EVENT_EXIT`.
- **Cambiare destinazione:** modifica la parola di uscita.
- **Aggiungere un forziere:** riga del marcatore, codice di collisione e un evento `SEARCH(SEARCH_CHEST)` con un flag nuovo ≥ 0xe00.
- **Spostare un NPC:** modifica x/z del piazzamento, e avvisa se x=z=0 nella riga significa che lo posiziona il codice.

Convalida su tutte queste operazioni:

- che i numeri di ingresso referenziati da ogni parola di uscita esistano negli Entrances della destinazione (altrimenti si ripiega sulla riga 0);
- gli spostamenti dei numeri degli attori quando si inseriscono righe di piazzamento;
- il limite di 10 marcatori;
- i budget di 32 KB dell'overlay e della ROM.

---
