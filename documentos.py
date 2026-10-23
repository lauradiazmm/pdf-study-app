import hashlib
import json
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


def contar_paginas(contenido: bytes) -> int:
    lector = PdfReader(BytesIO(contenido))
    if lector.is_encrypted:
        raise ValueError('Esta versión no admite PDF cifrados.')
    return len(lector.pages)


def preparar_documento(contenido: bytes, nombre: str, paginas: list[int]) -> dict:
    if len(contenido) > 10 * 1024 * 1024:
        raise ValueError('El PDF supera los 10 MB.')
    lector = PdfReader(BytesIO(contenido))
    if lector.is_encrypted:
        raise ValueError('Esta versión no admite PDF cifrados.')
    paginas = sorted(set(paginas))
    if not paginas or any(type(p) is not int or p < 1 or p > len(lector.pages) for p in paginas):
        raise ValueError('Selecciona al menos una página válida.')
    identificador = 'doc_' + hashlib.sha256(contenido).hexdigest()[:12]
    fragmentos, sin_texto = [], []
    for pagina in paginas:
        palabras = (lector.pages[pagina - 1].extract_text() or '').split()
        if not palabras:
            sin_texto.append(pagina)
            continue
        bloques, bloque = [], ''
        for palabra in palabras:
            if bloque and len(bloque) + len(palabra) + 1 > 1400:
                bloques.append(bloque)
                bloque = ''
            bloque = (bloque + ' ' + palabra).strip()
        if bloque:
            bloques.append(bloque)
        for numero, texto in enumerate(bloques, 1):
            fragmentos.append({'documento_id': identificador,
                'fragmento_id': f'p{pagina:03d}_f{numero:03d}',
                'pagina': pagina, 'texto': texto})
    return {'documento_id': identificador, 'archivo': Path(nombre).name,
        'total_paginas_pdf': len(lector.pages), 'paginas_solicitadas': paginas,
        'paginas_incluidas': sorted({f['pagina'] for f in fragmentos}),
        'paginas_sin_texto': sin_texto, 'metodo_extraccion': 'pypdf_texto',
        'limitaciones': ['Solo se utiliza el texto extraído de las páginas seleccionadas.',
            'No se interpretan imágenes ni se aplica OCR.',
            'Pueden faltar fórmulas, gráficos o partes de tablas y persistir errores de extracción.'],
        'fragmentos': fragmentos}


def metadatos_documento(documento: dict) -> dict:
    incluidos = documento['paginas_incluidas']
    return {k: documento[k] for k in ('documento_id', 'archivo', 'total_paginas_pdf',
        'paginas_solicitadas', 'paginas_incluidas', 'paginas_sin_texto',
        'metodo_extraccion', 'limitaciones')} | {
        'parcial': incluidos != list(range(1, documento['total_paginas_pdf'] + 1)),
        'alcance': 'Texto extraído; no equivale a una revisión visual completa del PDF.'}


def huella_contexto(documento: dict) -> str:
    return hashlib.sha256(json.dumps(documento, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
