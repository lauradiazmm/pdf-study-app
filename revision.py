"""Revisión humana local de cuestionarios; no utiliza la API."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import streamlit as st

from cuestionario import Cuestionario, validar_cuestionario
from documentos import huella_contexto

BASE = Path(__file__).resolve().parent


def mostrar_revision(documento: dict | None) -> None:
    activo = st.session_state.get("quiz_activo")
    if not activo or not documento or activo["contexto"] != huella_contexto(documento):
        return

    st.caption(
        "Puedes revisar y editar este borrador antes de practicar. "
        "El editor muestra las soluciones: quien revise no realizará "
        "después una prueba independiente con estas mismas preguntas."
    )
    if not st.checkbox(
        "Abrir revisión del cuestionario y sus soluciones",
        key=f"abrir_revision_{activo['id']}",
    ):
        return

    quiz = Cuestionario.model_validate(activo["cuestionario"])
    fragmentos = documento["fragmentos"]
    por_id = {f["fragmento_id"]: f for f in fragmentos}
    opciones_referencia = list(por_id)

    def etiqueta_referencia(identificador):
        fragmento = por_id[identificador]
        return f"Página {fragmento['pagina']} · {identificador}"

    st.info(
        "Comprueba el concepto, las condiciones, las cuatro opciones y "
        "la justificación. Debe existir una única respuesta correcta. "
        "Las comprobaciones automáticas no sustituyen esta revisión."
    )
    with st.expander("Consultar el texto fuente"):
        for fragmento in fragmentos:
            st.caption(etiqueta_referencia(fragmento["fragmento_id"]))
            st.text(fragmento["texto"])

    editadas = []
    with st.form(f"editar_cuestionario_{activo['id']}"):
        for numero, pregunta in enumerate(quiz.preguntas, 1):
            st.markdown(f"**Pregunta {numero}**")
            enunciado = st.text_area(
                "Enunciado", value=pregunta.enunciado,
                key=f"rev_{activo['id']}_{numero}_enunciado",
            )
            opciones = [
                st.text_input(
                    f"Opción {'ABCD'[i]}", value=opcion,
                    key=f"rev_{activo['id']}_{numero}_opcion_{i}",
                )
                for i, opcion in enumerate(pregunta.opciones)
            ]
            correcta = st.selectbox(
                "Solución", options=list(range(4)),
                index=pregunta.correcta,
                format_func=lambda indice: "ABCD"[indice],
                key=f"rev_{activo['id']}_{numero}_correcta",
            )
            justificacion = st.text_area(
                "Justificación", value=pregunta.justificacion,
                key=f"rev_{activo['id']}_{numero}_justificacion",
            )
            referencias = st.multiselect(
                "Fragmentos que respaldan la solución",
                options=opciones_referencia,
                default=[r.fragmento_id for r in pregunta.referencias],
                format_func=etiqueta_referencia,
                key=f"rev_{activo['id']}_{numero}_referencias",
            )
            editadas.append({
                "enunciado": enunciado.strip(),
                "opciones": [opcion.strip() for opcion in opciones],
                "correcta": correcta,
                "justificacion": justificacion.strip(),
                "referencias": [
                    {k: por_id[identificador][k]
                     for k in ("documento_id", "fragmento_id", "pagina")}
                    for identificador in referencias
                ],
            })
        observaciones = st.text_area(
            "Observaciones de la revisión",
            placeholder="Por ejemplo: se ha aclarado el caso par de la mediana.",
        )
        confirmada = st.checkbox(
            "He revisado las cinco preguntas, sus soluciones, "
            "los distractores y su respaldo en los fragmentos."
        )
        guardar = st.form_submit_button("Guardar versión revisada")

    if not guardar:
        return
    if not confirmada:
        st.warning("Completa la revisión y marca la casilla antes de guardarla como revisada.")
        return
    try:
        revisado = Cuestionario.model_validate({"preguntas": editadas})
        validar_cuestionario(revisado, documento)
    except ValueError as error:
        st.warning(f"No se ha guardado la revisión: {error}")
        return

    identificador = uuid4().hex
    original = copy.deepcopy(activo.get("cuestionario_original", activo["cuestionario"]))
    nuevo = {
        **copy.deepcopy(activo),
        "id": identificador,
        "id_origen": activo.get("id_origen", activo["id"]),
        "id_version_anterior": activo["id"],
        "estado_revision": "revisado_por_usuario",
        "fecha_revision_utc": datetime.now(timezone.utc).isoformat(),
        "observaciones_revision": observaciones.strip(),
        "cuestionario_original": original,
        "cuestionario_anterior": copy.deepcopy(activo["cuestionario"]),
        "cuestionario": revisado.model_dump(),
        # Permite recuperar las fuentes aunque el PDF deje de estar en sesión.
        "fragmentos_revision": copy.deepcopy(fragmentos),
    }
    try:
        carpeta = BASE / "data" / "cuestionarios_revisados"
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f"{identificador}.json"
        with ruta.open("x", encoding="utf-8") as archivo:
            json.dump(nuevo, archivo, ensure_ascii=False, indent=2)
    except OSError:
        st.error("No se pudo guardar la versión revisada. Se conserva el cuestionario anterior.")
        return

    st.session_state["quiz_activo"] = nuevo
    st.session_state.pop("quiz_resultado", None)
    st.session_state["aviso_revision_guardada"] = True
    st.rerun()
