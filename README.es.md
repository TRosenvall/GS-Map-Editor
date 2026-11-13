<!-- translated from README.md @ 2037a84ce1a0 -->
# GS Map Editor

[English](README.md) · **Español** · [Deutsch](README.de.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [日本語](README.ja.md)

_Esta es una traducción del [README.md](README.md) en inglés. Si las dos versiones difieren, la inglesa es la vigente._

Haz tu propia versión de **Golden Sun: The Broken Seal** sin escribir código. Vuelve a pintar pueblos, esconde cofres, escribe diálogos nuevos, añade personas y puertas, cambia la forma del mapa del mundo y luego pulsa **▶ Jugar** y recorre tu cambio. Cuando estés contento con él, exporta un pequeño parche para compartirlo.

El editor funciona sobre [alchemy](https://github.com/PascalPixel/alchemy), un proyecto que reconstruye el juego a partir de archivos de código fuente legibles. Compila tu juego desde ese código en tu propio ordenador, así que no necesitas una ROM para hacer un mod.

> **Versión preliminar: se buscan testers.** El editor cubre la edición inglesa de The Broken Seal, en macOS y, como prueba temprana, en Windows. Se ha probado sobre todo en un solo Mac con Intel, y la versión de Windows nunca se ha ejecutado en un PC con Windows de verdad, así que cada informe ayuda, incluido "me funcionó": [descárgalo](https://github.com/TRosenvall/GS-Map-Editor/releases), pruébalo y [cuéntanos qué tal fue](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md). Guarda una copia de seguridad de cualquier mod que te importe.

**Versión de alchemy:** este editor está probado con el commit de alchemy [`5ca23b1fe1`](https://github.com/PascalPixel/alchemy/commit/5ca23b1fe1774f954aacfbd7db35c8c9b9a59184) (2026-11-12). La instalación descarga exactamente ese commit. Alchemy cambia rápido, así que puede que una copia más nueva no funcione hasta que el editor se ponga al día.

## Contenido

- [Primeros pasos](#primeros-pasos)
- [Tu primer mod en dos minutos](#tu-primer-mod-en-dos-minutos)
- [El editor de un vistazo](#el-editor-de-un-vistazo)
- [Guardar y deshacer](#guardar-y-deshacer)
- [Echar un vistazo](#echar-un-vistazo)
- [Pintar: cómo se ve el suelo](#pintar-cómo-se-ve-el-suelo)
- [Zonas de paso: por dónde se puede caminar](#zonas-de-paso-por-dónde-se-puede-caminar)
- [Altura: lo alto que está el suelo](#altura-lo-alto-que-está-el-suelo)
- [Cofres](#cofres)
- [Eventos: personas, letreros y mensajes](#eventos-personas-letreros-y-mensajes)
- [Puertas](#puertas)
- [Mover personas](#mover-personas)
- [Sello: copiar y pegar](#sello-copiar-y-pegar)
- [Importar tus propias imágenes](#importar-tus-propias-imágenes)
- [Tablas de historia y escena](#tablas-de-historia-y-escena)
- [Combates en un lugar](#combates-en-un-lugar)
- [Conexiones](#conexiones)
- [Atlas: todos los lugares a la vez](#atlas-todos-los-lugares-a-la-vez)
- [El mapa del mundo](#el-mapa-del-mundo)
- [Revisar: encontrar problemas](#revisar-encontrar-problemas)
- [Jugar a tu juego](#jugar-a-tu-juego)
- [Compartir tu mod](#compartir-tu-mod)
- [Jugar al mod de otra persona](#jugar-al-mod-de-otra-persona)
- [Dónde se guarda tu trabajo](#dónde-se-guarda-tu-trabajo)
- [Atajos de teclado](#atajos-de-teclado)
- [Lo que todavía no puede hacer](#lo-que-todavía-no-puede-hacer)
- [Solución de problemas](#solución-de-problemas)
- [Informar de problemas](#informar-de-problemas)
- [Aspectos legales](#aspectos-legales)

## Primeros pasos

### Lo que necesitas

- Un Mac con macOS 11 o posterior, o un PC con Windows 10 u 11.
- Unos 3 GB de espacio libre para el código fuente del juego y su compilación.
- [mGBA](https://mgba.io/downloads.html), un emulador gratuito de Game Boy Advance, para jugar a tu juego (en Windows, su instalador para Windows).
- Una conexión a internet para la primera instalación.

### Consigue la app (Mac)

Descarga el `.dmg` más reciente desde [Releases](https://github.com/TRosenvall/GS-Map-Editor/releases):

- **AppleSilicon** para Macs con un chip M1, M2, M3, M4 o posterior;
- **Mac-Intel** para Macs con Intel.

¿No sabes cuál tienes? Menú Apple → **Acerca de este Mac**: "Chip: Apple M…" es Apple Silicon.

Abre el `.dmg` y arrastra **GS Map Editor** a **Aplicaciones**.

### Abrirla por primera vez (Mac)

La app todavía no está firmada con un certificado de desarrollador de Apple, así que macOS avisa la primera vez:

1. Ábrela desde Aplicaciones. macOS dice que no puede comprobar la app: pulsa **OK** (o **Cancelar**).
2. Abre **Ajustes del Sistema → Privacidad y seguridad**, desplázate hacia abajo y pulsa **Abrir igualmente** junto a GS Map Editor. Confirma con tu contraseña.

En macOS 14 y anteriores puedes, en su lugar, hacer clic derecho en la app, elegir **Abrir** y luego **Abrir** otra vez. Después de la primera vez se abre con normalidad.

Si prefieres compilar la app tú mismo, sigue [Aplicación de escritorio](docs/es/DEVELOPING.md#aplicación-de-escritorio-macos) en las notas para desarrolladores. Si te manejas con una terminal y ya tienes una copia de alchemy compilada, puedes saltarte la app y ejecutar `python3 server.py --root /path/to/alchemy`, y luego abrir http://127.0.0.1:8765/.

### Consigue el editor (Windows, prueba temprana)

El editor se ejecuta dentro de WSL, el Linux integrado en Windows, porque es la única forma de compilar el código fuente del juego en Windows. Se abre en tu navegador web.

1. Descarga `Install-GS-Map-Editor.cmd` desde [Releases](https://github.com/TRosenvall/GS-Map-Editor/releases). Si tu navegador dice que no se descarga con frecuencia, elige **Conservar**.
2. Haz doble clic en él. Windows dice que protegió tu PC porque el instalador todavía no está firmado: pulsa **Más información** y luego **Ejecutar de todas formas**.
3. La primera vez, activa WSL e instala Ubuntu. Windows pide permiso de administrador y puede pedirte que reinicies; si lo hace, reinicia y vuelve a hacer doble clic en el instalador.
4. Cuando Ubuntu te lo pida, elige un nombre de usuario y una contraseña. Al escribir la contraseña no se ve nada; es normal. El siguiente paso te la pide.
5. El instalador configura el editor dentro de Ubuntu y añade **GS Map Editor** a tu menú Inicio y a tu escritorio.

Abre **GS Map Editor**. Aparece una ventana pequeña; déjala abierta mientras usas el editor, ya que al cerrarla se detiene el editor. El editor se abre en tu navegador. Ejecutar el instalador otra vez actualiza el editor a la versión con la que venía.

En Windows, los atajos de teclado usan Ctrl donde esta guía dice ⌘, y Alt donde dice ⌥. Los parches exportados y los juegos parcheados van a **Documents\\GSMapEditor**, como en un Mac. El código fuente del juego y sus compilaciones se quedan dentro de Ubuntu, en `GSMapEditor` en tu carpeta personal de Ubuntu, porque compilar ahí es mucho más rápido; el Explorador de archivos lo muestra en **Linux → Ubuntu → home**.

### Instalación inicial

La primera vez, el editor se abre en una lista de pasos. Tarda unos 15 minutos, casi todo esperando. Pulsa el botón de cada paso y el editor hace el resto:

1. **Las herramientas para desarrolladores de Apple** (solo Mac): abre el instalador de Apple.
2. **Las herramientas para compilar el juego:** ya vienen incluidas con la app en un Mac, y el instalador las pone en su sitio en Windows.
3. **El código fuente del juego:** descarga alchemy en `~/Documents/GSMapEditor/` (en Windows, `GSMapEditor` en tu carpeta personal de Ubuntu). Si ya tienes una copia, elige **Ya tengo una copia…** y escoge su carpeta.
4. **Preparando la compilación:** prepara los compiladores del juego, una sola vez.
5. **Una primera compilación del juego:** compila el juego una vez.

Luego pulsa **Abrir el editor**. A partir de entonces, la app se abre directamente en el editor.

## Tu primer mod en dos minutos

1. Elige un lugar de la lista de la izquierda. Escribe en la casilla **Buscar un lugar** para buscar.
2. Pulsa **Cofre** en la barra superior y luego haz clic en un trozo de suelo vacío.
3. Escribe el nombre de un objeto, como `Herb`, y pulsa **Añadir cofre**.
4. Pulsa **▶ Jugar**. Tu juego se abre en mGBA, en el lugar que estabas editando, unos segundos después de que arranque el juego.
5. Acércate al cofre y ábrelo.

## El editor de un vistazo

| Zona | Qué hay |
|---|---|
| **Izquierda** | La lista de lugares. El mapa del mundo está arriba del todo. |
| **Barra superior** | Zoom, capas, superposiciones, herramientas y botones para guardar, revisar y jugar. |
| **Centro** | El mapa. |
| **Derecha** | El panel de la herramienta que estás usando. |
| **Línea inferior** | Mensajes de estado. Al pasar el cursor, dice qué hace el sitio que hay debajo, como "Cofre: Herb" o adónde lleva una salida, y qué casilla es. Los números de casilla son los mismos que usan Revisar, las puertas y los cofres. |

Marca **Avanzado** en la barra superior para mostrar números y códigos en bruto y un botón **Compilar** aparte. No lo necesitarás para editar normalmente.

### Idiomas

El editor habla inglés, español (Español), alemán (Deutsch), francés (Français), italiano (Italiano) y japonés (日本語). Empieza en el idioma de tu ordenador si lo tiene. Cámbialo con el menú 🌐, arriba a la derecha de la primera pantalla de instalación y al final de la barra superior. Solo cambian las palabras del propio editor: el juego que modificas es la edición inglesa, así que los nombres de lugares, las personas, los objetos y los diálogos que escribas se quedan en inglés.

Esta guía también está traducida: mira los enlaces de arriba. Las traducciones del editor y de esta guía se hicieron con ayuda de IA y todavía no las han revisado todas hablantes nativos. Donde una guía traducida difiera de esta, la guía en inglés es la vigente. Si algo suena raro, por favor [dínoslo](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md) con la redacción que esperarías.

## Guardar y deshacer

Algunos cambios esperan a que guardes, y otros se guardan al momento:

| Esperan a **Guardar** (o ⌘S) | Se guardan al momento |
|---|---|
| Pintar, Zonas de paso, Altura | Añadir, cambiar o quitar un cofre |
| Pegados con Sello | Eventos y puertas |
| Arrastrar cofres, piedras y personas | Pintar el mapa del mundo y mover pueblos |

El editor también guarda por ti antes de que cambies de lugar, vayas al mapa del mundo o pulses Jugar, así que pasar a otra cosa no te hará perder tu trabajo. Si se rechaza un guardado, te quedas donde estás y la línea inferior dice por qué.

Hay tres formas de volver atrás:

- **Deshacer** (⌘Z) quita tu último cambio, fuera el que fuera: primero lo pintado que aún no has guardado, luego las acciones guardadas, de la más nueva a la más antigua, desde cualquier herramienta y cualquier lugar. Añadir una persona, un cofre, una puerta, un evento, un trazo en el mapa del mundo: todo. La descripción emergente del botón dice qué va a deshacer y dónde, y el editor abre ese lugar para mostrártelo. Se conservan las últimas 30 acciones guardadas, incluso después de cerrar el editor.
- **Rehacer** (⇧⌘Z) devuelve lo que quitó Deshacer, hasta que hagas un cambio nuevo.
- **Restaurar lugar…** devuelve los mapas de un lugar, sus imágenes importadas y sus propias personas, puertas y eventos a como están en el juego original. Si cambias de opinión, **Deshacer** recupera tu versión. Si un lugar comparte su mapa con otros, esos también vuelven atrás, y el editor te avisa antes. Las personas y eventos que comparten otros lugares se dejan como están, salvo que digas lo contrario: el editor te pregunta.
- **Restaurar mapa del mundo…**, en la página del mapa del mundo, hace lo mismo con el mapa del mundo.

El texto que has escrito se queda en el archivo de texto del juego mientras algún evento siga usando parte de él. Solo se quita cuando ya nada usa ninguna de tus líneas. Deshacer una acción guardada mientras tienes cambios sin guardar también descarta esos cambios, y te pregunta antes.

Cada guardado es todo o nada. Si el editor se detiene a mitad, la próxima vez que arranque termina de deshacer el guardado a medias. Si no se puede escribir un archivo, por ejemplo porque está bloqueado en Finder, el guardado se rechaza y se deshace el resto.

## Echar un vistazo

Pulsa **Ver** (V) para mirar sin cambiar nada.

- **Zoom:** de 1× a 4×.
- **Capas:** cada lugar tiene hasta tres, llamadas **Suelo**, **Medio** y **Superior**. Puedes ocultar cada una. Marca **Avanzado** para tener controles deslizantes que las atenúan.
- **Superposiciones:** marca **Zonas de paso**, **Altura** para ver la altura del suelo, o **Cuadrícula** para ver las casillas.
- Los **cofres** siempre se ven en el mapa. Las puertas, las personas y los eventos se ven cuando usas sus herramientas.

## Pintar: cómo se ve el suelo

Pulsa **Pintar** (B).

1. Elige una capa en el menú **en** de la barra superior.
2. Elige un bloque del panel **Bloques** de la derecha, o mantén ⌥ y haz clic en el mapa para tomar el bloque que hay bajo el cursor.
3. Haz clic o arrastra sobre el mapa.
4. Guarda.

Marca **Rellenar** en la barra superior (o pulsa F) y un clic rellena toda la zona conectada que tiene el mismo bloque que la casilla en la que haces clic, en esa capa. Rellenar también funciona en **Zonas de paso** y **Altura**, y entonces busca la misma zona de paso o la misma altura. Deshacer quita un relleno entero de una vez.

Cada lugar tiene su propio conjunto de bloques, así que el panel cambia de un lugar a otro.

## Zonas de paso: por dónde se puede caminar

Pulsa **Zonas de paso** (C). Pintar un bloque no cambia por dónde se puede caminar, así que esto es un paso aparte. Elige un pincel y pinta.

| Pincel | Qué hace |
|---|---|
| **Suelo** | Suelo normal por el que se puede caminar. |
| **Pared** | Impide caminar, sea cual sea la altura. |
| **Saliente (saltar abajo)** | Mantén Abajo contra él un momento y el líder salta hacia abajo. |
| **Pared trepable / escalera** | Mantén Arriba o Abajo contra ella un momento para trepar. |
| **Hueco para saltar (saltar adelante)** | Empuja contra él un momento y el líder lo salta, si el otro lado permite aterrizar. |
| **Suelo con encuentros A / B** | Se puede caminar. Los combates aleatorios usan la primera o la segunda zona de encuentros del lugar. |
| **Suelo dañino** | Se puede caminar, pero hace daño al grupo tras suficientes pasos, si la escena lo activa. |
| **Sombra para Cloak** | Se puede caminar. El único suelo donde la Psinergía Cloak mantiene oculto al grupo. |
| **Jarrón, barril, caja, tumba, libros o pozo vacíos** | Al examinarlo no se encuentra nada. Normalmente también es una pared, por su altura. |

Las herramientas Cofre, Puertas y Eventos ponen ellas mismas los códigos especiales que necesitan, así que no tienes que pintarlos.

## Altura: lo alto que está el suelo

Pulsa **Altura** (H). El panel muestra las alturas que ya usa este lugar, de la más alta a la más baja, una por nivel ("Nivel 3"), y al pasar el cursor sobre una ves cuántas casillas la usan. Las rampas y las casillas divididas (mitad de un nivel y mitad de otro, donde un borde va en diagonal) están plegadas en **Rampas y casillas divididas**; varias pueden leerse igual pero mirar hacia otro lado, así que haz ⌥-clic en una del mapa para copiarla exactamente. **Avanzado** muestra cada altura por separado. Elige una y pinta. En el mapa, un azul más oscuro significa suelo más alto, y cada altura de la lista muestra su tono. El suelo más bajo del lugar no tiene azul, así que un puerto o una playa al pie del mapa no muestra ninguno.

Las alturas se cuentan en niveles, la unidad propia del juego (un nivel son 8 píxeles, media casilla). La altura afecta a por dónde se camina además de a cómo se ve. Las personas están a la altura del suelo que pisan, y el grupo puede subir o bajar un nivel cada vez: dos niveles o más actúan como una pared. Las rampas unen niveles, y una casilla de rampa puede subir dos, así que las escaleras y las laderas son rampas puestas una tras otra.

## Cofres

Pulsa **Cofre** (K).

- **Añadir uno:** haz clic en un sitio vacío, elige un **Objeto** (empieza a escribir su nombre) o una cantidad de **Monedas** y luego pulsa **Añadir cofre**.
- **Cambiar uno:** haz clic en él, cambia lo que contiene y confirma.
- **Quitar uno:** haz clic en él y pulsa **Quitar cofre**.
- **Mover uno:** arrástralo y luego guarda. Las Piedras de Psinergía también se pueden arrastrar. Un cofre no puede ir en una casilla que ya es una puerta, un letrero o un mensaje al pisar.

El editor se ocupa del resto, incluida la marca que recuerda que un cofre se ha abierto, para que un cofre siga vacío cuando vuelvas. Un lugar puede tener como máximo **10 cofres y Piedras de Psinergía**. Los demás sitios que examinar no cuentan para el límite de 10.

## Eventos: personas, letreros y mensajes

Pulsa **Eventos** (E). El panel muestra, en palabras, todo lo que pasa en este lugar: lo que dice la gente, los pensamientos de Mind Read, letreros, mensajes al pisar, cosas que examinar y zonas de salida. Las personas se ven en el mapa tal como son; pasa el cursor sobre alguien para ver lo que dice. Los scripts de escena se describen con palabras sencillas (marca **Avanzado** para ver la descripción completa). Las personas que esperan fuera del mapa hasta que la historia las trae no se dibujan; el panel dice cuántas hay.

La **Etapa de la historia** de arriba importa. Muchos lugares cambian a medida que avanza la historia, y cada etapa tiene sus propias personas y eventos. Elige la etapa que quieras editar.

### Añadir cosas

Haz clic en un sitio del mapa y luego elige:

- **Añadir un letrero (se lee con A)…** para un letrero o algo que examinar.
- **Añadir un mensaje al pisar…** para un mensaje que aparece cuando pisas ahí. No se repite mientras sigas ahí, así que no puede atrapar al jugador, y vuelve a aparecer si sales y regresas.
- **Añadir una persona aquí…** para elegir quién es, con una vista previa de su imagen, y si **camina por ahí**. Antes, el editor comprueba el sitio (ver más abajo).

Para quitar a alguien que añadiste, haz clic en esa persona y pulsa **Quitar a esta persona**: lo que dice se va también. Las personas propias del juego no se pueden quitar, porque la historia las mueve y habla con ellas, pero sí puedes moverlas.

### Dónde pueden estar las personas

No todo sitio que parece libre es un buen lugar para que alguien esté. Marca **Dónde pueden estar las personas** arriba, o simplemente pulsa **Añadir una persona aquí…**, y el mapa se colorea según lo que significaría poner a una persona ahí:

| Color | Significa |
|---|---|
| Verde | El grupo puede acercarse caminando y hablar con ella. |
| Amarillo | El grupo no puede pisar esa casilla, pero puede hablarle desde al lado, como a un tendero detrás de un mostrador. |
| Azul | Hielo por el que se desliza el grupo, como en Imil. Alguien ahí estorba al deslizarse. |
| Naranja | Una puerta, salida o sitio de paso: alguien ahí estorbaría. |
| Rojo | El grupo no puede acercarse lo suficiente caminando para hablar. |

Se calcula con las propias reglas de movimiento del juego, empezando en cada punto donde el grupo llega al lugar: puedes subir o bajar un nivel cada vez, las paredes te detienen y puedes hablar con alguien a dos casillas o menos. Las zonas que solo abren la Psinergía o la historia se ven en rojo, así que ahí el rojo no siempre significa que esté mal.

Cuando un sitio tiene un problema, el editor dice cuál es con palabras sencillas, por ejemplo "el suelo aquí está 4 niveles más alto que el camino más cercano", o que estar ahí dejaría al grupo sin acceso a una puerta. Luego ofrece una solución:

- **Mover al sitio bueno más cercano** mueve a la persona a la casilla más próxima que no tenga ningún problema.
- **Nivelar … casillas a la altura del camino** cambia la altura del suelo desde el camino más cercano hasta el sitio, para que el grupo pueda llegar caminando. La imagen no cambia, así que usa **Pintar** si debe parecer un camino. Es pintura normal sin guardar: Guardar la conserva y Deshacer la quita.
- **Añadir aquí de todos modos…** si sabes lo que haces, por ejemplo cuando un evento de la historia abre el camino.

Arrastrar a una persona con **Mover personas** pasa la misma comprobación al soltarla.

### Hacer que la gente hable

Haz clic en una persona. Pulsa **Hacer que diga algo…**, o **Añadir una línea para un momento de la historia…** si ya habla.

### Cambiar lo que hay

Cada evento de la lista tiene estos botones, cuando corresponden:

- **Cambiar palabras** abre el editor de texto.
- **Cuándo…** decide cuándo ocurre el evento: **Siempre**, **Solo cuando** una marca de la historia esté activada, o **Solo mientras no…** esté activada. Las marcas se muestran por su nombre. Una "marca propia de este lugar" se borra cada vez que el grupo entra en el lugar.
- **Quitar** lo borra.

### El editor de texto

Escribe con normalidad. Una línea en blanco empieza un cuadro de diálogo nuevo, y la vista previa muestra cómo se verán los cuadros en el juego. **+ nombre del héroe** inserta el nombre que haya elegido el jugador. La fuente del juego tiene letras, números y signos de puntuación simples, sin tildes ni acentos. Las comillas tipográficas, las rayas largas y "…" se convierten solas en sus formas simples, y cualquier otra cosa que la fuente no pueda dibujar se rechaza al guardar.

Tus palabras se añaden como líneas nuevas, y el texto propio del juego nunca se sobrescribe. Si la misma línea se usa en otro sitio, allí se queda como estaba.

### Escenas compartidas

Algunos lugares comparten sus personas y eventos con otros lugares. El panel te avisa cuando un cambio aquí también aparecerá allí.

## Puertas

Pulsa **Puertas** (D). Cada puerta se ve en el mapa con el sitio adonde lleva. Las celdas **azules** son puertas, y las **rojas** no llevan a ninguna parte.

- **Cambiar una puerta:** haz clic en ella, pulsa **Cambiar adónde lleva…**, elige un lugar y luego haz clic donde debe llegar el grupo en el mapa de ese lugar.
- **Crear una puerta:** haz clic en cualquier otro sitio y pulsa **Crear una puerta aquí…**. Puede llevar a cualquier parte del juego.
- **Quitar una puerta:** haz clic en ella y pulsa **Quitar puerta**. Sus celdas vuelven a ser suelo.
- **Seguir una puerta:** haz clic en ella y pulsa **Ir allí →**. Se abre el lugar al que lleva, con su punto de llegada marcado, y **← Volver a …** te devuelve a la puerta.

Una puerta cambia en todas las etapas de la historia del lugar. También se encuentran las puertas que abren los scripts de escena: puedes cambiar adónde llevan, pero el script en sí sigue igual.

## Mover personas

Pulsa **Mover personas** (P).

1. En el panel **Historia y escena**, elige una escena y una tabla de personas o de puntos de llegada.
2. Arrástralos por el mapa. Mantén ⇧ al soltar para ajustar a los 8 píxeles más cercanos.
3. Guarda.

Los puntos de llegada son donde aparece el grupo al entrar en un lugar. Pasa el cursor sobre una persona para ver quién es y qué dice. Las personas que esperan fuera del mapa hasta que la historia las trae están juntas, normalmente en la esquina superior izquierda, dibujadas una sola vez con un número como "×6"; arrastra una fuera para colocarla.

## Sello: copiar y pegar

Pulsa **Sello** (S).

1. Arrastra un rectángulo en el mapa para copiarlo.
2. Haz clic para pegar, aquí o en otro lugar que use el mismo conjunto de bloques.
3. Pulsa Esc para volver a copiar.

- **Zonas de paso y altura** copia eso junto con los bloques, y está activado por defecto.
- **Solo objetos** pega solo los árboles y otros objetos, no el suelo que tienen debajo.
- Un pegado es un solo paso de deshacer, y lo que copiaste se conserva al cambiar de lugar y al recargar.
- Los lugares con otro conjunto de bloques rechazan el pegado, porque cada bloque dibujaría una imagen equivocada.

## Importar tus propias imágenes

**Importar imagen…** está en el panel de Sello. Funciona en lugares cuyos gráficos no se comparten con ningún otro lugar, que son 27 de los 182 en una copia nueva del juego. En los demás, el editor se niega, porque tu imagen cambiaría el aspecto de otros lugares.

1. Elige **Capa superpuesta** (se dibuja sobre el suelo, con fondo transparente) o **Suelo**.
2. Pulsa **Importar imagen…** y elige un PNG, GIF o BMP. Puede cubrir como máximo 256 casillas de 16×16 píxeles, por ejemplo 256×256 píxeles, aunque una imagen detallada puede quedarse sin espacio antes. Si pasa, el editor lo dice.
3. Revisa la vista previa. Muestra los colores que el juego dibujará de verdad y cuánto espacio queda.
4. Pulsa **Añadir al conjunto de tiles**. Los bloques nuevos van al portapapeles de Sello, listos para colocarlos con un clic.

La imagen se ajusta a los colores de este lugar, y las piezas repetidas se reutilizan para ahorrar espacio. Cuando las hojas están llenas, el editor reutiliza los gráficos de bloques que el lugar nunca usa, y esos bloques desaparecen entonces de la paleta.

## Tablas de historia y escena

El panel **Historia y escena** muestra las escenas que usan este mapa y las tablas que hay detrás, con nombres sencillos como "Puntos de llegada: normal". Los puntos de llegada y las personas se ven en el mapa. Las salidas se editan como una lista, con una comprobación de que el punto de llegada que elijas existe. Casi siempre es más fácil usar las herramientas Puertas, Eventos y Mover personas.

## Combates en un lugar

Pulsa **Combates…** para ver los combates aleatorios del lugar en el que estás: con qué frecuencia hay combates y qué grupos de enemigos aparecen, con la probabilidad de cada uno. Cámbialos y pulsa **Guardar**. En la mayoría de cuevas y mazmorras los combates ocurren en cualquier sitio por el que camines; en algunas, solo en las casillas pintadas como **Suelo con encuentros A** en Zonas de paso. Algunos lugares comparten sus combates con otros, y el cuadro de diálogo lo indica: un cambio se ve en todos ellos.

## Conexiones

Pulsa **Conexiones** para ver cualquier lugar en el centro, con todos los lugares que llevan a él a la izquierda y todos los sitios adonde lleva a la derecha. Haz clic en un lugar para ir allí, o pulsa **Abrir** para saltar a esa puerta en el editor. Usa la casilla de búsqueda para encontrar un lugar.

## Atlas: todos los lugares a la vez

Pulsa **Atlas** para ver todos los lugares en un mismo lienzo, unidos por líneas que representan sus puertas y salidas. Los lugares de Golden Sun no se unen borde con borde, así que el atlas los coloca por su cuenta: cada pueblo o mazmorra queda cerca de su sitio en el mapa del mundo, con sus casas y salas al lado, empezando por la entrada.

- Arrastra el fondo para moverte y usa la rueda para hacer zoom. **Ajustar** lo muestra todo.
- Pasa el cursor sobre un lugar para resaltar sus puertas y los lugares adonde llevan.
- Haz clic en un lugar para abrirlo en el editor. Arrastra uno para moverlo: el atlas recuerda dónde lo pusiste, y **Restablecer disposición** lo devuelve todo a su sitio. La posición de los lugares en el atlas es solo para ti; no cambia el juego.
- Las líneas continuas salen de una puerta; las discontinuas son salidas que usa una escena o un script de la historia.

## El mapa del mundo

Elige el mapa del mundo arriba del todo de la lista de lugares. Pulsa **← Lugares** para volver.

| Herramienta | Tecla | Qué hace |
|---|---|---|
| **Ver** | V | Pasa el cursor para ver la región de un sitio y lo que hace. Haz clic en un pueblo, una mazmorra o un sitio de paso azul para ver adónde lleva. |
| **Suelo** | G | Pinta bloques de suelo. ⌥-clic toma un bloque, y los bloques recientes quedan a mano. |
| **Capa superpuesta** | O | Pinta montañas, árboles y costa. Por dónde se puede caminar depende de los tiles de ambas capas. |
| **Regiones** | R | Pinta regiones de encuentros. Cada una tiene sus propios combates aleatorios, y cada una lleva el nombre de los pueblos que contiene. En **Combates aquí**, cambia con qué frecuencia hay combates y qué grupos de enemigos aparecen, en terreno abierto y en bosques. |
| **Pueblos** | T | Arrastra un pueblo o una mazmorra para moverlo. Haz clic en uno para cambiar adónde lleva. **Colocar un icono nuevo…** añade uno, con una imagen que usan los propios pueblos del juego; los iconos que añadiste se pueden quitar. |
| **Puntos de paso** | P | Las casillas azules llevan a algún sitio al pisarlas. Haz clic en una para cambiar adónde lleva o quitarla, o haz clic en cualquier otra casilla para crear una nueva. **Añadir una casilla…** hace un punto más ancho: haz clic en las casillas que quieras añadir y luego pulsa Esc. |

- Marca **Zonas de paso**, **Regiones de encuentros** o **Lugares** para verlos en el mapa.
- Cuando mueves un pueblo, **mover también sus puntos de llegada** hace que sigas apareciendo junto a él al salir. Está activado por defecto.
- Los cambios se guardan mientras pintas. **Deshacer** quita el último trazo, y **Rehacer** lo devuelve.
- El mapa de la pantalla de pausa es una imagen aparte, así que no seguirá tus cambios, y los iconos nuevos no tienen marca en él.

## Revisar: encontrar problemas

Pulsa **Revisar** para repasar todos los mapas en busca de problemas que causarían tus cambios. Cada uno viene con una solución y un botón **Mostrar** que abre el lugar y rodea la casilla durante unos segundos. Busca:

- puertas que no llevan a ninguna parte o que llevan a un punto de llegada que no existe;
- cofres que no se pueden abrir, que no tienen nada definido, que se vuelven a llenar o que comparten una marca de "abierto";
- más de 10 cofres y piedras en un lugar;
- casillas que usan un bloque o una altura que el lugar no tiene;
- líneas que escribiste y que la fuente del juego no puede dibujar;
- lugares cuyos archivos se han dañado;
- ediciones que ya no encajan después de que se actualizara el código fuente del juego.

El juego original tiene sus propias rarezas, y están ocultas salvo que marques **Mostrar también las rarezas del juego original**. En un lugar que has editado, una rareza que ya tenía el original puede aparecer como tuya. En la página de un lugar, Jugar, Exportar y **Compilar** ejecutan Revisar por ti primero y preguntan antes de seguir si hay problemas. En la página del mapa del mundo, Jugar y Compilar no lo hacen, así que pulsa Revisar desde un lugar. Si Revisar no puede terminar, lo dice y pregunta antes de seguir.

## Jugar a tu juego

Pulsa **▶ Jugar**. Guarda, revisa, compila y abre tu juego en mGBA, empezando en el lugar que estás editando. Desde la página del mapa del mundo, compila y empieza en el mapa del mundo, sin la revisión.

- Cada vez que pulsas Jugar es una **partida nueva**: Isaac solo, sin avance en la historia, así que un lugar puede verse como su versión del principio del juego.
- Apareces en el primer punto de llegada del lugar desde el que el grupo puede seguir caminando, según las reglas de movimiento del juego, no en el sitio que estás viendo. Las escenas de la historia no se tienen en cuenta, así que en algunos lugares todavía puedes empezar dentro de una. Si pasa, elige otro punto de llegada en **Empezar en**, junto a ▶ Jugar, y vuelve a pulsar Jugar.
- Una compilación después de cambiar un mapa tarda unos 20 segundos.
- El punto de inicio solo existe en una copia desechable del juego, así que tu mod exportado sigue arrancando con normalidad desde la pantalla de título.

## Compartir tu mod

Pulsa **Exportar mod…**.

1. Rellena un **Nombre** y, si quieres, tu nombre y lo que cambia.
2. Pulsa **Exportar**.

Obtienes un pequeño parche `.bps` y un léame para los jugadores en `~/Documents/GSMapEditor/Exports/`. Pulsa **Mostrar en Finder** para verlos. Si vuelves a exportar con el mismo nombre, el editor pregunta si quieres sustituir el parche anterior o conservarlo y numerar el nuevo. Exportar ejecuta Revisar primero, y prueba cada parche una vez para confirmar que reproduce tu compilación exactamente.

Marca **Guardar también un .ips** si tus jugadores usan parcheadores antiguos. Es mucho más grande, porque IPS no puede registrar datos movidos.

**Comparte el parche, nunca el juego compilado.** Los jugadores aplican el parche a su propia copia, así que nunca repartes el juego en sí. Un parche `.bps` funciona con parcheadores habituales como Rom Patcher JS y Floating IPS, además de con este editor.

## Jugar al mod de otra persona

Pulsa **Parcheador…**.

1. Pulsa **Elegir un parche…** y elige un archivo `.bps`, `.ips` o `.ups`.
2. Elige el juego que vas a parchear: **El juego sin modificar, compilado en este Mac** (no hace falta ROM) o **Mi propio archivo ROM**.
3. Pulsa **Parchear**.

El juego parcheado se guarda en `~/Documents/GSMapEditor/Patched/`, y puedes pulsar **Jugar en mGBA** o **Mostrar en Finder**. Los parches BPS y UPS rechazan el juego equivocado. Los parches IPS no pueden comprobarlo, y el parcheador te lo dice.

## Dónde se guarda tu trabajo

| Qué | Dónde |
|---|---|
| Tu mod | Dentro de la carpeta del código fuente del juego, por defecto `~/Documents/GSMapEditor/alchemy/` |
| Parches exportados | `~/Documents/GSMapEditor/Exports/` |
| Juegos parcheados | `~/Documents/GSMapEditor/Patched/` |
| Ajustes del editor y tu historial de Deshacer | `~/Library/Application Support/GS Map Editor/` |
| Compilaciones temporales, se pueden borrar sin problema | `~/Library/Caches/GSMapEditor/` |

En Windows y Linux, los tres primeros están en `~/GSMapEditor/` en tu carpeta personal de Linux, los ajustes en `~/.config/gs-map-editor/` y las compilaciones temporales en `~/.cache/gs-map-editor/`.

Para hacer una copia de seguridad de tu mod, copia la carpeta del código fuente del juego a un sitio seguro. Tus cambios son archivos normales dentro de esa carpeta.

## Atajos de teclado

En Windows y Linux, usa Ctrl en lugar de ⌘ y Alt en lugar de ⌥.

| Tecla | Lugares | Mapa del mundo |
|---|---|---|
| V | Ver | Ver |
| B | Pintar | |
| C | Zonas de paso | |
| H | Altura | |
| K | Cofre | |
| E | Eventos | |
| D | Puertas | |
| P | Mover personas | |
| S | Sello | |
| F | Activar o desactivar Rellenar, en Pintar, Zonas de paso y Altura | |
| G / O / R / T / P | | Suelo / Capa superpuesta / Regiones / Pueblos / Puntos de paso |
| ⌘Z | Deshacer | Deshacer |
| ⇧⌘Z | Rehacer | Rehacer |
| ⌘S | Guardar | |
| ⌥-clic | Tomar un bloque | Tomar un bloque o una región |
| ⇧ al soltar | Ajustar personas a los 8 píxeles más cercanos | |
| Esc | Cerrar un cuadro de diálogo, o volver a copiar en Sello | Cerrar un cuadro de diálogo |

## Lo que todavía no puede hacer

- **The Lost Age**, ni ediciones que no sean la inglesa.
- **Windows o Linux** como app empaquetada.
- **Lugares totalmente nuevos:** no hay ningún botón para añadir uno.
- **Combates y datos del juego:** no se pueden editar los monstruos, los objetos, las tiendas ni la música. Puedes elegir cuáles de los grupos de enemigos del juego aparecen en cada sitio, y con qué frecuencia, pero no crear grupos nuevos.
- **Scripts de la historia:** puedes cambiar lo que dice la gente y cuándo, y añadir eventos sencillos, pero no escribir escenas cinemáticas.
- **El mapa de la pantalla de pausa.**

## Solución de problemas

| Ves | Qué hacer |
|---|---|
| "Para Jugar se necesita mGBA" | Instálalo desde [mgba.io](https://mgba.io) y vuelve a pulsar Jugar. |
| El editor dice que el código fuente del juego es de una versión que no sabe leer | El código fuente ha cambiado de una forma que este editor todavía no entiende. Aparta esa carpeta y luego usa **Descargar** en la pantalla de instalación. Tu mod se queda en la carpeta que apartaste. |
| "Tus cambios no se pudieron convertir en un juego" | Tus archivos están a salvo. Si menciona una línea que escribiste, cambia sus palabras. Si no, usa **Deshacer** hasta que compile, y pulsa **Mostrar detalles** para ver el mensaje de la propia compilación. |
| "No se pueden leer los archivos de este lugar" | Uno de sus archivos está dañado. Usa **Restaurar lugar…**, o **Deshacer** si lo causó un guardado reciente. |
| "No se puede leer el archivo que guarda tus cambios de personas, puertas y eventos" | Usa **Deshacer**. Si eso no ayuda, restaura ese archivo desde tu copia de seguridad. |
| "Este lugar no tiene espacio para más de estos" | El lugar se ha quedado sin códigos para letreros y mensajes al pisar. Quita uno que hayas añadido. |
| "La fuente del juego no tiene…" | Sustituye ese carácter por letras y signos de puntuación simples. |
| La pantalla de instalación dice que tu carpeta tiene un espacio en su ruta | La compilación no puede usar rutas con espacios. Elige una copia del código fuente del juego en una carpeta sin espacios en su ruta. |
| La app se abre en la pantalla de instalación con un error | El mensaje dice qué no pudo leer. Pulsa **Revisar de nuevo** después de arreglarlo. |
| "Algo salió mal" | Esa acción no terminó. Vuelve a intentarlo y, si sigue pasando, reinicia la app. |
| "Este mapa usa otro conjunto de bloques" | Sello solo pega entre lugares que comparten un conjunto de bloques. |
| "Este lugar comparte sus gráficos con otros lugares" | Importar solo funciona en lugares con gráficos propios. El mensaje nombra algunos que puedes usar. |
| "Ese bloque se retiró" | Sus gráficos se reutilizaron para una imagen importada. Elige otro bloque. |
| "El juego no tiene espacio para más cofres" | El juego se ha quedado sin marcas de "abierto" libres. Quita un cofre que hayas añadido. |
| Falta un cofre en el juego | Un lugar solo muestra sus primeros 10 cofres y piedras. Ejecuta **Revisar**. |
| Revisar dice que una edición "ya no encaja" | El código fuente del juego cambió por debajo de esa edición. Se conserva, pero queda fuera de tu juego. |
| Un lugar se ve distinto de lo que editaste | Puede que estés en otra **Etapa de la historia**, y Jugar empieza una partida nueva, que muestra la versión del principio. |
| La instalación falló a mitad | Pulsa **Revisar de nuevo** y luego el botón del paso. El registro bajo la lista de pasos muestra lo que pasó. |
| Windows: el editor no se abrió en tu navegador | La pequeña ventana de GS Map Editor muestra su dirección: cópiala en tu navegador. |
| Windows: el instalador dice que Ubuntu no está listo | Reinicia Windows si te lo pidió, abre **Ubuntu** una vez desde el menú Inicio para elegir un nombre de usuario y una contraseña, y luego vuelve a ejecutar el instalador. |

## Informar de problemas

Por favor, [abre una incidencia](https://github.com/TRosenvall/GS-Map-Editor/issues/new?template=bug_report.md) con lo que estabas haciendo, lo que pasó, y el chip y la versión de macOS de tu Mac. Cuando el editor ofrezca **Mostrar detalles** o un registro de la instalación, pulsa **Copiar** y pégalo. Por favor, no adjuntes ROMs ni archivos del juego.

## Aspectos legales

El código propio de GS Map Editor está bajo la [licencia MIT](LICENSE). Las herramientas incluidas mantienen sus propias licencias, que se enumeran en [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

El editor no contiene ninguna ROM ni gráficos del juego, y no distribuye el texto del juego. Los nombres y las imágenes se leen de tu propia copia del código fuente del juego mientras se ejecuta. Golden Sun pertenece a Nintendo y Camelot, y este proyecto no está afiliado a ellos. Alchemy es un proyecto aparte con sus propias condiciones.

Por favor, no compartas juegos compilados. Comparte parches en su lugar.

## Desarrolladores

Cómo compilar la app, las pruebas, cómo llegan las ediciones al juego y cómo seguir las actualizaciones de alchemy está todo en [docs/es/DEVELOPING.md](docs/es/DEVELOPING.md).
