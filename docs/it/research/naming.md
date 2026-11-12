<!-- translated from docs/research/naming.md @ 3e642cd20a29 -->
# Livello dei nomi: codici di collisione, oggetti, sprite, luoghi, dialoghi, flag (TBS)

*Questa è una traduzione dell'originale inglese [naming.md](../../research/naming.md); se i due testi differiscono, quello inglese è il più aggiornato.*

> **Da quando è stato scritto:** le tabelle dei nomi descritte qui sotto non vengono più distribuite. `gsmap/names.py` legge i nomi durante l'esecuzione dalla copia di lavoro (`en.po`, `flags.h`, `sprite_ids.h`, `item_table.c`, `scenes.s`, `scene_rules.s`). `gsmap/data` conserva solo i fotogrammi di anteprima, i flag liberi per i forzieri e le nostre descrizioni della calpestabilità.

Albero dei sorgenti: `alchemy/` (sola lettura), build inglese `out/tbs-en`. I percorsi sono relativi a `alchemy/games/tbs/` salvo quando iniziano con `out/` o `tools/`. **VERIFICATO** significa letto nel codice o nei dati, oppure controllato da uno script su tutti i file. **DEDOTTO** significa ricavato e non dimostrato. I dati generati sono in `docs/research/names/`. Gli script che li producono sono copiati in `docs/research/names/scripts/`; gli originali e i file intermedi sono nella cartella di prova `(a scratch folder)`.

## Riepilogo

1. **I codici di collisione** si dividono in tre gruppi: significati globali del motore, trigger delle scene e marcatori. (VERIFICATO)
   - **Significati globali:**
     - 0 pavimento
     - 240/241 terreno con incontri
     - 242..247 punti di ricerca vuoti fissi: giara, barile, cassa, tomba, libri, pozzo
     - 249 salto a catena
     - 250 pericolo
     - 251 ombra per Cloak
     - 252 sporgenza
     - 253 arrampicata
     - 254 salto di un varco
     - 255 muro
   - **1..239 sono trigger delle scene.** Il loro significato viene dalle tabelle degli eventi della scena: un'uscita, uno script al contatto o una ricerca.
   - **I marcatori (forzieri e pietre) possono usare solo 100..239.**
   - L'editor dovrebbe dare un nome a 1..239 per ogni mappa a partire dagli eventi. `collision_by_map.json` (di prova) è quella legenda, già risolta: per le uscite, il luogo di destinazione; per gli script, il nome dello script; per le ricerche, l'oggetto o il testo.
2. **Oggetti:**
   - Nome = messaggio `MsgItemName` (386) + id.
   - Icona = colonna `icon` di `items.tsv` → `graphics/ui/menu_icons/item_{icon:03d}.png` (16×16, palette incorporata).
   - Valore del forziere = `FIND_ITEM(id)` = `0x100000|id`, `FIND_COINS(n)` = `0x200000|n`, mimic = `0x500000|slot` (slot 0..7), oppure `FIND_PSYNERGY_STONE` = `0x300000`.
   - (VERIFICATO)
3. **Sprite:**
   - L'id dello sprite di un piazzamento si usa direttamente come riga di `graphics/sprite/sprites.tsv` (513 righe).
   - La sua grafica è `graphics/sprite/spr_NNN.png`, una striscia verticale di fotogrammi w×h disegnata con la palette OBJ condivisa da 224 colori.
   - Il fotogramma di anteprima è il primo fotogramma dell'animazione 1 più lo scostamento dell'orientamento.
   - Sono coperti 249 id, inclusi tutti i 219 usati. 71 nomi sono VERIFICATI (simboli e commenti della decompilazione); 178 sono DEDOTTI dall'immagine e dalle scene che li usano.
4. **Luoghi:**
   - `gScene_AreaNameRules` (`src/object/scene_rules.s:168`) dà a ogni scena o gruppo (facoltativamente per ingresso) un indice di area.
   - Il testo è il messaggio `MsgDebugEntryName` (2459 in EN) + indice.
   - 199 scene su 201 ricevono un nome. (VERIFICATO)
5. **Dialoghi:**
   - Il `msgid` di `en.po` è il numero del messaggio a 5 cifre con zeri iniziali. `msgctxt` è il nome del simbolo, oppure `message` quando il messaggio non ne ha.
   - Un valore di `SceneEvent` sotto 0x10000 è un numero di messaggio. Sopra, è uno script; le sue battute sono i simboli `Msg*` nel suo corpo.
   - Il trigger di un evento di dialogo è il numero dell'attore, cioè 8 + la riga del piazzamento.
   - (VERIFICATO)
6. **Flag:**
   - Ci sono 4.096 flag (0..0xfff).
   - I nuovi forzieri dovrebbero prendere i flag da **0xe00..0xfff**, usando solo flag che nessuna tabella, codice o letterale referenzia. **251 sono liberi** (`flags.json` `free_chest_flags`); i più bassi sono 0xe01, 0xe03..0xe0f e così via.
   - Non usare mai 0x200..0x3ff: sono temporanei di scena e di gruppo che vengono azzerati.

---

## 1. Codici di collisione

### 1.1 Significato nel motore (VERIFICATO salvo dove indicato)

Il codice di una cella è `struct MapCell.collisionCode` (`include/map.h:13-22`), letto dalla finestra del livello del capogruppo (`terrainId`), una cella da 16 px alla volta.

| Codice | Nome (per il giocatore) | Comportamento nel motore | Prove | Editor |
|---|---|---|---|---|
| 0 | **Pavimento** | Calpestabile. Usa il terreno con incontri 0, che non ha incontri a meno che lo shift = 1 della regola del luogo della scena non sposti la prima zona su di esso. | `src/object/object/step.c:240-276`; `src/object/object/encounter.c:76-90`; `src/object/location_rules.s:1-7` | pennello |
| 1..239 | **Trigger** (uscita / evento / ricerca) | Calpestare la cella imposta `work->action = code` (`step.c:247`). `Scene_RunTouchOrExit` esegue prima l'`EVENT_TOUCH` della scena con quel trigger (messaggio o script); se non c'è, usa `EVENT_EXIT`, il cui valore è il tipo di uscita (`events.c:333-380`). Premere A sulla cella davanti cerca un `EVENT_SEARCH` con lo stesso codice (`run_scene.c:440-450`). Anche gli eventi `USE_ITEM` e `PSYNERGY_IN_AREA` possono basarsi su di esso. Qualsiasi codice diverso da zero verifica anche le regioni di uscita (`step.c:244-245`). | come elencato | trigger: nominato per mappa dagli eventi (§1.3) |
| 100..239 | **Id di forziere / pietra / ricerca** | Tutto ciò che vale per 1..239, più: è l'unico intervallo che `Field_PlaceMapMarkers` accetta (`markers.c:57`). Un evento `SEARCH(SEARCH_CHEST)` mostra un forziere (oggetto 20, `markers.c:70`); `FIND_PSYNERGY_STONE` mostra una pietra (oggetto 28, `markers.c:105`). | | trigger; questi appartengono ai marcatori |
| 240 | **Terreno con mostri** | Calpestabile. Gli incontri usano `encounterGroups[1]`, la prima zona della regola, invece del terreno 0. Comune come pavimento dei dungeon: 23 mappe, per esempio map_009 (133 celle). | `step.c:22-23,264-267` | pennello |
| 241 | Terreno con mostri 2 | Come 240, ma usa `encounterGroups[2]`. **Nessuna mappa lo usa.** | `step.c:22-23` | pennello (avanzato) |
| 242 | Giara vuota | Quando la si esamina, dice "checked the jar… but didn't find anything". Scostamento di messaggio 2 da `MsgTileChecked` (2344) e `MsgTileResult` (2376). Scatta solo quando il terreno davanti è da 0 a 64 px sopra il capogruppo. | `src/object/fxdata.c:22-31`; `events.c:439-448`; `run_scene.c:441-447` | pennello |
| 243 | Barile vuoto | scostamento 3 | idem | pennello |
| 244 | Cassa di legno vuota | scostamento 13 | idem | pennello |
| 245 | Tomba vuota | scostamento 8 | idem | pennello |
| 246 | Libreria (libri) | scostamento 30 | idem | pennello |
| 247 | Pozzo | scostamento 31. Non usato nelle mappe. | idem | pennello |
| 248 | (non usato) | Nessun lettore trovato e nessuna mappa lo usa (DEDOTTO inerte). | — | non toccare |
| 249 | **Salto tra pietre** | Mai sollevato da `Field_ProcessStep`. Dopo un salto in avanti, atterrare su 0xf9 fa saltare di nuovo (salti a catena). Usato in 3 mappe (029, 098, 148). | `events.c:383-405`; `src/object/psynergy_effects/climbing.c:18-23,99-103` | pennello (avanzato) |
| 250 | **Terreno pericoloso** | Camminando, il contatore dei passi pericolosi sale e, a `hazardLimit`, il gruppo subisce `hazardDamage`. La scena imposta modalità, limite e danno. Mappe 063-067. | `step.c:24,293-327` | pennello |
| 251 | **Ombra (Cloak)** | Calpestabile. Cloak tiene nascosto il gruppo solo su questo codice; uscirne termina Cloak (`CLOAK_TILE`). Mappe 111 e 130-142 (Lunpa Fortress, Altmiller Cave…). | `src/object/psynergy_effects/cloak.c:7-11,71` | pennello |
| 252 | **Sporgenza (salto in basso)** | Spingi contro di essa per più di 12 fotogrammi tenendo premuto Giù, e il capogruppo salta giù. | `step.c:25-27,249`; `events.c:394-399` | pennello |
| 253 | **Parete scalabile / scala** | Spingi per più di 12 fotogrammi: Su sale, Giù scende. Durante l'arrampicata, un passo è permesso solo verso una cella con lo stesso codice. Arrivare su due celle 0xfd sovrapposte con y≠0 fa iniziare il gruppo in modalità arrampicata. | `events.c:407-415`; `src/field/field/player_control.c:874-881`; `src/object/object/actors.c:250-262` | pennello |
| 254 | **Varco da saltare** | Spingi per più di 12 fotogrammi: il capogruppo salta 2 celle in avanti se il punto di atterraggio lo permette (`Field_TryJumpForward`). 77 mappe. | `events.c:400-405`; `climbing.c:13-30` | pennello |
| 255 | **Muro** | Blocca sempre (`Map_CheckObjectStep` restituisce 2). | `src/field/field/terrain.c:477,526` | pennello |

La calpestabilità dipende anche dall'altezza. Un passo di più di 8 px in su o di più di 12 px in giù viene rifiutato (`terrain.c:494-497`), quindi un codice "pavimento" su una scogliera è comunque bloccato. La sovrapposizione della calpestabilità dovrebbe combinare il codice con le altezze di `grid_shape`. L'acqua **non** è un codice di collisione nelle mappe locali di TBS: è muro o altezza, e pozzanghere e simili sono trigger delle scene (DEDOTTO dall'istogramma: nessun codice dedicato).

I codici delle celle vengono anche cambiati durante l'esecuzione dal codice delle scene (`SetMapCellCollision`, `terrain.c:422`), a Colosso, Altin Peak, Crossbone Isle, Venus Lighthouse, Tolbi e Sol Sanctum. I codici 96..99 nelle mappe 078-083 (Altin Peak) non hanno un evento statico, quindi sono letti da uno script (DEDOTTO).

### 1.2 Istogramma d'uso (VERIFICATO da `coll_hist.py`, 182 mappe, celle nelle 3 finestre dei livelli)

| Codice | Celle | Mappe | Nota |
|---|---|---|---|
| 0 | 1,300,642 | 182 | pavimento |
| 255 | 47,077 | 151 | muro |
| 240 | 4,308 | 23 | terreno con mostri (dungeon/foreste: 009, 016, 025-030, 043, 046, 050, 055, 056, 062, 064, 066, 067, 078, 133, 136, 137, 164, 166, 167) |
| 21 | 4,244 | 34 | per esempio Lamakan Desert mappa 091: 2,677 celle di `EVENT_TOUCH 21 → HeatGauge_CountStep` |
| 251 | 1,729 | 9 | ombra per Cloak |
| 10 / 30 / 11 / 1 / 2 | 963 / 683 / 357 / 340 / 255 | 96 / 23 / 78 / 150 / 140 | i codici bassi sono per lo più uscite e script al contatto delle porte |
| 254 / 253 / 252 | 928 / 484 / 59 | 77 / 60 / 28 | salto / arrampicata / sporgenza |
| 243 / 244 / 242 / 245 / 246 | 500 / 482 / 388 / 32 / 18 | 29 / 29 / 28 / 6 / 3 | barili/casse/giare/tombe/libri vuoti |
| 100..107 | 100, 67, 37, 21, 8, 5, 3, 4 | 95..3 | forzieri (`SEARCH_CHEST` 66× su 100) e altre ricerche |
| 200..212 | 2..35 | 14..1 | punti di ricerca non marcatori (oggetti nascosti in giare/barili…) |
| 250 | 77 | 4 | pericolo |
| 249 | 3 | 3 | salto tra pietre |
| 241, 247, 248 | 0 | 0 | non usati |

I tipi di evento dietro 1..239 nelle mappe (conteggio = mappe): codice 1 → EXIT 130, TOUCH 44; codice 10 → TOUCH 65, EXIT 36; 100 → SEARCH_CHEST 66, SEARCH 36. Tabella completa: `coll_hist.json` (di prova). 136 coppie (mappa, codice) in 1..239 **non** hanno alcun evento statico nelle scene che usano la mappa. Sono usate da script o sono avanzi: mostrale come "Con script / sconosciuto".

### 1.3 Legenda per mappa (VERIFICATO, generata)

`collision_legend.py` scrive `collision_by_map.json` (di prova, 1 MB). Per ogni mappa fornisce:
- `scenes`;
- `cells_per_layer`, un istogramma dei codici per ogni finestra di livello;
- `events_by_code[code]`, un elenco di `{scene, table, kind: exit|touch|search|use_item|raised, control, condition, …}`, dove:
  - un'uscita ha `exit_kind, to_scene, to_entrance, to_name, to_symbol`;
  - uno script ha `script` (il simbolo ELF, per esempio `Event_EnterSanctum`, `HeatGauge_CountStep`);
  - un messaggio ha `message, text`;
  - una ricerca ha `search_target` (uno dei 32 nomi di `SearchTarget`, `include/field_scene.h:176-209`), `marker_chest` e `find_item/item_name | find_coins | psynergy_stone | mimic_slot`;
  - un contatto ha `needs_push` (0x200) e `needs_facing` (0x400).

La regola delle etichette per l'interfaccia è:
- "Uscita → {to_name}"
- "Evento: {nome dello script reso leggibile}"
- "Forziere: {oggetto}"
- "Ricerca {bersaglio}: {oggetto | testo}"

Quando non c'è alcun evento, l'etichetta è "Trigger non usato". Diverse tabelle per scena vengono scelte in base ai flag della storia, quindi l'interfaccia dovrebbe mostrarne l'unione e indicarla come "dipende dalla storia".

**Dati per l'editor:** `names/collision.json` (generato da `collision_json.py`):
```json
{"notes":[...],
 "ranges":[{"lo":0,"hi":0,"name":"Floor","category":"walk|block|move|search|trigger|unknown",
            "editor":"brush|trigger|trigger (markers own 100..239)|brush (advanced)|don't-touch",
            "meaning":"...","evidence":["src/...:lines"],"confidence":"VERIFIED","color":"#rrggbbaa"}],
 "codes":[{"code":240,"hex":"0xf0","range":"240-240","cells":4308,"maps":23}]}
```
Più una legenda per mappa generata al caricamento, nella forma di `collision_by_map.json` (`{map: {scenes, cells_per_layer[3]{code:count}, events_by_code{code:[event…]}}}`). L'editor dovrebbe costruirla durante l'esecuzione dagli overlay compilati (`Scenes` di gsmap) invece di distribuirla.

Tavolozza dei pennelli per i giocatori: Pavimento, Terreno con mostri, Muro, Sporgenza, Arrampicata, Varco da saltare, Ombra, Pericolo, e Giara/barile/cassa/tomba/libri vuoti. I trigger (1..239) non si dipingono mai liberamente. Vengono creati da azioni come "aggiungi porta" o "Aggiungi forziere", che assegnano un codice non usato su quella mappa (e sotto 100 per i non marcatori).

---

## 2. Oggetti

- **Id e simboli.** `include/item_ids.h` nomina solo gli id che il codice usa (VERIFICATO). La tabella degli oggetti `src/game/items.tsv` ha una riga per id (id = riga − 2, 324 righe), una colonna `label` con il nome inglese e le colonne price, type, flags, equip_mask, icon, … La struct è `ItemDefinition`, 0x2c byte (`include/game/item.h:104-137`).
  - Tipi: 0 nessuno (consumabile/chiave), 1 arma, 2 armatura, 3 scudo, 4 elmo, 5 stivali, 6 oggetto di Psicoenergia, 8 anello, 9 camicia (`item.h:43-55`).
  - Flag: 1 maledetto, 2 non rimovibile, 4 raro, **8 indispensabile (oggetto chiave)**, 0x10 accumulabile (`item.h:26-32`).
- **Nome inglese** = messaggio di en.po `MsgItemName + id` = **386 + id** (`item_ids.h:7-8`, en.po:1579; usato in `src/shop/shop/buy.c:350`, `src/window/window/decode.c:541`). Togli il prefisso `{article_class:N}`. Solo gli id 0..268 hanno un nome: 655 è `MsgEnemyName`. Descrizione = `MsgItemPlainName` (117) + id (`buy.c:68`). Controllati: 1 Long Sword, 180 Herb, 181 Nut, 268 Cleric's Ring (VERIFICATO).
- **Icone.** `src/graphics/ui/menu_icons/item_000.png`..`item_254.png`: PNG indicizzati 16×16, ciascuno con la propria palette da 16 colori, indice 0 trasparente. Tabella dei puntatori: `gUiIcon_ItemIconPointers` (`src/graphics/ui/menu_icons.s:4-261`). L'icona di un oggetto = `icon` di `items.tsv` (`ItemDefinition.icon`, `item.h:109`), disegnata da `ItemIcon_Compose` (`src/window/window/icons.c:114`); un indice ≥ al conteggio diventa 0 (`icons.c:63-64`). Herb → icona 117, Nut → 132.
  - **Regola dell'atlante:** icona k in (k%16·16, k//16·16) in un foglio 256×256.
  - L'atlante è stato costruito e controllato a occhio (di prova `items/item_icon_atlas.png`, `items/item_preview.png`): spade, armature, foglia dell'Herb, chiavi e sfere corrispondono tutte ai loro nomi.
  - Le varianti solo JA `item_080_ja`/`item_098_ja` non sono usate da EN.
  - DEDOTTO: la palette nel gioco è uguale a quella incorporata nel PNG.
- **Valori dei forzieri** (`include/field_scene.h:211-214`; `Field_SearchTile`, `src/object/object/events.c:429-560`), VERIFICATO:
  - `value & 0x0f000000 ≠ 0` → uno script (puntatore a funzione).
  - Altrimenti il tipo è `value & 0xfff00000`:
    - `0x100000` oggetto: metà bassa = id dell'oggetto; anche tutto ciò che non è 2/3/4/5 segue il percorso dell'oggetto.
    - `0x200000` monete: `(u16)` → 0..65535; il gioco usa 1..999.
    - `0x300000` Psynergy Stone: ripristina tutti i PP.
    - `0x400000` messaggio.
    - `0x500000` mimic: battaglia `Encounter_GetEnemyGroupAtSlot(99, slot)`. La zona 99 è "Mimic chests" (`src/object/encounter.tsv` riga 101, gruppi 350..357). Solo gli slot 0..7 sono validi (`encounter.c:244`).
  - `(value & 0xf0000) == 0x10000` → "Can't open it" per il gruppo (non usato).
  - La `condition` dell'evento è il flag di apertura: il forziere è mostrato aperto finché il flag è impostato, e il flag viene impostato quando si prende il contenuto. Se la borsa del gruppo è piena, l'oggetto resta e il flag resta non impostato (`events.c:565-590`).
  - Control `SEARCH(SEARCH_CHEST)` = 0x13. I bit 4..8 scelgono la riga "checked the X".
  - Indagine su 155 forzieri marcatori: 130 oggetti, 17 monete, 8 mimic (0x500000..0x500007, ciascuno una volta). Nessun forziere usa una Psynergy Stone o uno script.

**Dati per l'editor:** `names/items.json` (generato da `scripts/items/build_items.py`):
```json
[{"id":180,"symbol":"ITEM_HERB","symbol_in_header":true,"name":"Herb","description":"Replenishes 50 HP",
  "type":"none","type_id":0,"price":10,"flags":["stackable"],"key_item":false,"unused":false,
  "icon":117,"atlas":{"x":80,"y":112,"w":16,"h":16},"evidence":"items.tsv line 182; en.po msg 566"}]
```
L'output del selettore è `{"kind":"item","id":180}` → `FIND_ITEM(ITEM_HERB)` (0x1000b4), `{"kind":"coins","n":50}` → `FIND_COINS(50)`, `{"kind":"mimic","slot":0..7}` → `0x500000|slot`, oppure `{"kind":"psynergy_stone"}` → `FIND_PSYNERGY_STONE`. Nascondi le voci con `unused` (nome "?"/"???"/assente) e segnala con un avviso le voci `key_item`. L'atlante viene costruito durante l'esecuzione dalla copia di alchemy del giocatore, mai distribuito.

---

## 3. Sprite / NPC

- **Id → oggetto** (VERIFICATO):
  - `Event_SpawnObjectTable` (`src/object/object/actors.c:97-118`): gli id 0-7 = slot del gruppo, e `Party_RemapCharacterIdByFlags` (`actors.c:12-36`) scambia gli sprite da bambini 0x12/0x13 sotto `FLAG_CHILDHOOD`. Gli altri id prendono gli slot degli attori da 8 in poi nell'ordine delle righe (attore = 8 + riga).
  - Poi `Object_CreateFar(id)`, seleziona l'animazione 1 e imposta l'angolo da `facing`.
  - `FieldObject_Create` (`src/field/field/objects.c:245-290`): `id>>12` è il tipo. Tipo 0 = uno sprite `id & 0xfff`; tipo 2 (0x2000|n) = un gruppo di due sprite n, n+1; gli altri tipi non hanno sprite, per esempio 0x8000 = telecamera (`actors.c:266`).
- **Tabella degli sprite:** `gCharacter_DescriptorTable[id & 0xfff]` (`src/system/resource/metadata_get_record.c:7-9`) viene da `src/graphics/sprite/sprites.tsv` (513 righe; riga = id; colonne width, height, scale, drawKind, adjust, box, codec, frames, animations). Larghezza 0 = nessuna immagine (`src/field/field/animation.c:512`).
- **Regola dei PNG** (`tools/ags-graphics/sprite.c:120-160,295-330`):
  - `graphics/sprite/spr_NNN.png` della riga che possiede i fotogrammi; una riga alias si scrive `SPR_X=SPR_Y`.
  - Il foglio è una striscia verticale, con il fotogramma k a y = k·height. Un `spr_NNN.tsv` facoltativo con `list` rimappa i fotogrammi, e le sue righe `anim` sono le animazioni.
  - Palette: 8bpp, usa la palette condivisa da 224 colori `gSystem_BasicColorPalette` (`src/runtime/runtime/text.c:199`), incorporata in ogni PNG, con indice 0 trasparente.
- **Fotogramma di anteprima:** il primo comando di fotogramma dell'animazione 1 (i valori < 239 sono fotogrammi; 240 imposta il tipo di disegno; 254 salta a un'altra animazione; `src/field/field_internal.h:83-91`), più lo scostamento dell'orientamento per quel tipo di disegno (`src/field/facing.c`, applicato in `src/field/field/sprite_draw.c:150-185`; bit 7 = specchiato). Usa l'orientamento 0x3800 per una vista frontale diritta. Esattamente a 0x4000, i tipi 3 e 5 disegnano base+0 specchiato.
- **Id speciali:**
  - 20 forziere (VERIFICATO, `markers.c:70`).
  - 28 Psynergy Stone (VERIFICATO, `markers.c:105`).
  - 22 marcatore invisibile 16×16, usato 68× per banconi e punti con oggetti.
  - 4 e 7 hanno righe vuote.
  - 261-279 e 504 sono icone della mappa del mondo.
  - Le tabelle dei piazzamenti usano gli id 0..504.
- **Nomi.** Non esiste un enum globale degli sprite. I nomi vengono da:
  - `include/game/character_ids.h`;
  - enum `SPRITE_*` locali ai file (`src/scene/lunpa.h`, `vault_jail.c`, `tunnel_ruins.c`, `altin.c`, `altin_peak.c`, `tret_tree_*.c`, …);
  - commenti sulle righe.

  Questo dà 71 nomi VERIFICATI. Gli altri 178 sono DEDOTTI dall'immagine e dalle scene che usano l'id (per esempio "Townsperson A", "Dog"); `name_evidence` dice quali.
- I fogli di contatto sono stati controllati a occhio: fotogrammi frontali e colori corretti, nessuna immagine spazzatura. Sono `sprites/contact_sheet_npc60.png` e `sprites/contact_sheet_all.png` nella cartella di prova.

**Dati per l'editor:** `names/sprites.json` (generato da `scripts/sprites/build_sprites.py`, usando `spritelib.py`, `usage.py`, `names.py`, `names_manual.py` e `sheet.py`):
```json
[{"id":28,"hex":"0x1c","name":"Psynergy Stone","confidence":"VERIFIED","name_evidence":"...",
  "usage":1,"scenes":["MogallForest1"],"party_slot":false,"has_image":true,
  "png":"games/tbs/src/graphics/sprite/spr_028.png","frame":{"x":0,"y":0,"w":16,"h":16},
  "frame_index":0,"mirrored":false,"palette":{...},"draw_kind":11,"animation":1,"base_frame":0,
  "sheet_frames":11,"scale":256,"adjust":[0,2],"box":[20,16],"evidence":"sprites.tsv row 28 ..."}]
```
L'interfaccia ritaglia `png` a `frame` (specchiato se impostato) durante l'esecuzione. Per i nomi DEDOTTI si consiglia un file di sostituzioni "modifica nome" dal lato dell'editor.

---

## 4. Nomi dei luoghi

- `Scene_GetAreaNameIndex(scene, entrance)` (`src/object/object/encounter.c:326-350`) scorre `gScene_AreaNameRules` (`src/object/scene_rules.s:168-301`). Ogni riga è `scene_name Scene, entrance, index` oppure `group_name group, entrance, index` (`scene_rules.s:12-20`). Vince la **prima** riga corrispondente; l'ingresso -1 corrisponde a qualsiasi ingresso. Gruppo = `gField_SceneTable[scene].group` (`src/object/object/scene.c:157-159`; la colonna in `src/field/scenes.s`). Nessuna corrispondenza dà l'indice 0. (VERIFICATO)
- Testo = messaggio **`MsgDebugEntryName` + indice** (`src/object/psynergy_effects/world_map.c:400`, `src/window/battle_command/debug.c:23`). In EN, `MsgDebugEntryName` = 2459 = `RENDER_RESOURCE_BASE` 0x99B per le edizioni non europee con patch (`include/tbs_edition.h:264-271`, usato da `src/window/window/shortcuts.c:29`). Leggi la base dal `msgctxt "MsgDebugEntryName"` di en.po, non come costante. (VERIFICATO)
- Le righe `.if EDITION_INTERNATIONAL` (Altin Peak 4, ingressi 6/7) sono attive per EN (`include/game/ed_asm.h:11-16`).
- Risultato:
  - 199/201 scene ricevono un nome; Title (0) e LinkLobby (190, nominata solo per l'ingresso 1) no.
  - 21 scene non hanno un simbolo in `scenes.s`, quindi sono etichettate "Scene N" più il nome della loro area.
  - Esistono nomi specifici per ingresso, per esempio Sanctum: 1/2/20/21 Vale Sanctum, 10-12 Vault Sanctum, 35 Bilibin, 32 Xian, 29 Altin; VaultJail ingresso 2 = "Lunpa".
  - Visualizzazione: "{area_name} — {label}", per esempio "Vale — Vale Home". I nomi delle aree si ripetono in molte scene, quindi l'etichetta della scena le distingue.

**Dati per l'editor:** `names/places.json` (generato da `scripts/places.py`):
```json
{"area_message_base":2459,
 "scenes":[{"id":5,"symbol":"ValeHome","label":"Vale Home","group":3,"variant":2,"overlay":"0x374",
            "layered_row":4,"map":"003","area_index":10,"area_name":"Vale",
            "area_name_by_entrance":{},"area_message":2469}]}
```

---

## 5. Dialoghi

- **Schema di en.po** (VERIFICATO). Ogni voce è `msgctxt "<symbol>|message"`, `msgid "NNNNN"` (il numero del messaggio, con zeri iniziali fino a 5 cifre) e `msgstr` (testo). Ci sono 10.723 voci, 0..10722, senza buchi. I simboli escono come `out/tbs-en/text/msg_ids.h` (`#define TEXT_MESSAGE_NUMBER_<Sym> n`, `MSGNO(name)`). Il C delle scene scrive `MSGNO(MsgX)` nelle tabelle e `MsgX` nudo nel codice (`src/scene/README.md:60-61`).
- **Marcatura del testo:** `{page_break}` (nuovo riquadro), `{end_wait}` / `{end_now}` (fine), `{line_break}`, e gli argomenti `{protagonist_name}`, `{actor_name:N}`, `{argument_item_name:N}`, `{text_color:…}`, `{article_class:N}` (`tools/ags-text/symbols.c:28-60`). Un `\n` letterale è una riga visualizzata. Mostra i nomi come segnaposto, per esempio "[Isaac]".
- **Ricerca dei dialoghi** (`Scene_TalkToActor`, `src/object/object/events.c:197-290`; `Scene_FindEvent` `:111-165`):
  - Tipo 0 `EVENT_TALK`, con trigger = id dell'attore = 8 + riga del piazzamento.
  - Vince la prima riga la cui condizione è vera (-1 sempre; `flag|0x1000` = impostato; altrimenti non impostato), quindi un NPC può avere più righe scelte dai flag della storia.
  - `value < 0x10000` → un messaggio. Tutti gli 881 messaggi di dialogo diretti terminano con `{end_*}` (indagine), quindi un id è l'intero discorso.
  - Altrimenti il valore è uno script. Il tipo 7 è la battuta detta quando il gruppo ha fermato l'attore (`events.c:175-186`).
  - `talkFacing` controlla la rotazione.
- Per gli script, il dialogo sono i simboli `Msg*` nel corpo della funzione. Esempio: `Event_TalkAboutTheMayorAndTremors` (`src/scene/vale.c:160`) mostra `MsgValeTheGroundStillShakes` oppure `MsgValeYourGrandpaIsTheMayor` a seconda di `FLAG_PARTY_LEFT_VALE`. Questo dà un elenco di battute possibili, non il loro ordine né le loro condizioni (DEDOTTO sufficiente per le anteprime).
- I punti di ricerca mostrano `MsgTileChecked + target` e poi il testo di `FIND_MESSAGE` o del risultato (`events.c:452-470`).

**Dati per l'editor:** `dialogue.json` (di prova, 650 KB, generato da `scripts/dialogue.py`; 152 scene, 2.475 righe di dialogo). Contiene testo del gioco, quindi l'editor lo genera durante l'esecuzione:
```json
{"4":{"symbol":"Vale","tables":{"gVale_Events":[
  {"actor":8,"placement_row":0,"kind":"talk|talk_paused","condition":null|{"flag":2069,"when":"set|clear"},
   "message":3967,"msgctxt":"MsgValeMtAlephLooksBeautifulTodayIts","text":"Mt. Aleph looks\nbeautiful today..."},
  {"actor":10,"placement_row":2,"kind":"talk","condition":null,"script":"Event_TalkAboutTheMayorAndTremors",
   "source":"src/scene/vale.c","script_messages":[{"message":4556,"text":"..."}]}]}}}
```
Modificare il testo significa modificare il `msgstr` di `text/en.po` per msgid. Gli altri 5 cataloghi di lingua devono mantenere lo stesso insieme di msgid (`src/game/README.md:97-110`).

---

## 6. Flag

- **Memorizzazione:** 4.096 bit in `gGameFlagBytes`. I bit 0-2 del numero del flag scelgono il bit e i bit 3-11 il byte (`src/game/game/flags.c:7-24`, `include/game/game_flags.h:12`). Gli accessori a byte trattano 8 flag consecutivi come un unico contatore (`src/game/README.md:110-121`). Vengono tutti salvati (README; il checksum del salvataggio copre `gGameFlagBytes`, `include/save_state.h:55`).
- **Condizioni:** `-1` sempre, `flag|0x1000` = impostato, altrimenti il flag non è impostato. 0 su un piazzamento = "in vista" (`events.c:59-77`).
- **Intervalli** (`src/scene/README.md:48-59`, `include/flags.h:7-20`):
  - 0x000-0x0ff: gruppo (0-7) e Djinn (48-127).
  - 0x100-0x1ff: motore/sistema.
  - **0x200-0x2ff: temporanei di scena, azzerati a ogni ingresso.**
  - **0x300-0x3ff: flag di gruppo, azzerati entrando in un altro gruppo, numeri riutilizzati per ogni luogo.**
  - 0x400-0x7ff: nessun uso trovato (un riferimento, 0x400; DEDOTTO non usati, ma da evitare).
  - 0x800-0xdff: storia.
  - 0xe00-0xfff: flag di forzieri/ritrovamenti.
- **Nomi:** `include/flags.h` (970 righe) `#define FLAG_* value` con commenti `///`, per esempio `FLAG_ALTIN_PEAK_LUCKY_MEDAL 0xf78 ///< room 8's chest`. I flag locali di una scena sono definiti con `#define` nel file della scena stessa e non sono in flags.h.
- **Indagine sull'uso** (`flags_survey.py`, VERIFICATO nei limiti delle sue fonti):
  1. Ogni condizione, requiredFlag, flag di uscita e condizione di regione nelle tabelle degli overlay compilati.
  2. Ogni chiamata a un accessore di flag con argomento costante nell'output di `clang -E` di ciascun `src/**/*.c`. L'output va solo su stdout e alchemy non viene toccato.
  3. I campi flag delle righe `scene_cue`/`group_cue`/`location` in `scene_rules.s` e `location_rules.s`.
  4. Tutte le definizioni di flags.h.

  Trovati in uso: 0xe00-0xfff 213/512; 0x800-0xdff 300; 0x300-0x3ff 108.
- **Elenco prudente dei liberi** (`flags_free.py`): esclude inoltre qualsiasi valore 0xe00..0xfff (o la sua forma di condizione 0x1e00) che compaia come letterale esadecimale in qualunque punto di `src`/`include`, fuori dai dati di grafica e mappe. Restano **251 flag liberi**. Sequenze: 0xe03-0xe0f, 0xe49-0xe58, 0xe61-0xe73, 0xe81-0xea1, 0xef8-0xeff, 0xf09-0xf12, 0xfdb-0xfe0, … (`flags.json` `free_chest_flags`).
- **Regola di assegnazione per un nuovo forziere:**
  1. Prendi il flag più basso in `free_chest_flags` che non sia già usato dalle tabelle di sostituzione della mod (`games/tbs/src/mod/`) o da altre modifiche in sospeso.
  2. Scrivilo come condizione dell'evento `SEARCH(SEARCH_CHEST)`.
  3. Registralo nel manifesto della mod in modo che non venga mai riutilizzato, anche dopo l'eliminazione del forziere (nei vecchi salvataggi potrebbe essere impostato).
  4. Ricontrolla a ogni aggiornamento della versione fissata di alchemy rieseguendo l'indagine; l'elenco dei liberi dipende dal commit.
- **Verificare che un flag sia inutilizzato**, in quest'ordine:
  1. Non è in `used` di un'esecuzione recente di `flags_survey.py` (tabelle + codice + regole).
  2. Non c'è alcuna corrispondenza come letterale esadecimale (`flags_free.py`).
  3. Non è nel byte di alcun flag usato tramite accessore a byte (l'indagine li segna tutti e 8).
  4. Non è in 0x200-0x3ff.
  5. Dopo la build, cercare con `grep` l'halfword nel `.bin` dell'overlay **non** è affidabile (falsi positivi), quindi affidati a 1-4.

**Dati per l'editor:** `names/flags.json` (generato dai due script):
```json
{"total_flags":4096,
 "ranges":[{"lo":3584,"hi":4095,"meaning":"chest / find flags","editor":"allocate new chest flags here"}],
 "names":{"0xf78":["FLAG_ALTIN_PEAK_LUCKY_MEDAL"]},
 "used":{"0xf78":["flags.h","table 3a4:gAltinPeak_Events..."]},
 "free_chest_flags":[3585,3587,...]}
```

---

## File generati e come sono stati prodotti

Tutti gli script sono in `names/scripts/` (copie) e nella cartella di prova indicata sopra. Dipendono da `gsmap` di gs-mapedit (Project, Scenes, grid) e da `out/tbs-en`.

| File | Script | Input |
|---|---|---|
| `names/collision.json` | `collision_json.py` (dopo `coll_hist.py`) | lettura del motore descritta sopra; istogramma su `src/map/*/grid_collision.tsv` |
| `collision_by_map.json` di prova | `collision_legend.py` | griglie + tabelle di eventi/uscite compilate + `places.json` + `items.json` + en.po |
| `names/items.json` | `items/build_items.py` | `src/game/items.tsv`, en.po, `item_ids.h`, `graphics/ui/menu_icons/` |
| `items/search_events.json` di prova | `items/survey_chests.py` | tabelle degli eventi compilate |
| `names/sprites.json` | `sprites/build_sprites.py` (+ `spritelib.py`, `usage.py`, `names.py`, `names_manual.py`, `sheet.py`) | `graphics/sprite/sprites.tsv`, `spr_*.png`/`.tsv`, tabelle dei piazzamenti compilate, sorgenti delle scene |
| `names/places.json` | `places.py` (+ `po.py`) | `src/field/scenes.s`, `src/object/scene_rules.s`, en.po, `layered.tsv` tramite gsmap |
| `dialogue.json` di prova | `dialogue.py` | tabelle degli eventi compilate, simboli ELF degli overlay, `src/scene/**`, `out/tbs-en/text/msg_ids.h`, en.po |
| `names/flags.json` | `flags_survey.py` → `flags_free.py` → unione in linea | tabelle compilate, `clang -E` di `src/**/*.c`, file `.s` delle regole, flags.h |

Le immagini (atlante delle icone, fogli di contatto) e il testo del gioco non vengono volutamente inclusi nel repository; secondo la posizione legale di PRODUCT.md, l'app li costruisce dalla copia di lavoro del giocatore.

## Incognite

- Che cosa significhi 248 (nessun lettore, non usato), e se 241 funzioni come previsto (nessuna mappa lo usa).
- I codici 96..99 (Altin Peak) e 136 coppie (mappa, codice) in 1..239 non hanno alcun evento statico. Presumibilmente sono letti dal codice delle scene (chiamanti di `GetMapCellCollision`) o sono avanzi.
- Il significato delle collisioni sulla **mappa del mondo** è un sistema separato (byte di passo di `blocks.tsv`, `attributes.tsv`): vedi `overworld.md`.
- Chi scrive `touched_trigger`, e i bit alti del control dell'evento su 22 forzieri (0x400, 0x8400, 0xc400). Il bit 0x400 del *trigger* salta la riga "checked"; il significato dei bit del control non è confermato.
- Lo slot di palette nel gioco per le icone degli oggetti (si presume la palette del PNG).
- I 178 nomi di sprite DEDOTTI. Alcuni sono ipotesi (per esempio 44 "Dodonpa", 66/67, 69 "Lady Layana"). Il limite dell'indice dell'attore 0x2705 è segnato XXX nel sorgente. JA/IT usano `spriteja.tsv`/`spriteit.tsv`.
- Se un messaggio senza `{end_*}` prosegua nell'id successivo. Nessun messaggio di dialogo diretto ne è privo, quindi per le anteprime non importa.
- L'indagine sui flag non coglie i flag raggiunti solo tramite variabili o espressioni calcolate (5.191 chiamate ad accessori non costanti, incluse definizioni e cicli) né i flag negli array di dati C. Il passaggio sui letterali esadecimali copre la maggior parte di questi casi; 0x400-0x7ff sembra inutilizzato ma non è dimostrato.
- Se lo slot del mimic possa superare 7 in sicurezza (legge nella zona successiva, quindi non è utile).
