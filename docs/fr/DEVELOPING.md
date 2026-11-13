<!-- translated from docs/DEVELOPING.md @ 9804c9abc13f -->
# Développer GS Map Editor

*Ceci est une traduction du document anglais [DEVELOPING.md](../DEVELOPING.md) ; en cas de différence, c'est la version anglaise qui fait foi.*

Comment lancer, construire, tester et mettre à jour l'éditeur, et comment ses fonctionnalités marchent en interne. Pour apprendre à l'utiliser, lisez le [README](../../README.fr.md).

## Lancer depuis les sources

Il faut Python 3 avec Pillow, et une copie d'alchemy déjà compilée.

```sh
python3 server.py                  # alchemy at ~/gs_project/alchemy-port
python3 server.py --root /path/to/alchemy --port 8765
# open http://127.0.0.1:8765/
```

### Application de bureau (macOS)

`GS Map Editor.app` est l'éditeur dans sa propre fenêtre, pour les joueurs qui n'ouvrent jamais de terminal.

```sh
python3 -m venv .venv && .venv/bin/pip install pywebview pyinstaller pillow
python3 packaging/build_toolchain.py                          # binutils GBA + libpng, ~10 min, une seule fois
.venv/bin/python packaging/make_icon.py                       # packaging/icon.icns
.venv/bin/pyinstaller --noconfirm packaging/gsmapedit.spec    # -> dist/GS Map Editor.app
python3 packaging/make_dmg.py                                 # -> dist/GS-Map-Editor-<version>.dmg
python3 packaging/sign_and_notarize.py --identity "Developer ID Application: …"   # nécessite un compte Apple Developer
.venv/bin/python desktop.py                                   # ou le lancer sans empaquetage
```

L'application embarque ses propres outils de compilation (`packaging/toolchain`, 15 Mo) : les GNU binutils pour la GBA, une libpng statique et un petit substitut de `libpng-config` qui répond au `tools/Makefile` d'alchemy. Ils sont construits à partir de sources épinglées et vérifiées par somme de contrôle, et n'ont besoin de rien d'autre que macOS. Grâce à eux, les joueurs n'ont besoin que des outils de développement gratuits d'Apple ; Homebrew n'est utilisé que par une version sans la chaîne d'outils. `GSMAP_NO_BREW=1` masque Homebrew, pour prouver qu'une version n'en a pas besoin.

Au premier lancement, elle affiche une liste de contrôle d'installation (`static/setup.html`, `gsmap/setup.py`). Chaque étape est vérifiée, jamais supposée, et les étapes longues affichent leur journal en direct :
1. Les outils de développement d'Apple (ouvre l'installateur d'Apple).
2. Les outils de compilation : inclus avec l'application. Une version sans eux se rabat sur Homebrew et les paquets de l'INSTALL.md d'alchemy, vérifiés d'après ce que la compilation utilise plutôt que d'après les noms des formules.
3. La source du jeu : télécharger alchemy (épinglé au commit avec lequel cet éditeur a été testé) dans `~/Documents/GSMapEditor/` (sans espaces : la compilation ne les gère pas), ou choisir une copie existante.
4. `make bootstrap` (les compilateurs du jeu, construits une seule fois à partir des sources du sous-module `alchemy-gcc` d'alchemy, sans téléchargement), puis un premier `make tbs-en`.

Ensuite, l'application s'ouvre directement sur l'éditeur. Les réglages se trouvent dans `~/Library/Application Support/GS Map Editor/`. L'application ne contient aucune donnée du jeu : le jeu est construit à partir des sources d'alchemy sur le Mac du joueur. Ses deux serveurs n'écoutent que sur cette machine, derrière un jeton aléatoire. `desktop.py --no-window` affiche leurs adresses, pour les tests.

### Linux et Windows (WSL)

Sous Linux, l'éditeur tourne depuis les sources et s'ouvre dans le navigateur : `python3 desktop.py` (nécessite `python3-pil`) affiche la même liste de contrôle d'installation, avec les paquets apt de l'INSTALL.md d'alchemy à la place de Homebrew. Les installer nécessite `sudo`, donc la liste affiche la commande au lieu de l'exécuter. Les réglages vont dans `~/.config/gs-map-editor`, le cache de compilation dans `~/.cache/gs-map-editor`, et la source du jeu et les exports dans `~/GSMapEditor`. Sous Windows (WSL), les exports et les jeux patchés vont plutôt dans Documents\\GSMapEditor de Windows, et **J'en ai déjà une copie** ouvre la fenêtre de choix de dossier de Windows via PowerShell ; sous les autres Linux, il utilise zenity s'il est installé, et demande sinon de taper un chemin. Ce qui diffère selon le système (dossiers, ouverture d'un lien, mGBA, affichage d'un fichier) se trouve dans `gsmap/host.py`.

Windows exécute le même éditeur Linux dans WSL, qui est aussi la seule façon de compiler alchemy sous Windows :
- `windows/Install-GS-Map-Editor.cmd`, qu'une version publiée fournit avec son tag renseigné, active WSL et installe Ubuntu si nécessaire (droits d'administrateur, peut-être un redémarrage), exécute `windows/setup-in-wsl.sh` dans Ubuntu à ce tag, et ajoute des raccourcis dans le menu Démarrer et sur le bureau vers `wsl.exe … gs-map-editor`.
- L'éditeur s'ouvre dans le navigateur Windows grâce à la redirection localhost de WSL. Jouer lance le mGBA Windows depuis `Program Files\mGBA`, en lui donnant le chemin `\\wsl.localhost\…` du jeu. Le jeu se compile sur le disque propre d'Ubuntu, car une compilation sur `/mnt/c` est bien plus lente.
- Les pages affichent Ctrl et Alt à la place de ⌘ et ⌥ sur tout système autre qu'un Mac (`localWords` dans `static/common.js`).

`.github/workflows/linux.yml` vérifie cela sur les machines Ubuntu de GitHub à chaque push : `setup-in-wsl.sh` installe l'éditeur, `tests/setup_flow.py` parcourt l'installation du premier lancement via la commande installée, la compilation doit correspondre à `rom.sha1`, et les tests d'aller-retour, d'édition et de placement s'exécutent sur cette copie. La moitié Windows (le `.cmd`, l'installation de WSL, le raccourci, le mGBA Windows) n'a pas de test automatique : elle nécessite un PC Windows.

### Publier une version

Les versions sont construites par GitHub, sur ses Mac, par `.github/workflows/release.yml` : une image disque pour Apple Silicon (`macos-15`) et une pour Intel (`macos-15-intel`). Chaque tâche construit la chaîne d'outils et l'application, vérifie que les deux sont pour sa puce, exécute `packaging/smoke_test.py` (l'application démarre, trouve ses outils et indique l'épinglage) et crée le `.dmg`.

1. Définissez la version dans `packaging/gsmapedit.spec` (`CFBundleShortVersionString`).
2. Rédigez les notes que liront les joueurs dans `docs/releases/v<version>.md`.
3. Faites un commit, puis `git tag v<version> && git push origin v<version>`. Le workflow publie une pré-version avec les deux images, même si la tâche d'une des puces échoue.

**Run workflow** sur la page Actions construit les images sans publier de version. Les images ne sont pas signées : la section « Premier lancement » du README explique aux joueurs comment passer Gatekeeper, et `packaging/sign_and_notarize.py` prendra le relais dès qu'il y aura un Developer ID.

## Comment fonctionne chaque fonctionnalité

Cartes locales, The Broken Seal, édition anglaise. Pour savoir comment les utiliser, voir le [README](../../README.fr.md).

- **Regarder :** les 182 cartes, avec les bons jeux de tuiles et les emplacements réservés, affichage et opacité par calque, surcouches de collision et de hauteur.
- **Peindre :** blocs, collision et hauteur, avec pipette au ⌥-clic et annuler/rétablir. Les enregistrements sont exacts à l'octet près pour tout ce qui n'est pas modifié.
- **Tampon** (S) : faites glisser un rectangle pour copier une zone, puis cliquez pour la coller, ici ou dans une autre carte ayant le même jeu de blocs (Vale ↔ Debug · Sandbox).
  - La copie emporte les trois calques ainsi que la praticabilité et la hauteur.
  - **Objets seulement** colle uniquement les arbres et autres objets, pas le sol en dessous (un test de couleur contre le bloc de fond de chaque calque).
  - Un collage est une seule étape d'annulation. Le presse-papiers survit au changement de carte et au rechargement de la page. Échap revient à la copie.
  - Les cartes ayant un jeu de blocs différent refusent le collage, car chaque numéro de bloc dessinerait la mauvaise tuile.
- **Importer une image…** (cartes ayant leur propre jeu de tuiles ; aujourd'hui le Debug · Sandbox) : choisissez un PNG et un calque et voyez un aperçu, puis **Ajouter au jeu de tuiles**. Les nouveaux blocs arrivent dans le presse-papiers du Tampon, prêts à être placés d'un clic.
  - L'importateur découpe l'image en tuiles de 8×8 et fait correspondre ses couleurs à l'une des 14 lignes de palette de la carte (chaque tuile ne choisit sa propre ligne que si aucune ligne unique ne convient). L'index 0 est transparent.
  - Les tuiles déjà présentes dans les planches, y compris en miroir, sont réutilisées.
  - Les nouvelles tuiles vont d'abord dans l'espace vide. Viennent ensuite les tuiles utilisées uniquement par des blocs que la carte ne place jamais. Ces blocs sont *retirés* (masqués de la palette, refusés par le Tampon) et listés dans `games/tbs/src/mod/tilesets.json` d'alchemy.
  - L'aperçu montre les couleurs que le jeu dessinera, ainsi que la place restante.
- **Événements** (E) : tout ce qui se passe dans une scène, en mots, pour l'étape de l'histoire que vous choisissez :
  - **Personnages :** « 🗨 Garet: “Ever since the tremors started…” », les pensées lues par Mind Read, et les scripts avec leur propre description (« Asks about the mayor before departure, or the tremors after returning »).
  - **Cases :** panneaux (lus avec A), messages de passage, fouilles et ce qu'elles trouvent.
  - **Zones de sortie :** des boîtes qui servent de portes, dessinées sur la carte. Changez leur destination, ou supprimez-les.
  - Cliquez sur un personnage pour voir ses événements et **Le faire parler…** (ou ajouter une réplique pour un moment de l'histoire). Cliquez sur n'importe quelle case pour **ajouter un panneau**, **un message de passage** ou **un personnage**.
  - **Changer le texte** ouvre un éditeur avec des aperçus en direct de la boîte de dialogue : tapez normalement, et une ligne vide commence une nouvelle boîte. **Quand…** règle « toujours », « seulement une fois que <drapeau d'histoire> est activé » ou « seulement tant qu'il ne l'est pas », avec les drapeaux désignés par leur nom.
  - Les nouvelles répliques sont ajoutées à `en.po` dans un bloc appartenant à l'éditeur. Les répliques d'origine du jeu ne sont jamais réécrites : changer ce que dit quelqu'un le fait pointer vers une nouvelle réplique. Le texte que la police du jeu ne peut pas dessiner est refusé avant la compilation.
  - Quand une scène partage ses personnages et ses événements avec d'autres (c'est le cas du sandbox et du hub de debug), le panneau le signale.
- **Portes** (D) : chaque porte apparaît sur la carte avec sa destination (« → Vale Home ») ; celles qui ne mènent nulle part apparaissent en rouge.
  - Cliquez sur une porte, puis **Changer la destination…** : choisissez un lieu, puis cliquez sur un point d'arrivée sur sa carte.
  - Cliquez sur n'importe quelle autre case et **Créer une porte ici…** pour ajouter une porte vers n'importe quel endroit du jeu. **Supprimer la porte** retransforme toutes les cases d'une porte en sol.
  - Les portes ouvertes par des scripts de scène (la plupart de celles de Vale) sont aussi trouvées, en lisant quelle sortie le script demande. Leur destination peut changer ; le script reste.
  - Une porte change dans toutes les étapes de l'histoire de la scène, par des remplacements de sorties et d'événements. Les fichiers `.c` des scènes ne sont pas touchés.
- **Coffre** (K) : cliquez sur une case vide, choisissez un objet (avec son icône) ou une quantité de pièces, puis **Ajouter un coffre**. Cliquez sur un coffre pour changer son contenu ou le supprimer.
  - Une seule action écrit tout ce dont un coffre a besoin : le marqueur, le code de collision de la case, un événement `SEARCH(SEARCH_CHEST)` dans la table d'événements de la scène (sous forme de remplacement, pour que les fichiers `.c` des scènes restent intacts) et un nouveau drapeau « ouvert » pris dans la plage libre des coffres.
  - Le code est un code qu'aucune table d'événements des scènes de la carte n'utilise, et qu'aucune carte partageant ces tables n'a dans sa collision, donc rien d'autre ne devient fouillable. Au maximum 10 coffres et pierres par carte.
  - Un coffre est une ligne `treasure_spot` dans le `map.s` de la carte, dans la partie du fichier propre à l'édition anglaise.
- **Coffres et Pierres de Psynergie :** faites-les glisser pour les déplacer. La ligne du marqueur et les codes de collision des deux cases sont mis à jour ensemble, et les enregistrements qui enfreignent la règle marqueur/collision sont refusés.
- **Tables de scène :** pour chaque scène qui utilise la carte, choisissez une table.
  - Les entrées et les PNJ apparaissent sur la carte ; faites-les glisser avec l'outil Déplacer les personnages (P).
  - Les sorties sont modifiées sous forme de liste (type, scène cible, entrée, drapeau), avec une vérification que l'entrée cible existe.
- **Connexions :** n'importe quel lieu au centre, avec à gauche tous les lieux qui y mènent et à droite tous ceux vers lesquels il mène (porte, porte scriptée ou événement de scène, et le point d'arrivée). Cliquez sur un lieu pour vous y rendre ; **Ouvrir** saute à la porte dans l'éditeur.
- **Vérifier :** examine toutes les cartes à la recherche des problèmes que vos modifications causeraient dans le jeu et les décrit en termes simples, chacun avec une correction et un bouton **Afficher** qui ouvre l'endroit :
  - portes qui ne mènent nulle part, ou vers un point d'arrivée qui n'existe pas ;
  - coffres qui ne peuvent pas être ouverts, qui n'ont rien de défini, qui se remplissent à nouveau à cause d'un drapeau temporaire, ou qui partagent un drapeau « ouvert » ;
  - plus de 10 coffres et pierres sur une carte ; cases utilisant des blocs manquants ou retirés ;
  - modifications de tables de scène qui ne correspondent plus à la source du jeu (après une mise à jour d'alchemy).
  - Le jeu original a ses propres bizarreries (115 aujourd'hui, p. ex. 83 portes résiduelles). Chaque problème est aussi recherché dans le jeu non modifié, et ceux-là sont masqués à moins que vous ne les demandiez.
  - **Compiler** lance d'abord la vérification et demande confirmation avant de compiler s'il y a des problèmes.
- **Carte du monde** (en haut de la liste des lieux) : tout le monde extérieur, chargé au fil du défilement, avec les icônes des villes et des donjons étiquetées selon leur destination.
  - Surcouches : praticabilité (sol bloqué en rouge) et régions de rencontres, chacune nommée d'après les villes qu'elle contient (« Region 1 (Vale, Lunpa…) »).
  - **Sol** / **Surcouche** : peindre des blocs (⌥-clic en ramasse un ; les blocs utilisés récemment restent à portée de main). **Régions** : peindre les régions de rencontres. Les modifications s'enregistrent au fur et à mesure que vous peignez ; Annuler retire le dernier trait et Rétablir le remet. Les cases sont écrites dans `map/world/blocks.tsv`, en conservant les autres champs de chaque mot.
  - **Villes** : faites glisser une icône pour la déplacer. Ses points d'arrivée (là où vous apparaissez en quittant la ville) se déplacent avec elle, dans chaque étape de l'histoire où l'icône s'y trouve. Cliquez sur une icône ou une case de passage bleue pour changer sa destination.
  - Le nord enneigé est dessiné avec son propre jeu de graphismes. La carte de l'écran de pause est une image distincte et ne suit pas les modifications.
- **Exporter le mod… :** enregistre votre mod sous forme de petit patch `.bps`, avec un readme pour les joueurs, dans `~/Documents/GSMapEditor/Exports/`.
  - Le patch va du jeu non modifié à votre version compilée. Le jeu non modifié est compilé une seule fois à partir du commit d'où part votre mod : dans un dossier séparé via `git archive`, donc votre copie n'est pas touchée. Il est vérifié par rapport au `rom.sha1` d'alchemy, il est donc identique à la cartouche du commerce, et le patch s'applique au dump de n'importe qui.
  - Les patchs sont au format BPS (Rom Patcher JS, Floating IPS, patch à la volée des émulateurs). Les données déplacées deviennent des copies plutôt que de nouveaux octets. Chaque patch est appliqué une fois après son écriture, pour vérifier qu'il reproduit exactement votre version compilée.
  - L'export lance d'abord la vérification. Vous partagez vos modifications, jamais le jeu.
- **Patcheur… :** applique le patch `.bps`, `.ips` ou `.ups` d'un mod et enregistre le jeu dans `~/Documents/GSMapEditor/Patched/`, avec **Jouer dans mGBA** et **Afficher dans le Finder**.
  - Patchez soit le jeu non modifié que ce Mac a compilé à partir des sources (aucune ROM nécessaire), soit votre propre fichier ROM. Votre fichier est nommé d'après le `rom.sha1` d'alchemy (« Golden Sun (English) »), avec un avertissement s'il ne s'agit pas d'un jeu non modifié.
  - BPS et UPS refusent le mauvais jeu. IPS ne peut pas vérifier, et le patcheur le signale.
  - L'export peut aussi écrire un `.ips` pour les patcheurs plus anciens. Il est plus gros, car IPS ne peut pas enregistrer les données déplacées (4,2 Mo contre 383 Ko pour le mod de la salle de debug), et il est vérifié de la même façon.
- **▶ Jouer :** un seul bouton : enregistre ce qui n'est pas enregistré, lance la vérification, compile et ouvre votre jeu dans mGBA, en démarrant une nouvelle partie au lieu que vous modifiez (depuis la page de la carte du monde, sur la carte du monde). Le point de départ est écrit dans une copie jetable du jeu ; ce que vous exportez n'en garde aucune trace. Si la compilation échoue, vous obtenez une explication simple, avec les détails techniques repliés et un bouton de copie pour les rapports de bug. **Compiler** seul se trouve sous **Avancé**.
- **Annuler / Rétablir :** une seule paire de boutons pour tout. Annuler retire d'abord la peinture non enregistrée (la pile propre à la page), puis les actions enregistrées, de la plus récente à la plus ancienne, quels que soient l'outil et le lieu qui les ont faites ; un enregistrement transforme la pile de la page en une seule action enregistrée. Chaque écriture passe par `writing(label, where)` de `server.py`, une transaction de `gsmap/fsio.py` qui conserve l'ancien contenu des fichiers comme entrée d'historique étiquetée avec quoi et où (« adding a person », carte `051`). `undo_last` remet une entrée en place et conserve ce qu'elle a remplacé sous `history/redo` ; `redo_last` fait l'inverse ; une nouvelle action vide `history/redo`. Les deux passent par le journal, donc un plantage en cours de route est terminé au démarrage suivant. Les 30 dernières de chaque sont conservées, sous `history/` dans le dossier de support.
- **Où les personnages peuvent se tenir** (`gsmap/walk.py`) : les règles de déplacement du jeu, tirées du code de terrain d'alchemy : des pas de 8 pixels qui nécessitent cinq sondes dégagées, au plus 8 pixels vers le haut et 12 vers le bas (`terrain.c`, `MapGrid_CheckCollision`), les hauteurs tirées de la forme de chaque case par les seize fonctions de terrain et `terrain_tables.c`, les rebords, les points d'escalade et les fossés, et la parole à moins de 32 pixels et 48 vers le haut ou le bas. Les glissades sont suivies comme le fait `Imil_RunIceSlide`, pour tout déclencheur de passage dont le script fait glisser. Le groupe est suivi sur une grille de 8 pixels depuis chaque point d'arrivée de la scène ; un personnage bloque à moins de 12 pixels (deux rayons de 8, moins 2 chacun). `POST /api/map/<n>/walk` colore chaque case ; `/walk/check` renvoie les problèmes d'un endroit, l'endroit sans problème le plus proche, et les modifications de forme qui aplanissent un chemin jusqu'à lui (des formes plates que la carte possède déjà). Les modifications non enregistrées de forme et de praticabilité sont envoyées avec. La Psynergie et les événements de l'histoire ne sont pas suivis, et les personnages autres que celui vérifié ne sont pas des obstacles. Vérifié par rapport au jeu : environ 92 % des personnages placés par Camelot sont accessibles pour leur parler selon ces règles, le reste étant des salles de cinématiques et des endroits ouverts par la Psynergie.
- **Réinitialiser le lieu… :** remet un lieu tel que le jeu original l'a (Annuler ramène votre version). Les tables de scène que d'autres lieux partagent ne sont pas touchées, et l'éditeur le signale.
- **L'enregistrement, c'est tout ou rien :** les fichiers d'une action arrivent ensemble ou pas du tout, chaque fichier est remplacé en une seule étape, et si l'éditeur s'arrête en cours de route, il termine l'annulation au démarrage suivant.
- **Noms :** les lieux sont listés par leur nom dans le jeu (« Vale · Vale Home »).
- **Pinceaux de praticabilité :** nommés et codés par couleur (Sol, Mur, Rebord, Mur à escalader / échelle, Trou à sauter, Sol dangereux, cases de fouille, …).
- **Survol :** indique ce que fait une case (« Exit → Vale », « Chest: Herb », « Scripted (probably a door to …) »).
- **PNJ :** dessinés avec leurs sprites, listés par nom.
- **Tables de scène :** noms compréhensibles (« Arrival points: normal », « People: After Kalay »).
- **Case à cocher Avancé :** fait réapparaître les codes bruts.
- **Liens :** `?map=003&tool=points&kind=placements` ouvre directement un lieu.
- **Aucun graphisme ni texte livré :** les noms d'objets, de lieux, de personnages, de sprites et de drapeaux, les icônes d'objets et les aperçus de sprites sont tous lus à l'exécution depuis la copie d'alchemy du joueur. `gsmap/data` ne contient que les découvertes propres à l'éditeur : images d'aperçu, drapeaux de coffre libres, et ce que fait chaque code de praticabilité.

**Comment les modifications de scène atteignent le jeu :** par un seul point d'accroche, sans réécrire les fichiers de scène d'alchemy. Voir `docs/SPEC.md` et `games/tbs/src/mod/README.md` d'alchemy.
- L'éditeur stocke des copies modifiées des tables dans `games/tbs/src/mod/overrides.json` d'alchemy et génère `mod.c` à partir de celui-ci.
- `MOD_SCENE_LOADED` dans `Scene_LoadOverlay` (`system/main_routine.c`), que l'éditeur ajoute à une copie ordinaire la première fois qu'il écrit une modification de scène, substitue une enveloppe qui exécute toujours la logique propre à chaque scène pour choisir ses tables.
- Sans remplacements, GSMOD est désactivé et les six éditions se compilent toujours à l'identique, octet pour octet.

Les prochaines étapes sont dans le plan de construction de [`SPEC.md`](SPEC.md).

### Suivre alchemy

Tout ce que l'éditeur sait de l'organisation d'alchemy se trouve dans `gsmap/layout.py`. Le commit avec lequel il est testé est `ALCHEMY_PIN` dans `gsmap/setup.py`. Quand vous le changez, mettez aussi à jour la ligne de version dans le README, sinon le test de sécurité échoue. Pour essayer une nouvelle version :

1. `python3 -m gsmap.preflight path/to/alchemy` indique en termes simples ce qui ne correspond plus. Il s'exécute aussi à chaque démarrage, et s'arrête là plutôt que de dessiner des cartes avec les mauvaises tuiles.
2. Compilez-la, puis `python3 tools/snapshot.py path/to/alchemy new.json` et `python3 tools/snapshot.py --compare old.json new.json` montrent chaque différence dans ce que lit l'éditeur. Les deux versions compilent le même jeu, donc les résultats ne devraient changer que là où vous l'attendez.
3. Lancez les tests ci-dessous.

Faire passer une copie existante à un nouvel alchemy à la main relève de git ordinaire : fusionnez ou extrayez le nouveau commit, puis `git submodule update --init --recursive alchemy-gcc`. Depuis `alchemy-gcc` 3a12774 (alchemy du 2026-11-08), agbcc est constitué de fichiers ordinaires au lieu d'un sous-module imbriqué, et dans une copie antérieure la mise à jour s'arrête avec « untracked working tree files would be overwritten ». Dans `alchemy-gcc`, lancez `git submodule deinit -f agbcc`, supprimez le dossier `agbcc` et `.git/modules/agbcc` sous le dossier git d'alchemy-gcc, puis relancez la mise à jour. Supprimez `out/*/deps.mk` et `out/*/objects.mk` avant la première compilation. Le 2026-11-10, les commits les plus récents d'alchemy-gcc ont été reformulés et réépinglés, si bien qu'un `git fetch` dans une copie plus ancienne peut se terminer par « Errors during submodule fetch: alchemy-gcc » (« not our ref 8b1b6b4… ») ; le fetch principal a quand même fonctionné, et `git submodule update` extrait ensuite le nouvel épinglage. Le bouton **Télécharger** de l'installation fait toujours un clone neuf, donc les joueurs ne rencontrent pas ce problème.

Les modifications de scène enregistrées portent une empreinte de la table pour laquelle elles ont été faites. Une table renommée en amont la suit. Une modification d'une table dont le contenu d'origine a changé est conservée mais exclue du jeu, et la vérification le signale.

### Tests

- `python3 tests/safety.py` : ce qui ne doit jamais mal tourner : les échecs et les plantages ne laissent aucun fichier à moitié enregistré, annuler et rétablir parcourent les actions enregistrées dans l'ordre et une nouvelle modification vide le rétablissement, les coffres restent dans leurs propres salles, les valeurs incorrectes et les patchs malveillants sont refusés, les tables renommées ou modifiées sont gérées, une organisation inconnue est signalée plutôt que devinée.
- `python3 tests/placement.py` : les règles de déplacement confrontées au jeu : les personnages placés dans huit villes sont accessibles pour leur parler et leurs sorties atteignables, et à Imil la glace, un endroit enneigé inaccessible (avec sa correction par aplanissement), une allée étroite, un pas de porte et un mur font chacun l'objet d'un avertissement.
- `python3 tests/edits.py` : enregistre des modifications de blocs, de praticabilité et de hauteur sur une copie de vraies cartes et vérifie qu'elles se relisent, sans que rien d'autre ne change.
- `python3 tests/i18n.py` : chaque message affiché par le code est traduit dans chaque langue, et chaque traduction conserve ses `{placeholders}`, balises HTML et touches (⌘ ⇧ ⌥ ▶).
- `python3 tests/roundtrip.py` : charge et réenregistre chaque grille de carte, table d'images de cases et de formes, et liste de coffres (727 fichiers avec le mod de la salle de debug, 721 sur une copie ordinaire). Tous doivent ressortir identiques à l'octet près. Cela garantit qu'enregistrer une carte ne change que ce que vous avez modifié.

### Langues

Les mots propres à l'éditeur sont traduits ; le jeu reste en anglais. Écrivez chaque message en anglais, enveloppé pour qu'on puisse le trouver : `tr("…")` en Python (`gsmap/i18n.py`), `T('…')` dans les pages (`static/i18n.js`). Le premier argument est toujours une seule chaîne simple ; les parties variables sont des marqueurs `{name}` (`tr("Map {n} has {k} chests", n=n, k=k)`), et les pluriels sont deux modèles complets. Le texte des pages HTML, ainsi que les textes entiers ou les titres que les scripts insèrent dans la page, sont traduits tels qu'ils apparaissent lorsqu'ils correspondent exactement à un message ; tout ce qui se trouve dans un élément `data-notr` (les noms et dialogues du jeu) est laissé tel quel. Ne traduisez pas ce qui est écrit dans des fichiers (mod.c, en.po, le readme exporté) ni ce qui est comparé par le code.

`python3 tools/extract_strings.py` rassemble chaque message dans `static/i18n/<lang>.json` (anglais → traduction), en ajoutant les nouveaux vides et en supprimant ceux que le code n'a plus ; `--check` échoue si certains sont désynchronisés ou non traduits. La langue choisie dans le menu 🌐 est conservée dans les réglages de l'éditeur (`language`) ; tant qu'aucune n'est choisie, ce sont les langues préférées du navigateur qui décident. Les messages de chaque requête l'utilisent (`i18n.begin` dans les deux serveurs), et les pages reçoivent leur catalogue depuis `/i18n-strings.js`. Pour ajouter une langue, ajoutez-la à `LANGS` dans `gsmap/i18n.py`, lancez l'extracteur et remplissez le nouveau fichier.

Le README et cette documentation sont aussi traduits : `README.<lang>.md` à côté du README, et `docs/<lang>/` pour `DEVELOPING.md`, `PRODUCT.md`, `SPEC.md` et `research/`. `docs/upstream-issues.md` (pour le suivi des tickets en anglais d'alchemy), `docs/releases/` et `THIRD_PARTY_NOTICES.md` restent en anglais. Les fichiers anglais sont les originaux : modifiez-les d'abord, puis les traductions, et lancez `python3 tools/doc_translations.py --stamp` pour noter quel texte anglais chaque traduction suit désormais. Sans `--stamp`, l'outil vérifie les liens, titres, adresses web et fragments `code` de chaque traduction, et liste celles dont l'anglais a changé depuis. L'extracteur collecte aussi les noms et descriptions des pinceaux de praticabilité, dans `gsmap/data/collision.json`.

## Documentation

- [`SPEC.md`](SPEC.md) : la spécification de l'éditeur, les invariants et le plan de construction par étapes.
- [`research/`](research/) : les éléments de preuve avec références fichier:ligne.
  - `rendering.md` : emplacements réservés, jeux de tuiles, fenêtres, fusion, animation.
  - `local-connections.md` : scènes, sorties, marqueurs, PNJ, nouvelles cartes.
  - `overworld.md` : la carte du monde.
