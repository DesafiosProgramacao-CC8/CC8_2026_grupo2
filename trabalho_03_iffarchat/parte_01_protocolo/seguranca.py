"""FNV-1a de 32 bits implementado manualmente, sem bibliotecas de hash."""
import re
import unicodedata
from datetime import datetime, date
from .protocolo import validar_campo


def fnv1a(texto):
    resultado = 2166136261
    for byte in texto.encode('utf-8'):
        resultado ^= byte
        resultado = (resultado * 16777619) & 0xffffffff
    return f'{resultado:08x}'


def codificar_senha(senha):
    if not re.fullmatch(r'[A-Za-z0-9]{6}', senha):
        raise ValueError('A senha deve conter exatamente seis caracteres alfanumericos ASCII.')
    return fnv1a(senha)


def texto(valor, nome, limite=200):
    valor = unicodedata.normalize('NFC', validar_campo(valor)).strip()
    if not valor or len(valor) > limite:
        raise ValueError(f'{nome}: informe entre 1 e {limite} caracteres.')
    return valor


def nascimento(valor):
    if not re.fullmatch(r'[0-9]{2}/[0-9]{2}/[0-9]{4}', valor):
        raise ValueError('Nascimento deve seguir dd/mm/aaaa.')
    data = datetime.strptime(valor, '%d/%m/%Y').date()
    if data > date.today():
        raise ValueError('Nascimento nao pode estar no futuro.')
    return valor


def idade(valor, hoje=None):
    hoje = hoje or date.today()
    data = datetime.strptime(valor, '%d/%m/%Y').date()
    return hoje.year - data.year - ((hoje.month, hoje.day) < (data.month, data.day))
