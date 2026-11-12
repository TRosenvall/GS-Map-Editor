<!-- translated from docs/research/rendering.md @ 5cc75b0f23d8 -->
# Ricerca sul rendering: livelli, fusione, animazione delle tile, segnaposto

*Questa è una traduzione dell'originale inglese [rendering.md](../../research/rendering.md); se i due testi differiscono, quello inglese è il più aggiornato.*

Fonte: alchemy (`games/tbs/...`). I percorsi sono relativi a `games/tbs/` salvo dove indicato diversamente.
VERIFICATO significa che l'affermazione è stata letta nel codice del motore e confermata dal rendering. DEDOTTO significa che è un'ipotesi ragionata.
Gli script di prova e i rendering sono in
`(a scratch folder)`
(`r2.py` è il renderer di riferimento, `dirmap.py` risolve la tabella delle risorse delle scene).

## Riepilogo

Le mappe "scombinate" non sono causate dal parallasse. Le causano tre bug del visualizzatore, e due di questi colpiscono quasi tutte le mappe:

1. **Le celle segnaposto (0xfff) sono vera grafica.** Al caricamento la k-esima cella 0xfff, contata per righe sull'intera griglia 128×128, diventa il blocco k. In **tutte le 182 mappe** il numero di celle segnaposto è esattamente il numero di righe di `metatiles.tsv`. La tabella dei blocchi è di fatto "i blocchi unici in ordine di lettura", e i valori di cella espliciti li riutilizzano. Disegnare i segnaposto come vuoti fa sparire gran parte di ogni mappa. (VERIFICATO)
2. **Il tileset viene dalla tabella sbagliata.** Il gioco carica la palette di una mappa, i suoi tre fogli VRAM e il suo foglio D da `src/field/layered.tsv` (`gMap_LayeredScenes`), non dall'ordine in `directory.s`. **117 mappe su 182** usano una combinazione di palette o fogli diversa da quella che il visualizzatore presume. Esempi: il char block 3 della mappa 034 è `Set02TilesC` e il suo foglio D è `Set26TilesC`. VenusEntrance usa i fogli `Set07` con `Palette49`. (VERIFICATO)
3. **I limiti dell'intestazione sono solo i limiti predefiniti della telecamera.** La tabella degli ingressi di una scena può sovrascriverli. La mappa 034 (scena Bilibin3) è limitata a 16..400 px dai suoi ingressi. Fuori da quell'intervallo, l'area di 128×128 tile dell'intestazione è riempimento della griglia (blocco 3), che nel gioco non si vede mai. (VERIFICATO)

Parallasse e deriva esistono solo in 8 mappe (047, 103, 104, 147, 148; in 090/091/092/169 le maschere non hanno effetto perché la velocità è 0). La fusione è BLDCNT/BLDALPHA impostati da un piccolo script. Il primo bersaglio è quasi sempre il livello 2 (BG1), a volte il livello 1 (BG2). L'animazione delle tile è fatta di copie DMA di tile dal foglio D alla VRAM. Tutti e quattro sono stati implementati in `r2.py` e controllati con il rendering.

## (a) Livelli, finestre e scorrimento

**Strutture.** `struct LayeredSceneLayer {u8 x, y; s8 scrollX, scrollY, speedX, speedY; u8 periodX, periodY;}` si trova in `src/field/field/map_layers.c:172-181`. L'ordine della macro `map_layer` è lo stesso: x, y, rate_x, rate_y, drift_x, drift_y, period_x, period_y (`src/map/map.inc`).

**Caricamento** (`map_layers.c:274-303`, VERIFICATO):
- `offset = x<<19` e `y<<19`, quindi l'origine è x×8 px in virgola fissa 16.16.
- `scale = scroll*4096`, quindi rate/16 della vista.
- `speed = speed*4096`, quindi speed/16 px per fotogramma.
- `mask = period`.
- `phase = 0`.

**Per fotogramma** (`Map_UpdateLayerScroll`, `map_layers.c:474-566`; identico in `Map_SetCameraCenter` 572-630, VERIFICATO):
```
view   = followed point - focus, clamped to [min, max - 240x160]        (min/max = header bounds*8 px, or scene overrides)
base   = view * scale            (Q16 multiply → view * rate/16)
if speed: phase += speed; base = (base + phase) & ((period<<19) | 0x7ffff)   # avvolgimento; applicato solo quando speed != 0
pos    = base + offset           # angolo in alto a sinistra del livello in pixel della griglia
BG(3-li) scroll = pos
```
Il disegno legge le celle in `((pos/16) & 0x7f)` su entrambi gli assi (`Map_RenderMetatileRow/Column`, 411-462). Quindi **la finestra di un livello si avvolge modulo 128 celle (2048 px)**. Dimensione della finestra = schermo; non esiste una dimensione di finestra per livello.
Il livello li è mostrato su BG(3-li), con priorità BGCNT = il byte di priorità dell'intestazione, char base = il byte char dell'intestazione e screen base 5+li (314-322).

**Limiti della telecamera.** `work->min/max = header bounds << 19` (261-264). `Scene_ApplyEntrance` (`src/object/object/run_scene.c:488-499`) sovrascrive ciascuno di minX/minY/maxX/maxY in pixel quando `cameraLeft/Top/Right/Bottom != -1` dell'ingresso (`struct SceneEntrance`, `include/field_scene.h`). Mappa 034 = scena `Bilibin3` (`src/field/scenes.s:50`, indice mappa 0x24). I suoi ingressi 1 e 2 usano i limiti 16,16,400,400 (`src/scene/bilibin.c:780-785`). Alcune scene scrivono anche i limiti direttamente (`tolbi_ship_deck.c:1062`, `vale_babi.c:418-421`, `psynergy_effects/view.c:16`).

**Mappe con parametri di livello non predefiniti** (tutto il resto è `16,16,0,0,255,255`):

| mappa | livello | parametri | significato |
|---|---|---|---|
| 047 | 0 | rate 8,8 | parallasse a metà velocità |
| 103 | 0 | drift_y −25, period 255 | lo sfondo scorre verso l'alto di 25/16 px/fotogramma, si avvolge a 2048 px |
| 104 | 0 a y=92 | rate 6,6 | parallasse di cielo/mare (scena dell'albero della nave) |
| 147, 148 | 2 | rate 20,20, drift −121/16, 35/16 px/f, period 31 | sovrapposizione della tempesta di sabbia, si avvolge ogni 256 px |
| 090-092 (livello 0,1), 169 (livello 0) | | period 127/63, speed 0 | nessun effetto (la maschera si usa solo quando speed ≠ 0) |

**Ordine di priorità (GBA, VERIFICATO dal rendering).** Disegna dal fondo verso il davanti ordinando per `(-priority, layer index)`. A parità di priorità, il BG con il numero più basso sta sopra, quindi il livello 2 (BG1) sta sopra il livello 0 (BG3). Il `sorted(key=-priority)` dell'attuale visualizzatore è stabile, quindi dà già lo stesso risultato. Priorità 0 = spento.

**Regola di rendering per un visualizzatore Python:**
- *Livelli del campo* (rate 16, speed 0): `grid_px = (origin_px + map_px) mod 2048`, dove `map_px` è misurato da (0,0) dello spazio della griglia, non da bounds.left. È esatto per qualsiasi telecamera. L'attuale `render_layer` si comporta così per left=top=0, ma non si avvolge modulo 128 celle e ignora un bounds.left/top diverso da zero.
  - Forma corretta: `gx = (x*8/16 + bounds.left/2 + i) % 128` per la colonna di schermo i della finestra dei limiti, e lo stesso per y.
- *I livelli con parallasse/deriva* non hanno un'unica immagine statica. Regola consigliata per la vista mappa: ancorare al centro dell'intervallo della telecamera.
  - `V = ((min + max(min, max-240))/2, same for y)` e `pos = layer_pos(V) + (map_px - V)`.
  - È esatto per la telecamera in V e continuo altrove. Fase della deriva = 0 (o speed×fotogrammi).
  - Offri anche un'"anteprima della telecamera" 240×160 che usi esattamente `layer_pos(view)`.
- *Ritaglia* ai limiti della telecamera della scena quando sono noti; altrimenti usa i limiti dell'intestazione.

## (b) Fusione

**Meccanismo** (`src/field/field/map_animation.c:163-255`, VERIFICATO):
- `blend.tsv` si compila in halfword: `control v` → v (un valore BLDCNT, riconosciuto dal nibble alto 3); `level v wait` → v, wait; `jump n` → 0xfe00|n (cursore = script + 2n halfword); `stop` → 0xfeff; `end` → 0xffff (torna all'inizio).
- Su un `level`:
  - se i bit dell'effetto (7..6) dell'ultimo BLDCNT sono 01, allora `REG_BLDALPHA = v`;
  - altrimenti `REG_BLDY = v`;
  - poi attende `wait` fotogrammi.
- Uno script composto solo da `end` non installa nulla (`DisplayBlend_StartScript` 246).
- Il caricatore imposta prima `REG_BLDCNT = 0` (`map_layers.c:365-367`).

**Semantica GBA:**
- I bit 0-5 di BLDCNT sono il 1° bersaglio (bit0 BG0, bit1 BG1 = livello 2, bit2 BG2 = livello 1, bit3 BG3 = livello 0, bit4 OBJ, bit5 sfondo).
- I bit 6-7 sono l'effetto (1 alpha, 2 schiarisci, 3 scurisci).
- I bit 8-13 sono il 2° bersaglio.
- BLDALPHA: EVA = bit 0-4 (peso del livello bersaglio 1), EVB = bit 8-12 (peso di ciò che sta sotto), ciascuno limitato a 16.
- `out = min(31, (top*EVA + below*EVB) >> 4)` per canale a 5 bit.
- BLDY: `I + (31-I)*Y/16` (schiarisci) oppure `I - I*Y/16` (scurisci).

**Valori trovati nelle mappe TBS** (primo `level` dopo `control`):

| BLDCNT | livello bersaglio | effetto | mappe (esempi) |
|---|---|---|---|
| 0x3f42 | livello 2 (BG1) sopra tutto | alpha | 005-007/032/076 (0x1006: 6/16 + 16/16 additivo), 021, 022-024/136/137, 025-027/077-085 (0xa09: 9/16 + 10/16 = l'acqua di 080), 029, 033/040/062/115/144 (0x1003 bagliore, animato 3-4), 047 (0xc04), 053, 054-058/109/155/156/163, 063-067/100, 073, 075, 108, 113, 133, 139-142 (0xb0e), 154, 164-167 |
| 0x3f44 | livello 1 (BG2) | alpha | 009/145/146, 010/019, 012/013/016, 014/015, 018/038/052/094/095/099/102/120/121/151/160/161 (0x1008), 061, 086, 105, 124 |
| 0x3fc8 | livello 0 (BG3) | scurisci, BLDY 3-6 | 046 |
| (nessuno) | — | solo BLDY, nessun effetto | 039/042/043, 114, 125: lo script scrive i livelli con BLDCNT=0. Una scena deve impostare BLDCNT (DEDOTTO) |
| solo `end` | — | — | 36 mappe (020, 028, 031, 036, 037, 048, 051, 060, 072, 074, 089, 093, … inclusa la 134 tramite `map_020/blend`) |

La maggior parte dei livelli con EVB=16 è **bagliore additivo** (raggi di luce, torce). Un'attesa di 43210 significa che il livello è costante.

**Fusioni impostate dalle scene** (non in `blend.tsv`; VERIFICATO nel codice):
- `src/scene/altmiller_cave.c:195-222, 313-320`: BLDCNT 0x3f42 con BLDALPHA 0x1000..0x600, oppure 0xc04. La mappa 134 = scena AltmillerCave5 (`scenes.s:165`) ha il suo livello di oscurità fuso in questo modo.
- Anche `tret_tree_branch.c:163` (BG1 4/12), `tolbi_spring.c`, `vale_babi.c`, `mercury_lighthouse*.c`, `crossbone_isle_platform_rooms.c`, `lemurian_ship.c`.

**Regola di rendering:**
- Analizza lo script di fusione e prendi il BLDCNT e il primo livello, oppure simulalo fino al fotogramma t.
- Per ogni livello disegnato dal fondo verso il davanti: se il suo bit BG è nel target1 ed effect==1, `rgb = min(31,(layer*EVA + below*EVB)>>4)` dove il livello è opaco. "Sotto" è il colore già composto (o lo sfondo); tutti i control di TBS usano il 2° bersaglio 0x3f.
- Per gli effetti 2/3, applica BLDY ai pixel di quel livello.
- Usa colori a 5 bit (valore PNG >> 3) per risultati esatti.
- Facoltativamente, tieni una piccola tabella di eccezioni per mappa per le fusioni impostate dalle scene (134 → 0x3f42/0xc04).

## (c) Animazione delle tile

**Meccanismo** (`src/field/field/map_animation.c:7-145`, VERIFICATO):
- `animation.tsv` si compila in halfword: `channel n` → 0xfd00|n, `frame src cnt dst wait` → 4 halfword, `jump n` → 0xfe00|n, `stop` → 0xfeff, `end` → 0xffff.
- `MapAnimation_StartChannels` scorre il flusso. Ogni 0xfdNN avvia il canale NN&15 all'halfword successiva, in pausa se il bit 7 è impostato (`channel 0x8N`; una scena lo riprende tramite `Map_ClearLayerEntryFlag`).
- A ogni fotogramma, per ogni canale non in pausa:
  - se timer>0: timer−− e passa al canale successivo.
  - altrimenti esegue al cursore:
    - 0xffff → cursore = inizio
    - 0xfeNN → cursore = inizio + 2·NN halfword
    - 0xfeff → resta fermo
    - altrimenti copia `cnt` tile, imposta timer = wait, cursore += 4, e ripete nello stesso fotogramma.
  - Quindi **una copia con attesa W resta a schermo per W fotogrammi**, e W=0 concatena la copia successiva nello stesso fotogramma.
- Copia (4bpp, `wideTiles==0`), in tile da 32 byte contate dal **char block 1**:
  - `src >= 0x600`: da `Ram_DecodeBuffer (0x0201c000) + src*32`, cioè `gMapLayerData` (0x02028000, `src/system/ewram.s:236-244`, `include/ram_buffer.h`) + (src−0x600)*32. Cioè la **tile src−0x600 del foglio D** (foglio D = colonna 5 di `layered.tsv`, decodificato in gMapLayerData in `map_layers.c:357-359`).
  - `src < 0x600`: dalla tile VRAM `512+src` (assoluta, dal blocco 0).
  - Destinazione: tile VRAM assoluta `512+dst`.
- La tile assoluta di una voce della mappa è `charBase*512 + (entry & 0x3ff)`.

**Come produrre il fotogramma t:**
1. VRAM iniziale: blocchi 1/2/3 dalle colonne 2/3/4 di `layered.tsv`, e foglio D dalla colonna 5.
2. Costruisci i canali come sopra; salta i canali in pausa (`channel 0x8N`).
3. Esegui l'aggiornamento t+1 volte, modificando un array di tile VRAM.
4. Poi fai il rendering normalmente con le tile modificate.

I cicli sono brevi (il ciclo dell'acqua della 34 è di 24 fotogrammi; la 127 salta dopo 10+10 fotogrammi). Una GIF/anteprima può avanzare di 1..N fotogrammi. L'atlante dei metatile va ricostruito per ogni fotogramma o, meglio, messo in cache per tile.

## (d) Segnaposto 0xfff

**Meccanismo** (VERIFICATO):
- `Tilemap_ConvertBuffer` (`src/field/field/map_layers.c:110-122`) esegue `Tile_ConvertMap` (`src/graphics/tile/convert_map.s:8-50`) sul piano dei blocchi.
- r5 = 0xFFF00000 verifica `(cell<<20) == 0xfff<<20`.
- r4 parte da 0xFFFFF001; `cell + r4` (troncato a 16 bit) = `(cell & 0xf000) | k`, e r4 si incrementa a ogni segnaposto.
- Il gemello in C non usato `Tilemap_NumberPlaceholderBlocks` (84-103) fa lo stesso.
- Risultato: **la k-esima cella (contando da 0, per righe su tutte le 128×128 celle, tutti i livelli insieme) i cui 12 bit bassi sono 0xfff diventa il blocco k. Il suo nibble alto viene mantenuto.**
- Il disegno usa poi `Ram_MapBlocks[(cell<<20)>>19]` (solo i 12 bit bassi, 411-437).

**Convalida.** Per ognuna delle 182 mappe, il numero di segnaposto è uguale al numero di righe di `metatiles.tsv` (`allph.py`). I rendering di 034 e VenusEntrance diventano grafica coerente (vedi sotto). Quindi i segnaposto non sono riempiti da codice sconosciuto: sono i blocchi unici della mappa in ordine di lettura. Si può rispondere all'`XXX` in `src/map/README.md`. (Si contano solo le celle che valgono esattamente 0xfff al caricamento; le copie di celle a runtime `Map_CopyMetatileIndicesRect` avvengono dopo.)

**Regola:** prima del rendering, `n=0; for y in 0..127: for x in 0..127: if cell&0xfff==0xfff: cell=(cell&0xf000)|n; n+=1`.
Per un editor questo ha delle conseguenze:
- Dipingere una cella verso o da 0xfff rinumera tutti i segnaposto successivi.
- La modifica deve mantenere il numero di segnaposto uguale al numero di blocchi, altrimenti i blocchi memorizzati slittano.
- Mostra il numero di blocco risolto e, al salvataggio, memorizza 0xfff solo dove `resolved == running count`. In alternativa, lascia le celle come sono e tratta 0xfff come "prossimo blocco unico".

## Rendering convalidati

Tutti in `(a scratch folder)`:
- `cur_034.png`, `cur_VenusEntrance.png`: il visualizzatore attuale (difettoso).
- `ph_034.png`, `ph_VenusEntrance.png`: solo la correzione dei segnaposto (034 coerente; Venus ancora con il tileset sbagliato).
- `new_034.png`: tutte le correzioni. Fiume/foresta coerenti nelle celle 1..25. Il resto è riempimento fuori telecamera.
- `new_VenusEntrance.png`: tutte le correzioni. Foresta e ingresso del Venus Lighthouse corretti.
- `new_040.png` vs `new_040_noblend.png`: bagliore additivo delle torce (0x3f42, 0x1003).
- `new_080.png` vs `_noblend`: acqua fusa 9/16 + 10/16.
- `new_016.png`: stanze del Sol Sanctum, 0x3f44 sul livello 1.
- `new_134.png`: oscurità opaca. `new_134_sceneblend.png`: con lo 0x3f42/0xc04 di Altmiller, oscurità a 4/16.
- `new_104.png` (ancoraggio a metà telecamera), `cam_104_0_0.png`, `cam_104_128_208.png`: cielo in parallasse.
- `new_147.png`: sovrapposizione di sabbia in deriva.
- `new_047.png`, `new_103.png`.
- `anim_034_f00..f40.png`, `anim_034.gif`, `anim_034_compare.png`: i fotogrammi 0 e 24 dell'animazione dell'acqua differiscono.

## Modifiche esatte consigliate per gsmap/project.py

1. **Risorse delle scene** (sostituisce l'abbinamento di `_read_directory`):
   - Espandi `directory.s` in un elenco ordinato di voci. Applica le macro esattamente: `group K, a,b` → `K_a, K_b`; `area S, L, maps` → `Field_MapNN…, Tileset_SPalette, Tileset_STiles<L…>`; `recolor P, maps` → `Field_MapNN…, Tileset_PaletteP`; `overlays`; `unused N` → N voci; `resource , X` → X.
   - Imposta `base = index('Field_Map001')`.
   - Ogni riga di `src/field/layered.tsv` è `[header, palette, blk1, blk2, blk3, sheetD]`; mappa ciascun valore su `entries[base+v]`.
   - Usa come chiave l'etichetta dell'intestazione (`Field_MapNNN` / `Field_<Name>`) e usa la prima riga. Le mappe 108 e 110 hanno due righe con palette diverse (45/58 e 15/18). Esponi l'alternativa.
   - Risolvi le etichette tramite l'esistente `self.symbols`. Implementazione di riferimento: `dirmap.py`.
2. **Atlante:** tile assoluta `a = char_base*512 + (e&0x3ff)`.
   - Blocco `a//512` 1..3 → `[blk1, blk2, blk3][a//512-1]`. Blocco 0 = tile delle finestre, quindi saltalo. 4+ non è valido.
   - Le righe di palette 14/15 non sono della mappa (UI). Mostrale come trasparenti o con un colore di debug.
3. **Segnaposto:** risolvi 0xfff → ordinale progressivo (regola in d) in `load_grid` per il rendering. Elimina il test `== EMPTY → skip`. Tieni la griglia grezza per il salvataggio.
4. **Finestre:** `gx = (layer.x//2 + bounds.left//2 + i) % 128`, e lo stesso per y (avvolgere, non saltare). Per i livelli con rate≠16 o drift≠0, usa la regola dell'ancoraggio a metà telecamera di (a).
5. **Fusione:** analizza blend.tsv (`control`/`level`/`jump`/`stop`/`end`). Componi dal fondo verso il davanti con le formule BLDCNT/BLDALPHA/BLDY di (b). Imposta il cursore dell'opacità del livello su EVA/16 come valore predefinito solo come approssimazione (il risultato esatto è additivo: `top*EVA + below*EVB`).
6. **Animazione:** tieni un array di tile `vram[2048]` modificabile più `sheetD[512]`. Fai avanzare i canali come in (c). Esponi un numero di fotogramma o un controllo di riproduzione.
7. **Limiti della telecamera (facoltativo):** usa come predefiniti i limiti dell'intestazione. Offri "ritaglia al contenuto" o i limiti degli ingressi della scena. Scena → indice mappa viene da `src/field/scenes.s` (`scene name, code, area, kind, map`, dove map = la riga in `layered.tsv`). I limiti sono nelle tabelle `struct SceneEntrance` in `src/scene/*.c`.

## Incognite

- Come funzionano le fusioni per le mappe il cui script non ha `control` (039/042/043/114/125). DEDOTTO: una scena imposta BLDCNT; non tracciato.
- Fusioni impostate dalle scene e riprese dell'animazione (`channel 0x8N`) per mappa: è stato tracciato solo Altmiller (134).
- Quale riga di `layered.tsv` usa una scena quando una mappa ne ha due (108, 110). Entrambe le palette sono valide.
- Perché solo la deriva verticale riempie tutte le 32 righe BG (`map_layers.c:600-604`, un XXX di alchemy). Per un rendering statico non importa.
- I limiti della telecamera per le mappe diverse dalla 034 non sono stati tabulati. `scenes.s` + le tabelle degli ingressi li darebbero.
- È stato controllato solo il ramo dell'edizione EN; `layered.tsv` non ha varianti per edizione.
