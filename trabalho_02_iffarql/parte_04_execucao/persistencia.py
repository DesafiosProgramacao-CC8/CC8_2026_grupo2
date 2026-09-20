import json
import os
import tempfile
from pathlib import Path
from typing import Dict

from parte_01_banco.banco import BancoDados
from parte_03_linguagem.tipos import ErroIFFARQL


class Persistencia:
    def para_dados(self, banco: BancoDados) -> Dict:
        tabelas = []
        for tabela in banco.tabelas.values():
            tabelas.append({
                "nome": tabela.nome,
                "colunas": [
                    {"nome": coluna.nome, "tipo": coluna.tipo, "referencia": coluna.referencia}
                    for coluna in tabela.colunas[1:]
                ],
                "proximo_id": tabela.proximo_id,
                "registros": list(tabela.registros.em_ordem()),
            })
        return {"formato": "IFFARQL", "versao": 1, "tabelas": tabelas}

    def salvar(self, banco: BancoDados, arquivo: Path) -> None:
        arquivo = Path(arquivo)
        temporario = None
        try:
            # O arquivo anterior so e substituido depois de escrever a copia inteira.
            descritor, nome = tempfile.mkstemp(prefix=".iffarql_", suffix=".tmp", dir=arquivo.parent)
            temporario = Path(nome)
            with os.fdopen(descritor, "w", encoding="utf-8", newline="\n") as saida:
                json.dump(self.para_dados(banco), saida, ensure_ascii=False, indent=2, allow_nan=False)
                saida.write("\n")
                saida.flush()
                os.fsync(saida.fileno())
            os.replace(temporario, arquivo)
        except (OSError, ValueError, OverflowError) as erro:
            raise ErroIFFARQL(f"Nao foi possivel salvar {arquivo}: {erro}") from erro
        finally:
            if temporario is not None:
                try:
                    temporario.unlink(missing_ok=True)
                except OSError:
                    pass

    def carregar(self, arquivo: Path) -> BancoDados:
        def objeto(pares):
            dados = {}
            for chave, valor in pares:
                if chave in dados:
                    raise ErroIFFARQL(f"Chave JSON repetida: {chave}.")
                dados[chave] = valor
            return dados

        def constante_invalida(valor):
            raise ErroIFFARQL(f"Numero JSON invalido: {valor}.")

        try:
            with Path(arquivo).open("r", encoding="utf-8-sig") as entrada:
                dados = json.load(entrada, object_pairs_hook=objeto, parse_constant=constante_invalida)
            return self.de_dados(dados)
        except ErroIFFARQL:
            raise
        except (OSError, UnicodeError, ValueError, KeyError, TypeError, RecursionError) as erro:
            raise ErroIFFARQL(f"Arquivo de banco invalido ou indisponivel: {erro}") from erro

    def de_dados(self, dados: Dict) -> BancoDados:
        if type(dados) is not dict or set(dados) != {"formato", "versao", "tabelas"}:
            raise ErroIFFARQL("Estrutura de arquivo IFFARQL invalida.")
        if dados["formato"] != "IFFARQL" or type(dados["versao"]) is not int or dados["versao"] != 1:
            raise ErroIFFARQL("Formato ou versao de banco nao suportados.")
        if type(dados["tabelas"]) is not list:
            raise ErroIFFARQL("Lista de tabelas invalida.")
        banco = BancoDados()
        nomes = set()
        for item in dados["tabelas"]:
            if type(item) is not dict or set(item) != {"nome", "colunas", "proximo_id", "registros"}:
                raise ErroIFFARQL("Definicao de tabela invalida.")
            if type(item["nome"]) is not str or item["nome"] in nomes:
                raise ErroIFFARQL("Nome de tabela invalido ou repetido.")
            nomes.add(item["nome"])
            if type(item["colunas"]) is not list or type(item["registros"]) is not list:
                raise ErroIFFARQL("Colunas ou registros invalidos.")
            for coluna in item["colunas"]:
                if type(coluna) is not dict or set(coluna) != {"nome", "tipo", "referencia"}:
                    raise ErroIFFARQL("Definicao de coluna invalida.")
                if type(coluna["nome"]) is not str or type(coluna["tipo"]) is not str or (coluna["referencia"] is not None and type(coluna["referencia"]) is not str):
                    raise ErroIFFARQL("Nome, tipo ou referencia de coluna invalida.")

        # Cria primeiro as tabelas que nao dependem de outras ainda pendentes.
        pendentes = list(dados["tabelas"])
        while pendentes:
            restantes = []
            for item in pendentes:
                if any(coluna["referencia"] is not None and coluna["referencia"] not in banco.tabelas for coluna in item["colunas"]):
                    restantes.append(item)
                    continue
                definicoes = [(c["nome"], c["tipo"], c["referencia"]) for c in item["colunas"]]
                banco.criar_tabela(item["nome"], definicoes)
            if len(restantes) == len(pendentes):
                raise ErroIFFARQL("Referencia inexistente ou ciclo entre tabelas do arquivo.")
            pendentes = restantes

        for item in dados["tabelas"]:
            tabela = banco.obter_tabela(item["nome"])
            tabela.proximo_id = item["proximo_id"]
            for registro in item["registros"]:
                if type(registro) is not dict or "id" not in registro:
                    raise ErroIFFARQL("Registro sem id ou com estrutura invalida.")
                tabela.registros.inserir(registro["id"], dict(registro))
        banco.validar_integridade()
        return banco
