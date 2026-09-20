from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from parte_03_linguagem.tipos import ErroIFFARQL, TipoDado, TIPOS


@dataclass
class ExpressaoPronta:
    tipo: TipoDado
    avaliar: Callable


class Expressao(ABC):
    @abstractmethod
    def preparar(self, colunas: Dict, esperado: Optional[TipoDado] = None) -> ExpressaoPronta:
        pass

    def dica_tipo(self, colunas: Dict) -> Optional[TipoDado]:
        return None


@dataclass
class Literal(Expressao):
    valor: Any
    tipo: str

    def dica_tipo(self, colunas: Dict) -> Optional[TipoDado]:
        return TIPOS.get(self.tipo)

    def preparar(self, colunas: Dict, esperado: Optional[TipoDado] = None) -> ExpressaoPronta:
        tipo = TIPOS.get(self.tipo)
        if self.tipo == "CADEIA":
            tipo = esperado if esperado is not None and esperado.nome == "DATA" else TIPOS["TEXTO"]
        valor = tipo.validar(self.valor)
        return ExpressaoPronta(tipo, lambda registro: valor)


@dataclass
class Campo(Expressao):
    nome: str

    def dica_tipo(self, colunas: Dict) -> TipoDado:
        if self.nome not in colunas:
            raise ErroIFFARQL(f"Coluna inexistente: {self.nome}.")
        return colunas[self.nome]

    def preparar(self, colunas: Dict, esperado: Optional[TipoDado] = None) -> ExpressaoPronta:
        return ExpressaoPronta(self.dica_tipo(colunas), lambda registro: registro[self.nome])


@dataclass
class Unaria(Expressao):
    operador: str
    expressao: Expressao

    def dica_tipo(self, colunas: Dict) -> Optional[TipoDado]:
        return self.expressao.dica_tipo(colunas)

    def preparar(self, colunas: Dict, esperado: Optional[TipoDado] = None) -> ExpressaoPronta:
        interna = self.expressao.preparar(colunas, esperado)
        if interna.tipo.nome not in {"INTEIRO", "DECIMAL"}:
            raise ErroIFFARQL("Sinal unario so pode ser usado em numeros.")
        sinal = -1 if self.operador == "-" else 1
        return ExpressaoPronta(interna.tipo, lambda registro: interna.tipo.validar(sinal * interna.avaliar(registro)))


@dataclass
class Binaria(Expressao):
    esquerda: Expressao
    operador: str
    direita: Expressao

    def dica_tipo(self, colunas: Dict) -> Optional[TipoDado]:
        return self.esquerda.dica_tipo(colunas)

    def preparar(self, colunas: Dict, esperado: Optional[TipoDado] = None) -> ExpressaoPronta:
        dica = self.esquerda.dica_tipo(colunas) or esperado or self.direita.dica_tipo(colunas)
        esquerda = self.esquerda.preparar(colunas, dica)
        direita = self.direita.preparar(colunas, esquerda.tipo)
        tipo_final = esquerda.tipo.resultado(self.operador, direita.tipo)

        def avaliar(registro):
            return esquerda.tipo.operar(
                self.operador, esquerda.avaliar(registro), direita.tipo, direita.avaliar(registro)
            )

        return ExpressaoPronta(tipo_final, avaliar)


@dataclass
class Condicao:
    esquerda: Expressao
    operador: str
    direita: Expressao

    def preparar(self, colunas: Dict) -> Callable:
        dica = self.esquerda.dica_tipo(colunas) or self.direita.dica_tipo(colunas)
        esquerda = self.esquerda.preparar(colunas, dica)
        direita = self.direita.preparar(colunas, esquerda.tipo)
        esquerda.tipo.resultado(self.operador, direita.tipo)

        def aceita(registro):
            return esquerda.tipo.operar(
                self.operador, esquerda.avaliar(registro), direita.tipo, direita.avaliar(registro)
            )

        return aceita

    def id_exato(self) -> Optional[int]:
        if self.operador == "==":
            for campo, valor in ((self.esquerda, self.direita), (self.direita, self.esquerda)):
                if isinstance(campo, Campo) and campo.nome == "id" and isinstance(valor, Literal) and valor.tipo == "INTEIRO":
                    return valor.valor
        return None
