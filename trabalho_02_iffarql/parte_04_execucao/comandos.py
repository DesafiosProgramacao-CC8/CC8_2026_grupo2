from abc import ABC, abstractmethod

from parte_01_banco.modelos import Resultado
from parte_02_consultas.consultas import Consultas


class Comando(ABC):
    altera_banco = False

    @abstractmethod
    def executar(self, banco, instrucao) -> Resultado:
        pass


class CriarTabela(Comando):
    altera_banco = True

    def executar(self, banco, instrucao) -> Resultado:
        banco.criar_tabela(instrucao.tabela, instrucao.colunas)
        return Resultado(f"Tabela {instrucao.tabela} criada.")


class ApagarTabela(Comando):
    altera_banco = True

    def executar(self, banco, instrucao) -> Resultado:
        banco.apagar_tabela(instrucao.tabela)
        return Resultado(f"Tabela {instrucao.tabela} apagada.")


class InserirRegistro(Comando):
    altera_banco = True

    def executar(self, banco, instrucao) -> Resultado:
        identificador = banco.inserir(instrucao.tabela, instrucao.valores)
        return Resultado(f"Registro inserido com id {identificador}.")


class AtualizarRegistros(Comando):
    altera_banco = True

    def executar(self, banco, instrucao) -> Resultado:
        quantidade = banco.atualizar(instrucao.tabela, instrucao.atualizacoes, instrucao.condicao)
        return Resultado(f"{quantidade} registro(s) atualizado(s).")


class ApagarRegistros(Comando):
    altera_banco = True

    def executar(self, banco, instrucao) -> Resultado:
        quantidade = banco.apagar_dados(instrucao.tabela, instrucao.condicao)
        return Resultado(f"{quantidade} registro(s) apagado(s).")


class MostrarRegistros(Comando):
    def executar(self, banco, instrucao) -> Resultado:
        colunas, registros, tipos = Consultas().mostrar(banco, instrucao.tabela, instrucao.condicao)
        return Resultado(f"{len(registros)} registro(s) encontrado(s).", colunas, registros, tipos)


COMANDOS = {
    "CRIATABELA": CriarTabela(), "APAGATABELA": ApagarTabela(),
    "INSERIREM": InserirRegistro(), "ATUALIZATABELA": AtualizarRegistros(),
    "APAGADADOSDE": ApagarRegistros(), "MOSTRADADOSDE": MostrarRegistros(),
}
