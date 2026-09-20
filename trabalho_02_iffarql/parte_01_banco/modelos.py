from dataclasses import dataclass, field
from typing import Dict, List, Optional

from parte_01_banco.avl import ArvoreAVL
from parte_03_linguagem.tipos import obter_tipo


@dataclass
class Coluna:
    nome: str
    tipo: str
    referencia: Optional[str] = None


class Tabela:
    def __init__(self, nome: str, colunas: List[Coluna]):
        self.nome = nome
        self.colunas = [Coluna("id", "INTEIRO")] + colunas
        self.registros = ArvoreAVL(nome)
        self.proximo_id = 1

    def tipos(self) -> Dict:
        return {coluna.nome: obter_tipo(coluna.tipo) for coluna in self.colunas}


@dataclass
class Resultado:
    mensagem: str = ""
    colunas: List[str] = field(default_factory=list)
    registros: List[Dict] = field(default_factory=list)
    tipos: Dict = field(default_factory=dict)
    detalhes: List = field(default_factory=list)
