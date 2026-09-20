import re
from dataclasses import dataclass
from typing import List

from parte_03_linguagem.tipos import ErroIFFARQL


@dataclass
class Token:
    tipo: str
    texto: str
    posicao: int


class AnalisadorLexico:
    def tokenizar(self, comando: str) -> List[Token]:
        tokens: List[Token] = []
        pos = 0
        pares = {'"': '"', "'": "'", "“": "”", "‘": "’"}
        while pos < len(comando):
            caractere = comando[pos]
            if caractere.isspace():
                pos += 1
                continue
            inicio = pos
            if caractere in pares:
                fechamento = pares[caractere]
                pos += 1
                texto = ""
                while pos < len(comando) and comando[pos] != fechamento:
                    if comando[pos] == "\\" and pos + 1 < len(comando) and comando[pos + 1] in {fechamento, "\\"}:
                        pos += 1
                    texto += comando[pos]
                    pos += 1
                if pos == len(comando):
                    raise ErroIFFARQL(f"Aspas nao fechadas na posicao {inicio + 1}.")
                tokens.append(Token("CADEIA", texto, inicio))
                pos += 1
                continue
            numero = re.match(r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", comando[pos:])
            if numero:
                texto = numero.group()
                tipo = "DECIMAL" if any(c in texto for c in ".eE") else "INTEIRO"
                tokens.append(Token(tipo, texto, pos))
                pos += len(texto)
                continue
            nome = re.match(r"[A-Za-z_][A-Za-z_0-9]*", comando[pos:])
            if nome:
                texto = nome.group()
                tokens.append(Token("NOME", texto, pos))
                pos += len(texto)
                continue
            duplo = comando[pos:pos + 2]
            if duplo in {"<=", ">=", "==", "<>"}:
                tokens.append(Token("SIMBOLO", duplo, pos))
                pos += 2
                continue
            if caractere in "()+-*/=<>;":
                tokens.append(Token("SIMBOLO", caractere, pos))
                pos += 1
                continue
            raise ErroIFFARQL(f"Caractere inesperado na posicao {pos + 1}: {caractere!r}.")
        if tokens and tokens[-1].texto == ";" and tokens[-1].tipo == "SIMBOLO":
            tokens.pop()
        tokens.append(Token("FIM", "", len(comando)))
        return tokens
