import re
from dataclasses import dataclass, field
from typing import List, Optional

from parte_03_linguagem.expressoes import Binaria, Campo, Condicao, Literal, Unaria
from parte_03_linguagem.lexico import AnalisadorLexico
from parte_03_linguagem.tipos import COMPARADORES, ErroIFFARQL, TIPOS


COMANDOS = {
    "CRIATABELA", "APAGATABELA", "INSERIREM", "ATUALIZATABELA", "APAGADADOSDE",
    "MOSTRADADOSDE", "SALVARBD", "CARREGARBD", "CARREGARIFFARQL",
}
RESERVADAS = COMANDOS | set(TIPOS) | {"COM", "ONDE", "VALOR", "CHAVESTRANGEIRA", "VERDADEIRO", "FALSO", "TRUE", "FALSE", "NULO", "NULL", "SAIR", "AJUDA"}


def validar_nome(nome: str) -> str:
    if not isinstance(nome, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", nome) or nome in RESERVADAS:
        raise ErroIFFARQL(f"Nome invalido ou reservado: {nome!r}.")
    return nome


@dataclass
class Instrucao:
    comando: str
    tabela: str = ""
    colunas: List = field(default_factory=list)
    valores: List = field(default_factory=list)
    atualizacoes: List = field(default_factory=list)
    condicao: Optional[Condicao] = None
    arquivo: str = ""


class Analisador:
    def analisar(self, texto: str) -> Instrucao:
        texto = texto.strip()
        nome_comando = texto.split(maxsplit=1)[0] if texto else ""
        if nome_comando not in COMANDOS:
            raise ErroIFFARQL("Comando desconhecido. Use as palavras reservadas em MAIUSCULAS.")
        if nome_comando in {"SALVARBD", "CARREGARBD", "CARREGARIFFARQL"}:
            partes = texto.split(maxsplit=1)
            if len(partes) != 2:
                raise ErroIFFARQL("Informe o nome do arquivo.")
            caminho = partes[1].strip()
            if caminho.endswith(";"):
                caminho = caminho[:-1].rstrip()
            pares = {'"': '"', "'": "'", "“": "”", "‘": "’"}
            if caminho and caminho[0] in pares:
                if len(caminho) < 2 or caminho[-1] != pares[caminho[0]] or pares[caminho[0]] in caminho[1:-1]:
                    raise ErroIFFARQL("Aspas invalidas no nome do arquivo.")
                caminho = caminho[1:-1]
            elif any(c.isspace() or c in '\"\'“”‘’' for c in caminho):
                raise ErroIFFARQL("Use aspas em caminhos com espacos.")
            if not caminho or any(ord(c) < 32 for c in caminho):
                raise ErroIFFARQL("Nome de arquivo invalido.")
            return Instrucao(nome_comando, arquivo=caminho)

        self.tokens = AnalisadorLexico().tokenizar(texto)
        self.pos = 0
        instrucao = Instrucao(self.consumir().texto)
        instrucao.tabela = self.nome()
        if nome_comando == "CRIATABELA":
            self.exigir("(")
            while not (self.atual().tipo == "SIMBOLO" and self.atual().texto == ")"):
                nome = self.nome()
                token_tipo = self.consumir()
                tipo = token_tipo.texto
                if token_tipo.tipo != "NOME" or tipo not in TIPOS:
                    raise ErroIFFARQL(f"Tipo desconhecido: {tipo}.")
                referencia = None
                if self.aceitar("CHAVESTRANGEIRA"):
                    if tipo != "INTEIRO":
                        raise ErroIFFARQL("CHAVESTRANGEIRA deve ser INTEIRO.")
                    referencia = self.nome()
                instrucao.colunas.append((nome, tipo, referencia))
            self.exigir(")")
        elif nome_comando == "INSERIREM":
            self.exigir("VALOR")
            self.exigir("(")
            while not (self.atual().tipo == "SIMBOLO" and self.atual().texto == ")"):
                instrucao.valores.append(self.literal())
            self.exigir(")")
        elif nome_comando == "ATUALIZATABELA":
            self.exigir("COM")
            while True:
                nome = self.nome()
                self.exigir("=")
                instrucao.atualizacoes.append((nome, self.expressao()))
                if not self.aceitar("COM"):
                    break
            instrucao.condicao = self.condicao()
        elif nome_comando in {"MOSTRADADOSDE", "APAGADADOSDE"}:
            instrucao.condicao = self.condicao()
        if self.atual().tipo != "FIM":
            raise ErroIFFARQL(f"Trecho inesperado: {self.atual().texto!r}. Use um unico comparador no ONDE.")
        return instrucao

    def atual(self):
        return self.tokens[self.pos]

    def consumir(self):
        token = self.atual()
        if token.tipo == "FIM":
            raise ErroIFFARQL("Comando incompleto.")
        self.pos += 1
        return token

    def aceitar(self, texto: str) -> bool:
        if self.atual().texto == texto and self.atual().tipo not in {"CADEIA", "FIM"}:
            self.pos += 1
            return True
        return False

    def exigir(self, texto: str) -> None:
        if not self.aceitar(texto):
            raise ErroIFFARQL(f"Esperado {texto!r} na posicao {self.atual().posicao + 1}.")

    def nome(self) -> str:
        token = self.consumir()
        if token.tipo != "NOME":
            raise ErroIFFARQL("Esperado um nome de tabela ou coluna.")
        return validar_nome(token.texto)

    def literal(self):
        sinal = 1
        tem_sinal = self.atual().tipo == "SIMBOLO" and self.atual().texto in {"+", "-"}
        if tem_sinal:
            sinal = -1 if self.consumir().texto == "-" else 1
        token = self.consumir()
        if token.tipo in {"INTEIRO", "DECIMAL"}:
            conversor = int if token.tipo == "INTEIRO" else float
            try:
                valor = conversor(token.texto) * sinal
            except (ValueError, OverflowError):
                raise ErroIFFARQL("Numero invalido ou excessivamente grande.") from None
            TIPOS[token.tipo].validar(valor)
            return Literal(valor, token.tipo)
        if tem_sinal:
            raise ErroIFFARQL("Sinal so pode acompanhar um numero.")
        if token.tipo == "CADEIA":
            return Literal(token.texto, "CADEIA")
        if token.tipo == "NOME" and token.texto in {"VERDADEIRO", "TRUE", "FALSO", "FALSE"}:
            return Literal(token.texto in {"VERDADEIRO", "TRUE"}, "BOOLEANO")
        raise ErroIFFARQL("Valor invalido. Textos e datas precisam de aspas; valores nulos nao sao permitidos.")

    def primaria(self):
        token = self.atual()
        if self.aceitar("("):
            valor = self.expressao()
            self.exigir(")")
            return valor
        if token.tipo == "SIMBOLO" and token.texto in {"+", "-"}:
            return Unaria(self.consumir().texto, self.primaria())
        if token.tipo == "NOME" and token.texto not in RESERVADAS:
            return Campo(self.nome())
        return self.literal()

    def termo(self):
        esquerda = self.primaria()
        while self.atual().tipo == "SIMBOLO" and self.atual().texto in {"*", "/"}:
            esquerda = Binaria(esquerda, self.consumir().texto, self.primaria())
        return esquerda

    def expressao(self):
        esquerda = self.termo()
        while self.atual().tipo == "SIMBOLO" and self.atual().texto in {"+", "-"}:
            esquerda = Binaria(esquerda, self.consumir().texto, self.termo())
        return esquerda

    def condicao(self) -> Optional[Condicao]:
        if not self.aceitar("ONDE"):
            return None
        esquerda = self.expressao()
        operador = self.consumir()
        if operador.tipo != "SIMBOLO" or operador.texto not in COMPARADORES:
            raise ErroIFFARQL("Comparador invalido. Use <, <=, >, >=, == ou <>.")
        return Condicao(esquerda, operador.texto, self.expressao())
