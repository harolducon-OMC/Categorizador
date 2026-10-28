# Plataforma de Insights

Categorización de preguntas abiertas (temas y marcas) con IA, dashboards, insights por categoría
y módulo de Awareness (TOM / Espontáneo / Ayudado). Hecha con Streamlit.

## Estructura

```
Home.py                    Carga del Excel/CSV
pages/1_Categorizacion.py  Selección de preguntas abiertas, categorías y clasificación
pages/2_Dashboard.py       Frecuencias, cruces por segmento, insights y reporte Excel
pages/3_Awareness.py       Awareness (lógica del repo HaroldDuconAbril/awareness)
core/                      Lógica (llm, coding, topics, validation, brands, insights, export, awareness, ui, state)
assets/                    Fondo y logo
sample_data/               Archivo de ejemplo para probar
tests/smoke_test.py        Prueba de la lógica sin gastar API
```

## Ejecutar en tu computador

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Mac / Linux:  source .venv/bin/activate
python -m pip install -r requirements.txt

# Secrets locales (copia y edita el archivo; define usuario y contraseña propios)
# Windows:      copy .streamlit\secrets.toml.example .streamlit\secrets.toml
# Mac / Linux:  cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Descomenta y personaliza APP_USERNAME y APP_PASSWORD antes de iniciar la app.

python -m streamlit run Home.py
```

La validación básica con TF-IDF queda disponible con las dependencias principales. Para activar **embeddings multilingües y BERTopic** en un computador local, instala además `python -m pip install -r requirements-extra.txt`. Esta opción añade PyTorch y puede descargar alrededor de 2 GB de dependencias y modelos; se deja fuera de la instalación normal de Streamlit Cloud para evitar problemas de memoria y tiempo de despliegue.

La segunda opinión opcional **cat-survey / cat-llm** se instala con `python -m pip install -r requirements-validation.txt`. El manifiesto de Render (`requirements-render.txt`) ya incluye ese archivo. En esta versión, cat-survey compara una muestra de hasta 200 respuestas únicas; está conectado a Gemini (Google) y Anthropic directos, no a Groq/Cohere/OpenRouter. El paquete declara licencia **GPL-3.0-or-later**: revisa las obligaciones aplicables al proyecto antes de redistribuirlo o publicarlo.

En Windows también puedes ejecutar `Instalar_en_Windows.bat` desde la carpeta del proyecto. Crea/activa `.venv`, instala `requirements.txt` (incluye `openai`) y abre la app con ese mismo Python. Si ya tenías la app abierta, ciérrala y vuelve a iniciarla después de instalar.

Pruebas de lógica (sin API): `python tests/smoke_test.py` y `python tests/test_catllm_check.py`.

## Subir a tu GitHub

1. Crea un repositorio **privado** vacío en GitHub (sin README).
2. En la terminal de VS Code, dentro de la carpeta del proyecto:

```bash
git init
git add .
git commit -m "Plataforma de Insights - versión inicial"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

`.gitignore` ya excluye `secrets.toml` y los `.xlsx` para no subir claves ni datos de clientes.

## Desplegar en Streamlit Community Cloud

1. Entra a https://share.streamlit.io e inicia sesión con GitHub.
2. **Create app** → elige tu repo, rama `main`, archivo principal `Home.py`.
3. **Advanced settings → Secrets**: configura obligatoriamente `APP_USERNAME` y `APP_PASSWORD` con valores privados propios. Agrega también las claves de IA que usarás (`GEMINI_API_KEY`, `GROQ_API_KEY`, `COHERE_API_KEY`, `OPENROUTER_API_KEY` o `ANTHROPIC_API_KEY`). Sin ambas credenciales de acceso, la app no se inicia.
4. **Deploy**.

## Notas para uso en la empresa

- En la barra lateral se elige proveedor y modelo. También se puede ingresar un ID de modelo personalizado si el proveedor lo ofrece.
- Después de categorizar, en la página **Categorización** pulsa **Preparar Excel completo** y luego **Descargar Excel categorizado**. El archivo incluye todas las filas y columnas originales, categorías asignadas, columnas indicadoras y frecuencias. El Dashboard también conserva su descarga de reporte, incluida la hoja de validación si ejecutaste la segunda opinión.
- El tamaño de muestra que aparece al proponer categorías (250 por defecto; ajustable a 500, 750 o 1.000) **solo influye en la propuesta del catálogo**, no en cuántas respuestas se clasifican. Al pulsar **Clasificar respuestas**, `core.coding.classify` procesa todas las filas de la pregunta: agrupa textos idénticos, envía textos únicos en lotes de 30 con hasta cuatro llamadas concurrentes y vuelve a intentar los faltantes en lotes menores. Por ejemplo, 1.000 respuestas únicas requieren aproximadamente 34 solicitudes iniciales, además de posibles reintentos; las respuestas repetidas reducen esa cantidad. El tiempo, la cuota y el costo dependen del proveedor/modelo. Revisa los casos sin clasificar antes de exportar.
- **BERTopic + IA** requiere al menos 60 respuestas distintas. En los resultados puedes abrir **Validación**: la segunda opinión (TF-IDF o embeddings) detecta inconsistencias, pero como aprende de las etiquetas de la IA **no mide exactitud independiente**. Para estimar acuerdo real, descarga la muestra ciega, codifícala manualmente y súbela de nuevo.
- **cat-survey / cat-llm** aparece dentro de la comparación de validación y ejecuta una segunda clasificación independiente en una muestra que eliges (hasta 200 respuestas únicas por ejecución). No sustituye ni cambia el resultado principal; permite medir acuerdo y descargar discrepancias. Cada respuesta puede requerir una o más llamadas al proveedor, por lo que la interfaz pide confirmación y advierte de cuota/cargos. El modo asíncrono por lotes de cat-survey no se activa en Streamlit porque puede tardar minutos u horas y no es apropiado para una petición interactiva.
- Embeddings y BERTopic ejecutan un modelo multilingüe local (`paraphrase-multilingual-MiniLM-L12-v2`); no usan Hugging Face Inference Providers ni consumen sus créditos, aunque la primera ejecución necesita descargar el modelo desde el Hub y usar CPU/memoria.
- Gemini y Groq ofrecen cuotas gratuitas limitadas; OpenRouter ofrece una cuota baja para modelos con sufijo `:free`. Cohere lista Command A+ como modelo sin coste, pero las claves Trial tienen límites y no se deben considerar aptas para uso comercial/producción. Anthropic API es de pago. Los límites y modelos disponibles cambian; revisa los [precios y límites de Gemini](https://ai.google.dev/gemini-api/docs/pricing), [límites de Groq](https://console.groq.com/docs/rate-limits), [cuotas de Cohere](https://docs.cohere.com/docs/rate-limits) y [FAQ de OpenRouter](https://openrouter.ai/docs/faq) antes de procesar un estudio.
- GitHub `public-apis` y PublicAPIs.io son directorios, no servicios de inferencia, así que no aceptan una API key para clasificar respuestas.
- Los textos de las respuestas se envían a la API del LLM para clasificarse: valida la política de datos del cliente.
- La app usa un único usuario y contraseña compartidos, definidos como `APP_USERNAME` y `APP_PASSWORD` en Secrets. No son cuentas individuales; no pongas esas credenciales en el código ni en GitHub. Para una clave distinta por persona, utiliza además las opciones de control de acceso del despliegue.
- El selector de la barra lateral controla el modelo. Los secrets para proveedores son `GEMINI_API_KEY`, `GROQ_API_KEY`, `COHERE_API_KEY`, `OPENROUTER_API_KEY` y `ANTHROPIC_API_KEY`.
- Los porcentajes y las citas de los insights se calculan en código; la IA solo redacta la explicación.

## Siguientes mejoras posibles

- Corrección manual fila por fila de las respuestas clasificadas.
- Guardar y reutilizar codeframes entre estudios.
