#usa o banco do trabalho 2 pra guardar os dados do chat
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from vendor.iffarql.parte_04_execucao.motor import MotorIFFARQL
from vendor.iffarql.parte_04_execucao.comandos import COMANDOS
from vendor.iffarql.parte_03_linguagem.analisador import Analisador


def literal(valor):
    if type(valor) is bool:
        return 'VERDADEIRO' if valor else 'FALSO'
    if type(valor) is int:
        return str(valor)
    #aspas e barras do texto precisam chegar inteiras no analisador
    return '"' + str(valor).replace('\\', '\\\\').replace('"', '\\"') + '"'


def inserir(tabela, *valores):
    dados = ' '.join(map(literal, valores))
    return f'INSERIREM {tabela} VALOR ({dados})'


def atualizar(tabela, identificador, **campos):
    blocos = ' COM '.join(f'{k} = {literal(v)}' for k, v in campos.items())
    return f'ATUALIZATABELA {tabela} COM {blocos} ONDE id == {int(identificador)}'


class Repositorio:
    def __init__(self, arquivo):
        self.arquivo = Path(arquivo).resolve()
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        self.motor = MotorIFFARQL(str(self.arquivo))

        #se já tem um banco salvo, carrego ele; senão crio as tabelas do chat
        if self.arquivo.exists():
            self.motor.executar('CARREGARBD ' + literal(str(self.arquivo)))
        else:
            linhas = Path(__file__).with_name('esquema.iffarql').read_text().splitlines()
            comandos = [linha for linha in linhas if linha.strip() and not linha.startswith('#')]
            self.transacao(comandos)

        #se faltar alguma tabela, dá erro ao abrir sem sobrescrever o arquivo
        for tabela in ('Usuario', 'Amizade', 'Conversa', 'Evento'):
            self.todos(tabela)

    def todos(self, tabela):
        return self.motor.executar(f'MOSTRADADOSDE {tabela}').registros

    def obter(self, tabela, identificador):
        registros = self.motor.executar(
            f'MOSTRADADOSDE {tabela} ONDE id == {int(identificador)}').registros
        if not registros:
            raise ValueError(f'{tabela} inexistente.')
        return registros[0]

    def transacao(self, comandos):
        #faço o lote numa cópia pra não deixar uma alteração pela metade
        candidato = deepcopy(self.motor.banco)
        for comando in comandos:
            instrucao = Analisador().analisar(comando)
            COMANDOS[instrucao.comando].executar(candidato, instrucao)
        candidato.validar_integridade()

        #só troco o banco em memória depois de salvar a cópia
        self.motor.persistencia.salvar(candidato, self.arquivo)
        self.motor.banco = candidato
        self.motor.arquivo_ativo = self.arquivo
        self.motor.tabela_ja_criada = True

    def amizade(self, dono, outro, aceita=False):
        for registro in self.todos('Amizade'):
            if registro['id_usuario_1'] == dono and registro['id_usuario_2'] == outro:
                if aceita and (registro['pendente'] or registro['bloqueado']):
                    raise ValueError('A amizade ainda nao foi aceita.')
                return registro
        raise ValueError('Amizade inexistente.')

    def conversa(self, dono, outro):
        ida = self.amizade(dono, outro, True)
        volta = self.amizade(outro, dono, True)

        #junto as mensagens dos dois lados e identifico quem enviou cada uma
        mensagens = []
        for mensagem in self.todos('Conversa'):
            if mensagem['id_amizade'] == ida['id']:
                remetente = dono
            elif mensagem['id_amizade'] == volta['id']:
                remetente = outro
            else:
                continue
            mensagens.append(dict(mensagem, remetente=remetente))

        #se duas mensagens caem no mesmo minuto, o id desempata
        return sorted(
            mensagens,
            key=lambda mensagem: (
                datetime.strptime(mensagem['data'], '%d/%m/%Y'),
                mensagem['hora'], mensagem['minuto'], mensagem['id'],
            ),
        )
