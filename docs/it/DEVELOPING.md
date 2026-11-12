<!-- translated from docs/DEVELOPING.md @ 0055eb8d2996 -->
# Sviluppare GS Map Editor

*Questa è una traduzione del file inglese [DEVELOPING.md](../DEVELOPING.md); se i due differiscono, vale quello inglese.*

Come avviare, compilare, testare e aggiornare l'editor, e come funzionano dall'interno le sue funzioni. Per imparare a usarlo, leggi il [README](../../README.it.md).

## Avviarlo dai sorgenti

Servono Python 3 con Pillow e un checkout di alchemy già compilato.

```sh
python3 server.py                  # alchemy in ~/gs_project/alchemy-port
python3 server.py --root /path/to/alchemy --port 8765
# apri http://127.0.0.1:8765/
```

### App desktop (macOS)

`GS Map Editor.app` è l'editor in una finestra tutta sua, per i giocatori che non aprono mai un terminale.

```sh
python3 -m venv .venv && .venv/bin/pip install pywebview pyinstaller pillow
python3 packaging/build_toolchain.py                          # binutils per GBA + libpng, ~10 min, una volta sola
.venv/bin/python packaging/make_icon.py                       # packaging/icon.icns
.venv/bin/pyinstaller --noconfirm packaging/gsmapedit.spec    # -> dist/GS Map Editor.app
python3 packaging/make_dmg.py                                 # -> dist/GS-Map-Editor-<version>.dmg
python3 packaging/sign_and_notarize.py --identity "Developer ID Application: …"   # serve un account Apple Developer
.venv/bin/python desktop.py                                   # oppure avvialo senza impacchettarlo
```

L'app porta con sé i propri strumenti di compilazione (`packaging/toolchain`, 15 MB): le GNU binutils per il GBA, una libpng statica e un piccolo sostituto di `libpng-config` che risponde al `tools/Makefile` di alchemy. Sono compilati da sorgenti fissati a una versione e con checksum verificato, e non hanno bisogno d'altro che di macOS. Con questi, ai giocatori servono solo gli strumenti per sviluppatori gratuiti di Apple; Homebrew viene usato solo da una build senza la toolchain. `GSMAP_NO_BREW=1` nasconde Homebrew, per dimostrare che una build non ne ha bisogno.

Al primo avvio mostra una lista di configurazione (`static/setup.html`, `gsmap/setup.py`). Ogni passaggio viene verificato, mai dato per scontato, e i passaggi lunghi mostrano il loro log in tempo reale:
1. Gli strumenti per sviluppatori di Apple (apre l'installer di Apple).
2. Gli strumenti di compilazione: inclusi nell'app. Una build senza di essi ripiega su Homebrew e sui pacchetti indicati nell'INSTALL.md di alchemy, verificati in base a ciò che la build usa e non in base ai nomi delle formule.
3. Il sorgente del gioco: scarica alchemy (fissato al commit con cui questo editor è stato testato) in `~/Documents/GSMapEditor/` (senza spazi: la build non li gestisce), oppure scegli un checkout esistente.
4. `make bootstrap` (i compilatori del gioco, compilati una volta sola dai sorgenti nel submodule `alchemy-gcc` di alchemy, senza download), poi un primo `make tbs-en`.

Dopo di che, l'app si apre direttamente nell'editor. Le impostazioni stanno in `~/Library/Application Support/GS Map Editor/`. L'app non contiene dati del gioco: il gioco viene compilato dai sorgenti di alchemy sul Mac del giocatore. Entrambi i suoi server ascoltano solo su questa macchina, protetti da un token casuale. `desktop.py --no-window` stampa i loro indirizzi, per i test.

### Linux e Windows (WSL)

Su Linux l'editor gira dai sorgenti e si apre nel browser: `python3 desktop.py` (serve `python3-pil`) mostra la stessa lista di configurazione, con i pacchetti apt dell'INSTALL.md di alchemy al posto di Homebrew. Installarli richiede `sudo`, quindi la lista mostra il comando invece di eseguirlo. Le impostazioni vanno in `~/.config/gs-map-editor`, la cache di compilazione in `~/.cache/gs-map-editor`, e il sorgente del gioco e le esportazioni in `~/GSMapEditor`. Ciò che cambia da sistema a sistema (cartelle, apertura di un link, mGBA, mostrare un file) si trova in `gsmap/host.py`.

Windows esegue lo stesso editor Linux dentro WSL, che è anche l'unico modo in cui alchemy si compila su Windows:
- `windows/Install-GS-Map-Editor.cmd`, che una release include con il suo tag già inserito, attiva WSL e installa Ubuntu se serve (diritti di amministratore, forse un riavvio), esegue `windows/setup-in-wsl.sh` dentro Ubuntu a quel tag, e aggiunge collegamenti nel menu Start e sul desktop a `wsl.exe … gs-map-editor`.
- L'editor si apre nel browser di Windows attraverso l'inoltro di localhost di WSL. Gioca avvia l'mGBA di Windows da `Program Files\mGBA`, passandogli il percorso `\\wsl.localhost\…` del gioco. Il gioco viene compilato sul disco di Ubuntu, perché una build su `/mnt/c` è molte volte più lenta.
- Le pagine mostrano Ctrl e Alt al posto di ⌘ e ⌥ su qualsiasi sistema che non sia un Mac (`localWords` in `static/common.js`).

`.github/workflows/linux.yml` lo verifica sulle macchine Ubuntu di GitHub a ogni push: `setup-in-wsl.sh` installa l'editor, `tests/setup_flow.py` percorre la configurazione del primo avvio tramite il comando installato, la build deve corrispondere a `rom.sha1`, e i test di andata e ritorno, di modifica e di posizionamento girano su quel checkout. La metà Windows (il `.cmd`, l'installazione di WSL, il collegamento, l'mGBA di Windows) non ha test automatici: serve un PC Windows.

### Pubblicare una release

Le release sono compilate da GitHub, sui suoi Mac, da `.github/workflows/release.yml`: un'immagine disco per Apple Silicon (`macos-15`) e una per Intel (`macos-15-intel`). Ogni job compila la toolchain e l'app, verifica che entrambe siano per il suo chip, esegue `packaging/smoke_test.py` (l'app si avvia, trova i suoi strumenti e nomina il commit fissato) e crea il `.dmg`.

1. Imposta la versione in `packaging/gsmapedit.spec` (`CFBundleShortVersionString`).
2. Scrivi le note che leggeranno i giocatori in `docs/releases/v<version>.md`.
3. Fai il commit, poi `git tag v<version> && git push origin v<version>`. Il workflow pubblica una pre-release con entrambe le immagini, anche se il job di un chip fallisce.

**Run workflow** nella pagina Actions compila le immagini senza pubblicare una release. Le immagini non sono firmate: la sezione "Aprirla la prima volta" del README spiega come i giocatori superano Gatekeeper, e `packaging/sign_and_notarize.py` subentra quando ci sarà un Developer ID.

## Come funziona ogni funzione

Mappe locali, The Broken Seal, edizione inglese. Per come usarle, vedi il [README](../../README.it.md).

- **Visualizza:** tutte le 182 mappe, con i set di tile corretti e i segnaposto, attivazione e opacità per livello, sovrapposizioni di collisione e altezza.
- **Dipingi:** blocchi, collisione e altezza, con contagocce ⌥-clic e annulla/ripeti. I salvataggi sono identici byte per byte per tutto ciò che non è stato modificato.
- **Timbro** (S): trascina un rettangolo per copiare un'area, poi clicca per incollarla, qui o in un'altra mappa con lo stesso set di blocchi (Vale ↔ Debug · Sandbox).
  - La copia porta con sé tutti e tre i livelli più calpestabilità e altezza.
  - **Solo oggetti** incolla solo gli alberi e gli altri oggetti, non il terreno sotto di essi (un test sul colore rispetto al blocco di sfondo di ciascun livello).
  - Un incollaggio è un solo passo di annullamento. Gli appunti sopravvivono al cambio di mappa e al ricaricamento della pagina. Esc torna alla copia.
  - Le mappe con un set di blocchi diverso rifiutano l'incollaggio, perché ogni numero di blocco disegnerebbe la tile sbagliata.
- **Importa immagine…** (mappe con un set di tile proprio; oggi il Debug · Sandbox): scegli un PNG e un livello e guarda un'anteprima, poi **Aggiungi al set di tile**. I nuovi blocchi finiscono negli appunti del Timbro, pronti per essere messi al loro posto con un clic.
  - L'importatore taglia l'immagine in tile 8×8 e ne adatta i colori a una delle 14 righe di palette della mappa (ogni tile sceglie una riga propria solo se nessuna riga singola va bene). L'indice 0 è trasparente.
  - Le tile già presenti nei fogli, comprese quelle specchiate, vengono riutilizzate.
  - Le nuove tile vanno prima negli spazi vuoti. Poi vengono le tile usate solo da blocchi che la mappa non piazza mai. Quei blocchi vengono *ritirati* (nascosti dalla palette, rifiutati dal Timbro) ed elencati in `games/tbs/src/mod/tilesets.json` di alchemy.
  - L'anteprima mostra i colori che il gioco disegnerà, più quanto spazio rimane.
- **Eventi** (E): tutto ciò che succede in una scena, a parole, per la fase della storia che scegli:
  - **Persone:** "🗨 Garet: “Ever since the tremors started…”", pensieri di Mind Read e script con una loro descrizione ("Chiede del sindaco prima della partenza, o dei tremori dopo il ritorno").
  - **Punti:** cartelli (da leggere con A), messaggi al passaggio, punti da esaminare e ciò che vi si trova.
  - **Aree di uscita:** riquadri che fanno da porte, disegnati sulla mappa. Cambia dove portano, o rimuovili.
  - Clicca una persona per vederne gli eventi e **Fagli dire qualcosa…** (o **Aggiungi una battuta per un momento della storia…**). Clicca un punto qualsiasi per aggiungere **un cartello**, **un messaggio al passaggio** o **una persona**.
  - **Cambia parole** apre un editor di testo con anteprime dal vivo dei riquadri di dialogo: scrivi normalmente, e una riga vuota inizia un nuovo riquadro. **Quando…** imposta "sempre", "solo dopo che <flag della storia> è attivo" o "solo finché non è attivo", con i flag per nome.
  - Le nuove battute vengono aggiunte a `en.po` in un blocco gestito dall'editor. Le battute del gioco non vengono mai riscritte: cambiare ciò che qualcuno dice lo fa puntare a una battuta nuova. Il testo che il font del gioco non sa disegnare viene rifiutato prima della build.
  - Quando una scena condivide le sue persone e i suoi eventi con altre (la sandbox e l'hub di debug lo fanno), il pannello lo dice.
- **Porte** (D): ogni porta appare sulla mappa con la sua destinazione ("→ Vale Home"); quelle che non portano da nessuna parte appaiono in rosso.
  - Clicca una porta, poi **Cambia dove porta…**: scegli un luogo, poi clicca un punto di arrivo sulla sua mappa.
  - Clicca un qualsiasi altro punto e **Crea una porta qui…** per aggiungere una porta verso qualunque posto del gioco. **Rimuovi porta** riporta tutte le celle di una porta a terreno.
  - Vengono trovate anche le porte aperte dagli script di scena (la maggior parte di quelle di Vale), leggendo quale uscita chiede lo script. La loro destinazione si può cambiare; lo script resta.
  - Una porta cambia in tutte le fasi della storia della scena, tramite override di uscite ed eventi. I file `.c` delle scene non vengono toccati.
- **Forzieri** (K): clicca un punto vuoto, scegli un oggetto (con la sua icona) o una quantità di monete, e **Aggiungi forziere**. Clicca un forziere per cambiarne il contenuto o rimuoverlo.
  - Una sola azione scrive tutto ciò che serve a un forziere: il marcatore, il codice di collisione della cella, un evento `SEARCH(SEARCH_CHEST)` nella tabella degli eventi della scena (come override, così i file `.c` delle scene restano intatti) e un nuovo flag "aperto" preso dall'intervallo libero dei forzieri.
  - Il codice è uno che nessuna tabella degli eventi delle scene della mappa usa, e che nessuna mappa che condivide quelle tabelle ha nella sua collisione, così nient'altro diventa ispezionabile. Al massimo 10 forzieri e pietre per mappa.
  - Un forziere è una riga `treasure_spot` nel `map.s` della mappa, nella parte del file dell'edizione inglese.
- **Forzieri e Psynergy Stone:** trascina per spostarli. La riga del marcatore e i codici di collisione di entrambe le celle si aggiornano insieme, e i salvataggi che violano la regola marcatore/collisione vengono rifiutati.
- **Tabelle delle scene:** per ogni scena che usa la mappa, scegli una tabella.
  - Ingressi e PNG appaiono sulla mappa; trascinali con lo strumento Sposta persone (P).
  - Le uscite si modificano come elenco (tipo, scena di destinazione, ingresso, flag), con un controllo che l'ingresso di destinazione esista.
- **Collegamenti:** un luogo qualsiasi al centro, con ogni luogo che porta lì a sinistra e ogni posto verso cui porta a destra (porta, porta con script o evento di scena, e il punto di arrivo). Clicca un luogo per spostarti lì; **Apri** salta alla porta nell'editor.
- **Controlla:** esamina ogni mappa alla ricerca di problemi che le tue modifiche causerebbero nel gioco e li descrive a parole semplici, ciascuno con una soluzione e un pulsante **Mostra** che apre il punto:
  - porte che non portano da nessuna parte, o a un punto di arrivo che non esiste;
  - forzieri che non si possono aprire, non hanno nulla definito, si riempiono di nuovo a causa di un flag temporaneo, o condividono un flag "aperto";
  - più di 10 forzieri e pietre in una mappa; celle che usano blocchi mancanti o ritirati;
  - modifiche alle tabelle delle scene che non corrispondono più al sorgente del gioco (dopo un aggiornamento di alchemy).
  - Il gioco originale ha stranezze sue (115 oggi, per esempio 83 porte rimaste inutilizzate). Ogni problema viene cercato anche nel gioco non modificato, e quelli trovati lì sono nascosti a meno che tu non li chieda.
  - **Compila** esegue prima il controllo e chiede conferma prima di compilare con dei problemi.
- **Mappa del mondo** (in cima all'elenco dei luoghi): l'intero mondo esterno, caricato mentre scorri, con le icone di città e dungeon etichettate con la loro destinazione.
  - Sovrapposizioni: calpestabilità (terreno bloccato in rosso) e regioni degli incontri, ciascuna chiamata con il nome delle città che contiene ("Regione 1 (Vale, Lunpa…)").
  - **Terreno** / **Sovrapposizione**: dipingi blocchi (⌥-clic ne raccoglie uno; i blocchi usati di recente restano a portata di mano). **Regioni**: dipingi le regioni degli incontri. Le modifiche si salvano mentre dipingi; Annulla toglie l'ultima pennellata e Ripeti la rimette. Le celle vengono scritte in `map/world/blocks.tsv`, mantenendo gli altri campi di ogni parola.
  - **Città**: trascina un'icona per spostarla. I suoi punti di arrivo (dove compari uscendo dalla città) si spostano con lei, in ogni fase della storia che ha l'icona lì. Clicca un'icona o un punto di passaggio blu per cambiare dove porta.
  - Il nord innevato è disegnato con un suo set grafico. La mappa della schermata di pausa è un'immagine separata e non segue le modifiche.
- **Esporta mod…:** salva la tua mod come piccola patch `.bps`, più un readme per i giocatori, in `~/Documents/GSMapEditor/Exports/`.
  - La patch va dal gioco non modificato alla tua build. Il gioco non modificato viene compilato una volta dal commit da cui parte la tua mod: in una cartella separata tramite `git archive`, così il tuo checkout resta intatto. Viene verificato con il `rom.sha1` di alchemy, quindi è uguale alla cartuccia originale, e la patch si applica al dump di chiunque.
  - Le patch sono BPS (Rom Patcher JS, Floating IPS, soft-patching negli emulatori). I dati spostati diventano copie invece di byte nuovi. Ogni patch viene applicata una volta dopo essere stata scritta, per verificare che riproduca esattamente la tua build.
  - L'esportazione esegue prima Controlla. Condividi le tue modifiche, mai il gioco.
- **Applica patch…:** applica la patch `.bps`, `.ips` o `.ups` di una mod e salva il gioco in `~/Documents/GSMapEditor/Patched/`, con **Gioca in mGBA** e **Mostra nel Finder**.
  - Applica la patch al gioco non modificato che questo Mac ha compilato dai sorgenti (nessuna ROM necessaria) o al tuo file ROM. Il tuo file viene riconosciuto grazie al `rom.sha1` di alchemy ("Golden Sun (English)"), con un avviso quando non è un gioco non modificato.
  - BPS e UPS rifiutano il gioco sbagliato. IPS non può verificarlo, e il patcher lo dice.
  - Esporta può anche scrivere un `.ips` per i patcher più vecchi. È più grande, perché IPS non può registrare i dati spostati (4,2 MB contro 383 KB per la mod della stanza di debug), e viene verificato allo stesso modo.
- **▶ Gioca:** un solo pulsante: salva ciò che non è salvato, esegue Controlla, compila e apre il tuo gioco in mGBA, iniziando una nuova partita nel luogo che stai modificando (dalla pagina della mappa del mondo, sulla mappa del mondo). La partenza viene scritta in una copia usa e getta del gioco; ciò che esporti non ne ha traccia. Se la build fallisce ricevi una spiegazione semplice, con i dettagli tecnici ripiegati e un pulsante Copia per le segnalazioni di bug. Compila da solo si trova sotto Avanzate.
- **Annulla / Ripeti:** una sola coppia di pulsanti per tutto. Annulla toglie prima le pennellate non salvate (la pila della pagina), poi le azioni salvate dalla più recente, qualunque strumento e luogo le abbia fatte; un salvataggio trasforma la pila della pagina in un'unica azione salvata. Ogni scrittura passa per `writing(label, where)` di `server.py`, una transazione di `gsmap/fsio.py` che conserva il vecchio contenuto dei file come voce di cronologia etichettata con cosa e dove ("aggiunta di una persona", mappa `051`). `undo_last` rimette una voce e conserva ciò che ha sostituito sotto `history/redo`; `redo_last` fa il contrario; una nuova azione svuota `history/redo`. Entrambi passano per il journal, così un crash a metà viene completato all'avvio successivo. Vengono conservate le ultime 30 di ciascuno, sotto `history/` nella cartella di supporto.
- **Dove possono stare le persone** (`gsmap/walk.py`): le regole di movimento del gioco, dal codice del campo di alchemy: passi di 8 pixel che richiedono cinque sonde libere, al massimo 8 pixel in salita e 12 in discesa (`terrain.c`, `MapGrid_CheckCollision`), altezze ricavate dalla forma di ogni cella tramite le sedici funzioni del terreno e `terrain_tables.c`, sporgenze, punti di arrampicata e fossi, e parlare entro 32 pixel e 48 in su o in giù. Gli scivoloni vengono seguiti come fa `Imil_RunIceSlide`, per ogni attivatore a passo il cui script fa scivolare. Il gruppo viene seguito su un reticolo di 8 pixel da ogni punto di arrivo della scena; una persona blocca entro 12 pixel (due raggi di 8, meno 2 ciascuno). `POST /api/map/<n>/walk` colora ogni casella; `/walk/check` restituisce i problemi di un punto, il punto più vicino che non ne ha, e le modifiche di forma che livellano un percorso fino a lì (forme piatte che la mappa ha già). Le modifiche non salvate di forma e calpestabilità vengono inviate insieme. La Psicoenergia e gli eventi della storia non vengono seguiti, e le persone diverse da quella controllata non sono ostacoli. Verificato sul gioco: circa il 92% delle persone piazzate da Camelot è raggiungibile per parlarci secondo queste regole, mentre il resto si trova in stanze di cutscene e in posti aperti con la Psicoenergia.
- **Ripristina luogo…:** rimette un luogo com'è nel gioco originale (Annulla riporta la tua versione). Le tabelle delle scene condivise da altri luoghi vengono lasciate stare, e lo dice.
- **Il salvataggio è tutto o niente:** i file di un'azione arrivano insieme o per niente, ogni file viene sostituito in un solo passo, e se l'editor si chiude a metà completa l'annullamento all'avvio successivo.
- **Nomi:** i luoghi sono elencati con i loro nomi nel gioco ("Vale · Vale Home").
- **Pennelli di calpestabilità:** con nome e colore (Pavimento, Muro, Sporgenza, Parete scalabile / scala, Varco da saltare, Terreno dannoso, punti da esaminare, …).
- **Passaggio del mouse:** dice cosa fa una cella ("Uscita → Vale", "Forziere: Herb", "Con script (probabilmente una porta per …)").
- **PNG:** disegnati con i loro sprite, elencati per nome.
- **Tabelle delle scene:** nomi comprensibili ("Punti di arrivo: normale", "Persone: After Kalay").
- **Casella Avanzate:** fa ricomparire i codici grezzi.
- **Link:** `?map=003&tool=points&kind=placements` apre direttamente un luogo.
- **Nessuna grafica o testo incluso:** i nomi di oggetti, luoghi, personaggi, sprite e flag, le icone degli oggetti e le anteprime degli sprite vengono tutti letti durante l'esecuzione dal checkout di alchemy del giocatore. `gsmap/data` contiene solo le scoperte dell'editor stesso: fotogrammi di anteprima, flag liberi per i forzieri e cosa fa ogni codice di calpestabilità.

**Come le modifiche alle scene arrivano al gioco:** tramite un solo hook, senza riscrivere i file delle scene di alchemy. Vedi `docs/SPEC.md` e `games/tbs/src/mod/README.md` di alchemy.
- L'editor salva le copie modificate delle tabelle in `games/tbs/src/mod/overrides.json` di alchemy e ne genera `mod.c`.
- `MOD_SCENE_LOADED` in `Scene_LoadOverlay` (`system/main_routine.c`), che l'editor aggiunge a un checkout pulito la prima volta che scrive una modifica a una scena, sostituisce un wrapper che esegue comunque la logica propria di ogni scena per scegliere le tabelle.
- Senza override, GSMOD è spento e tutte e sei le edizioni si compilano ancora identiche byte per byte.

Le fasi successive sono nel piano di sviluppo in [`SPEC.md`](SPEC.md).

### Stare al passo con alchemy

Tutto ciò che l'editor sa della struttura di alchemy si trova in `gsmap/layout.py`. Il commit con cui è testato è `ALCHEMY_PIN` in `gsmap/setup.py`. Quando lo cambi, aggiorna anche la riga della versione nel README, altrimenti il test di sicurezza fallisce. Per provare una nuova versione:

1. `python3 -m gsmap.preflight path/to/alchemy` dice a parole semplici cosa non corrisponde più. Viene eseguito anche a ogni avvio, e si ferma lì invece di disegnare mappe con le tile sbagliate.
2. Compilala, poi `python3 tools/snapshot.py path/to/alchemy new.json` e `python3 tools/snapshot.py --compare old.json new.json` mostrano ogni differenza in ciò che l'editor legge. Le due versioni compilano lo stesso gioco, quindi i risultati dovrebbero cambiare solo dove te lo aspetti.
3. Esegui i test qui sotto.

Spostare a mano un checkout esistente su un nuovo alchemy è normale git: fai il merge o il checkout del nuovo commit, poi `git submodule update --init --recursive alchemy-gcc`. Da `alchemy-gcc` 3a12774 (alchemy 2026-11-08), agbcc è composto da file normali invece che da un submodule annidato, e in un checkout precedente l'aggiornamento si ferma con "untracked working tree files would be overwritten". Dentro `alchemy-gcc`, esegui `git submodule deinit -f agbcc`, elimina la cartella `agbcc` e `.git/modules/agbcc` sotto la cartella git di alchemy-gcc, poi aggiorna di nuovo. Elimina `out/*/deps.mk` e `out/*/objects.mk` prima della prima build. Il 2026-11-10 i commit più recenti di alchemy-gcc sono stati riformulati e rifissati, quindi un `git fetch` in un checkout più vecchio può finire con "Errors during submodule fetch: alchemy-gcc" ("not our ref 8b1b6b4…"); il fetch principale ha comunque funzionato, e `git submodule update` poi fa il checkout del nuovo commit fissato. Il pulsante **Scarica** della configurazione crea sempre un clone nuovo, così i giocatori non incontrano questo problema.

Le modifiche salvate alle scene portano un'impronta della tabella per cui sono state fatte. Una tabella rinominata a monte la segue. Una modifica a una tabella il cui contenuto originale è cambiato viene conservata ma lasciata fuori dal gioco, e Controlla la segnala.

### Test

- `python3 tests/safety.py`: ciò che non deve mai andare storto: errori e crash non lasciano file salvati a metà, annulla e ripeti percorrono le azioni salvate in ordine e una nuova modifica svuota il ripeti, i forzieri restano nelle loro stanze, i valori errati e le patch ostili vengono rifiutati, le tabelle rinominate o modificate vengono gestite, una struttura sconosciuta viene segnalata invece di essere indovinata.
- `python3 tests/placement.py`: le regole di movimento confrontate con il gioco: le persone piazzate in otto città sono raggiungibili per parlarci e le loro vie d'uscita sono raggiungibili, e a Imil il ghiaccio, un punto innevato irraggiungibile (con la sua correzione di livellamento), un vicolo stretto, una soglia e un muro producono ciascuno un avviso.
- `python3 tests/edits.py`: salva modifiche a blocchi, calpestabilità e altezza su una copia di mappe reali e verifica che vengano rilette correttamente, senza che altro cambi.
- `python3 tests/i18n.py`: ogni messaggio che il codice mostra è tradotto in ogni lingua, e ogni traduzione mantiene i suoi `{placeholders}`, tag HTML e tasti (⌘ ⇧ ⌥ ▶).
- `python3 tests/roundtrip.py`: carica e risalva ogni griglia di mappa, tabella di immagini delle celle e di forme, ed elenco di forzieri (727 file con la mod della stanza di debug, 721 su un checkout pulito). Tutti devono risultare identici byte per byte. Questo garantisce che salvare una mappa cambi solo ciò che hai modificato.

### Lingue

Le parole dell'editor sono tradotte; il gioco resta in inglese. Scrivi ogni messaggio in inglese, racchiuso in modo che possa essere trovato: `tr("…")` in Python (`gsmap/i18n.py`), `T('…')` nelle pagine (`static/i18n.js`). Il primo argomento è sempre una semplice stringa; le parti che cambiano sono segnaposto `{name}` (`tr("Map {n} has {k} chests", n=n, k=k)`), e i plurali sono due modelli completi. Il testo nelle pagine HTML, e i testi o titoli interi che gli script inseriscono nella pagina, vengono tradotti così come appaiono quando corrispondono esattamente a un messaggio; tutto ciò che sta dentro un elemento `data-notr` (i nomi e i dialoghi del gioco) viene lasciato com'è. Non tradurre ciò che viene scritto nei file (mod.c, en.po, il readme esportato) o confrontato dal codice.

`python3 tools/extract_strings.py` raccoglie ogni messaggio in `static/i18n/<lang>.json` (inglese → traduzione), aggiungendo quelli nuovi vuoti ed eliminando quelli che il codice non ha più; `--check` fallisce se qualcuno non è allineato o non è tradotto. La lingua scelta nel menu 🌐 viene conservata nelle impostazioni dell'editor (`language`); finché non se ne sceglie una, decidono le lingue preferite del browser. I messaggi di ogni richiesta la usano (`i18n.begin` in entrambi i server), e le pagine ricevono il loro catalogo da `/i18n-strings.js`. Per aggiungere una lingua, aggiungila a `LANGS` in `gsmap/i18n.py`, esegui l'estrattore e compila il nuovo file.

Anche il README e questa documentazione sono tradotti: `README.<lang>.md` accanto al README, e `docs/<lang>/` per `DEVELOPING.md`, `PRODUCT.md`, `SPEC.md` e `research/`. `docs/upstream-issues.md` (per il tracker in inglese di alchemy), `docs/releases/` e `THIRD_PARTY_NOTICES.md` restano in inglese. I file inglesi sono gli originali: cambia prima quelli, poi le traduzioni, ed esegui `python3 tools/doc_translations.py --stamp` per registrare quale testo inglese segue ora ogni traduzione. Senza `--stamp` controlla link, titoli, indirizzi web e frammenti `code` di ogni traduzione, ed elenca quelle il cui inglese è cambiato da allora. L'estrattore raccoglie anche i nomi e le descrizioni dei pennelli di calpestabilità, in `gsmap/data/collision.json`.

## Documentazione

- [`SPEC.md`](SPEC.md): la specifica dell'editor, le invarianti e il piano di sviluppo a fasi.
- [`research/`](research/): prove con riferimenti file:riga.
  - `rendering.md`: segnaposto, set di tile, finestre, fusione, animazione.
  - `local-connections.md`: scene, uscite, marcatori, PNG, nuove mappe.
  - `overworld.md`: la mappa del mondo.
