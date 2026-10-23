import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from documentos import metadatos_documento

CARPETA = Path(__file__).resolve().parent / 'data' / 'registros'


def guardar_consulta(pregunta: str, nivel: str, interes: str, modelo: str,
        respuesta: str, sistema: str, documento: dict | None = None):
    CARPETA.mkdir(parents=True, exist_ok=True)
    identificador = uuid4().hex
    registro = {'id': identificador, 'fecha_utc': datetime.now(timezone.utc).isoformat(),
        'pregunta': pregunta, 'nivel': nivel, 'interes': interes, 'modelo': modelo,
        'sistema': sistema, 'respuesta': respuesta,
        'alcance_documental': metadatos_documento(documento) if documento is not None else None}
    ruta = CARPETA / f'{identificador}.json'
    ruta.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding='utf-8')
    return ruta
