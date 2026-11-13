<!-- translated from docs/PRODUCT.md @ 34e70fd313ab -->
# gs-mapedit pour les joueurs : plan produit

*Ceci est une traduction du document anglais [PRODUCT.md](../PRODUCT.md) ; en cas de différence, c'est la version anglaise qui fait foi.*

**Public :** des fans et moddeurs sans formation technique, c'est-à-dire sans terminal, hexadécimal, C, git ni systèmes de compilation.
**Livraison :** une application de bureau empaquetée avec un installateur.
*(Décidé par le propriétaire du projet, 2026-10-20.)*

La couche moteur qui existe aujourd'hui reste la fondation. Elle couvre les formats de fichiers, les enregistrements exacts à l'octet près, les invariants, le point d'accroche des tables de scène et la compilation. Ce plan porte sur la couche que voient les joueurs.

## Principes

1. **Des noms, des images et des lieux, jamais des codes.** Chaque valeur que voit un joueur est nommée, prévisualisée ou montrée sur une carte. Les nombres bruts restent derrière une option « Avancé ».
2. **Une intention, une action.** « Ajouter un coffre avec un Herb » devient une seule action, même si elle touche la liste des marqueurs, la collision, un événement de scène et un nouveau drapeau.
3. **Impossible de casser le jeu sans le savoir.** Les invariants sont imposés comme aujourd'hui, et expliqués en termes simples : « Cette porte ne mène encore nulle part. » (✅ le bouton Vérifier, lancé aussi avant chaque compilation.)
4. **Toujours à un clic de jouer.** Modifier, puis Jouer. La compilation est invisible sauf si elle échoue, et les échecs se lisent comme des conseils, pas comme une sortie de compilateur.
5. **Aucune distribution de ROM.** Les mods sont partagés sous forme de fichiers patch que les joueurs appliquent à leur propre dump de cartouche.

## Ce que font les joueurs (parcours → écrans)

| Parcours | Écran / interaction | Briques du moteur (existent ?) |
|---|---|---|
| Explorer les lieux du jeu | **Vue du monde :** le monde extérieur plus chaque ville/donjon, avec les connexions dessinées | Moteur de rendu ✅, vue Connexions ✅ (lieu par lieu), Atlas ✅ (tous les lieux d'un coup), Y aller ✅ (suivre une porte), monde extérieur ✅ |
| Repeindre une partie d'une carte | **Peindre :** palette de tuiles par thème, pinceaux, remplissage, copier/coller de zones | Peinture de blocs ✅ ; Remplir ✅ ; copier-coller (Tampon) ✅ |
| Changer où l'on peut marcher | **Pinceau de praticabilité :** praticable / bloqué / rebord / échelle / eau, montré comme une surcouche nette | Peinture de collision ✅ ; **codes nommés ❌ (recherche)** |
| Déplacer une porte / changer sa destination | Cliquer sur une porte, puis choisir la destination en cliquant sur la carte cible | ✅ outil Portes |
| Ajouter/déplacer un coffre ou une Pierre de Psynergie | Poser un coffre ; choisir son contenu (sélecteur d'objets avec icônes, pièces, mimique) | ✅ outil Coffre (objets, pièces) ; les pierres se déplacent seulement |
| Placer/déplacer des personnages | Faire glisser les PNJ avec aperçus de sprites ; voir et modifier ce qu'ils disent | Positions ✅ ; aperçus de sprites ✅ ; ce qu'ils disent au survol ✅ ; ajout et suppression ✅ |
| Essayer | **Jouer :** compiler puis ouvrir l'émulateur sur cette carte | Jouer en un clic ✅ (enregistre, vérifie, compile, ouvre au lieu en cours de modification) |
| Partager | **Exporter le mod :** un fichier patch plus une description | ✅ BPS de la version d'origine à la version moddée |
| Annuler les erreurs / tout recommencer | Panneau d'historique ; « réinitialiser cette carte » | Annuler et Rétablir ✅ (les 30 dernières actions enregistrées, conservées d'une session à l'autre) ; Réinitialiser le lieu ✅ |

## Couche de noms (recherche nécessaire, surtout des consultations)

- **Codes de collision :** mur, sol, rebords, points d'escalade, cases de fouille, danger, sorties, coffres. Sources : `step.c`, `events.c`, les documents de recherche.
- **Scènes :** les noms de `scenes.s` plus les noms de zones (les noms de lieux du jeu lui-même) pour l'affichage.
- **Objets :** les noms de `include/item_ids.h`, plus les icônes d'objets tirées des graphismes du jeu.
- **Sprites :** id de sprite → nom et image d'aperçu tirée des graphismes des objets.
- **Dialogues :** id de message → texte de `text/en.po` (10 724 entrées).
- **Drapeaux :** les noms de `include/flags.h`, plus un allocateur de nouveaux drapeaux de coffre (≥ 0xe00, inutilisés).

## Architecture d'empaquetage (recommandation)

- **Enveloppe :** pywebview (le WKWebView natif) dans un paquet PyInstaller : un seul `.app` de 30 Mo contenant Python, le serveur et les pages. *(Changé depuis Tauri, 2026-10-22 : le backend est déjà en Python, et Tauri ajouterait une chaîne d'outils Rust sans gain pour l'instant. Tauri reste une option si le backend passe à Rust.)*
- **Backend :** le serveur Python actuel, dans le même processus.
- **Source du jeu :** l'application télécharge alchemy à un commit épinglé que nous avons vérifié. Les joueurs ne voient jamais git. Les mises à jour sont explicites : « Nouvelle version d'alchemy disponible ; testée ✓ ».
- **Chaîne d'outils :** la partie la plus difficile.
  - alchemy a besoin de ses compilateurs épinglés (construits à partir des sources), de binutils et de ses propres outils C (libpng).
  - Plan : les construire par plateforme en CI et les livrer sous forme de binaires précompilés. Les compilateurs sont sous GPL ; nous publions leurs sources.
  - Plateformes : macOS d'abord (Intel + Apple Silicon), puis Windows (alchemy ne prend officiellement en charge Windows que via WSL, donc un portage natif des outils est le risque), puis Linux.
- **Patchs :**
  - Comme la version d'origine est identique à l'octet près à la ROM du commerce, un patch = diff(version d'origine, version moddée), calculé localement sans jamais toucher à une ROM du commerce.
  - Les joueurs l'appliquent à leur propre dump avec n'importe quel patcheur BPS, ou avec notre application.
- **Test en jeu :** embarquer mGBA (MPL-2.0) ou détecter une installation existante ; lancer sur la carte modifiée si un point d'entrée de debug le permet.

## Jalons

1. **Interface pour les joueurs dans l'application actuelle.** Tout ce qui est ici passe directement dans l'enveloppe de bureau. Cela couvre :
   - la couche de noms ;
   - les pinceaux de praticabilité ;
   - les portes reliées par un clic ;
   - les sélecteurs d'objets/de sprites ;
   - une action d'ajout de coffre ;
   - la validation en termes simples ;
   - la vue du monde/des connexions.
2. **Essai d'empaquetage (macOS) :** ✅ paquet d'application et installation au premier lancement (télécharge alchemy, compile une fois). ✅ chaîne d'outils embarquée (sans Homebrew). Reste à faire : signature/notarisation (nécessite un Developer ID), compilation native Apple Silicon, un test sur un Mac vraiment neuf. Réussite = un Mac neuf passe de zéro à « Jouer » sans terminal.
3. **Export de patch** ✅ (BPS, vérifié par rapport à rom.sha1). Appliquer les patchs des autres ✅ (le Patcheur).
4. **Édition du monde extérieur** ✅ (étapes 4–5 de SPEC.md) : sol, surcouche, régions et leurs combats, icônes de villes (déplacées, reliées, ajoutées), cases de passage.
5. **Empaquetage Windows et Linux.** Windows fonctionne via WSL avec un script d'installation (premiers tests) ; Linux tourne depuis les sources.

## Risques

- **Portabilité de la chaîne d'outils (Windows).** La compilation d'alchemy suppose un shell Unix. Cela peut nécessiter une intégration WSL ou un portage natif de ses petits outils C.
- **Évolution en amont.** alchemy change tous les jours. Épingler un commit, et conditionner les mises à jour à nos vérifications d'aller-retour et de rendu complet ainsi qu'à une compilation de test.
- **Portée du « sens ».** Certains codes de collision et types d'événements restent inconnus même d'alchemy. Les inconnus restent visibles mais étiquetés « inconnu (avancé) ».
- **Position juridique :** nous ne livrons jamais de ROM, de ressources extraites ni de jeux compilés. Les joueurs ne fournissent rien (The Broken Seal se compile à partir des sources), et l'application télécharge alchemy elle-même.
