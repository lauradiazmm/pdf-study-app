import hashlib
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import streamlit as st
from google.genai import errors
from documentos import (
    contar_paginas, preparar_documento, huella_contexto, metadatos_documento,
)
from agente import MODELO, SISTEMA, responder
from resumen import SISTEMA_RESUMEN, generar_resumen
from registro import guardar_consulta
from perfil import cargar_perfil, guardar_perfil, NIVELES, INTERESES
from cuestionario import Cuestionario, SISTEMA_CUESTIONARIO, generar_cuestionario
from revision import mostrar_revision

base = Path(__file__).resolve().parent

st.set_page_config(page_title="Asistente de estudio", page_icon="📚")
st.title("📚 Asistente de estudio")
st.subheader("1. Preparar un PDF")
st.caption("La extracción se hace en este equipo. Al generar una respuesta, se envían a Google el perfil seleccionado, la pregunta y el texto necesario del documento.")
archivo_pdf = st.file_uploader("Selecciona un PDF de hasta 10 MB", type=["pdf"])

def retirar_documento():
    for clave in (
        "documento_preparado", "ultima_respuesta", "ultima_tarea",
        "contexto_respuesta", "quiz_activo", "quiz_resultado",
    ):
        st.session_state.pop(clave, None)

if archivo_pdf is None:
    retirar_documento()
    st.session_state.pop("huella_pdf", None)
else:
    contenido = archivo_pdf.getvalue()
    huella = hashlib.sha256(contenido).hexdigest() + archivo_pdf.name
    if st.session_state.get("huella_pdf") != huella:
        retirar_documento()
        st.session_state["huella_pdf"] = huella
    if len(contenido) > 10 * 1024 * 1024:
        retirar_documento()
        st.warning("Selecciona un PDF de hasta 10 MB.")
    else:
        try:
            total = contar_paginas(contenido)
            if not total:
                raise ValueError("El PDF no contiene páginas.")
            st.write(f"El documento tiene {total} páginas.")
            # Fuera de un formulario: cambiar la selección invalida inmediatamente
            # el contexto anterior, antes de poder volver a generar.
            paginas = st.multiselect("Páginas que quieres preparar",
                options=list(range(1, total + 1)),
                default=list(range(1, min(total, 2) + 1)), key="paginas_" + huella)
            documento_anterior = st.session_state.get("documento_preparado")
            if documento_anterior and documento_anterior["paginas_solicitadas"] != sorted(paginas):
                retirar_documento()
            if st.button("Extraer y activar estas páginas"):
                retirar_documento()
                with st.spinner("Extrayendo texto en este equipo..."):
                    st.session_state["documento_preparado"] = preparar_documento(
                        contenido, archivo_pdf.name, paginas)
        except Exception as error:
            retirar_documento()
            st.error(f"No se ha podido preparar el PDF: {error}")

documento = st.session_state.get("documento_preparado")
listo = bool(documento and documento["fragmentos"])
if documento:
    st.write("Documento activo: " + documento["archivo"])
    st.write("Páginas con texto: " + (", ".join(map(str, documento["paginas_incluidas"])) or "ninguna"))
    if documento["paginas_sin_texto"]:
        st.warning("Sin texto extraíble en las páginas: " + ", ".join(map(str, documento["paginas_sin_texto"])) + ". Esta versión no aplica OCR.")
    st.warning("Se utiliza únicamente el texto extraído. Pueden faltar imágenes, fórmulas o partes de tablas. Revisa la vista previa.")
    with st.expander("Revisar los fragmentos preparados"):
        for fragmento in documento["fragmentos"]:
            st.caption(f"Página {fragmento['pagina']} · {fragmento['fragmento_id']}")
            st.text(fragmento["texto"])
else:
    st.info("Carga un PDF y prepara sus páginas para consultar o resumir.")

st.divider()
st.subheader("2. Estudiar el documento activo")
try:
    perfil_guardado = cargar_perfil()
    if perfil_guardado["nivel"] not in NIVELES or perfil_guardado["interes"] not in INTERESES:
        raise ValueError("Perfil no válido")
except (OSError, ValueError, KeyError, TypeError):
    st.warning("No se pudo recuperar el perfil. Puedes guardarlo de nuevo.")
    perfil_guardado = {"nivel": "Inicial", "interes": "Sin interés específico"}

# Fuera del formulario: el cuestionario recibe el nivel visible actual.
if st.session_state.get("perfil_nivel") not in NIVELES:
    st.session_state["perfil_nivel"] = perfil_guardado["nivel"]
if st.session_state.get("perfil_interes") not in INTERESES:
    st.session_state["perfil_interes"] = perfil_guardado["interes"]

nivel = st.selectbox(
    "Nivel de conocimiento previo", NIVELES, key="perfil_nivel"
)
interes = st.selectbox(
    "Interés para los ejemplos de las dudas", INTERESES, key="perfil_interes"
)
if st.button("Guardar perfil"):
    try:
        guardar_perfil(nivel, interes)
        st.success("Perfil guardado.")
    except (OSError, ValueError):
        st.error("No se ha podido guardar el perfil.")
        traceback.print_exc()

with st.form("consulta"):
    tarea = st.selectbox(
        "¿Qué quieres hacer?",
        ["Resolver una duda", "Resumir las páginas preparadas"],
    )
    pregunta = st.text_area(
        "Escribe tu duda; para el resumen puedes dejarlo vacío", max_chars=1500
    )
    enviar = st.form_submit_button("Generar", disabled=not listo)
if enviar and listo:
    es_resumen = tarea == "Resumir las páginas preparadas"
    if not es_resumen and not pregunta.strip():
        st.warning("Escribe una pregunta antes de continuar.")
    else:
        st.session_state.pop("ultima_respuesta", None)
        try:
            with st.spinner("Preparando la respuesta..."):
                if es_resumen:
                    respuesta = generar_resumen(nivel, documento)
                    sistema = SISTEMA_RESUMEN
                    pregunta_registrada = "Resumen de las páginas preparadas"
                    interes_registrado = "No aplicado al resumen"
                else:
                    peticion = f"Nivel declarado: {nivel}.\nInterés declarado: {interes}.\nPregunta: {pregunta.strip()}"
                    respuesta = responder(peticion, documento)
                    sistema = SISTEMA
                    pregunta_registrada = pregunta.strip()
                    interes_registrado = interes
            st.session_state.update(ultima_respuesta=respuesta, ultima_tarea=tarea,
                contexto_respuesta=huella_contexto(documento))
            try:
                guardar_consulta(pregunta=pregunta_registrada, nivel=nivel,
                    interes=interes_registrado, modelo=MODELO, respuesta=respuesta,
                    sistema=sistema, documento=documento)
                st.success("Resultado guardado.")
            except OSError:
                st.warning("La respuesta se ha generado, pero no se pudo guardar el registro.")
                traceback.print_exc()
        except errors.APIError as error:
            if error.code == 503:
                st.warning("El servicio está temporalmente saturado. Inténtalo más tarde; el cuestionario y el historial siguen disponibles.")
            elif error.code == 429:
                st.warning("Se ha alcanzado un límite de uso. Espera antes de volver a intentarlo.")
            else:
                st.error("El servicio de IA no ha podido completar la petición.")
            traceback.print_exc()
        except ValueError as error:
            st.warning(str(error))
        except Exception:
            st.error("No se pudo completar la operación. Consulta el detalle en la terminal.")
            traceback.print_exc()
if (listo and "ultima_respuesta" in st.session_state
        and st.session_state.get("contexto_respuesta") == huella_contexto(documento)):
    st.subheader(st.session_state["ultima_tarea"])
    st.caption("Fuente: " + documento["archivo"] + ", páginas " + ", ".join(map(str, documento["paginas_incluidas"])))
    st.markdown(st.session_state["ultima_respuesta"])
# Cuestionario del documento activo.
st.divider()
st.header("Practicar con el documento activo")
st.caption(
    "Cuestionario generado automáticamente, con revisión manual disponible. "
    "La validación comprueba estructura y referencias, "
    "pero no garantiza la corrección de todas las preguntas."
)

contexto_actual = (
    huella_contexto(documento) if listo else None
)

# Retira el cuestionario si cambia el documento o sus páginas.
guardado = st.session_state.get("quiz_activo")

if guardado and guardado["contexto"] != contexto_actual:
    st.session_state.pop("quiz_activo", None)
    st.session_state.pop("quiz_resultado", None)

if st.button(
    "Generar cuestionario del documento",
    disabled=not listo,
):
    try:
        with st.spinner("Generando cinco preguntas..."):
            quiz_generado = generar_cuestionario(
                nivel,
                documento,
            )

        identificador = uuid4().hex

        st.session_state["quiz_activo"] = {
            "id": identificador,
            "contexto": contexto_actual,
            "nivel": nivel,
            "modelo": MODELO,
            "documento": metadatos_documento(documento),
            "cuestionario": quiz_generado.model_dump(),
        }
        st.session_state.pop("quiz_resultado", None)

        try:
            guardar_consulta(
                pregunta="Generar cuestionario de cinco preguntas",
                nivel=nivel,
                interes="No aplicado",
                modelo=MODELO,
                respuesta=quiz_generado.model_dump_json(indent=2),
                sistema=SISTEMA_CUESTIONARIO,
                documento=documento,
            )
        except OSError:
            st.warning(
                "El cuestionario está disponible, pero no se pudo "
                "guardar el registro de generación."
            )

    except errors.APIError as error:
        if error.code == 429:
            st.warning(
                "Se ha alcanzado un límite de uso. "
                "Espera antes de volver a intentarlo."
            )
        elif error.code == 503:
            st.warning(
                "El servicio está temporalmente saturado. "
                "Inténtalo más tarde."
            )
        else:
            st.error("No se pudo generar el cuestionario.")
        traceback.print_exc()

    except ValueError as error:
        st.warning(f"No se pudo validar el cuestionario: {error}")

    except Exception:
        st.error(
            "No se pudo completar la generación. "
            "Consulta el detalle en la terminal."
        )
        traceback.print_exc()

mostrar_revision(documento)

if st.session_state.pop("aviso_revision_guardada", False):
    st.success("Versión revisada guardada.")

guardado = st.session_state.get("quiz_activo")

if guardado:
    st.caption(
        "Estado del cuestionario: "
        + guardado.get(
            "estado_revision",
            "generado_sin_revision_humana",
        )
    )

    quiz = Cuestionario.model_validate(
        guardado["cuestionario"]
    )

    fuente = guardado["documento"]
    st.caption(
        f"Fuente: {fuente['archivo']} · "
        "Páginas: "
        + ", ".join(map(str, fuente["paginas_incluidas"]))
        + f" · Nivel al generar: {guardado['nivel']}"
    )

    if guardado["nivel"] != nivel:
        st.info(
            "Este cuestionario conserva el nivel con el que se generó: "
            + guardado["nivel"]
            + ". Cambiar el perfil no modifica sus preguntas."
        )

    terminado = "quiz_resultado" in st.session_state

    with st.form(f"responder_quiz_{guardado['id']}"):
        elecciones = []

        for numero, pregunta_quiz in enumerate(
            quiz.preguntas, start=1
        ):
            eleccion = st.radio(
                f"{numero}. {pregunta_quiz.enunciado}",
                options=range(4),
                format_func=lambda indice, opciones=pregunta_quiz.opciones: (
                    f"{'ABCD'[indice]}. {opciones[indice]}"
                ),
                index=None,
                disabled=terminado,
                key=f"quiz_{guardado['id']}_{numero}",
            )
            elecciones.append(eleccion)

        corregir = st.form_submit_button(
            "Corregir",
            disabled=terminado,
        )

    if corregir:
        if any(eleccion is None for eleccion in elecciones):
            st.warning("Responde las cinco preguntas.")
        else:
            aciertos = sum(
                eleccion == pregunta.correcta
                for eleccion, pregunta in zip(
                    elecciones, quiz.preguntas
                )
            )

            intento = {
                "fecha_utc": datetime.now(timezone.utc).isoformat(),
                "cuestionario_id": guardado["id"],
                "contexto": guardado["contexto"],
                "estado_revision": guardado.get(
                    "estado_revision",
                    "generado_sin_revision_humana",
                ),
                "id_version_anterior": guardado.get("id_version_anterior"),
                "cuestionario_original": guardado.get("cuestionario_original"),
                "modelo": guardado["modelo"],
                "nivel": guardado["nivel"],
                "alcance_documental": fuente,
                "version_cuestionario": guardado["cuestionario"],
                "respuestas": elecciones,
                "aciertos": aciertos,
                "total": len(quiz.preguntas),
                "guardado": False,
            }

            carpeta = base / "data" / "resultados"

            try:
                carpeta.mkdir(parents=True, exist_ok=True)
                ruta = carpeta / f"{uuid4().hex}.json"

                registro_intento = {
                    clave: valor
                    for clave, valor in intento.items()
                    if clave != "guardado"
                }

                ruta.write_text(
                    json.dumps(
                        registro_intento,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                intento["guardado"] = True

            except OSError:
                traceback.print_exc()

            st.session_state["quiz_resultado"] = intento
            st.rerun()

    resultado = st.session_state.get("quiz_resultado")

    if resultado:
        st.success(
            f"Resultado según las soluciones generadas: "
            f"{resultado['aciertos']} de {resultado['total']}."
        )

        for numero, (eleccion, pregunta_quiz) in enumerate(
            zip(resultado["respuestas"], quiz.preguntas),
            start=1,
        ):
            correcta = pregunta_quiz.correcta
            estado = (
                "Correcta" if eleccion == correcta
                else "Incorrecta"
            )

            st.markdown(f"**Pregunta {numero}: {estado}**")
            st.write(
                f"Solución: {'ABCD'[correcta]}. "
                f"{pregunta_quiz.opciones[correcta]}"
            )
            st.write(pregunta_quiz.justificacion)

            paginas = sorted({
                referencia.pagina
                for referencia in pregunta_quiz.referencias
            })

            st.caption(
                f"Fuente: {fuente['archivo']}, página(s) "
                + ", ".join(map(str, paginas))
            )

        if resultado["guardado"]:
            st.caption("Resultado guardado.")
        else:
            st.warning(
                "El resultado está disponible en esta sesión, "
                "pero no se pudo guardar en el equipo."
            )
st.divider()
st.header("Historial de práctica")
st.caption(
    "Intentos guardados en este equipo. Las puntuaciones no determinan "
    "automáticamente tu nivel y pueden corresponder a documentos y "
    "cuestionarios de distinta dificultad."
)

carpeta_resultados = base / "data" / "resultados"
historial = []
archivos_invalidos = 0

for archivo in carpeta_resultados.glob("*.json"):
    try:
        intento = json.loads(archivo.read_text(encoding="utf-8"))
        fecha = datetime.fromisoformat(intento["fecha_utc"])
        aciertos = intento["aciertos"]
        total = intento["total"]
        if (
            fecha.tzinfo is None
            or type(aciertos) is not int
            or type(total) is not int
            or total <= 0
            or not 0 <= aciertos <= total
        ):
            raise ValueError("Resultado no válido.")
        alcance = intento.get("alcance_documental") or {}
        if not isinstance(alcance, dict):
            raise ValueError("Metadatos documentales no válidos.")
        paginas = alcance.get("paginas_incluidas", alcance.get("paginas", []))
        if not isinstance(paginas, list) or any(type(p) is not int or p < 1 for p in paginas):
            raise ValueError("Páginas no válidas.")
        historial.append({
            "fecha": fecha,
            "documento": alcance.get("archivo", "No registrado"),
            "paginas": ", ".join(map(str, paginas)),
            "nivel": intento.get("nivel", "No registrado"),
            "revision": intento.get("estado_revision", "No registrada"),
            "aciertos": aciertos,
            "total": total,
        })
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        archivos_invalidos += 1

if archivos_invalidos:
    st.warning(f"No se pudieron leer {archivos_invalidos} registros.")

if not historial:
    st.info("Todavía no hay resultados de cuestionarios guardados.")
else:
    historial.sort(key=lambda registro: registro["fecha"], reverse=True)
    etiquetas_revision = {
        "generado_sin_revision_humana": "Pendiente de revisión humana",
        "revisado_para_demostracion": "Revisado para demostración",
    }
    filas = [
        {
            "Fecha y hora local": registro["fecha"]
                .astimezone().strftime("%d/%m/%Y %H:%M"),
            "Documento": registro["documento"],
            "Páginas": registro["paginas"],
            "Nivel": registro["nivel"],
            "Revisión": etiquetas_revision.get(
                registro["revision"], registro["revision"]
            ),
            "Aciertos": registro["aciertos"],
            "Preguntas": registro["total"],
        }
        for registro in historial
    ]
    st.dataframe(filas, hide_index=True)
    st.caption(
        "Los registros antiguos pueden carecer de documento, nivel o "
        "estado de revisión. Repetir preguntas puede mejorar la puntuación "
        "por familiaridad; no demuestra por sí solo aprendizaje."
    )
st.divider()
st.subheader("Ver un intento guardado")

archivos_intentos = sorted(
    (base / "data" / "resultados").glob("*.json"),
    key=lambda ruta: ruta.name,
)

intentos_disponibles = {}

for ruta in archivos_intentos:
    try:
        intento = json.loads(
            ruta.read_text(encoding="utf-8")
        )

        fecha = datetime.fromisoformat(intento["fecha_utc"])

        if fecha.tzinfo is None:
            raise ValueError("La fecha no incluye zona horaria.")

        intentos_disponibles[ruta.name] = {
            "fecha": fecha,
            "contenido": intento,
        }

    except (OSError, ValueError, KeyError, TypeError):
        continue

ordenados = sorted(
    intentos_disponibles,
    key=lambda nombre: intentos_disponibles[nombre]["fecha"],
    reverse=True,
)


def etiqueta_intento(nombre):
    registro = intentos_disponibles[nombre]
    intento = registro["contenido"]
    alcance = intento.get("alcance_documental") or {}

    documento_nombre = (
        alcance.get("archivo", "Documento no registrado")
        if isinstance(alcance, dict)
        else "Documento no registrado"
    )

    fecha_texto = (
        registro["fecha"]
        .astimezone()
        .strftime("%d/%m/%Y %H:%M:%S")
    )

    return (
        f"{fecha_texto} · {documento_nombre} · "
        f"{nombre[:8]}"
    )


if not ordenados:
    st.info("No hay intentos disponibles para consultar.")

else:
    elegido = st.selectbox(
        "Selecciona un intento",
        options=ordenados,
        format_func=etiqueta_intento,
        index=None,
        placeholder="Elige un intento guardado",
    )

    if elegido is not None:
        intento = intentos_disponibles[elegido]["contenido"]

        try:
            version = intento["version_cuestionario"]

            # Compatibilidad con los registros del cuestionario antiguo.
            if (
                isinstance(version, dict)
                and "cuestionario" in version
            ):
                version = version["cuestionario"]

            quiz_historico = Cuestionario.model_validate(version)
            respuestas = intento["respuestas"]

            if (
                not isinstance(respuestas, list)
                or len(respuestas) != len(quiz_historico.preguntas)
                or any(
                    type(respuesta) is not int
                    or respuesta not in range(4)
                    for respuesta in respuestas
                )
            ):
                raise ValueError(
                    "Las respuestas guardadas no son válidas."
                )

            aciertos = sum(
                respuesta == pregunta.correcta
                for respuesta, pregunta in zip(
                    respuestas,
                    quiz_historico.preguntas,
                )
            )

            st.write(
                f"Resultado según las soluciones guardadas: "
                f"{aciertos} de {len(quiz_historico.preguntas)}."
            )

            st.caption(
                "Consulta del intento original. "
                "No modifica el documento activo ni genera "
                "una nueva evaluación."
            )

            estado = intento.get(
                "estado_revision", "No registrado"
            )
            st.caption(f"Estado de revisión guardado: {estado}")

            for numero, (respuesta, pregunta) in enumerate(
                zip(respuestas, quiz_historico.preguntas),
                start=1,
            ):
                with st.expander(
                    f"{numero}. {pregunta.enunciado}"
                ):
                    for indice, opcion in enumerate(
                        pregunta.opciones
                    ):
                        st.write(f"{'ABCD'[indice]}. {opcion}")

                    st.write(
                        f"Tu respuesta: {'ABCD'[respuesta]}. "
                        f"{pregunta.opciones[respuesta]}"
                    )

                    correcta = pregunta.correcta

                    st.write(
                        f"Solución guardada: "
                        f"{'ABCD'[correcta]}. "
                        f"{pregunta.opciones[correcta]}"
                    )

                    st.write(pregunta.justificacion)

                    for referencia in pregunta.referencias:
                        st.caption(
                            f"Referencia guardada: "
                            f"{referencia.documento_id}, "
                            f"{referencia.fragmento_id}, "
                            f"página {referencia.pagina}"
                        )

        except (ValueError, KeyError, TypeError):
            st.warning(
                "Este registro no contiene un cuestionario "
                "y unas respuestas completos y válidos."
            )