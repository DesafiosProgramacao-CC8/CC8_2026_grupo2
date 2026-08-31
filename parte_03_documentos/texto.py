import re
import unicodedata
from typing import Dict, List, Tuple

from parte_02_estruturas.ordenacao import merge_sort


STOPWORDS = {
    "a", "ao", "aos", "aquela", "aquele", "aqueles", "as", "ate",
    "com", "como", "da", "das", "de", "dela", "dele", "deles", "do",
    "dos", "e", "ela", "elas", "ele", "eles", "em", "entre", "era",
    "essa", "esse", "esta", "este", "eu", "foi", "foram", "ha", "isso",
    "isto", "ja", "mais", "mas", "me", "mesmo", "meu", "minha", "muito",
    "na", "nas", "nao", "no", "nos", "o", "os", "ou", "para", "pela",
    "pelas", "pelo", "pelos", "por", "que", "se", "sem", "ser", "seu",
    "sua", "tambem", "tem", "um", "uma", "voce"
}


def normalizar_texto(texto: str) -> str:
    texto = (texto or "").lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(texto.split())


def tokenizar(texto: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", normalizar_texto(texto))


def contar_frequencias(palavras: List[str]) -> Dict[str, int]:
    frequencias: Dict[str, int] = {}
    for palavra in palavras:
        frequencias[palavra] = frequencias.get(palavra, 0) + 1
    return frequencias



def palavras_mais_comuns(frequencias: Dict[str, int], limite: int) -> List[Tuple[str, int]]:
    itens = list(frequencias.items())

    def vem_antes(a: Tuple[str, int], b: Tuple[str, int]) -> bool:
        if a[1] != b[1]:
            return a[1] > b[1]
        return a[0] < b[0]

    return merge_sort(itens, vem_antes)[:limite]
