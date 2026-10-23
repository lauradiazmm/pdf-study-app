import re


class ErrorReferencias(ValueError):
    pass


def validar_referencias(
    texto: str,
    referencias_permitidas: set[tuple[str, str, int]],
) -> None:
    citas = re.findall(
        r"\[[^\]\n]*doc_[^\]\n]*\]",
        texto,
    )

    if not citas:
        raise ErrorReferencias(
            "La respuesta no incluye referencias documentales verificables."
        )

    # Una referencia completa: documento, fragmento y página.
    referencia = (
        r"(doc_[a-zA-Z0-9_]+)\s*,\s*"
        r"(p\d+_f\d+)\s*,\s*p\.\s*(\d+)"
    )

    # Admite una o varias referencias completas en un corchete.
    grupo = re.compile(
        rf"\s*{referencia}"
        rf"(?:\s*[,;]\s*{referencia})*\s*"
    )

    for cita in citas:
        contenido = cita[1:-1]

        if grupo.fullmatch(contenido) is None:
            raise ErrorReferencias(
                f"La respuesta contiene una referencia "
                f"con formato incorrecto: {cita}"
            )

        for coincidencia in re.finditer(referencia, contenido):
            documento_id, fragmento_id, pagina = (
                coincidencia.groups()
            )

            identificador = (
                documento_id,
                fragmento_id,
                int(pagina),
            )

            if identificador not in referencias_permitidas:
                raise ErrorReferencias(
                    "La respuesta cita un fragmento o una página "
                    "que no coincide con la evidencia enviada: "
                    f"{coincidencia.group()}"
                )