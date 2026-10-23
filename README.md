# Asistente de estudio con PDF

Prototipo educativo para personas adultas desarrollado en Python y Streamlit.
Genera explicaciones, resúmenes y cuestionarios a partir del texto extraído
de las páginas seleccionadas de un PDF.

## Funciones

- Carga de un PDF de hasta 10 MB y selección de páginas.
- Vista previa del texto extraído.
- Resolución de dudas con búsqueda de fragmentos y referencias.
- Explicaciones adaptadas al nivel Inicial o Intermedio.
- Ejemplos relacionados con Música, Cine o sin interés específico.
- Resúmenes del texto preparado.
- Cuestionarios de cinco preguntas y cuatro opciones.
- Editor para revisar preguntas, soluciones, justificaciones y referencias.
- Corrección local y consulta del historial de intentos.
- Perfil local con nivel e interés.

## Requisitos

- uv instalado.
- Python 3.11. La instalación de desarrollo se comprobó con Python 3.11.5.
- Conexión a internet para instalar dependencias y generar contenido.
- Una clave propia de Gemini API con acceso al modelo configurado.

Modelo configurado en esta versión: `gemini-3.5-flash-lite`.
Su disponibilidad y cuota dependen del proyecto y del proveedor.

## Instalación

Descarga o clona el repositorio y abre una terminal en su carpeta.

Instala las dependencias con las versiones recogidas en `uv.lock`:

```bash
uv sync --locked --python 3.11
```

No es necesario activar manualmente el entorno para utilizar los comandos
`uv run` de esta guía.

## Configurar la clave

Crea un archivo `.env` a partir de `.env.example`.

En macOS o Linux:

```bash
cp .env.example .env
```

En Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Abre `.env` y sustituye el valor de ejemplo por tu clave:

```dotenv
GEMINI_API_KEY=pon_aqui_tu_clave
```

No publiques ni compartas este archivo. Está excluido mediante `.gitignore`.
La clave de la autora no se incluye en la entrega.

## Ejecutar

Desde la carpeta del proyecto:

```bash
uv run --locked streamlit run app.py
```

Abre la dirección `Local URL` que aparezca en la terminal.
El puerto puede variar si hay otras aplicaciones abiertas.

Para detener la aplicación, pulsa `Ctrl + C` en la terminal.

## Recorrido de prueba

Utiliza un PDF digital con texto seleccionable y contenido que tengas
permiso para enviar al proveedor.

1. Carga el PDF y selecciona las páginas.
2. Prepara el documento y comprueba la vista previa del texto.
3. Selecciona nivel e interés.
4. Resuelve una duda sobre una definición presente en esas páginas.
5. Comprueba que la respuesta utiliza referencias del documento activo.
6. Genera un resumen y contrástalo con el texto.
7. Genera un cuestionario, responde y pulsa «Corregir».
8. Comprueba las soluciones y el resultado guardado en el historial.
9. Si utilizas el editor, revisa las preguntas y guarda una nueva versión.

La revisión muestra las soluciones. Una práctica posterior con las mismas
preguntas no es una evaluación independiente de conocimientos.

Cada generación consume cuota. La corrección, la edición y la consulta
del historial se realizan localmente, sin nuevas llamadas al modelo.

## Cómo funciona el agente

En la resolución de dudas, Gemini puede solicitar una búsqueda documental,
examinar los fragmentos recuperados y reformular la consulta.

El código permite como máximo dos búsquedas y tres peticiones lógicas al
modelo. Los reintentos internos de la librería de conexión pueden añadir
intentos de comunicación.

Los resúmenes y cuestionarios siguen un flujo fijo y reciben todos los
fragmentos preparados. No utilizan ese bucle de búsqueda.

## Archivos principales

| Archivo | Responsabilidad |
| --- | --- |
| `app.py` | Interfaz y coordinación de las funciones. |
| `documentos.py` | Extracción, fragmentación y metadatos del PDF. |
| `herramientas.py` | Búsqueda en el documento activo. |
| `agente.py` | Resolución de dudas, herramientas y trazas. |
| `resumen.py` | Generación de resúmenes. |
| `cuestionario.py` | Generación y validación de cuestionarios. |
| `validacion.py` | Comprobación del formato y existencia de referencias. |
| `revision.py` | Edición y conservación de versiones del cuestionario. |
| `perfil.py` | Persistencia del nivel y el interés. |
| `registro.py` | Guardado de consultas. |
| `pyproject.toml` | Configuración y dependencias del proyecto. |
| `uv.lock` | Versiones de dependencias para reproducir la instalación. |

## Datos locales

Durante el uso se crean archivos dentro de `data/` para el perfil,
los registros, las trazas, los intentos y los cuestionarios revisados.
Estos datos están excluidos del repositorio mediante `.gitignore`.

Las trazas pueden contener preguntas y fragmentos del documento.
No deben compartirse sin revisar su contenido.

El PDF preparado permanece en la sesión. Si esta se pierde, debe cargarse
de nuevo. El historial guardado no se incorpora automáticamente al modelo
como memoria del estudiante.

## Límites

- Extrae texto con pypdf; no realiza OCR ni interpreta imágenes o gráficos.
- Las fórmulas guardadas como imágenes pueden quedar fuera del contexto.
- No busca en internet ni consulta varios documentos simultáneamente.
- La búsqueda utiliza palabras y prefijos, no similitud semántica.
- Resúmenes y cuestionarios rechazan contextos serializados superiores
  a 30.000 caracteres, sin recortarlos silenciosamente.
- Se solicitan explicaciones y resúmenes de hasta 180 palabras, pero no
  existe todavía un contador que garantice ese límite.
- Validar una referencia no demuestra que respalde la afirmación.
- Una estructura válida no garantiza preguntas correctas o sin ambigüedad.
- La revisión humana del cuestionario es opcional.
- No hay autenticación ni aislamiento de datos entre usuarios.
- Es un prototipo local, no un servicio público preparado para producción.

## Errores de generación

- **Clave ausente:** comprueba que `.env` esté en la carpeta del proyecto
  y contenga `GEMINI_API_KEY`.
- **429:** revisa el detalle del error; puede indicar un límite de cuota
  o de frecuencia. Evita repetir solicitudes continuamente.
- **503:** el proveedor puede estar temporalmente saturado.
  Espera antes de volver a intentarlo.
- **Referencia inválida:** la aplicación ha rechazado una cita que no
  cumple las reglas de validación.
- **Página sin texto:** puede tratarse de una página escaneada.
  Esta versión no dispone de OCR.

La aplicación no activa facturación ni cambia automáticamente de modelo.
El nivel gratuito está sujeto a las condiciones y cuotas del proveedor;
no se garantiza disponibilidad ilimitada.

## Estado de evaluación

Se han realizado pruebas manuales de desarrollo e integración.
En la copia de entrega se han comprobado la instalación de dependencias,
la apertura de la interfaz y una generación de resumen.

Todavía no hay una batería automatizada conectada a integración continua,
un juez LLM independiente ni un despliegue público.
