<!-- translated from docs/SPEC.md @ fc648c206c4f -->
# gs-mapedit: specifica dell'editor e piano di sviluppo

*Questa è una traduzione del file inglese [SPEC.md](../SPEC.md); se i due differiscono, vale quello inglese.*

Ambito: un editor di mappe per **Golden Sun: The Broken Seal** costruito sull'albero dei sorgenti di alchemy. Copre le **mappe locali** (città, dungeon, interni) e il **mondo esterno**. The Lost Age condivide il formato delle mappe locali, quindi arriverà più avanti con poco sforzo. Il motore del suo mondo esterno è ancora per lo più in assembly in alchemy.

L'editor legge e scrive solo i file sorgente di alchemy: TSV, PNG e zone ristrette di tabelle C/asm. Non tocca mai una ROM. Le prove dettagliate, con riferimenti file:riga, sono in `docs/research/` (`rendering.md`, `local-connections.md`, `overworld.md`). Questo file riporta le decisioni.

## Regole di base

1. **Andata e ritorno identica byte per byte.** Caricare e salvare qualsiasi cosa non modificata deve riprodurre il file byte per byte. Ogni tipo di file ha un test di andata e ritorno sull'intero albero. Una build non modificata deve continuare a dare OK con `compare`.
2. **Modifica sul posto; aggiungi in fondo, non inserire.** Le posizioni delle righe nelle tabelle sono identità. Numero dell'attore = 8 + riga di posizionamento. Id della scena = riga in `scenes.s`. Le tabelle delle uscite usano semplici numeri di scena. Inserire una riga rinumera le cose senza avvisare, quindi le nuove righe vanno in fondo.
3. **Valida prima di salvare.** Ogni operazione ha delle invarianti (sotto). L'editor si rifiuta di salvare uno stato che ne viola una, oppure lo segnala chiaramente.
4. **La build è il giudice.** Dopo il salvataggio, esegui `make tbs-en`. L'editor mostra gli errori di build. Una prova di gioco in mGBA è il controllo finale.
5. **Fissa alchemy.** Lavora su un commit noto. Prima di passare a uno nuovo, esegui `tests/roundtrip.py` e il controllo di rendering completo (circa 2 minuti). Hanno rilevato subito la ristrutturazione dei percorsi del 19 ottobre.

## Mappe locali

### Rendering (implementato, verificato su tutte le 182 mappe)

- **Risorse:** la palette, i char block 1–3 e il foglio D di ogni mappa vengono dalla sua riga di `gMaps` (`map/maps.c`), risolta tramite il `gamepak/resource_directory.s` espanso. Le mappe 001, 002, 108 e 110 hanno righe alternative.
- **Segnaposto:** la k-esima cella `0xfff`, per righe sull'intera griglia 128×128, è il blocco k con il suo nibble alto mantenuto (`field/map_grid_convert.s`). Il numero di segnaposto è uguale al numero di righe di `metatiles.tsv` su tutte le 182 mappe.
- **Finestre:** la finestra di ogni livello parte dall'origine del livello più i limiti dell'intestazione e si avvolge a 128.
- **Ancora da fare:**
  - composizione della fusione (`blend.tsv`: BLDCNT/BLDALPHA/BLDY);
  - animazione delle tile (`animation.tsv`, foglio D);
  - ancoraggio della parallasse per le mappe 047, 103, 104, 147 e 148;
  - limiti facoltativi della telecamera dagli ingressi delle scene.

  Le regole sono in `rendering.md`.

### Dati modificabili e invarianti

| Cosa | File | Modifica | Invarianti / note |
|---|---|---|---|
| Blocchi per cella (3 livelli) | `map.txt`, l'immagine di ogni cella | dipingere id di blocco risolti | Salvato con il **codificatore dei segnaposto**: percorri per righe con un contatore k. Una cella il cui blocco == k viene scritta `0xfff` (nibble alto mantenuto) e k++; le altre celle vengono scritte esplicitamente. Verificato come inverso esatto su tutte le 182 mappe. |
| Definizioni dei blocchi | `cell_pictures.tsv` | aggiungere nuove combinazioni di tile 2×2 | Massimo 4.095 blocchi. Numero di riga = id del blocco. |
| Codici di collisione | `map.txt`, il comportamento di ogni cella | dipingere | Per finestra di livello. I codici 1–239 possono portare eventi (uscite, forzieri). |
| Altezza / forma | `map.txt`, la forma di ogni cella, + `shapes.tsv` | dipingere | Per finestra di livello. |
| Forzieri / Psynergy Stone | righe `treasure_spot x, z, id` in `map.s` | aggiungere/spostare/rimuovere | **id deve essere uguale al codice di collisione in (x, z)**: verificato 418/418. Il gioco ne piazza al massimo 10 per scena, contando solo i marcatori il cui codice è un forziere o una Psynergy Stone non ancora presa negli eventi di quella scena (`treasure_spots.c`). Riga marcatore di fine `ff ff ff`. Il contenuto richiede un evento `SEARCH(SEARCH_CHEST)` nella scena con un nuovo flag. |
| Animazione delle tile | `animation.tsv` | più avanti | Massimo 16 canali. |

File condivisi: i blocchi possono venire dalla cartella di un'altra mappa, e anche le celle e gli attributi di `default/` sono condivisi. L'editor mostra quando un file è condiviso e avvisa prima di modificarlo.

### Tabelle delle scene: un hook, override gestiti dall'editor

**Progetto (indicazione del proprietario): modifiche minime ai file di alchemy.**
- Il motore legge ogni tabella delle scene tramite `gOverlayArea`, la tabella d'ingresso dell'overlay della scena in RAM. Gli overlay vengono caricati in un solo punto: `Scene_LoadOverlay` (`system/main_routine.c`).
- L'editor aggiunge lì **una riga**, `MOD_SCENE_LOADED(gMainRoutineWork.next, &gOverlayArea);`. È una macro che si espande nel nulla a meno che la build non definisca `GSMOD`, così la build originale continua a corrispondere alla versione commerciale.
- Con `GSMOD`, la macro chiama il codice generato dall'editor in `games/tbs/src/mod/`. Quel codice sostituisce i puntatori a funzione della tabella d'ingresso (ingressi, uscite, posizionamenti, eventi, regioni) con funzioni che restituiscono le tabelle di override dell'editor per quella scena, e lascia stare il resto.
- Anche la mappa del mondo è un overlay di scena, quindi lo stesso hook copre le icone, le uscite e gli eventi del mondo esterno.
- I file `.c` delle scene non vengono mai riscritti. Le tabelle di override stanno nella cartella della mod, in ROM. I file di soli dati (tabelle delle mappe, righe dei forzieri) vengono comunque modificati direttamente.

Le tabelle sottostanti, per riferimento:

Le scene stanno in `games/tbs/src/scene/<place>.c`. Contengono cinque tipi di tabella, tutti array C a livello di file fatti di letterali e macro:

| Tabella | Numero | Campi della riga |
|---|---|---|
| Ingressi | 189 | entrance, required_flag, x, y, z, facing, limiti della telecamera |
| Uscite | 99 | tipo → (scena, ingresso), flag facoltativo |
| Posizionamenti | 274 | sprite, condizione, comportamento, x, y, z, orientamento, orientamento nel dialogo, flag |
| Eventi | 263 | tipo/controllo, attivatore, condizione, valore |
| Regioni | 14 | riquadro min/max, condizione, tipo di uscita |

L'editor *legge* questi array dai file `.c` delle scene, inizializzando un override con le righe originali di una scena, e *scrive* solo le copie di override in `mod/`. Eventi: decodifica le parole di controllo note e mantiene alla lettera quelle sconosciute (circa 220 sono esadecimale grezzo).

Validazione:
- L'ingresso di destinazione di ogni uscita esiste nella scena di destinazione.
- Le righe di posizionamento non vengono inserite a metà tabella (spostamento dei numeri degli attori).
- La dimensione dell'overlay resta sotto i 32 KB (il più grande ha 120 B liberi).
- Le righe con x=z=0 vengono posizionate dal codice; l'editor le segna come sola lettura.

Il grafo delle uscite è: codice di collisione / script / regione → tipo di uscita → tabella delle uscite → (scena, ingresso) → riga dell'ingresso. L'editor lo mostra come link cliccabili tra le mappe.

### Nuove mappe (ultima fase)

La lista di controllo è in `local-connections.md` §6:
- 25 slot liberi nella directory delle risorse, fissati a 0x08320000;
- aggiungere righe a `gMaps` (`map/maps.c`) e `scenes.s`;
- aggiungere la riga della mappa a `ld_script.ld` prima degli overlay, più l'overlay, la musica, il nome dell'area e le regole degli incontri;
- gruppo ≤ 0x7f, id di scena < 511.

**Lo spazio nella ROM è il vero limite:** da 3,5 a 43 KB liberi alla fine degli 8 MB, a seconda dell'edizione. Una vera nuova mappa probabilmente significa far crescere la ROM oltre gli 8 MB, cosa non testata.

## Mondo esterno

| Cosa | File | Note |
|---|---|---|
| Celle del terreno + della sovrapposizione | `map/world/blocks.tsv` | 320×512 u32. I chunk sono di 16×16 celle, disposti 32 per riga nel TSV e 16×16 nel mondo. Terreno = chunk c, sovrapposizione = c + 320. Alternative 256–319 (set della neve, ponte della storia). Bit della cella: 0–15 blocco, 16–23 codice di passo/evento, 24–30 tipo di terreno (= regione degli incontri), 31 banco di comportamento. |
| Blocchi | `map/default/cells.tsv` | 4.386 × 4 byte di tile. **Condiviso con le mappe locali.** Meglio aggiungere in fondo. |
| Calpestabilità | `map/default/attributes.tsv` | Per tile 8×8, 4×4 nibble. Vince la sovrapposizione, poi il terreno, altrimenti 7. I valori 5–12 sono calpestabili. Anche questo è condiviso. |
| Grafica | `graphics/world_map/*.png` | 8bpp, 256 tile per livello, 224 colori. Il set B è il nord innevato. Mantieni la modalità e gli indici dei PNG. |
| Icone delle città / entrare | `scene/world_map.c` `gWorldMapPlacements`, `gWorldMapEvents`, `gWorldMapExits` | Icona = attore 8 + riga. Toccarla attiva l'attivatore 100 + attore → `EVENT_EXIT` → uscita → (scena, ingresso). Alcune voci sono invece codici di passo. Devono restare allineate con `gWorldMap_PlaceMarkers` (attore 11 + i). |
| Uscire verso il mondo | `gWorldMapEntrances` | Il `SCENE_EXIT(n, 2, e)` di una città mette il gruppo alla riga e. |
| Incontri | regole di `object/zonedata.c` → zone di `object/encounter.tsv` | Tipo di terreno + comportamento → regola → zona (104 righe fisse). |

Avvertenze:
- La mappa della schermata di pausa (`picture.png`) è una grafica separata, quindi va ridipinta a mano dopo le modifiche alle coste.
- In TBS non ci sono varianti del mondo esterno per lingua.
- Il mondo esterno di The Lost Age è diverso (2048 chunk, 32×32) e il suo motore è per lo più in assembly, quindi resta fuori dall'ambito finché alchemy non lo fa corrispondere.

## Piano di sviluppo

| Fase | Consegna | Verifica |
|---|---|---|
| **1. Visualizzatore** ✅ | Tutte le 182 mappe locali disegnate correttamente; sovrapposizioni; informazioni al passaggio del mouse | andata e ritorno su 895 file; rendering completo; controlli visivi |
| **1b. Fedeltà del rendering** | Composizione della fusione, tile animate (riproduzione/fotogramma), ancoraggio della parallasse, ritaglio ai limiti della telecamera | Confronto con i rendering convalidati di `rendering.md`; idealmente screenshot di mGBA |
| **2. Pittura locale** ✅ tranne il compositore di nuovi blocchi | Palette di blocchi dall'atlante; pittura per livello; pennelli di collisione/altezza; compositore di nuovi blocchi (scegli 4 tile); annulla/ripeti; salvataggio con il codificatore dei segnaposto | Salvataggio non modificato identico byte per byte; salvataggio modificato che compila (`make tbs-en`); si avvia in mGBA |
| **3. Marcatori + tabelle delle scene** ✅ aggiunta, riempimento, spostamento e rimozione dei forzieri; porte collegate con un clic (ricollegamento, aggiunta, rimozione, porte con script incluse); eventi a parole con nuove battute, cartelli, messaggi al passaggio, persone e condizioni; aree di uscita; spostamento delle pietre; ingressi, PNG, uscite | Posizionamento di forzieri/pietre (marcatore + collisione + evento); modifica di ingressi/uscite/posizionamenti; navigazione del grafo delle uscite tra le mappe | Andata e ritorno delle tabelle identica byte per byte su tutte le 201 scene; build; prova di gioco di una modifica a un'uscita |
| **4. Visualizzatore del mondo esterno** ✅ | Mondo dall'alto con set A/B, livello di sovrapposizione, calpestabilità, sovrapposizione tipo di terreno/incontri, icone delle città e link delle uscite | Portare il prototipo di ricerca; confronto con `world_mixed_small.png` |
| **5. Modifica del mondo esterno** ✅ blocchi di terreno/sovrapposizione, regioni e le loro zone degli incontri, spostamento, collegamento e aggiunta di icone, punti di passaggio | Dipingere celle (blocco, tipo di terreno, codice di passo); modificare icone, uscite, ingressi; zone degli incontri | Andata e ritorno di `blocks.tsv` e delle tabelle; build; prova di gioco |
| **6. Nuove mappe / scene** | Procedura guidata per la lista di controllo delle nuove mappe; indicatore del budget della ROM | Build; prova di gioco |

Le fasi 2–3 rendono l'editor locale davvero utile. Le 4–5 aggiungono il mondo esterno. La 6 è la più rischiosa, perché dipende dallo spazio nella ROM.

## Domande aperte

- ~~La build richiede che il numero di segnaposto = numero di blocchi?~~ **No.** Testato: una modifica che lascia 56 segnaposto per 441 blocchi compila e si collega. Il codificatore scrive esplicitamente i blocchi successivi una volta che una prima occorrenza viene ridipinta, quindi il diff è più grande ma valido. L'aspetto nel gioco richiede ancora una prova di gioco.
- Mappe il cui `blend.tsv` non imposta mai BLDCNT (039, 042, 043, 114, 125): la fusione probabilmente viene dal codice della scena.
- Cosa sono gli `scene_points` di TLA; cosa scrive `touched_trigger`; valori di comportamento dei posizionamenti superiori a 2.
- Se una ROM oltre gli 8 MB si avvia e salva correttamente sugli emulatori e sull'hardware di destinazione.
