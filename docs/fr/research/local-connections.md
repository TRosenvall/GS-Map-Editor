<!-- translated from docs/research/local-connections.md @ 9ab200ba52b5 -->
# Cartes locales : comment elles se connectent et comment elles sont peuplées (TBS, avec des notes sur TLA)

*Ceci est une traduction du document anglais [local-connections.md](../../research/local-connections.md) ; en cas de différence, c'est la version anglaise qui fait foi.*

Arborescence source : `alchemy/` (lecture seule). Les chemins ci-dessous sont relatifs à `alchemy/games/tbs/` sauf s'ils commencent par `games/`, `tools/` ou `out/`. « VÉRIFIÉ » = lu dans le code/les données, ou contrôlé par un script sur tous les fichiers ; « DÉDUIT » = déduit, non prouvé.

## Résumé

1. Une **scène** est une ligne de `gField_SceneTable` (`src/field/scenes.s`) : identifiant de ressource de l'overlay, groupe, variante, **ligne de carte en couches**. L'identifiant de scène est l'index de la ligne. 201 lignes. (VÉRIFIÉ)
2. La ligne de carte indexe `gMap_LayeredScenes` (`src/field/layered.tsv`, 186 lignes). Chaque ligne contient 6 décalages de ressources depuis `ResourceId_Map001` : en-tête de carte, palette, 3 planches de tuiles, données de couches. La table des scènes choisit donc la carte **et** le jeu de tuiles ensemble, et le numéro de ligne n'est **pas** le numéro `map_NNN`. (VÉRIFIÉ)
3. Le code de chaque overlay (`scene/<place>.c`) renvoie cinq tables via six veneers d'entrée : Entrances, Exits, Placements, Events, Regions, plus Initialize. Les accesseurs peuvent choisir entre plusieurs tables selon un drapeau ou l'identifiant de scène. (VÉRIFIÉ)
4. **Les sorties passent par des événements.** Le code de collision d'une case (1..239) correspond à un événement `EVENT_EXIT` (valeur = type de sortie), un script d'événement de contact appelle `Engine_EventRequestExit(kind)`, ou une boîte de région s'applique. La table des sorties associe ensuite (scène actuelle, type) à (scène, entrée). (VÉRIFIÉ)
5. À l'arrivée, la première ligne `SceneEntrance` dont `entrance` correspond et dont le drapeau est mis (ou -1) place le groupe et limite la caméra. Si aucune ligne ne correspond, la ligne 0 est utilisée. (VÉRIFIÉ)
6. Les **marqueurs** (`markers.tsv` : x, z, id) sont les positions des coffres et des Pierres de Psynergie. L'id est égal au code de collision de la case dans les 417 marqueurs. Ce que contient un marqueur vient de l'événement `SEARCH` de la scène ayant ce déclencheur. (VÉRIFIÉ)
7. Les **PNJ** sont des lignes `ScenePlacement`. Numéro d'acteur = 8 + index de ligne, que la condition de la ligne soit vraie ou non (le README des scènes dit le contraire). Les positions sont en 16.16. 396 des 2,321 lignes sont en (0,0) et sont positionnées par le code ; il y a 405 appels `Engine_ActorSetPosition` en ligne. (VÉRIFIÉ)
8. Chaque table de connexion est un initialiseur C ordinaire de portée fichier, fait de littéraux et de macros. Toutes peuvent être réécrites si l'outil les modifie sur place, en gardant les blocs `#if`, les noms symboliques et `const`. Les identifiants de scène dans les mots de sortie sont des **littéraux numériques**. Dans le code, ce sont des symboles de l'éditeur de liens `(s32)&SceneId_X`. (VÉRIFIÉ)
9. TLA garde les entrées, points et limites de caméra par carte dans un 7e bloc de carte (`scene_*.tsv`). Ses overlays ne portent le plus souvent qu'un `SceneEntrance` d'une ligne. C'est une différence de moteur, donc TBS ne peut pas passer aux mêmes fichiers. (VÉRIFIÉ pour la disposition, DÉDUIT pour la sémantique)
10. Pour ajouter une nouvelle carte ou scène, prendre les 25 emplacements `unused` du répertoire et ajouter des lignes à la fin des tables de scènes et de couches. Les adresses de banque fixes et **~3.5–43 Ko de marge de ROM par édition** (remplissage à 8 Mo) sont les limites strictes. (VÉRIFIÉ)

---

## 1. Câblage scène ↔ carte

### 1.1 Table des scènes (VÉRIFIÉ)

`src/field/scenes.s:1-9` :

```
.macro scene name, code, area, kind, map
  .equiv SceneId_\name, (. - gField_SceneTable) / 8   ; id = row index
  .2byte \code   ; overlay resource id (= directory index, 0x36f..0x3ce)
  .byte \area, \kind  ; group, variant
  .2byte \map, 0      ; gMap_LayeredScenes row, reserved
```

- `struct SceneRecord` se trouve dans `include/field_runtime.h:18-26` : `resourceId, group, variant, mapIndex, reserved`, 8 octets.
- La table a 201 lignes (décompte par script). Les lignes sans nom (`scene , 0x376, ...`) n'ont pas de symbole `SceneId_`.
- `Game_ResetForNewGame` (`src/object/object/scene.c:204-289`) fait `record = &table[gGameState.scene]`, puis `gGameState.map = record->mapIndex` (`:286`), puis `Scene_LoadOverlay` → `Resource_LoadCode(table[scene].resourceId, &gOverlayArea)` (`:294-298`), puis `Scene_TakeExit(Field_RunScene(entrance))` (`:288`).
- `group` sert à :
  - les règles de musique et de nom de zone (`src/object/scene_rules.s`, lues par `Scene_ResolveInteractionResult` et `Scene_GetAreaNameIndex` dans `src/object/object/encounter.c:279-345`) ;
  - l'effacement des drapeaux 0x300-0x3ff lors d'un changement de groupe ;
  - le drapeau « visité » `(group & 0x7f) + 0x180` (`scene.c:344`), donc un groupe doit être ≤ 0x7f.
- `variant` 2 marque les villes. Il désactive la régénération des PP à la marche et bloque Retreat (`src/object/object/run_scene.c`, `sceneVariant == 2`).
- Plusieurs scènes peuvent partager un overlay, par exemple Bilibin1/2/3 = 0x38b et AltinPeak1..11 = 0x3a4. Elles partagent aussi un même fichier `.c`.
- **Les identifiants de scène dans le code C sont des symboles de l'éditeur de liens.** `scene_ids.h` déclare `extern char SceneId_X;` et le code compare `gGameState.scene == (s32)&SceneId_X`, ce qui charge un mot du pool de littéraux. Il y a 487 utilisations de ce type dans `src/scene/*.c`.
- Run_scene compare `gGameState.map == (s32)&SceneId_Clear`, qui vaut 1, pour détecter la carte du monde (`run_scene.c:45`). (VÉRIFIÉ)
- **Les identifiants de scène dans les tables de données** (mots de sortie) sont des entiers simples ou les quelques noms `enum SceneId` de `include/field_scene.h:13-24`. Ce ne sont pas des symboles, ils ne suivent donc **pas** une renumérotation. (VÉRIFIÉ)

### 1.2 Choix de la carte : table des couches (VÉRIFIÉ)

`src/field/layered.s` fait `.incbin "layered.table"`, construit à partir de `src/field/layered.tsv`. Ses colonnes sont `map0..map5:u16` et il a 186 lignes. L'objet est placé dans `rom_main_01` (objects.tsv:59).

`struct LayeredSceneEntry { u16 resources[6]; }` se trouve dans `src/field/field/map_layers.c:164`. `Map_LoadLayeredScene(index)` (`:211`) utilise les six ressources ainsi :

| Colonne | Ressource | Utilisation |
|---|---|---|
| [0] | en-tête de carte | `Resource_GetTableEntry(resources[0] + ResourceId_Map001)` (`:233`) |
| [1] | palette | décodée ; la couleur 0 (le fond) est conservée (`:337`) |
| [2] | planche de tuiles | bloc de caractères 1 (`:345-357`) |
| [3] | planche de tuiles | bloc de caractères 2 |
| [4] | planche de tuiles | bloc de caractères 3 |
| [5] | données de couches | décodées dans `gMapLayerData` |

Toutes les valeurs sont des décalages depuis `ResourceId_Map001`. Développer les macros du répertoire les résout par nom (script de travail) :

- les lignes 0 et 1 sont `Field_Map001` + `Blank*`. Title, Clear et WorldMap les utilisent ; le chemin de la carte du monde ne les charge jamais.
- la ligne 2 est `Field_Map000` + `Set00{Palette,TilesA-D}` ;
- la ligne 5 est `Field_Map004` + `Set03*` ;
- la ligne 12 est `Field_Map010` + palette/A/B/C de Set09 + **Set08TilesD**.

123 des 186 lignes ne sont pas six ressources consécutives : une ligne peut mélanger des planches de jeux différents, et les recolorations réutilisent des planches. L'éditeur doit donc traiter la ligne comme six références indépendantes.

`map_NNN/` est nommé d'après `Field_MapNNN` (la numérotation du répertoire, `src/map/README.md` « The map numbers are the directory's »). Par exemple, la scène ValeHome (id 5) a mapIndex 4 → `Field_Map003` = `src/map/map_003/`. Le `markers.tsv` de cette carte (13,44,100) correspond à l'événement `SEARCH(...)` de ValeHome avec le déclencheur 100 (`src/scene/vale_home.c`, events).

Deux cartes portent des noms de lieu au lieu de numéros : `gondowan_passage/` (`Field_GondowanPassage`) et `venus_entrance/` (`Field_VenusEntrance`). Sur les 182 ressources de carte distinctes référencées, 8 sont utilisées par plus d'une scène.

### 1.3 Répertoire des ressources (VÉRIFIÉ)

`src/system/resource/directory.s` contient les macros `resource`, `group`, `area SET, sheets, maps...`, `recolor`, `overlays`, `unused` (`:1-51`).

- L'identifiant d'une entrée est sa **position** : `ResourceId_X = (. - Resource_DirectoryTable)/4`.
- `area SetNN, ABCD, mmm` émet `Field_Mapmmm`, puis `Tileset_SetNNPalette`, puis `TilesA..D`.
- Les overlays viennent en dernier, `overlays 36F … 3CE` (96 entrées, `:299-306`), suivis de `unused 25` (`:307`). Chaque emplacement inutilisé est `.4byte 0`.
- `Resource_GetTableEntry(i)` n'est que `Resource_DirectoryTable[i]` sans vérification de bornes (`src/runtime/runtime/system.c:150-152`).
- Le répertoire se trouve au début de `rom_tail_02`, qui est **épinglé** à 0x08320000 en EN (`main.ld`, dernier `ABSOLUTE` ; `out/tbs-en/tbs-en.map:7353`).
- Les données de carte (`map_NNN/map.s`, qui porte aussi les planches du jeu de tuiles qu'il possède), puis `src/system/overlay/overlays` suivent dans l'ordre de `rom_tail_02` (objects.tsv:436-631).
- Insérer une entrée de répertoire avant les overlays renumérote toutes les ressources suivantes. Cela casse les identifiants d'overlay de scenes.s (`0x36f`…) et tous les décalages de `layered.tsv` après le point d'insertion. Utiliser les emplacements `unused` : index 0x3cf..0x3e7. (DÉDUIT de la macro positionnelle ; l'arithmétique est VÉRIFIÉE.)

### 1.4 Overlays : entry, import, objects.tsv, overlays.tsv, édition de liens (VÉRIFIÉ)

`src/scene/README.md` et `src/system/overlay/overlay.ld` décrivent les overlays.

- **Entry** (`scene/entry/<place>.s`) se compose de six lignes `overlay_veneer` dans un ordre fixe : Initialize, GetEntrances, GetExits, GetPlacements, GetEvents, GetRegions. Chaque veneer est `ldr r4; bx r4; .4byte target` (`src/system/overlay.s:5-11`). Le moteur les lit comme `struct SceneEntries` (`include/field_runtime.h:42-57`) : un mot de veneer plus un pointeur de fonction chacun, 48 octets. Il appelle `gOverlayArea.entrances()` et ainsi de suite.
- **Import** (`scene/import/<place>.s`) se compose de `.set overlay_imports,1`, puis `.set import.NAME,1` pour chaque routine du moteur que le C appelle, puis `.include overlay.inc`. `overlay.inc` contient la liste maîtresse ordonnée d'environ 405 lignes `import NAME, TARGET`. Seules les lignes activées émettent un stub (`src/system/overlay.inc:9-25`). Les overlays ne peuvent pas s'appeler entre eux.
- **objects.tsv** donne à chaque overlay trois lignes `text` dans l'ordre (`entry/<place>`, `<place>`, `import/<place>`), avec en première colonne l'identifiant de l'overlay en hexadécimal (p. ex. `374 text games/tbs/src/scene/vale_home`). Une ligne `bss` facultative peut suivre (`.bss COMMON`, ou `resource_<id>_overlay .bss` depuis `src/system/overlay/ovl_<id>.s`).
- **overlays.tsv** donne l'en-tête de section de sortie `.bss` (p. ex. `.bss ALIGN(16)`) pour les 36 overlays qui ont des lignes bss. `tools/ags-objects/ags-objects.c:165-205` échoue avec « bss header and rows disagree » si un seul des deux existe.
- **Édition de liens.**
  - Chaque overlay est lié à 0x2008000 contre `symbols.elf` (Makefile:209-219).
  - Dans un overlay, tout le `.text` vient d'abord, puis tout le `.rodata`, puis tout le `.data`, dans l'ordre des objets (passes de `render()` dans `ags-objects.c`). Les tables `const` vont donc dans `.rodata` et les autres dans `.data`.
  - L'image est compressée par `tools/ags-overlays` en `resource_<id>.lz` et intégrée par `src/system/overlay/overlays.s` (`Resource_Overlay36F: .incbin ...` plus des octets résiduels `PACKER:` par édition).
  - `Resource_LoadCode` la décode dans `gOverlayArea` et corrige les BL Thumb (`system.c:228`).
- La zone d'overlay fait 32 Ko, et code + rodata + data + bss doivent y tenir. D'après les mesures de `out/tbs-en/overlays/*.map`, les plus grands sont 0x3b1 avec 32,648 o (120 o libres), 0x373 Vale avec 30,764 et 0x3c8 avec 30,732. (VÉRIFIÉ d'après la sortie de construction.)

### 1.5 Autres tables indexées par scène (VÉRIFIÉ)

Elles utilisent des symboles `SceneId_` ou le groupe, et restent donc correctes lors d'ajouts en fin de table :

- `src/object/scene_rules.s` :
  - `gScene_InteractionRuleTable` (musique : `scene_cue` / `group_cue`) ;
  - `gScene_AreaNameRules` (`scene_name` / `group_name`) ;
  - `gParty_PairResolveRules` (`return_to`, points de retour après une défaite) ;
  - `gBattle_BackdropScenes`.
- `src/object/location_rules.s` `gBattle_LocationRules` : zones de rencontres par (scène, entrée, drapeau).
- `src/scene/world_map.c` `gWorldMapExits` (`SCENE_EXITS(2)`…) et ses événements `EVENT_EXIT` (44) : comment la carte du monde entre dans les scènes locales.

---

## 2. Sorties et entrées

### 2.1 `struct SceneEntrance` (24 octets, `include/field_scene.h:54-70`) (VÉRIFIÉ)

| # | Champ | Type | Signification |
|---|---|---|---|
| 1 | entrance | s16 | le numéro d'entrée que nomme le mot de sortie ; -1 termine la table |
| 2 | requiredFlag | s16 | -1, ou un drapeau qui doit être **mis** (simple `GameFlag_TestFar`, sans encodage 0x1000) |
| 3 | x | s16 | pixels |
| 4 | y | s16 | pixels (hauteur ; non nul dans 20/1520 lignes) |
| 5 | z | s16 | pixels (« bas » de la carte) |
| 6 | facing | u16 | 1/65536 de tour (`enum Facing`, pas de 0x2000) |
| 7 | unused1 | s16 | 0 partout, non lu |
| 8 | cameraLeft | s16 | pixels, -1 = garder la limite de l'en-tête de carte |
| 9 | cameraTop | s16 | de même |
| 10 | cameraRight | s16 | de même |
| 11 | cameraBottom | s16 | de même |
| 12 | unused2 | s16 | 0 partout, non lu |

`Scene_ApplyEntrance` (`src/object/object/run_scene.c:461-505`) :

1. Cherche `entrance == gGameState.entrance && (flag == -1 || flag set)`. Si rien ne correspond, il utilise la **ligne 0**.
2. Sauf avec `FLAG_KEEP_PARTY_POSITION`, il écrit `gGameState.x/y/z = value << 16` et `heading = facing`.
3. Limite les bornes de la caméra, avec une vue minimale de 240×160.

Statistiques sur 189 tables / 1,520 lignes :

- 3 lignes utilisent un drapeau ;
- 1,023 règlent des limites de caméra ;
- les deux champs inutilisés valent 0 partout ;
- la colonne entrance est une constante symbolique dans 21 lignes.

### 2.2 Comment une sortie se déclenche (VÉRIFIÉ)

Il y a trois façons de quitter une scène :

1. **Case de sortie.** `Field_ProcessStep` lit le code de collision de la case du meneur (`src/object/object/step.c:240-249`).
   - Les codes `1..239` (`STEP_EVENT_FIRST/LAST`, `:19-27`) règlent `work->action = code`.
   - `Scene_RunTouchOrExit(code)` (`src/object/object/events.c:333-385`) cherche d'abord un événement `EVENT_TOUCH` avec `trigger == code`. S'il en existe un, il exécute son message ou son script, et le script reçoit le code en argument.
   - Sinon, il cherche `EVENT_EXIT` avec `trigger == code` : il joue le son de sortie (bits 5..4 du contrôle : 0 normal, 0x20 → SE_128 + effet 26, 0x30 → SE_129 + effet 25, 0x10 aucun) et règle `work->exit = event.value`, le **type de sortie**.
2. **Script.** Un script de contact/dialogue/Psynergie appelle `Engine_EventRequestExit(kind)`. C'est importé sous le nom `Event_SetExitRequestFar` (`src/system/overlay.inc:321`). Il y a environ 200 sites d'appel. Les portes typiques utilisent `TOUCH_WALKING_INTO(FACING_NORTH)` sur le code de collision de la porte, animent les cases de la porte, font entrer le meneur, puis demandent la sortie (`vale_home.c:444-471`). Les coordonnées d'animation des portes sont des **arguments d'appel en ligne** (`Event_OpenDoorAndWalkThrough(44, 7, 248, 279)`, `Map_CopyCellsTo(...)`) ou des tableaux `u16 ...DoorCells[]` `MAP_CELL_STEP(srcX,srcY,w,h,frames)` (`include/field_event.h:59-61`).
3. **Région.**
   - `struct SceneRegion` (`include/field_runtime.h:30-37`, 16 o) est `minX,minY,minZ,maxX,maxY,maxZ` (pixels ; min inclus, max exclu), `condition` et `value` = type de sortie. minX -1 termine la table.
   - Elle est vérifiée par `Field_CheckExitRegions` (`step.c:135-186`) chaque fois que le code de la case du meneur est non nul.
   - Il y a 14 tables de régions, 38 lignes ; la plupart des scènes renvoient NULL.

`Field_RunScene` renvoie `work->exit`. `Scene_TakeExit(kind)` (`src/object/object/scene.c:25-89`) ensuite :

- parcourt la table des sorties de l'overlay jusqu'au mot d'en-tête égal à l'identifiant de la scène actuelle ;
- prend le premier mot de sortie dont `kind == exitKind` ou dont le type est `0xff` (n'importe lequel), **et** dont le drapeau n'est pas mis (`SCENE_EXIT_IF` : le mot de drapeau suit ; la sortie est **ignorée tant que le drapeau est mis**) ;
- se rabat sur la scène de la première sortie, avec l'entrée 0, s'il atteint d'abord un mot de type 0 ou la fin (0x1ff).

### 2.3 Encodage des mots de sortie (VÉRIFIÉ)

`include/field_scene.h:72-77` :

```
SCENE_EXITS(scene)              = scene                         // header
SCENE_EXIT(kind, scene, ent)    = kind<<20 | ent<<12 | scene
SCENE_EXIT_IF(k, s, e, flag)    = SCENE_EXIT(k,s,e) | 0x10000000, flag   // two words
SCENE_EXITS_END                 = 0x1ff
```

| Champ | Bits |
|---|---|
| scène | 0..11 (le repli ne masque que 9 bits, et 0x1ff est la fin, donc les identifiants de scène doivent être < 511) |
| entrée | 12..19 (0..255) |
| type | 20..27 (1..254 réels, 0xff n'importe lequel, 0 = **en-tête**) |
| drapeau à suivre | bit 28 |

**`SCENE_EXIT(0, N, 0)` est un en-tête de scène, identique à `SCENE_EXITS(N)`.** Les tables d'overlays partagés l'utilisent : `gAltinPeak_Exits` (`altin_peak.c:2671-2722`) contient les listes de sorties de 11 scènes après un seul `SCENE_EXITS(77)`. Un script a trouvé des en-têtes pour 200 des 201 scènes d'overlay ; seule la scène sans nom 59 (overlay 0x39d) n'en a pas. TLA traite en plus un mot de drapeau de -1 comme « toujours » (`games/tla/src/field/common/take_exit.c`).

### 2.4 Catalogue des tables dans `src/scene/*.c` (+ `common/*.h`) (VÉRIFIÉ par script)

| Type (identifier par le **type**, les noms varient : `gX_Exits`, `gXExits`, `gXExits1`…) | Tables | Lignes | Tables avec `#if` à l'intérieur | `const` |
|---|---|---|---|---|
| `struct SceneEntrance` | 189 | 1,520 | 0 | 5 |
| tables de sorties `u32` (`SCENE_EXITS`) | 99 | 1,479 mots de sortie | 1 | 5 |
| `struct ScenePlacement` | 274 | 2,321 | 4 | 18 |
| `struct SceneEvent` | 263 | 5,891 | 10 | 13 |
| `struct SceneRegion` | 14 | 38 | 3 | 1 |
| Tableaux de pas de cases de porte (`u16` `MAP_CELL_STEP`, cases compactées `u32`, `struct MapCellAnim`) | ~10 | — | — | — |

Types d'événements par nombre de lignes :

- `PSYNERGY_ON_ACTOR` 1585
- `EVENT_TALK` 1374
- `EVENT_EXIT` 903
- `EVENT_TOUCH` 531
- `SEARCH(..)` 506
- `TOUCH_WALKING_INTO` 493
- contrôles en hexadécimal brut comme `0x31`/`0x21` (sortie avec bits de son), `0xc4f3`, `0x8413` : environ 220

Tous sont des tableaux initialisés de portée fichier, une ligne entre accolades par enregistrement (sorties : une macro par mot, parfois deux par ligne sous clang-format, p. ex. `world_map.c:2802`). Les accesseurs les renvoient, éventuellement choisis par drapeau ou par scène (`vale_home.c:104-160`, `bilibin.c:106-114`). Les tables de placement sont pour la plupart **non const**, car `Scene_AssignViewFlags` écrit à l'exécution la `condition` des lignes dont la condition vaut 0 (`src/object/object/actors.c:325`).

---

## 3. Marqueurs (coffres, Pierres de Psynergie)

- **Format** (VÉRIFIÉ). `markers.tsv` a l'en-tête `x:u8	z:u8	event:u8`, des lignes de colonne de case, ligne de case et id, et se termine par la ligne `0xff 0xff 0xff`. Il est encodé brut (`markers.table`, **pas** en LZ) et inclus par incbin comme 6e bloc de l'en-tête (`src/map/map_004/map.s:25`). Les valeurs peuvent être décimales ou en hexadécimal `0x` : `map_002/markers_es.tsv` ne diffère de `markers.tsv` que par le format des nombres.
  - Il y a 118 fichiers de marqueurs : 106 de base et 12 variantes d'édition (`*_ja/_de/_es.tsv`, choisies par `.ifdef TBS_EDITION_*` dans map.s).
  - 76 fichiers map.s pointent vers le `map_000/markers.table` vide.
- **Chargeur** (VÉRIFIÉ). La liste des marqueurs n'est pas décodée : `work->script = header + header->markers` (`map_layers.c:258`). `Field_PlaceMapMarkers` (`src/object/object/markers.c:30-131`), appelé depuis `run_scene.c:73`, fait ce qui suit :
  - Seuls les identifiants **100..239** sont pris en compte.
  - Pour chacun, il prend le premier événement de scène avec `trigger == id` :
    - `control & 0x1ff == 19` (`SEARCH(SEARCH_CHEST)`) : il crée l'objet **20** (coffre) au centre de la case `(col<<20)+0x80000`, calé sur le terrain. Si le drapeau de condition de l'événement est mis, le coffre est affiché ouvert (animation 2) ; si le drapeau est mis et que la valeur est une mimique (`0x5xxxxx`), il n'est pas placé du tout.
    - autre `SEARCH` avec la valeur `0x300000` (`FIND_PSYNERGY_STONE`) dont le drapeau n'est pas mis : il crée l'objet **28** (pierre).
  - Au plus `MARKER_MAX` = 10 sont placés. Un marqueur sans événement correspondant ne place rien.
- **Id = code de collision** (VÉRIFIÉ). Les 417 lignes de marqueurs de TBS ont toutes `grid_collision[x,z] == id` (script de travail). La fouille elle-même est indexée sur le code de collision de la case devant (`Scene_FindEvent(EVENT_SEARCH, code)`, `events.c:111`, `Field_SearchTile` `events.c:429`). Un marqueur sans le code de collision correspondant afficherait un coffre impossible à ouvrir. **L'éditeur doit écrire les deux.**
- **Contenu et drapeaux** (VÉRIFIÉ). Le contenu se trouve dans la table d'événements de la scène : `{ SEARCH(SEARCH_CHEST), <id>, <opened-flag>, FIND_ITEM(ITEM_X) | FIND_COINS(n) | FIND_PSYNERGY_STONE | FIND_MESSAGE(m) | 0x5xxxxx mimic | EVENT_SCRIPT(fn) }` (`include/field_scene.h:118-217`).
  - La condition est le drapeau « ouvert ». Selon le README, la plupart des drapeaux de coffre sont ≥ 0xe00. Le drapeau est mis quand on prend le contenu du coffre (`events.c:500-560`).
  - Le bit 16 de la valeur signifie « le groupe ne peut pas l'ouvrir ».
  - Il y a 135 lignes `SEARCH(SEARCH_CHEST)` et 17 lignes `FIND_PSYNERGY_STONE`. Certaines pierres utilisent des lignes `SEARCH_FACING(...)` avec une constante nommée `TRIGGER_STONE`, et certaines pierres sont de simples scripts (`Event_UsePsynergyStone` de ValeHome).
- Les codes 242..247 sont des messages fixes de « point de fouille », 250 est un sol dangereux, et 252..254 sont des corniches/points d'escalade (`step.c:19-27`, `events.c:387-418`). 0xff est un mur.

---

## 4. PNJ et objets

`struct ScenePlacement` (24 o, `include/field_scene.h:81-98`) (VÉRIFIÉ) :

| Champ | Type | Signification |
|---|---|---|
| sprite | s16 | type d'objet/de sprite ; 0-7 = personnages du groupe (emplacements propres), -1 termine la table |
| condition | s16 | -1 toujours ; `flag\|0x1000` = drapeau mis ; sinon drapeau non mis ; 0 = « en vue » (réécrit par `Scene_AssignViewFlags`) |
| behavior | s32 | `ACTOR_STAND`=1, `ACTOR_WANDER`=2, petits entiers (p. ex. 3), ou un pointeur vers un script d'action SC_ `s32 ...[]` |
| x, y, z | s32 | pixels en 16.16 via `PIXELS(n)` |
| facing | u16 | 1/65536 de tour |
| talkFacing | u8 | TALK_FACE_PARTY 0, _AND_BACK 1, KEEP 2, 3 suit le meneur |
| flags | u8 | bit 0 `PLACEMENT_SHARE_PREVIOUS_SPRITE` |

**Apparition** (`src/object/object/actors.c:75-180`, `ObjectTable_ResetForObject` `:217`) (VÉRIFIÉ) :

- Le meneur apparaît d'après `gGameState`, puis la table à partir de l'emplacement 8.
- **`actorIndex = slot++` s'exécute avant le test de condition (`:105-107`)**, donc une ligne ignorée utilise quand même son numéro : **acteur = 8 + index de ligne** pour les sprites > 7. Les déclencheurs `EVENT_TALK` et `PSYNERGY_ON_ACTOR` nomment ces numéros, donc réordonner ou insérer des lignes renumérote tous les événements de dialogue.
- Hauteur : y est ajouté à la hauteur du terrain hors de la carte du monde.
- Le maximum est de 58 acteurs placés (emplacements 8..65).
- Les lignes à drapeau de Djinn (48..127) ont aussi besoin de `condition+80`.

Décompte de la colonne behavior sur 2,321 lignes : STAND 1,705, WANDER 132, entier 306, symbole de script 178.

- 396 lignes sont en x=z=0. Ce sont des acteurs que le code Initialize positionne ou déplace.
- Le positionnement en ligne est courant :
  - `Engine_ActorSetPosition` : 405 appels
  - `OBJ_POS_SET(no,x,z)` (pixels, `include/event.h:13`) : 119
  - `Engine_ObjectCreate(kind,x,y,z)` : 53, pour les effets et les objets supplémentaires
  - `Engine_ActorWalkTo` : 36

Le placement statique des PNJ est donc des données, mais la mise en scène des cinématiques est du code.

---

## 5. `scene_*.tsv` de TLA (bloc de carte, pas overlay)

Le `map.s` de TLA a **7** blocs : metatiles, shapes, grid, shape_grid, animation, blend, scene (`games/tla/src/map/map_008/map.s`). Il n'y a pas de bloc de marqueurs et TLA n'a pas de `markers.tsv`.

Le bloc scene est `scene.parts.lz`, compressé en LZ. `scene.tsv` liste ses parties dans l'ordre : `SCENE_HEADER, SCENE_POINTS, SCENE_ENTRANCES, SCENE_PATCHES, SCENE_BOUNDS`. Il est présent dans 286 cartes.

| Fichier | Colonnes | Remarques |
|---|---|---|
| `scene_header.tsv` | `entrances:u16 patches:u16 bounds:u16 none:u16` | décalages en octets depuis le début du bloc ; les points commencent à 8. Vérifié pour les 286 : entrances = 8 + size(points), patches = entrances + size(entrances), bounds = patches + size(patches) ; `none` = 0 partout (VÉRIFIÉ) |
| `scene_points.tsv` | `id:u8 x:u16 z:u16` | se termine par `0xff` ; 579 points, identifiants surtout 1..28, 99 ×10. Signification inconnue (DÉDUIT : points de script ou de caméra ; pas des coffres, qui sont basés sur les cases dans TBS) |
| `scene_entrances.tsv` | `id:u8 x:u16 z:u16 flags:u8` | 1,970 lignes. DÉDUIT : équivalent du `SceneEntrance` de TBS (id, x, z). Le quartet bas des flags = facing>>12 (valeurs 4=S 1105×, 12=N 685×, 0=E, 8=O, 2/6/14 diagonales), et le bit 4 (16) est un drapeau supplémentaire (28, 20) |
| `scene_patches.tsv` | `key:u16 source_x:u8 source_y:u8 x:u8 y:u8 width:u8 height:u8` | se termine par `0xffff` ; **vide dans les 286** |
| `scene_bounds.tsv` | `left:s8 top:s8 right:s8 bottom:s8` | généralement une ligne + `-1`. DÉDUIT : limites de caméra en cases de 16 px (map_008 : 0,0,40,34) |

Côté overlay, les scènes de TLA ont toujours leurs Exits/Placements/Events en C (`games/tla/src/scene/<place>/data.c`). 86 des 97 tables `SceneEntrance` n'ont qu'une seule ligne, celle de repli, ce qui laisse fortement penser que le moteur de TLA prend les positions dans le bloc de carte (DÉDUIT ; le lecteur n'est pas décompilé). Un script tentant de faire correspondre les paires (scène, entrée) des sorties de TLA aux identifiants d'entrée des cartes par un décalage fixe scène→carte n'a pas été concluant, car la table des couches de TLA n'est pas dans les sources.

**TBS va-t-il migrer ?** DÉDUIT **non**, du moins pas vers les mêmes fichiers. Les cartes de la ROM de TBS ont 6 blocs avec les marqueurs, et son moteur lit les entrées dans les overlays, donc les données restent là où la ROM les place. Historique git :

- Fichiers de cartes de TLA : « TLA: the four field maps still copied, from editable tables » (a20313083f) et d'autres.
- Le travail récent sur les scènes de TBS est de l'humanisation du C (« Align scene table getters with the engine contracts », db7167f0b0).

Aucun de ces commits ne mentionne le déplacement des tables de scènes vers du TSV.

---

## 6. Ajouter une nouvelle carte ou scène (liste de contrôle)

Préférer **l'ajout en fin** à l'insertion, partout.

1. **Données de carte.**
   - Créer `src/map/map_180/` : `map.s` (`.global Field_Map180`, `map_header`, 3×`map_layer`, 6×`map_block`, incbins) et les TSV.
   - Réutiliser un jeu de tuiles existant (pas de nouvelles planches) ou ajouter des planches et une palette à sa suite.
   - Les blocs inutilisés sont `map_block Field_Map180` avec un décalage de 0. Pour les marqueurs, pointer vers `map_000/markers.table` ou vers les vôtres.
2. **objects.tsv.** Ajouter `main rom_tail_02 games/tbs/src/map/map_180/map` **avant** la ligne `system/overlay/overlays` (objects.tsv:631). Cela donne l'ordre dans la ROM ; aucune adresse n'est épinglée après 0x08320000.
3. **directory.s.** Transformer un `unused` en `resource , Field_Map180`, et en palette/tuiles si elles sont nouvelles ; réduire `unused 25` en conséquence (`:307`). Les nouveaux identifiants sont 0x3cf+ et les identifiants existants ne se décalent pas.
4. **layered.tsv.** Ajouter en fin une ligne de décalages depuis `ResourceId_Map001` : carte, palette, tuiles ×3, données de couches. Son index de ligne est la `map` de la scène. Elle est placée dans `rom_main_01`, avec de l'espace libre avant le début fixe de `rom_main_02` : EN 4,020 o, DE 1,204 o, ES/FR 1,972 o (12 o par ligne).
5. **Overlay de scène** (pour donner à la scène son propre code) :
   - `src/scene/<place>.c`, `entry/<place>.s` (6 veneers), `import/<place>.s` (imports dans l'ordre de `overlay.inc`) ;
   - prototypes dans `include/unit/scene/<place>.h` (91 existent) ;
   - lignes objects.tsv `3cf text .../entry/<place>`, `3cf text .../<place>`, `3cf text .../import/<place>`, plus un `3cf bss ...` facultatif avec une ligne d'en-tête dans `overlays.tsv` ;
   - `src/system/overlay/overlays.s` : `Resource_Overlay3CF: .incbin "overlays/resource_3cf.lz"` + `.balign 4` ;
   - répertoire : un emplacement `unused` devient `resource , Resource_Overlay3CF`.
   - Sinon, réutiliser un overlay existant comme variante, comme les salles d'Altin Peak : ajouter une ligne de scène avec le même code et faire un branchement sur `SceneId_` dans les accesseurs.
6. **scenes.s.** **Ajouter en fin** `scene NewPlace, 0x3cf, <group>, <variant>, <layered row>`. Le nouvel identifiant est 201, donc tous les identifiants numériques existants restent valides. La table est dans `rom_main_04`, 8 o par ligne ; espace libre avant la banque fixe : EN 3,448 o, DE 1,040 o. Ajouter `extern char SceneId_NewPlace;` à `include/scene_ids.h`. Le groupe doit être ≤ 0x7f (drapeau visité). Les identifiants de scène doivent être < 0x1ff (repli du mot de sortie).
7. **Connexions.**
   - Ajouter un mot de sortie dans la table des sorties de chaque voisin, sous **son** en-tête : `SCENE_EXIT(kind, 201, entrance)`.
   - Ajouter une ligne `EVENT_EXIT` (ou un script de contact) dans les événements du voisin pour le code de collision que vous peignez sur les cases de sortie.
   - Peindre ce code dans le `grid_collision.tsv` du voisin.
   - Faire de même en miroir dans la nouvelle scène : en-tête `SCENE_EXITS(201)`, ses sorties, des entrées dont les numéros correspondent à ce que nomment les mots de sortie des voisins, les placements, les événements.
8. **Règles.** Musique (`scene_cue`/`group_cue`), nom de zone (`scene_name`/`group_name`), retour après défaite (`return_to`) et décor de combat dans `src/object/scene_rules.s` ; rencontres dans `src/object/location_rules.s`. Sans ces lignes, vous obtenez MUS_018, aucun nom, aucune rencontre et le dernier décor de combat.
9. **Texte.** Ajouter les messages dans `text/<lang>.po`, avec un `msgctxt` par symbole de message.
10. **Budget** (VÉRIFIÉ, `out/tbs-*/tbs-*.map`).
    - La ROM est complétée jusqu'à 0x08800000 (Makefile:134). Espace libre à la fin : EN 11,076 o, IT 11,040, DE 10,108, ES 4,128, FR 3,584, JA 43,100.
    - Une nouvelle carte plus un overlay dépassera probablement cela, il faudra donc relever le `ROM_END_tbs` de 8 Mo. `MEMORY ROM` autorise déjà 32M (`main.ld`). Cela rend la ROM non identique. (DÉDUIT : sans danger ; non testé.)
    - RAM d'overlay ≤ 32 Ko.

---

## 7. Faisabilité de la génération de code (par table)

Règle générale : les valeurs se compilent en octets fixes, donc la mise en forme et les espaces sont libres. L'exactitude octet par octet dépend de :

- le même ordre des lignes ;
- les mêmes valeurs, y compris symboliques (`MSGNO(Msg…)` se résout en numéros de message, `EVENT_SCRIPT(fn)` en relocalisations, les noms de drapeaux depuis `flags.h`) ;
- le même `const`, qui choisit le placement en `.rodata` ou en `.data` ;
- les mêmes blocs par édition et par patch `#if TBS_PATCH_n` / `LANGUAGE` ;
- le même ordre des tables dans le fichier.

| Table | Réécriture sûre ? | Comment faire l'aller-retour |
|---|---|---|
| SceneEntrance | Oui, très régulière : 12 champs littéraux, 21 noms d'entrée symboliques | modification d'une ligne `{...}` en préservant le CST ; garder un symbole quand la valeur est inchangée |
| Exit `u32[]` | Oui, avec précaution : uniquement des macros, mais des `#define` par scène (`ROOM_ENTRANCE(exit)`, `LUNPA_EXIT_TO_*`), des en-têtes `SCENE_EXIT(0,N,0)`, `#if !TBS_PATCH_3` (vale_home.c) | analyser les appels de macros, les évaluer en mots, ne réémettre que les appels touchés ; ne jamais fusionner `SCENE_EXIT(0,..)` et `SCENE_EXITS` |
| ScenePlacement | En grande partie : `PIXELS(n)`, `FACING_X + FACING_STEP`, noms de personnages (`GARET`), symboles de scripts, 4 tables avec `#if` | modifier les champs sur place ; garder l'ordre des lignes (numéros d'acteurs) |
| SceneEvent | La plus difficile : macros de champs de bits plus environ 220 contrôles en hexadécimal brut, symboles de messages et de fonctions, 10 `#if` | traiter comme des éléments opaques sauf les champs modifiés (déclencheur, condition, valeur FIND_) |
| SceneRegion | Oui, petite : 3 avec `#if` | sur place |
| markers.tsv | Oui, fichier de données | réécrire le TSV ; décimal et hexadécimal sont tous deux acceptés |
| scenes.s / layered.tsv / directory.s | Oui, orientés lignes | ajout en fin uniquement |

Vérification :

- Reconstruire et lancer `make compare` / `compare-tbs` (Makefile:48-51).
- Pour des vérifications rapides, comparer les sections de `out/tbs-<ed>/overlays/resource_<id>.elf` avant et après une réécriture sans changement. Une simple remise en forme doit donner une sortie `.bin` et `.lz` d'overlay identique.
- Éviter de régénérer des fichiers entiers : ils contiennent du code, des régions `// clang-format off`, des commentaires et des blocs `#ifdef UBFIX`.

---

## 8. Inconnues

- Ce qui écrit `EventWork.touchedTrigger` (`include/field/event_work.h:26`), que les scripts lisent. Il n'a pas d'écrivain nommé dans le code principal (DÉDUIT : le code touché).
- Les petits entiers de `ScenePlacement.behavior` autres que 1 et 2 (3 est courant) : la sémantique de `ObjectMotion_SetActionCallback` n'est pas tracée ici.
- La table complète des types de sprites (les identifiants d'objet 20 = coffre, 28 = pierre et 0x8000 = caméra sont VÉRIFIÉS d'après markers.c et actors.c).
- TLA : la signification de `scene_points`, du bit 4 de `scene_entrances.flags`, les unités des limites, la résolution scène→carte, et la 6e colonne de la table des scènes (également XXX dans `games/tla/src/field/README.md`).
- Si les emplacements `unused` du répertoire et une ROM de plus de 8 Mo fonctionnent sur le matériel et les émulateurs (DÉDUIT oui).
- La scène 59 (sans nom, 0x39d) n'a pas d'en-tête de sorties. Les sorties y laissent la scène inchangée (`Scene_TakeExit` conserve l'état quand aucun en-tête n'est trouvé).

---

## 9. Modèle de données proposé pour l'éditeur

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

Opérations d'édition :

- **Déplacer une case de sortie :** code de grid_collision plus la ligne `EVENT_EXIT`.
- **Changer la destination :** modifier le mot de sortie.
- **Ajouter un coffre :** ligne de marqueur, code de collision, et un événement `SEARCH(SEARCH_CHEST)` avec un nouveau drapeau ≥ 0xe00.
- **Déplacer un PNJ :** modifier x/z du placement, et avertir si le x=z=0 de la ligne signifie que le code le positionne.

Valider sur l'ensemble de ces opérations :

- les numéros d'entrée référencés par chaque mot de sortie existent dans les Entrances de la cible (sinon c'est le repli sur la ligne 0) ;
- les décalages de numéros d'acteurs quand des lignes de placement sont insérées ;
- la limite de 10 marqueurs ;
- les budgets de 32 Ko d'overlay et de ROM.

---
