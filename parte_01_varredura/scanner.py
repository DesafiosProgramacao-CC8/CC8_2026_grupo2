import os
from typing import Callable, Dict


def percorrer_diretorio(pasta: str, ao_encontrar_arquivo: Callable[[str], None], estatisticas: Dict[str, int]) -> None:
    """Percorre pasta/subpastas. Itens sem permissão são ignorados."""
    try:
        with os.scandir(pasta) as itens:
            for item in itens:
                try:
                    if item.is_dir(follow_symlinks=False):
                        percorrer_diretorio(item.path, ao_encontrar_arquivo, estatisticas)
                    elif item.is_file(follow_symlinks=False):
                        ao_encontrar_arquivo(item.path)
                except PermissionError:
                    estatisticas["erros_permissao"] += 1
                except (OSError, UnicodeError):
                    estatisticas["erros_leitura"] += 1
                except Exception:
                    estatisticas["erros_leitura"] += 1
    except PermissionError:
        estatisticas["erros_permissao"] += 1
    except OSError:
        estatisticas["erros_leitura"] += 1
