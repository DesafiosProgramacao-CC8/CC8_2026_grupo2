from copy import deepcopy
from pathlib import Path
from typing import Optional

from parte_01_banco.banco import BancoDados
from parte_01_banco.modelos import Resultado
from parte_03_linguagem.analisador import Analisador
from parte_03_linguagem.tipos import ErroIFFARQL
from parte_04_execucao.comandos import COMANDOS
from parte_04_execucao.persistencia import Persistencia


class MotorIFFARQL:
    def __init__(self, arquivo_temporario: Optional[str] = None):
        self.banco = BancoDados()
        self.persistencia = Persistencia()
        self.arquivo_ativo: Optional[Path] = None
        self.arquivo_temporario = Path(arquivo_temporario or "iffarql_temporario.json").expanduser().resolve()
        self.tabela_ja_criada = False
        self.arquivos_em_execucao = []

    def _caminho(self, nome: str) -> Path:
        caminho = Path(nome).expanduser()
        if not caminho.is_absolute() and self.arquivos_em_execucao:
            caminho = self.arquivos_em_execucao[-1].parent / caminho
        return caminho.resolve()

    def _proteger_script(self, caminho: Path) -> None:
        if caminho in self.arquivos_em_execucao:
            raise ErroIFFARQL("O banco nao pode sobrescrever um TXT que esta sendo executado.")

    def executar(self, texto: str) -> Resultado:
        try:
            instrucao = Analisador().analisar(texto)
            if instrucao.comando == "CARREGARIFFARQL":
                return self.executar_arquivo(self._caminho(instrucao.arquivo))
            if instrucao.comando == "SALVARBD":
                destino = self._caminho(instrucao.arquivo)
                self._proteger_script(destino)
                self.persistencia.salvar(self.banco, destino)
                self.arquivo_ativo = destino
                return Resultado(f"Banco salvo em {destino}.")
            if instrucao.comando == "CARREGARBD":
                if self.tabela_ja_criada or self.banco.tabelas:
                    raise ErroIFFARQL("CARREGARBD exige uma sessao sem nenhuma tabela criada. Reinicie o programa.")
                origem = self._caminho(instrucao.arquivo)
                self._proteger_script(origem)
                novo = self.persistencia.carregar(origem)
                self.banco = novo
                self.arquivo_ativo = origem
                self.tabela_ja_criada = bool(novo.tabelas)
                return Resultado(f"Banco carregado de {origem}.")

            comando = COMANDOS[instrucao.comando]
            if not comando.altera_banco:
                return comando.executar(self.banco, instrucao)

            # A transacao trabalha em uma copia. Erros descartam essa copia.
            candidato = deepcopy(self.banco)
            resultado = comando.executar(candidato, instrucao)
            candidato.validar_integridade()
            destino = self.arquivo_ativo or self.arquivo_temporario
            self._proteger_script(destino)
            self.persistencia.salvar(candidato, destino)
            # Confirma em memoria somente depois de persistir com sucesso.
            self.banco = candidato
            if instrucao.comando == "CRIATABELA":
                self.tabela_ja_criada = True
            return resultado
        except ErroIFFARQL:
            raise
        except (OSError, ValueError, ArithmeticError, RecursionError) as erro:
            raise ErroIFFARQL(f"Nao foi possivel executar o comando: {erro}") from erro

    def executar_arquivo(self, arquivo: Path) -> Resultado:
        if self.tabela_ja_criada or self.banco.tabelas:
            raise ErroIFFARQL("CARREGARIFFARQL exige uma sessao sem nenhuma tabela criada. Reinicie o programa.")
        arquivo = Path(arquivo).resolve()
        if arquivo in self.arquivos_em_execucao or len(self.arquivos_em_execucao) >= 20:
            raise ErroIFFARQL("Carregamento recursivo ou profundidade de arquivos excedida.")
        if arquivo == (self.arquivo_ativo or self.arquivo_temporario):
            raise ErroIFFARQL("Use um TXT de comandos diferente do arquivo de persistencia.")
        try:
            # Le o arquivo antes de executar a primeira linha.
            linhas = arquivo.read_text(encoding="utf-8-sig").splitlines()
        except (OSError, UnicodeError) as erro:
            raise ErroIFFARQL(f"Nao foi possivel ler o TXT: {erro}") from erro
        resultado = Resultado()
        executados = erros = 0
        self.arquivos_em_execucao.append(arquivo)
        try:
            for numero, linha in enumerate(linhas, 1):
                linha = linha.strip()
                if not linha or linha.startswith("#"):
                    continue
                try:
                    interno = self.executar(linha)
                    resultado.detalhes.append((numero, interno))
                    executados += 1
                except ErroIFFARQL as erro:
                    resultado.detalhes.append((numero, str(erro)))
                    erros += 1
        finally:
            self.arquivos_em_execucao.pop()
        resultado.mensagem = f"TXT processado: {executados} comando(s) concluido(s), {erros} erro(s) nesta lista de linhas."
        return resultado
