from typing import Dict
from parte_01_varredura.modelos import ArquivoIndexado
from parte_03_documentos.texto import normalizar_texto, tokenizar

try:
    from PIL import Image, ExifTags
except ImportError:
    Image = None
    ExifTags = None


def criar_imagem_indexada(dados_basicos: Dict, caminho: str) -> ArquivoIndexado:
    largura = altura = None
    formato = dados_basicos["extensao"].replace(".", "").upper()
    modo_cor = ""
    metadados: Dict[str, str] = {
        "nome": dados_basicos["nome"],
        "extensao": dados_basicos["extensao"],
        "tamanho": dados_basicos["tamanho_formatado"],
        "modificado": dados_basicos["modificado_em"],
    }

    if Image is not None:
        try:
            with Image.open(caminho) as imagem:
                largura, altura = imagem.size
                formato = imagem.format or formato
                modo_cor = imagem.mode or ""
                metadados.update({
                    "formato": str(formato),
                    "modo_cor": str(modo_cor),
                    "largura": str(largura),
                    "altura": str(altura),
                    "dimensoes": f"{largura}x{altura}",
                })
                try:
                    exif = imagem.getexif()
                    if exif and ExifTags is not None:
                        for codigo, valor in exif.items():
                            nome_tag = ExifTags.TAGS.get(codigo, str(codigo))
                            valor_texto = str(valor)[:200]
                            metadados[f"exif_{nome_tag}"] = valor_texto
                except Exception:
                    pass
        except Exception:
            pass

    texto_metadados = " ".join(f"{chave} {valor}" for chave, valor in metadados.items())
    return ArquivoIndexado(
        **dados_basicos,
        largura=largura,
        altura=altura,
        formato_imagem=str(formato),
        modo_cor=modo_cor,
        metadados=metadados,
        texto_metadados_normalizado=normalizar_texto(texto_metadados),
    )


def inserir_imagem_nos_indices(imagem, indice_imagens, indice_metadados) -> None:
    indice_imagens.inserir(imagem.nome_normalizado, imagem.id, imagem.id)
    tokens = set(tokenizar(" ".join(f"{k} {v}" for k, v in imagem.metadados.items())))
    if imagem.largura and imagem.altura:
        tokens.add(normalizar_texto(f"{imagem.largura}x{imagem.altura}"))
    for token in tokens:
        indice_metadados.inserir(token, imagem.id, imagem.id)
