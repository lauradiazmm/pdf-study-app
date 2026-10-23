import re
import unicodedata

from documentos import metadatos_documento

PALABRAS_VACIAS = {'a', 'al', 'como', 'con', 'de', 'del', 'el', 'en',
    'es', 'explica', 'la', 'las', 'lo', 'los', 'me', 'para', 'por', 'que',
    'se', 'sin', 'sobre', 'un', 'una', 'y'}


def obtener_palabras(texto: str) -> set[str]:
    normalizado = unicodedata.normalize('NFD', texto.lower())
    sin_acentos = ''.join(c for c in normalizado if unicodedata.category(c) != 'Mn')
    return set(re.findall(r'[a-z0-9]+', sin_acentos)) - PALABRAS_VACIAS


def buscar_en_documento(consulta: str, documento: dict) -> dict:
    fragmentos = documento['fragmentos']
    terminos = obtener_palabras(consulta)
    coincidencias = []
    for indice, fragmento in enumerate(fragmentos):
        palabras = obtener_palabras(fragmento['texto'])
        puntuacion = sum(any(t == p or (len(t) >= 4 and p.startswith(t))
            for p in palabras) for t in terminos)
        if puntuacion:
            coincidencias.append((puntuacion, indice))
    coincidencias.sort(key=lambda x: (-x[0], x[1]))
    principales = [i for _, i in coincidencias[:2]]
    seleccionados = set(principales)
    for indice in principales:
        for vecino in (indice - 1, indice + 1):
            if 0 <= vecino < len(fragmentos) and fragmentos[vecino]['pagina'] == fragmentos[indice]['pagina']:
                seleccionados.add(vecino)
    return {'consulta': consulta, **metadatos_documento(documento),
        'resultados': [fragmentos[i] for i in sorted(seleccionados)]}
