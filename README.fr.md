<!-- translated from README.md @ 1a86f855b136 -->
# GS Map Editor

[English](README.md) · [Español](README.es.md) · [Deutsch](README.de.md) · **Français** · [Italiano](README.it.md) · [日本語](README.ja.md)

*Ceci est une traduction du guide anglais [README.md](README.md). Si les deux diffèrent, c'est la version anglaise qui fait foi.*

Créez votre propre version de **Golden Sun: The Broken Seal** sans écrire de code. Repeignez des villes, cachez des coffres, écrivez de nouveaux dialogues, ajoutez des personnages et des portes, remodelez la carte du monde, puis appuyez sur **▶ Jouer** et promenez-vous dans votre modification. Quand vous en êtes satisfait, exportez un petit patch à partager.

L'éditeur s'appuie sur [alchemy](https://github.com/PascalPixel/alchemy), un projet qui reconstruit le jeu à partir de fichiers source lisibles. Il compile votre jeu à partir de cette source sur votre propre ordinateur : vous n'avez donc pas besoin de ROM pour créer un mod.

> **Avant-première : testeurs recherchés.** L'éditeur couvre l'édition anglaise de The Broken Seal, sur macOS et, à titre de premier essai, sur Windows. Il a surtout été testé sur un seul Mac Intel, et la version Windows n'a jamais tourné sur un vrai PC Windows : chaque retour compte, y compris « ça a marché » : [téléchargez-le](https://github.com/TRosenvall/GS-Map-Editor/releases), essayez-le et [dites-nous comment ça s'est passé](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md). Gardez une sauvegarde de tout mod auquel vous tenez.

**Version d'alchemy :** cet éditeur est testé avec le commit d'alchemy [`5ca23b1fe1`](https://github.com/PascalPixel/alchemy/commit/5ca23b1fe1774f954aacfbd7db35c8c9b9a59184) (2026-11-12). L'installation télécharge exactement ce commit. Alchemy évolue vite : une copie plus récente risque de ne pas fonctionner tant que l'éditeur ne l'a pas rattrapée.

## Sommaire

- [Pour commencer](#pour-commencer)
- [Votre premier mod en deux minutes](#votre-premier-mod-en-deux-minutes)
- [L'éditeur en un coup d'œil](#léditeur-en-un-coup-dœil)
- [Enregistrer et annuler](#enregistrer-et-annuler)
- [Regarder la carte](#regarder-la-carte)
- [Peindre : l'apparence du sol](#peindre--lapparence-du-sol)
- [Praticabilité : où l'on peut marcher](#praticabilité--où-lon-peut-marcher)
- [Hauteur : la hauteur du sol](#hauteur--la-hauteur-du-sol)
- [Coffres](#coffres)
- [Événements : personnages, panneaux et messages](#événements--personnages-panneaux-et-messages)
- [Portes](#portes)
- [Déplacer les personnages](#déplacer-les-personnages)
- [Tampon : copier et coller](#tampon--copier-et-coller)
- [Importer vos propres images](#importer-vos-propres-images)
- [Tables d'histoire et de scène](#tables-dhistoire-et-de-scène)
- [Combats dans un lieu](#combats-dans-un-lieu)
- [Connexions](#connexions)
- [Atlas : tous les lieux d'un coup](#atlas--tous-les-lieux-dun-coup)
- [La carte du monde](#la-carte-du-monde)
- [Vérifier : trouver les problèmes](#vérifier--trouver-les-problèmes)
- [Jouer à votre jeu](#jouer-à-votre-jeu)
- [Partager votre mod](#partager-votre-mod)
- [Jouer au mod de quelqu'un d'autre](#jouer-au-mod-de-quelquun-dautre)
- [Où se trouve votre travail](#où-se-trouve-votre-travail)
- [Raccourcis clavier](#raccourcis-clavier)
- [Ce qu'il ne sait pas encore faire](#ce-quil-ne-sait-pas-encore-faire)
- [Dépannage](#dépannage)
- [Signaler un problème](#signaler-un-problème)
- [Mentions légales](#mentions-légales)

## Pour commencer

### Ce qu'il vous faut

- Un Mac sous macOS 11 ou plus récent, ou un PC sous Windows 10 ou 11.
- Environ 3 Go d'espace libre pour la source du jeu et sa compilation.
- [mGBA](https://mgba.io/downloads.html), un émulateur Game Boy Advance gratuit, pour jouer à votre jeu (sous Windows, son installateur Windows).
- Une connexion Internet pour la première installation.

### Obtenir l'application (Mac)

Téléchargez le `.dmg` le plus récent depuis les [Releases](https://github.com/TRosenvall/GS-Map-Editor/releases) :

- **AppleSilicon** pour les Mac équipés d'une puce M1, M2, M3, M4 ou plus récente ;
- **Mac-Intel** pour les Mac Intel.

Vous ne savez pas lequel vous avez ? Menu Pomme → **À propos de ce Mac** : « Puce : Apple M… » signifie Apple Silicon.

Ouvrez le `.dmg` et faites glisser **GS Map Editor** dans **Applications**.

### Premier lancement (Mac)

L'application n'est pas encore signée avec un certificat de développeur Apple, donc macOS vous avertit la première fois :

1. Ouvrez-la depuis Applications. macOS indique qu'il ne peut pas vérifier l'application : appuyez sur **Terminé** (ou **Annuler**).
2. Ouvrez **Réglages Système → Confidentialité et sécurité**, faites défiler vers le bas et appuyez sur **Ouvrir quand même** à côté de GS Map Editor. Confirmez avec votre mot de passe.

Sous macOS 14 et versions antérieures, vous pouvez à la place faire un clic droit sur l'application, choisir **Ouvrir**, puis **Ouvrir** à nouveau. Après la première fois, elle s'ouvre normalement.

Si vous préférez compiler l'application vous-même, suivez [Application de bureau](docs/fr/DEVELOPING.md#application-de-bureau-macos) dans les notes pour développeurs. Si vous êtes à l'aise avec un terminal et avez déjà une copie d'alchemy compilée, vous pouvez vous passer de l'application et lancer `python3 server.py --root /path/to/alchemy`, puis ouvrir http://127.0.0.1:8765/.

### Obtenir l'éditeur (Windows, premier essai)

L'éditeur tourne dans WSL, le Linux intégré à Windows, car c'est la seule façon de compiler la source du jeu sous Windows. Il s'ouvre dans votre navigateur web.

1. Téléchargez `Install-GS-Map-Editor.cmd` depuis les [Releases](https://github.com/TRosenvall/GS-Map-Editor/releases). Si votre navigateur indique qu'il n'est pas fréquemment téléchargé, choisissez **Conserver**.
2. Double-cliquez dessus. Windows indique qu'il a protégé votre PC parce que l'installateur n'est pas encore signé : appuyez sur **Informations complémentaires**, puis sur **Exécuter quand même**.
3. La première fois, il active WSL et installe Ubuntu. Windows demande l'autorisation d'administrateur et peut vous demander de redémarrer ; dans ce cas, redémarrez et double-cliquez à nouveau sur l'installateur.
4. Quand Ubuntu le demande, choisissez un nom d'utilisateur et un mot de passe. Rien ne s'affiche quand vous tapez le mot de passe ; c'est normal. L'étape suivante vous le redemande.
5. L'installateur met en place l'éditeur dans Ubuntu et ajoute **GS Map Editor** à votre menu Démarrer et à votre bureau.

Ouvrez **GS Map Editor**. Une petite fenêtre apparaît ; gardez-la ouverte pendant que vous utilisez l'éditeur, car la fermer arrête l'éditeur. L'éditeur s'ouvre dans votre navigateur. Relancer l'installateur met l'éditeur à jour vers la version fournie avec celui-ci.

Sous Windows, les raccourcis clavier utilisent Ctrl là où ce guide indique ⌘, et Alt là où il indique ⌥. Les patchs exportés et les jeux patchés vont dans **Documents\\GSMapEditor**, comme sur Mac. La source du jeu et ses compilations restent dans Ubuntu, dans `GSMapEditor` de votre dossier personnel Ubuntu, car la compilation y est beaucoup plus rapide ; l'Explorateur de fichiers l'affiche sous **Linux → Ubuntu → home**.

### Installation au premier lancement

La première fois, l'éditeur s'ouvre sur une liste d'étapes. Cela prend environ 15 minutes, surtout de l'attente. Appuyez sur le bouton de chaque étape et l'éditeur fait le reste :

1. **Les outils de développement d'Apple** (Mac uniquement) : ouvre l'installateur d'Apple.
2. **Les outils pour compiler le jeu :** déjà inclus dans l'application sur Mac, et mis en place par l'installateur sous Windows.
3. **La source du jeu :** télécharge alchemy dans `~/Documents/GSMapEditor/` (sous Windows, `GSMapEditor` dans votre dossier personnel Ubuntu). Si vous en avez déjà une copie, choisissez **J'en ai déjà une copie…** et sélectionnez son dossier.
4. **Préparation de la compilation :** installe les compilateurs du jeu, une seule fois.
5. **Une première compilation du jeu :** compile le jeu une fois.

Appuyez ensuite sur **Ouvrir l'éditeur**. Par la suite, l'application s'ouvre directement sur l'éditeur.

## Votre premier mod en deux minutes

1. Choisissez un lieu dans la liste à gauche. Tapez dans la case **Trouver un lieu** pour chercher.
2. Appuyez sur **Coffre** dans la barre du haut, puis cliquez sur un bout de sol vide.
3. Tapez le nom d'un objet, par exemple `Herb`, et appuyez sur **Ajouter un coffre**.
4. Appuyez sur **▶ Jouer**. Votre jeu s'ouvre dans mGBA, dans le lieu que vous modifiiez, quelques secondes après le démarrage du jeu.
5. Approchez-vous du coffre et ouvrez-le.

## L'éditeur en un coup d'œil

| Zone | Ce qu'on y trouve |
|---|---|
| **Gauche** | La liste des lieux. La carte du monde est en haut. |
| **Barre du haut** | Le zoom, les calques, les surcouches, les outils, et les boutons pour enregistrer, vérifier et jouer. |
| **Milieu** | La carte. |
| **Droite** | Le panneau de l'outil que vous utilisez. |
| **Ligne du bas** | Les messages d'état. Quand vous survolez la carte, elle indique ce que fait la case sous votre curseur, par exemple « Coffre : Herb » ou la destination d'une sortie, et de quelle case il s'agit. Les numéros de case sont ceux qu'utilisent Vérifier, les portes et les coffres. |

Cochez **Avancé** dans la barre du haut pour afficher les nombres et codes bruts et un bouton **Compiler** séparé. Vous n'en aurez pas besoin pour une utilisation normale.

### Langues

L'éditeur parle anglais, espagnol (Español), allemand (Deutsch), français (Français), italien (Italiano) et japonais (日本語). Il démarre dans la langue de votre ordinateur s'il la connaît. Changez-la avec le menu 🌐, en haut à droite du premier écran d'installation et au bout de la barre du haut. Seuls les mots de l'éditeur changent : le jeu que vous modifiez est l'édition anglaise, donc les noms de lieux, les personnages, les objets et les dialogues que vous écrivez restent en anglais.

Ce guide est aussi traduit : voir les liens en haut. Les traductions de l'éditeur et de ce guide ont été faites avec l'aide de l'IA et n'ont pas encore toutes été relues par des locuteurs natifs. Là où un guide traduit diffère de celui-ci, c'est le guide anglais qui fait foi. Si quelque chose sonne bizarrement, merci de [le signaler](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md) en indiquant la formulation que vous attendiez.

## Enregistrer et annuler

Certaines modifications attendent que vous enregistriez, d'autres sont enregistrées tout de suite :

| Attend **Enregistrer** (ou ⌘S) | Enregistré immédiatement |
|---|---|
| Peindre, Praticabilité, Hauteur | Ajouter, changer ou supprimer un coffre |
| Collages du Tampon | Événements et portes |
| Faire glisser des coffres, des pierres et des personnages | Peinture de la carte du monde et déplacement des villes |

L'éditeur enregistre aussi pour vous avant que vous changiez de lieu, alliez sur la carte du monde ou appuyiez sur Jouer : passer à autre chose ne vous fera donc pas perdre votre travail. Si un enregistrement est refusé, vous restez où vous êtes et la ligne du bas indique pourquoi.

Il y a trois façons de revenir en arrière :

- **Annuler** (⌘Z) défait votre dernière modification, quelle qu'elle soit : d'abord la peinture pas encore enregistrée, puis les actions enregistrées, de la plus récente à la plus ancienne, depuis n'importe quel outil et n'importe quel lieu. Ajouter un personnage, un coffre, une porte, un événement, un trait sur la carte du monde : tout y passe. L'infobulle du bouton indique ce qu'il va annuler et où, et l'éditeur ouvre ce lieu pour vous le montrer. Les 30 dernières actions enregistrées sont conservées, même après la fermeture de l'éditeur.
- **Rétablir** (⇧⌘Z) remet ce qu'Annuler a défait, jusqu'à ce que vous fassiez une nouvelle modification.
- **Réinitialiser le lieu…** remet les cartes d'un lieu, ses images importées et ses propres personnages, portes et événements tels que le jeu d'origine les a. Si vous changez d'avis, **Annuler** ramène votre version. Si un lieu partage sa carte avec d'autres, ceux-ci sont réinitialisés aussi, et l'éditeur vous prévient d'abord. Les personnages et événements que d'autres lieux partagent ne sont pas touchés, sauf si vous le demandez : l'éditeur vous pose la question.
- **Réinitialiser la carte du monde…**, sur la page de la carte du monde, fait de même pour la carte du monde.

Le texte que vous avez écrit reste dans le fichier de texte du jeu tant qu'un événement en utilise encore une partie. Il n'est supprimé que lorsque plus rien n'utilise aucune de vos répliques. Annuler une action enregistrée alors que vous avez des modifications non enregistrées supprime aussi celles-ci, et l'éditeur vous demande d'abord.

Chaque enregistrement se fait en entier ou pas du tout. Si l'éditeur s'arrête en cours de route, il finit d'annuler l'enregistrement à moitié fait au prochain démarrage. Si un fichier ne peut pas être écrit, par exemple parce qu'il est verrouillé dans le Finder, l'enregistrement est refusé et le reste est annulé.

## Regarder la carte

Appuyez sur **Regarder** (V) pour regarder sans rien modifier.

- **Zoom :** de 1× à 4×.
- **Calques :** chaque lieu en a jusqu'à trois, appelés **Sol**, **Milieu** et **Au-dessus**. Vous pouvez masquer chacun d'eux. Cochez **Avancé** pour avoir des curseurs qui les estompent.
- **Superpositions :** cochez **Praticabilité**, **Hauteur** pour voir la hauteur du sol, ou **Grille** pour voir les cases.
- Les **coffres** sont toujours visibles sur la carte. Les portes, les personnages et les événements apparaissent quand vous utilisez leurs outils.

## Peindre : l'apparence du sol

Appuyez sur **Peindre** (B).

1. Choisissez un calque dans le menu **sur** de la barre du haut.
2. Choisissez un bloc dans le panneau **Blocs** à droite, ou maintenez ⌥ et cliquez sur la carte pour prendre le bloc sous le curseur.
3. Cliquez ou faites glisser sur la carte.
4. Enregistrez.

Cochez **Remplir** dans la barre du haut (ou appuyez sur F) : un clic remplit alors toute la zone d'un seul tenant qui a le même bloc que la case cliquée, sur ce calque. Remplir fonctionne aussi dans **Praticabilité** et **Hauteur**, en suivant alors la même praticabilité ou la même hauteur. Annuler défait un remplissage entier d'un coup.

Chaque lieu a son propre jeu de blocs, donc le panneau change d'un lieu à l'autre.

## Praticabilité : où l'on peut marcher

Appuyez sur **Praticabilité** (C). Peindre un bloc ne change pas les endroits où l'on peut marcher, c'est donc une étape à part. Choisissez un pinceau et peignez.

| Pinceau | Ce qu'il fait |
|---|---|
| **Sol** | Sol ordinaire sur lequel on peut marcher. |
| **Mur** | Bloque la marche, quelle que soit la hauteur. |
| **Rebord (sauter en bas)** | Maintenez Bas contre lui un instant et le meneur saute en contrebas. |
| **Mur à escalader / échelle** | Maintenez Haut ou Bas contre lui un instant pour grimper. |
| **Trou à sauter (saut en avant)** | Poussez contre lui un instant et le meneur saute par-dessus, si l'autre côté permet d'atterrir. |
| **Sol de rencontres A / B** | Praticable. Les combats aléatoires utilisent la première ou la deuxième zone de rencontres du lieu. |
| **Sol dangereux** | Praticable, mais blesse le groupe après assez de pas, si la scène l'active. |
| **Ombre pour Cloak** | Praticable. Le seul sol où la Psynergie Cloak garde le groupe caché. |
| **Jarre, tonneau, caisse, tombe, livres, puits vides** | Le fouiller ne donne rien. En général c'est aussi un mur, par sa hauteur. |

Les outils Coffre, Portes et Événements placent eux-mêmes les codes spéciaux dont ils ont besoin, vous n'avez donc pas à les peindre.

## Hauteur : la hauteur du sol

Appuyez sur **Hauteur** (H). Le panneau liste les hauteurs que ce lieu utilise déjà, de la plus haute à la plus basse, par exemple « Plat, 24 px » ou « Pente, de 16 à 24 px de gauche à droite ». Les hauteurs qui se liraient pareil reçoivent un numéro, et en survoler une indique combien de cases l'utilisent. Choisissez-en une et peignez.

La hauteur influe sur la marche autant que sur l'apparence. Les personnages se tiennent à la hauteur du sol sur lequel ils sont, et le jeu refuse un pas de plus de 8 pixels vers le haut ou de 12 pixels vers le bas : une grande différence de hauteur agit donc comme un mur.

## Coffres

Appuyez sur **Coffre** (K).

- **En ajouter un :** cliquez sur un emplacement vide, choisissez un **Objet** (commencez à taper son nom) ou une somme de **Pièces**, puis appuyez sur **Ajouter un coffre**.
- **En changer un :** cliquez dessus, changez son contenu et confirmez.
- **En supprimer un :** cliquez dessus et appuyez sur **Supprimer le coffre**.
- **En déplacer un :** faites-le glisser, puis enregistrez. Les Pierres de Psynergie peuvent aussi être déplacées. Un coffre ne peut pas aller sur une case qui est déjà une porte, un panneau ou un message de passage.

L'éditeur s'occupe du reste, y compris du drapeau qui retient qu'un coffre a été ouvert, pour qu'un coffre reste vide quand vous revenez. Un lieu peut contenir au maximum **10 coffres et Pierres de Psynergie**. Les autres endroits à fouiller ne comptent pas dans les 10.

## Événements : personnages, panneaux et messages

Appuyez sur **Événements** (E). Le panneau liste en toutes lettres tout ce qui se passe dans ce lieu : ce que disent les personnages, les pensées lues avec Mind Read, les panneaux, les messages de passage, les fouilles et les zones de sortie. Les personnages apparaissent sur la carte tels qu'ils sont ; survolez quelqu'un pour voir ce qu'il dit. Les scripts de scène sont décrits en mots simples (cochez **Avancé** pour la description complète). Les personnages qui attendent hors de la carte jusqu'à ce que l'histoire les amène ne sont pas dessinés ; le panneau indique combien il y en a.

L'**Étape de l'histoire** en haut est importante. Beaucoup de lieux changent au fil de l'histoire, et chaque étape a ses propres personnages et événements. Choisissez l'étape que vous voulez modifier.

### Ajouter des choses

Cliquez sur un emplacement de la carte, puis choisissez :

- **Ajouter un panneau (lu avec A)…** pour un panneau ou quelque chose à examiner.
- **Ajouter un message de passage…** pour un message qui s'affiche quand vous marchez à cet endroit. Il ne se répète pas tant que vous y restez, il ne peut donc pas bloquer le joueur, et il s'affiche à nouveau si vous partez puis revenez.
- **Ajouter un personnage ici…** pour choisir qui c'est, avec un aperçu de son image, et s'il **se promène**. L'éditeur vérifie d'abord l'emplacement (voir ci-dessous).

Pour retirer un personnage que vous avez ajouté, cliquez dessus et appuyez sur **Supprimer ce personnage** : ce qu'il dit disparaît aussi. Les personnages d'origine du jeu ne peuvent pas être supprimés, car l'histoire les déplace et leur parle, mais vous pouvez les déplacer.

### Là où les personnages peuvent se tenir

Tous les emplacements qui semblent dégagés ne conviennent pas pour y placer quelqu'un. Cochez **Là où les personnages peuvent se tenir** en haut, ou appuyez simplement sur **Ajouter un personnage ici…**, et la carte est colorée selon ce que signifierait un personnage à cet endroit :

| Couleur | Signification |
|---|---|
| Vert | Le groupe peut s'approcher et lui parler. |
| Jaune | Le groupe ne peut pas marcher sur cette case, mais peut lui parler depuis à côté, comme un marchand derrière un comptoir. |
| Bleu | De la glace sur laquelle le groupe glisse, comme à Imil. Quelqu'un placé là gêne la glissade. |
| Orange | Une porte, une sortie ou une case de passage : quelqu'un placé là gênerait. |
| Rouge | Le groupe ne peut pas s'approcher assez en marchant pour parler. |

C'est calculé à partir des propres règles de déplacement du jeu, en partant de chaque point où le groupe arrive dans le lieu : on peut monter de 8 pixels et descendre de 12, les murs arrêtent, et on peut parler à quelqu'un jusqu'à deux cases de distance. Les endroits que seuls la Psynergie ou l'histoire rendent accessibles apparaissent en rouge, donc le rouge n'y signifie pas toujours une erreur.

Quand un emplacement pose problème, l'éditeur dit lequel avec des mots simples, par exemple « le sol ici est 32 pixels plus haut que le chemin le plus proche », ou que se tenir là couperait le groupe d'une porte. Puis il propose une solution :

- **Déplacer vers le bon emplacement le plus proche** déplace le personnage vers la case la plus proche qui ne pose aucun problème.
- **Mettre … cases à la hauteur du chemin** change la hauteur du sol depuis le chemin le plus proche jusqu'à l'emplacement, pour que le groupe puisse y marcher. L'image ne change pas : utilisez **Peindre** si cela doit ressembler à un chemin. C'est de la peinture ordinaire non enregistrée : Enregistrer la garde et Annuler la défait.
- **Ajouter ici quand même…** si vous savez mieux, par exemple quand un événement de l'histoire ouvre le passage.

Faire glisser un personnage avec **Déplacer les personnages** déclenche la même vérification quand vous le relâchez.

### Faire parler les personnages

Cliquez sur un personnage. Appuyez sur **Le faire parler…**, ou sur **Ajouter une réplique pour un moment de l'histoire…** s'il parle déjà.

### Changer ce qui s'y trouve

Chaque événement de la liste a ces boutons, quand ils s'appliquent :

- **Changer le texte** ouvre l'éditeur de texte.
- **Quand…** décide quand l'événement a lieu : **Toujours**, **Seulement une fois que…** un drapeau d'histoire est activé, ou **Seulement tant que… n'est pas** activé. Les drapeaux sont listés par nom. Un « drapeau propre à ce lieu » est effacé chaque fois que le groupe entre dans le lieu.
- **Supprimer** l'efface.

### L'éditeur de texte

Tapez normalement. Une ligne vide commence une nouvelle boîte de dialogue, et l'aperçu montre à quoi ressembleront les boîtes dans le jeu. **+ nom du héros** insère le nom choisi par le joueur. La police du jeu contient les lettres simples, les chiffres et la ponctuation, sans accents. Les guillemets typographiques, les tirets longs et « … » deviennent automatiquement leur forme simple, et tout autre caractère que la police ne sait pas dessiner est refusé à l'enregistrement.

Vos mots sont ajoutés comme de nouvelles répliques, et le texte d'origine du jeu n'est jamais écrasé. Si la même réplique est utilisée ailleurs, elle y reste telle quelle.

### Scènes partagées

Certains lieux partagent leurs personnages et événements avec d'autres lieux. Le panneau vous prévient quand une modification ici apparaîtra aussi là-bas.

## Portes

Appuyez sur **Portes** (D). Chaque porte apparaît sur la carte avec sa destination. Les cases **bleues** sont des portes, et les **rouges** ne mènent nulle part.

- **Changer une porte :** cliquez dessus, appuyez sur **Changer la destination…**, choisissez un lieu, puis cliquez là où le groupe doit arriver sur la carte de ce lieu.
- **Créer une porte :** cliquez sur n'importe quel autre emplacement et appuyez sur **Créer une porte ici…**. Elle peut mener n'importe où dans le jeu.
- **Supprimer une porte :** cliquez dessus et appuyez sur **Supprimer la porte**. Ses cases redeviennent du sol.
- **Suivre une porte :** cliquez dessus et appuyez sur **Y aller →**. Le lieu vers lequel elle mène s'ouvre avec son point d'arrivée marqué, et **← Retour à …** vous ramène à la porte.

Une porte change dans toutes les étapes de l'histoire du lieu. Les portes ouvertes par des scripts de scène sont trouvées aussi : vous pouvez changer leur destination, mais le script lui-même reste le même.

## Déplacer les personnages

Appuyez sur **Déplacer les personnages** (P).

1. Dans le panneau **Histoire et scène**, choisissez une scène et une table de personnages ou de points d'arrivée.
2. Faites-les glisser sur la carte. Maintenez ⇧ en relâchant pour les aligner sur les 8 pixels les plus proches.
3. Enregistrez.

Les points d'arrivée sont les endroits où le groupe apparaît en entrant dans un lieu. Survolez un personnage pour voir qui il est et ce qu'il dit. Les personnages qui attendent hors de la carte jusqu'à ce que l'histoire les amène sont regroupés, en général dans le coin supérieur gauche, dessinés une seule fois avec un nombre comme « ×6 » ; faites-en glisser un pour le placer.

## Tampon : copier et coller

Appuyez sur **Tampon** (S).

1. Faites glisser un rectangle sur la carte pour le copier.
2. Cliquez pour coller, ici ou dans un autre lieu qui utilise le même jeu de blocs.
3. Appuyez sur Échap pour revenir à la copie.

- **Praticabilité et hauteur** les copie avec les blocs, et est activé par défaut.
- **Objets seulement** colle seulement les arbres et autres objets, pas le sol en dessous.
- Un collage est une seule étape d'annulation, et votre copie survit au changement de lieu et au rechargement.
- Les lieux avec un autre jeu de blocs refusent le collage, car chaque bloc dessinerait la mauvaise image.

## Importer vos propres images

**Importer une image…** se trouve dans le panneau Tampon. Cela fonctionne pour les lieux dont les graphismes ne sont partagés avec aucun autre lieu, soit 27 des 182 lieux d'une copie neuve du jeu. Ailleurs, l'éditeur refuse, car votre image changerait l'apparence d'autres lieux.

1. Choisissez **Surcouche** (dessinée par-dessus le sol, avec un fond transparent) ou **Sol**.
2. Appuyez sur **Importer une image…** et choisissez un PNG, GIF ou BMP. Elle peut couvrir au maximum 256 cases de 16×16 pixels, par exemple 256×256 pixels, mais une image détaillée peut manquer de place plus tôt. L'éditeur vous le dit si c'est le cas.
3. Vérifiez l'aperçu. Il montre les couleurs que le jeu dessinera réellement, et combien de place il reste.
4. Appuyez sur **Ajouter au jeu de tuiles**. Les nouveaux blocs arrivent dans le presse-papiers du Tampon, prêts à être placés d'un clic.

L'image est adaptée aux couleurs de ce lieu, et les morceaux répétés sont réutilisés pour gagner de la place. Quand les planches sont pleines, l'éditeur réutilise les graphismes de blocs que le lieu n'utilise jamais, et ces blocs disparaissent alors de la palette.

## Tables d'histoire et de scène

Le panneau **Histoire et scène** montre les scènes qui utilisent cette carte et les tables qui se trouvent derrière, avec des noms parlants comme « Arrival points: normal ». Les points d'arrivée et les personnages apparaissent sur la carte. Les sorties se modifient sous forme de liste, avec une vérification que le point d'arrivée choisi existe. La plupart du temps, les outils Portes, Événements et Déplacer les personnages sont plus simples.

## Combats dans un lieu

Appuyez sur **Combats…** pour voir les combats aléatoires du lieu où vous êtes : leur fréquence, et quels groupes d'ennemis apparaissent avec quelle probabilité chacun. Modifiez-les et appuyez sur **Enregistrer**. Dans la plupart des grottes et des donjons, les combats ont lieu partout où l'on marche ; dans certains, seulement sur les cases peintes en **Sol de rencontres A** dans Praticabilité. Certains lieux partagent leurs combats avec d'autres, et la boîte de dialogue le signale : une modification apparaît alors dans tous.

## Connexions

Appuyez sur **Connexions** pour voir n'importe quel lieu au milieu, avec à gauche tous les lieux qui y mènent et à droite tous ceux vers lesquels il mène. Cliquez sur un lieu pour vous y déplacer, ou appuyez sur **Ouvrir** pour aller à cette porte dans l'éditeur. Utilisez la case de recherche pour trouver un lieu.

## Atlas : tous les lieux d'un coup

Appuyez sur **Atlas** pour voir tous les lieux sur une même toile, reliés par des lignes pour leurs portes et leurs sorties. Les lieux de Golden Sun ne se touchent pas bord à bord, donc l'atlas les dispose lui-même : chaque ville ou donjon se place près de son emplacement sur la carte du monde, avec ses maisons et ses salles à côté, en partant de l'entrée.

- Faites glisser le fond pour vous déplacer, et faites défiler pour zoomer. **Ajuster** affiche tout.
- Survolez un lieu pour mettre en évidence ses portes et les lieux vers lesquels elles mènent.
- Cliquez sur un lieu pour l'ouvrir dans l'éditeur. Faites-en glisser un pour le déplacer : l'atlas retient où vous l'avez mis, et **Réinitialiser la disposition** remet tout en place. La position des lieux dans l'atlas ne concerne que vous ; elle ne change pas le jeu.
- Les lignes pleines partent d'une porte ; les lignes en pointillés sont des sorties qu'utilise une scène ou un script de l'histoire.

## La carte du monde

Choisissez la carte du monde en haut de la liste des lieux. Appuyez sur **← Lieux** pour revenir.

| Outil | Touche | Ce qu'il fait |
|---|---|---|
| **Regarder** | V | Survolez pour voir la région d'un emplacement et ce qu'il fait. Cliquez sur une ville, un donjon ou une case de passage bleue pour voir où elle mène. |
| **Sol** | G | Peindre les blocs du sol. ⌥-clic prend un bloc, et les blocs récents restent à portée de main. |
| **Surcouche** | O | Peindre les montagnes, les arbres et les côtes. La marche dépend des tuiles des deux calques. |
| **Régions** | R | Peindre les régions de rencontres. Chacune a ses propres combats aléatoires, et chacune porte le nom des villes qu'elle contient. Sous **Combats ici**, changez la fréquence des combats et les groupes d'ennemis qui apparaissent, en terrain découvert et en forêt. |
| **Villes** | T | Faites glisser une ville ou un donjon pour le déplacer. Cliquez dessus pour changer sa destination. **Placer une nouvelle icône…** en ajoute une, avec une image qu'utilisent les villes du jeu lui-même ; les icônes que vous avez ajoutées peuvent être supprimées. |
| **Cases de passage** | P | Les cases bleues mènent quelque part quand on marche dessus. Cliquez sur l'une d'elles pour changer sa destination ou la supprimer, ou cliquez sur n'importe quelle autre case pour en créer une nouvelle. **Ajouter une case…** élargit une case de passage : cliquez sur les cases à ajouter, puis appuyez sur Échap. |

- Cochez **Praticabilité**, **Régions de rencontres** ou **Lieux** pour les afficher sur la carte.
- Quand vous déplacez une ville, **déplacer aussi ses points d'arrivée** fait que vous réapparaissez à côté d'elle en la quittant. C'est activé par défaut.
- Les modifications sont enregistrées pendant que vous peignez. **Annuler** défait le dernier trait, et **Rétablir** le remet.
- La carte de l'écran de pause est une image séparée : elle ne suivra pas vos modifications, et les nouvelles icônes n'y ont pas de repère.

## Vérifier : trouver les problèmes

Appuyez sur **Vérifier** pour passer en revue toutes les cartes à la recherche des problèmes que vos modifications causeraient. Chacun est accompagné d'une correction et d'un bouton **Afficher** qui ouvre le lieu et entoure la case pendant quelques secondes. Il recherche :

- les portes qui ne mènent nulle part ou vers un point d'arrivée qui n'existe pas ;
- les coffres qui ne peuvent pas être ouverts, qui n'ont rien de défini, qui se remplissent à nouveau ou qui partagent un drapeau « ouvert » ;
- plus de 10 coffres et pierres dans un lieu ;
- les cases qui utilisent un bloc ou une hauteur que le lieu n'a pas ;
- les répliques que vous avez écrites et que la police du jeu ne sait pas dessiner ;
- les lieux dont les fichiers ont été endommagés ;
- les modifications qui ne correspondent plus après une mise à jour de la source du jeu.

Le jeu d'origine a ses propres bizarreries, et elles sont masquées sauf si vous cochez **Afficher aussi les bizarreries du jeu d'origine**. Sur un lieu que vous avez modifié, une bizarrerie que l'original avait déjà peut être listée comme la vôtre. Sur la page d'un lieu, Jouer, Exporter et **Compiler** lancent Vérifier pour vous d'abord et demandent avant de continuer s'il y a des problèmes. Sur la page de la carte du monde, Jouer et Compiler ne le font pas : appuyez donc sur Vérifier depuis un lieu. Si Vérifier ne peut pas terminer, il le dit et demande avant de continuer.

## Jouer à votre jeu

Appuyez sur **▶ Jouer**. Cela enregistre, vérifie, compile et ouvre votre jeu dans mGBA, en commençant dans le lieu que vous modifiez. Depuis la page de la carte du monde, cela compile et démarre sur la carte du monde, sans la vérification.

- Chaque partie lancée avec Jouer est une **nouvelle partie** : Isaac seul, sans progression dans l'histoire, donc un lieu peut ressembler à sa version du début du jeu.
- Vous apparaissez au premier point d'arrivée du lieu depuis lequel le groupe peut continuer à marcher, selon les règles de déplacement du jeu, pas à l'endroit que vous regardez. Les scènes de l'histoire ne sont pas suivies, donc quelques lieux peuvent encore vous faire démarrer au milieu de l'une d'elles. Si cela arrive, choisissez un autre point d'arrivée dans **Départ**, à côté de ▶ Jouer, et appuyez de nouveau sur Jouer.
- Une compilation après une modification de carte prend environ 20 secondes.
- Le point de départ n'existe que dans une copie jetable du jeu : votre mod exporté démarre donc normalement depuis l'écran titre.

## Partager votre mod

Appuyez sur **Exporter le mod…**.

1. Remplissez un **Nom**, et éventuellement votre nom et ce que le mod change.
2. Appuyez sur **Exporter**.

Vous obtenez un petit patch `.bps` et un fichier lisez-moi pour les joueurs dans `~/Documents/GSMapEditor/Exports/`. Appuyez sur **Afficher dans le Finder** pour les voir. Si vous exportez de nouveau sous le même nom, l'éditeur demande s'il faut remplacer le patch précédent ou le garder et numéroter le nouveau. L'export lance d'abord Vérifier, et teste chaque patch une fois pour confirmer qu'il reproduit exactement votre compilation.

Cochez **Enregistrer aussi un .ips** si vos joueurs utilisent d'anciens patcheurs. Il est beaucoup plus gros, car IPS ne sait pas noter les données déplacées.

**Partagez le patch, jamais le jeu compilé.** Les joueurs appliquent le patch à leur propre copie : vous ne distribuez donc jamais le jeu lui-même. Un patch `.bps` fonctionne avec les patcheurs courants comme Rom Patcher JS et Floating IPS, ainsi qu'avec cet éditeur.

## Jouer au mod de quelqu'un d'autre

Appuyez sur **Patcheur…**.

1. Appuyez sur **Choisir un patch…** et choisissez un fichier `.bps`, `.ips` ou `.ups`.
2. Choisissez le jeu à patcher : **Le jeu non modifié, compilé sur ce Mac** (aucune ROM nécessaire), ou **Mon propre fichier ROM**.
3. Appuyez sur **Patch**.

Le jeu patché est enregistré dans `~/Documents/GSMapEditor/Patched/`, et vous pouvez appuyer sur **Jouer dans mGBA** ou **Afficher dans le Finder**. Les patchs BPS et UPS refusent le mauvais jeu. Les patchs IPS ne peuvent pas le vérifier, et le patcheur vous le signale.

## Où se trouve votre travail

| Quoi | Où |
|---|---|
| Votre mod | Dans le dossier de la source du jeu, par défaut `~/Documents/GSMapEditor/alchemy/` |
| Patchs exportés | `~/Documents/GSMapEditor/Exports/` |
| Jeux patchés | `~/Documents/GSMapEditor/Patched/` |
| Réglages de l'éditeur et votre historique d'annulation | `~/Library/Application Support/GS Map Editor/` |
| Compilations temporaires, sans risque à supprimer | `~/Library/Caches/GSMapEditor/` |

Sous Windows et Linux, les trois premiers se trouvent dans `~/GSMapEditor/` dans votre dossier personnel Linux, les réglages dans `~/.config/gs-map-editor/` et les compilations temporaires dans `~/.cache/gs-map-editor/`.

Pour sauvegarder votre mod, copiez le dossier de la source du jeu dans un endroit sûr. Vos modifications sont des fichiers ordinaires dans ce dossier.

## Raccourcis clavier

Sous Windows et Linux, utilisez Ctrl pour ⌘ et Alt pour ⌥.

| Touche | Lieux | Carte du monde |
|---|---|---|
| V | Regarder | Regarder |
| B | Peindre | |
| C | Praticabilité | |
| H | Hauteur | |
| K | Coffre | |
| E | Événements | |
| D | Portes | |
| P | Déplacer les personnages | |
| S | Tampon | |
| F | Activer ou désactiver Remplir, dans Peindre, Praticabilité et Hauteur | |
| G / O / R / T / P | | Sol / Surcouche / Régions / Villes / Cases de passage |
| ⌘Z | Annuler | Annuler |
| ⇧⌘Z | Rétablir | Rétablir |
| ⌘S | Enregistrer | |
| ⌥-clic | Prendre un bloc | Prendre un bloc ou une région |
| ⇧ en relâchant | Aligner les personnages sur les 8 pixels les plus proches | |
| Échap | Fermer une fenêtre, ou revenir à la copie dans Tampon | Fermer une fenêtre |

## Ce qu'il ne sait pas encore faire

- **The Lost Age**, et les éditions autres que l'anglaise.
- **Windows ou Linux** en tant qu'application empaquetée.
- **Des lieux entièrement nouveaux :** il n'y a pas de bouton pour en ajouter un.
- **Les combats et les données du jeu :** les monstres, les objets, les boutiques et la musique ne peuvent pas être modifiés. Vous pouvez choisir lesquels des groupes d'ennemis du jeu apparaissent à chaque endroit, et à quelle fréquence, mais pas créer de nouveaux groupes.
- **Les scripts de l'histoire :** vous pouvez changer ce que disent les personnages et quand, et ajouter des événements simples, mais pas écrire de cinématiques.
- **La carte de l'écran de pause.**

## Dépannage

| Vous voyez | Que faire |
|---|---|
| « Jouer nécessite mGBA » | Installez-le depuis [mgba.io](https://mgba.io) et appuyez de nouveau sur Jouer. |
| L'éditeur dit que la source du jeu est une version qu'il ne sait pas lire | La source a changé d'une façon que cet éditeur ne comprend pas encore. Mettez ce dossier de côté, puis utilisez **Télécharger** sur l'écran d'installation. Votre mod reste dans le dossier que vous avez déplacé. |
| « Vos modifications n'ont pas pu être transformées en jeu » | Vos fichiers sont en sécurité. Si le message cite une réplique que vous avez écrite, changez-en les mots. Sinon, utilisez **Annuler** jusqu'à ce que la compilation réussisse, et appuyez sur **Afficher les détails** pour voir le message de la compilation elle-même. |
| « Les fichiers de ce lieu sont illisibles » | L'un de ses fichiers est endommagé. Utilisez **Réinitialiser le lieu…**, ou **Annuler** si un enregistrement récent en est la cause. |
| « Le fichier qui contient vos modifications de personnages, portes et événements est illisible » | Utilisez **Annuler**. Si cela ne suffit pas, restaurez ce fichier depuis votre sauvegarde. |
| « Ce lieu n'a plus de place pour d'autres éléments de ce type » | Le lieu n'a plus de codes disponibles pour les panneaux et les messages de passage. Supprimez-en un que vous avez ajouté. |
| « La police du jeu n'a pas de… » | Remplacez ce caractère par des lettres et une ponctuation simples. |
| L'écran d'installation dit que le chemin de votre dossier contient une espace | La compilation ne peut pas utiliser de chemins avec des espaces. Choisissez une copie de la source du jeu dans un dossier dont le chemin ne contient pas d'espace. |
| L'application s'ouvre sur l'écran d'installation avec une erreur | Le message indique ce qu'elle n'a pas pu lire. Appuyez sur **Vérifier à nouveau** après avoir corrigé le problème. |
| « Un problème est survenu » | Cette action ne s'est pas terminée. Réessayez, et si cela se reproduit, redémarrez l'application. |
| « Cette carte utilise un autre jeu de blocs » | Tampon ne colle qu'entre des lieux qui partagent un jeu de blocs. |
| « Ce lieu partage ses graphismes avec d'autres lieux » | L'import ne fonctionne que sur les lieux qui ont leurs propres graphismes. Le message en cite quelques-uns que vous pouvez utiliser. |
| « Ce bloc a été retiré » | Ses graphismes ont été réutilisés pour une image importée. Choisissez un autre bloc. |
| « Le jeu n'a plus de place pour d'autres coffres » | Le jeu n'a plus de drapeaux « ouvert » libres. Supprimez un coffre que vous avez ajouté. |
| Un coffre manque dans le jeu | Un lieu n'affiche que ses 10 premiers coffres et pierres. Lancez **Vérifier**. |
| Vérifier dit qu'une modification « ne correspond plus » | La source du jeu a changé sous cette modification. Elle est conservée mais laissée de côté dans votre jeu. |
| Un lieu a l'air différent de ce que vous avez modifié | Vous êtes peut-être sur une autre **Étape de l'histoire**, et Jouer lance une nouvelle partie, qui montre la version du début. |
| L'installation a échoué en cours de route | Appuyez sur **Vérifier à nouveau**, puis sur le bouton de l'étape. Le journal sous la liste d'étapes montre ce qui s'est passé. |
| Windows : l'éditeur ne s'est pas ouvert dans votre navigateur | La petite fenêtre GS Map Editor affiche son adresse : copiez-la dans votre navigateur. |
| Windows : l'installateur dit qu'Ubuntu n'est pas prêt | Redémarrez Windows si on vous l'a demandé, ouvrez une fois **Ubuntu** depuis le menu Démarrer pour choisir un nom d'utilisateur et un mot de passe, puis relancez l'installateur. |

## Signaler un problème

Merci d'[ouvrir un ticket](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md) en indiquant ce que vous faisiez, ce qui s'est passé, ainsi que la puce et la version de macOS de votre Mac. Quand l'éditeur propose **Afficher les détails** ou un journal d'installation, appuyez sur **Copier** et collez-le. Merci de ne pas joindre de ROM ni de fichiers du jeu.

## Mentions légales

Le code propre à GS Map Editor est sous [licence MIT](LICENSE). Les outils fournis gardent leurs propres licences, listées dans [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

L'éditeur ne contient ni ROM ni graphismes du jeu, et il ne distribue pas le texte du jeu. Les noms et les images sont lus depuis votre propre copie de la source du jeu pendant qu'il tourne. Golden Sun appartient à Nintendo et Camelot, et ce projet n'est pas affilié à eux. Alchemy est un projet séparé avec ses propres conditions.

Merci de ne pas partager de jeux compilés. Partagez plutôt des patchs.

## Développeurs

La compilation de l'application, les tests, la façon dont les modifications arrivent dans le jeu et la façon de suivre les mises à jour d'alchemy se trouvent dans [docs/fr/DEVELOPING.md](docs/fr/DEVELOPING.md).
