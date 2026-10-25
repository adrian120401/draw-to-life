# Verificación de Draw to Life

## Minijuego de burbujas · 16 de octubre de 2026 (17 de octubre UTC)

Nuevo juguete Burbujas: cinco aciertos, hasta tres objetivos simultáneos,
última burbuja dorada y celebración de 2.4 segundos con tres saltos y un máximo
de 48 piezas de confeti. Cinco puntos indican el avance. No hay cuenta atrás
ni derrota; se puede salir siempre, repetir o volver al juego libre.

- **27 tests JavaScript** pasaron: cinco aciertos únicos, ids viejos/dobles
  ignorados, final dorado y celebración única, limpieza de partículas,
  repetición/salida, escenas largas acotadas, movimiento reducido y guardas
  de pausa/destrucción. Se mantienen las regresiones de guardar la pelota.
- Corregida la continuidad de una burbuja sin tocar durante más de diez
  segundos: el reinicio del tiempo producía un salto de **41.57px** en 2ms;
  ahora recorre **0.027px** en ese mismo intervalo. La regresión de continuidad
  falló antes de quitar el reinicio y pasa con la deriva sinusoidal continua.
- **17 tests Python** del flujo UI, expresiones y paquete portable pasaron;
  la exportación comprueba los controles nuevos. Ruff, sintaxis JavaScript
  y `git diff --check` sin errores.
- **Chromium en 1440 × 900 y 390 × 844**: completar cinco aciertos con ratón,
  toques CDP y teclado, foco conservado y transferido al repetir, salida con
  cruz/Volver/Escape, pausa que congela el reloj y deshabilita objetivos,
  repetición desde cero y pelota que sigue pudiéndose guardar.
- Con movimiento reducido las burbujas permanecen quietas y se puede ganar
  sin saltos ni confeti. HTML recién exportado abierto desde `file://` y
  juego comprobado sin conexión.
- **Flujo completo real en la app por LAN**: subida de `test1.png`, generación
  CUDA y entrada automática al resultado; cinco aciertos y vuelta al juego
  libre dentro del iframe de Gradio a 390 × 844, sin desborde. Ejecución
  `outputs/20261017_012924_a65f9d/`: `completed`, **81.32 s** totales y
  **37.11 s** de difusión. Esta ejecución valida integración, además de las
  capturas del visor independiente descritas abajo.
- Muestra orientativa de escritorio: **91 renders / 1.5 segundos**, media
  **0.17 ms**, p95 **0.30 ms** dentro de `render()`, incluidos los objetivos
  DOM. No mide toda la composición ni representa rendimiento físico móvil.
  Objetivos medidos a 390px: **52 × 52px**, por encima del mínimo de 44px.
- Detector ejecutado una vez: aviso previo de color `#3e2757`; dos avisos
  nuevos de tamaño/radio se corrigieron usando los pasos existentes 20/22px.
  Capturas finales en `.impeccable/review/bubbles-*.png`, realizadas con un
  perro real generado previamente y el HTML nuevo, sin repetir la inferencia
  para estas capturas. No se presenta el viewport ni CDP como teléfono físico.
- Revisión independiente: composición y juego aprobados; continuidad de la
  deriva corregida y verificada. La última corrección fue sincronizar el
  sidecar de diseño; el revisor la puntuó como resuelta y devolvió **ship**
  para esa corrección. Ambos documentos de diseño quedaron actualizados.

## Corrección de pelota permanente · 16 de octubre de 2026

Reproducido: la pelota seguía activa tras 60 segundos y tocar de nuevo su
control solo volvía a lanzarla. No existía una salida del juego desde la UI.
Ahora ese control alterna entre Pelota y Guardar; también se puede arrastrar
la pelota a su lugar. Guardarla detiene la persecución, termina la reacción
de juego y deja que la mascota vuelva al centro, conservando una comida activa.

- **20 tests JavaScript** pasaron, incluidas dos regresiones que fallaban
  antes del cambio: guardar desde el control y devolver la pelota al lugar.
- **17 tests Python** del flujo UI, expresiones y exportación pasaron.
- **Chromium, 1440 × 900 y 390 × 844**: lanzar/guardar con ratón, teclado
  y toque CDP; arrastrar para lanzar sigue funcionando; recoger la pelota
  en vivo y devolverla; vuelta al centro y alimentación concurrente.
- HTML recién exportado probado desde `file://`. Detector de diseño sin
  hallazgos en los tres archivos modificados. Capturas `ball-*-desktop.png`
  y `ball-*-mobile.png` en `.impeccable/review/tactile/`.
- Revisión independiente de esta corrección: **ship**, sin cambios pendientes.
  DESIGN.md y el sidecar documentan los estados de lanzar/guardar.

## Juego táctil y cámara · 16 de octubre de 2026

Se conserva el mundo lila y el flujo de tres pantallas. El juego ahora combina
fruta arrastrable hasta la boca, caricias, cosquillas y pelota con rebotes,
persecución y empujones. La bienvenida dura aproximadamente un segundo y no
hay un bloqueo global entre comida, mimos y juego. Hay sonido breve con mute,
pausa, teclado y movimiento reducido. Cámara y galería comparten el mismo
pipeline y reintento; se agregaron HEIC/HEIF y acceso LAN optativo.

- **86 tests Python** pasaron en el venv Windows: lectura HEIC/HEIF con EXIF,
  archivos dañados, entradas de cámara/galería y limpieza, bind local/LAN,
  generación, contrato y exportación. **18 tests JavaScript** pasaron: alimento
  único y retorno al fallar/cancelar, respuestas simultáneas, captura cancelada,
  física acotada durante 20 segundos y estados con movimiento reducido.
- **Ruff, sintaxis JavaScript, pip check y git diff --check** sin errores.
  Continúan dos avisos de deprecación NumPy en los tests de Diffusers.
- **Flujo completo real por Gradio y Chromium**: botón “Sacar foto” → archivo
  HEIC → análisis/generación local CUDA → visor automático. Ejecución
  `outputs/20261016_231435_d76aa3/`: `completed`, **105.46 s** totales,
  **40.26 s** de difusión, perro reconocido y ZIP generado. La entrada HEIC
  se codificó desde `test1.png`; no es una captura de una cámara física.
- **Navegador 1440 × 900 y 390 × 844**, sin desborde horizontal: fruta
  arrastrada a la boca transformada, comida mientras juega/recibe mimos,
  roce corporal con cosquillas, lanzamiento y persecución de pelota, mute,
  pausa que congela la física, teclado y movimiento reducido estable.
  Cancelar un toque mediante CDP devuelve la fruta y libera la captura.
- **Compatibilidad**: pato, guía de rig libre y manifest v1 sin variantes
  opcionales cargan y comen. La guía libre valida estructura y movimiento,
  no calidad de generación. El HTML continúa jugando sin red tras cargar.
  Una exportación nueva abrió directamente con `file://` y el navegador sin
  conexión: reproductor, física, audio y comida se cargaron sin servidor.
- **Medición orientativa en Chromium de escritorio**: 116 renders durante
  dos segundos, media **0.18 ms** y percentil 95 **0.30 ms** de trabajo JS
  dentro de `render()`. No incluye toda la composición del navegador ni
  representa rendimiento de un teléfono.
- La app se inició con el argumento real `--lan`; la dirección
  `http://192.168.0.225:7860` devolvió HTTP 200 y abrió en Chromium.
  Sin ese argumento se mantiene el bind local.
- **Revisión independiente de interfaz**: las cinco capturas y la escena
  conservaron el mundo aprobado. La única corrección requerida fue sincronizar
  DESIGN.md y su sidecar con los juguetes y reacciones nuevos. El revisor
  comprobó esa corrección como resuelta y devolvió **ship** para ese punto.

Las capturas están en `output/playwright/tactile/` y
`.impeccable/review/tactile/` (ignoradas por git). Las vistas de resultado
completo usan la nueva generación HEIC; las de comida y cosquillas reutilizan
un perro generado previamente en el visor independiente con el nuevo runtime.

Pendiente de comprobación física: selector nativo y cámara trasera en
iPhone/Android, sonido y fluidez en ese dispositivo, y conexión desde otro
equipo a través del firewall de Windows. El viewport móvil y los eventos CDP
no equivalen a una prueba en un teléfono real. No se cambiaron modelos ni se
redujo artificialmente el tiempo de generación para esta demostración.

## Flujo simple e interacciones · 15 de octubre de 2026 (16 de octubre UTC)

La interfaz ahora muestra carga, espera y juego como pantallas separadas. La
foto inicia la generación automáticamente y el resultado abre el visor sin un
paso adicional. El visor incluye comida, mimos, juego, expresiones de boca y
ojos, pausa, teclado y movimiento reducido. Las nuevas variantes son opcionales
en el contrato v1; se conservan el catálogo existente y la anatomía de cada rig.

- **80 tests Python pasaron** en Python 3.11 de Windows. Cubren el nuevo flujo,
  retorno a carga ante errores, limpieza y reinicio, variantes faciales,
  conservación de nariz y arte original, rutas inválidas y exportación completa.
- **12 tests JavaScript pasaron**: transformaciones heredadas, parpadeo, ciclos,
  estados de comida, retorno al reposo, posición transformada de la boca,
  rechazo de acciones superpuestas y feedback con movimiento reducido.
- **Ruff 0.13.2**, `git diff --check`, compileall, sintaxis JavaScript y `pip check`:
  sin errores. Diffusers conserva dos avisos de deprecación de NumPy en los
  tests de scheduler; no provocaron fallos.
- **Generación real por CLI**, `test1.png`, seed 42: perro reconocido,
  adaptación de cuerpo y cabeza en la **GTX 1050 Ti de 4 GB**, estado `completed`,
  **101.20 s** totales y **40.53 s** de difusión. Resultado en
  `outputs/20261016_024818_2f449f/`, con expresiones y ZIP autosuficiente.
- **Flujo real en navegador**: subida de `test1.png` → “Mirando tu dibujo…” →
  “Dándole vida…” → mascota interactiva. Ejecución
  `outputs/20261016_025158_6a824b/`: **80.68 s** totales, **37.96 s** de difusión,
  estado `completed`, CUDA. Se comprobaron descarga de `character.zip` y
  “Otro dibujo”, que elimina el visor y vuelve a la carga.
- **Playwright / Chromium**, escritorio 1440 × 900 y celular 390 × 844:
  captura de las tres pantallas, comida, mimos, juego, bloqueo de acciones
  simultáneas, pausa y continuación. Alimentación y teclado funcionan sin
  conexión después de cargar el HTML. Con movimiento reducido las matrices
  corporales permanecen estables y la acción termina liberando sus botones.
- **Otras anatomías**: alimentación y juego probados en el pato y en un rig
  libre. La criatura libre de esta comprobación usa una guía estructural para
  validar movimientos; no se presenta como arte generado por IA.
- Se probó una imagen PNG inválida desde el navegador: vuelve a la carga con
  un mensaje breve y sin mostrar un personaje anterior.
- Revisión independiente de interfaz: **ship**, sin correcciones materiales.
  Se inspeccionaron las siete capturas de carga, espera, resultado y comida.
  Una captura de escritorio se repitió después de estabilizar el tamaño del
  iframe; el botón de pausa quedó visible, sin cambiar el código para la toma.

Las capturas finales de composición reutilizan el personaje de la primera
generación real en un servidor de prueba, para comprobar los últimos ajustes
visuales sin repetir inferencia. Ese servidor no forma parte de la app. Las
capturas están en `output/playwright/` y `.impeccable/review/` (ignoradas por git).

El entorno virtual de Windows se recreó con las dependencias fijadas del
proyecto. No se modificaron los pesos ni se regeneró el catálogo. Los tiempos
anteriores son mediciones de estas ejecuciones, no promesas de rendimiento.

## Filtro retirado y adaptación real · 13 de octubre de 2026 (14 de octubre UTC)

La ejecución `20261014_022828_c04812` reconoció `test1.png` como perro, pero falló por el filtro durante la adaptación, que seguía activo tras preparar el catálogo. A pedido del usuario, la generación ahora carga todos los pipelines con `safety_checker=None`, `feature_extractor=None` y `requires_safety_checker=False`. Se retiró la comprobación NSFW posterior y esos componentes dejaron de ser requisitos del diagnóstico y las descargas. Los archivos ya descargados se conservan. Esta decisión reemplaza la omisión temporal limitada al catálogo descrita más abajo.

- **65 tests Python pasaron** en el venv de Windows, incluyendo salida sin campos NSFW, rechazo de imágenes vacías, snapshots sin componentes de filtro y error de generación visible en el visor de Gradio.
- **Ruff 0.13.2**: sin errores en `app.py`, `draw_to_life`, `scripts` y `tests`.
- **Prueba real con pesos locales y CUDA**, mismo `test1.png`, paleta por defecto y semilla `274919534`: visión reconoció perro; se adaptaron cuerpo y cabeza; se guardaron portada, texturas, manifest, HTML autosuficiente y ZIP. Estado `completed`, duración **81.17 s**, difusión **37.17 s**, sin avisos NSFW ni imágenes negras.
- Resultado: [portada](outputs/20261014_023407_b75db5/final_character.png), [visor exportado](outputs/20261014_023407_b75db5/character/index.html), [ZIP](outputs/20261014_023407_b75db5/character.zip) y [metadata](outputs/20261014_023407_b75db5/metadata.json). La portada se inspeccionó visualmente y contiene el perro con la paleta aplicada.

La prueba real ejecutó el pipeline directamente, sin un navegador. El callback de error de Gradio se verificó mediante un test con inferencia simulada; la interacción animada en navegador sigue pendiente.

## Filtro durante la preparación del catálogo · 13 de octubre de 2026

La preparación de bases conocidas omite temporalmente el safety checker de Diffusers antes de generar cada textura. El componente y la detección permanecen en el código; el checker se restaura al terminar la inferencia, incluso si falla. Adaptaciones y creación libre mantienen la detección activada. No se modifica la clasificación de especies.

- **63 tests Python pasaron** en el venv de Windows. Los nuevos tests verifican que el catálogo omite el checker, que otras generaciones lo mantienen y que se restaura tanto al generar una textura como al fallar. La generación simulada conserva los píxeles y la ruta normal sigue rechazando resultados bloqueados.
- **Ruff 0.13.2**: sin errores en `app.py`, `draw_to_life`, `scripts` y `tests`.

El aviso reportado aparece después de generar la textura: Diffusers evalúa el resultado y lo sustituye por negro antes de devolverlo. No es una evaluación de la foto de referencia. No se ha repetido la generación completa con pesos reales ni comprobado visualmente el resultado marcado; los tests de esta corrección simulan la inferencia.

## Corrección de preparación en Windows · 13 de octubre de 2026

Reproducido con Diffusers 0.34.0 el error `final_sigmas_type` al convertir el scheduler DEIS de DreamShaper a DPM. La conversión ahora fija `algorithm_type=dpmsolver++`, `solver_type=midpoint` y `final_sigmas_type=zero`, conservando el calendario de ruido del modelo.

- **60 tests Python pasaron** con el intérprete del venv de Windows (`.venv/Scripts/python.exe -m pytest -q`). Incluyen la carga del generador con schedulers reales de DEIS y PNDM, pesos simulados y cuatro pasos de DPM con tensores finitos. No requieren descargar ni cargar pesos.
- **Ruff 0.13.2**: sin errores en `app.py`, `draw_to_life`, `scripts` y `tests`.
- Corregida también la validación de rutas de texturas con raíz o unidad de Windows, detectada por la suite nativa; comprobadas rutas POSIX y Windows.

Estas pruebas reemplazan la limitación anterior de ejecución de la suite Python. No verifican generación completa del catálogo, calidad de las texturas, inferencia CUDA ni interacción en navegador. Diffusers emitió dos avisos de deprecación de NumPy durante los tests de scheduler, sin fallos.

## Etapa animada · 13 de octubre de 2026

Implementados el catálogo de seis estructuras, preparación con IA local y checkpoints, adaptación por piezas, generación libre, rig versionado, reproductor Canvas y exportación del personaje. **Las seis bases con arte generado todavía no están preparadas en esta copia.** Las guías estructurales no se contabilizan como personajes generados.

Comprobaciones realizadas en esta sesión:

- **18 tests Python pasaron**: contrato del personaje, jerarquías, referencias inválidas, ciclos, pivotes, rutas de texturas y clasificación/ambigüedad de especies. Ejecutados con Python **3.13.5** temporal; la instalación de Windows sigue destinada a Python 3.11.
- **7 tests JavaScript pasaron**: herencia de transformaciones, parpadeo, retorno al reposo, movimiento reducido, ciclos inválidos, matrices finitas y período del estado idle.
- **Ruff 0.13.2**: sin errores en `app.py`, `draw_to_life`, `scripts` y `tests`.
- **Compileall y validación sintáctica de JavaScript**: sin errores.

Comprobaciones pendientes:

- La suite completa de pytest no pudo recolectar cuatro módulos por falta de numpy/Pillow en el entorno temporal. Los tests de máscaras, colores, checkpoints, exportación y orquestación están escritos pero **no se declaran aprobados**.
- Generación real de las seis bases con DreamShaper 8 y revisión de sus texturas y movimientos.
- Flujo real con `test1.png`, dibujo coloreado y criatura fuera del catálogo, comparación de tiempos y repetición sin internet.
- Ejecución nativa con Python 3.11 y la GTX 1050 Ti de Windows.
- Interacción en navegador y UI Gradio completas. El sandbox bloquea sockets TCP (`PermissionError: Operation not permitted`); Chrome DevTools cerró el target y el daemon de Playwright no pudo arrancar.

El entorno comenzó sin Python de Linux; se preparó un intérprete temporal y las dependencias necesarias para los checks anteriores. Las descargas de las librerías de imagen se cortaron repetidamente con errores de conexión/SSL y quedaron incompletas. La interoperabilidad WSL → Python de Windows falla con `UtilBindVsockAnyPort`; la política de la sesión rechazó ejecutar ese diagnóstico fuera del sandbox. No se reemplazó el arte de los modelos por imágenes simuladas.

Para completar la preparación en PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\prepare-characters.ps1
.\.venv\Scripts\python.exe scripts\prepare_characters.py --status
.\.venv\Scripts\python.exe -m pytest -q
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

El script publica una base solo después de generar sus texturas y validar el rig. Repetirlo reanuda las piezas completas; un checkpoint corrupto se regenera. Los tests simulados no prueban calidad del arte.

## Verificación histórica de la v1 estática

Verificación realizada el **10 de octubre de 2026**. Las generaciones usan los modelos locales reales; no son outputs simulados de los tests.

## Resultados

| Entrada | Estilo | Colores | Tiempo en CPU | Resultado |
| --- | --- | --- | --- | --- |
| Conejo coloreado | Sticker | Verde y rojo del dibujo | 292 s | [PNG](outputs/20261010_135008_03c218/final_character.png) |
| Gato en lápiz | Cartoon suave | Paleta infantil automática | 247 s | [PNG](outputs/20261010_135525_908fc8/final_character.png) |
| Monstruito con sombrero | Mascota virtual | Paleta por defecto seleccionada | 246 s | [PNG](outputs/20261010_140552_07d28c/final_character.png) |

Todos los resultados son PNG RGB de **512 × 512**, con fondo blanco. Cada carpeta contiene original, recorte, aislamiento RGBA, referencia, guía Scribble y metadata con `status: completed`.

Revisión visual: el conejo conserva orejas largas, ojos, verde y remera roja; el gato conserva orejas triangulares, bigotes, cola y expresión; el monstruito conserva cuerpo redondeado, orejas puntiagudas, sonrisa y sombrero. El sombrero permanece separado del cuerpo, como en el dibujo de muestra: la v1 no asegura corregir automáticamente esa clase de relación espacial.

Las entradas son dibujos **sintéticos con desenfoque leve**, creados con Pillow. Aún no se midió calidad con fotografías reales tomadas por usuarios.

## Checks ejecutados

- **18 tests pasaron**: colores y su conservación durante la limpieza, papel, partes separadas, paleta, inputs inválidos, pesos truncados, metadata, fallos y reintento CUDA → CPU simulado.
- **Ruff:** sin errores.
- **Compileall:** sin errores.
- **pip check:** sin dependencias rotas en el entorno de verificación.
- **Doctor:** los tres modelos completos y legibles.
- Importación de clases de Transformers y Diffusers y construcción de los 33 componentes de Gradio.
- Callbacks de carga y borrado: salida de nueve valores, con imagen original y limpieza de resultados anteriores.
- Rutas ASGI: HTML, configuración, esquema API, subida multipart, arranque de cola y vista previa por SSE devolvieron HTTP 200. La subida conserva el nombre original.
- Gato y monstruito procesados con `HF_HUB_OFFLINE=1` y `TRANSFORMERS_OFFLINE=1`.

Los tests de orquestación simulan los modelos caros y no evalúan calidad visual. La tabla de resultados corresponde a ejecuciones separadas con los modelos completos.

## Entorno y límites de la verificación

La verificación utilizó Python 3.11 en Linux/WSL y **PyTorch 2.7.1 + CPU**. La instalación destinada a Windows usa **PyTorch 2.7.1 + CUDA 11.8**; su ejecución nativa con la GTX 1050 Ti queda pendiente.

El sandbox de esta sesión bloquea creación de sockets de red y envío por sockets entre threads (`PermissionError: Operation not permitted`). También bloquea la interoperabilidad para ejecutar Python de Windows desde WSL. Por eso no se pudo abrir un servidor TCP ni revisar la interfaz en un navegador real.

Las rutas ASGI se comprobaron con un harness temporal que ejecuta callbacks rápidos en un solo thread, sin modificar el código de la aplicación. Esto verifica rutas, payloads, subida y serialización, pero no reemplaza una prueba de navegador ni de concurrencia nativa.

Los pesos ya están guardados en `models/`, y `.env` apunta a esa carpeta para reutilizarlos desde Windows. Ejecutar `scripts/install.ps1` y luego `scripts/start.ps1` para abrir la demo.

## Hoja de Stitch preparada para la demo — 24 de octubre de 2026

- Se preparó un rig vectorial específico a partir del personaje de referencia, con orejas, brazos, pies, pancita, ojos y boca separados. Procedencia explícita `prepared` / `authored_vector_rig`, sin presentarlo como una base generada por IA.
- El modo automático reconoce el contorno con SIFT + homografía y exige suficientes coincidencias distribuidas en la hoja. Reutiliza el rig, rectifica la foto y extrae colores interiores por región, sin inferencia de visión ni difusión.
- **102 pruebas Python aprobadas**, incluidas 16 nuevas de reconocimiento, fotos simuladas con giro/perspectiva/sombra, transferencia de colores, exclusión de fondos, rechazo de otros dibujos y coincidencias parciales, exportación y respeto de modos manuales. La suite se ejecutó fuera de la sandbox: los sockets internos de asyncio/Gradio quedaban bloqueados dentro de ella. Dos advertencias de deprecación existentes de Diffusers/NumPy.
- **27 pruebas del reproductor aprobadas** con `node --test tests/character-player.test.cjs`; Ruff y `git diff --check` de los archivos modificados sin errores.
- En Chrome se cargó la foto original mediante **Sacar foto** en una instancia nueva en `127.0.0.1:7861`: abrió la mascota interactiva, funcionaron comida y pelota y se comprobó visualmente la composición. Metadata: `generation_mode=prepared_demo`, `live_model_inference=false`, `models={}`, `duration_seconds=2.22`. Esa duración corresponde al procesamiento local y empaquetado; no mide la captura ni la transferencia desde un celular.
- Falta la prueba física con la hoja recién pintada y la cámara del teléfono. Mantener el personaje completo, cercano y sus contornos negros visibles; una coincidencia insuficiente conserva el flujo normal de IA.

### Corrección tras la prueba con el personaje dibujado de nuevo

- Se recuperó `outputs/20261024_145644_05c282/original.jpg`. Sus metadatos ya describían `stitch`, pero la máscara incluía textura y sombras de toda la hoja; el camino rápido anterior solo comparaba trazos de la misma hoja. Esto explica el rig rectangular, aunque la descripción visual identificara el personaje.
- Se separan pigmentos y lápiz de papel claro mediante color y contraste fuerte, descartando grano y motas; se cierran cortes pequeños antes de rellenar la silueta. Se conserva el blanco opaco dentro del personaje y el exterior transparente. En hojas inclinadas se enmascaran las esquinas de mesa incluidas en el recorte. El análisis visual recibe la imagen aislada sobre blanco.
- Cuando SIFT no coincide, se compara la silueta completa con la referencia original y el rig, normalizando escala, proporciones y giros acotados. Se exige solapamiento ≥0,76 y una ventaja ≥0,07 respecto a otros animales. La foto rehecha no se añadió a las referencias: está en `tests/fixtures/stitch-redrawn.jpg` solo para regresión. La foto obtiene aproximadamente 0,85 de solapamiento frente a 0,62 de los otros animales y usa `prepared_demo` sin cargar modelos.
- **111 pruebas Python aprobadas**, incluidas nueve regresiones nuevas: foto real, hoja vacía con textura y sombra, lápiz gris, giros, colores simulados por zona, mesa con hoja inclinada y recorrido completo sin visión ni difusión. Dos advertencias existentes de deprecación de Diffusers/NumPy. Ruff sin errores.
- Comprobación local de procesamiento y exportación con la foto rehecha: alrededor de 4,2 segundos en la primera ejecución medida. El contorno de birome azul sin relleno no se toma como pintura de la piel. La transferencia de colores se probó con rellenos simulados; sigue pendiente una captura física de esa hoja ya pintada.
- Se inició una instancia actualizada para comprobar el navegador; el conector de Chrome rechazó acceder a la ruta local del original guardado, por lo que no se afirma una nueva verificación de cámara desde el navegador para esta corrección. Los callbacks y el recorrido de procesamiento/exportación se verificaron con pruebas y con la foto guardada.
