<!-- translated from docs/DEVELOPING.md @ a2a351788bee -->
# Desarrollo de GS Map Editor

*Esta es una traducción del documento en inglés [DEVELOPING.md](../DEVELOPING.md); si los dos difieren, el inglés es el actualizado.*

Cómo ejecutar, compilar, probar y actualizar el editor, y cómo funcionan sus funciones por dentro. Para aprender a usarlo, lee el [README](../../README.es.md).

## Ejecutar desde el código fuente

Necesita Python 3 con Pillow y una copia de alchemy ya compilada.

```sh
python3 server.py                  # alchemy en ~/gs_project/alchemy-port
python3 server.py --root /path/to/alchemy --port 8765
# abre http://127.0.0.1:8765/
```

### Aplicación de escritorio (macOS)

`GS Map Editor.app` es el editor en su propia ventana, para jugadores que nunca abren una terminal.

```sh
python3 -m venv .venv && .venv/bin/pip install pywebview pyinstaller pillow
python3 packaging/build_toolchain.py                          # binutils de GBA + libpng, ~10 min, una vez
.venv/bin/python packaging/make_icon.py                       # packaging/icon.icns
.venv/bin/pyinstaller --noconfirm packaging/gsmapedit.spec    # -> dist/GS Map Editor.app
python3 packaging/make_dmg.py                                 # -> dist/GS-Map-Editor-<version>.dmg
python3 packaging/sign_and_notarize.py --identity "Developer ID Application: …"   # necesita una cuenta de Apple Developer
.venv/bin/python desktop.py                                   # o ejecútala sin empaquetar
```

La aplicación lleva sus propias herramientas de compilación (`packaging/toolchain`, 15 MB): GNU binutils para la GBA, una libpng estática y un pequeño sustituto de `libpng-config` que responde al `tools/Makefile` de alchemy. Se compilan a partir de fuentes fijadas y con suma de verificación, y no necesitan nada más que macOS. Con ellas, los jugadores solo necesitan las herramientas de desarrollo gratuitas de Apple; Homebrew solo lo usa una compilación sin el toolchain. `GSMAP_NO_BREW=1` oculta Homebrew, para demostrar que una compilación no lo necesita.

En el primer arranque muestra una lista de instalación (`static/setup.html`, `gsmap/setup.py`). Cada paso se comprueba, nunca se da por hecho, y los pasos largos muestran su registro en directo:
1. Las herramientas de desarrollo de Apple (abre el instalador de Apple).
2. Las herramientas de compilación: incluidas con la aplicación. Una compilación sin ellas recurre a Homebrew y a los paquetes del INSTALL.md de alchemy, comprobados por lo que usa la compilación y no por los nombres de las fórmulas.
3. El código fuente del juego: descargar alchemy (fijado al commit con el que se probó este editor) en `~/Documents/GSMapEditor/` (sin espacios: la compilación no los admite), o elegir una copia existente.
4. `make bootstrap` (los compiladores del juego, compilados una vez a partir de las fuentes del submódulo `alchemy-gcc` de alchemy, sin descargas), y después un primer `make tbs-en`.

Después de eso, la aplicación abre directamente el editor. Los ajustes se guardan en `~/Library/Application Support/GS Map Editor/`. La aplicación no contiene datos del juego: el juego se compila a partir del código fuente de alchemy en el Mac del jugador. Sus dos servidores escuchan solo en este equipo, detrás de un token aleatorio. `desktop.py --no-window` muestra sus direcciones, para pruebas.

### Linux y Windows (WSL)

En Linux el editor se ejecuta desde el código fuente y se abre en el navegador: `python3 desktop.py` (necesita `python3-pil`) muestra la misma lista de instalación, con los paquetes apt del INSTALL.md de alchemy en lugar de Homebrew. Instalarlos necesita `sudo`, así que la lista muestra el comando en lugar de ejecutarlo. Los ajustes van en `~/.config/gs-map-editor`, la caché de compilación en `~/.cache/gs-map-editor`, y el código fuente del juego y las exportaciones en `~/GSMapEditor`. En Windows (WSL), las exportaciones y los juegos parcheados van en Documents\\GSMapEditor de Windows, y **Ya tengo una copia** abre el diálogo de carpetas de Windows mediante PowerShell; en otros Linux usa zenity si está instalado, y si no, pide escribir la ruta. Lo que cambia según el sistema (carpetas, abrir un enlace, mGBA, mostrar un archivo) está en `gsmap/host.py`.

Windows ejecuta el mismo editor de Linux dentro de WSL, que es además la única forma en que alchemy compila en Windows:
- `windows/Install-GS-Map-Editor.cmd`, que una versión publicada lleva con su etiqueta ya puesta, activa WSL e instala Ubuntu si hace falta (derechos de administrador, quizá un reinicio), ejecuta `windows/setup-in-wsl.sh` dentro de Ubuntu en esa etiqueta, y añade accesos directos en el menú Inicio y el escritorio a `wsl.exe … gs-map-editor`.
- El editor se abre en el navegador de Windows mediante el reenvío de localhost de WSL. Jugar inicia el mGBA de Windows desde `Program Files\mGBA`, con la ruta `\\wsl.localhost\…` del juego. El juego se compila en el propio disco de Ubuntu, ya que una compilación en `/mnt/c` es muchas veces más lenta.
- Las páginas muestran Ctrl y Alt en lugar de ⌘ y ⌥ en cualquier sistema que no sea un Mac (`localWords` en `static/common.js`).

`.github/workflows/linux.yml` comprueba esto en las máquinas Ubuntu de GitHub en cada push: `setup-in-wsl.sh` instala el editor, `tests/setup_flow.py` recorre la instalación del primer arranque mediante el comando instalado, la compilación debe coincidir con `rom.sha1`, y las pruebas de ida y vuelta, de edición, de colocación y de funciones se ejecutan sobre esa copia. La mitad de Windows (el `.cmd`, la instalación de WSL, el acceso directo, el mGBA de Windows) no tiene prueba automática: necesita un PC con Windows.

### Publicar versiones

Las versiones las compila GitHub, en sus Macs, mediante `.github/workflows/release.yml`: una imagen de disco para Apple Silicon (`macos-15`) y otra para Intel (`macos-15-intel`). Cada trabajo compila el toolchain y la aplicación, comprueba que ambos son para su chip, ejecuta `packaging/smoke_test.py` (la aplicación arranca, encuentra sus herramientas y nombra el commit fijado) y crea el `.dmg`.

1. Pon la versión en `packaging/gsmapedit.spec` (`CFBundleShortVersionString`).
2. Escribe las notas que leen los jugadores en `docs/releases/v<version>.md`.
3. Haz commit y luego `git tag v<version> && git push origin v<version>`. El flujo de trabajo publica una versión preliminar con ambas imágenes, aunque falle el trabajo de uno de los chips.

**Run workflow** en la página Actions compila las imágenes sin publicar una versión. Las imágenes no están firmadas: el apartado "Abrirla por primera vez" del README explica cómo los jugadores pueden pasar Gatekeeper, y `packaging/sign_and_notarize.py` se encargará de ello cuando haya un Developer ID.

## Cómo funciona cada función

Mapas locales, The Broken Seal, edición inglesa. Para saber cómo usarlas, consulta el [README](../../README.es.md).

- **Ver:** los 182 mapas, con los tilesets correctos y los marcadores de posición, interruptores y opacidad por capa, y capas de colisión y altura.
- **Pintar:** bloques, colisión y altura, con cuentagotas con ⌥-clic y deshacer/rehacer. Lo que no se ha editado se guarda idéntico byte a byte.
- **Sello** (S): arrastra un rectángulo para copiar una zona y luego haz clic para pegarla, aquí o en otro mapa con el mismo conjunto de bloques (Vale ↔ Debug · Sandbox).
  - La copia lleva las tres capas más las zonas de paso y la altura.
  - **Solo objetos** pega solo los árboles y demás objetos, no el suelo de debajo (una prueba de color contra el bloque de fondo de cada capa).
  - Un pegado es un solo paso de deshacer. El portapapeles sobrevive al cambio de mapa y a la recarga de la página. Esc vuelve a copiar.
  - Los mapas con otro conjunto de bloques rechazan el pegado, ya que cada número de bloque dibujaría el tile equivocado.
- **Importar imagen** (mapas con su propio conjunto de tiles; hoy el Debug · Sandbox): elige un PNG y una capa y mira una vista previa, luego **Añadir al conjunto de tiles**. Los bloques nuevos van al portapapeles del Sello, listos para colocarlos con un clic.
  - El importador corta la imagen en tiles de 8×8 y ajusta sus colores a una de las 14 filas de la paleta del mapa (cada tile elige su propia fila solo si ninguna fila sirve para todos). El índice 0 es transparente.
  - Los tiles que ya están en las hojas, incluidos los reflejados, se reutilizan.
  - Los tiles nuevos van primero al espacio en blanco. Después vienen los tiles que solo usan bloques que el mapa nunca coloca. Esos bloques se *retiran* (se ocultan de la paleta y el Sello los rechaza) y se listan en `games/tbs/src/mod/tilesets.json` de alchemy.
  - La vista previa muestra los colores que dibujará el juego, y cuánto espacio queda.
- **Eventos** (E): todo lo que pasa en una escena, en palabras, para la etapa de la historia que elijas:
  - **Personas:** "🗨 Garet: “Ever since the tremors started…”", pensamientos de Mind Read, y scripts con su propia descripción ("Pregunta por el alcalde antes de la partida, o por los temblores después de volver").
  - **Sitios:** letreros (se leen con A), mensajes al pisar, cosas que examinar y lo que se encuentra.
  - **Zonas de salida:** recuadros que funcionan como puertas, dibujados en el mapa. Cambia adónde llevan, o quítalos.
  - Haz clic en una persona para ver sus eventos y **hacer que diga algo** (o añadir una línea para un momento de la historia). Haz clic en cualquier sitio para **añadir un letrero**, **un mensaje al pisar** o **una persona**.
  - **Cambiar palabras** abre un editor de texto con vistas previas en directo del cuadro de diálogo: escribe con normalidad, y una línea en blanco empieza un cuadro nuevo. **Cuándo…** establece "siempre", "solo cuando <marca de la historia> esté activado" o "solo mientras no lo esté", con las marcas por su nombre.
  - Las líneas nuevas se añaden a `en.po` en un bloque propio del editor. Las líneas del propio juego nunca se reescriben: cambiar lo que dice alguien le hace apuntar a una línea nueva. El texto que la fuente del juego no puede dibujar se rechaza antes de compilar.
  - Cuando una escena comparte sus personas y eventos con otras (el sandbox y el centro de depuración lo hacen), el panel lo indica.
- **Puertas** (D): cada puerta aparece en el mapa con su destino ("→ Vale Home"); las que no llevan a ningún sitio aparecen en rojo.
  - Haz clic en una puerta y luego en **Cambiar adónde lleva…**: elige un lugar y luego haz clic en un punto de llegada de su mapa.
  - Haz clic en cualquier otro sitio y en **Crear una puerta aquí…** para añadir una puerta a cualquier lugar del juego. **Quitar puerta** vuelve a convertir en suelo todas las celdas de una puerta.
  - Las puertas que abren los scripts de escena (la mayoría de las de Vale) también se encuentran, leyendo qué salida pide el script. Su destino se puede cambiar; el script se queda.
  - Una puerta cambia en todas las etapas de la historia de la escena, mediante sustituciones de salidas y eventos. Los archivos `.c` de escena no se tocan.
- **Cofres** (K): haz clic en un sitio vacío, elige un objeto (con su icono) o una cantidad de monedas, y **Añadir cofre**. Haz clic en un cofre para cambiar su contenido o quitarlo.
  - Una sola acción escribe todo lo que necesita un cofre: el marcador, el código de colisión de la celda, un evento `SEARCH(SEARCH_CHEST)` en la tabla de eventos de la escena (como sustitución, para que los archivos `.c` de escena no se toquen) y una marca de "abierto" nueva del rango libre para cofres.
  - El código es uno que no usa ninguna tabla de eventos de las escenas del mapa, y que ningún mapa que comparta esas tablas tiene en su colisión, así que nada más se vuelve examinable. El juego coloca como máximo 10 cofres y Piedras de Psinergía por escena; los demás sitios que examinar no cuentan.
  - Un cofre es una línea `treasure_spot` en el `map.s` del mapa, en la parte del archivo de la edición inglesa.
- **Cofres y Piedras de Psinergía:** arrastra para mover. La fila del marcador y los códigos de colisión de ambas celdas se actualizan juntos, y se rechazan los guardados que rompan la regla marcador/colisión.
- **Tablas de escena:** para cada escena que usa el mapa, elige una tabla.
  - Las entradas y los PNJ aparecen en el mapa; arrástralos con la herramienta Mover personas (P).
  - Las salidas se editan como una lista (tipo, escena de destino, entrada, marca), con una comprobación de que la entrada de destino existe.
- **Conexiones:** cualquier lugar en el centro, con todos los lugares que llevan a él a la izquierda y todos a los que lleva a la derecha (puerta, puerta con script o evento de escena, y el punto de llegada). Haz clic en un lugar para ir allí; **Abrir** salta a la puerta en el editor.
- **Revisar:** examina todos los mapas en busca de problemas que tus cambios causarían en el juego y los explica en palabras sencillas, cada uno con un arreglo y un botón **Mostrar** que abre el sitio:
  - puertas que no llevan a ningún sitio, o a un punto de llegada que no existe;
  - cofres que no se pueden abrir, que no tienen nada definido, que se rellenan por una marca temporal o que comparten una marca de "abierto";
  - más de 10 cofres y Piedras de Psinergía en una escena; celdas que usan bloques que faltan o retirados;
  - ediciones de tablas de escena que ya no coinciden con el código fuente del juego (tras una actualización de alchemy).
  - El juego original tiene sus propias rarezas (115 hoy, p. ej. 83 puertas sobrantes). Cada problema se busca también en el juego sin modificar, y esos se ocultan salvo que los pidas.
  - **Compilar** ejecuta primero la revisión y pregunta antes de compilar con problemas.
- **Mapa del mundo** (arriba de la lista de lugares): todo el mapa del mundo, cargado a medida que te desplazas, con iconos de pueblos y mazmorras etiquetados según adónde llevan.
  - Capas: zonas de paso (el terreno bloqueado en rojo) y regiones de encuentros, cada una con el nombre de los pueblos que contiene ("Región 1 (Vale, Lunpa…)").
  - **Suelo** / **Capa superpuesta**: pinta bloques (⌥-clic recoge uno; los bloques usados recientemente quedan a mano). **Regiones**: pinta regiones de encuentros. Los cambios se guardan mientras pintas; Deshacer quita el último trazo y Rehacer lo vuelve a poner. Las celdas se escriben en `map/world/blocks.tsv`, conservando los demás campos de cada palabra.
  - **Pueblos**: arrastra un icono para moverlo. Sus puntos de llegada (donde apareces al salir del pueblo) se mueven con él, en todas las etapas de la historia que tienen el icono ahí. Haz clic en un icono o en un sitio azul de paso para cambiar adónde lleva.
  - El norte nevado se dibuja con su propio conjunto de gráficos. El mapa de la pantalla de pausa es una imagen aparte y no sigue las ediciones.
- **Exportar mod…:** guarda tu mod como un pequeño parche `.bps`, más un léame para los jugadores, en `~/Documents/GSMapEditor/Exports/`.
  - El parche va del juego sin modificar a tu compilación. El juego sin modificar se compila una vez a partir del commit del que parte tu mod: en una carpeta aparte mediante `git archive`, así que tu copia no se toca. Se comprueba con el `rom.sha1` de alchemy, así que es igual al cartucho comercial, y el parche se aplica al volcado propio de cualquiera.
  - Los parches son BPS (Rom Patcher JS, Floating IPS, parcheo al vuelo de emuladores). Los datos movidos se convierten en copias en lugar de bytes nuevos. Cada parche se aplica una vez después de escribirlo, para comprobar que reproduce exactamente tu compilación.
  - Exportar ejecuta Revisar primero. Compartes tus cambios, nunca el juego.
- **Parcheador…:** aplica el parche `.bps`, `.ips` o `.ups` de un mod y guarda el juego en `~/Documents/GSMapEditor/Patched/`, con **Jugar en mGBA** y **Mostrar en Finder**.
  - Parchea el juego sin modificar que este Mac compiló desde el código fuente (no hace falta ROM) o tu propio archivo de ROM. Tu archivo se nombra a partir del `rom.sha1` de alchemy ("Golden Sun (English)"), con un aviso cuando no es un juego sin modificar.
  - BPS y UPS rechazan el juego equivocado. IPS no puede comprobarlo, así que el parcheador lo avisa.
  - Exportar también puede escribir un `.ips` para parcheadores antiguos. Es más grande, porque IPS no puede registrar datos movidos (4,2 MB frente a 383 KB para el mod de la sala de depuración), y se comprueba de la misma forma.
- **▶ Jugar:** un solo botón: guarda lo que no está guardado, ejecuta Revisar, compila y abre tu juego en mGBA, empezando una partida nueva en el lugar que estás editando (desde la página del mapa del mundo, en el mapa del mundo). El inicio se escribe en una copia desechable del juego; lo que exportas no lleva rastro de ello. Si la compilación falla recibes una explicación sencilla, con los detalles técnicos plegados y un botón Copiar para informes de errores. Compilar por sí solo está en Avanzado.
- **Deshacer / Rehacer:** un solo par de botones para todo. Deshacer quita primero la pintura sin guardar (la pila propia de la página) y después las acciones guardadas, de la más reciente a la más antigua, sea cual sea la herramienta y el lugar que las hizo; un guardado convierte la pila de la página en una sola acción guardada. Cada escritura pasa por `writing(label, where)` de `server.py`, una transacción de `gsmap/fsio.py` que guarda el contenido anterior de los archivos como una entrada del historial etiquetada con qué y dónde ("adding a person", mapa `051`). `undo_last` restaura una entrada y guarda lo que sustituyó en `history/redo`; `redo_last` hace lo contrario; una acción nueva vacía `history/redo`. Ambos pasan por el diario, así que un fallo a medias se termina en el siguiente arranque. Se guardan las últimas 30 de cada uno, en `history/` dentro de la carpeta de soporte.
- **Dónde pueden estar las personas** (`gsmap/walk.py`): las reglas de movimiento del juego, tomadas del código de campo de alchemy: pasos de 8 píxeles que necesitan cinco sondas libres, como máximo 8 píxeles hacia arriba y 12 hacia abajo (`terrain.c`, `MapGrid_CheckCollision`), alturas a partir de la forma de cada celda mediante las dieciséis funciones de terreno y `terrain_tables.c`, salientes, puntos de escalada y huecos, y hablar a menos de 32 píxeles y 48 hacia arriba o abajo. Los deslizamientos se siguen como hace `Imil_RunIceSlide`, para cualquier activador al pisar cuyo script deslice. Se sigue al grupo en una retícula de 8 píxeles desde cada punto de llegada de la escena; una persona bloquea a menos de 12 píxeles (dos radios de 8, menos 2 cada uno). `POST /api/map/<n>/walk` colorea cada casilla; `/walk/check` devuelve los problemas de un sitio, el sitio más cercano sin ninguno, y las ediciones de forma que nivelan un camino hasta él (formas planas que el mapa ya tiene). Las ediciones de forma y de zonas de paso sin guardar se envían también. La Psinergía y los eventos de la historia no se siguen, y las personas distintas de la que se comprueba no son obstáculos. Comprobado con el juego: con estas reglas se puede hablar con alrededor del 92% de las personas que colocó Camelot; el resto son salas de escenas cinemáticas y lugares que abre la Psinergía.
- **Restaurar lugar…:** devuelve un lugar a como está en el juego original (Deshacer recupera tu versión). Las tablas de escena que comparten otros lugares no se tocan, y lo indica.
- **Guardar es todo o nada:** los archivos de una acción se guardan juntos o ninguno, cada archivo se sustituye en un solo paso, y si el editor muere a medias termina de deshacer en el siguiente arranque.
- **Nombres:** los lugares se listan por sus nombres del juego ("Vale · Vale Home").
- **Pinceles de zonas de paso:** con nombre y código de color (Suelo, Pared, Saliente, Pared trepable / escalera, Hueco para saltar, Suelo dañino, sitios para examinar, …).
- **Al pasar el ratón:** dice qué hace una celda ("Salida → Vale", "Cofre: Herb", "Con script (probablemente una puerta a …)").
- **PNJ:** dibujados con sus sprites, listados por nombre.
- **Tablas de escena:** nombres amigables ("Arrival points: normal", "People: After Kalay").
- **Casilla Avanzado:** vuelve a mostrar los códigos en bruto.
- **Enlaces:** `?map=003&tool=points&kind=placements` abre directamente un lugar.
- **Sin arte ni texto incluidos:** los nombres de objetos, lugares, personajes, sprites y marcas, los iconos de objetos y las vistas previas de sprites se leen todos en tiempo de ejecución de la propia copia de alchemy del jugador. `gsmap/data` contiene solo los hallazgos propios del editor: fotogramas de vista previa, marcas libres para cofres y qué hace cada código de zona de paso.

**Cómo llegan las ediciones de escena al juego:** mediante un solo gancho, sin reescribir los archivos de escena de alchemy. Consulta `docs/SPEC.md` y `games/tbs/src/mod/README.md` de alchemy.
- El editor guarda copias editadas de las tablas en `games/tbs/src/mod/overrides.json` de alchemy y genera `mod.c` a partir de él.
- `MOD_SCENE_LOADED` en `Scene_LoadOverlay` (`system/main_routine.c`), que el editor añade a una copia limpia la primera vez que escribe una edición de escena, pone en su lugar un envoltorio que sigue ejecutando la propia lógica de cada escena para elegir tablas.
- Sin sustituciones, GSMOD está desactivado y las seis ediciones siguen compilando idénticas byte a byte.

Las próximas etapas están en el plan de construcción de [`SPEC.md`](SPEC.md).

### Seguir el ritmo de alchemy

Todo lo que el editor sabe de la estructura de alchemy está en `gsmap/layout.py`. El commit con el que se prueba es `ALCHEMY_PIN` en `gsmap/setup.py`. Cuando lo cambies, actualiza también la línea de versión del README, o falla la prueba de seguridad. Para probar una versión nueva:

1. `python3 -m gsmap.preflight path/to/alchemy` dice en palabras sencillas lo que ya no coincide. También se ejecuta en cada arranque, y se detiene ahí en lugar de dibujar mapas con los tiles equivocados.
2. Compílala, y luego `python3 tools/snapshot.py path/to/alchemy new.json` y `python3 tools/snapshot.py --compare old.json new.json` muestran todas las diferencias en lo que lee el editor. Las dos versiones compilan el mismo juego, así que los resultados solo deberían cambiar donde lo esperas.
3. Ejecuta las pruebas de abajo.

Mover a mano una copia existente a un alchemy nuevo es git normal: fusiona o haz checkout del commit nuevo, y luego `git submodule update --init --recursive alchemy-gcc`. Desde `alchemy-gcc` 3a12774 (alchemy 2026-11-08), agbcc son archivos normales en lugar de un submódulo anidado, y en una copia anterior a eso la actualización se detiene con "untracked working tree files would be overwritten". Dentro de `alchemy-gcc`, ejecuta `git submodule deinit -f agbcc`, borra la carpeta `agbcc` y `.git/modules/agbcc` dentro de la carpeta git de alchemy-gcc, y vuelve a actualizar. Borra `out/*/deps.mk` y `out/*/objects.mk` antes de la primera compilación. El 2026-11-10 los commits más recientes de alchemy-gcc se reescribieron y se volvieron a fijar, así que un `git fetch` en una copia antigua puede terminar con "Errors during submodule fetch: alchemy-gcc" ("not our ref 8b1b6b4…"); el fetch principal ha funcionado igualmente, y `git submodule update` luego hace checkout del nuevo commit fijado. **Descargar** en la instalación siempre hace un clon nuevo, así que los jugadores no se encuentran con esto.

Las ediciones de escena guardadas llevan una huella de la tabla para la que se hicieron. Una tabla renombrada en alchemy la sigue. Una edición de una tabla cuyo contenido original cambió se conserva pero se deja fuera del juego, y Revisar lo indica.

### Pruebas

- `python3 tests/safety.py`: lo que nunca debe salir mal: los fallos y cierres inesperados no dejan archivos a medio guardar, deshacer y rehacer recorren las acciones guardadas en orden y un cambio nuevo vacía rehacer, los cofres se quedan en sus propias salas, los valores incorrectos y los parches hostiles se rechazan, las tablas renombradas o cambiadas se gestionan, una estructura desconocida se notifica en lugar de adivinarse.
- `python3 tests/placement.py`: las reglas de movimiento comparadas con el juego: se puede hablar con las personas colocadas en ocho pueblos y llegar a sus salidas, y en Imil se avisa del hielo, de un sitio nevado inalcanzable (con su arreglo de nivelación), de un pasillo estrecho, de un umbral y de una pared.
- `python3 tests/features.py`: los casos límite de las funciones más nuevas, en copias desechables: quitar personas añadidas, dónde empieza Jugar, nombres de exportación, sitios al pisar e iconos de pueblos del mapa del mundo, zonas de encuentros y lo que restaura Restaurar, la caché del atlas, los problemas del mapa del mundo que encuentra Revisar, el commit del que parte un mod, qué sitios de cofre cuentan para el límite de 10 y las descripciones de scripts con palabras sencillas.
- `python3 tests/edits.py`: guarda ediciones de bloques, zonas de paso y altura en una copia de mapas reales y comprueba que se leen igual, sin ningún otro cambio.
- `python3 tests/i18n.py`: cada mensaje que muestra el código está traducido en todos los idiomas, y cada traducción conserva sus `{placeholders}`, etiquetas HTML y teclas (⌘ ⇧ ⌥ ▶).
- `python3 tests/roundtrip.py`: carga y vuelve a guardar cada cuadrícula de mapa, tabla de imágenes de celda y de formas, y lista de cofres (727 archivos con el mod de la sala de depuración, 721 en una copia limpia). Todos deben salir idénticos byte a byte. Esto garantiza que guardar un mapa solo cambia lo que editaste.

### Idiomas

Las palabras propias del editor están traducidas; el juego sigue en inglés. Escribe cada mensaje en inglés, envuelto para que se pueda encontrar: `tr("…")` en Python (`gsmap/i18n.py`), `T('…')` en las páginas (`static/i18n.js`). El primer argumento es siempre una sola cadena simple; las partes que cambian son marcadores `{name}` (`tr("Map {n} has {k} chests", n=n, k=k)`), y los plurales son dos plantillas completas. El texto de las páginas HTML, y los textos o títulos completos que los scripts ponen en la página, se traducen tal como aparecen cuando coinciden exactamente con un mensaje; nada dentro de un elemento `data-notr` (los nombres y diálogos del juego) se toca. No traduzcas lo que se escribe en archivos (mod.c, en.po, el léame exportado) ni lo que el código compara.

`python3 tools/extract_strings.py` reúne cada mensaje en `static/i18n/<lang>.json` (inglés → traducción), añadiendo los nuevos vacíos y quitando los que el código ya no tiene; `--check` falla si alguno está desfasado o sin traducir. El idioma elegido en el menú 🌐 se guarda en los ajustes del editor (`language`); hasta que se elige uno, deciden los idiomas preferidos del navegador. Los mensajes de cada petición lo usan (`i18n.begin` en ambos servidores), y las páginas obtienen su catálogo de `/i18n-strings.js`. Para añadir un idioma, añádelo a `LANGS` en `gsmap/i18n.py`, ejecuta el extractor y rellena el archivo nuevo.

El README y esta documentación también están traducidos: `README.<lang>.md` junto al README, y `docs/<lang>/` para `DEVELOPING.md`, `PRODUCT.md`, `SPEC.md` y `research/`. `docs/upstream-issues.md` (para el gestor de incidencias en inglés de alchemy), `docs/releases/` y `THIRD_PARTY_NOTICES.md` se quedan en inglés. Los archivos en inglés son los originales: cámbialos primero, luego las traducciones, y ejecuta `python3 tools/doc_translations.py --stamp` para anotar qué texto en inglés sigue ahora cada traducción. Sin `--stamp`, comprueba los enlaces, encabezados, direcciones web y fragmentos `code` de cada traducción, y lista las que tienen el inglés cambiado desde entonces. El extractor también recoge los nombres y descripciones de los pinceles de zonas de paso, de `gsmap/data/collision.json`.

## Documentación

- [`SPEC.md`](SPEC.md): la especificación del editor, sus invariantes y el plan de construcción por etapas.
- [`research/`](research/): pruebas con referencias file:line.
  - `rendering.md`: marcadores de posición, tilesets, ventanas, mezcla, animación.
  - `local-connections.md`: escenas, salidas, marcadores, PNJ, mapas nuevos.
  - `overworld.md`: el mapa del mundo.
