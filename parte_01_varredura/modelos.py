from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ArquivoIndexado:
    id: str
    nome: str
    nome_normalizado: str
    caminho: str
    extensao: str
    tipo: str
    tamanho: int
    tamanho_formatado: str
    modificado_em: str

    # Documento
    frequencias: Dict[str, int] = field(default_factory=dict)
    palavras_comuns: List[Tuple[str, int]] = field(default_factory=list)
    amostra_texto: str = ""

    # Imagem
    largura: Optional[int] = None
    altura: Optional[int] = None
    formato_imagem: str = ""
    modo_cor: str = ""
    metadados: Dict[str, str] = field(default_factory=dict)
    texto_metadados_normalizado: str = ""
