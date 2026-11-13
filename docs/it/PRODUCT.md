<!-- translated from docs/PRODUCT.md @ 34e70fd313ab -->
# gs-mapedit per i giocatori: piano di prodotto

*Questa è una traduzione del file inglese [PRODUCT.md](../PRODUCT.md); se i due differiscono, vale quello inglese.*

**Pubblico:** fan e modder senza preparazione tecnica, cioè niente terminale, esadecimale, C, git o sistemi di build.
**Distribuzione:** un'app desktop impacchettata con un installer.
*(Deciso dal proprietario del progetto, 2026-10-20.)*

Il livello del motore che esiste oggi resta la base. Questo comprende i formati dei file, i salvataggi identici byte per byte, le invarianti, l'hook delle tabelle delle scene e la build. Questo piano riguarda il livello che vedono i giocatori.

## Principi

1. **Nomi, immagini e luoghi, mai codici.** Ogni valore che un giocatore vede ha un nome, un'anteprima o viene mostrato su una mappa. I numeri grezzi stanno dietro un interruttore "Avanzate".
2. **Un'intenzione, un'azione.** "Aggiungere un forziere con un Herb" diventa un'unica azione, anche se tocca l'elenco dei marcatori, la collisione, un evento di scena e un nuovo flag.
3. **Impossibile rompere il gioco senza accorgersene.** Le invarianti vengono fatte rispettare come oggi, e spiegate in linguaggio semplice: "Questa porta non porta ancora da nessuna parte." (✅ il pulsante Controlla, eseguito anche prima di ogni Compila.)
4. **Sempre a un clic dal gioco.** Modifica, poi Gioca. La build è invisibile a meno che non fallisca, e gli errori si leggono come indicazioni, non come output del compilatore.
5. **Nessuna distribuzione di ROM.** Le mod si condividono come file di patch che i giocatori applicano al dump della propria cartuccia.

## Cosa fanno i giocatori (percorsi → schermate)

| Percorso | Schermata / interazione | Parti del motore (esistono?) |
|---|---|---|
| Esplorare i luoghi del gioco | **Vista del mondo:** il mondo esterno più ogni città/dungeon, con i collegamenti disegnati | Renderer ✅, vista Collegamenti ✅ (luogo per luogo), Atlante ✅ (tutti i luoghi insieme), Vai lì ✅ (seguire una porta), mondo esterno ✅ |
| Ridipingere parte di una mappa | **Dipingi:** palette di tile per tema, pennelli, riempimento, copia/incolla di regioni | Pittura di blocchi ✅; Riempi ✅; copia e incolla (Timbro) ✅ |
| Cambiare dove si può camminare | **Pennello di calpestabilità:** calpestabile / bloccato / sporgenza / scala / acqua, mostrato come una sovrapposizione pulita | Pittura della collisione ✅; **codici con nome ❌ (ricerca)** |
| Spostare una porta / cambiare dove porta | Clicca una porta, poi scegli la destinazione cliccando sulla mappa di arrivo | ✅ Strumento Porte |
| Aggiungere/spostare un forziere o una Psynergy Stone | Piazza un forziere; scegli il contenuto (selettore di oggetti con icone, monete, mimic) | ✅ Strumento Forziere (oggetti, monete); le pietre si possono solo spostare |
| Piazzare/spostare persone | Trascina i PNG con anteprime degli sprite; guarda e modifica ciò che dicono | Posizioni ✅; anteprime degli sprite ✅; ciò che dicono al passaggio del mouse ✅; aggiunta e rimozione ✅ |
| Provarlo | **Gioca:** build più apertura dell'emulatore su quella mappa | Gioca con un clic ✅ (salva, controlla, compila, apre nel luogo che si sta modificando) |
| Condividerlo | **Esporta mod:** un file di patch più una descrizione | ✅ BPS dalla build originale alla build della mod |
| Annullare errori / ricominciare | Pannello della cronologia; "ripristina questa mappa" | Annulla e Ripeti ✅ (ultime 30 azioni salvate, conservate tra una sessione e l'altra); Ripristina luogo ✅ |

## Livello dei nomi (serve ricerca, per lo più consultazioni)

- **Codici di collisione:** muro, pavimento, sporgenze, punti di arrampicata, punti di ricerca, pericoli, uscite, forzieri. Fonti: `step.c`, `events.c`, i documenti di ricerca.
- **Scene:** i nomi di `scenes.s` più i nomi delle aree (i nomi dei luoghi del gioco stesso) per la visualizzazione.
- **Oggetti:** i nomi di `include/item_ids.h`, più le icone degli oggetti dalla grafica del gioco.
- **Sprite:** id dello sprite → nome e un'immagine di anteprima dalla grafica degli oggetti.
- **Dialoghi:** id del messaggio → testo da `text/en.po` (10.724 voci).
- **Flag:** i nomi di `include/flags.h`, più un allocatore di nuovi flag per i forzieri (≥ 0xe00, non usati).

## Architettura del pacchetto (raccomandazione)

- **Guscio:** pywebview (il WKWebView nativo) in un bundle PyInstaller: un unico `.app` da 30 MB che contiene Python, il server e le pagine. *(Cambiato da Tauri, 2026-10-22: il backend è già in Python, e Tauri aggiungerebbe una toolchain Rust senza alcun vantaggio per ora. Tauri resta un'opzione se il backend passa a Rust.)*
- **Backend:** il server Python di oggi, nello stesso processo.
- **Sorgente del gioco:** l'app scarica alchemy a un commit fissato che abbiamo verificato. I giocatori non vedono mai git. Gli aggiornamenti sono espliciti: "Nuova versione di alchemy disponibile; testata ✓".
- **Toolchain:** la parte più difficile.
  - alchemy ha bisogno dei suoi compilatori fissati (compilati dai sorgenti), delle binutils e dei suoi strumenti C (libpng).
  - Piano: compilarli per ogni piattaforma nella CI e distribuirli come binari precompilati. I compilatori sono GPL; ne pubblichiamo i sorgenti.
  - Piattaforme: prima macOS (Intel + Apple Silicon), poi Windows (alchemy supporta ufficialmente Windows solo tramite WSL, quindi un porting nativo degli strumenti è il rischio), poi Linux.
- **Patch:**
  - Poiché la build originale è identica byte per byte alla ROM commerciale, una patch = diff(build originale, build della mod), calcolata in locale senza mai toccare una ROM commerciale.
  - I giocatori la applicano al proprio dump con qualsiasi patcher BPS, o con la nostra app.
- **Prova di gioco:** includere mGBA (MPL-2.0) o rilevarne uno installato; avviare sulla mappa modificata se un punto d'ingresso di debug lo permette.

## Traguardi

1. **Interfaccia per i giocatori nell'app attuale.** Tutto ciò che è qui passa direttamente al guscio desktop. Comprende:
   - il livello dei nomi;
   - i pennelli di calpestabilità;
   - le porte collegate con un clic;
   - i selettori di oggetti/sprite;
   - un'azione per aggiungere forzieri;
   - la validazione in linguaggio semplice;
   - la vista del mondo/dei collegamenti.
2. **Prova di impacchettamento (macOS):** ✅ bundle dell'app e configurazione al primo avvio (scarica alchemy, compila una volta). ✅ toolchain inclusa (senza Homebrew). Restano: firma/notarizzazione (serve un Developer ID), build nativa per Apple Silicon, un test su un Mac davvero nuovo. Successo = un Mac nuovo passa da zero a "Gioca" senza un terminale.
3. **Esportazione delle patch** ✅ (BPS, verificata con rom.sha1). Applicare le patch degli altri ✅ (Applica patch).
4. **Modifica del mondo esterno** ✅ (fasi 4–5 di SPEC.md): terreno, sovrapposizione, regioni e le loro battaglie, icone delle città (spostate, collegate, aggiunte), punti di passaggio.
5. **Pacchetti per Windows e Linux.** Windows funziona tramite WSL da uno script di installazione (primo test); Linux gira dai sorgenti.

## Rischi

- **Portabilità della toolchain (Windows).** La build di alchemy presuppone una shell Unix. Questo potrebbe richiedere un'integrazione con WSL o un porting nativo dei suoi piccoli strumenti C.
- **Cambiamenti a monte.** alchemy cambia ogni giorno. Fissare un commit, e subordinare gli aggiornamenti ai nostri controlli di andata e ritorno e di rendering completo più una build di prova.
- **Portata del "significato".** Alcuni codici di collisione e tipi di evento sono ancora sconosciuti perfino ad alchemy. Gli sconosciuti restano visibili ma etichettati "sconosciuto (avanzato)".
- **Posizione legale:** non distribuiamo mai ROM, risorse estratte o giochi compilati. I giocatori non forniscono nulla (The Broken Seal si compila dai sorgenti), e l'app scarica alchemy da sola.
