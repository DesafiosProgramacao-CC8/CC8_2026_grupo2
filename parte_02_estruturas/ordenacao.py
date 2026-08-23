#Rafael de Camargo 2023010914
#merge sort usado para ordenar palavras e resultados

from typing import Any, Callable, List


def merge_sort(lista: List[Any], vem_antes: Callable[[Any, Any], bool]) -> List[Any]:
    #uma lista vazia ou com um item já está ordenada
    if len(lista) <= 1:
        return list(lista)

    meio = len(lista) // 2

    #divide a lista e ordena cada metade
    esquerda = merge_sort(lista[:meio], vem_antes)
    direita = merge_sort(lista[meio:], vem_antes)

    resultado: List[Any] = []
    pos_esquerda = 0
    pos_direita = 0

    #compara o primeiro item disponível de cada metade
    while pos_esquerda < len(esquerda) and pos_direita < len(direita):
        item_esquerda = esquerda[pos_esquerda]
        item_direita = direita[pos_direita]

        if vem_antes(item_direita, item_esquerda):
            resultado.append(item_direita)
            pos_direita += 1
        else:
            #em caso de empate mantém primeiro o item da esquerda
            resultado.append(item_esquerda)
            pos_esquerda += 1

    #adiciona os itens que sobraram em uma das metades
    resultado.extend(esquerda[pos_esquerda:])
    resultado.extend(direita[pos_direita:])
    return resultado
