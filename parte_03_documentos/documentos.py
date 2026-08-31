from typing import Dict
from parte_01_varredura.modelos import ArquivoIndexado
from parte_03_documentos.texto import STOPWORDS, contar_frequencias, palavras_mais_comuns, tokenizar


QUANTIDADE_PALAVRAS_COMUNS = 20


def criar_documento_indexado(dados_basicos: Dict, caminho: str) -> ArquivoIndexado:
    with open(caminho, "r", encoding="utf-8", errors="ignore") as arquivo_txt:
        conteudo = arquivo_txt.read()

    palavras = tokenizar(conteudo)
    frequencias = contar_frequencias(palavras)

    frequencias_relevantes = {
        palavra: frequencia
        for palavra, frequencia in frequencias.items()
        if palavra not in STOPWORDS and len(palavra) >= 2
    }

    comuns = palavras_mais_comuns(frequencias_relevantes, QUANTIDADE_PALAVRAS_COMUNS)
    amostra = " ".join(conteudo.split())
    if len(amostra) > 450:
        amostra = amostra[:447] + "..."

    return ArquivoIndexado(
        **dados_basicos,
        frequencias=dict(frequencias),
        palavras_comuns=comuns,
        amostra_texto=amostra,
    )


def inserir_documento_nos_indices(documento, indice_documentos, indice_conteudo) -> None:
    indice_documentos.inserir(documento.nome_normalizado, documento.id, documento.id)
    for palavra, frequencia in documento.frequencias.items():
        indice_conteudo.inserir(palavra, documento.id, frequencia)
