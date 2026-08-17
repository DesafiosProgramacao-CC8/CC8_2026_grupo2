import hashlib
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from iffagle.estruturas.avl import ArvoreAVL
from iffagle.modelos import ArquivoIndexado
from iffagle.servicos.documentos import criar_documento_indexado, inserir_documento_nos_indices
from iffagle.servicos.imagens import criar_imagem_indexada, inserir_imagem_nos_indices
from iffagle.servicos.pesquisa_documentos import buscar_documentos
from iffagle.servicos.pesquisa_imagens import buscar_imagens
from iffagle.servicos.scanner import percorrer_diretorio
from iffagle.estruturas.ordenacao import merge_sort
from iffagle.texto import normalizar_texto


class IFFagleIndexador:
    EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png"}
    EXTENSOES_DOCUMENTO = {".txt"}

    def __init__(self):
        self.limpar()

    def limpar(self) -> None:
        self.indice_imagens = ArvoreAVL("Índice de imagens")
        self.indice_documentos = ArvoreAVL("Índice de documentos")
        self.indice_conteudo = ArvoreAVL("Índice de conteúdo dos documentos")
        self.indice_metadados_imagens = ArvoreAVL("Índice de metadados das imagens")
        self.arquivos: Dict[str, ArquivoIndexado] = {}
        self.pasta_indexada: Optional[str] = None
        self.estatisticas = {
            "imagens": 0,
            "documentos": 0,
            "ignorados": 0,
            "erros_permissao": 0,
            "erros_leitura": 0,
        }

    def indexar_pasta(self, pasta: str) -> Dict[str, int]:
        pasta = os.path.abspath(os.path.expanduser(pasta.strip()))
        if not os.path.isdir(pasta):
            raise ValueError("A pasta informada não existe ou não é uma pasta válida.")
        self.limpar()
        self.pasta_indexada = pasta
        percorrer_diretorio(pasta, self._indexar_arquivo, self.estatisticas)
        return dict(self.estatisticas)

    def _indexar_arquivo(self, caminho: str) -> None:
        extensao = os.path.splitext(caminho)[1].lower()
        try:
            if extensao in self.EXTENSOES_DOCUMENTO:
                dados = self._dados_basicos(caminho, "documento")
                documento = criar_documento_indexado(dados, caminho)
                self.arquivos[documento.id] = documento
                inserir_documento_nos_indices(documento, self.indice_documentos, self.indice_conteudo)
                self.estatisticas["documentos"] += 1
            elif extensao in self.EXTENSOES_IMAGEM:
                dados = self._dados_basicos(caminho, "imagem")
                imagem = criar_imagem_indexada(dados, caminho)
                self.arquivos[imagem.id] = imagem
                inserir_imagem_nos_indices(imagem, self.indice_imagens, self.indice_metadados_imagens)
                self.estatisticas["imagens"] += 1
            else:
                self.estatisticas["ignorados"] += 1
        except PermissionError:
            self.estatisticas["erros_permissao"] += 1
        except Exception:
            self.estatisticas["erros_leitura"] += 1

    def _dados_basicos(self, caminho: str, tipo: str) -> Dict[str, Any]:
        stat = os.stat(caminho)
        nome = os.path.basename(caminho)
        id_arquivo = hashlib.sha1(caminho.encode("utf-8", errors="ignore")).hexdigest()
        return {
            "id": id_arquivo,
            "nome": nome,
            "nome_normalizado": normalizar_texto(nome),
            "caminho": os.path.abspath(caminho),
            "extensao": os.path.splitext(nome)[1].lower(),
            "tipo": tipo,
            "tamanho": stat.st_size,
            "tamanho_formatado": self._formatar_tamanho(stat.st_size),
            "modificado_em": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
        }

    @staticmethod
    def _formatar_tamanho(numero_bytes: int) -> str:
        tamanho = float(numero_bytes)
        for unidade in ["B", "KB", "MB", "GB", "TB"]:
            if tamanho < 1024 or unidade == "TB":
                return f"{int(tamanho)} {unidade}" if unidade == "B" else f"{tamanho:.1f} {unidade}"
            tamanho /= 1024
        return f"{numero_bytes} B"

    def buscar(self, consulta: str, tipo: str = "todos", criterio: str = "todos") -> List[Dict[str, Any]]:
        consulta = consulta.strip()
        if not consulta:
            return []
        if tipo not in {"todos", "documentos", "imagens"}:
            tipo = "todos"
        if criterio not in {"todos", "nome", "conteudo", "metadados"}:
            criterio = "todos"

        resultados: List[Dict[str, Any]] = []
        if tipo in {"todos", "documentos"} and criterio in {"todos", "nome", "conteudo"}:
            resultados.extend(buscar_documentos(
                consulta, criterio, self.arquivos, self.indice_documentos, self.indice_conteudo
            ))
        if tipo in {"todos", "imagens"} and criterio in {"todos", "nome", "metadados"}:
            resultados.extend(buscar_imagens(
                consulta, criterio, self.arquivos, self.indice_imagens, self.indice_metadados_imagens
            ))

        def vem_antes(a, b):
            tipo_a = 0 if a["arquivo"].tipo == "documento" else 1
            tipo_b = 0 if b["arquivo"].tipo == "documento" else 1
            if tipo_a != tipo_b:
                return tipo_a < tipo_b
            if a["relevancia"] != b["relevancia"]:
                return a["relevancia"] > b["relevancia"]
            return a["arquivo"].nome_normalizado < b["arquivo"].nome_normalizado

        return merge_sort(resultados, vem_antes)

    def resumo_estruturas(self):
        arvores = [
            self.indice_imagens,
            self.indice_documentos,
            self.indice_conteudo,
            self.indice_metadados_imagens,
        ]
        return [{"nome": a.nome, "nos": a.quantidade_nos, "altura": a.altura} for a in arvores]
