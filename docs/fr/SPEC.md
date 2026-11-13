<!-- translated from docs/SPEC.md @ a658d8254020 -->
# gs-mapedit : spécification de l'éditeur et plan de construction

*Ceci est une traduction du document anglais [SPEC.md](../SPEC.md) ; en cas de différence, c'est la version anglaise qui fait foi.*

Périmètre : un éditeur de cartes pour **Golden Sun: The Broken Seal** construit sur l'arborescence source d'alchemy. Il couvre les **cartes locales** (villes, donjons, intérieurs) et le **monde extérieur**. The Lost Age partage le format des cartes locales, il viendra donc plus tard à faible coût. Son moteur de monde extérieur est encore surtout en assembleur dans alchemy.

L'éditeur lit et écrit uniquement les fichiers source d'alchemy : TSV, PNG, et des régions étroites de tables en C/asm. Il ne touche jamais à une ROM. Les éléments de preuve détaillés, avec références fichier:ligne, se trouvent dans `docs/research/` (`rendering.md`, `local-connections.md`, `overworld.md`). Ce fichier énonce les décisions.

## Règles de base

1. **Aller-retour exact à l'octet près.** Charger puis enregistrer quoi que ce soit de non modifié doit reproduire le fichier octet pour octet. Chaque type de fichier reçoit un test d'aller-retour sur toute l'arborescence. Une compilation non modifiée doit toujours passer `compare` OK.
2. **Modifier sur place ; ajouter à la fin, ne pas insérer.** Les positions des lignes de table sont des identités. Numéro d'acteur = 8 + ligne de placement. Id de scène = ligne dans `scenes.s`. Les tables de sorties utilisent des numéros de scène simples. Insérer une ligne renumérote les choses sans prévenir, donc les nouvelles lignes vont à la fin.
3. **Valider avant d'enregistrer.** Chaque opération a des invariants (ci-dessous). L'éditeur refuse d'enregistrer un état qui en enfreint un, ou le signale clairement.
4. **La compilation est le juge.** Après l'enregistrement, lancer `make tbs-en`. L'éditeur fait remonter les erreurs de compilation. Un test en jeu dans mGBA est la vérification finale.
5. **Épingler alchemy.** Travailler sur un commit connu. Avant de passer à un nouveau, lancer `tests/roundtrip.py` et la vérification de rendu complet (environ 2 minutes). Elles ont détecté immédiatement la restructuration des chemins du 19 octobre.

## Cartes locales

### Rendu (implémenté, vérifié sur les 182 cartes)

- **Ressources :** la palette, les blocs de caractères 1–3 et la planche D de chaque carte proviennent de sa ligne `gMaps` (`map/maps.c`), résolue via le `gamepak/resource_directory.s` développé. Les cartes 001, 002, 108 et 110 ont des lignes alternatives.
- **Emplacements réservés :** la k-ième case `0xfff`, ligne par ligne sur toute la grille de 128×128, est le bloc k avec son quartet supérieur conservé (`field/map_grid_convert.s`). Le nombre d'emplacements réservés est égal au nombre de lignes de `metatiles.tsv` sur les 182 cartes.
- **Fenêtres :** la fenêtre de chaque calque commence à l'origine du calque plus les limites de l'en-tête et boucle à 128.
- **Reste à faire :**
  - composition des fusions (`blend.tsv` : BLDCNT/BLDALPHA/BLDY) ;
  - animation des tuiles (`animation.tsv`, planche D) ;
  - ancrage de la parallaxe pour les cartes 047, 103, 104, 147 et 148 ;
  - limites de caméra facultatives tirées des entrées de scène.

  Les règles sont dans `rendering.md`.

### Données modifiables et invariants

| Élément | Fichier | Modification | Invariants / remarques |
|---|---|---|---|
| Blocs par case (3 calques) | `map.txt`, l'image de chaque case | peindre des id de blocs résolus | Enregistré avec l'**encodeur d'emplacements réservés** : parcourir ligne par ligne avec un compteur k. Une case dont le bloc == k est écrite `0xfff` (quartet supérieur conservé) et k++ ; les autres cases sont écrites explicitement. Vérifié comme l'inverse exact sur les 182 cartes. |
| Définitions de blocs | `cell_pictures.tsv` | ajouter de nouvelles combinaisons de tuiles 2×2 | 4 095 blocs au maximum. Numéro de ligne = id du bloc. |
| Codes de collision | `map.txt`, le comportement de chaque case | peindre | Par fenêtre de calque. Les codes 1–239 peuvent porter des événements (sorties, coffres). |
| Hauteur / forme | `map.txt`, la forme de chaque case, + `shapes.tsv` | peindre | Par fenêtre de calque. |
| Coffres / Pierres de Psynergie | lignes `treasure_spot x, z, id` dans `map.s` | ajouter/déplacer/supprimer | **l'id doit être égal au code de collision en (x, z)** : vérifié 418/418. 10 au maximum par carte. Ligne de marqueur de fin `ff ff ff`. Le contenu nécessite un événement `SEARCH(SEARCH_CHEST)` dans la scène avec un nouveau drapeau. |
| Animation des tuiles | `animation.tsv` | plus tard | 16 canaux au maximum. |

Fichiers partagés : les blocs peuvent venir du dossier d'une autre carte, et les cases et attributs de `default/` sont partagés aussi. L'éditeur indique quand un fichier est partagé et avertit avant de le modifier.

### Tables de scène : un point d'accroche, des remplacements appartenant à l'éditeur

**Conception (orientation du propriétaire) : modifications minimales des fichiers d'alchemy.**
- Le moteur lit chaque table de scène via `gOverlayArea`, la table d'entrée de l'overlay de scène en RAM. Les overlays sont chargés à un seul endroit : `Scene_LoadOverlay` (`system/main_routine.c`).
- L'éditeur y ajoute **une ligne**, `MOD_SCENE_LOADED(gMainRoutineWork.next, &gOverlayArea);`. C'est une macro qui ne produit rien sauf si la compilation définit `GSMOD`, donc la version d'origine continue de correspondre au jeu du commerce.
- Avec `GSMOD`, la macro appelle du code généré par l'éditeur dans `games/tbs/src/mod/`. Ce code remplace les pointeurs de fonction de la table d'entrée (entrées, sorties, placements, événements, régions) par des fonctions qui renvoient les tables de remplacement de l'éditeur pour cette scène, et laisse le reste tel quel.
- La carte du monde est aussi un overlay de scène, donc le même point d'accroche couvre les icônes, les sorties et les événements du monde extérieur.
- Les fichiers `.c` des scènes ne sont jamais réécrits. Les tables de remplacement résident dans le dossier mod, en ROM. Les fichiers de données pures (tables de carte, lignes de coffres) sont toujours modifiés directement.

Les tables sous-jacentes, pour référence :

Les scènes se trouvent dans `games/tbs/src/scene/<place>.c`. Elles contiennent cinq types de tables, tous des tableaux C de portée fichier composés de littéraux et de macros :

| Table | Nombre | Champs d'une ligne |
|---|---|---|
| Entrées | 189 | entrance, required_flag, x, y, z, orientation, limites de caméra |
| Sorties | 99 | type → (scène, entrée), drapeau facultatif |
| Placements | 274 | sprite, condition, comportement, x, y, z, orientation, orientation en parlant, drapeaux |
| Événements | 263 | type/contrôle, déclencheur, condition, valeur |
| Régions | 14 | boîte min/max, condition, type de sortie |

L'éditeur *lit* ces tableaux dans les fichiers `.c` des scènes, en initialisant un remplacement avec les lignes d'origine d'une scène, et *écrit* uniquement les copies de remplacement dans `mod/`. Événements : décoder les mots de contrôle connus et conserver tels quels les inconnus (environ 220 sont en hexadécimal brut).

Validation :
- L'entrée cible de chaque sortie existe dans la scène cible.
- Les lignes de placement ne sont pas insérées au milieu de la table (décalage des numéros d'acteur).
- La taille de l'overlay reste sous 32 Ko (le plus gros a 120 o de libre).
- Les lignes avec x=z=0 sont positionnées par le code ; l'éditeur les marque en lecture seule.

Le graphe des sorties est : code de collision / script / région → type de sortie → table de sorties → (scène, entrée) → ligne d'entrée. L'éditeur le montre sous forme de liens cliquables entre cartes.

### Nouvelles cartes (dernière étape)

La liste de contrôle se trouve dans `local-connections.md` §6 :
- 25 emplacements libres dans le répertoire de ressources, épinglés à 0x08320000 ;
- ajouter des lignes à `gMaps` (`map/maps.c`) et à `scenes.s` ;
- ajouter la ligne de la carte à `ld_script.ld` avant les overlays, plus l'overlay, la musique, le nom de zone et les règles de rencontres ;
- groupe ≤ 0x7f, id de scène < 511.

**L'espace en ROM est la vraie limite :** 3,5 à 43 Ko de libre à la fin des 8 Mo, selon l'édition. Une vraie nouvelle carte implique probablement d'agrandir la ROM au-delà de 8 Mo, ce qui n'a pas été testé.

## Monde extérieur

| Élément | Fichier | Remarques |
|---|---|---|
| Cases du sol + de la surcouche | `map/world/blocks.tsv` | 320×512 u32. Les morceaux font 16×16 cases, disposés sur 32 de large dans le TSV et en 16×16 dans le monde. Sol = morceau c, surcouche = c + 320. Alternatives 256–319 (jeu enneigé, pont de l'histoire). Bits d'une case : 0–15 bloc, 16–23 code de passage/d'événement, 24–30 type de terrain (= région de rencontres), 31 banque de comportement. |
| Blocs | `map/default/cells.tsv` | 4 386 × 4 octets de tuiles. **Partagé avec les cartes locales.** Préférer l'ajout à la fin. |
| Praticabilité | `map/default/attributes.tsv` | Par tuile de 8×8, 4×4 quartets. La surcouche l'emporte, puis le sol, sinon 7. Les valeurs 5–12 sont praticables. Partagé aussi. |
| Graphismes | `graphics/world_map/*.png` | 8 bpp, 256 tuiles par calque, 224 couleurs. Le jeu B est le nord enneigé. Préserver le mode et les indices des PNG. |
| Icônes de villes / entrée | `scene/world_map.c` `gWorldMapPlacements`, `gWorldMapEvents`, `gWorldMapExits` | Icône = acteur 8 + ligne. Le contact déclenche 100 + acteur → `EVENT_EXIT` → sortie → (scène, entrée). Certaines entrées sont plutôt des codes de passage. Doit rester aligné avec `gWorldMap_PlaceMarkers` (acteur 11 + i). |
| Rejoindre le monde | `gWorldMapEntrances` | Le `SCENE_EXIT(n, 2, e)` d'une ville place le groupe à la ligne e. |
| Rencontres | règles de `object/zonedata.c` → zones de `object/encounter.tsv` | Type de terrain + comportement → règle → zone (104 lignes fixes). |

Mises en garde :
- La carte de l'écran de pause (`picture.png`) est une illustration distincte, elle doit donc être repeinte à la main après des modifications de côtes.
- Il n'y a pas de variantes du monde extérieur par langue dans TBS.
- Le monde extérieur de The Lost Age est différent (2048 morceaux, 32×32) et son moteur est surtout en assembleur, il est donc hors périmètre jusqu'à ce qu'alchemy le reconstitue.

## Plan de construction

| Étape | Livre | Vérification |
|---|---|---|
| **1. Visionneuse** ✅ | Les 182 cartes locales rendues correctement ; surcouches ; infos au survol | aller-retour sur 895 fichiers ; rendu complet ; vérifications visuelles |
| **1b. Fidélité du rendu** | Composition des fusions, tuiles animées (lecture/image par image), ancrage de la parallaxe, recadrage selon les limites de caméra | Comparer aux rendus validés de `rendering.md` ; idéalement à des captures d'écran de mGBA |
| **2. Peinture locale** ✅ sauf le compositeur de nouveaux blocs | Palette de blocs depuis l'atlas ; peinture par calque ; pinceaux de collision/hauteur ; compositeur de nouveaux blocs (choisir 4 tuiles) ; annuler/rétablir ; enregistrement avec l'encodeur d'emplacements réservés | Enregistrement non modifié identique à l'octet près ; enregistrement modifié qui compile (`make tbs-en`) ; démarre dans mGBA |
| **3. Marqueurs + tables de scène** ✅ ajout, remplissage, déplacement et suppression de coffres ; portes reliées par un clic (redirection, ajout, suppression, portes scriptées comprises) ; événements en mots avec nouvelles répliques, panneaux, messages de passage, personnages et conditions ; zones de sortie ; déplacement des pierres ; entrées, PNJ, sorties | Placement de coffres/pierres (marqueur + collision + événement) ; modification des entrées/sorties/placements ; navigation dans le graphe des sorties entre cartes | Aller-retour des tables identique à l'octet près sur les 201 scènes ; compilation ; test en jeu d'un changement de sortie |
| **4. Visionneuse du monde extérieur** ✅ | Monde vu de dessus avec les jeux A/B, calque de surcouche, praticabilité, surcouche des types de terrain/rencontres, icônes de villes et liens de sortie | Porter le prototype de recherche ; comparer à `world_mixed_small.png` |
| **5. Édition du monde extérieur** ✅ blocs du sol/de la surcouche, régions, déplacements et liens des icônes ; codes de passage, zones de rencontres et nouvelles icônes encore à faire | Peindre les cases (bloc, type de terrain, code de passage) ; modifier les icônes, sorties, entrées ; zones de rencontres | Aller-retour de `blocks.tsv` et des tables ; compilation ; test en jeu |
| **6. Nouvelles cartes / scènes** | Assistant pour la liste de contrôle des nouvelles cartes ; jauge du budget ROM | Compilation ; test en jeu |

Les étapes 2–3 rendent l'éditeur local vraiment utile. 4–5 ajoutent le monde extérieur. 6 est la plus risquée, car elle dépend de l'espace en ROM.

## Questions ouvertes

- ~~La compilation exige-t-elle nombre d'emplacements réservés = nombre de blocs ?~~ **Non.** Testé : une modification laissant 56 emplacements réservés pour 441 blocs compile et se lie. L'encodeur écrit explicitement les blocs suivants dès qu'une première apparition est repeinte, donc le diff est plus gros mais valide. L'apparence en jeu nécessite encore un test en jeu.
- Les cartes dont le `blend.tsv` ne définit jamais BLDCNT (039, 042, 043, 114, 125) : la fusion vient probablement du code de scène.
- Ce que sont les `scene_points` de TLA ; ce qui écrit `touched_trigger` ; les valeurs de comportement de placement supérieures à 2.
- Si une ROM de plus de 8 Mo démarre et enregistre correctement sur les émulateurs et le matériel visés.
