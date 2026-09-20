from typing import Dict, List

from parte_01_banco.modelos import Coluna, Tabela
from parte_02_consultas.consultas import Consultas
from parte_03_linguagem.analisador import validar_nome
from parte_03_linguagem.tipos import ErroIFFARQL, obter_tipo


class BancoDados:
    def __init__(self):
        self.tabelas: Dict[str, Tabela] = {}

    def obter_tabela(self, nome: str) -> Tabela:
        if nome not in self.tabelas:
            raise ErroIFFARQL(f"Tabela inexistente: {nome}.")
        return self.tabelas[nome]

    def criar_tabela(self, nome: str, definicoes: List) -> None:
        validar_nome(nome)
        if nome in self.tabelas:
            raise ErroIFFARQL(f"Ja existe uma tabela chamada {nome}.")
        colunas: List[Coluna] = []
        nomes = set()
        for nome_coluna, tipo, referencia in definicoes:
            validar_nome(nome_coluna)
            obter_tipo(tipo)
            if nome_coluna.lower() == "id":
                raise ErroIFFARQL("O campo id e criado automaticamente.")
            if nome_coluna in nomes:
                raise ErroIFFARQL(f"Coluna repetida: {nome_coluna}.")
            if referencia is not None:
                if tipo != "INTEIRO":
                    raise ErroIFFARQL("Chave estrangeira deve ser INTEIRO.")
                self.obter_tabela(referencia)
            nomes.add(nome_coluna)
            colunas.append(Coluna(nome_coluna, tipo, referencia))
        self.tabelas[nome] = Tabela(nome, colunas)

    def apagar_tabela(self, nome: str) -> None:
        tabela = self.obter_tabela(nome)
        if tabela.registros.quantidade_nos:
            raise ErroIFFARQL("Nao e possivel apagar uma tabela com registros.")
        for outra in self.tabelas.values():
            for coluna in outra.colunas:
                if coluna.referencia == nome:
                    raise ErroIFFARQL(f"Tabela referenciada por {outra.nome}.{coluna.nome}. Apague primeiro a tabela dependente.")
        del self.tabelas[nome]

    def inserir(self, nome: str, valores: List) -> int:
        tabela = self.obter_tabela(nome)
        colunas = tabela.colunas[1:]
        if len(valores) != len(colunas):
            raise ErroIFFARQL(f"Esperados {len(colunas)} valores, recebidos {len(valores)}. Nao informe o id.")
        registro = {"id": tabela.proximo_id}
        for coluna, expressao in zip(colunas, valores):
            tipo = obter_tipo(coluna.tipo)
            pronta = expressao.preparar({}, tipo)
            if pronta.tipo.nome != tipo.nome:
                raise ErroIFFARQL(f"Coluna {coluna.nome} exige {tipo.nome}, recebido {pronta.tipo.nome}.")
            registro[coluna.nome] = tipo.validar(pronta.avaliar({}))
        self._validar_registro(tabela, registro)
        tabela.registros.inserir(tabela.proximo_id, registro)
        tabela.proximo_id += 1
        return registro["id"]

    def atualizar(self, nome: str, atualizacoes: List, condicao) -> int:
        tabela = self.obter_tabela(nome)
        tipos = tabela.tipos()
        preparadas = {}
        for coluna, expressao in atualizacoes:
            if coluna == "id":
                raise ErroIFFARQL("O campo id nao pode ser alterado.")
            if coluna not in tipos:
                raise ErroIFFARQL(f"Coluna inexistente: {coluna}.")
            if coluna in preparadas:
                raise ErroIFFARQL(f"Coluna repetida nos blocos COM: {coluna}.")
            pronta = expressao.preparar(tipos, tipos[coluna])
            if pronta.tipo.nome != tipos[coluna].nome:
                raise ErroIFFARQL(f"Resultado incompativel com a coluna {coluna}.")
            preparadas[coluna] = pronta
        registros = Consultas().buscar(tabela, condicao)
        for registro in registros:
            novo = dict(registro)
            # Todos os COM usam os valores originais daquele registro.
            for coluna, pronta in preparadas.items():
                novo[coluna] = tipos[coluna].validar(pronta.avaliar(registro))
            self._validar_registro(tabela, novo)
            tabela.registros.substituir(registro["id"], novo)
        return len(registros)

    def apagar_dados(self, nome: str, condicao) -> int:
        tabela = self.obter_tabela(nome)
        registros = Consultas().buscar(tabela, condicao)
        ids = {registro["id"] for registro in registros}
        for outra in self.tabelas.values():
            for coluna in outra.colunas:
                if coluna.referencia == nome:
                    for registro in outra.registros.em_ordem():
                        if registro[coluna.nome] in ids:
                            raise ErroIFFARQL(f"Registro referenciado por {outra.nome}.{coluna.nome}. Remocao cancelada.")
        for identificador in ids:
            tabela.registros.remover(identificador)
        return len(ids)

    def _validar_registro(self, tabela: Tabela, registro: Dict) -> None:
        if set(registro) != {coluna.nome for coluna in tabela.colunas}:
            raise ErroIFFARQL(f"Campos invalidos no registro de {tabela.nome}.")
        for coluna in tabela.colunas:
            valor = registro[coluna.nome]
            normalizado = obter_tipo(coluna.tipo).validar(valor)
            if normalizado != valor:
                raise ErroIFFARQL("Arquivo contem texto sem normalizacao de acentos.")
            if coluna.nome == "id" and valor < 1:
                raise ErroIFFARQL("Id deve ser positivo.")
            if coluna.referencia is not None:
                destino = self.obter_tabela(coluna.referencia)
                if destino.registros.buscar(valor) is None:
                    raise ErroIFFARQL(f"Chave estrangeira invalida: {coluna.nome} = {valor} nao existe em {destino.nome}.")

    def validar_integridade(self) -> None:
        for tabela in self.tabelas.values():
            maior_id = 0
            for registro in tabela.registros.em_ordem():
                self._validar_registro(tabela, registro)
                maior_id = max(maior_id, registro["id"])
            if type(tabela.proximo_id) is not int or tabela.proximo_id <= maior_id:
                raise ErroIFFARQL(f"Proximo id invalido na tabela {tabela.nome}.")
