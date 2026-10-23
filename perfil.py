import json
from pathlib import Path

RUTA_PERFIL = (
    Path(__file__).resolve().parent / "data" / "perfil.json"
)

NIVELES = ["Inicial", "Intermedio"]
INTERESES = ["Sin interés específico", "Música", "Cine"]


def cargar_perfil():
    predeterminado = {
        "nivel": "Inicial",
        "interes": "Sin interés específico",
    }

    if not RUTA_PERFIL.exists():
        return predeterminado

    perfil = json.loads(
        RUTA_PERFIL.read_text(encoding="utf-8")
    )

    if perfil.get("nivel") not in NIVELES:
        raise ValueError("El nivel guardado no es válido.")

    if perfil.get("interes") not in INTERESES:
        raise ValueError("El interés guardado no es válido.")

    return {
        "nivel": perfil["nivel"],
        "interes": perfil["interes"],
    }


def guardar_perfil(nivel, interes):
    if nivel not in NIVELES or interes not in INTERESES:
        raise ValueError("Perfil no válido.")

    RUTA_PERFIL.parent.mkdir(parents=True, exist_ok=True)

    RUTA_PERFIL.write_text(
        json.dumps(
            {"nivel": nivel, "interes": interes},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )