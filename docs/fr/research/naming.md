<!-- translated from docs/research/naming.md @ 3e642cd20a29 -->
# Couche de nommage : codes de collision, objets, sprites, lieux, dialogues, drapeaux (TBS)

*Ceci est une traduction du document anglais [naming.md](../../research/naming.md) ; en cas de différence, c'est la version anglaise qui fait foi.*

> **Depuis la rédaction de ce document :** les tables de noms décrites ci-dessous ne sont plus livrées. `gsmap/names.py` lit les noms à l'exécution depuis la copie de travail (`en.po`, `flags.h`, `sprite_ids.h`, `item_table.c`, `scenes.s`, `scene_rules.s`). `gsmap/data` ne conserve que les images d'aperçu, les drapeaux de coffre libres et nos propres descriptions de praticabilité.

Arborescence source : `alchemy/` (lecture seule), construction anglaise `out/tbs-en`. Les chemins sont relatifs à `alchemy/games/tbs/` sauf s'ils commencent par `out/` ou `tools/`. **VÉRIFIÉ** signifie lu dans le code ou les données, ou contrôlé par un script sur tous les fichiers. **DÉDUIT** signifie déduit et non prouvé. Les données générées se trouvent dans `docs/research/names/`. Les scripts qui les produisent sont copiés dans `docs/research/names/scripts/` ; les originaux et les fichiers intermédiaires sont dans le répertoire de travail `(a scratch folder)`.

## Résumé

1. Les **codes de collision** se répartissent en trois groupes : significations globales du moteur, déclencheurs de scène et marqueurs. (VÉRIFIÉ)
   - **Significations globales :**
     - 0 sol
     - 240/241 sol à rencontres
     - 242..247 points de fouille vides fixes : jarre, tonneau, caisse, tombe, livres, puits
     - 249 saut en chaîne
     - 250 danger
     - 251 ombre de Cloak
     - 252 corniche
     - 253 escalade
     - 254 saut d'un vide
     - 255 mur
   - **1..239 sont des déclencheurs de scène.** Leur signification vient des tables d'événements de la scène : une sortie, un script de contact ou une fouille.
   - **Les marqueurs (coffres et pierres) ne peuvent utiliser que 100..239.**
   - L'éditeur devrait nommer 1..239 par carte d'après les événements. `collision_by_map.json` (travail temporaire) est cette légende, déjà résolue : pour les sorties, le lieu de destination ; pour les scripts, le nom du script ; pour les fouilles, l'objet ou le texte.
2. **Objets :**
   - Nom = message `MsgItemName` (386) + id.
   - Icône = colonne `icon` de `items.tsv` → `graphics/ui/menu_icons/item_{icon:03d}.png` (16×16, palette intégrée).
   - Valeur de coffre = `FIND_ITEM(id)` = `0x100000|id`, `FIND_COINS(n)` = `0x200000|n`, mimique = `0x500000|slot` (emplacements 0..7), ou `FIND_PSYNERGY_STONE` = `0x300000`.
   - (VÉRIFIÉ)
3. **Sprites :**
   - L'identifiant de sprite du placement sert directement de ligne de `graphics/sprite/sprites.tsv` (513 lignes).
   - Ses graphismes sont `graphics/sprite/spr_NNN.png`, une bande verticale d'images w×h dessinées avec la palette OBJ partagée de 224 couleurs.
   - L'image d'aperçu est la première image de l'animation 1 plus le décalage d'orientation.
   - 249 identifiants sont couverts, dont les 219 utilisés. 71 noms sont VÉRIFIÉS (symboles et commentaires de la décompilation) ; 178 sont DÉDUITS de l'image et des scènes qui les utilisent.
4. **Lieux :**
   - `gScene_AreaNameRules` (`src/object/scene_rules.s:168`) donne à chaque scène ou groupe (éventuellement par entrée) un index de zone.
   - Le texte est le message `MsgDebugEntryName` (2459 en EN) + index.
   - 199 des 201 scènes reçoivent un nom. (VÉRIFIÉ)
5. **Dialogues :**
   - Le `msgid` de `en.po` est le numéro de message sur 5 chiffres complété par des zéros. `msgctxt` est le nom du symbole, ou `message` quand le message n'en a pas.
   - Une valeur de `SceneEvent` inférieure à 0x10000 est un numéro de message. Au-delà, c'est un script ; ses répliques sont les symboles `Msg*` de son corps.
   - Le déclencheur d'un événement de dialogue est le numéro d'acteur, soit 8 + la ligne de placement.
   - (VÉRIFIÉ)
6. **Drapeaux :**
   - Il y a 4 096 drapeaux (0..0xfff).
   - Les nouveaux coffres devraient prendre leurs drapeaux dans **0xe00..0xfff**, en n'utilisant que des drapeaux qu'aucune table, aucun code ni aucun littéral ne référence. **251 sont libres** (`flags.json` `free_chest_flags`), les plus bas étant 0xe01, 0xe03..0xe0f, etc.
   - Ne jamais utiliser 0x200..0x3ff : ce sont des temporaires de scène et de groupe qui sont réinitialisés.

---

## 1. Codes de collision

### 1.1 Signification pour le moteur (VÉRIFIÉ sauf mention contraire)

Le code d'une case est `struct MapCell.collisionCode` (`include/map.h:13-22`), lu dans la fenêtre de la couche du meneur (`terrainId`), une case de 16 px à la fois.

| Code | Nom (côté joueur) | Comportement du moteur | Preuve | Éditeur |
|---|---|---|---|---|
| 0 | **Sol** | Praticable. Utilise le sol à rencontres 0, qui n'a pas de rencontres sauf si le décalage de la règle de lieu de la scène = 1 y déplace la première zone. | `src/object/object/step.c:240-276` ; `src/object/object/encounter.c:76-90` ; `src/object/location_rules.s:1-7` | pinceau |
| 1..239 | **Déclencheur** (sortie / événement / fouille) | Marcher sur la case déclenche `work->action = code` (`step.c:247`). `Scene_RunTouchOrExit` exécute d'abord l'`EVENT_TOUCH` de la scène avec ce déclencheur (message ou script) ; s'il n'y en a pas, il utilise `EVENT_EXIT`, dont la valeur est le type de sortie (`events.c:333-380`). Appuyer sur A sur la case devant cherche `EVENT_SEARCH` avec le même code (`run_scene.c:440-450`). Les événements `USE_ITEM` et `PSYNERGY_IN_AREA` peuvent aussi s'y rattacher. Tout code non nul teste aussi les régions de sortie (`step.c:244-245`). | comme indiqué | déclencheur : nommé par carte d'après les événements (§1.3) |
| 100..239 | **Identifiant de coffre / pierre / fouille** | Tout ce que fait 1..239, plus : c'est la seule plage qu'accepte `Field_PlaceMapMarkers` (`markers.c:57`). Un événement `SEARCH(SEARCH_CHEST)` affiche un coffre (objet 20, `markers.c:70`) ; `FIND_PSYNERGY_STONE` affiche une pierre (objet 28, `markers.c:105`). | | déclencheur ; les marqueurs possèdent ces codes |
| 240 | **Sol à monstres** | Praticable. Les rencontres utilisent `encounterGroups[1]`, la première zone de la règle, au lieu du sol 0. Courant comme sol de donjon : 23 cartes, p. ex. map_009 (133 cases). | `step.c:22-23,264-267` | pinceau |
| 241 | Sol à monstres 2 | Comme 240, mais utilise `encounterGroups[2]`. **Aucune carte ne l'utilise.** | `step.c:22-23` | pinceau (avancé) |
| 242 | Jarre vide | Quand on la fouille, dit « checked the jar… but didn't find anything ». Décalage de message 2 depuis `MsgTileChecked` (2344) et `MsgTileResult` (2376). Ne se déclenche que lorsque le sol devant est de 0 à 64 px au-dessus du meneur. | `src/object/fxdata.c:22-31` ; `events.c:439-448` ; `run_scene.c:441-447` | pinceau |
| 243 | Tonneau vide | décalage 3 | idem | pinceau |
| 244 | Caisse en bois vide | décalage 13 | idem | pinceau |
| 245 | Tombe vide | décalage 8 | idem | pinceau |
| 246 | Bibliothèque (livres) | décalage 30 | idem | pinceau |
| 247 | Puits | décalage 31. Inutilisé dans les cartes. | idem | pinceau |
| 248 | (inutilisé) | Aucun lecteur trouvé, et aucune carte ne l'utilise (DÉDUIT inerte). | — | ne pas toucher |
| 249 | **Saut de pierre en pierre** | Jamais déclenché par `Field_ProcessStep`. Après un saut en avant, atterrir sur 0xf9 fait sauter à nouveau (sauts enchaînés). Utilisé dans 3 cartes (029, 098, 148). | `events.c:383-405` ; `src/object/psynergy_effects/climbing.c:18-23,99-103` | pinceau (avancé) |
| 250 | **Sol dangereux** | En marchant, le compteur de pas dangereux augmente, et à `hazardLimit` le groupe subit `hazardDamage`. La scène règle le mode, la limite et les dégâts. Cartes 063-067. | `step.c:24,293-327` | pinceau |
| 251 | **Ombre (Cloak)** | Praticable. Cloak ne garde le groupe caché que sur ce code ; le quitter met fin à Cloak (`CLOAK_TILE`). Cartes 111 et 130-142 (Lunpa Fortress, Altmiller Cave…). | `src/object/psynergy_effects/cloak.c:7-11,71` | pinceau |
| 252 | **Corniche (sauter en bas)** | Poussez contre elle pendant plus de 12 images en maintenant Bas, et le meneur saute en bas. | `step.c:25-27,249` ; `events.c:394-399` | pinceau |
| 253 | **Mur escaladable / échelle** | Poussez pendant plus de 12 images : Haut fait grimper, Bas fait descendre. Pendant l'escalade, un pas n'est permis que vers une case de même code. Arriver sur deux cases 0xfd empilées avec y≠0 fait démarrer le groupe en mode escalade. | `events.c:407-415` ; `src/field/field/player_control.c:874-881` ; `src/object/object/actors.c:250-262` | pinceau |
| 254 | **Saut d'un vide** | Poussez pendant plus de 12 images : le meneur saute de 2 cases en avant si l'atterrissage le permet (`Field_TryJumpForward`). 77 cartes. | `events.c:400-405` ; `climbing.c:13-30` | pinceau |
| 255 | **Mur** | Bloque toujours (`Map_CheckObjectStep` renvoie 2). | `src/field/field/terrain.c:477,526` | pinceau |

La praticabilité dépend aussi de la hauteur. Un pas de plus de 8 px vers le haut ou de plus de 12 px vers le bas est refusé (`terrain.c:494-497`), donc un code « sol » sur une falaise reste bloquant. La surcouche de praticabilité devrait combiner le code avec les hauteurs de `grid_shape`. L'eau n'est **pas** un code de collision dans les cartes locales de TBS : c'est un mur ou une hauteur, et les flaques et éléments semblables sont des déclencheurs de scène (DÉDUIT de l'histogramme : pas de code dédié).

Les codes des cases sont aussi modifiés à l'exécution par le code des scènes (`SetMapCellCollision`, `terrain.c:422`), dans Colosso, Altin Peak, Crossbone Isle, Venus Lighthouse, Tolbi et Sol Sanctum. Les codes 96..99 des cartes 078-083 (Altin Peak) n'ont pas d'événement statique, ils sont donc lus par script (DÉDUIT).

### 1.2 Histogramme d'utilisation (VÉRIFIÉ par `coll_hist.py`, 182 cartes, cases dans les 3 fenêtres de couche)

| Code | Cases | Cartes | Remarque |
|---|---|---|---|
| 0 | 1,300,642 | 182 | sol |
| 255 | 47,077 | 151 | mur |
| 240 | 4,308 | 23 | sol à monstres (donjons/forêts : 009, 016, 025-030, 043, 046, 050, 055, 056, 062, 064, 066, 067, 078, 133, 136, 137, 164, 166, 167) |
| 21 | 4,244 | 34 | p. ex. carte 091 de Lamakan Desert : 2,677 cases de `EVENT_TOUCH 21 → HeatGauge_CountStep` |
| 251 | 1,729 | 9 | ombre de Cloak |
| 10 / 30 / 11 / 1 / 2 | 963 / 683 / 357 / 340 / 255 | 96 / 23 / 78 / 150 / 140 | les codes bas sont surtout des sorties et des scripts de contact de porte |
| 254 / 253 / 252 | 928 / 484 / 59 | 77 / 60 / 28 | saut / escalade / corniche |
| 243 / 244 / 242 / 245 / 246 | 500 / 482 / 388 / 32 / 18 | 29 / 29 / 28 / 6 / 3 | tonneaux/caisses/jarres/tombes/livres vides |
| 100..107 | 100, 67, 37, 21, 8, 5, 3, 4 | 95..3 | coffres (`SEARCH_CHEST` 66× sur 100) et autres fouilles |
| 200..212 | 2..35 | 14..1 | points de fouille hors marqueurs (objets cachés dans des jarres/tonneaux…) |
| 250 | 77 | 4 | danger |
| 249 | 3 | 3 | saut |
| 241, 247, 248 | 0 | 0 | inutilisés |

Les types d'événement derrière 1..239 sur l'ensemble des cartes (nombre = cartes) : code 1 → EXIT 130, TOUCH 44 ; code 10 → TOUCH 65, EXIT 36 ; 100 → SEARCH_CHEST 66, SEARCH 36. Table complète : `coll_hist.json` (travail temporaire). 136 paires (carte, code) dans 1..239 n'ont **aucun** événement statique dans les scènes qui utilisent la carte. Elles sont utilisées par des scripts ou sont des restes : les afficher comme « Scripté / inconnu ».

### 1.3 Légende par carte (VÉRIFIÉ, générée)

`collision_legend.py` écrit `collision_by_map.json` (travail temporaire, 1 Mo). Pour chaque carte, il donne :
- `scenes` ;
- `cells_per_layer`, un histogramme des codes pour chaque fenêtre de couche ;
- `events_by_code[code]`, une liste de `{scene, table, kind: exit|touch|search|use_item|raised, control, condition, …}`, où :
  - une sortie a `exit_kind, to_scene, to_entrance, to_name, to_symbol` ;
  - un script a `script` (le symbole ELF, p. ex. `Event_EnterSanctum`, `HeatGauge_CountStep`) ;
  - un message a `message, text` ;
  - une fouille a `search_target` (l'un des 32 noms `SearchTarget`, `include/field_scene.h:176-209`), `marker_chest`, et `find_item/item_name | find_coins | psynergy_stone | mimic_slot` ;
  - un contact a `needs_push` (0x200) et `needs_facing` (0x400).

La règle d'étiquetage pour l'interface est :
- « Sortie → {to_name} »
- « Événement : {humanized script} »
- « Coffre : {item} »
- « Fouille {target} : {item | text} »

Quand il n'y a pas d'événement, l'étiquette est « Déclencheur inutilisé ». Plusieurs tables par scène sont choisies selon des drapeaux d'histoire, l'interface devrait donc afficher leur union et la marquer « dépend de l'histoire ».

**Données de l'éditeur :** `names/collision.json` (généré par `collision_json.py`) :
```json
{"notes":[...],
 "ranges":[{"lo":0,"hi":0,"name":"Floor","category":"walk|block|move|search|trigger|unknown",
            "editor":"brush|trigger|trigger (markers own 100..239)|brush (advanced)|don't-touch",
            "meaning":"...","evidence":["src/...:lines"],"confidence":"VERIFIED","color":"#rrggbbaa"}],
 "codes":[{"code":240,"hex":"0xf0","range":"240-240","cells":4308,"maps":23}]}
```
Plus une légende par carte générée au chargement, de la forme de `collision_by_map.json` (`{map: {scenes, cells_per_layer[3]{code:count}, events_by_code{code:[event…]}}}`). L'éditeur devrait la construire à l'exécution à partir des overlays construits (gsmap `Scenes`) plutôt que de la livrer.

Palette de pinceaux pour les joueurs : Sol, Sol à monstres, Mur, Corniche, Escalade, Saut d'un vide, Ombre, Danger, et Jarre/Tonneau/Caisse/Tombe/Livres vides. Les déclencheurs (1..239) ne sont jamais peints librement. Ils sont créés par des actions comme « ajouter une porte » ou « Ajouter un coffre », qui allouent un code inutilisé sur cette carte (et inférieur à 100 pour ce qui n'est pas un marqueur).

---

## 2. Objets

- **Identifiants et symboles.** `include/item_ids.h` ne nomme que les identifiants que le code utilise (VÉRIFIÉ). La table des objets `src/game/items.tsv` a une ligne par identifiant (id = ligne − 2, 324 lignes), une colonne `label` avec le nom anglais, et les colonnes price, type, flags, equip_mask, icon, … La structure est `ItemDefinition`, 0x2c octets (`include/game/item.h:104-137`).
  - Types : 0 aucun (consommable/clé), 1 arme, 2 armure, 3 bouclier, 4 casque, 5 bottes, 6 objet de Psynergie, 8 anneau, 9 chemise (`item.h:43-55`).
  - Drapeaux : 1 maudit, 2 impossible à déséquiper, 4 rare, **8 indispensable (objet clé)**, 0x10 empilable (`item.h:26-32`).
- **Nom anglais** = message de en.po `MsgItemName + id` = **386 + id** (`item_ids.h:7-8`, en.po:1579 ; utilisé à `src/shop/shop/buy.c:350`, `src/window/window/decode.c:541`). Retirer le préfixe `{article_class:N}`. Seuls les identifiants 0..268 ont des noms : 655 est `MsgEnemyName`. Description = `MsgItemPlainName` (117) + id (`buy.c:68`). Vérifié : 1 Long Sword, 180 Herb, 181 Nut, 268 Cleric's Ring (VÉRIFIÉ).
- **Icônes.** `src/graphics/ui/menu_icons/item_000.png`..`item_254.png` : PNG indexés de 16×16, chacun avec sa propre palette de 16 couleurs, index 0 transparent. Table de pointeurs : `gUiIcon_ItemIconPointers` (`src/graphics/ui/menu_icons.s:4-261`). L'icône d'un objet = `icon` de `items.tsv` (`ItemDefinition.icon`, `item.h:109`), dessinée par `ItemIcon_Compose` (`src/window/window/icons.c:114`) ; un index ≥ au nombre d'icônes devient 0 (`icons.c:63-64`). Herb → icône 117, Nut → 132.
  - **Règle de l'atlas :** icône k en (k%16·16, k//16·16) dans une planche de 256×256.
  - L'atlas a été construit et vérifié à l'œil (travail temporaire `items/item_icon_atlas.png`, `items/item_preview.png`) : épées, armures, feuille de Herb, clés et orbes correspondent tous à leurs noms.
  - Les variantes propres au JA `item_080_ja`/`item_098_ja` ne sont pas utilisées par EN.
  - DÉDUIT : la palette en jeu est égale à celle intégrée au PNG.
- **Valeurs de coffre** (`include/field_scene.h:211-214` ; `Field_SearchTile`, `src/object/object/events.c:429-560`), VÉRIFIÉ :
  - `value & 0x0f000000 ≠ 0` → un script (pointeur de fonction).
  - Sinon le type est `value & 0xfff00000` :
    - `0x100000` objet : moitié basse = identifiant d'objet ; tout ce qui n'est pas 2/3/4/5 prend aussi le chemin des objets.
    - `0x200000` pièces : `(u16)` → 0..65535 ; le jeu utilise 1..999.
    - `0x300000` Pierre de Psynergie : restaure tous les PP.
    - `0x400000` message.
    - `0x500000` mimique : combat `Encounter_GetEnemyGroupAtSlot(99, slot)`. La zone 99 est « Mimic chests » (`src/object/encounter.tsv` ligne 101, groupes 350..357). Seuls les emplacements 0..7 sont valides (`encounter.c:244`).
  - `(value & 0xf0000) == 0x10000` → « Can't open it » pour le groupe (inutilisé).
  - La `condition` de l'événement est le drapeau d'ouverture : le coffre est affiché ouvert tant que le drapeau est mis, et le drapeau est mis quand on prend le contenu. Si le sac du groupe est plein, l'objet reste et le drapeau reste non mis (`events.c:565-590`).
  - Contrôle `SEARCH(SEARCH_CHEST)` = 0x13. Les bits 4..8 choisissent la réplique « checked the X ».
  - Relevé de 155 coffres marqueurs : 130 objets, 17 pièces, 8 mimiques (0x500000..0x500007, chacune une fois). Aucun coffre n'utilise de Pierre de Psynergie ni de script.

**Données de l'éditeur :** `names/items.json` (généré par `scripts/items/build_items.py`) :
```json
[{"id":180,"symbol":"ITEM_HERB","symbol_in_header":true,"name":"Herb","description":"Replenishes 50 HP",
  "type":"none","type_id":0,"price":10,"flags":["stackable"],"key_item":false,"unused":false,
  "icon":117,"atlas":{"x":80,"y":112,"w":16,"h":16},"evidence":"items.tsv line 182; en.po msg 566"}]
```
La sortie du sélecteur est `{"kind":"item","id":180}` → `FIND_ITEM(ITEM_HERB)` (0x1000b4), `{"kind":"coins","n":50}` → `FIND_COINS(50)`, `{"kind":"mimic","slot":0..7}` → `0x500000|slot`, ou `{"kind":"psynergy_stone"}` → `FIND_PSYNERGY_STONE`. Masquer les entrées avec `unused` (nom « ? »/« ??? »/aucun) et signaler les entrées `key_item` par un avertissement. L'atlas est construit à l'exécution à partir de la copie d'alchemy du joueur, jamais livré.

---

## 3. Sprites / PNJ

- **Identifiant → objet** (VÉRIFIÉ) :
  - `Event_SpawnObjectTable` (`src/object/object/actors.c:97-118`) : les identifiants 0-7 = emplacements du groupe, et `Party_RemapCharacterIdByFlags` (`actors.c:12-36`) échange les sprites d'enfants 0x12/0x13 sous `FLAG_CHILDHOOD`. Les autres identifiants prennent les emplacements d'acteurs 8+ dans l'ordre des lignes (acteur = 8 + ligne).
  - Puis `Object_CreateFar(id)`, sélection de l'animation 1, et réglage de l'angle d'après `facing`.
  - `FieldObject_Create` (`src/field/field/objects.c:245-290`) : `id>>12` est le type. Type 0 = un sprite `id & 0xfff` ; type 2 (0x2000|n) = un groupe de deux sprites n, n+1 ; les autres types n'ont pas de sprite, p. ex. 0x8000 = caméra (`actors.c:266`).
- **Table des sprites :** `gCharacter_DescriptorTable[id & 0xfff]` (`src/system/resource/metadata_get_record.c:7-9`) provient de `src/graphics/sprite/sprites.tsv` (513 lignes ; ligne = id ; colonnes width, height, scale, drawKind, adjust, box, codec, frames, animations). Largeur 0 = pas d'image (`src/field/field/animation.c:512`).
- **Règle des PNG** (`tools/ags-graphics/sprite.c:120-160,295-330`) :
  - `graphics/sprite/spr_NNN.png` de la ligne qui possède les images ; une ligne alias s'écrit `SPR_X=SPR_Y`.
  - La planche est une bande verticale, l'image k étant à y = k·height. Un `spr_NNN.tsv` facultatif `list` réordonne les images, et ses lignes `anim` sont les animations.
  - Palette : 8bpp, utilisant la palette partagée de 224 couleurs `gSystem_BasicColorPalette` (`src/runtime/runtime/text.c:199`), intégrée à chaque PNG, index 0 transparent.
- **Image d'aperçu :** la première commande d'image de l'animation 1 (les valeurs < 239 sont des images ; 240 règle le type de dessin ; 254 saute vers une autre animation ; `src/field/field_internal.h:83-91`), plus le décalage d'orientation pour ce type de dessin (`src/field/facing.c`, appliqué dans `src/field/field/sprite_draw.c:150-185` ; bit 7 = en miroir). Utiliser l'orientation 0x3800 pour une vue de face droite. À exactement 0x4000, les types 3 et 5 dessinent base+0 en miroir.
- **Identifiants spéciaux :**
  - 20 coffre au trésor (VÉRIFIÉ, `markers.c:70`).
  - 28 Pierre de Psynergie (VÉRIFIÉ, `markers.c:105`).
  - 22 marqueur invisible de 16×16, utilisé 68× pour les comptoirs et les emplacements d'objets.
  - 4 et 7 ont des lignes vides.
  - 261-279 et 504 sont des icônes de la carte du monde.
  - Les tables de placement utilisent les identifiants 0..504.
- **Noms.** Il n'y a pas d'énumération globale des sprites. Les noms viennent de :
  - `include/game/character_ids.h` ;
  - énumérations `SPRITE_*` locales aux fichiers (`src/scene/lunpa.h`, `vault_jail.c`, `tunnel_ruins.c`, `altin.c`, `altin_peak.c`, `tret_tree_*.c`, …) ;
  - commentaires de lignes.

  Cela donne 71 noms VÉRIFIÉS. Les 178 autres sont DÉDUITS de l'image et des scènes qui utilisent l'identifiant (p. ex. « Townsperson A », « Dog ») ; `name_evidence` indique lesquels.
- Les planches-contacts ont été vérifiées à l'œil : images de face et couleurs correctes, pas de déchets. Ce sont `sprites/contact_sheet_npc60.png` et `sprites/contact_sheet_all.png` dans le travail temporaire.

**Données de l'éditeur :** `names/sprites.json` (généré par `scripts/sprites/build_sprites.py`, avec `spritelib.py`, `usage.py`, `names.py`, `names_manual.py` et `sheet.py`) :
```json
[{"id":28,"hex":"0x1c","name":"Psynergy Stone","confidence":"VERIFIED","name_evidence":"...",
  "usage":1,"scenes":["MogallForest1"],"party_slot":false,"has_image":true,
  "png":"games/tbs/src/graphics/sprite/spr_028.png","frame":{"x":0,"y":0,"w":16,"h":16},
  "frame_index":0,"mirrored":false,"palette":{...},"draw_kind":11,"animation":1,"base_frame":0,
  "sheet_frames":11,"scale":256,"adjust":[0,2],"box":[20,16],"evidence":"sprites.tsv row 28 ..."}]
```
L'interface recadre `png` sur `frame` (en miroir si indiqué) à l'exécution. Un fichier de surcharge « modifier le nom » côté éditeur est recommandé pour les noms DÉDUITS.

---

## 4. Noms de lieux

- `Scene_GetAreaNameIndex(scene, entrance)` (`src/object/object/encounter.c:326-350`) parcourt `gScene_AreaNameRules` (`src/object/scene_rules.s:168-301`). Chaque ligne est `scene_name Scene, entrance, index` ou `group_name group, entrance, index` (`scene_rules.s:12-20`). La **première** ligne correspondante l'emporte ; l'entrée -1 correspond à n'importe quelle entrée. Groupe = `gField_SceneTable[scene].group` (`src/object/object/scene.c:157-159` ; la colonne dans `src/field/scenes.s`). Sans correspondance, on obtient l'index 0. (VÉRIFIÉ)
- Texte = message **`MsgDebugEntryName` + index** (`src/object/psynergy_effects/world_map.c:400`, `src/window/battle_command/debug.c:23`). En EN, `MsgDebugEntryName` = 2459 = `RENDER_RESOURCE_BASE` 0x99B pour les éditions non européennes patchées (`include/tbs_edition.h:264-271`, utilisé par `src/window/window/shortcuts.c:29`). Lire la base dans le `msgctxt "MsgDebugEntryName"` de en.po, et non comme une constante. (VÉRIFIÉ)
- Les lignes `.if EDITION_INTERNATIONAL` (Altin Peak 4, entrées 6/7) sont actives pour EN (`include/game/ed_asm.h:11-16`).
- Résultat :
  - 199/201 scènes reçoivent un nom ; Title (0) et LinkLobby (190, nommée seulement pour l'entrée 1) non.
  - 21 scènes n'ont pas de symbole dans `scenes.s`, elles sont donc étiquetées « Scene N » plus le nom de leur zone.
  - Des noms propres à une entrée existent, p. ex. Sanctum : 1/2/20/21 Vale Sanctum, 10-12 Vault Sanctum, 35 Bilibin, 32 Xian, 29 Altin ; entrée 2 de VaultJail = « Lunpa ».
  - Affichage : « {area_name} — {label} », p. ex. « Vale — Vale Home ». Les noms de zone se répètent sur de nombreuses scènes, l'étiquette de scène lève donc l'ambiguïté.

**Données de l'éditeur :** `names/places.json` (généré par `scripts/places.py`) :
```json
{"area_message_base":2459,
 "scenes":[{"id":5,"symbol":"ValeHome","label":"Vale Home","group":3,"variant":2,"overlay":"0x374",
            "layered_row":4,"map":"003","area_index":10,"area_name":"Vale",
            "area_name_by_entrance":{},"area_message":2469}]}
```

---

## 5. Dialogues

- **Schéma de en.po** (VÉRIFIÉ). Chaque entrée est `msgctxt "<symbol>|message"`, `msgid "NNNNN"` (le numéro de message, complété par des zéros sur 5 chiffres) et `msgstr` (texte). Il y a 10,723 entrées, 0..10722, sans trous. Les symboles ressortent dans `out/tbs-en/text/msg_ids.h` (`#define TEXT_MESSAGE_NUMBER_<Sym> n`, `MSGNO(name)`). Le C des scènes écrit `MSGNO(MsgX)` dans les tables et `MsgX` seul dans le code (`src/scene/README.md:60-61`).
- **Balisage du texte :** `{page_break}` (nouvelle boîte), `{end_wait}` / `{end_now}` (fin), `{line_break}`, et les arguments `{protagonist_name}`, `{actor_name:N}`, `{argument_item_name:N}`, `{text_color:…}`, `{article_class:N}` (`tools/ags-text/symbols.c:28-60`). Un `\n` littéral est une ligne d'affichage. Afficher les noms sous forme d'emplacements comme « [Isaac] ».
- **Recherche du dialogue** (`Scene_TalkToActor`, `src/object/object/events.c:197-290` ; `Scene_FindEvent` `:111-165`) :
  - Type 0 `EVENT_TALK`, avec déclencheur = identifiant d'acteur = 8 + ligne de placement.
  - La première ligne dont la condition est vraie l'emporte (-1 toujours ; `flag|0x1000` = mis ; sinon non mis), donc un PNJ peut avoir plusieurs lignes choisies selon des drapeaux d'histoire.
  - `value < 0x10000` → un seul message. Les 881 messages de dialogue directs se terminent tous par `{end_*}` (relevé), donc un identifiant constitue toute la réplique.
  - Sinon la valeur est un script. Le type 7 est la réplique dite quand le groupe a arrêté l'acteur (`events.c:175-186`).
  - `talkFacing` contrôle le fait de se retourner.
- Pour les scripts, le dialogue est l'ensemble des symboles `Msg*` du corps de la fonction. Exemple : `Event_TalkAboutTheMayorAndTremors` (`src/scene/vale.c:160`) affiche `MsgValeTheGroundStillShakes` ou `MsgValeYourGrandpaIsTheMayor` selon `FLAG_PARTY_LEFT_VALE`. Cela donne une liste de répliques possibles, pas leur ordre ni leurs conditions (DÉDUIT suffisant pour les aperçus).
- Les points de fouille affichent `MsgTileChecked + target` puis le texte `FIND_MESSAGE` ou de résultat (`events.c:452-470`).

**Données de l'éditeur :** `dialogue.json` (travail temporaire, 650 Ko, généré par `scripts/dialogue.py` ; 152 scènes, 2,475 lignes de dialogue). Il contient du texte du jeu, l'éditeur le génère donc à l'exécution :
```json
{"4":{"symbol":"Vale","tables":{"gVale_Events":[
  {"actor":8,"placement_row":0,"kind":"talk|talk_paused","condition":null|{"flag":2069,"when":"set|clear"},
   "message":3967,"msgctxt":"MsgValeMtAlephLooksBeautifulTodayIts","text":"Mt. Aleph looks\nbeautiful today..."},
  {"actor":10,"placement_row":2,"kind":"talk","condition":null,"script":"Event_TalkAboutTheMayorAndTremors",
   "source":"src/scene/vale.c","script_messages":[{"message":4556,"text":"..."}]}]}}}
```
Modifier du texte signifie modifier le `msgstr` de `text/en.po` par msgid. Les 5 autres catalogues de langue doivent garder le même ensemble de msgid (`src/game/README.md:97-110`).

---

## 6. Drapeaux

- **Stockage :** 4,096 bits dans `gGameFlagBytes`. Les bits 0-2 du numéro de drapeau choisissent le bit et les bits 3-11 l'octet (`src/game/game/flags.c:7-24`, `include/game/game_flags.h:12`). Les accesseurs par octet traitent 8 drapeaux consécutifs comme un compteur (`src/game/README.md:110-121`). Tous sont sauvegardés (README ; la somme de contrôle de la sauvegarde couvre `gGameFlagBytes`, `include/save_state.h:55`).
- **Conditions :** `-1` toujours, `flag|0x1000` = mis, sinon le drapeau n'est pas mis. 0 sur un placement = « en vue » (`events.c:59-77`).
- **Plages** (`src/scene/README.md:48-59`, `include/flags.h:7-20`) :
  - 0x000-0x0ff : groupe (0-7) et Djinn (48-127).
  - 0x100-0x1ff : moteur/système.
  - **0x200-0x2ff : temporaires de scène, effacés à chaque entrée.**
  - **0x300-0x3ff : drapeaux de groupe, réinitialisés en entrant dans un autre groupe, numéros réutilisés selon le lieu.**
  - 0x400-0x7ff : aucune utilisation trouvée (une référence, 0x400 ; DÉDUIT inutilisé, mais à éviter).
  - 0x800-0xdff : histoire.
  - 0xe00-0xfff : drapeaux de coffre/trouvaille.
- **Nommage :** `include/flags.h` (970 lignes) `#define FLAG_* value` avec des commentaires `///`, p. ex. `FLAG_ALTIN_PEAK_LUCKY_MEDAL 0xf78 ///< room 8's chest`. Les drapeaux locaux à une scène sont définis par `#define` dans le fichier de la scène et ne figurent pas dans flags.h.
- **Relevé d'utilisation** (`flags_survey.py`, VÉRIFIÉ dans la limite de ses sources) :
  1. Chaque condition, requiredFlag, drapeau de sortie et condition de région dans les tables des overlays construits.
  2. Chaque appel d'accesseur de drapeau avec un argument constant dans la sortie `clang -E` de chaque `src/**/*.c`. La sortie va uniquement sur stdout et alchemy n'est pas touché.
  3. Les champs de drapeau des lignes `scene_cue`/`group_cue`/`location` de `scene_rules.s` et `location_rules.s`.
  4. Toutes les définitions de flags.h.

  Trouvés utilisés : 0xe00-0xfff 213/512 ; 0x800-0xdff 300 ; 0x300-0x3ff 108.
- **Liste libre prudente** (`flags_free.py`) : exclut en plus toute valeur 0xe00..0xfff (ou sa forme de condition 0x1e00) qui apparaît comme littéral hexadécimal n'importe où dans `src`/`include`, hors graphismes et données de carte. Il reste **251 drapeaux libres**. Séries : 0xe03-0xe0f, 0xe49-0xe58, 0xe61-0xe73, 0xe81-0xea1, 0xef8-0xeff, 0xf09-0xf12, 0xfdb-0xfe0, … (`flags.json` `free_chest_flags`).
- **Règle d'allocation pour un nouveau coffre :**
  1. Prendre le plus bas drapeau de `free_chest_flags` qui n'est pas déjà utilisé par les tables de surcharge propres au mod (`games/tbs/src/mod/`) ni par d'autres modifications en attente.
  2. L'écrire comme condition de l'événement `SEARCH(SEARCH_CHEST)`.
  3. L'enregistrer dans le manifeste du mod pour qu'il ne soit jamais réutilisé, même après la suppression du coffre (d'anciennes sauvegardes peuvent l'avoir mis).
  4. Revérifier à chaque mise à jour de la version épinglée d'alchemy en relançant le relevé ; la liste libre dépend du commit.
- **Vérifier qu'un drapeau est inutilisé**, dans cet ordre :
  1. Il n'est pas dans `used` d'une exécution récente de `flags_survey.py` (tables + code + règles).
  2. Il n'y a aucune correspondance de littéral hexadécimal (`flags_free.py`).
  3. Il n'est dans l'octet d'aucun drapeau à accesseur par octet (le relevé marque les 8).
  4. Il n'est pas dans 0x200-0x3ff.
  5. Après la construction, chercher avec `grep` le demi-mot dans le `.bin` de l'overlay n'est **pas** fiable (faux positifs), donc s'en tenir à 1-4.

**Données de l'éditeur :** `names/flags.json` (généré à partir des deux scripts) :
```json
{"total_flags":4096,
 "ranges":[{"lo":3584,"hi":4095,"meaning":"chest / find flags","editor":"allocate new chest flags here"}],
 "names":{"0xf78":["FLAG_ALTIN_PEAK_LUCKY_MEDAL"]},
 "used":{"0xf78":["flags.h","table 3a4:gAltinPeak_Events..."]},
 "free_chest_flags":[3585,3587,...]}
```

---

## Fichiers générés et comment ils ont été produits

Tous les scripts sont dans `names/scripts/` (copies) et dans le répertoire de travail ci-dessus. Ils dépendent du `gsmap` de gs-mapedit (Project, Scenes, grid) et de `out/tbs-en`.

| Fichier | Script | Entrées |
|---|---|---|
| `names/collision.json` | `collision_json.py` (après `coll_hist.py`) | lecture du moteur ci-dessus ; histogramme sur `src/map/*/grid_collision.tsv` |
| travail temporaire `collision_by_map.json` | `collision_legend.py` | grilles + tables d'événements/sorties construites + `places.json` + `items.json` + en.po |
| `names/items.json` | `items/build_items.py` | `src/game/items.tsv`, en.po, `item_ids.h`, `graphics/ui/menu_icons/` |
| travail temporaire `items/search_events.json` | `items/survey_chests.py` | tables d'événements construites |
| `names/sprites.json` | `sprites/build_sprites.py` (+ `spritelib.py`, `usage.py`, `names.py`, `names_manual.py`, `sheet.py`) | `graphics/sprite/sprites.tsv`, `spr_*.png`/`.tsv`, tables de placement construites, sources des scènes |
| `names/places.json` | `places.py` (+ `po.py`) | `src/field/scenes.s`, `src/object/scene_rules.s`, en.po, `layered.tsv` via gsmap |
| travail temporaire `dialogue.json` | `dialogue.py` | tables d'événements construites, symboles ELF des overlays, `src/scene/**`, `out/tbs-en/text/msg_ids.h`, en.po |
| `names/flags.json` | `flags_survey.py` → `flags_free.py` → fusion en ligne | tables construites, `clang -E` de `src/**/*.c`, fichiers `.s` de règles, flags.h |

Les images (atlas d'icônes, planches-contacts) et le texte du jeu ne sont volontairement pas versionnés ; conformément à la position juridique de PRODUCT.md, l'application les construit à partir de la copie du joueur.

## Inconnues

- Ce que signifie 248 (aucun lecteur, inutilisé), et si 241 fonctionne comme prévu (aucune carte ne l'utilise).
- Les codes 96..99 (Altin Peak) et 136 paires (carte, code) dans 1..239 n'ont pas d'événement statique. Ils sont vraisemblablement lus par le code des scènes (appelants de `GetMapCellCollision`) ou sont des restes.
- La signification des collisions sur la **carte du monde** est un système distinct (octet de pas de `blocks.tsv`, `attributes.tsv`) : voir `overworld.md`.
- L'écrivain de `touched_trigger`, et les bits hauts du contrôle d'événement sur 22 coffres (0x400, 0x8400, 0xc400). Le bit 0x400 du *déclencheur* saute la réplique « checked » ; la signification des bits de contrôle n'est pas confirmée.
- L'emplacement de palette en jeu pour les icônes d'objets (on suppose la palette du PNG).
- Les 178 noms de sprites DÉDUITS. Certains sont des suppositions (p. ex. 44 « Dodonpa », 66/67, 69 « Lady Layana »). La limite d'index d'acteur 0x2705 est marquée XXX dans la source. JA/IT utilisent `spriteja.tsv`/`spriteit.tsv`.
- Si un message sans `{end_*}` se poursuit dans l'identifiant suivant. Aucun message de dialogue direct n'en manque, cela n'a donc pas d'importance pour les aperçus.
- Le relevé des drapeaux manque les drapeaux atteints seulement par des variables ou des expressions calculées (5,191 appels d'accesseur non constants, définitions et boucles comprises) et les drapeaux dans les tableaux de données C. La passe sur les littéraux hexadécimaux couvre la plupart de ces cas ; 0x400-0x7ff semble inutilisé mais ce n'est pas prouvé.
- Si l'emplacement de mimique peut dépasser 7 sans danger (il lit dans la zone suivante, ce n'est donc pas utile).
