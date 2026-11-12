<!-- translated from README.md @ b21e30165e76 -->
# GS Map Editor

[English](README.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · **Italiano** · [日本語](README.ja.md)

_Questa è una traduzione del [README.md](README.md) in inglese; se le due versioni sono diverse, quella inglese è la più aggiornata._

Crea la tua versione di **Golden Sun: The Broken Seal** senza scrivere codice. Ridipingi le città, nascondi forzieri, scrivi nuovi dialoghi, aggiungi persone e porte, rimodella la mappa del mondo, poi premi **▶ Gioca** e vai in giro nella tua modifica. Quando ne sei soddisfatto, esporta una piccola patch da condividere.

L'editor lavora su [alchemy](https://github.com/PascalPixel/alchemy), un progetto che ricostruisce il gioco a partire da file sorgente leggibili. Compila il tuo gioco da quel sorgente sul tuo computer, quindi non ti serve una ROM per creare una mod.

> **Anteprima: cerchiamo tester.** L'editor copre l'edizione inglese di The Broken Seal, su macOS e, come primo test, su Windows. È stato provato soprattutto su un solo Mac Intel, e la versione Windows non è mai stata eseguita su un vero PC Windows, quindi ogni segnalazione aiuta, anche "ha funzionato": [scaricalo](https://github.com/TRosenvall/GS-Map-Editor/releases), provalo e [raccontaci com'è andata](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md). Tieni un backup di ogni mod a cui tieni.

**Versione di alchemy:** questo editor è testato con il commit di alchemy [`0c937e7df0`](https://github.com/PascalPixel/alchemy/commit/0c937e7df0b71b23760fbd19d048e99dd3969490) (2026-11-11). La configurazione scarica esattamente quel commit. Alchemy cambia in fretta, quindi una copia più recente potrebbe non funzionare finché l'editor non si mette in pari.

## Indice

- [Per iniziare](#per-iniziare)
- [La tua prima mod in due minuti](#la-tua-prima-mod-in-due-minuti)
- [L'editor in breve](#leditor-in-breve)
- [Salvare e annullare](#salvare-e-annullare)
- [Guardarsi intorno](#guardarsi-intorno)
- [Dipingi: com'è il terreno](#dipingi-comè-il-terreno)
- [Calpestabilità: dove si può camminare](#calpestabilità-dove-si-può-camminare)
- [Altezza: quanto è alto il terreno](#altezza-quanto-è-alto-il-terreno)
- [Forzieri](#forzieri)
- [Eventi: persone, cartelli e messaggi](#eventi-persone-cartelli-e-messaggi)
- [Porte](#porte)
- [Sposta persone](#sposta-persone)
- [Timbro: copia e incolla](#timbro-copia-e-incolla)
- [Importare le tue immagini](#importare-le-tue-immagini)
- [Tabelle della storia e delle scene](#tabelle-della-storia-e-delle-scene)
- [Collegamenti](#collegamenti)
- [La mappa del mondo](#la-mappa-del-mondo)
- [Controlla: trovare i problemi](#controlla-trovare-i-problemi)
- [Giocare al tuo gioco](#giocare-al-tuo-gioco)
- [Condividere la tua mod](#condividere-la-tua-mod)
- [Giocare alla mod di qualcun altro](#giocare-alla-mod-di-qualcun-altro)
- [Dove si trova il tuo lavoro](#dove-si-trova-il-tuo-lavoro)
- [Scorciatoie da tastiera](#scorciatoie-da-tastiera)
- [Cosa non sa ancora fare](#cosa-non-sa-ancora-fare)
- [Risoluzione dei problemi](#risoluzione-dei-problemi)
- [Segnalare problemi](#segnalare-problemi)
- [Note legali](#note-legali)

## Per iniziare

### Cosa ti serve

- Un Mac con macOS 11 o successivo, oppure un PC con Windows 10 o 11.
- Circa 3 GB di spazio libero per il sorgente del gioco e la sua compilazione.
- [mGBA](https://mgba.io/downloads.html), un emulatore Game Boy Advance gratuito, per giocare al tuo gioco (su Windows, il suo programma di installazione per Windows).
- Una connessione a internet per la prima configurazione.

### Scaricare l'app (Mac)

Scarica il `.dmg` più recente da [Releases](https://github.com/TRosenvall/GS-Map-Editor/releases):

- **AppleSilicon** per i Mac con chip M1, M2, M3, M4 o successivi;
- **Mac-Intel** per i Mac Intel.

Non sai quale hai? Menu Apple → **Informazioni su questo Mac**: "Chip: Apple M…" vuol dire Apple Silicon.

Apri il `.dmg` e trascina **GS Map Editor** in **Applicazioni**.

### Aprirla la prima volta (Mac)

L'app non è ancora firmata con un certificato da sviluppatore Apple, quindi la prima volta macOS mostra un avviso:

1. Aprila da Applicazioni. macOS dice che non può verificare l'app: premi **Fine** (o **Annulla**).
2. Apri **Impostazioni di Sistema → Privacy e sicurezza**, scorri in basso e premi **Apri comunque** accanto a GS Map Editor. Conferma con la tua password.

Su macOS 14 e precedenti puoi invece fare clic destro sull'app, scegliere **Apri** e poi di nuovo **Apri**. Dopo la prima volta si apre normalmente.

Se preferisci compilare l'app da te, segui [App desktop](docs/it/DEVELOPING.md#app-desktop-macos) nelle note per sviluppatori. Se ti trovi a tuo agio con il terminale e hai già una copia di alchemy compilata, puoi saltare l'app ed eseguire `python3 server.py --root /path/to/alchemy`, poi aprire http://127.0.0.1:8765/.

### Scaricare l'editor (Windows, primo test)

L'editor funziona dentro WSL, il Linux integrato in Windows, perché è l'unico modo per compilare il sorgente del gioco su Windows. Si apre nel tuo browser web.

1. Scarica `Install-GS-Map-Editor.cmd` da [Releases](https://github.com/TRosenvall/GS-Map-Editor/releases). Se il browser dice che non viene scaricato comunemente, scegli **Mantieni**.
2. Fai doppio clic sul file. Windows dice di aver protetto il PC perché il programma di installazione non è ancora firmato: premi **Ulteriori informazioni**, poi **Esegui comunque**.
3. La prima volta attiva WSL e installa Ubuntu. Windows chiede i permessi di amministratore e potrebbe chiederti di riavviare; in quel caso riavvia e fai di nuovo doppio clic sul programma di installazione.
4. Quando Ubuntu lo chiede, scegli un nome utente e una password. Mentre scrivi la password non compare nulla; è normale. Il passaggio successivo te la chiede.
5. Il programma di installazione configura l'editor dentro Ubuntu e aggiunge **GS Map Editor** al menu Start e al desktop.

Apri **GS Map Editor**. Compare una piccola finestra; tienila aperta mentre usi l'editor, perché chiuderla ferma l'editor. L'editor si apre nel tuo browser. Eseguire di nuovo il programma di installazione aggiorna l'editor alla versione con cui è stato distribuito.

Su Windows le scorciatoie da tastiera usano Ctrl dove questa guida dice ⌘, e Alt dove dice ⌥. Il tuo lavoro si trova dentro Ubuntu, in `GSMapEditor` nella tua cartella home di Ubuntu; Esplora file la mostra sotto **Linux → Ubuntu → home**.

### Configurazione iniziale

La prima volta l'editor si apre su una lista di controllo. Ci vogliono circa 15 minuti, passati soprattutto ad aspettare. Premi il pulsante di ogni passaggio e l'editor fa il resto:

1. **Gli strumenti per sviluppatori di Apple** (solo Mac): apre il programma di installazione di Apple.
2. **Gli strumenti per compilare il gioco:** già inclusi nell'app su Mac, e messi a posto dal programma di installazione su Windows.
3. **Il codice sorgente del gioco:** scarica alchemy in `~/Documents/GSMapEditor/` (su Windows, `GSMapEditor` nella tua cartella home di Ubuntu). Se ne hai già una copia, scegli **Ne ho già una copia…** (su Windows, scrivi il suo percorso).
4. **Preparazione della compilazione:** configura i compilatori del gioco, una volta sola.
5. **Una prima compilazione del gioco:** compila il gioco una volta.

Poi premi **Apri l'editor**. Da quel momento l'app si apre direttamente nell'editor.

## La tua prima mod in due minuti

1. Scegli un luogo dalla lista a sinistra. Scrivi nella casella **Trova un luogo** per cercare.
2. Premi **Forziere** nella barra in alto, poi clicca un pezzo di terreno libero.
3. Scrivi il nome di un oggetto, per esempio `Herb`, e premi **Aggiungi forziere**.
4. Premi **▶ Gioca**. Il tuo gioco si apre in mGBA, nel luogo che stavi modificando, pochi secondi dopo l'avvio del gioco.
5. Avvicinati al forziere e aprilo.

## L'editor in breve

| Zona | Cosa c'è |
|---|---|
| **Sinistra** | La lista dei luoghi. La mappa del mondo è in cima. |
| **Barra in alto** | Zoom, livelli, sovrapposizioni, strumenti e pulsanti per salvare, controllare e giocare. |
| **Centro** | La mappa. |
| **Destra** | Il pannello dello strumento che stai usando. |
| **Riga in basso** | Messaggi di stato. Mentre passi sopra con il mouse, dice cosa fa il punto sotto il cursore, per esempio "Forziere: Herb" o dove porta un'uscita. |

Spunta **Avanzate** nella barra in alto per mostrare numeri e codici grezzi e un pulsante **Compila** separato. Per le modifiche normali non ti servirà.

### Lingue

L'editor parla inglese, spagnolo (Español), tedesco (Deutsch), francese (Français), italiano e giapponese (日本語). Si avvia nella lingua del tuo computer, se la conosce. Puoi cambiarla con il menu 🌐, in alto a destra nella prima schermata di configurazione e in fondo alla barra in alto. Cambiano solo le parole dell'editor: il gioco che stai modificando è l'edizione inglese, quindi i nomi dei luoghi, le persone, gli oggetti e i dialoghi che scrivi restano in inglese.

Anche questa guida è tradotta: vedi i link in cima. Le traduzioni dell'editor e di questa guida sono state fatte con l'aiuto dell'IA e non sono ancora state tutte controllate da madrelingua. Dove una guida tradotta è diversa da questa, la guida inglese è quella aggiornata. Se qualcosa suona strano, per favore [segnalalo](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md) indicando la formulazione che ti aspetteresti.

## Salvare e annullare

Alcune modifiche aspettano che tu salvi, altre si salvano subito:

| Aspettano **Salva** (o ⌘S) | Si salvano subito |
|---|---|
| Dipingi, Calpestabilità, Altezza | Aggiungere, modificare o rimuovere un forziere |
| Incollature con il Timbro | Eventi e porte |
| Trascinare forzieri, pietre e persone | Pittura della mappa del mondo e spostamenti delle città |

L'editor salva anche da solo prima che tu cambi luogo, vada alla mappa del mondo o prema Gioca, quindi andare avanti non ti fa perdere il lavoro. Se un salvataggio viene rifiutato, resti dove sei e la riga in basso dice perché.

Ci sono tre modi per tornare indietro:

- **Annulla** (⌘Z) toglie la tua ultima modifica, qualunque fosse: prima la pittura non ancora salvata, poi le azioni salvate, dalla più recente, da qualsiasi strumento e in qualsiasi luogo. Aggiungere una persona, un forziere, una porta, un evento, una pennellata sulla mappa del mondo: tutto. Il suggerimento del pulsante dice cosa annullerà e dove, e l'editor apre quel luogo per mostrartelo. Le ultime 30 azioni salvate vengono conservate, anche dopo aver chiuso l'editor.
- **Ripeti** (⇧⌘Z) rimette ciò che Annulla ha tolto, finché non fai una nuova modifica.
- **Ripristina luogo…** riporta le mappe di un luogo, le immagini importate e le sue persone, porte ed eventi come sono nel gioco originale. Se cambi idea, **Annulla** ti restituisce la tua versione. Se un luogo condivide la mappa con altri, anche quelli tornano all'originale, e l'editor ti avvisa prima. Le persone e gli eventi condivisi con altri luoghi restano come sono, a meno che tu non dica diversamente: l'editor te lo chiede.
- **Ripristina mappa del mondo…**, nella pagina della mappa del mondo, fa lo stesso per la mappa del mondo.

Il testo che hai scritto resta nel file di testo del gioco finché un evento ne usa ancora una parte. Viene rimosso solo quando nessuna delle tue righe è più usata. Annullare un'azione salvata mentre hai modifiche non salvate elimina anche quelle, e prima te lo chiede.

Ogni salvataggio è tutto o niente. Se l'editor si ferma a metà, la volta successiva che si avvia finisce di annullare il salvataggio rimasto a metà. Se un file non si può scrivere, per esempio perché è bloccato nel Finder, il salvataggio viene rifiutato e il resto viene annullato.

## Guardarsi intorno

Premi **Visualizza** (V) per guardare senza cambiare nulla.

- **Zoom:** da 1× a 4×.
- **Livelli:** ogni luogo ne ha fino a tre, chiamati **Terreno**, **Centrale** e **Superiore**. Puoi nascondere ciascuno. Spunta **Avanzate** per avere dei cursori che li sfumano.
- **Sovrapposizioni:** spunta **Calpestabilità**, **Altezza** per vedere l'altezza del terreno, o **Griglia** per vedere le caselle.
- I **forzieri** si vedono sempre sulla mappa. Porte, persone ed eventi si vedono quando usi i loro strumenti.

## Dipingi: com'è il terreno

Premi **Dipingi** (B).

1. Scegli un livello nel menu **su** nella barra in alto.
2. Scegli un blocco dal pannello **Blocchi** a destra, oppure tieni premuto ⌥ e clicca la mappa per prendere il blocco sotto il cursore.
3. Clicca o trascina sulla mappa.
4. Salva.

Ogni luogo ha il suo set di blocchi, quindi il pannello cambia da un luogo all'altro.

## Calpestabilità: dove si può camminare

Premi **Calpestabilità** (C). Dipingere un blocco non cambia dove si può camminare, quindi questo è un passaggio a parte. Scegli un pennello e dipingi.

| Pennello | Cosa fa |
|---|---|
| **Pavimento** | Terreno normale su cui si può camminare. |
| **Muro** | Blocca il passaggio, qualunque sia l'altezza. |
| **Sporgenza (salta giù)** | Tieni premuto Giù contro di esso per un momento e il capofila salta giù. |
| **Parete scalabile / scala** | Tieni premuto Su o Giù contro di esso per un momento per arrampicarti. |
| **Varco da saltare (salto in avanti)** | Spingi contro di esso per un momento e il capofila ci salta sopra, se il lato opposto permette di atterrare. |
| **Terreno con scontri A / B** | Calpestabile. Le battaglie casuali usano la prima o la seconda zona di scontri del luogo. |
| **Terreno dannoso** | Calpestabile, ma ferisce il gruppo dopo un certo numero di passi, se la scena lo attiva. |
| **Ombra per Cloak** | Calpestabile. L'unico terreno dove la Psicoenergia Cloak tiene nascosto il gruppo. |
| **Giara, barile, cassa, tomba, libri, pozzo vuoti** | Cercandoci non si trova nulla. Di solito è anche un muro, grazie alla sua altezza. |

Gli strumenti Forziere, Porte ed Eventi impostano da soli i codici speciali di cui hanno bisogno, quindi non devi dipingerli tu.

## Altezza: quanto è alto il terreno

Premi **Altezza** (H). Il pannello elenca le altezze che questo luogo usa già, per esempio "Piano, 24 px" o "Pendenza o gradino". Scegline una e dipingi.

L'altezza influisce sul camminare oltre che sull'aspetto. Le persone stanno all'altezza del terreno su cui si trovano, e il gioco rifiuta un passo di più di 8 pixel in salita o di 12 pixel in discesa, quindi una grande differenza di altezza fa da muro.

## Forzieri

Premi **Forziere** (K).

- **Aggiungerne uno:** clicca un punto libero, scegli un **Oggetto** (inizia a scriverne il nome) o una quantità di **Monete**, poi premi **Aggiungi forziere**.
- **Modificarne uno:** cliccalo, cambia cosa contiene e conferma.
- **Rimuoverne uno:** cliccalo e premi **Rimuovi forziere**.
- **Spostarne uno:** trascinalo, poi salva. Anche le Psynergy Stone si possono trascinare. Un forziere non può stare su una casella che è già una porta, un cartello o un messaggio al passaggio.

L'editor pensa al resto, compreso il flag che ricorda che un forziere è stato aperto, così il forziere resta vuoto quando torni. Un luogo può contenere al massimo **10 forzieri e pietre**.

## Eventi: persone, cartelli e messaggi

Premi **Eventi** (E). Il pannello elenca a parole tutto ciò che succede in questo luogo: cosa dicono le persone, i pensieri letti con Mind Read, i cartelli, i messaggi al passaggio, le ricerche e le aree di uscita.

La **Fase della storia** in cima è importante. Molti luoghi cambiano man mano che la storia va avanti, e ogni fase ha le sue persone e i suoi eventi. Scegli la fase che vuoi modificare.

### Aggiungere cose

Clicca un punto sulla mappa, poi scegli:

- **Aggiungi un cartello (si legge con A)…** per un cartello o qualcosa da esaminare.
- **Aggiungi un messaggio al passaggio…** per un messaggio che compare quando passi su quel punto. Non si ripete mentre ci resti sopra, quindi non può intrappolare il giocatore, e ricompare se ti sposti e poi torni.
- **Aggiungi una persona qui…** per scegliere chi è, con un'anteprima dell'immagine, e se **Va in giro**. Prima l'editor controlla il punto (vedi sotto).

### Dove possono stare le persone

Non ogni punto che sembra libero è un buon posto per una persona. Spunta **Dove possono stare le persone** in cima, oppure premi semplicemente **Aggiungi una persona qui…**, e la mappa si colora in base a cosa significherebbe una persona in quel punto:

| Colore | Significa |
|---|---|
| Verde | Il gruppo può avvicinarsi e parlarci. |
| Giallo | Il gruppo non può salire su quella casella, ma può parlarci da accanto, come con un negoziante dietro un bancone. |
| Blu | Ghiaccio su cui il gruppo scivola, come a Imil. Qualcuno fermo lì intralcia la scivolata. |
| Arancione | Una porta, un'uscita o un punto di passaggio: qualcuno lì sarebbe d'intralcio. |
| Rosso | Il gruppo non riesce ad avvicinarsi abbastanza camminando per parlarci. |

Viene calcolato con le regole di movimento del gioco stesso, partendo da ogni punto in cui il gruppo arriva nel luogo: puoi salire di 8 pixel e scendere di 12, i muri ti fermano, e puoi parlare con qualcuno entro due caselle. I posti che si aprono solo con la Psicoenergia o con la storia appaiono in rosso, quindi lì il rosso non vuol sempre dire sbagliato.

Quando un punto ha un problema, l'editor dice qual è a parole semplici, per esempio "il terreno qui è 32 pixel più alto del percorso più vicino", oppure che stare lì taglierebbe fuori il gruppo da una porta. Poi offre una soluzione:

- **Sposta nel punto buono più vicino** sposta la persona sulla casella più vicina senza problemi.
- **Livella … caselle all'altezza del sentiero** cambia l'altezza del terreno dal sentiero più vicino fino al punto, così il gruppo può arrivarci camminando. L'immagine non cambia, quindi usa **Dipingi** se deve sembrare un sentiero. È una normale pittura non salvata: Salva la mantiene e Annulla la toglie.
- **Aggiungi qui comunque…** se ne sai di più, per esempio quando un evento della storia apre la strada.

Trascinare una persona con **Sposta persone** comporta lo stesso controllo quando la lasci andare.

### Far parlare le persone

Clicca una persona. Premi **Fagli dire qualcosa…**, oppure **Aggiungi una battuta per un momento della storia…** se parla già.

### Cambiare ciò che c'è

Ogni evento della lista ha questi pulsanti, dove servono:

- **Cambia parole** apre l'editor di testo.
- **Quando…** decide quando succede l'evento: **Sempre**, **Solo dopo che** un flag della storia è attivo, o **Solo finché** non lo è. I flag sono elencati per nome.
- **Rimuovi** lo elimina.

### L'editor di testo

Scrivi normalmente. Una riga vuota inizia un nuovo riquadro di dialogo, e l'anteprima mostra come appariranno i riquadri nel gioco. **+ nome dell'eroe** inserisce il nome che ha scelto il giocatore. Il font del gioco ha lettere semplici, numeri e punteggiatura, senza accenti. Le virgolette curve, i trattini lunghi e "…" diventano da soli le loro forme semplici, e qualsiasi altra cosa che il font non sa disegnare viene rifiutata quando salvi.

Le tue parole vengono aggiunte come nuove righe, e il testo originale del gioco non viene mai sovrascritto. Se la stessa riga è usata altrove, lì resta com'era.

### Scene condivise

Alcuni luoghi condividono persone ed eventi con altri luoghi. Il pannello ti avvisa quando una modifica qui comparirà anche là.

## Porte

Premi **Porte** (D). Ogni porta compare sulla mappa con la sua destinazione. Le celle **blu** sono porte, quelle **rosse** non portano da nessuna parte.

- **Cambiare una porta:** cliccala, premi **Cambia dove porta…**, scegli un luogo, poi clicca dove deve arrivare il gruppo sulla mappa di quel luogo.
- **Creare una porta:** clicca qualsiasi altro punto e premi **Crea una porta qui…**. Può portare ovunque nel gioco.
- **Rimuovere una porta:** cliccala e premi **Rimuovi porta**. Le sue celle tornano terreno.

Una porta cambia in tutte le fasi della storia del luogo. Vengono trovate anche le porte aperte dagli script di scena: puoi cambiare dove portano, ma lo script resta lo stesso.

## Sposta persone

Premi **Sposta persone** (P).

1. Nel pannello **Storia e scena**, scegli una scena e una tabella di persone o di punti di arrivo.
2. Trascinali sulla mappa. Tieni premuto ⇧ mentre li lasci per agganciarli agli 8 pixel più vicini.
3. Salva.

I punti di arrivo sono dove compare il gruppo quando entra in un luogo.

## Timbro: copia e incolla

Premi **Timbro** (S).

1. Trascina un rettangolo sulla mappa per copiarlo.
2. Clicca per incollare, qui o in un altro luogo che usa lo stesso set di blocchi.
3. Premi Esc per tornare a copiare.

- **Calpestabilità e altezza** copia anche quelle insieme ai blocchi, ed è attivo per impostazione predefinita.
- **Solo oggetti** incolla solo gli alberi e gli altri oggetti, non il terreno sotto.
- Un'incollatura è un solo passo di annullamento, e la tua copia sopravvive al cambio di luogo e al ricaricamento.
- I luoghi con un set di blocchi diverso rifiutano l'incollatura, perché ogni blocco disegnerebbe l'immagine sbagliata.

## Importare le tue immagini

**Importa immagine…** si trova nel pannello Timbro. Funziona sui luoghi la cui grafica non è condivisa con nessun altro luogo, cioè 27 dei 182 di una copia appena scaricata del gioco. Altrove l'editor rifiuta, perché la tua immagine cambierebbe l'aspetto di altri luoghi.

1. Scegli **Sovrapposizione** (disegnata sopra il terreno, con sfondo trasparente) o **Terreno**.
2. Premi **Importa immagine…** e scegli un PNG, GIF o BMP. Può coprire al massimo 256 caselle da 16×16 pixel, per esempio 256×256 pixel, anche se un'immagine dettagliata può esaurire lo spazio prima. In quel caso l'editor te lo dice.
3. Controlla l'anteprima. Mostra i colori che il gioco disegnerà davvero e quanto spazio resta.
4. Premi **Aggiungi al set di tile**. I nuovi blocchi finiscono negli appunti del Timbro, pronti per essere messi al loro posto con un clic.

L'immagine viene adattata ai colori di questo luogo, e i pezzi ripetuti vengono riutilizzati per risparmiare spazio. Quando i fogli sono pieni, l'editor riutilizza la grafica di blocchi che il luogo non usa mai, e quei blocchi poi spariscono dalla tavolozza.

## Tabelle della storia e delle scene

Il pannello **Storia e scena** mostra le scene che usano questa mappa e le tabelle che ci stanno dietro, con nomi comprensibili come "Punti di arrivo: normale". I punti di arrivo e le persone compaiono sulla mappa. Le uscite si modificano come lista, con un controllo che il punto di arrivo scelto esista. Nella maggior parte dei casi gli strumenti Porte, Eventi e Sposta persone sono più semplici.

## Collegamenti

Premi **Collegamenti** per vedere un luogo qualsiasi al centro, con a sinistra tutti i luoghi che portano lì e a destra tutti quelli verso cui porta. Clicca un luogo per spostarti lì, o premi **Apri** per saltare a quella porta nell'editor. Usa la casella di ricerca per trovare un luogo.

## La mappa del mondo

Scegli la mappa del mondo in cima alla lista dei luoghi. Premi **← Luoghi** per tornare indietro.

| Strumento | Tasto | Cosa fa |
|---|---|---|
| **Visualizza** | V | Passa sopra con il mouse per vedere la regione di un punto e cosa fa. Clicca una città, un dungeon o un punto di passaggio blu per vedere dove porta. |
| **Terreno** | G | Dipingi i blocchi del terreno. ⌥-clic prende un blocco, e i blocchi recenti restano a portata di mano. |
| **Sovrapposizione** | O | Dipingi montagne, alberi e coste. Dove si può camminare dipende dalle tile di entrambi i livelli. |
| **Regioni** | R | Dipingi le regioni degli scontri. Ognuna ha le sue battaglie casuali, e ognuna prende il nome dalle città al suo interno. |
| **Città** | T | Trascina una città o un dungeon per spostarlo. Cliccane uno per cambiare dove porta. |

- Spunta **Calpestabilità**, **Regioni degli scontri** o **Luoghi** per mostrarli sulla mappa.
- Quando sposti una città, **sposta anche i suoi punti di arrivo** fa sì che, uscendo, tu compaia ancora accanto a essa. È attivo per impostazione predefinita.
- Le modifiche si salvano mentre dipingi. **Annulla** toglie l'ultima pennellata e **Ripeti** la rimette.
- La mappa della schermata di pausa è un'immagine separata, quindi non seguirà le tue modifiche.

## Controlla: trovare i problemi

Premi **Controlla** per esaminare tutte le mappe alla ricerca dei problemi che le tue modifiche causerebbero. Ognuno arriva con una soluzione e un pulsante **Mostra** che apre il punto. Cerca:

- porte che non portano da nessuna parte o portano a un punto di arrivo che non esiste;
- forzieri che non si possono aprire, non hanno nulla definito, si riempiono di nuovo o condividono un flag di apertura;
- più di 10 forzieri e pietre in un luogo;
- caselle che usano un blocco o un'altezza che il luogo non ha;
- righe che hai scritto e che il font del gioco non sa disegnare;
- luoghi i cui file sono danneggiati;
- modifiche che non sono più compatibili dopo un aggiornamento del sorgente del gioco.

Il gioco originale ha le sue stranezze, e quelle sono nascoste a meno che tu non spunti **Mostra anche le stranezze del gioco originale**. In un luogo che hai modificato, una stranezza che l'originale aveva già può comparire come tua. Nella pagina di un luogo, Gioca, Esporta e **Compila** eseguono prima Controlla per te e chiedono conferma prima di continuare se ci sono problemi. Nella pagina della mappa del mondo, Gioca e Compila non lo fanno, quindi premi Controlla da un luogo. Se Controlla non riesce a finire, lo dice e chiede conferma prima di continuare.

## Giocare al tuo gioco

Premi **▶ Gioca**. Salva, controlla, compila e apre il tuo gioco in mGBA, partendo dal luogo che stai modificando. Dalla pagina della mappa del mondo, compila e parte sulla mappa del mondo, senza il controllo.

- Ogni Gioca è una **partita nuova**: Isaac da solo, senza progressi nella storia, quindi un luogo può apparire nella sua versione di inizio gioco.
- Compari nel primo punto di arrivo del luogo che non sembra murato, non nel punto che stai guardando. È una stima: in alcuni luoghi parti ancora bloccato o dentro una scena della storia. Se succede, scegli un altro punto di arrivo in **Parti da**, accanto a ▶ Gioca, e premi di nuovo Gioca.
- Una compilazione dopo una modifica alla mappa richiede circa 20 secondi.
- Il punto di partenza esiste solo in una copia usa e getta del gioco, quindi la mod che esporti si avvia comunque normalmente dalla schermata del titolo.

## Condividere la tua mod

Premi **Esporta mod…**.

1. Compila il campo **Nome** e, se vuoi, il tuo nome e cosa cambia la mod.
2. Premi **Esporta**.

Ottieni una piccola patch `.bps` e un leggimi per i giocatori in `~/Documents/GSMapEditor/Exports/`. Premi **Mostra nel Finder** per vederli. Esporta esegue prima Controlla, e prova ogni patch una volta per confermare che riproduca esattamente la tua compilazione.

Spunta **Salva anche un .ips** se i tuoi giocatori usano patcher più vecchi. È molto più grande, perché IPS non sa registrare i dati spostati.

**Condividi la patch, mai il gioco compilato.** I giocatori applicano la patch alla propria copia, così non distribuisci mai il gioco stesso. Una patch `.bps` funziona con i patcher più comuni, come Rom Patcher JS e Floating IPS, oltre che con questo editor.

## Giocare alla mod di qualcun altro

Premi **Patcher…**.

1. Premi **Scegli una patch…** e scegli un file `.bps`, `.ips` o `.ups`.
2. Scegli il gioco a cui applicarla: **Il gioco originale, compilato su questo Mac** (nessuna ROM necessaria), oppure **Il mio file ROM**.
3. Premi **Patch**.

Il gioco modificato viene salvato in `~/Documents/GSMapEditor/Patched/`, e puoi premere **Gioca in mGBA** o **Mostra nel Finder**. Le patch BPS e UPS rifiutano il gioco sbagliato. Le patch IPS non possono controllarlo, e il patcher te lo dice.

## Dove si trova il tuo lavoro

| Cosa | Dove |
|---|---|
| La tua mod | Dentro la cartella del sorgente del gioco, per impostazione predefinita `~/Documents/GSMapEditor/alchemy/` |
| Patch esportate | `~/Documents/GSMapEditor/Exports/` |
| Giochi modificati con patch | `~/Documents/GSMapEditor/Patched/` |
| Impostazioni dell'editor e la tua cronologia di Annulla | `~/Library/Application Support/GS Map Editor/` |
| Compilazioni temporanee, si possono eliminare | `~/Library/Caches/GSMapEditor/` |

Su Windows e Linux le prime tre si trovano in `~/GSMapEditor/` nella tua cartella home di Linux, le impostazioni in `~/.config/gs-map-editor/` e le compilazioni temporanee in `~/.cache/gs-map-editor/`.

Per fare un backup della tua mod, copia la cartella del sorgente del gioco in un posto sicuro. Le tue modifiche sono normali file in quella cartella.

## Scorciatoie da tastiera

Su Windows e Linux, usa Ctrl al posto di ⌘ e Alt al posto di ⌥.

| Tasto | Luoghi | Mappa del mondo |
|---|---|---|
| V | Visualizza | Visualizza |
| B | Dipingi | |
| C | Calpestabilità | |
| H | Altezza | |
| K | Forziere | |
| E | Eventi | |
| D | Porte | |
| P | Sposta persone | |
| S | Timbro | |
| G / O / R / T | | Terreno / Sovrapposizione / Regioni / Città |
| ⌘Z | Annulla | Annulla |
| ⇧⌘Z | Ripeti | Ripeti |
| ⌘S | Salva | |
| ⌥-clic | Prendi un blocco | Prendi un blocco o una regione |
| ⇧ mentre lasci | Aggancia le persone agli 8 pixel più vicini | |
| Esc | Chiudi una finestra di dialogo, o torna a copiare nel Timbro | Chiudi una finestra di dialogo |

## Cosa non sa ancora fare

- **The Lost Age**, e le edizioni diverse da quella inglese.
- **Windows o Linux** come app pacchettizzata.
- **Luoghi completamente nuovi:** non c'è un pulsante per aggiungerne uno.
- **Battaglie e dati di gioco:** mostri, tabelle degli scontri, oggetti, negozi e musica non si possono modificare, anche se puoi dipingere a quale regione degli scontri appartiene un punto della mappa del mondo.
- **Script della storia:** puoi cambiare cosa dicono le persone e quando, e aggiungere eventi semplici, ma non scrivere scene di intermezzo.
- **La mappa della schermata di pausa.**

## Risoluzione dei problemi

| Vedi | Cosa fare |
|---|---|
| "Per giocare serve mGBA" | Installalo da [mgba.io](https://mgba.io) e premi di nuovo Gioca. |
| L'editor dice che il sorgente del gioco è una versione che non sa leggere | Il sorgente è cambiato in un modo che questo editor non capisce ancora. Sposta altrove quella cartella, poi usa **Scarica** nella schermata di configurazione. La tua mod resta nella cartella che hai spostato. |
| "Non è stato possibile trasformare le tue modifiche in un gioco" | I tuoi file sono al sicuro. Se indica una riga che hai scritto, cambiane le parole. Altrimenti usa **Annulla** finché non si compila, e premi **Mostra dettagli** per vedere il messaggio della compilazione stessa. |
| "I file di questo luogo non si possono leggere" | Uno dei suoi file è danneggiato. Usa **Ripristina luogo…**, oppure **Annulla** se l'ha causato un salvataggio recente. |
| "Il file che contiene le tue modifiche a persone, porte ed eventi non si può leggere" | Usa **Annulla**. Se non basta, ripristina quel file dal tuo backup. |
| "Questo luogo non ha spazio per altri di questi" | Il luogo ha finito i codici per cartelli e messaggi al passaggio. Rimuovine uno che hai aggiunto. |
| "Il font del gioco non ha…" | Sostituisci quel carattere con lettere semplici e punteggiatura. |
| La schermata di configurazione dice che il percorso della tua cartella contiene uno spazio | La compilazione non può usare percorsi con spazi. Scegli una copia del sorgente del gioco in una cartella il cui percorso non contenga spazi. |
| L'app si apre sulla schermata di configurazione con un errore | Il messaggio dice cosa non è riuscita a leggere. Premi **Controlla di nuovo** dopo aver risolto. |
| "Qualcosa è andato storto" | Quell'azione non è finita. Riprova, e se continua a succedere, riavvia l'app. |
| "Questa mappa usa un set di blocchi diverso" | Il Timbro incolla solo tra luoghi che condividono un set di blocchi. |
| "Questo luogo condivide la grafica con altri luoghi" | Importa funziona solo sui luoghi con una grafica propria. Il messaggio ne indica alcuni che puoi usare. |
| "Quel blocco è stato ritirato" | La sua grafica è stata riutilizzata per un'immagine importata. Scegli un altro blocco. |
| "Il gioco non ha spazio per altri forzieri" | Il gioco ha finito i flag di apertura liberi. Rimuovi un forziere che hai aggiunto. |
| Nel gioco manca un forziere | Un luogo mostra solo i suoi primi 10 forzieri e pietre. Esegui **Controlla**. |
| Controlla dice che una modifica "non è più compatibile" | Il sorgente del gioco è cambiato sotto quella modifica. Viene conservata ma lasciata fuori dal tuo gioco. |
| Un luogo sembra diverso da come l'hai modificato | Forse sei in un'altra **Fase della storia**, e Gioca avvia una partita nuova, che mostra la versione iniziale. |
| La configurazione si è interrotta a metà | Premi **Controlla di nuovo**, poi il pulsante del passaggio. Il log sotto la lista di controllo mostra cosa è successo. |
| Windows: l'editor non si è aperto nel browser | La piccola finestra di GS Map Editor mostra il suo indirizzo: copialo nel browser. |
| Windows: il programma di installazione dice che Ubuntu non è pronto | Riavvia Windows se te l'ha chiesto, apri una volta **Ubuntu** dal menu Start per scegliere nome utente e password, poi esegui di nuovo il programma di installazione. |

## Segnalare problemi

Per favore [apri una segnalazione](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md) con cosa stavi facendo, cosa è successo, e il chip e la versione di macOS del tuo Mac. Quando l'editor offre **Mostra dettagli** o un log di configurazione, premi **Copia** e incollalo. Per favore non allegare ROM o file del gioco.

## Note legali

Il codice di GS Map Editor è sotto la [licenza MIT](LICENSE). Gli strumenti inclusi mantengono le proprie licenze, elencate in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

L'editor non contiene ROM né grafica del gioco, e non distribuisce il testo del gioco. Nomi e immagini vengono letti dalla tua copia del sorgente del gioco mentre è in esecuzione. Golden Sun appartiene a Nintendo e Camelot, e questo progetto non è affiliato con loro. Alchemy è un progetto separato con le sue condizioni.

Per favore non condividere giochi compilati. Condividi invece le patch.

## Sviluppatori

Come compilare l'app, i test, come le modifiche arrivano nel gioco e come seguire gli aggiornamenti di alchemy: è tutto in [docs/it/DEVELOPING.md](docs/it/DEVELOPING.md).
