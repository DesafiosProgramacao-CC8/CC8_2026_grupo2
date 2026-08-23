#Rafael de Camargo 2023010914
#árvore avl usada na indexação e busca dos arquivos

from typing import Any, Dict, Optional, Tuple

from iffagle.texto import normalizar_texto


#representa cada nó da árvore
class NoAVL:
    def __init__(self, chave: str, identificador: str, valor: Any):
        self.chave = chave
        self.valores: Dict[str, Any] = {identificador: valor}
        self.esquerda: Optional["NoAVL"] = None
        self.direita: Optional["NoAVL"] = None
        self.altura = 1


class ArvoreAVL:
    def __init__(self, nome: str):
        self.nome = nome
        self.raiz: Optional[NoAVL] = None
        self.quantidade_nos = 0

    #retorna a altura do nó ou zero quando ele não existe
    def _altura(self, no: Optional[NoAVL]) -> int:
        if no is None:
            return 0
        return no.altura

    #recalcula a altura depois de uma inserção ou rotação
    def _atualizar_altura(self, no: NoAVL) -> None:
        altura_esquerda = self._altura(no.esquerda)
        altura_direita = self._altura(no.direita)
        no.altura = 1 + max(altura_esquerda, altura_direita)

    #calcula a diferença de altura entre os dois lados
    def _fator_balanceamento(self, no: Optional[NoAVL]) -> int:
        if no is None:
            return 0
        return self._altura(no.esquerda) - self._altura(no.direita)

    #faz a rotação simples para a direita
    def _rotacao_direita(self, no: NoAVL) -> NoAVL:
        novo_topo = no.esquerda
        if novo_topo is None:
            return no

        subarvore_central = novo_topo.direita
        novo_topo.direita = no
        no.esquerda = subarvore_central

        self._atualizar_altura(no)
        self._atualizar_altura(novo_topo)
        return novo_topo

    #faz a rotação simples para a esquerda
    def _rotacao_esquerda(self, no: NoAVL) -> NoAVL:
        novo_topo = no.direita
        if novo_topo is None:
            return no

        subarvore_central = novo_topo.esquerda
        novo_topo.esquerda = no
        no.direita = subarvore_central

        self._atualizar_altura(no)
        self._atualizar_altura(novo_topo)
        return novo_topo

    #normaliza a chave e inicia a inserção recursiva
    def inserir(self, chave: str, identificador: str, valor: Any) -> None:
        chave_normalizada = normalizar_texto(chave)
        if not chave_normalizada:
            return

        self.raiz, criou_no = self._inserir(self.raiz, chave_normalizada, identificador, valor)

        if criou_no:
            self.quantidade_nos += 1

    def _inserir(self, no: Optional[NoAVL], chave: str, identificador: str, valor: Any) -> Tuple[NoAVL, bool]:
        if no is None:
            return NoAVL(chave, identificador, valor), True

        criou_no = False

        if chave < no.chave:
            no.esquerda, criou_no = self._inserir(no.esquerda, chave, identificador, valor)
        elif chave > no.chave:
            no.direita, criou_no = self._inserir(no.direita, chave, identificador, valor)
        else:
            #arquivos com a mesma chave ficam guardados no mesmo nó
            no.valores[identificador] = valor
            return no, False

        self._atualizar_altura(no)
        fator = self._fator_balanceamento(no)

        #caso esquerda-esquerda
        if fator > 1 and no.esquerda is not None and chave < no.esquerda.chave:
            return self._rotacao_direita(no), criou_no

        #caso direita-direita
        if fator < -1 and no.direita is not None and chave > no.direita.chave:
            return self._rotacao_esquerda(no), criou_no

        #caso esquerda-direita
        if fator > 1 and no.esquerda is not None and chave > no.esquerda.chave:
            no.esquerda = self._rotacao_esquerda(no.esquerda)
            return self._rotacao_direita(no), criou_no

        #caso direita-esquerda
        if fator < -1 and no.direita is not None and chave < no.direita.chave:
            no.direita = self._rotacao_direita(no.direita)
            return self._rotacao_esquerda(no), criou_no

        return no, criou_no

    #busca uma chave exata aproveitando a ordenação da árvore
    def buscar(self, chave: str) -> Dict[str, Any]:
        chave_normalizada = normalizar_texto(chave)
        atual = self.raiz

        while atual is not None:
            if chave_normalizada == atual.chave:
                return dict(atual.valores)

            if chave_normalizada < atual.chave:
                atual = atual.esquerda
            else:
                atual = atual.direita

        return {}

    #busca um trecho que pode estar em qualquer parte da chave
    def buscar_contendo(self, trecho: str) -> Dict[str, Any]:
        trecho_normalizado = normalizar_texto(trecho)
        encontrados: Dict[str, Any] = {}

        if trecho_normalizado:
            self._buscar_contendo(self.raiz, trecho_normalizado, encontrados)

        return encontrados

    #percorre toda a árvore porque o trecho pode estar no meio da chave
    def _buscar_contendo(self, no: Optional[NoAVL], trecho: str, encontrados: Dict[str, Any]) -> None:
        if no is None:
            return

        self._buscar_contendo(no.esquerda, trecho, encontrados)

        if trecho in no.chave:
            encontrados.update(no.valores)

        self._buscar_contendo(no.direita, trecho, encontrados)

    @property
    def altura(self) -> int:
        return self._altura(self.raiz)
