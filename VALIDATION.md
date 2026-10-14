# Verificación de Draw to Life

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
