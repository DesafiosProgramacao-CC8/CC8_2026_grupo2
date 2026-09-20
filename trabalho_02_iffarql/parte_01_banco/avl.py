"""AVL adaptada de parte_02_estruturas/avl.py do Trabalho Integrador I.

Base: CC8_2026_grupo2, commit bcb5450. Mantem as rotacoes e o calculo de
alturas; usa id inteiro e registro completo e acrescenta remocao balanceada.
"""
from typing import Dict, Iterator, Optional, Tuple

from parte_03_linguagem.tipos import ErroIFFARQL


class NoAVL:
    def __init__(self, chave: int, registro: Dict):
        self.chave = chave
        self.registro = registro
        self.esquerda: Optional["NoAVL"] = None
        self.direita: Optional["NoAVL"] = None
        self.altura = 1


class ArvoreAVL:
    def __init__(self, nome: str):
        self.nome = nome
        self.raiz: Optional[NoAVL] = None
        self.quantidade_nos = 0

    def _altura(self, no: Optional[NoAVL]) -> int:
        if no is None:
            return 0
        return no.altura

    def _atualizar_altura(self, no: NoAVL) -> None:
        altura_esquerda = self._altura(no.esquerda)
        altura_direita = self._altura(no.direita)
        no.altura = 1 + max(altura_esquerda, altura_direita)

    def _fator_balanceamento(self, no: Optional[NoAVL]) -> int:
        if no is None:
            return 0
        return self._altura(no.esquerda) - self._altura(no.direita)

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

    def _balancear(self, no: NoAVL) -> NoAVL:
        self._atualizar_altura(no)
        fator = self._fator_balanceamento(no)
        if fator > 1:
            if self._fator_balanceamento(no.esquerda) < 0:
                no.esquerda = self._rotacao_esquerda(no.esquerda)
            return self._rotacao_direita(no)
        if fator < -1:
            if self._fator_balanceamento(no.direita) > 0:
                no.direita = self._rotacao_direita(no.direita)
            return self._rotacao_esquerda(no)
        return no

    def inserir(self, chave: int, registro: Dict) -> None:
        if type(chave) is not int or chave < 1:
            raise ErroIFFARQL("A chave da AVL deve ser um id inteiro positivo.")
        self.raiz = self._inserir(self.raiz, chave, registro)
        self.quantidade_nos += 1

    def _inserir(self, no: Optional[NoAVL], chave: int, registro: Dict) -> NoAVL:
        if no is None:
            return NoAVL(chave, registro)
        if chave < no.chave:
            no.esquerda = self._inserir(no.esquerda, chave, registro)
        elif chave > no.chave:
            no.direita = self._inserir(no.direita, chave, registro)
        else:
            raise ErroIFFARQL(f"Id duplicado: {chave}.")
        return self._balancear(no)

    def buscar(self, chave: int) -> Optional[Dict]:
        atual = self.raiz
        while atual is not None:
            if chave == atual.chave:
                return dict(atual.registro)
            if chave < atual.chave:
                atual = atual.esquerda
            else:
                atual = atual.direita
        return None

    def substituir(self, chave: int, registro: Dict) -> None:
        atual = self.raiz
        while atual is not None:
            if chave == atual.chave:
                atual.registro = registro
                return
            atual = atual.esquerda if chave < atual.chave else atual.direita
        raise ErroIFFARQL(f"Registro inexistente: {chave}.")

    def remover(self, chave: int) -> bool:
        self.raiz, removeu = self._remover(self.raiz, chave)
        if removeu:
            self.quantidade_nos -= 1
        return removeu

    def _remover(self, no: Optional[NoAVL], chave: int) -> Tuple[Optional[NoAVL], bool]:
        if no is None:
            return None, False
        if chave < no.chave:
            no.esquerda, removeu = self._remover(no.esquerda, chave)
        elif chave > no.chave:
            no.direita, removeu = self._remover(no.direita, chave)
        else:
            if no.esquerda is None:
                return no.direita, True
            if no.direita is None:
                return no.esquerda, True
            # O sucessor e o menor elemento da subarvore direita.
            sucessor = no.direita
            while sucessor.esquerda is not None:
                sucessor = sucessor.esquerda
            no.chave, no.registro = sucessor.chave, sucessor.registro
            no.direita, _ = self._remover(no.direita, sucessor.chave)
            removeu = True
        return self._balancear(no), removeu

    def em_ordem(self) -> Iterator[Dict]:
        yield from self._em_ordem(self.raiz)

    def _em_ordem(self, no: Optional[NoAVL]) -> Iterator[Dict]:
        if no is not None:
            yield from self._em_ordem(no.esquerda)
            yield dict(no.registro)
            yield from self._em_ordem(no.direita)

    @property
    def altura(self) -> int:
        return self._altura(self.raiz)
