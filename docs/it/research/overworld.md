<!-- translated from docs/research/overworld.md @ 52c37110966a -->
# Ricerca sull'overworld (mappa del mondo): Golden Sun TBS, dai sorgenti di alchemy

*Questa è una traduzione dell'originale inglese [overworld.md](../../research/overworld.md); se i due testi differiscono, quello inglese è il più aggiornato.*

Albero dei sorgenti: `~/gs_project/alchemy` (sola lettura). I percorsi qui sotto sono relativi a
`games/tbs/` salvo quando iniziano con `games/` o `tools/`. Etichette: **[V]** = VERIFICATO (letto nel codice o nei dati,
o confermato dal rendering del prototipo), **[I]** = DEDOTTO.

Script e rendering del prototipo (di prova, non fanno parte di questo repository):
`(a scratch folder)`
(`render_world.py`, `render_area.py`, `render_gameplay.py`, `world_mixed.png`, `world_annotated.png`, `collision.png`, `terrain_kind.png`, `north_compare.png`).

## Riepilogo

1. Tutto il terreno dell'overworld è un'unica tabella: `src/map/world/blocks.tsv`, 320 righe x 512 colonne di **parole di cella** u32 in esadecimale, costruita da `tools/ags-graphics` (forma `blocks`) in `blocks.blocks`, che `src/map/map.s` include con incbin come `Field_PerspectiveDataA` [V].
2. La tabella contiene 640 **chunk** di 16x16 celle (il codice chiama un chunk "tile"). I chunk 0-319 sono il livello 0 (BG3, terreno), i 320-639 sono il livello 1 (BG2, sovrapposizione: montagne, alberi, costa), con chunk del livello 1 = chunk del livello 0 + 320 [V].
3. Il mondo è 16x16 chunk = 256x256 celle; una cella misura 32 pixel del mondo (16 pixel di schermo/BG), quindi il mondo è 8192x8192 px del mondo e si avvolge [V]. Gli id di chunk 0-255 stanno nel chunk del mondo (id%16, id//16); i 256-319 sono alternative scambiate dal codice [V].
4. Una parola di cella: bit 0-15 id del blocco, bit 16-23 codice di passo/evento, bit 24-30 tipo di terreno (regione degli incontri; 21 = set grafico della neve), bit 31 flag del banco di comportamento [V].
5. Un id di blocco indicizza `src/map/default/cells.tsv` (4386 blocchi da 4 byte: numeri di tile 8x8 TL, TR, BL, BR) [V]. Le tile sono a 8bpp, 256 per livello: set A = `tiles_a+b` (livello 0) e `tiles_c+d` (livello 1), palette `palette_a.png` (224 colori); set B (neve) = `tiles_f..i`, `palette_b` [V].
6. Il rendering è in modalità 2 (BG2+BG3 affini) con matrici per scanline via HBlank-DMA per la prospettiva "mode 7"; un rendering piatto dall'alto non ha bisogno di niente di tutto ciò. Il prototipo esegue correttamente il rendering dell'intera mappa di 4096x4096 pixel BG [V].
7. La calpestabilità è per tile grafica 8x8, non per cella: `default/attributes.tsv` dà a ogni tile una griglia 4x4 di valori di collisione a 4 bit (il livello superiore vince su quello inferiore; 0 = nessuno; predefinito 7); 5-12 calpestabile [V].
8. Incontri casuali: tipo di terreno (bit 24-30 della cella) + comportamento del terreno (dal valore di collisione, banco dal bit 31 / tipo 21) -> `gWorldMap_EncounterRules` (`src/object/zonedata.c`) -> riga della zona di `src/object/encounter.tsv` [V].
9. Città/dungeon sono attori piazzati (sprite icona) in `gWorldMapPlacements` (`src/scene/world_map.c`); toccare l'attore N solleva il trigger 100+N, abbinato da un `EVENT_EXIT` in `gWorldMapEvents` -> numero di uscita -> `gWorldMapExits` -> (scena, ingresso). Alcuni ingressi sono invece codici di passo della cella (bit 16-23) [V]. Uscire da una città usa la tabella delle uscite di quella città `SCENE_EXIT(n, 2, e)` -> posizione `gWorldMapEntrances[e]` [V].
10. Nessuna variante per edizione dei dati della mappa del mondo in TBS; gli indirizzi di inizio della coda della ROM differiscono per edizione, e qualsiasi modifica rompe la corrispondenza byte per byte "compare OK" [V].

## File e formati

| Dati | File sorgente | Formato | Costruito come / collegato da |
| --- | --- | --- | --- |
| Celle del terreno, entrambi i livelli | `src/map/world/blocks.tsv` | Nessuna intestazione. 320 righe x 512 token separati da tabulazioni; ogni token è esadecimale minuscolo senza `0x`, senza zeri iniziali (`0`, `1b`, `9500014a`), fine riga LF, LF finale [V]. Letto da `blocks()` in `tools/ags-graphics/tables.c:235-282`: le righe devono essere un multiplo di 16, tutte le righe della stessa larghezza (multiplo di 16) [V]. Un gruppo 16x16 può essere tutto `-` (omesso, offset 0) ma mai solo in parte [V; TBS non ne ha, TLA ne ha 969]. | `blocks.blocks`: tabella di 640 offset u32, poi le 256 parole u32 di ogni chunk (1024 byte) compresse separatamente con LZ di tipo `plz` (`tables.c:262-276`) [V]. `src/map/map.s:1-4` `.incbin` come `Field_PerspectiveDataA`, seguito da `.byte 0x01 @ PACKER` [V]. Voce di directory `group Field, PerspectiveDataA, ...` in `src/system/resource/directory.s:123` [V]. |
| Numerazione dei chunk nel TSV | idem | Il chunk `i` occupa le righe TSV `(i//32)*16..+15`, colonne `(i%32)*16..+15` (chunk disposti 32 per riga, per righe) [V: `tables.c:257`]. Questa NON è la disposizione del mondo: il mondo è largo 16 chunk, quindi una riga di chunk del TSV contiene due righe di chunk del mondo affiancate [V dal rendering]. | |
| Blocchi (metatile) | `src/map/default/cells.tsv` | Intestazione `cell0:u8 ... cell15:u8`; valori `0x6b`; 1097 righe, l'ultima corta (8 valori) = 17544 byte = 4386 blocchi x 4 byte [V]. Blocco b = byte `4b..4b+3` = numero di tile (u8) in alto a sinistra, in alto a destra, in basso a sinistra, in basso a destra [V: `src/field/field/world_map.c:71-91`, `444-451`]. Condiviso da entrambi i livelli; il livello seleziona il banco di tile. | `cells.table.lz`; `map.s:5-7` come `Field_DefaultMapCells` (+1 byte PACKER); decodificato in `Ram_MapCellBuffer` (`gMapCellBuffer`, 0xc000 byte, `src/system/ewram.s:223-226`) da `world_map.c:158-160` [V]. La stessa tabella è anche le "celle predefinite" delle mappe a livelli (README `src/map/README.md` riga `default/`). |
| Collisione delle tile | `src/map/default/attributes.tsv` | Intestazione `attr0:u8..attr15:u8`; 256 righe = 4096 byte [V]. Byte 0x000-0x7ff: tile 0-255 del livello inferiore (BG3), 8 byte ciascuna; 0x800-0xfff: tile 0-255 del livello superiore (BG2) [V: `src/field/field/terrain.c:535-580`]. Per tile: 4 righe x 2 byte; ogni byte contiene due valori a 4 bit, nibble basso = sinistra; un valore = 2x2 px BG (4x4 px del mondo). | `attributes.table.lz`, `map.s:11-13` `Field_DefaultMetatileAttributes`; decodificato in `Ram_MapCollision` (`world_map.c:161-163`) [V]. |
| Animazione delle tile | `src/map/default/animation.tsv` | Intestazione `word0:u16..word7:u16`, 465 halfword; script a canali (`0xfdNN` canale, gruppi tile sorgente/conteggio/tile destinazione/fotogrammi, `0xfeNN` salto, `0xfeff` stop, `0xffff` ciclo) [V: `src/field/field/map_animation.c:7-13`]. Le tile sorgente >= 0x600 vengono da `gMapLayerData` (= `tiles_e`/`tiles_j`) [V: `map_animation.c:57-61`]. | `animation.table.lz`, `map.s:8-10`; decodificato in `Ram_MapCollision+0x1000` e avviato (`world_map.c:149-152`) [V]. |
| Grafica delle tile | `src/graphics/world_map/tiles_{a..j}.png` | PNG indicizzato, valore del pixel = indice di colore 8bpp grezzo, palette PNG = `palette_*.png` [V]. a-d, f-i: 128x64 (128 tile ciascuno); e, j: 128x128 (256 tile, sorgente dell'animazione) [V]. | `tiles_X.8bpp.lz`, `src/graphics/world_map/worldmap.s` (ciascuno seguito da byte PACKER) [V]. Directory `directory.s:124-135` (`WorldMapPaletteA`, `WorldMapTilesA..J`) [V]. |
| Palette | `palette_a.png`, `palette_b.png` | PNG indicizzato 16x14 = 224 colori [V]. Caricata nella palette BG 0-223, colore 0 sostituito dallo sfondo corrente (`world_map.c:331-335`) [V]. | `.gbapal.plz` (`worldmap.s:4`, `:26`) [V]. |
| Tabella dei set grafici | `src/field/world_map_resources.c:11-28` | `gWorldMap_GraphicsResources[2][6]` = {palette, tile x5} per il set A (A..E) e il set B (F..J) [V]. | C. |
| Regole degli incontri per terreno | `src/object/zonedata.c:7-15` | `gWorldMap_EncounterRules[132]` s16: 32 regole {tipo, comportamento (-1 qualsiasi), flag (-1 nessuno / regola disattivata una volta impostato), zona} + terminatore tipo -1 [V]. | C. |
| Zone degli incontri | `src/object/encounter.tsv` | Intestazione `rate:u16 level:u16 group0..7:u16 weight0..7:u8 zone` (l'ultima colonna è un'etichetta, non codificata); 104 zone [V]. | `encounter.table`, `src/object/arcspark.s:10-13` [V]. |
| Comportamento del terreno | `src/field/mapdata.c:37-41` | `gWorldMap_TerrainBehaviorTable[48]` u8, indice = valore di collisione + banco (0x10 se bit 31 della cella, 0x20 se tipo 21) [V]. | C. |
| Tabelle della scena | `src/scene/world_map.c` | `gWorldMapEntrances` (`:2717`), `gWorldMapExits` (`:2802`), `gWorldMapPlacements` (`:2863`) + varianti della storia (`:2966-3058`), `gWorldMapEvents` (`:3060`) [V]. Formati in `include/field_scene.h:54-150` [V]. | Overlay della mappa del mondo 0x371 (`objects.tsv:640-644`), collegato a 0x2008000, limite di 32 KB (`src/scene/README.md` Limits) [V]. |
| Indicatori della mappa nella schermata di pausa | `src/object/scripts.s:340-383` | `gWorldMap_PlaceMarkers`: coppie {tile<<16 \| flag, nome del luogo}; la riga i descrive l'attore 11+i; le righe a 0 riservano un attore; -1 termina [V: `src/object/psynergy_effects/world_map.c:282-323`]. | asm `.4byte`. |
| Immagine della schermata di pausa | `src/graphics/world_map/picture.png` | 240x160 8bpp, copre x del mondo 4096-8192, z 0-4096 [V: `psynergy_effects/world_map.c:10-11, 318-322`]. Disegnata a mano, non generata dai blocchi [I]. | `src/graphics/title/title.s:68-71` `Field_WorldMapPicture` [V]. |
| Riquadri della storia | `src/graphics/world_map/story.png`, `storymap.tsv`, `storypal.png` | Grafica degli inserti della storia nell'overlay della mappa del mondo [V: `story.s`]. Non sono dati del terreno. | `story.s`, oggetto dell'overlay `objects.tsv:643` [V]. |

Id di scena della mappa del mondo: `scene WorldMap, 0x371, 0x02, 1, 0x01` è la scena 2 (`src/field/scenes.s:17`); id di scena = indice di riga di `gField_SceneTable` (`scenes.s:1-5`) [V]. Il suo indice mappa 1 è uguale a `SceneId_Clear`, ed è ciò che seleziona la modalità prospettica in `Field_RunScene` (`src/object/object/run_scene.c:45-49`) [V].

## Rendering

Gerarchia (TBS) [V]:

```
world (wraps)  16 x 16 chunks                      8192 x 8192 world px, 4096 x 4096 BG px
chunk          16 x 16 cells   (code: "tile")      512 world px, 256 BG px; 1 KB decoded
cell           u32 word, low 16 bits = block id    32 world px, 16 BG px
block          2 x 2 tiles (4 bytes in cells.tsv)  
tile           8 x 8, 8bpp, from bank per layer    16 world px, 8 BG px
```

- **Visualizzazione**: `Map_InitializePerspectiveScene` (`world_map.c:112-264`) imposta BG3 = char base 2, screen base 8; BG2 = char base 3, screen base 10; entrambi affini 512x512 px, con avvolgimento (`:164-174`); BG1 livello di testo per la vista fissa; `DISPCNT_MODE_2` (`:249`) [V]. BG2 è disegnato sopra BG3, colore 0 trasparente (commento in `view.c:66-69`: dove BG2 è trasparente si vede BG3) [V].
- **Banchi di tile**: tiles[1] (A) del set -> char block 2, tiles[2] (B) -> blocco 2 + 0x2000, tiles[3] (C) -> char block 3, tiles[4] (D) -> blocco 3 + 0x2000, tiles[5] (E) -> `gMapLayerData` (`world_map.c:336-352`) [V]. Quindi i numeri di tile 0-127 del livello 0 = `tiles_a`, 128-255 = `tiles_b`; livello 1: `tiles_c`, `tiles_d` [V dal rendering].
- **Streaming**: le mappe BG contengono una finestra di 2x2 chunk intorno al giocatore. `perspective->tileIds[256]` mappa ogni slot di chunk del mondo su un id di chunk, inizializzato all'identità (`world_map.c:262-263`). `Map_WriteLayerCellTile` decodifica con LZ il chunk `id` (il livello 1 usa `id + 320`, `:298`, `:640`) nel quarto `(x&1, y&1)` di `Ram_MapBlocks` e scrive i byte della mappa affine dalla tabella dei blocchi (`:38-95`) [V]. L'indice della finestra usa `& 15`, quindi il mondo si avvolge ogni 16 chunk [V].
- **Prospettiva**: `WorldMap_BuildScanlineTable` (`src/field/field/view.c`) + la routine ARM `Transform_UpdateVertices` costruiscono una coppia affine (BG2/BG3 PA..Y) per scanline; `MapAnimation_ApplyAffineFrame` carica la riga 0 e invia il resto via HBlank-DMA (`world_map.c:386-441`) [V]. Inclinazione predefinita 0xe000 (-1/8 di giro), piano lontano 0x1fe0000, centro (120,96) (`:198-249`) [V]. Una vista dall'alto dell'editor ignora tutto questo.
- **Set grafico B**: `WorldMap_LoadGraphics(x,z)` sceglie il set B se la cella del livello 0 sotto il gruppo ha tipo 21, solo al caricamento della scena (`world_map.c:323-329`, chiamata da `run_scene.c:76-78`) [V]. Con il set B fa anche puntare gli slot di chunk 10-12 e 26-28 ai chunk alternativi 0x10a-0x10c, 0x11a-0x11c (`:366-374`) [V]. Il rendering conferma che il set B è il nord innevato (zona di Imil); nel set A quegli slot mostrano un segnaposto bianco [V: `north_compare.png`].
- **Scambio di chunk della storia**: `FieldMap_SetWindowCellTile(128, 256, 176, 56)` (`src/scene/world_map.c:534`) mette il chunk 264 nello slot 59 (chunk del mondo (11,3)) finché `FLAG_LAMAKAN_SAND_MONSTER_BEATEN` non è impostato; aritmetica in `world_map.c:271-300` [V]. Visivamente 264 e 59 differiscono per un ponte [V rendering; significato I]. È l'unica chiamata (grep) [V]. 57 dei 64 chunk alternativi (256-319, e i loro gemelli del livello 1) non sono referenziati dal codice di TBS [I: grep non ha trovato altri utilizzatori; tutti i 64 sono non vuoti e distinti da 0-255].
- **Animazione**: i canali di animazione delle tile copiano da `gMapLayerData` (tile E/J) alla VRAM; irrilevante per un rendering statico [V].

Algoritmo di rendering dall'alto (implementato in `render_world.py`, 7 s in Python puro) [V]:

```
for layer L in (0,1), world chunk (cx,cy) in 16x16:
    c = cy*16 + cx + 320*L                         # usa le sostituzioni di tileIds per il set B / gli scambi della storia
    for cell (x,y) in 16x16: word = tsv[(c//32)*16 + y][(c%32)*16 + x]
        b = word & 0xffff; t[0..3] = cells_bytes[4b..4b+3]
        draw tile t[k] from bank L at BG px ((cx*16+x)*16 + (k&1)*8, (cy*16+y)*16 + (k>>1)*8)
        (layer 1: skip pixel value 0)
palette: palette_a.png (or palette_b.png for kind-21 cells / set B)
```

Risultato: `world_mixed.png` (set A, celle di tipo 21 disegnate con il set B) mostra Angara e Gondowan nel quadrante in alto a destra (chunk x 8-15, y 0-7), il resto è oceano; terra di riempimento piatta sul bordo occidentale del continente; tre isolotti [V]. Sovrapponendo `gWorldMapEntrances` e le posizioni dei piazzamenti a mondo/2, l'icona di Vale (attore 11 a 5678,1200) cade al suo posto, gli ingressi 0-2 appena a sud, e il codice di passo 90 (Flint) accanto [V: `world_annotated_zoom.png`].

## Dati di gioco

### Parola di cella (livello 0) [V]

| Bit | Significato | Prove |
| --- | --- | --- |
| 0-15 | id del blocco in `cells.tsv` (16 bit pieni, nessuna maschera a 12 bit sulla mappa del mondo) | `world_map.c:82-86, 445` |
| 16-23 | codice di passo (`struct MapCell.collisionCode`): 1-239 eventi di passo della scena, 240-241 terreno con incontri, 252-254 teletrasporti, 0xff muro (significato delle mappe a livelli) | `include/map.h:13-22`, `src/object/object/step.c:20-25, 231-245` |
| 24-30 | tipo di terreno = regione degli incontri (usati 0 nessuno, 1-6, 21, 31) | `terrain.c:619-624`, `zonedata.c` |
| 31 | seleziona il banco di comportamento 0x10 | `terrain.c:615-617` |

Le celle del livello 1 usano solo i bit 0-15; tutti i loro bit alti sono 0 nei dati [V: statistiche]. Vengono letti solo i bit alti del livello 0 (il codice indicizza le righe 0-31 di `Ram_MapBlocks`, che sono il livello 0) [V]. Il commento nel codice `struct WorldMapCell {tile:24, kind:7, flag:1}` (`world_map.c:17-23`) accorpa il codice di passo in "tile"; i lettori usano i byte separatamente [V].

Censimento dei valori (livello 0, tutti i 320 chunk): tipi 0 74215, 1 915, 2 1542, 3 1001, 4 771, 5 494, 6 1304, 21 1334, 31 156; bit 31 impostato su 188 celle; codici di passo presenti: 13, 15, 18, 28, 29, 32, 42, 47, 50, 51, 55, 61, 74, 75, 90, 91, 92, 93, 95, 96, 100 [V].

### Calpestabilità / terreno [V]

- `GetWorldMapCollision` (`terrain.c:535-580`): prende il byte della mappa BG (il numero della tile 8x8) nello screen block 10 (livello superiore) nella posizione, cerca il suo nibble in `Ram_MapCollision + 0x800`; se è 0, fa lo stesso per lo screen block 8 (inferiore) in `Ram_MapCollision`; se è ancora 0, restituisce 7. Nibble = riga `((y>>1)&3)`, byte `((x>>2)&1)`, `(x>>1)&1` seleziona il nibble alto, in unità di 2 px del mondo.
- `CheckWorldMapWalkable` (`terrain.c:586-592`): calpestabile se e solo se il valore è 5..12.
- Comportamento = `gWorldMap_TerrainBehaviorTable[bank + value]` (`mapdata.c:37-41`): banco 0: 5->1, 6->7, 7/8/10-13->1, 9->2; banco 0x10 (bit 31): 5->4, 9->6; banco 0x20 (tipo 21): 5-13->5 tranne 9->6. Il comportamento sceglie anche lo sfondo della battaglia (`encounter.c:118`, `Battle_SelectTerrainBackdrop` `encounter.c:404-429`): 1 prateria, 2 foresta, 3 deserto, 4 e 7 spiaggia, 5 e 6 distesa innevata, altro Sol Sanctum [V].
- Censimento della mappa di collisione composta: compaiono i valori 1-4, 14, 15 (bloccati; acqua/montagna/scogliera) e 5-10 (calpestabili); 9 = foresta (comportamento 2) secondo le etichette degli incontri [V dati; etichetta "forest" da `encounter.tsv`].
- Altezza: nessuna sulla mappa del mondo (le celle non hanno un byte di forma; attori piazzati con y=0 e senza altezza del terreno, `src/object/object/actors.c:143-158`) [V].

### Incontri casuali [V]

A ogni passo sulla mappa del mondo: `Field_ProcessStep` -> `Encounter_RollWorldMap(&leader->x, speed)` (`step.c:261-263`) -> `Encounter_ResolveWorldMapZoneAndBackdrop` (`encounter.c:103-120`): la prima regola in `gWorldMap_EncounterRules` con tipo, comportamento (o -1) corrispondenti e flag non impostato dà la zona; poi `Encounter_SelectEnemyGroup` (`encounter.c:130-218`) usa la riga di `encounter.tsv`: rate (+5 per ogni livello del gruppo sopra `level`, massimo 5), bias, 8 gruppi pesati (righe di `src/battle/formatn.tsv`). Le regole delle scene del campo (`src/object/location_rules.s`) non si usano sulla mappa del mondo (`Encounter_SelectSceneZones(0)`, `run_scene.c:49`).

Regole (tipo: comportamento -> zona): 1: 4,7,1->7, 2->8; 2: 4,7,1->13, 2->14; 21: 5->29, 6->30; 31: 1->37, 2->38; 3: 3,4,7,1->45, 2->46; 4: ...->54, 2->55; 5: ...->64, 2->65; 6: ...->80, 2->81. Zone etichettate in `encounter.tsv` ("World map: terrain kind 1, grassland and beach", ...). Il comportamento 3 (deserto) è elencato nelle regole ma la tabella dei comportamenti non lo produce mai, quindi sulla mappa del mondo di TBS il terreno desertico conta come prateria/spiaggia [V tabella letta; effetto sul gioco I]. Battaglie dei Djinn: zone 100-103 tramite `gEncounter_AreaEntryTable` (`zonedata.c:19-29`).

`terrain_kind.png` mostra regioni coerenti (tipo 1 intorno a Vale, 2 Bilibin, 21 neve del nord, ...) [V rendering; nomi dei luoghi I].

### Entrare in città/dungeon [V]

Due meccanismi, entrambi terminano in `gWorldMapEvents` (`src/scene/world_map.c:3060-3125`):

1. **Icone dei luoghi (la maggior parte delle città)**: le righe di `gWorldMapPlacements` (`:2863-2964`) sono gli attori 8, 9, ... nell'ordine delle righe; una riga la cui condizione fallisce occupa comunque il suo slot (`actors.c:103-108`). `WorldMap_UpdateLocationContacts` (`world_map.c:416-466`) imposta `touchedTrigger = actor + 100` quando |dx|+|dz| del capogruppo < somma dei raggi in scala (e `FLAG_CONTACT_BLOCKED` 0x104 non impostato). Un evento `{ EVENT_EXIT, 100+actor, cond, exitNo }` lo mappa su un'uscita; per esempio la riga 3 (attore 11, sprite 0x105 a 5678,1200) -> trigger 111 -> uscita 1 -> `SCENE_EXIT(1, 5, 10)` = scena 5 (villaggio di Vale) ingresso 10. Alcuni trigger eseguono invece degli script (i passaggi 116/125/130/150/151 scelgono un'uscita in base al lato di avvicinamento, `:367-410`).
2. **Codici di passo nella mappa**: bit 16-23 della cella = codice; `{ EVENT_EXIT, code, cond, exitNo }` (codici 13, 15, 18, 28, 29, 32, 42, 47, 50, 51, 55, 61, 75) oppure script `EVENT_TOUCH`/`SEARCH` (90-96 Djinn, viaggio, naufragio; 100 ricerca delle Turtle Boots; 112 percorso di trasferimento; 74 bordo orientale).

Codifica delle uscite `SCENE_EXIT(exit, scene, entrance) = exit<<20 | entrance<<12 | scene`, la forma con flag aggiunge 0x10000000 e una parola di flag; la tabella inizia con `SCENE_EXITS(own scene)` e termina con 0x1ff (`include/field_scene.h:72-77`).

### Uscire dalle città [V]

La tabella delle uscite della città nomina la scena 2: per esempio `gValeHome_Exits` `SCENE_EXIT(10, 2, 1)` (`src/scene/vale_home.c:1903`); Bilibin `SCENE_EXIT(1, 2, 5)` (`bilibin.c:805`). L'ingresso `e` è una riga di `gWorldMapEntrances` (`struct SceneEntrance`, 24 byte: entrance, requiredFlag, x, y, z (pixel s16), facing, unused, telecamera L/T/R/B, unused; `field_scene.h:54-67`). Ingresso 1 = (5680, 0, 1226) rivolto a sud, appena sotto l'icona di Vale. Gli ingressi speciali (33, 49, 64-80, 90, 91, 99) scelgono anche tabelle di piazzamento e filmati (`world_map.c:308-342`, `496-560`).

## Limiti e vincoli

- Numero e disposizione dei chunk sono fissati dal codice: 640 chunk, offset di livello 320 (`0x140`, `world_map.c:298, 640`), griglia di slot 16x16 (`& 15`), alternative agli id fissi 0x10a-0x10c, 0x11a-0x11c, 264 [V]. Tieni `blocks.tsv` esattamente a 320x512.
- Ogni chunk si decodifica in 1024 byte in un blocco di heap da 0x400 (`world_map.c:56-57`) [V].
- Tile: 256 per livello (le voci della mappa affine sono byte) [V]; 224 colori di palette, indice 0 forzato allo sfondo [V]. I banchi di tile E/J (256 tile) alimentano l'animazione [V].
- Blocchi: l'id del blocco è a 16 bit nella cella, ma `cells.tsv` si decodifica in `gMapCellBuffer` (0xc000 byte, `ewram.s:225`) -> al massimo 12288 blocchi [I]; lo stesso buffer contiene l'immagine 240x160 della vista fissa durante gli eventi (`world_map.c:711-712`) e viene ricaricato dopo (`:766-767`) [V].
- Tabella delle collisioni fissa di 4096 byte (2 x 256 tile x 8) [V]; lo script di animazione deve starci dopo, in `gMapCollision` (0x4000 in totale, inizia a +0x1000) [I].
- Piazzamenti: slot degli attori 8..65 (`actors.c:98`, `CONTACT_LAST_ACTOR = 65`); i trigger dei luoghi 108..165 non devono scontrarsi con i codici di passo usati per altri eventi [V/I]. La riga i di `gWorldMap_PlaceMarkers` deve restare allineata con l'attore 11+i [V].
- L'overlay della mappa del mondo (codice + tabelle + grafica della storia) deve stare in 32 KB a 0x2008000 [V: README delle scene]. Le coordinate degli ingressi sono s16 [V].
- Compressione: ogni chunk è LZ `plz` (`tools/common/lz.c`, `LZ_PALETTE_UNTAGGED`, macchina `{4123, 485, 4126, 272}`); celle/attributi/animazione `.table.lz`, tile `.8bpp.lz`, palette `.gbapal.plz` [V]. La build ricodifica da TSV/PNG, quindi un editor scrive solo i sorgenti; non scrivere mai a mano `.blocks`/`.lz`.
- Corrispondenza byte per byte: i sorgenti non modificati riproducono la ROM originale (byte letterali PACKER e meccanismo `_patch.tsv`, `src/map/README.md` "How the build encodes a map"); qualsiasi modifica fa differire quell'edizione, cioè `make compare-editions` fallisce per scelta di progetto [V]. I byte `PACKER:` finali in `map.s`/`worldmap.s` sono dati obsoleti innocui dopo una modifica [I].
- Disposizione della ROM: `rom_tail_02` (che contiene `map.s`, `objects.tsv:443`) inizia a un indirizzo fisso per edizione (`main.ld:122-126`) ed è l'ultima regione; la crescita sposta solo i dati successivi; fine della cartuccia TBS 0x08800000 (`Makefile` `ROM_END_tbs`) [V]; il superamento di questo limite non l'ho controllato io [I].
- Edizioni: nessuna variante `_ja/_de/...` né `.ifdef TBS_EDITION_*` in `map/world`, `map/default`, `graphics/world_map`, `zonedata.c`, `mapdata.c`, `world_map_resources.c` [V grep]. `scene/world_map.c` ha solo differenze di codice `TBS_PATCH_3` (`:1657-1666`) [V]. Nomi dei luoghi / messaggi sono nei cataloghi PO per lingua (`games/tbs/text/*.po`) [V README delle scene].

### Differenze in TLA (in breve)

- `games/tla/src/map/world/blocks.tsv` è 1024 righe x 512 = 2048 chunk; offset del livello 1 0x400 (`games/tla/src/field/common/map/perspective.c:42`) e una finestra di 32x32 chunk (`tiles[32][32]`, `:8`) -> mondo di 32x32 chunk (16384 px del mondo) [V]. 969 chunk sono omessi (`-`) [V].
- Piazzato da `games/tla/src/map/world/blocks.s` (file proprio, `.balign 4, 0`) [V].
- Quattro set grafici A-D, ciascuno con palette + 6 fogli di tile (`tiles_a1..d6.png`), più tabelle di animazione/attributi per set (`anim_b/d.tsv`, `attr_b/c/d.tsv`) in `games/tla/src/graphics/world_map/`; directory `games/tla/src/system/resource/directory.s:420-458` [V]. `cells.tsv` è più grande (2745 righe) [V].
- La maggior parte del codice del motore della mappa del mondo di TLA è ancora assembly (`object_dispatch_5.s`); si presume che la semantica di tipo/flag sia condivisa [I].

## Incognite

Segnalate da alchemy:
- XXX `world_map.c:569`: `WorldMap_UpdateView` legge la posizione seguita senza un controllo NULL.
- XXX `world_map.c:778`: se sia voluto che `Map_LoadDefaultCellsAndUpdateBlock` lasci impostato `animationActive`.
- XXX `src/scene/world_map.c:500-504`: i flag 0x161 e 0x85c (impostati dagli ingressi 99 e 1) non sono letti da nessun codice di TBS.
- XXX `actors.c:101-102`: il limite dello sprite 0x2705 nella generazione dei piazzamenti.
- Flag degli incontri 351/353 senza nome (`encounter.c:148-152`); regola "flag 5 / unità 5 esperienza > 130".
- Gli XXX delle mappe a livelli (blocco segnaposto 0xfff, byte di riempimento dell'intestazione) non si applicano: la mappa del mondo non usa la maschera a 12 bit [V].

Non risolte da questa ricerca:
- L'intenzione dei progettisti per il bit 31 della cella: meccanicamente trasforma la collisione 5 nel comportamento 4 (sfondo spiaggia) e la 9 nel 6 (sfondo distesa innevata) [V]; perché quelle 188 celle lo abbiano non è noto [I].
- Perché il valore di collisione 6 si mappa sul comportamento 7 (un secondo id di spiaggia) [I].
- Lo scopo dei 57 chunk alternativi che nessun codice di TBS referenzia (avanzi o dell'epoca di TLA) [I].
- Il significato esatto di ciascun valore di collisione 1-4, 14, 15 (acqua, montagna o scogliera) e di 6, 8, 10 [I].
- Se `picture.png` (mappa della pausa) sia stata derivata dai dati del terreno; un editor che cambia le coste deve ridisegnarla a mano [I].
- Quale scena/ingresso raggiunga ogni `EVENT_EXIT` in termini comprensibili richiede di unire i nomi di `gField_SceneTable` (alcuni nomi di scena in alchemy sono noti per essere imprecisi, per esempio la scena 5 `ValeHome` è il villaggio di Vale) [V per l'esempio].

## Modello di dati proposto per l'editor

Livello Python, tutto l'I/O solo sui file sorgente di alchemy. Mantieni la formattazione del testo originale per avere diff puliti.

| Entità | Campi | File (lettura/scrittura) | Note sul round-trip |
| --- | --- | --- | --- |
| `WorldGrid` | `chunks[640][16][16]: u32` più viste derivate `cell(layer, gx, gy)` tramite la mappa degli slot; `slot_map[256] = identity` | `src/map/world/blocks.tsv` | Scrivi esattamente 320x512 token, `format(v, 'x')` (minuscolo, senza riempimento, `0` per zero), separatori di tabulazione, fine riga `\n` + `\n` finale. Non emettere mai `-` in TBS. La riscrittura identica byte per byte di un file non modificato deve essere un test. |
| `Cell` | `block: u16`, `step_code: u8`, `kind: u7`, `bank_flag: bool` (livello 0); livello 1 solo `block` | impacchettato in `WorldGrid` | Conserva alla lettera i bit alti del livello 1 (tutti 0) e qualsiasi bit sconosciuto. |
| `Alternates` | `set_b_swaps {10:0x10a, 11:0x10b, 12:0x10c, 26:0x11a, 27:0x11b, 28:0x11c}`, `story_swaps {59:264}` | costanti da `world_map.c:366-372`, `scene/world_map.c:534` (sola lettura) | L'editor dovrebbe modificare le alternative insieme ai loro chunk base e mostrare entrambe le viste. |
| `BlockTable` | `blocks[4386][4]: u8` | `src/map/default/cells.tsv` | Riga di intestazione mantenuta; 16 valori per riga, `0x%02x`, ultima riga corta ammessa. Condivisa con le mappe a livelli: modificare un blocco cambia ogni mappa che usa le celle predefinite; meglio aggiungere nuovi blocchi in coda. |
| `TileCollision` | nibble `lower[256][4][4]`, `upper[256][4][4]` | `src/map/default/attributes.tsv` | 16 byte per riga, `0x%02x`, intestazione mantenuta. Condivisa anche con i dati predefiniti delle mappe a livelli [I]. |
| `Tileset` | per set: palette (224 RGB), banchi L0 (A+B), L1 (C+D), banco di animazione (E/J) | `src/graphics/world_map/*.png` | Mantieni la modalità PNG P, le dimensioni esatte e la palette identica a `palette_*.png` (indice = colore). Riscrivere i PNG va bene per la build se gli indici sono conservati; verifica che siano identici pixel per pixel anziché file per file. |
| `Animation` | script dei canali (elenco u16) | `src/map/default/animation.tsv` | All'inizio trattale come parole opache. |
| `Entrance` | `id, required_flag, x, y, z, facing, camera[4]` | `gWorldMapEntrances` in `src/scene/world_map.c:2717-2800` | Sorgente C: analizza/rigenera solo il blocco di inizializzazione tra marcatori noti; mantieni i nomi `CONDITION_ALWAYS`, `FACING_*`. |
| `Exit` | `exit_no, scene, entrance, flag?` | `gWorldMapExits` (`:2802-2839`) e le `*_Exits` delle città | Idem; mantieni la forma con macro `SCENE_EXIT(...)`. |
| `Placement` (icona del luogo) | `row/actor, sprite, condition, behavior, x, z, facing, talk, flags` | `gWorldMapPlacements` (`:2863-2964`) | Numero dell'attore = 8 + riga; inserire/rimuovere righe rinumera i trigger (100+attore) e l'allineamento di `gWorldMap_PlaceMarkers` (attore 11+i). Meglio modificare sul posto. |
| `Event` | `kind/control, trigger, condition, value` | `gWorldMapEvents` (`:3060-3125`) | Uscite: `{ EVENT_EXIT, trigger, cond, exit_no }`; gli script fanno riferimento a funzioni C (sola lettura nell'editor). |
| `EncounterRule` | `kind, behavior, flag, zone` | `src/object/zonedata.c:7-15` | 132 s16 incluso il terminatore; se si aggiungono regole va aggiornata la dimensione letterale dell'array. |
| `EncounterZone` | `rate, level, groups[8], weights[8], label` | `src/object/encounter.tsv` | Forma tabellare; 104 righe fissate dai riferimenti (id delle zone nel codice/nelle regole). |
| `PlaceMarker` | `tile, flag, name_id` per attore 11+i | `src/object/scripts.s:340-383` | Righe asm `.4byte`. |

Viste consigliate per l'editor: (1) composito dall'alto con scelta del set per cella (tipo 21 -> set B), (2) sovrapposizione delle collisioni da `TileCollision` tramite i numeri di tile delle celle (prima superiore, poi inferiore, poi 7), (3) sovrapposizioni di tipo e codice di passo, (4) ingressi/piazzamenti a mondo/2. Funzioni di supporto per le coordinate: px del mondo = px BG x 2; cella = mondo // 32; slot di chunk = cella // 16; (riga, colonna) del TSV per il livello L = `((c//32)*16 + gy%16, (c%32)*16 + gx%16)` con `c = slot_map[(gy//16)*16 + gx//16] + 320*L`.
