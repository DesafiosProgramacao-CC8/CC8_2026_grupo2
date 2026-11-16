"""Protocolo textual do enunciado. TCP pode fragmentar ou agrupar quadros."""
from dataclasses import dataclass
from enum import IntEnum


class Codigo(IntEnum):
    CONECTAR = 2
    CONECTADO = 3
    PING = 4
    PONG = 5
    REGISTRAR = 8
    REGISTRADO = 9
    AUTENTICAR = 16
    AUTENTICADO = 17
    DESCONECTAR = 32
    DESCONECTADO = 33
    LISTARUSUARIOS = 64
    USUARIOS = 65
    VERIFICARNOTIFICACAO = 128
    NOTIFICACOES = 129
    NOVAAMIZADE = 256
    PEDIDOAMIZADE = 257
    CONEXAOAMIZADE = 258
    RESPOSTAAMIZADE = 259
    ALTERARSILENCIAMENTO = 512
    SILENCIARALTERADO = 513
    PEGARMENSAGENS = 1024
    MENSAGENS = 1025
    ENVIARMENSAGEM = 2048
    MENSAGEMENVIADA = 2049
    PEGARHISTORICOMENSAGENS = 4096
    HISTORICOMENSAGENS = 4097
    VERPERFIL = 8192
    PERFIL = 8193
    ATUALIZARPERFIL = 16384
    PERFILATUALIZADO = 16385
    ERRO = 32768


ARIDADES = {2: 0, 3: 0, 4: 0, 5: 0, 8: 4, 9: 0, 16: 2, 17: 1,
            32: 1, 33: 0, 64: 2, 128: 1, 256: 2, 257: 1, 258: 3,
            259: 2, 512: 2, 513: 0, 1024: 2, 2048: 3, 2049: 0,
            4096: 2, 8192: 1, 8193: 4, 16384: 4, 16385: 0, 32768: 2}
GRUPOS = {65: 2, 129: 1, 1025: 5, 4097: 5}
REQUISICOES = {2, 4, 8, 16, 32, 64, 128, 256, 258, 512, 1024, 2048,
               4096, 8192, 16384}
ERROS = {8: 'ERROREGISTRO', 16: 'ERROAUTENTICACAO', 64: 'ERROLISTARUSUARIOS',
         1024: 'ERROMENSAGENS', 2048: 'ERROENVIARMENSAGEM',
         4096: 'ERROHISTORICOMENSAGENS', 8192: 'ERROVERPERFIL',
         16384: 'ERROATUALIZARPERFIL'}


class ErroProtocolo(ValueError):
    pass


def validar_campo(valor):
    valor = str(valor)
    # CR/LF e controles tambem sao rejeitados para manter o terminal legivel.
    if '|' in valor or any(ord(c) < 32 or ord(c) == 127 for c in valor):
        raise ErroProtocolo('Campo contem separador ou caractere de controle reservado.')
    return valor


@dataclass(frozen=True)
class Quadro:
    codigo: int
    parametros: tuple = ()

    def bytes(self):
        valores = [validar_campo(v) for v in self.parametros]
        _validar(self.codigo, valores)
        return ('|'.join([str(int(self.codigo))] + valores) + '|#\n').encode('utf-8')


def _validar(codigo, parametros):
    if codigo in ARIDADES:
        ok = len(parametros) == ARIDADES[codigo]
    elif codigo in GRUPOS:
        ok = len(parametros) % GRUPOS[codigo] == 0
    else:
        raise ErroProtocolo('Codigo desconhecido.')
    if not ok:
        raise ErroProtocolo('Quantidade de parametros invalida.')


def decodificar(dados):
    try:
        texto = dados.decode('utf-8')
    except UnicodeDecodeError as erro:
        raise ErroProtocolo('UTF-8 invalido.') from erro
    if not texto.endswith('|#\n'):
        raise ErroProtocolo('Terminador invalido; esperado |#\\n.')
    partes = texto[:-3].split('|')
    if not partes[0].isascii() or not partes[0].isdecimal():
        raise ErroProtocolo('Codigo numerico invalido.')
    codigo = int(partes[0])
    campos = tuple(validar_campo(p) for p in partes[1:])
    _validar(codigo, campos)
    return Quadro(codigo, campos)


class LeitorQuadros:
    def __init__(self, limite=4 * 1024 * 1024):
        self.buffer = bytearray()
        self.limite = limite

    def alimentar(self, dados):
        self.buffer.extend(dados)
        quadros = []
        while True:
            fim = self.buffer.find(b'#\n')
            if fim < 0:
                if len(self.buffer) > self.limite:
                    raise ErroProtocolo('Quadro excedeu o limite.')
                return quadros
            if fim + 2 > self.limite:
                raise ErroProtocolo('Quadro excedeu o limite.')
            bruto = bytes(self.buffer[:fim + 2])
            del self.buffer[:fim + 2]
            quadros.append(decodificar(bruto))

    def finalizar(self):
        if self.buffer:
            raise ErroProtocolo('Conexao encerrada com quadro incompleto.')
