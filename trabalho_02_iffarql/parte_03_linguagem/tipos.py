import math
import operator
import re
import unicodedata
from abc import ABC, abstractmethod
from typing import Any, Dict


COMPARADORES = {
    "<": operator.lt, "<=": operator.le, ">": operator.gt,
    ">=": operator.ge, "==": operator.eq, "<>": operator.ne,
}
DIAS_MESES = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


class ErroIFFARQL(ValueError):
    """Erro de comando, valor ou integridade apresentado no terminal."""


class TipoDado(ABC):
    nome = ""
    operacoes = set()

    @abstractmethod
    def validar(self, valor: Any) -> Any:
        pass

    def resultado(self, operador: str, outro: "TipoDado") -> "TipoDado":
        if operador not in self.operacoes or self.nome != outro.nome:
            raise ErroIFFARQL(f"Operacao invalida: {self.nome} {operador} {outro.nome}.")
        return TIPOS["BOOLEANO"] if operador in COMPARADORES else self

    def operar(self, operador: str, valor: Any, outro: "TipoDado", segundo: Any) -> Any:
        self.resultado(operador, outro)
        if operador in COMPARADORES:
            return COMPARADORES[operador](valor, segundo)
        raise ErroIFFARQL(f"Operador {operador} nao implementado para {self.nome}.")

    def formatar(self, valor: Any) -> str:
        return str(valor)

    def serializar(self, valor: Any) -> Any:
        return valor


class TipoNumerico(TipoDado):
    operacoes = set(COMPARADORES) | {"+", "-", "*", "/"}

    def operar(self, operador: str, valor: Any, outro: TipoDado, segundo: Any) -> Any:
        self.resultado(operador, outro)
        if operador in COMPARADORES:
            return super().operar(operador, valor, outro, segundo)
        if operador == "/" and segundo == 0:
            raise ErroIFFARQL("Divisao por zero.")
        if operador == "/" and self.nome == "INTEIRO":
            # A divisao inteira trunca em direcao a zero, sem converter para float.
            valor_final = abs(valor) // abs(segundo)
            if (valor < 0) != (segundo < 0):
                valor_final = -valor_final
        else:
            funcoes = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv}
            valor_final = funcoes[operador](valor, segundo)
        return self.validar(valor_final)


class TipoInteiro(TipoNumerico):
    nome = "INTEIRO"

    def validar(self, valor: Any) -> int:
        if type(valor) is not int:
            raise ErroIFFARQL("Esperado um valor INTEIRO, sem aspas.")
        return valor


class TipoDecimal(TipoNumerico):
    nome = "DECIMAL"

    def validar(self, valor: Any) -> float:
        if type(valor) is not float or not math.isfinite(valor):
            raise ErroIFFARQL("Esperado um DECIMAL finito com ponto, como 1.80.")
        return valor


class TipoBooleano(TipoDado):
    nome = "BOOLEANO"
    operacoes = {"==", "<>"}

    def validar(self, valor: Any) -> bool:
        if type(valor) is not bool:
            raise ErroIFFARQL("Esperado VERDADEIRO ou FALSO, sem aspas.")
        return valor

    def formatar(self, valor: bool) -> str:
        return "VERDADEIRO" if valor else "FALSO"


class TipoTexto(TipoDado):
    nome = "TEXTO"
    operacoes = set(COMPARADORES) | {"+"}

    def validar(self, valor: Any) -> str:
        if type(valor) is not str:
            raise ErroIFFARQL("Esperado um TEXTO entre aspas.")
        texto = unicodedata.normalize("NFD", valor)
        return "".join(c for c in texto if unicodedata.category(c) != "Mn")

    def operar(self, operador: str, valor: str, outro: TipoDado, segundo: Any) -> Any:
        self.resultado(operador, outro)
        if operador == "+":
            return self.validar(valor + segundo)
        return super().operar(operador, valor, outro, segundo)


class TipoData(TipoDado):
    nome = "DATA"
    operacoes = set(COMPARADORES) | {"+", "-"}

    def validar(self, valor: Any) -> str:
        if type(valor) is not str or not re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", valor):
            raise ErroIFFARQL("DATA deve seguir dd/mm/aaaa entre aspas.")
        dia, mes, ano = (int(parte) for parte in valor.split("/"))
        if not 1 <= ano <= 9999 or not 1 <= mes <= 12 or not 1 <= dia <= DIAS_MESES[mes - 1]:
            raise ErroIFFARQL(f"DATA invalida: {valor}. Fevereiro tem sempre 28 dias.")
        return valor

    def ordinal(self, valor: str) -> int:
        dia, mes, ano = (int(parte) for parte in valor.split("/"))
        return (ano - 1) * 365 + sum(DIAS_MESES[:mes - 1]) + dia - 1

    def de_ordinal(self, numero: int) -> str:
        if not 0 <= numero < 9999 * 365:
            raise ErroIFFARQL("Calculo de DATA ultrapassa os anos 0001 a 9999.")
        ano, restante = divmod(numero, 365)
        mes = 1
        while restante >= DIAS_MESES[mes - 1]:
            restante -= DIAS_MESES[mes - 1]
            mes += 1
        return f"{restante + 1:02d}/{mes:02d}/{ano + 1:04d}"

    def resultado(self, operador: str, outro: TipoDado) -> TipoDado:
        if operador in {"+", "-"} and outro.nome == "INTEIRO":
            return self
        if operador in COMPARADORES and outro.nome == "DATA":
            return TIPOS["BOOLEANO"]
        raise ErroIFFARQL(f"Operacao invalida: DATA {operador} {outro.nome}.")

    def operar(self, operador: str, valor: str, outro: TipoDado, segundo: Any) -> Any:
        self.resultado(operador, outro)
        if operador in COMPARADORES:
            return COMPARADORES[operador](self.ordinal(valor), self.ordinal(segundo))
        dias = segundo if operador == "+" else -segundo
        return self.de_ordinal(self.ordinal(valor) + dias)


TIPOS: Dict[str, TipoDado] = {
    "INTEIRO": TipoInteiro(), "DECIMAL": TipoDecimal(), "BOOLEANO": TipoBooleano(),
    "TEXTO": TipoTexto(), "DATA": TipoData(),
}


def obter_tipo(nome: str) -> TipoDado:
    if nome not in TIPOS:
        raise ErroIFFARQL(f"Tipo desconhecido: {nome}.")
    return TIPOS[nome]
