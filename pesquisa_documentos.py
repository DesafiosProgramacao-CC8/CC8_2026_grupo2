from typing import Any, Dict, List
from iffagle.texto import normalizar_texto, tokenizar


def buscar_documentos(consulta: str, criterio: str, arquivos, indice_documentos, indice_conteudo) -> List[Dict[str, Any]]:
    consulta_normalizada = normalizar_texto(consulta)
    tokens = tokenizar(consulta)
    candidatos: Dict[str, Dict[str, Any]] = {}

    def obter(id_arquivo: str):
        if id_arquivo not in candidatos:
            candidatos[id_arquivo] = {"score": 0, "motivos": set(), "tokens_encontrados": set()}
        return candidatos[id_arquivo]

    if criterio in {"todos", "nome"}:
        for id_arquivo in indice_documentos.buscar_contendo(consulta_normalizada):
            arquivo = arquivos[id_arquivo]
            c = obter(id_arquivo)
            if arquivo.nome_normalizado == consulta_normalizada:
                c["score"] += 100
            elif arquivo.nome_normalizado.startswith(consulta_normalizada):
                c["score"] += 70
            else:
                c["score"] += 40
            c["motivos"].add("nome")

    if criterio in {"todos", "conteudo"}:
        for token in tokens:
            ocorrencias = indice_conteudo.buscar(token)
            for id_arquivo, frequencia in ocorrencias.items():
                arquivo = arquivos[id_arquivo]
                c = obter(id_arquivo)
                c["score"] += int(frequencia) * 5
                c["tokens_encontrados"].add(token)
                c["motivos"].add("conteúdo")
                palavras_comuns = dict(arquivo.palavras_comuns)
                if token in palavras_comuns:
                    c["score"] += 20 + palavras_comuns[token]
                    c["motivos"].add("palavra frequente")

        for c in candidatos.values():
            if len(c["tokens_encontrados"]) > 1:
                c["score"] += len(c["tokens_encontrados"]) * 10

    return [
        {
            "arquivo": arquivos[id_arquivo],
            "relevancia": int(dados["score"]),
            "motivos": sorted(dados["motivos"]),
            "palavras_comuns": arquivos[id_arquivo].palavras_comuns[:8],
        }
        for id_arquivo, dados in candidatos.items()
    ]
