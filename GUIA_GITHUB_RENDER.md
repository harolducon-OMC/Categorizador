# Actualizar Categorizador en GitHub y Render

Esta carpeta contiene la versión integrada de la aplicación. Incluye la validación adicional con cat-survey (cat-llm) y una configuración de Render que instala BERTopic y los embeddings multilingües. El ZIP de entrega no incluye el entorno virtual ni el archivo local de secretos.

## Consideración de recursos y costos

Render puede ejecutar Streamlit y los modelos de BERTopic; el punto a vigilar es la memoria, no una incompatibilidad de Streamlit. El plan gratuito de Render tiene 512 MB de RAM y no es adecuado para cargar de manera confiable PyTorch, sentence-transformers y el modelo multilingüe. El archivo `render.yaml` solicita `1c-2g` (1 CPU y 2 GB de RAM), un plan pagado. La memoria real necesaria depende del tamaño de la base y del modelo; si el proceso termina por falta de memoria, aumenta el plan. Comprueba los precios actuales antes de crear el servicio.

El primer uso de BERTopic descarga el modelo multilingüe desde Hugging Face y puede tardar. La configuración instalada deja el caché en el filesystem normal de Render, que es efímero: una reconstrucción o reinicio puede implicar volver a descargarlo. El disco persistente de Render es opcional y de pago; no se requiere para que la app funcione.

## 1. Actualizar el repositorio existente desde Git Bash

1. Descarga y descomprime el ZIP actualizado en una carpeta temporal. Conserva una copia de seguridad de `F:\plataforma-insights-render` antes de copiar archivos.
2. Abre Git Bash y sincroniza primero la rama remota. Si tienes cambios locales sin guardar, consérvalos en un commit o una copia antes de continuar:

```bash
cd /f/plataforma-insights-render
git status --short
git fetch origin
git pull --rebase origin main
```

3. Copia los archivos del ZIP sobre la raíz de `F:\plataforma-insights-render`. No reemplaces ni borres la carpeta `.git` ni el archivo local `.streamlit/secrets.toml`; tampoco subas datos de clientes.
4. En Git Bash, revisa y sube solo los archivos de esta actualización:

```bash
git add core/catllm_check.py pages/1_Categorizacion.py requirements-validation.txt README.md GUIA_GITHUB_RENDER.md tests/test_catllm_check.py
git status --short
git commit -m "Integra comparacion cat-survey y amplía la muestra"
git push origin main
```

El repositorio actual es `https://github.com/harolducon-OMC/Categorizador.git`. Si GitHub responde `403 Permission denied`, inicia sesión en Git Bash con la cuenta que tenga permiso de escritura sobre ese repositorio; no compartas tokens ni contraseñas.

`git status --short` sirve para revisar lo que se va a subir. Verifica que NO aparezcan `.streamlit/secrets.toml`, archivos de datos de clientes ni `.venv/`. El `.gitignore` excluye secretos, entornos virtuales, archivos `.xlsx` y bytecode.

Si Git Bash indica que falta configurar identidad, usa tus datos de GitHub:

```bash
git config --global user.name "Tu nombre"
git config --global user.email "tu-correo@example.com"
```

No compartas ni pegues contraseñas o API keys en GitHub. Si una clave real se subió alguna vez, revócala en el proveedor y crea otra; borrarla en un commit posterior no elimina el historial.

## 2. Crear el servicio en Render

1. En Render, elige **New → Blueprint** o conecta el repositorio con **New → Web Service**. La plantilla `render.yaml` configura los comandos de instalación y arranque.
2. Si usas **Blueprint**, selecciona el repositorio y la rama `main`, revisa el servicio `plataforma-insights` y confirma la creación. El plan declarado es `1c-2g`; cámbialo si quieres otro tamaño.
3. En **Environment** del servicio agrega las claves que vayas a utilizar, por ejemplo:

```text
APP_USERNAME=un-usuario-privado
APP_PASSWORD=una-clave-larga-y-unica
GEMINI_API_KEY=...             # si usarás Gemini en la plataforma
ANTHROPIC_API_KEY=...          # si usarás Anthropic o cat-survey con Claude
```

Agrega solo las claves necesarias. `APP_USERNAME` y `APP_PASSWORD` son requeridos por la versión actual de la app. La comparación cat-survey usa Gemini (Google) o Anthropic directos; toma la clave de la misma configuración de la plataforma. OpenAI no está configurado como proveedor en esta versión. No se guardan claves en el repositorio.

4. Despliega. Render instala las dependencias de `requirements-render.txt` y ejecuta Streamlit escuchando en `0.0.0.0` y en el puerto asignado por Render.
5. Cuando termine, abre la URL `onrender.com` que aparece en el servicio. Prueba primero carga de CSV, clasificación regular, exportación y después BERTopic/cat-survey. cat-survey compara una muestra de hasta 200 respuestas únicas; la clasificación principal sigue procesando todas las filas.

## Dependencias opcionales

`requirements-render.txt` instala los paquetes normales, `requirements-extra.txt` (BERTopic y sentence-transformers) y `requirements-validation.txt` (cat-survey). Para ejecutar la app localmente sin los modelos semánticos, basta con `pip install -r requirements.txt`. Cat-survey se puede instalar aparte con `pip install -r requirements-validation.txt`.

La validación cat-survey envía respuestas al proveedor seleccionado y puede generar cargos de API. También está basada en `cat-survey`, cuya licencia indicada por el paquete es GPL-3.0-or-later; revisa las obligaciones de licencia antes de distribuir la aplicación a terceros.

## Si el despliegue falla

En Render abre **Logs → Deploy** y **Logs → Runtime**. Si falla la instalación de `cat-survey`, puedes cambiar temporalmente `buildCommand` en `render.yaml` a `pip install -r requirements.txt -r requirements-extra.txt`, hacer commit y subir el cambio; la aplicación funcionará sin el módulo cat-survey. Si falla al cargar embeddings por falta de memoria, sube el plan de cómputo o desactiva BERTopic y usa «Solo IA» y TF-IDF.
