<!-- translated from docs/research/rendering.md @ 5cc75b0f23d8 -->
# Recherche sur le rendu : couches, mélange, animation des tuiles, emplacements réservés

*Ceci est une traduction du document anglais [rendering.md](../../research/rendering.md) ; en cas de différence, c'est la version anglaise qui fait foi.*

Source : alchemy (`games/tbs/...`). Les chemins sont relatifs à `games/tbs/` sauf indication contraire.
VÉRIFIÉ signifie que l'affirmation a été lue dans le code du moteur et confirmée par un rendu. DÉDUIT signifie qu'il s'agit d'une supposition raisonnée.
Les scripts et rendus de travail se trouvent dans
`(a scratch folder)`
(`r2.py` est le moteur de rendu de référence, `dirmap.py` résout la table des ressources de scène).

## Résumé

Les cartes « brouillées » ne sont pas causées par la parallaxe. Trois bogues du visualiseur en sont la cause, et deux d'entre eux touchent presque toutes les cartes :

1. **Les cases réservées (0xfff) sont de vrais graphismes.** Au chargement, la k-ième case 0xfff, comptée ligne par ligne sur toute la grille 128×128, devient le bloc k. Dans **les 182 cartes**, le nombre de cases réservées est exactement le nombre de lignes de `metatiles.tsv`. La table des blocs est en fait « les blocs uniques dans l'ordre de lecture », et les valeurs de case explicites les réutilisent. Dessiner les cases réservées comme vides fait disparaître la plus grande partie de chaque carte. (VÉRIFIÉ)
2. **Le jeu de tuiles vient de la mauvaise table.** Le jeu charge la palette d'une carte, ses trois planches VRAM et sa planche D depuis `src/field/layered.tsv` (`gMap_LayeredScenes`), et non selon l'ordre de `directory.s`. **117 des 182 cartes** utilisent une combinaison de palette ou de planches différente de celle que suppose le visualiseur. Exemples : le bloc de caractères 3 de la carte 034 est `Set02TilesC` et sa planche D est `Set26TilesC`. VenusEntrance utilise les planches `Set07` avec `Palette49`. (VÉRIFIÉ)
3. **Les limites de l'en-tête ne sont que les limites de caméra par défaut.** La table des entrées d'une scène peut les remplacer. La carte 034 (scène Bilibin3) est limitée à 16..400 px par ses entrées. En dehors de cette plage, la zone d'en-tête de 128×128 tuiles est du remplissage de grille (bloc 3), jamais vu en jeu. (VÉRIFIÉ)

La parallaxe et la dérive n'existent que sur 8 cartes (047, 103, 104, 147, 148 ; sur 090/091/092/169, les masques n'ont aucun effet car la vitesse vaut 0). Le mélange est BLDCNT/BLDALPHA, réglé par un petit script. La première cible est presque toujours la couche 2 (BG1), parfois la couche 1 (BG2). L'animation des tuiles consiste en copies DMA de tuiles de la planche D vers la VRAM. Ces quatre mécanismes ont été implémentés dans `r2.py` et vérifiés par rendu.

## (a) Couches, fenêtres et défilement

**Structures.** `struct LayeredSceneLayer {u8 x, y; s8 scrollX, scrollY, speedX, speedY; u8 periodX, periodY;}` se trouve dans `src/field/field/map_layers.c:172-181`. L'ordre de la macro `map_layer` est le même : x, y, rate_x, rate_y, drift_x, drift_y, period_x, period_y (`src/map/map.inc`).

**Chargement** (`map_layers.c:274-303`, VÉRIFIÉ) :
- `offset = x<<19` et `y<<19`, donc l'origine est x×8 px en virgule fixe 16.16.
- `scale = scroll*4096`, donc rate/16 de la vue.
- `speed = speed*4096`, donc speed/16 px par image.
- `mask = period`.
- `phase = 0`.

**À chaque image** (`Map_UpdateLayerScroll`, `map_layers.c:474-566` ; idem dans `Map_SetCameraCenter` 572-630, VÉRIFIÉ) :
```
view   = followed point - focus, clamped to [min, max - 240x160]        (min/max = header bounds*8 px, or scene overrides)
base   = view * scale            (Q16 multiply → view * rate/16)
if speed: phase += speed; base = (base + phase) & ((period<<19) | 0x7ffff)   # wrap; only applied when speed != 0
pos    = base + offset           # layer's top-left in grid pixels
BG(3-li) scroll = pos
```
Le dessin lit les cases à `((pos/16) & 0x7f)` sur les deux axes (`Map_RenderMetatileRow/Column`, 411-462). Donc **une fenêtre de couche boucle modulo 128 cases (2048 px)**. Taille de la fenêtre = l'écran ; il n'y a pas de taille de fenêtre par couche.
La couche li est affichée sur BG(3-li), avec la priorité BGCNT = l'octet de priorité de l'en-tête, la base des caractères = l'octet de caractères de l'en-tête, et la base d'écran 5+li (314-322).

**Limites de la caméra.** `work->min/max = header bounds << 19` (261-264). `Scene_ApplyEntrance` (`src/object/object/run_scene.c:488-499`) remplace chacun de minX/minY/maxX/maxY, en pixels, lorsque `cameraLeft/Top/Right/Bottom != -1` dans l'entrée (`struct SceneEntrance`, `include/field_scene.h`). Carte 034 = scène `Bilibin3` (`src/field/scenes.s:50`, index de carte 0x24). Ses entrées 1 et 2 utilisent les limites 16,16,400,400 (`src/scene/bilibin.c:780-785`). Quelques scènes écrivent aussi les limites directement (`tolbi_ship_deck.c:1062`, `vale_babi.c:418-421`, `psynergy_effects/view.c:16`).

**Cartes avec des paramètres de couche non standard** (tout le reste est `16,16,0,0,255,255`) :

| carte | couche | paramètres | signification |
|---|---|---|---|
| 047 | 0 | rate 8,8 | parallaxe à mi-vitesse |
| 103 | 0 | drift_y −25, period 255 | l'arrière-plan défile vers le haut à 25/16 px/image, boucle à 2048 px |
| 104 | 0 à y=92 | rate 6,6 | parallaxe ciel/mer (scène du mât du navire) |
| 147, 148 | 2 | rate 20,20, drift −121/16, 35/16 px/image, period 31 | surcouche de tempête de sable, boucle tous les 256 px |
| 090-092 (couches 0,1), 169 (couche 0) | | period 127/63, speed 0 | aucun effet (le masque ne sert que si speed ≠ 0) |

**Ordre de priorité (GBA, VÉRIFIÉ par rendu).** Dessiner de l'arrière vers l'avant, trié par `(-priority, layer index)`. À priorité égale, le BG de plus petit numéro est au-dessus, donc la couche 2 (BG1) est au-dessus de la couche 0 (BG3). Le `sorted(key=-priority)` du visualiseur actuel est stable, il donne donc déjà le même résultat. Priorité 0 = désactivée.

**Règle de rendu pour un visualiseur Python :**
- *Couches de terrain* (rate 16, speed 0) : `grid_px = (origin_px + map_px) mod 2048`, où `map_px` est mesuré depuis (0,0) de l'espace de la grille, et non depuis bounds.left. C'est exact pour toute caméra. L'actuel `render_layer` se comporte ainsi pour left=top=0, mais il ne boucle pas modulo 128 cases et ignore un bounds.left/top non nul.
  - Forme correcte : `gx = (x*8/16 + bounds.left/2 + i) % 128` pour la colonne d'écran i de la fenêtre des limites, et de même pour y.
- *Couches à parallaxe/dérive* : elles n'ont pas d'image statique unique. Règle recommandée pour la vue de carte : ancrer au milieu de la plage de la caméra.
  - `V = ((min + max(min, max-240))/2, same for y)` et `pos = layer_pos(V) + (map_px - V)`.
  - C'est exact pour la caméra en V et continu ailleurs. Phase de dérive = 0 (ou speed×images).
  - Proposer aussi un « aperçu caméra » de 240×160 qui utilise exactement `layer_pos(view)`.
- *Recadrer* sur les limites de caméra de la scène quand elles sont connues ; sinon utiliser les limites de l'en-tête.

## (b) Mélange

**Mécanisme** (`src/field/field/map_animation.c:163-255`, VÉRIFIÉ) :
- `blend.tsv` se compile en demi-mots : `control v` → v (une valeur BLDCNT, reconnue à son quartet supérieur 3) ; `level v wait` → v, wait ; `jump n` → 0xfe00|n (curseur = script + 2n demi-mots) ; `stop` → 0xfeff ; `end` → 0xffff (retour au début).
- Sur un `level` :
  - si les bits d'effet (7..6) du dernier BLDCNT valent 01, alors `REG_BLDALPHA = v` ;
  - sinon `REG_BLDY = v` ;
  - puis attendre `wait` images.
- Un script qui ne contient que `end` n'installe rien (`DisplayBlend_StartScript` 246).
- Le chargeur règle d'abord `REG_BLDCNT = 0` (`map_layers.c:365-367`).

**Sémantique GBA :**
- Les bits 0-5 de BLDCNT sont la 1re cible (bit0 BG0, bit1 BG1 = couche 2, bit2 BG2 = couche 1, bit3 BG3 = couche 0, bit4 OBJ, bit5 fond).
- Les bits 6-7 sont l'effet (1 alpha, 2 éclaircir, 3 assombrir).
- Les bits 8-13 sont la 2e cible.
- BLDALPHA : EVA = bits 0-4 (poids de la couche cible 1), EVB = bits 8-12 (poids de ce qui est dessous), chacun plafonné à 16.
- `out = min(31, (top*EVA + below*EVB) >> 4)` par canal de 5 bits.
- BLDY : `I + (31-I)*Y/16` (éclaircir) ou `I - I*Y/16` (assombrir).

**Valeurs trouvées dans les cartes de TBS** (premier `level` après `control`) :

| BLDCNT | couche cible | effet | cartes (exemples) |
|---|---|---|---|
| 0x3f42 | couche 2 (BG1) par-dessus tout | alpha | 005-007/032/076 (0x1006 : 6/16 + 16/16 additif), 021, 022-024/136/137, 025-027/077-085 (0xa09 : 9/16 + 10/16 = l'eau de 080), 029, 033/040/062/115/144 (0x1003 lueur, animée 3-4), 047 (0xc04), 053, 054-058/109/155/156/163, 063-067/100, 073, 075, 108, 113, 133, 139-142 (0xb0e), 154, 164-167 |
| 0x3f44 | couche 1 (BG2) | alpha | 009/145/146, 010/019, 012/013/016, 014/015, 018/038/052/094/095/099/102/120/121/151/160/161 (0x1008), 061, 086, 105, 124 |
| 0x3fc8 | couche 0 (BG3) | assombrir, BLDY 3-6 | 046 |
| (aucun) | — | BLDY seul, sans effet | 039/042/043, 114, 125 : le script écrit des niveaux avec BLDCNT=0. Une scène doit régler BLDCNT (DÉDUIT) |
| `end` seul | — | — | 36 cartes (020, 028, 031, 036, 037, 048, 051, 060, 072, 074, 089, 093, … dont 134 via `map_020/blend`) |

La plupart des niveaux avec EVB=16 sont une **lueur additive** (rais de lumière, torches). Une attente de 43210 signifie que le niveau est constant.

**Mélanges réglés par la scène** (absents de `blend.tsv` ; VÉRIFIÉ dans le code) :
- `src/scene/altmiller_cave.c:195-222, 313-320` : BLDCNT 0x3f42 avec BLDALPHA 0x1000..0x600, ou 0xc04. La carte 134 = scène AltmillerCave5 (`scenes.s:165`) a sa couche d'obscurité mélangée de cette façon.
- Également `tret_tree_branch.c:163` (BG1 4/12), `tolbi_spring.c`, `vale_babi.c`, `mercury_lighthouse*.c`, `crossbone_isle_platform_rooms.c`, `lemurian_ship.c`.

**Règle de rendu :**
- Analyser le script de mélange et prendre le BLDCNT et le premier niveau, ou le simuler jusqu'à l'image t.
- Pour chaque couche dessinée de l'arrière vers l'avant : si son bit BG est dans target1 et effect==1, `rgb = min(31,(layer*EVA + below*EVB)>>4)` là où la couche est opaque. « Dessous » est la couleur déjà composée (ou le fond) ; tous les control de TBS utilisent la 2e cible 0x3f.
- Pour les effets 2/3, appliquer BLDY aux pixels de cette couche.
- Utiliser la couleur sur 5 bits (valeur PNG >> 3) pour des résultats exacts.
- Éventuellement, garder une petite table de surcharges par carte pour les mélanges réglés par la scène (134 → 0x3f42/0xc04).

## (c) Animation des tuiles

**Mécanisme** (`src/field/field/map_animation.c:7-145`, VÉRIFIÉ) :
- `animation.tsv` se compile en demi-mots : `channel n` → 0xfd00|n, `frame src cnt dst wait` → 4 demi-mots, `jump n` → 0xfe00|n, `stop` → 0xfeff, `end` → 0xffff.
- `MapAnimation_StartChannels` parcourt le flux. Chaque 0xfdNN démarre le canal NN&15 au demi-mot suivant, en pause si le bit 7 est mis (`channel 0x8N` ; une scène le relance via `Map_ClearLayerEntryFlag`).
- À chaque image, pour chaque canal non en pause :
  - si timer>0 : timer−− et passer au canal suivant.
  - sinon exécuter au curseur :
    - 0xffff → curseur = début
    - 0xfeNN → curseur = début + 2·NN demi-mots
    - 0xfeff → rester arrêté
    - sinon copier `cnt` tuiles, régler timer = wait, curseur += 4, et reboucler dans la même image.
  - Donc **une copie avec une attente W reste à l'écran pendant W images**, et W=0 enchaîne sur la copie suivante dans la même image.
- Copie (4bpp, `wideTiles==0`), en tuiles de 32 octets comptées depuis le **bloc de caractères 1** :
  - `src >= 0x600` : depuis `Ram_DecodeBuffer (0x0201c000) + src*32`, c'est-à-dire `gMapLayerData` (0x02028000, `src/system/ewram.s:236-244`, `include/ram_buffer.h`) + (src−0x600)*32. C'est **la tuile src−0x600 de la planche D** (planche D = colonne 5 de `layered.tsv`, décodée dans gMapLayerData à `map_layers.c:357-359`).
  - `src < 0x600` : depuis la tuile VRAM `512+src` (absolue, depuis le bloc 0).
  - Destination : tuile VRAM absolue `512+dst`.
- La tuile absolue d'une entrée de carte est `charBase*512 + (entry & 0x3ff)`.

**Comment produire l'image t :**
1. VRAM de départ : blocs 1/2/3 depuis les colonnes 2/3/4 de `layered.tsv`, et planche D depuis la colonne 5.
2. Construire les canaux comme ci-dessus ; ignorer les canaux en pause (`channel 0x8N`).
3. Exécuter la mise à jour t+1 fois, en modifiant un tableau de tuiles VRAM.
4. Puis faire le rendu normalement avec les tuiles modifiées.

Les boucles sont courtes (le cycle de l'eau de 34 dure 24 images ; 127 saute après 10+10 images). Un GIF/aperçu peut avancer de 1..N images. L'atlas des métatuiles doit être reconstruit à chaque image, ou mieux, mis en cache par tuile.

## (d) Emplacements réservés 0xfff

**Mécanisme** (VÉRIFIÉ) :
- `Tilemap_ConvertBuffer` (`src/field/field/map_layers.c:110-122`) exécute `Tile_ConvertMap` (`src/graphics/tile/convert_map.s:8-50`) sur le plan des blocs.
- r5 = 0xFFF00000 teste `(cell<<20) == 0xfff<<20`.
- r4 commence à 0xFFFFF001 ; `cell + r4` (tronqué à 16 bits) = `(cell & 0xf000) | k`, et r4 s'incrémente à chaque case réservée.
- Le jumeau C inutilisé `Tilemap_NumberPlaceholderBlocks` (84-103) fait la même chose.
- Résultat : **la k-ième case (à partir de 0, ligne par ligne sur les 128×128 cases, toutes couches confondues) dont les 12 bits de poids faible valent 0xfff devient le bloc k. Son quartet supérieur est conservé.**
- Le dessin utilise ensuite `Ram_MapBlocks[(cell<<20)>>19]` (12 bits de poids faible seulement, 411-437).

**Validation.** Pour chacune des 182 cartes, le nombre de cases réservées est égal au nombre de lignes de `metatiles.tsv` (`allph.py`). Les rendus de 034 et de VenusEntrance deviennent des graphismes cohérents (voir plus bas). Les cases réservées ne sont donc pas remplies par du code inconnu : ce sont les blocs uniques de la carte dans l'ordre de lecture. On peut répondre au `XXX` de `src/map/README.md`. (Seules les cases qui valent exactement 0xfff au chargement sont comptées ; les copies de cases à l'exécution `Map_CopyMetatileIndicesRect` ont lieu plus tard.)

**Règle :** avant le rendu, `n=0; for y in 0..127: for x in 0..127: if cell&0xfff==0xfff: cell=(cell&0xf000)|n; n+=1`.
Pour un éditeur, cela a des conséquences :
- Peindre une case vers ou depuis 0xfff renumérote toutes les cases réservées suivantes.
- L'édition doit garder le nombre de cases réservées égal au nombre de blocs, sinon les blocs stockés se décalent.
- Afficher le numéro de bloc résolu et, à l'enregistrement, ne stocker 0xfff que là où `resolved == running count`. Sinon, garder les cases telles quelles et traiter 0xfff comme « bloc unique suivant ».

## Rendus validés

Tous dans `(a scratch folder)` :
- `cur_034.png`, `cur_VenusEntrance.png` : le visualiseur actuel (cassé).
- `ph_034.png`, `ph_VenusEntrance.png` : correction des cases réservées seulement (034 cohérente ; Venus toujours avec le mauvais jeu de tuiles).
- `new_034.png` : toutes les corrections. Rivière/forêt cohérente dans les cases 1..25. Le reste est du remplissage hors caméra.
- `new_VenusEntrance.png` : toutes les corrections. Forêt et entrée du Venus Lighthouse correctes.
- `new_040.png` contre `new_040_noblend.png` : lueur de torche additive (0x3f42, 0x1003).
- `new_080.png` contre `_noblend` : eau mélangée 9/16 + 10/16.
- `new_016.png` : salles du Sol Sanctum, 0x3f44 sur la couche 1.
- `new_134.png` : obscurité opaque. `new_134_sceneblend.png` : avec le 0x3f42/0xc04 d'Altmiller, obscurité à 4/16.
- `new_104.png` (ancrage au milieu de la caméra), `cam_104_0_0.png`, `cam_104_128_208.png` : ciel en parallaxe.
- `new_147.png` : surcouche de sable en dérive.
- `new_047.png`, `new_103.png`.
- `anim_034_f00..f40.png`, `anim_034.gif`, `anim_034_compare.png` : les images 0 et 24 de l'animation de l'eau diffèrent.

## Modifications exactes recommandées pour gsmap/project.py

1. **Ressources de scène** (remplacer l'appariement de `_read_directory`) :
   - Développer `directory.s` en une liste ordonnée d'entrées. Appliquer exactement les macros : `group K, a,b` → `K_a, K_b` ; `area S, L, maps` → `Field_MapNN…, Tileset_SPalette, Tileset_STiles<L…>` ; `recolor P, maps` → `Field_MapNN…, Tileset_PaletteP` ; `overlays` ; `unused N` → N entrées ; `resource , X` → X.
   - Fixer `base = index('Field_Map001')`.
   - Chaque ligne de `src/field/layered.tsv` est `[header, palette, blk1, blk2, blk3, sheetD]` ; faire correspondre chacune à `entries[base+v]`.
   - Indexer par l'étiquette d'en-tête (`Field_MapNNN` / `Field_<Name>`), et utiliser la première ligne. Les cartes 108 et 110 ont deux lignes avec des palettes différentes (45/58 et 15/18). Exposer l'alternative.
   - Résoudre les étiquettes via le `self.symbols` existant. Implémentation de référence : `dirmap.py`.
2. **Atlas :** tuile absolue `a = char_base*512 + (e&0x3ff)`.
   - Bloc `a//512` 1..3 → `[blk1, blk2, blk3][a//512-1]`. Le bloc 0 = tuiles de fenêtre, donc l'ignorer. 4 et plus est invalide.
   - Les lignes de palette 14/15 ne sont pas celles de la carte (interface). Les afficher transparentes ou dans une couleur de débogage.
3. **Cases réservées :** résoudre 0xfff → ordinal courant (règle en d) dans `load_grid` pour le rendu. Supprimer le test `== EMPTY → skip`. Garder la grille brute pour l'enregistrement.
4. **Fenêtres :** `gx = (layer.x//2 + bounds.left//2 + i) % 128`, et de même pour y (boucler, ne pas ignorer). Pour les couches avec rate≠16 ou drift≠0, utiliser la règle d'ancrage au milieu de la caméra de (a).
5. **Mélange :** analyser blend.tsv (`control`/`level`/`jump`/`stop`/`end`). Composer de l'arrière vers l'avant avec les formules BLDCNT/BLDALPHA/BLDY de (b). Régler par défaut le curseur d'opacité de la couche à EVA/16 seulement à titre d'approximation (le résultat exact est additif : `top*EVA + below*EVB`).
6. **Animation :** garder un tableau de tuiles modifiable `vram[2048]` plus `sheetD[512]`. Faire avancer les canaux selon (c). Exposer un numéro d'image ou une commande de lecture.
7. **Limites de la caméra (facultatif) :** par défaut, les limites de l'en-tête. Proposer « recadrer sur le contenu » ou les limites des entrées de la scène. Scène → index de carte provient de `src/field/scenes.s` (`scene name, code, area, kind, map`, où map = la ligne de `layered.tsv`). Les limites se trouvent dans les tables `struct SceneEntrance` de `src/scene/*.c`.

## Inconnues

- Comment fonctionnent les mélanges des cartes dont le script n'a pas de `control` (039/042/043/114/125). DÉDUIT : une scène règle BLDCNT ; non tracé.
- Mélanges réglés par la scène et reprises d'animation (`channel 0x8N`) par carte : seul Altmiller (134) a été tracé.
- Quelle ligne de `layered.tsv` une scène utilise quand une carte en a deux (108, 110). Les deux palettes sont valides.
- Pourquoi seule la dérive verticale remplit les 32 lignes BG (`map_layers.c:600-604`, un XXX d'alchemy). Sans importance pour un rendu statique.
- Les limites de caméra des cartes autres que 034 n'ont pas été tabulées. `scenes.s` + les tables d'entrées les donneraient.
- Seule la branche de l'édition EN a été vérifiée ; `layered.tsv` n'a pas de variantes par édition.
