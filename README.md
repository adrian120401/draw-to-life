# Draw to Life · mascotas animadas

La app convierte dibujos en mascotas 2D de caricatura que **respiran, parpadean, comen y reaccionan a los mimos y al juego**. El catálogo tiene una estructura por animal: perro, gato, pato, cerdo, conejo y oso. Las bases se preparan previamente con IA local; después se recolorean y se corrigen sus piezas manteniendo las uniones y las animaciones.

## Preparar y ejecutar la versión animada

En PowerShell desde la carpeta del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\prepare-characters.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

La preparación descarga explícitamente los modelos y crea las seis bases. Puede tardar mucho; no se prometen tiempos en segundos. Si se interrumpe, repetir el comando reutiliza las piezas completadas. Las bases se publican solo cuando el rig y sus texturas están completos. Para ver el estado real:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_characters.py --status
.\.venv\Scripts\python.exe scripts\prepare_characters.py --animal dog --seed 42
```

`--force` regenera conservando un backup de la base anterior. Los checkpoints de preparación quedan en `assets/characters/.work/`. Las guías estructurales están definidas en código y **no cuentan como bases generadas**: el catálogo exige texturas producidas por IA y un rig válido.

La interfaz tiene tres pantallas: **subir una foto → analizar/generar → jugar con la mascota**. La generación comienza al subir una imagen válida y abre automáticamente el resultado. Usa **Cartoon infantil**, selección automática de especie y colores del dibujo; las imágenes sin color usan la paleta configurada. El fondo lila y sus formas se adaptan a escritorio y celular.

La pantalla final es una escena táctil: arrastrá la **fruta hasta la boca**, acariciá la cabeza, frotá la pancita para hacer cosquillas o lanzá la **pelota** para que la mascota la persiga y la empuje. También podés tocar los juguetes. La bienvenida dura alrededor de un segundo; la mirada, el parpadeo y las reacciones mantienen vivo al personaje sin agregar brazos. Las respuestas se combinan: podés dar mimos y jugar mientras come. Hay sonidos cortos, un control para silenciarlos y pausa. Se puede crear otro dibujo y guardar el paquete portable; no hay hambre, monedas, voz ni progreso persistente.

Cuando la pelota está en juego, su control cambia a **Guardar**: tocarlo o devolver la pelota arrastrándola a su lugar termina la persecución y la mascota vuelve al centro. Con teclado, el mismo botón alterna entre lanzar y guardar; `pet.toggleBall()` permite esa alternancia desde código, mientras `pet.play()` conserva su comportamiento de lanzamiento.

**Burbujas** abre una ronda de cinco aciertos: tocá las burbujas para que la mascota reaccione, reventá la última burbuja dorada y festejá con tres saltitos y confeti. Cinco puntos muestran el avance. La ronda no tiene cuenta regresiva ni derrota; al terminar podés repetir o volver, y la cruz permite salir en cualquier momento. Al entrar se guarda la pelota. Pausa y mute siguen disponibles. Con teclado, usá Tab y Enter para elegir/reventar burbujas, o Escape para salir; con movimiento reducido quedan quietas y la celebración conserva la expresión sin saltos ni confeti. También funciona sin conexión en el paquete descargado. Desde código están disponibles `pet.startBubbles()`, `pet.popBubble(id)` y `pet.stopBubbles()`.

Para usarla desde un teléfono conectado a la misma Wi-Fi que la PC:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Lan
```

La terminal muestra la URL de la PC para abrirla en el teléfono. La PC debe permanecer encendida y Windows debe permitir Python en la red privada. Sin `-Lan` sigue disponible solo en la PC. También podés ejecutar `python app.py --lan` desde el entorno instalado.

**Sacar foto** abre el selector de cámara nativo con preferencia por la cámara trasera; **Subí tu dibujo** conserva la galería. El comportamiento exacto del selector depende del navegador del teléfono. Se admiten JPG, PNG, WebP, HEIC y HEIF, con orientación EXIF corregida y los mismos límites de 30 MB y 40 megapíxeles. No hace falta mantener una cámara en vivo ni usar `getUserMedia`.

### Hoja de Stitch preparada para la demo

La hoja de referencia ya está preparada en `assets/demo/stitch/`, con un rig 2D propio, piezas, pivotes y expresiones. Se inicia con los mismos scripts `scripts/start.ps1` o `scripts/start.ps1 -Lan`; no hace falta ejecutar una preparación adicional. Reiniciar la app carga los cambios.

Al usar **Sacar foto** (o la galería), primero se separa el pigmento del papel claro, su textura y sombras suaves. Se eliminan motas aisladas y se cierran pequeños cortes del contorno antes de rellenar la silueta; los interiores sin pintar conservan superficie opaca y blanca. Los modelos reciben el personaje aislado sobre blanco.

El modo automático intenta reconocer la misma hoja mediante SIFT y una homografía validada. Si se dibujó otra vez, compara la silueta completa con la referencia y el rig, normalizando escala, proporciones y giros de hasta 18°; exige una coincidencia suficiente y una ventaja frente a las formas de los otros animales del catálogo. Este segundo camino admite diferencias entre trazos y contornos de birome azul. No usa la foto del segundo dibujo como otra plantilla: está guardada únicamente como prueba de regresión.

Si coincide, reutiliza las piezas animadas y toma tres colores por región de la foto nueva: cuerpo/cabeza, pancita y orejas/nariz. Las regiones se alinean antes de medir sus colores para evitar incluir mesa o garabatos exteriores; en el dibujo rehecho también se descartan líneas finas de birome al medir el relleno. Las zonas sin color detectable quedan claras. La transferencia conserva el sombreado y los contornos del rig, sin copiar cada trazo del lápiz. No se ejecutan SmolVLM ni difusión durante ese recorrido. Su procedencia se registra como `prepared` / `authored_vector_rig`, diferenciada de las bases generadas con IA.

El personaje debe aparecer completo sobre papel claro y con trazos visibles. Las coincidencias parciales o insuficientes siguen el flujo normal de IA; también lo conservan los modos explícitos `free`, `template`, `legacy` y la selección manual de otro animal. El paquete de demo permite usar este personaje incluso sin los modelos de generación instalados; otros dibujos siguen necesitando los modelos. El reconocimiento por forma tiene umbrales conservadores y no garantiza cualquier versión de Stitch ni sustituye un clasificador semántico general.

Para reconstruir el recurso a partir de la foto de referencia original (900×1600), está `python scripts/prepare_demo_character.py RUTA_DE_LA_FOTO`. Este comando es de preparación, no se ejecuta durante la demo. Solo se guarda el contorno recortado de la referencia, sin el entorno de la foto. El ZIP portable preparado está en `assets/demo/stitch.zip`.

Los modos y la corrección manual del animal siguen disponibles en la CLI y la API Python:

| Modo | Comportamiento |
| --- | --- |
| Automático | Adapta una base preparada cuando reconoce el animal; de lo contrario crea un personaje nuevo. |
| Adaptar una base | Exige una base disponible; admite seleccionar el animal manualmente. |
| Crear desde cero | Genera piezas nuevas a partir de la silueta y descripción del dibujo. |

Si la especie es ambigua o está fuera del catálogo se usa generación libre, sin importar la demora. Una base existente dañada produce un error explícito. Un fallo técnico conserva los intermedios y nunca muestra una guía ni el resultado anterior como personaje nuevo.

## Personaje animado y paquete para un juego

La salida principal es un **ZIP de personaje animado**. Los PNG son sus texturas, y la portada estática queda disponible aparte. Extraé el ZIP y abrí `index.html`: la vista previa es autosuficiente y no necesita servidor ni internet.

```text
character.json          # contrato de personaje, schema_version: 1
textures/*.png          # capas RGBA del mismo tamaño que el lienzo
masks/*.png             # máscaras invariables de cada pieza
guides/*.png            # referencias y guías estructurales
preview.png             # composición estática transparente
character-player.js     # reproductor sin dependencias de un motor de juegos
index.html              # vista animada con texturas embebidas
```

El contrato incluye tamaño de lienzo, paleta, capas, animaciones y procedencia. Cada capa tiene identificador, padre, pivote `[x,y]` en píxeles del lienzo, ruta relativa de textura, rol de color y movimiento. Las capas faciales admiten `expressions`, un mapa opcional de nombres (`happy`, `closed`, `open`, `chew`) a rutas PNG relativas, y la boca puede declarar `mouth_anchor: [x, y]`. El orden de las capas define el orden de dibujo. La jerarquía transmite los movimientos del cuerpo a la cabeza y la cara; la comida sigue esa misma transformación.

Se mantiene `schema_version: 1`: el reproductor nuevo carga los paquetes anteriores con sus animaciones básicas, y las variantes opcionales no impiden que el reproductor anterior use la textura de reposo. Al adaptar una base antigua se preparan sus expresiones localmente, sin regenerar su cuerpo ni modificar el catálogo. Los PNG de expresión incluyen su procedencia procedural.

Para integrarlo en una página servida localmente:

```javascript
const pet = await DrawToLifePlayer.load(canvas, './character/character.json');
pet.feed(); // false si esta fruta ya se está comiendo o el juego está en pausa.
pet.pet(); // Los mimos se combinan con la comida.
pet.play(); // Lanza la pelota; pet.play(-1) cambia la dirección.
pet.setMuted(true);
pet.setPaused(true);
// Al desmontar la vista:
pet.destroy();
```

También admite `load(canvas, manifest, assets)`, donde `assets` asigna un data URI por identificador de capa y por variante (`mouth__happy`, por ejemplo). Emite `character:react`, `character:actionstart`, `character:actionend`, `character:interaction`, `character:mute` y `character:pause`. Los eventos de acción incluyen `detail.action`; pausa incluye `detail.paused`. Enter/Espacio dan mimos y las flechas lanzan la pelota. Los juguetes son botones accesibles por teclado. Pausar congela la escena; ocultar la página cancela gestos y sonidos. Con movimiento reducido las expresiones responden sin saltos, persecución ni partículas. El HTML y el ZIP incluyen las mismas interacciones que la app y no necesitan conexión.

## Generación y parámetros nuevos

El análisis usa OpenCV/Pillow y SmolVLM2 local. La descripción incluye especie normalizada y un indicador explícito de ambigüedad. DreamShaper 8 + ControlNet generan las texturas de cuerpo y cabeza; orejas, alas y cola reutilizan su acabado. La cara mantiene texturas procedimentales separadas para controlar ojos y boca.

La generación no carga ni ejecuta el filtro NSFW de Diffusers, tanto en el catálogo como en adaptaciones, creación libre y modo v1. La validación sigue rechazando imágenes vacías, pesos dañados y rigs incompletos. Los fallos aparecen también en el visor principal.

Durante la adaptación, la difusión trabaja sobre cada pieza y conserva máscaras, pivotes y solapas ocultas. La paleta cambia tono/saturación preservando sombreado y contornos. Se usan hasta tres colores dominantes, sin asignar cada color original a una parte del cuerpo; los faltantes se completan con la paleta configurable. El rig libre separa cuerpo y cabeza de la silueta del dibujo y coloca una cara en una región interior suficiente. Si el contorno impide esa separación, usa una estructura redondeada nueva y genera sus texturas con IA local, registrando la simplificación. Los errores técnicos se informan explícitamente.

| Variable | Default | Uso |
| --- | --- | --- |
| `CHARACTER_MODEL_ID` | `Lykon/dreamshaper-8` | Modelo SD 1.5 para bases y correcciones. |
| `CHARACTER_CATALOG_DIR` | `assets/characters` | Catálogo local. |
| `PART_IMAGE_SIZE` | `384` | Resolución de difusión de cada pieza, colocada después en su máscara original. |
| `CATALOG_STEPS` | `40` | Pasos de referencia para creación. |
| `CATALOG_STRENGTH` | `0.55` | Intensidad de creación del acabado. |
| `ADAPTATION_STRENGTH` | `0.30` | Intensidad de las correcciones habituales. |

Se conserva cualquier `.env` existente. Los parámetros de modelos, dispositivo, paleta y lienzo de la v1 siguen disponibles. Visión y difusión se cargan por etapas; CUDA conserva offload y reintento en CPU ante fallos recuperables. Una seed no garantiza igualdad entre dispositivos.

```powershell
.\.venv\Scripts\python.exe scripts\process_image.py test1.png --mode auto --seed 42
.\.venv\Scripts\python.exe scripts\process_image.py test1.png --mode template --animal dog
.\.venv\Scripts\python.exe scripts\process_image.py examples\monstruo.png --mode free
node tests/character-player.test.cjs
```

La CLI y la UI usan animación por defecto. La API Python conserva compatibilidad: llamadas existentes a `Pipeline.prepare()` sin `mode` usan el flujo v1. Para animación indicar `style="Cartoon infantil"` y `mode="auto"`, `"template"` o `"free"`. Los estilos anteriores siguen disponibles con `mode="legacy"`.

Metadata agrega modo efectivo, base utilizada, modelo/revisión, correcciones por pieza, parámetros efectivos, tiempos y paquete exportado. Los tests con modelos simulados no demuestran calidad visual. Para validar los modelos reales hay que preparar las seis bases, revisar sus movimientos y procesar el perro de `test1.png`, un dibujo coloreado y una criatura fuera del catálogo. Ver `VALIDATION.md` para las comprobaciones realizadas y pendientes.

Referencias: [DreamShaper 8](https://huggingface.co/Lykon/dreamshaper-8), [Img2img y strength](https://huggingface.co/docs/diffusers/v0.34.0/en/using-diffusers/img2img). Modelos y dependencias conservan sus propias licencias.

---

# Documentación de la v1 estática (compatibilidad)

Un prototipo **100% local** que convierte una foto de un dibujo infantil en una mascota 2D. La interfaz muestra la foto, el recorte limpio, el dibujo aislado y el personaje generado.

La primera instalación necesita internet para descargar dependencias y modelos. Después, las imágenes se procesan en tu PC, sin API keys ni servicios de generación externos.

## Instalación en Windows

Requisitos: **Python 3.11 de 64 bits**, driver NVIDIA actualizado y espacio libre para el entorno y los modelos. La configuración está pensada para una GTX 1050 Ti de 4 GB y 32 GB de RAM. Reservá aproximadamente **15–20 GB** entre dependencias, modelos y espacio temporal de instalación. La caché de modelos utiliza C: por defecto, aunque el proyecto esté en E:.

Abrí PowerShell en `E:\signs\drawToLife`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\download-models.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Los scripts detienen la instalación si un paso falla. Si necesitás indicar Python explícitamente:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Python "C:\Users\Adria\AppData\Local\Programs\Python\Python311\python.exe"
```

La app abre **http://127.0.0.1:7860**. Para cerrarla, presioná `Ctrl+C` en la terminal. No necesitás activar el entorno virtual para usar los scripts.

En esta copia de trabajo, `.env` apunta a `models/` para reutilizar los pesos descargados durante la preparación. En una instalación nueva, `.env.example` utiliza la caché estándar de C:. El script de instalación conserva cualquier `.env` existente.

También podés ejecutar cada paso directamente:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m draw_to_life.models download-models
.\.venv\Scripts\python.exe -m draw_to_life.models doctor
.\.venv\Scripts\python.exe app.py
```

No sobrescribas `.env` si ya personalizaste la configuración. PyTorch está fijado a la build **2.7.1 + CUDA 11.8**; no hace falta instalar el CUDA Toolkit por separado. Se incluye torchvision compatible y no se requiere Flash Attention, xFormers ni bitsandbytes.

## Uso

1. Fotografiar un personaje completo, preferentemente de frente, sobre papel claro con buena luz.
2. Subir JPG, PNG o WebP (hasta 30 MB y 40 megapíxeles).
3. Elegir **Sticker**, **Cartoon suave** o **Mascota virtual**.
4. Elegir colores del dibujo o paleta por defecto. Un dibujo monocromático usa automáticamente la paleta por defecto.
5. Presionar **Dar vida al dibujo** y esperar el progreso. La descripción es completamente automática.
6. Descargar el PNG o encontrar todos los archivos en `outputs/`.

La lectura visual ocurre en CPU y la generación utiliza GPU con offload a RAM. **No se promete generación en segundos** en una GTX 1050 Ti. Si CUDA no puede completar la generación por memoria o precisión, se reintenta en CPU float32 a la misma resolución; la UI y metadata informan el cambio. El tiempo real depende del dibujo, los parámetros y el equipo.

Si faltan modelos, la app muestra la preparación pendiente y deshabilita la generación. La descarga se puede repetir para completar archivos faltantes. Reiniciá la app tras descargar.

### Dibujos de muestra

`examples/` contiene un conejo coloreado, un gato en lápiz y un monstruito con sombrero. Son **entradas sintéticas de prueba creadas con Pillow**, no personajes generados por IA ni evidencia de calidad del modelo. Se pueden seleccionar desde la interfaz.

Para recrearlos:

```powershell
.\.venv\Scripts\python.exe scripts\make_examples.py
```

### Ejecución sin interfaz

```powershell
.\.venv\Scripts\python.exe scripts\process_image.py examples\conejo.png --mode legacy --style Sticker --seed 42
.\.venv\Scripts\python.exe scripts\process_image.py examples\gato_lapiz.png --mode legacy --style "Cartoon suave" --default-palette
```

## Configuración

Copiá `.env.example` a `.env`. No contiene secretos.

| Variable | Default | Uso |
| --- | --- | --- |
| `MODEL_CACHE_DIR` | Caché estándar de Hugging Face | Directorio de modelos; por ejemplo `C:/DrawToLife/models`. Cambiarlo requiere descargar en ese directorio. |
| `OUTPUT_DIR` | `outputs` | Carpeta de resultados; rutas relativas al proyecto. |
| `DEVICE` | `auto` | `auto`, `cuda` o `cpu`. |
| `IMAGE_SIZE` | `512` | Resolución cuadrada, múltiplo de 8 entre 256 y 768. |
| `INFERENCE_STEPS` | `30` | Pasos de referencia; img2img utiliza una fracción según la intensidad. |
| `IMAGE_STRENGTH` | `0.65` | Cuánto reinterpretar el dibujo; menor conserva más la imagen original. |
| `CONTROL_SCALE` | `0.7` | Peso de los trazos del dibujo. |
| `GUIDANCE_SCALE` | `7.0` | Peso del prompt. |
| `CPU_THREADS` | `4` | Threads de PyTorch; ajustar según CPU. |
| `PALETTE_PRIMARY` | `#91CDB5` | Color principal por defecto. |
| `PALETTE_SECONDARY` | `#FFE2A8` | Secundario por defecto. |
| `PALETTE_ACCENT` | `#F39AA8` | Acento por defecto. |
| `PORT` | `7860` | Puerto local. |

Los tres colores también se pueden cambiar en la interfaz para cada ejecución. Los códigos HEX son una referencia: el generador recibe nombres de color y una imagen inicial coloreada; no se garantiza reproducción exacta de cada HEX.

Los IDs de los modelos son configurables, pero los reemplazos deben ser compatibles con las mismas clases de Transformers/Diffusers y la disposición de archivos verificada. Esta v1 no es un cargador universal de checkpoints.

## Arquitectura

```text
Foto → OpenCV/Pillow → recorte, trazos, silueta y colores
                         ↓
                  SmolVLM2 en CPU → descripción estructurada
                         ↓
       Referencia + trazos + descripción + estilo + paleta
                         ↓
        SD 1.5 + ControlNet Scribble → personaje 2D PNG
                         ↓
                    Gradio + outputs/
```

- `processing.py`: corrección EXIF, reducción de tamaño, detección de hoja clara, compensación de iluminación, agrupación de componentes, silueta y colores dominantes. Mantiene trazos y silueta separados para no borrar interiores blancos.
- `description.py`: **HuggingFaceTB/SmolVLM2-2.2B-Instruct** interpreta rasgos en CPU. Su salida se valida; se reintenta una vez si el JSON es inválido. Una descripción ambigua utiliza un resumen general y registra una advertencia.
- `generation.py`: **stable-diffusion-v1-5/stable-diffusion-v1-5**, guiado por **lllyasviel/control_v11p_sd15_scribble**. Se usa img2img con la referencia limpia y trazos blancos sobre negro, a 512 × 512. Un prompt breve adaptado al contexto de CLIP expresa el objetivo de la instrucción interna; el prompt efectivo se guarda en metadata.
- `models.py`: descarga explícita de pesos safetensors y archivos necesarios, verificación de snapshots completos y diagnóstico CUDA con un kernel real.
- `pipeline.py`: orquestación independiente de la UI y guardado por etapas. Libera el generador antes de cargar visión; el modelo de visión se libera antes de generar.
- `ui.py`: cuatro vistas, estilos, paleta, progreso y descargas. Cola de una ejecución activa para no competir por VRAM.

La generación nunca descarga modelos automáticamente: usa snapshots y `local_files_only=True`. Telemetría de Hugging Face y Gradio desactivada, fuentes locales y servidor restringido a localhost.

## Estructura

```text
drawToLife/
├── app.py
├── draw_to_life/
│   ├── config.py
│   ├── processing.py
│   ├── description.py
│   ├── generation.py
│   ├── models.py
│   ├── pipeline.py
│   └── ui.py
├── examples/
├── scripts/
│   ├── install.ps1
│   ├── download-models.ps1
│   ├── start.ps1
│   ├── make_examples.py
│   └── process_image.py
├── tests/
├── outputs/
├── .env.example
├── requirements.txt
└── requirements-dev.txt
```

## Outputs

Cada ejecución crea una carpeta `outputs/AAAAMMDD_HHMMSS_id/` con timestamp UTC y sufijo único:

```text
original.jpg              # archivo original sin recomprimir; conserva su extensión
cropped.png               # recorte preprocesado
isolated.png              # dibujo RGBA, papel exterior transparente
generation_reference.png  # referencia centrada y con paleta aplicada
control_scribble.png      # condición estructural para ControlNet
final_character.png       # resultado 2D RGB con fondo blanco
metadata.json
```

Metadata incluye nombre original, timestamp, colores detectados/aplicados, descripción, estilo, modelos, seed, bbox en coordenadas de la imagen original orientada, parámetros, prompts, dispositivo y duración. Una ejecución fallida registra `status: failed` y conserva los intermedios ya guardados. No produce una mascota de sustitución ni muestra el resultado anterior como nuevo.

## Verificación

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app.py draw_to_life scripts tests
.\.venv\Scripts\python.exe -m draw_to_life.models doctor
```

Los tests verifican aislamiento, partes separadas, colores, paletas, inputs inválidos y el contrato de archivos. Los tests de orquestación simulan los modelos caros; **no demuestran calidad generativa**. Para validar esa calidad, procesá los tres dibujos con los modelos reales, revisá silueta, rasgos, frontalidad y limpieza, y repetí una ejecución sin internet después de descargar los modelos.

Una seed ayuda a reproducir el resultado en el mismo entorno; no garantiza igualdad entre CPU/GPU o versiones distintas.

Ver [VALIDATION.md](VALIDATION.md) para resultados generados, tiempos medidos y límites de las verificaciones realizadas en esta copia.

## Límites de la v1

Soporta animales, monstruitos tiernos y criaturas simples. No incluye animación, juego, humanos realistas, reconocimiento perfecto de accesorios ni identidad constante entre generaciones.

La fidelidad depende de los modelos y del dibujo. La vista frontal se solicita al generador, pero una entrada de perfil extremo puede conservar rasgos de perfil. Sombras fuertes, papel muy arrugado, líneas de cuaderno, varios personajes o contornos muy abiertos pueden dificultar el aislamiento. La silueta aproximada queda señalada cuando corresponde.

## Diagnóstico

- **Modelos ausentes/incompletos:** repetir `download-models.ps1` y comprobar que `MODEL_CACHE_DIR` coincide con la ubicación de descarga.
- **CUDA no disponible:** revisar el driver y ejecutar `doctor`. `DEVICE=auto` usa CPU si no hay CUDA; `DEVICE=cuda` exige CUDA en la comprobación de la UI.
- **Instalación de Python desde WSL:** los scripts están destinados a PowerShell nativo en Windows. Si WSL informa `UtilBindVsockAnyPort`, ejecutar la instalación desde Windows evita ese problema de interoperabilidad.
- **Sin espacio en E:** dejar `MODEL_CACHE_DIR` vacío usa C: por defecto. Evitar copiar también los pesos dentro del proyecto.
- **Puerto ocupado:** cambiar `PORT` en `.env`.
- **Dibujo no detectado:** acercar la cámara, encuadrar un solo personaje y mejorar la luz.

## Modelos y licencias

Las dependencias y modelos conservan sus propias licencias. Consultar las fichas oficiales antes de distribuir pesos o publicar un producto:

- [SmolVLM2-2.2B-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct)
- [Stable Diffusion 1.5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5)
- [ControlNet Scribble](https://huggingface.co/lllyasviel/control_v11p_sd15_scribble)
- [Offloading en Diffusers](https://huggingface.co/docs/diffusers/optimization/memory)
