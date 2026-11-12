<!-- translated from docs/research/overworld.md @ 52c37110966a -->
# Recherche sur la carte du monde : Golden Sun TBS, d'après les sources d'alchemy

*Ceci est une traduction du document anglais [overworld.md](../../research/overworld.md) ; en cas de différence, c'est la version anglaise qui fait foi.*

Arborescence source : `~/gs_project/alchemy` (lecture seule). Les chemins ci-dessous sont relatifs à
`games/tbs/` sauf s'ils commencent par `games/` ou `tools/`. Étiquettes : **[V]** = VÉRIFIÉ (lu dans le code ou les données,
ou confirmé par le rendu du prototype), **[I]** = DÉDUIT.

Scripts et rendus du prototype (travail temporaire, hors de ce dépôt) :
`(a scratch folder)`
(`render_world.py`, `render_area.py`, `render_gameplay.py`, `world_mixed.png`, `world_annotated.png`, `collision.png`, `terrain_kind.png`, `north_compare.png`).

## Résumé

1. Tout le sol de la carte du monde est une seule table : `src/map/world/blocks.tsv`, 320 lignes x 512 colonnes de **mots de case** u32 en hexadécimal, construite par `tools/ags-graphics` (forme `blocks`) en `blocks.blocks`, que `src/map/map.s` inclut par incbin sous le nom `Field_PerspectiveDataA` [V].
2. La table contient 640 **morceaux** de 16x16 cases (le code appelle un morceau une « tile »). Les morceaux 0-319 sont la couche 0 (BG3, sol), 320-639 la couche 1 (BG2, surcouche : montagnes, arbres, côtes), avec morceau de couche 1 = morceau de couche 0 + 320 [V].
3. Le monde fait 16x16 morceaux = 256x256 cases ; une case vaut 32 pixels du monde (16 pixels écran/BG), donc le monde fait 8192x8192 px du monde et boucle [V]. Les identifiants de morceau 0-255 se placent au morceau du monde (id%16, id//16) ; 256-319 sont des variantes substituées par le code [V].
4. Un mot de case : bits 0-15 identifiant de bloc, bits 16-23 code de pas/d'événement, bits 24-30 type de terrain (région de rencontres ; 21 = jeu graphique de neige), bit 31 indicateur de banque de comportement [V].
5. Un identifiant de bloc indexe `src/map/default/cells.tsv` (4386 blocs de 4 octets : numéros de tuiles 8x8 HG, HD, BG, BD) [V]. Les tuiles sont en 8bpp, 256 par couche : jeu A = `tiles_a+b` (couche 0) et `tiles_c+d` (couche 1), palette `palette_a.png` (224 couleurs) ; jeu B (neige) = `tiles_f..i`, `palette_b` [V].
6. Le rendu est en mode 2 (BG2+BG3 affines) avec des matrices par ligne de balayage via DMA HBlank pour la perspective « mode 7 » ; un rendu plat vu de dessus n'a besoin de rien de tout cela. Le prototype rend correctement la carte entière de 4096x4096 pixels BG [V].
7. La praticabilité se définit par tuile graphique 8x8, et non par case : `default/attributes.tsv` donne à chaque tuile une grille 4x4 de valeurs de collision sur 4 bits (la couche supérieure l'emporte sur l'inférieure ; 0 = aucune ; défaut 7) ; 5-12 sont praticables [V].
8. Rencontres aléatoires : type de terrain (bits 24-30 de la case) + comportement du terrain (d'après la valeur de collision, banque d'après le bit 31 / type 21) -> `gWorldMap_EncounterRules` (`src/object/zonedata.c`) -> ligne de zone de `src/object/encounter.tsv` [V].
9. Les villes/donjons sont des acteurs placés (sprites d'icône) dans `gWorldMapPlacements` (`src/scene/world_map.c`) ; toucher l'acteur N déclenche 100+N, associé à un `EVENT_EXIT` dans `gWorldMapEvents` -> numéro de sortie -> `gWorldMapExits` -> (scène, entrée). Certaines entrées sont à la place des codes de pas de case (bits 16-23) [V]. Quitter une ville utilise la table de sorties de cette ville `SCENE_EXIT(n, 2, e)` -> position `gWorldMapEntrances[e]` [V].
10. Aucune variante par édition des données de la carte du monde dans TBS ; les adresses de début de la fin de ROM diffèrent selon l'édition, et toute modification casse la correspondance octet par octet « compare OK » [V].

## Fichiers et formats

| Données | Fichier(s) source | Format | Construit sous / relié par |
| --- | --- | --- | --- |
| Cases du sol, les deux couches | `src/map/world/blocks.tsv` | Pas d'en-tête. 320 lignes x 512 éléments séparés par des tabulations ; chaque élément en hexadécimal minuscule sans `0x`, sans zéros de tête (`0`, `1b`, `9500014a`), fins de ligne LF, LF final [V]. Lu par `blocks()` dans `tools/ags-graphics/tables.c:235-282` : le nombre de lignes doit être un multiple de 16, toutes les lignes de même largeur (multiple de 16) [V]. Un groupe 16x16 peut être entièrement `-` (omis, décalage 0) mais jamais en partie [V ; TBS n'en a aucun, TLA en a 969]. | `blocks.blocks` : table de décalages de 640 x u32, puis les 256 mots u32 de chaque morceau (1024 octets) compressés séparément avec le type LZ `plz` (`tables.c:262-276`) [V]. `src/map/map.s:1-4` `.incbin` sous `Field_PerspectiveDataA`, suivi de `.byte 0x01 @ PACKER` [V]. Entrée de répertoire `group Field, PerspectiveDataA, ...` à `src/system/resource/directory.s:123` [V]. |
| Numérotation des morceaux dans le TSV | idem | Le morceau `i` occupe les lignes TSV `(i//32)*16..+15`, colonnes `(i%32)*16..+15` (morceaux disposés sur 32 de large, ligne par ligne) [V : `tables.c:257`]. Ce n'est PAS la disposition du monde : le monde fait 16 morceaux de large, donc une ligne de morceaux du TSV contient deux lignes de morceaux du monde côte à côte [V par rendu]. | |
| Blocs (métatuiles) | `src/map/default/cells.tsv` | En-tête `cell0:u8 ... cell15:u8` ; valeurs `0x6b` ; 1097 lignes, dernière ligne courte (8 valeurs) = 17544 octets = 4386 blocs x 4 octets [V]. Bloc b = octets `4b..4b+3` = numéro de tuile haut-gauche, haut-droite, bas-gauche, bas-droite (u8) [V : `src/field/field/world_map.c:71-91`, `444-451`]. Partagé par les deux couches ; la couche sélectionne la banque de tuiles. | `cells.table.lz` ; `map.s:5-7` sous `Field_DefaultMapCells` (+1 octet PACKER) ; décodé dans `Ram_MapCellBuffer` (`gMapCellBuffer`, 0xc000 octets, `src/system/ewram.s:223-226`) par `world_map.c:158-160` [V]. La même table sert aussi de « cases par défaut » aux cartes en couches (README `src/map/README.md` ligne `default/`). |
| Collision des tuiles | `src/map/default/attributes.tsv` | En-tête `attr0:u8..attr15:u8` ; 256 lignes = 4096 octets [V]. Octets 0x000-0x7ff : tuiles 0-255 de la couche inférieure (BG3), 8 octets chacune ; 0x800-0xfff : tuiles 0-255 de la couche supérieure (BG2) [V : `src/field/field/terrain.c:535-580`]. Par tuile : 4 lignes x 2 octets ; chaque octet contient deux valeurs de 4 bits, quartet bas = gauche ; une valeur = 2x2 px BG (4x4 px du monde). | `attributes.table.lz`, `map.s:11-13` `Field_DefaultMetatileAttributes` ; décodé dans `Ram_MapCollision` (`world_map.c:161-163`) [V]. |
| Animation des tuiles | `src/map/default/animation.tsv` | En-tête `word0:u16..word7:u16`, 465 demi-mots ; script de canaux (`0xfdNN` canal, groupes tuile source/nombre/tuile destination/images, `0xfeNN` saut, `0xfeff` arrêt, `0xffff` boucle) [V : `src/field/field/map_animation.c:7-13`]. Les tuiles sources >= 0x600 viennent de `gMapLayerData` (= `tiles_e`/`tiles_j`) [V : `map_animation.c:57-61`]. | `animation.table.lz`, `map.s:8-10` ; décodé dans `Ram_MapCollision+0x1000` et démarré (`world_map.c:149-152`) [V]. |
| Graphismes des tuiles | `src/graphics/world_map/tiles_{a..j}.png` | PNG indexé, valeur de pixel = index de couleur 8bpp brut, palette PNG = `palette_*.png` [V]. a-d, f-i : 128x64 (128 tuiles chacune) ; e, j : 128x128 (256 tuiles, source d'animation) [V]. | `tiles_X.8bpp.lz`, `src/graphics/world_map/worldmap.s` (chacun suivi d'octets PACKER) [V]. Répertoire `directory.s:124-135` (`WorldMapPaletteA`, `WorldMapTilesA..J`) [V]. |
| Palettes | `palette_a.png`, `palette_b.png` | PNG indexé 16x14 = 224 couleurs [V]. Chargées dans la palette BG 0-223, couleur 0 remplacée par le fond courant (`world_map.c:331-335`) [V]. | `.gbapal.plz` (`worldmap.s:4`, `:26`) [V]. |
| Table des jeux graphiques | `src/field/world_map_resources.c:11-28` | `gWorldMap_GraphicsResources[2][6]` = {palette, tuiles x5} pour le jeu A (A..E) et le jeu B (F..J) [V]. | C. |
| Règles de rencontres par terrain | `src/object/zonedata.c:7-15` | `gWorldMap_EncounterRules[132]` s16 : 32 règles {type, comportement (-1 n'importe lequel), drapeau (-1 aucun / règle désactivée une fois mis), zone} + terminateur type -1 [V]. | C. |
| Zones de rencontres | `src/object/encounter.tsv` | En-tête `rate:u16 level:u16 group0..7:u16 weight0..7:u8 zone` (la dernière colonne est une étiquette, non encodée) ; 104 zones [V]. | `encounter.table`, `src/object/arcspark.s:10-13` [V]. |
| Comportement du terrain | `src/field/mapdata.c:37-41` | `gWorldMap_TerrainBehaviorTable[48]` u8, index = valeur de collision + banque (0x10 si bit 31 de la case, 0x20 si type 21) [V]. | C. |
| Tables de scène | `src/scene/world_map.c` | `gWorldMapEntrances` (`:2717`), `gWorldMapExits` (`:2802`), `gWorldMapPlacements` (`:2863`) + variantes selon l'histoire (`:2966-3058`), `gWorldMapEvents` (`:3060`) [V]. Formats dans `include/field_scene.h:54-150` [V]. | Overlay de la carte du monde 0x371 (`objects.tsv:640-644`), lié à 0x2008000, limite de 32 Ko (`src/scene/README.md` Limits) [V]. |
| Marqueurs de la carte de l'écran de pause | `src/object/scripts.s:340-383` | `gWorldMap_PlaceMarkers` : paires {tile<<16 \| flag, nom de lieu} ; la ligne i décrit l'acteur 11+i ; les lignes à 0 réservent un acteur ; -1 termine [V : `src/object/psynergy_effects/world_map.c:282-323`]. | asm `.4byte`. |
| Image de l'écran de pause | `src/graphics/world_map/picture.png` | 240x160 8bpp, couvre x du monde 4096-8192, z 0-4096 [V : `psynergy_effects/world_map.c:10-11, 318-322`]. Dessinée à la main, non générée à partir des blocs [I]. | `src/graphics/title/title.s:68-71` `Field_WorldMapPicture` [V]. |
| Images de l'histoire | `src/graphics/world_map/story.png`, `storymap.tsv`, `storypal.png` | Graphismes des inserts narratifs dans l'overlay de la carte du monde [V : `story.s`]. Pas des données de sol. | `story.s`, objet d'overlay `objects.tsv:643` [V]. |

Identifiant de scène de la carte du monde : `scene WorldMap, 0x371, 0x02, 1, 0x01` est la scène 2 (`src/field/scenes.s:17`) ; identifiant de scène = index de ligne de `gField_SceneTable` (`scenes.s:1-5`) [V]. Son index de carte 1 est égal à `SceneId_Clear`, ce qui sélectionne le mode perspective dans `Field_RunScene` (`src/object/object/run_scene.c:45-49`) [V].

## Rendu

Hiérarchie (TBS) [V] :

```
world (wraps)  16 x 16 chunks                      8192 x 8192 world px, 4096 x 4096 BG px
chunk          16 x 16 cells   (code: "tile")      512 world px, 256 BG px; 1 KB decoded
cell           u32 word, low 16 bits = block id    32 world px, 16 BG px
block          2 x 2 tiles (4 bytes in cells.tsv)  
tile           8 x 8, 8bpp, from bank per layer    16 world px, 8 BG px
```

- **Affichage** : `Map_InitializePerspectiveScene` (`world_map.c:112-264`) règle BG3 = base de caractères 2, base d'écran 8 ; BG2 = base de caractères 3, base d'écran 10 ; tous deux affines de 512x512 px, qui bouclent (`:164-174`) ; BG1 couche de texte pour la vue fixe ; `DISPCNT_MODE_2` (`:249`) [V]. BG2 est dessiné par-dessus BG3, couleur 0 transparente (commentaire `view.c:66-69` : BG2 laisse voir BG3 là où il est transparent) [V].
- **Banques de tuiles** : tiles[1] du jeu (A) -> bloc de caractères 2, tiles[2] (B) -> bloc 2 + 0x2000, tiles[3] (C) -> bloc de caractères 3, tiles[4] (D) -> bloc 3 + 0x2000, tiles[5] (E) -> `gMapLayerData` (`world_map.c:336-352`) [V]. Donc les numéros de tuiles 0-127 de la couche 0 = `tiles_a`, 128-255 = `tiles_b` ; couche 1 : `tiles_c`, `tiles_d` [V par rendu].
- **Chargement progressif** : les cartes BG contiennent une fenêtre de 2x2 morceaux autour du joueur. `perspective->tileIds[256]` associe chaque emplacement de morceau du monde à un identifiant de morceau, initialisé à l'identité (`world_map.c:262-263`). `Map_WriteLayerCellTile` décode en LZ le morceau `id` (la couche 1 utilise `id + 320`, `:298`, `:640`) dans le quart `(x&1, y&1)` de `Ram_MapBlocks` et écrit les octets de la carte affine d'après la table des blocs (`:38-95`) [V]. L'index de fenêtre utilise `& 15`, d'où la boucle du monde tous les 16 morceaux [V].
- **Perspective** : `WorldMap_BuildScanlineTable` (`src/field/field/view.c`) + la routine ARM `Transform_UpdateVertices` construisent une paire affine (BG2/BG3 PA..Y) par ligne de balayage ; `MapAnimation_ApplyAffineFrame` charge la ligne 0 et envoie le reste par DMA HBlank (`world_map.c:386-441`) [V]. Inclinaison par défaut 0xe000 (-1/8 de tour), plan lointain 0x1fe0000, centre (120,96) (`:198-249`) [V]. Une vue d'éditeur de dessus ignore tout cela.
- **Jeu graphique B** : `WorldMap_LoadGraphics(x,z)` choisit le jeu B si la case de couche 0 sous le groupe est de type 21, au chargement de la scène seulement (`world_map.c:323-329`, appelé depuis `run_scene.c:76-78`) [V]. Avec le jeu B, il fait aussi pointer les emplacements de morceaux 10-12 et 26-28 vers les morceaux de remplacement 0x10a-0x10c, 0x11a-0x11c (`:366-374`) [V]. Le rendu confirme que le jeu B est le nord enneigé (région d'Imil) ; dans le jeu A, ces emplacements montrent un bouche-trou blanc [V : `north_compare.png`].
- **Échange de morceau lié à l'histoire** : `FieldMap_SetWindowCellTile(128, 256, 176, 56)` (`src/scene/world_map.c:534`) place le morceau 264 dans l'emplacement 59 (morceau du monde (11,3)) tant que `FLAG_LAMAKAN_SAND_MONSTER_BEATEN` n'est pas mis ; calcul dans `world_map.c:271-300` [V]. Visuellement, 264 et 59 diffèrent par un pont [V rendu ; signification I]. C'est le seul appel (grep) [V]. 57 des 64 morceaux de remplacement (256-319, et leurs jumeaux de couche 1) ne sont référencés par aucun code de TBS [I : grep n'a trouvé aucun autre utilisateur ; les 64 sont tous non vides et distincts de 0-255].
- **Animation** : les canaux d'animation des tuiles copient depuis `gMapLayerData` (tuiles E/J) vers la VRAM ; sans importance pour un rendu statique [V].

Algorithme de rendu vu de dessus (implémenté dans `render_world.py`, 7 s en Python pur) [V] :

```
for layer L in (0,1), world chunk (cx,cy) in 16x16:
    c = cy*16 + cx + 320*L                         # use tileIds overrides for set B / story swaps
    for cell (x,y) in 16x16: word = tsv[(c//32)*16 + y][(c%32)*16 + x]
        b = word & 0xffff; t[0..3] = cells_bytes[4b..4b+3]
        draw tile t[k] from bank L at BG px ((cx*16+x)*16 + (k&1)*8, (cy*16+y)*16 + (k>>1)*8)
        (layer 1: skip pixel value 0)
palette: palette_a.png (or palette_b.png for kind-21 cells / set B)
```

Résultat : `world_mixed.png` (jeu A, cases de type 21 dessinées avec le jeu B) montre Angara et Gondowan dans le quart supérieur droit (morceaux x 8-15, y 0-7), le reste étant de l'océan ; des terres de remplissage plates au bord ouest du continent ; trois îlots [V]. Superposer `gWorldMapEntrances` et les positions de placement à monde/2 place l'icône de Vale (acteur 11 en 5678,1200), les entrées 0-2 juste au sud, et le code de pas 90 (Flint) à côté [V : `world_annotated_zoom.png`].

## Données de jeu

### Mot de case (couche 0) [V]

| Bits | Signification | Preuve |
| --- | --- | --- |
| 0-15 | identifiant de bloc dans `cells.tsv` (16 bits complets, pas de masque de 12 bits sur la carte du monde) | `world_map.c:82-86, 445` |
| 16-23 | code de pas (`struct MapCell.collisionCode`) : 1-239 événements de pas de scène, 240-241 sol à rencontres, 252-254 téléportations, 0xff mur (signification des cartes en couches) | `include/map.h:13-22`, `src/object/object/step.c:20-25, 231-245` |
| 24-30 | type de terrain = région de rencontres (0 aucune, 1-6, 21, 31 utilisés) | `terrain.c:619-624`, `zonedata.c` |
| 31 | sélectionne la banque de comportement 0x10 | `terrain.c:615-617` |

Les cases de couche 1 n'utilisent que les bits 0-15 ; tous leurs bits supérieurs valent 0 dans les données [V : statistiques]. Seuls les bits supérieurs de la couche 0 sont lus (le code indexe les lignes 0-31 de `Ram_MapBlocks`, c'est-à-dire la couche 0) [V]. Le commentaire du code `struct WorldMapCell {tile:24, kind:7, flag:1}` (`world_map.c:17-23`) regroupe le code de pas dans « tile » ; les lecteurs utilisent les octets séparément [V].

Recensement des valeurs (couche 0, les 320 morceaux) : types 0 74215, 1 915, 2 1542, 3 1001, 4 771, 5 494, 6 1304, 21 1334, 31 156 ; bit 31 mis sur 188 cases ; codes de pas présents : 13, 15, 18, 28, 29, 32, 42, 47, 50, 51, 55, 61, 74, 75, 90, 91, 92, 93, 95, 96, 100 [V].

### Praticabilité / terrain [V]

- `GetWorldMapCollision` (`terrain.c:535-580`) : prendre l'octet de la carte BG (le numéro de tuile 8x8) dans le bloc d'écran 10 (couche supérieure) à la position, chercher son quartet dans `Ram_MapCollision + 0x800` ; si 0, faire de même pour le bloc d'écran 8 (inférieur) dans `Ram_MapCollision` ; si toujours 0, renvoyer 7. Quartet = ligne `((y>>1)&3)`, octet `((x>>2)&1)`, `(x>>1)&1` sélectionne le quartet haut, en unités de 2 px du monde.
- `CheckWorldMapWalkable` (`terrain.c:586-592`) : praticable si et seulement si la valeur est entre 5 et 12.
- Comportement = `gWorldMap_TerrainBehaviorTable[bank + value]` (`mapdata.c:37-41`) : banque 0 : 5->1, 6->7, 7/8/10-13->1, 9->2 ; banque 0x10 (bit 31) : 5->4, 9->6 ; banque 0x20 (type 21) : 5-13->5 sauf 9->6. Le comportement choisit aussi le décor de combat (`encounter.c:118`, `Battle_SelectTerrainBackdrop` `encounter.c:404-429`) : 1 prairie, 2 forêt, 3 désert, 4 et 7 plage, 5 et 6 plaine enneigée, autre Sol Sanctum [V].
- Recensement de la carte de collision composée : on trouve les valeurs 1-4, 14, 15 (bloquées ; eau/montagne/falaise) et 5-10 (praticables) ; 9 = forêt (comportement 2) d'après les étiquettes de rencontres [V données ; étiquette « forest » d'après `encounter.tsv`].
- Hauteur : aucune sur la carte du monde (les cases n'ont pas d'octet de forme ; acteurs placés avec y=0 et sans hauteur de terrain, `src/object/object/actors.c:143-158`) [V].

### Rencontres aléatoires [V]

À chaque pas sur la carte du monde : `Field_ProcessStep` -> `Encounter_RollWorldMap(&leader->x, speed)` (`step.c:261-263`) -> `Encounter_ResolveWorldMapZoneAndBackdrop` (`encounter.c:103-120`) : la première règle de `gWorldMap_EncounterRules` dont le type, le comportement (ou -1) correspondent et dont le drapeau n'est pas mis donne la zone ; puis `Encounter_SelectEnemyGroup` (`encounter.c:130-218`) utilise la ligne de `encounter.tsv` : taux (+5 par niveau du groupe au-dessus de `level`, max 5), biais, 8 groupes pondérés (lignes de `src/battle/formatn.tsv`). Les règles des scènes de terrain (`src/object/location_rules.s`) ne servent pas sur la carte du monde (`Encounter_SelectSceneZones(0)`, `run_scene.c:49`).

Règles (type : comportement -> zone) : 1 : 4,7,1->7, 2->8 ; 2 : 4,7,1->13, 2->14 ; 21 : 5->29, 6->30 ; 31 : 1->37, 2->38 ; 3 : 3,4,7,1->45, 2->46 ; 4 : ...->54, 2->55 ; 5 : ...->64, 2->65 ; 6 : ...->80, 2->81. Zones étiquetées dans `encounter.tsv` (« World map: terrain kind 1, grassland and beach », ...). Le comportement 3 (désert) figure dans les règles mais la table des comportements ne le produit jamais, donc sur la carte du monde de TBS le sol désertique compte comme prairie/plage [V lecture de la table ; effet en jeu I]. Combats de Djinn : zones 100-103 via `gEncounter_AreaEntryTable` (`zonedata.c:19-29`).

`terrain_kind.png` montre des régions cohérentes (type 1 autour de Vale, 2 Bilibin, 21 nord enneigé, ...) [V rendu ; noms de lieux I].

### Entrer dans les villes/donjons [V]

Deux mécanismes, tous deux aboutissant à `gWorldMapEvents` (`src/scene/world_map.c:3060-3125`) :

1. **Icônes de lieu (la plupart des villes)** : les lignes de `gWorldMapPlacements` (`:2863-2964`) sont les acteurs 8, 9, ... dans l'ordre des lignes ; une ligne dont la condition échoue consomme quand même son emplacement (`actors.c:103-108`). `WorldMap_UpdateLocationContacts` (`world_map.c:416-466`) règle `touchedTrigger = actor + 100` quand |dx|+|dz| du meneur < somme des rayons mis à l'échelle (et `FLAG_CONTACT_BLOCKED` 0x104 non mis). Un événement `{ EVENT_EXIT, 100+actor, cond, exitNo }` l'associe à une sortie ; p. ex. ligne 3 (acteur 11, sprite 0x105 en 5678,1200) -> déclencheur 111 -> sortie 1 -> `SCENE_EXIT(1, 5, 10)` = scène 5 (village de Vale) entrée 10. Certains déclencheurs exécutent plutôt des scripts (les passages 116/125/130/150/151 choisissent une sortie selon le côté d'approche, `:367-410`).
2. **Codes de pas dans la carte** : bits 16-23 de la case = code ; `{ EVENT_EXIT, code, cond, exitNo }` (codes 13, 15, 18, 28, 29, 32, 42, 47, 50, 51, 55, 61, 75) ou scripts `EVENT_TOUCH`/`SEARCH` (90-96 Djinn, voyage, naufrage ; 100 fouille des Turtle Boots ; 112 itinéraire de transfert ; 74 bord est).

Encodage des sorties `SCENE_EXIT(exit, scene, entrance) = exit<<20 | entrance<<12 | scene`, la forme avec drapeau ajoute 0x10000000 et un mot de drapeau ; la table commence par `SCENE_EXITS(own scene)` et se termine par 0x1ff (`include/field_scene.h:72-77`).

### Quitter les villes [V]

La table de sorties de la ville nomme la scène 2 : p. ex. `gValeHome_Exits` `SCENE_EXIT(10, 2, 1)` (`src/scene/vale_home.c:1903`) ; Bilibin `SCENE_EXIT(1, 2, 5)` (`bilibin.c:805`). L'entrée `e` est une ligne de `gWorldMapEntrances` (`struct SceneEntrance`, 24 octets : entrance, requiredFlag, x, y, z (pixels s16), facing, unused, camera L/T/R/B, unused ; `field_scene.h:54-67`). Entrée 1 = (5680, 0, 1226) orientée vers le sud, juste sous l'icône de Vale. Des entrées spéciales (33, 49, 64-80, 90, 91, 99) choisissent aussi des tables de placement et des cinématiques (`world_map.c:308-342`, `496-560`).

## Limites et contraintes

- Le nombre et la disposition des morceaux sont fixés par le code : 640 morceaux, décalage de couche 320 (`0x140`, `world_map.c:298, 640`), grille d'emplacements 16x16 (`& 15`), remplacements aux identifiants fixes 0x10a-0x10c, 0x11a-0x11c, 264 [V]. Garder `blocks.tsv` à exactement 320x512.
- Chaque morceau se décode en 1024 octets dans un bloc de tas de 0x400 (`world_map.c:56-57`) [V].
- Tuiles : 256 par couche (les entrées de carte affine sont des octets) [V] ; 224 couleurs de palette, index 0 forcé au fond [V]. Les banques de tuiles E/J (256 tuiles) alimentent l'animation [V].
- Blocs : l'identifiant de bloc fait 16 bits dans la case, mais `cells.tsv` se décode dans `gMapCellBuffer` (0xc000 octets, `ewram.s:225`) -> au plus 12288 blocs [I] ; le même tampon contient l'image de vue fixe 240x160 pendant les événements (`world_map.c:711-712`) et est rechargé ensuite (`:766-767`) [V].
- Table de collision fixe de 4096 octets (2 x 256 tuiles x 8) [V] ; le script d'animation doit tenir après elle dans `gMapCollision` (0x4000 au total, commence à +0x1000) [I].
- Placements : emplacements d'acteurs 8..65 (`actors.c:98`, `CONTACT_LAST_ACTOR = 65`) ; les déclencheurs de lieu 108..165 ne doivent pas entrer en collision avec les codes de pas utilisés pour d'autres événements [V/I]. La ligne i de `gWorldMap_PlaceMarkers` doit rester alignée avec l'acteur 11+i [V].
- L'overlay de la carte du monde (code + tables + graphismes de l'histoire) doit tenir dans 32 Ko à 0x2008000 [V : README des scènes]. Les coordonnées des entrées sont en s16 [V].
- Compression : chaque morceau est en LZ `plz` (`tools/common/lz.c`, `LZ_PALETTE_UNTAGGED`, machine `{4123, 485, 4126, 272}`) ; cases/attributs/animation en `.table.lz`, tuiles en `.8bpp.lz`, palettes en `.gbapal.plz` [V]. La construction réencode à partir des TSV/PNG, donc un éditeur n'écrit que des sources ; ne jamais écrire à la main des `.blocks`/`.lz`.
- Correspondance octet par octet : des sources inchangées reproduisent la ROM d'origine (octets littéraux PACKER et mécanisme `_patch.tsv`, `src/map/README.md` « How the build encodes a map ») ; toute modification fait différer cette édition, c'est-à-dire que `make compare-editions` échoue par conception [V]. Les octets `PACKER:` en fin de `map.s`/`worldmap.s` sont des données périmées sans conséquence après une modification [I].
- Disposition de la ROM : `rom_tail_02` (qui contient `map.s`, `objects.tsv:443`) commence à une adresse fixe par édition (`main.ld:122-126`) et est la dernière région ; une croissance ne décale que les données suivantes ; fin de cartouche de TBS 0x08800000 (`Makefile` `ROM_END_tbs`) [V] ; je n'ai pas vérifié ce qui se passe en cas de dépassement [I].
- Éditions : aucune variante `_ja/_de/...` ni `.ifdef TBS_EDITION_*` dans `map/world`, `map/default`, `graphics/world_map`, `zonedata.c`, `mapdata.c`, `world_map_resources.c` [V grep]. `scene/world_map.c` n'a que des différences de code `TBS_PATCH_3` (`:1657-1666`) [V]. Les noms de lieux / messages sont dans des catalogues PO par langue (`games/tbs/text/*.po`) [V README des scènes].

### Différences de TLA (en bref)

- `games/tla/src/map/world/blocks.tsv` fait 1024 lignes x 512 = 2048 morceaux ; décalage de couche 1 de 0x400 (`games/tla/src/field/common/map/perspective.c:42`) et une fenêtre de 32x32 morceaux (`tiles[32][32]`, `:8`) -> monde de 32x32 morceaux (16384 px du monde) [V]. 969 morceaux sont omis (`-`) [V].
- Placé par `games/tla/src/map/world/blocks.s` (fichier à part, `.balign 4, 0`) [V].
- Quatre jeux graphiques A-D, chacun avec une palette + 6 planches de tuiles (`tiles_a1..d6.png`), plus des tables d'animation/d'attributs par jeu (`anim_b/d.tsv`, `attr_b/c/d.tsv`) dans `games/tla/src/graphics/world_map/` ; répertoire `games/tla/src/system/resource/directory.s:420-458` [V]. `cells.tsv` est plus grand (2745 lignes) [V].
- La plus grande partie du code moteur de la carte du monde de TLA est encore en assembleur (`object_dispatch_5.s`) ; la sémantique des types/drapeaux est supposée partagée [I].

## Inconnues

Signalées par alchemy :
- XXX `world_map.c:569` : `WorldMap_UpdateView` lit la position suivie sans vérifier NULL.
- XXX `world_map.c:778` : savoir si le fait que `Map_LoadDefaultCellsAndUpdateBlock` laisse `animationActive` activé est voulu.
- XXX `src/scene/world_map.c:500-504` : les drapeaux 0x161 et 0x85c (mis par les entrées 99 et 1) ne sont lus par aucun code de TBS.
- XXX `actors.c:101-102` : la limite de sprite 0x2705 dans l'apparition des placements.
- Drapeaux de rencontre 351/353 sans nom (`encounter.c:148-152`) ; règle « flag 5 / unit 5 experience > 130 ».
- Les XXX des cartes en couches (bloc réservé 0xfff, octets de remplissage de l'en-tête) ne s'appliquent pas : la carte du monde n'utilise pas de masque de 12 bits [V].

Non résolu par cette recherche :
- Intention des concepteurs pour le bit 31 de la case : mécaniquement, il transforme la collision 5 en comportement 4 (décor de plage) et 9 en 6 (décor de plaine enneigée) [V] ; on ne sait pas pourquoi ces 188 cases le portent [I].
- Pourquoi la valeur de collision 6 correspond au comportement 7 (un second identifiant de plage) [I].
- Utilité des 57 morceaux de remplacement qu'aucun code de TBS ne référence (restes ou époque de TLA) [I].
- Signification exacte de chaque valeur de collision 1-4, 14, 15 (eau, montagne ou falaise) et de 6, 8, 10 [I].
- Si `picture.png` (carte de pause) a été dérivée des données du sol ; un éditeur qui modifie les côtes doit la redessiner à la main [I].
- Savoir quelle scène/entrée chaque `EVENT_EXIT` atteint en termes compréhensibles demande de joindre les noms de `gField_SceneTable` (certains noms de scène d'alchemy sont connus pour être inexacts, p. ex. la scène 5 `ValeHome` est le village de Vale) [V pour l'exemple].

## Modèle de données proposé pour l'éditeur

Couche Python, toutes les entrées/sorties portant uniquement sur les fichiers sources d'alchemy. Conserver la mise en forme du texte d'origine pour des diffs lisibles.

| Entité | Champs | Fichier (lecture/écriture) | Remarques sur l'aller-retour |
| --- | --- | --- | --- |
| `WorldGrid` | `chunks[640][16][16]: u32` plus des vues dérivées `cell(layer, gx, gy)` via la table d'emplacements ; `slot_map[256] = identity` | `src/map/world/blocks.tsv` | Écrire exactement 320x512 éléments, `format(v, 'x')` (minuscules, sans remplissage, `0` pour zéro), séparateurs tabulation, fins de ligne `\n` + `\n` final. Ne jamais émettre `-` dans TBS. La réécriture à l'identique octet par octet d'un fichier non modifié doit faire l'objet d'un test. |
| `Cell` | `block: u16`, `step_code: u8`, `kind: u7`, `bank_flag: bool` (couche 0) ; couche 1 seulement `block` | intégré dans `WorldGrid` | Conserver tels quels les bits supérieurs de la couche 1 (tous à 0) et tout bit inconnu. |
| `Alternates` | `set_b_swaps {10:0x10a, 11:0x10b, 12:0x10c, 26:0x11a, 27:0x11b, 28:0x11c}`, `story_swaps {59:264}` | constantes de `world_map.c:366-372`, `scene/world_map.c:534` (lecture seule) | L'éditeur devrait modifier les remplacements avec leurs morceaux de base et montrer les deux vues. |
| `BlockTable` | `blocks[4386][4]: u8` | `src/map/default/cells.tsv` | Ligne d'en-tête conservée ; 16 valeurs par ligne, `0x%02x`, dernière ligne courte autorisée. Partagée avec les cartes en couches : modifier un bloc change toutes les cartes qui utilisent les cases par défaut ; préférer l'ajout de nouveaux blocs. |
| `TileCollision` | quartets `lower[256][4][4]`, `upper[256][4][4]` | `src/map/default/attributes.tsv` | 16 octets par ligne, `0x%02x`, en-tête conservé. Partagée aussi avec les données par défaut des cartes en couches [I]. |
| `Tileset` | par jeu : palette (224 RVB), banques L0 (A+B), L1 (C+D), banque d'animation (E/J) | `src/graphics/world_map/*.png` | Garder le mode PNG P, les tailles exactes et une palette identique à `palette_*.png` (index = couleur). Réécrire les PNG ne pose pas de problème pour la construction si les index sont préservés ; vérifier l'identité des pixels plutôt que celle des fichiers. |
| `Animation` | scripts de canaux (liste de u16) | `src/map/default/animation.tsv` | Traiter d'abord comme des mots opaques. |
| `Entrance` | `id, required_flag, x, y, z, facing, camera[4]` | `gWorldMapEntrances` dans `src/scene/world_map.c:2717-2800` | Source C : analyser/régénérer uniquement le bloc d'initialisation entre des repères connus ; garder les noms `CONDITION_ALWAYS`, `FACING_*`. |
| `Exit` | `exit_no, scene, entrance, flag?` | `gWorldMapExits` (`:2802-2839`) et les `*_Exits` des villes | Idem ; garder la forme macro `SCENE_EXIT(...)`. |
| `Placement` (icône de lieu) | `row/actor, sprite, condition, behavior, x, z, facing, talk, flags` | `gWorldMapPlacements` (`:2863-2964`) | Numéro d'acteur = 8 + ligne ; insérer/supprimer des lignes renumérote les déclencheurs (100+actor) et l'alignement de `gWorldMap_PlaceMarkers` (acteur 11+i). Préférer la modification sur place. |
| `Event` | `kind/control, trigger, condition, value` | `gWorldMapEvents` (`:3060-3125`) | Sorties : `{ EVENT_EXIT, trigger, cond, exit_no }` ; les scripts référencent des fonctions C (lecture seule dans l'éditeur). |
| `EncounterRule` | `kind, behavior, flag, zone` | `src/object/zonedata.c:7-15` | 132 s16, terminateur compris ; le littéral de taille du tableau doit être mis à jour si des règles sont ajoutées. |
| `EncounterZone` | `rate, level, groups[8], weights[8], label` | `src/object/encounter.tsv` | Forme de table ; 104 lignes fixées par les références (identifiants de zone dans le code/les règles). |
| `PlaceMarker` | `tile, flag, name_id` par acteur 11+i | `src/object/scripts.s:340-383` | Lignes asm `.4byte`. |

Vues d'éditeur recommandées : (1) composite vu de dessus avec choix du jeu par case (type 21 -> jeu B), (2) surcouche de collision à partir de `TileCollision` via les numéros de tuiles des cases (supérieure, puis inférieure, puis 7), (3) surcouches de type et de code de pas, (4) entrées/placements à monde/2. Fonctions utilitaires de coordonnées : px du monde = px BG x 2 ; case = monde // 32 ; emplacement de morceau = case // 16 ; (ligne, colonne) TSV pour la couche L = `((c//32)*16 + gy%16, (c%32)*16 + gx%16)` avec `c = slot_map[(gy//16)*16 + gx//16] + 320*L`.
