from typing import Any, Dict, List
from parte_03_documentos.texto import normalizar_texto, tokenizar


def buscar_imagens(consulta: str, criterio: str, arquivos, indice_imagens, indice_metadados) -> List[Dict[str, Any]]:
    consulta_normalizada = normalizar_texto(consulta)
    tokens = tokenizar(consulta)
    candidatos: Dict[str, Dict[str, Any]] = {}

    def obter(id_arquivo: str):
        if id_arquivo not in candidatos:
            candidatos[id_arquivo] = {"score": 0, "motivos": set()}
        return candidatos[id_arquivo]

    if criterio in {"todos", "nome"}:
        for id_arquivo in indice_imagens.buscar_contendo(consulta_normalizada):
            arquivo = arquivos[id_arquivo]
            c = obter(id_arquivo)
            if arquivo.nome_normalizado == consulta_normalizada:
                c["score"] += 100
            elif arquivo.nome_normalizado.startswith(consulta_normalizada):
                c["score"] += 70
            else:
                c["score"] += 40
            c["motivos"].add("nome")

    if criterio in {"todos", "metadados"}:
        chaves_busca = set(tokens)
        if "x" in consulta_normalizada:
            chaves_busca.add(consulta_normalizada)

        for chave in chaves_busca:
            for id_arquivo in indice_metadados.buscar(chave):
                c = obter(id_arquivo)
                c["score"] += 20
                c["motivos"].add("metadados")

        if len(consulta_normalizada) > 2:
            for arquivo in arquivos.values():
                if arquivo.tipo == "imagem" and consulta_normalizada in arquivo.texto_metadados_normalizado:
                    c = obter(arquivo.id)
                    c["score"] += 30
                    c["motivos"].add("metadados")

    return [
        {
            "arquivo": arquivos[id_arquivo],
            "relevancia": int(dados["score"]),
            "motivos": sorted(dados["motivos"]),
            "palavras_comuns": [],
        }
        for id_arquivo, dados in candidatos.items()
    ]
