<!-- translated from docs/PRODUCT.md @ e6b4dbb6d85f -->
# gs-mapedit para jugadores: plan de producto

*Esta es una traducción del documento en inglés [PRODUCT.md](../PRODUCT.md); si los dos difieren, el inglés es el actualizado.*

**Público:** fans y modders sin formación técnica, es decir, sin terminal, hexadecimal, C, git ni sistemas de compilación.
**Entrega:** una aplicación de escritorio empaquetada con instalador.
*(Decidido por el dueño del proyecto, 2026-10-20.)*

La capa del motor que existe hoy sigue siendo la base. Eso abarca los formatos de archivo, los guardados idénticos byte a byte, los invariantes, el gancho de las tablas de escena y la compilación. Este plan trata de la capa que ven los jugadores.

## Principios

1. **Nombres, imágenes y lugares, nunca códigos.** Cada valor que ve un jugador tiene nombre, vista previa o se muestra en un mapa. Los números en bruto quedan detrás de un interruptor "Avanzado".
2. **Una intención, una acción.** "Añadir un cofre con un Herb" se convierte en una sola acción, aunque toque la lista de marcadores, la colisión, un evento de escena y un indicador nuevo.
3. **Imposible romper el juego sin darse cuenta.** Los invariantes se hacen cumplir como hoy, y se explican en lenguaje sencillo: "Esta puerta todavía no lleva a ningún sitio." (✅ el botón Revisar, que también se ejecuta antes de cada compilación.)
4. **Siempre a un clic de jugar.** Edita y luego juega. La compilación es invisible salvo que falle, y los fallos se leen como orientación, no como salida del compilador.
5. **Sin distribuir ROMs.** Los mods se comparten como archivos de parche que los jugadores aplican a su propio volcado del cartucho.

## Lo que hacen los jugadores (recorridos → pantallas)

| Recorrido | Pantalla / interacción | Piezas del motor (¿existen?) |
|---|---|---|
| Explorar los lugares del juego | **Vista del mundo:** el mapa del mundo más cada pueblo/mazmorra, con las conexiones dibujadas | Renderizador ✅, vista de Conexiones ✅ (lugar por lugar), renderizador del mapa del mundo (prototipo de investigación) |
| Repintar parte de un mapa | **Pintar:** paleta de tiles por tema, pinceles, relleno, copiar/pegar zonas | Pintado de bloques ✅; relleno/copia/zonas ❌ |
| Cambiar por dónde se puede caminar | **Pincel de zonas de paso:** transitable / bloqueado / saliente / escalera / agua, mostrado como una capa limpia | Pintado de colisión ✅; **códigos con nombre ❌ (investigación)** |
| Mover una puerta / cambiar adónde lleva | Haz clic en una puerta y elige el destino haciendo clic en el mapa de destino | ✅ herramienta Puertas |
| Añadir/mover un cofre o una Piedra de Psinergía | Suelta un cofre; elige el contenido (selector de objetos con iconos, monedas, mímico) | ✅ herramienta de cofres (objetos, monedas); las piedras solo se mueven |
| Colocar/mover personas | Arrastra PNJ con vistas previas de sus sprites; ve y edita lo que dicen | Posiciones ✅; **vistas previas de sprites ❌, búsqueda de diálogos ❌** |
| Probarlo | **Jugar:** compilar y abrir el emulador en ese mapa | Jugar con un clic ✅ (guarda, revisa, compila y abre en el lugar que se está editando) |
| Compartirlo | **Exportar mod:** un archivo de parche más una descripción | ✅ BPS de la compilación original a la compilación del mod |
| Deshacer errores / empezar de nuevo | Panel de historial; "restaurar este mapa" | Deshacer ✅ (solo en la sesión); historial persistente ❌ |

## Capa de nombres (necesita investigación, sobre todo consultas)

- **Códigos de colisión:** pared, suelo, salientes, puntos de escalada, puntos de búsqueda, peligro, salidas, cofres. Fuentes: `step.c`, `events.c`, los documentos de investigación.
- **Escenas:** nombres de `scenes.s` más nombres de zona (los propios nombres de lugares del juego) para mostrar.
- **Objetos:** nombres de `include/item_ids.h`, más los iconos de objetos de los gráficos del juego.
- **Sprites:** id de sprite → nombre y una imagen de vista previa a partir de los gráficos de objetos.
- **Diálogo:** id de mensaje → texto de `text/en.po` (10.724 entradas).
- **Indicadores:** nombres de `include/flags.h`, más un asignador de indicadores nuevos para cofres (≥ 0xe00, sin usar).

## Arquitectura de empaquetado (recomendación)

- **Envoltorio:** pywebview (el WKWebView nativo) en un paquete de PyInstaller: una sola `.app` de 30 MB que contiene Python, el servidor y las páginas. *(Cambiado desde Tauri, 2026-10-22: el backend ya es Python, y Tauri añadiría un toolchain de Rust sin ganar nada por ahora. Tauri sigue siendo una opción si el backend pasa a Rust.)*
- **Backend:** el servidor Python de hoy, en el mismo proceso.
- **Código fuente del juego:** la aplicación descarga alchemy en un commit fijado que hemos verificado. Los jugadores nunca ven git. Las actualizaciones son explícitas: "Nueva versión de alchemy disponible; probada ✓".
- **Toolchain:** la parte más difícil.
  - alchemy necesita sus compiladores fijados (compilados desde el código fuente), binutils y sus propias herramientas en C (libpng).
  - Plan: compilarlos para cada plataforma en CI y distribuirlos como binarios precompilados. Los compiladores son GPL; publicamos sus fuentes.
  - Plataformas: primero macOS (Intel + Apple Silicon), luego Windows (alchemy solo admite oficialmente Windows a través de WSL, así que el riesgo es un port nativo de las herramientas), luego Linux.
- **Parches:**
  - Como la compilación original es idéntica byte a byte a la ROM comercial, un parche = diff(compilación original, compilación del mod), calculado localmente sin tocar nunca una ROM comercial.
  - Los jugadores lo aplican a su propio volcado con cualquier parcheador BPS, o con nuestra aplicación.
- **Pruebas de juego:** incluir mGBA (MPL-2.0) o detectar uno instalado; arrancar en el mapa editado si un punto de entrada de depuración lo permite.

## Hitos

1. **Interfaz para jugadores en la aplicación actual.** Todo esto pasa directamente al envoltorio de escritorio. Abarca:
   - la capa de nombres;
   - los pinceles de zonas de paso;
   - puertas enlazadas con un clic;
   - selectores de objetos/sprites;
   - una acción de añadir cofre;
   - validación en lenguaje sencillo;
   - la vista del mundo/conexiones.
2. **Prueba de empaquetado (macOS):** ✅ paquete de la aplicación e instalación del primer arranque (descarga alchemy, compila una vez). ✅ toolchain incluido (sin Homebrew). Pendiente: firma/notarización (necesita un Developer ID), compilación nativa para Apple Silicon, una prueba en un Mac realmente nuevo. Éxito = un Mac nuevo pasa de cero a "Jugar" sin terminal.
3. **Exportar parches** ✅ (BPS, comprobado con rom.sha1). Importar (aplicar parches de otros en la aplicación) sigue pendiente.
4. **Edición del mapa del mundo** (etapas 4–5 de SPEC.md) en la interfaz para jugadores.
5. **Empaquetado para Windows y Linux.**

## Riesgos

- **Portabilidad del toolchain (Windows).** La compilación de alchemy da por hecho un shell de Unix. Esto puede necesitar integración con WSL o un port nativo de sus pequeñas herramientas en C.
- **Cambios constantes en alchemy.** alchemy cambia a diario. Fija un commit, y condiciona las actualizaciones a nuestras comprobaciones de ida y vuelta y de renderizar todo, más una compilación de prueba.
- **Alcance del "significado".** Algunos códigos de colisión y tipos de evento siguen siendo desconocidos incluso para alchemy. Lo desconocido sigue visible pero etiquetado como "desconocido (avanzado)".
- **Postura legal:** nunca distribuimos ROMs, recursos extraídos ni juegos compilados. Los jugadores no aportan nada (The Broken Seal se compila desde el código fuente), y la aplicación descarga alchemy por sí misma.
