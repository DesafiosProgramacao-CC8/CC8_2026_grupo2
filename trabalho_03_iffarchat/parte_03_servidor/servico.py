"""Regras do chat. Todos os metodos sao chamados dentro da fila unica."""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from parte_01_protocolo.protocolo import Quadro, ERROS, REQUISICOES
from parte_01_protocolo.seguranca import texto, nascimento, idade
from parte_02_persistencia.repositorio import inserir, atualizar
from parte_02_persistencia.amizades import gerenciar_amizade

# Mensagens gerais pendentes por sessao; as mais antigas sao descartadas.
LIMITE_GERAIS = 500


def _hash_opaco(valor):
    # O servidor nao interpreta o hash: sem normalizar, cadastro e login comparam o mesmo texto.
    if not valor or len(valor) > 200:
        raise ValueError('Hash da senha: informe entre 1 e 200 caracteres.')
    return valor


@dataclass(eq=False)
class Sessao:
    conectada: bool = False
    usuario: int | None = None
    gerais: deque = field(default_factory=lambda: deque(maxlen=LIMITE_GERAIS))
    convites_vistos: set = field(default_factory=set)


class ServicoChat:
    def __init__(self):
        self.online = {}

    def tratar_sem_banco(self, sessao, quadro):
        """CONECTAR e PING so usam o estado da propria conexao: dispensam a fila do banco."""
        if quadro.codigo in (2, 4):
            return self.tratar(None, sessao, quadro)
        return None

    def sair(self, repo, sessao):
        if sessao.usuario is not None and self.online.get(sessao.usuario) is sessao:
            del self.online[sessao.usuario]
        sessao.usuario = None
        sessao.conectada = False
        sessao.gerais.clear()
        sessao.convites_vistos.clear()

    def tratar(self, repo, sessao, quadro):
        codigo, p = quadro.codigo, quadro.parametros
        try:
            if codigo not in REQUISICOES:
                raise ValueError('Este codigo nao e uma requisicao de cliente.')
            if codigo == 2:
                sessao.conectada = True
                return [Quadro(3)]
            if not sessao.conectada:
                raise ValueError('Envie CONECTAR primeiro.')
            if codigo == 4:
                return [Quadro(5)]
            if codigo == 8:
                if sessao.usuario is not None:
                    raise ValueError('Desconecte antes de registrar outro usuario.')
                nome, apelido, data, senha = p
                nome = texto(nome, 'Nome')
                apelido = texto(apelido, 'Apelido', 40)
                nascimento(data)
                senha = _hash_opaco(senha)
                if any(u['apelido'].casefold() == apelido.casefold() for u in repo.todos('Usuario')):
                    raise ValueError('Apelido ja cadastrado.')
                repo.transacao([inserir('Usuario', nome, apelido, data, senha)])
                return [Quadro(9)]
            if codigo == 16:
                if sessao.usuario is not None:
                    raise ValueError('Esta conexao ja esta autenticada.')
                usuario = next((u for u in repo.todos('Usuario')
                                if u['apelido'].casefold() == p[0].casefold()
                                and u['senha'] == p[1]), None)
                if usuario is None:
                    raise ValueError('Apelido ou senha invalida.')
                uid = usuario['id']
                if uid in self.online:
                    raise ValueError('Usuario ja esta online.')
                sessao.usuario = uid
                self.online[uid] = sessao
                return [Quadro(17, (str(uid),))]
            if sessao.usuario is None:
                raise ValueError('Autenticacao necessaria.')
            uid = sessao.usuario
            # VERPERFIL consulta o alvo. Todos os outros IDs iniciais sao o autor.
            if codigo != 8192 and self._id(p[0]) != uid:
                raise ValueError('O ID informado nao pertence a esta sessao.')
            if codigo == 32:
                self.sair(repo, sessao)
                return [Quadro(33)]
            if codigo == 64:
                if p[1] == '0':
                    ids = sorted(self.online)
                elif p[1] == '1':
                    ids = sorted(a['id_usuario_2'] for a in repo.todos('Amizade')
                                 if a['id_usuario_1'] == uid and not a['pendente'])
                else:
                    raise ValueError('Tipo deve ser 0 (ONLINE) ou 1 (AMIGOS).')
                campos = []
                for outro in ids:
                    campos.extend((str(outro), repo.obter('Usuario', outro)['apelido']))
                return [Quadro(65, tuple(campos))]
            if codigo == 128:
                minhas = [a for a in repo.todos('Amizade') if a['id_usuario_1'] == uid]
                convites = [a for a in minhas if a['pendente'] and a['solicitante'] != uid]
                quadros = [Quadro(257, (str(a['solicitante']),))
                           for a in convites if a['id'] not in sessao.convites_vistos]
                comandos = []
                for evento in repo.todos('Evento'):
                    if evento['destinatario'] != uid:
                        continue
                    if not evento['entregue']:
                        quadros.append(Quadro(259, (str(evento['origem']),
                                                   'VERDADEIRO' if evento['aceito'] else 'FALSO')))
                    # Evento entregue (ou herdado de versao anterior) nao tem mais utilidade.
                    comandos.append(f"APAGADADOSDE Evento ONDE id == {int(evento['id'])}")
                if comandos:
                    repo.transacao(comandos)
                sessao.convites_vistos.update(a['id'] for a in convites)
                ids = sorted(a['id_usuario_2'] for a in minhas
                             if a['ha_notificacao'] and not a['silenciado'] and not a['pendente'])
                quadros.append(Quadro(129, tuple(map(str, ids))))
                return quadros
            if codigo in (256, 258, 512):
                return gerenciar_amizade(repo, self, uid, codigo, p)
            if codigo == 2048:
                mensagem = texto(p[2], 'Mensagem', 2000)
                agora = datetime.now().astimezone()
                campos = (str(uid), mensagem, agora.strftime('%d/%m/%Y'),
                          str(agora.hour), str(agora.minute))
                if not p[1]:
                    for destino in self.online.values():
                        destino.gerais.append(campos)
                else:
                    outro = self._outro(repo, uid, p[1])
                    a = repo.amizade(uid, outro, True)
                    b = repo.amizade(outro, uid, True)
                    repo.transacao([inserir('Conversa', a['id'], campos[2], agora.hour,
                                            agora.minute, mensagem),
                                    atualizar('Amizade', b['id'], ha_notificacao=True)])
                return [Quadro(2049)]
            if codigo in (1024, 4096):
                if not p[1]:
                    if codigo == 4096:
                        raise ValueError('Nao existe historico da conversa geral.')
                    campos = tuple(v for m in sessao.gerais for v in m)
                    sessao.gerais.clear()
                    return [Quadro(1025, campos)]
                outro = self._outro(repo, uid, p[1])
                a = repo.amizade(uid, outro, True)
                mensagens = repo.conversa(uid, outro)
                if codigo == 1024:
                    novas = [m for m in mensagens if m['id'] > a['ultimo_lido']]
                    if novas or a['ha_notificacao']:
                        ultimo = max([a['ultimo_lido']] + [m['id'] for m in novas])
                        repo.transacao([atualizar('Amizade', a['id'], ultimo_lido=ultimo,
                                                  ha_notificacao=False)])
                    campos = tuple(v for m in novas for v in
                                   (str(m['remetente']), m['mensagem'], m['data'],
                                    str(m['hora']), str(m['minuto'])))
                    return [Quadro(1025, campos)]
                campos = tuple(v for m in mensagens for v in
                               (str(m['remetente']), m['data'], str(m['hora']),
                                str(m['minuto']), m['mensagem']))
                return [Quadro(4097, campos)]
            if codigo == 8192:
                u = repo.obter('Usuario', self._id(p[0]))
                return [Quadro(8193, (str(u['id']), u['nome_completo'], u['apelido'],
                                     str(idade(u['data_nascimento']))))]
            if codigo == 16384:
                u = repo.obter('Usuario', uid)
                if p[3] != u['senha']:
                    raise ValueError('Senha atual invalida.')
                nome = texto(p[1], 'Nome')
                data = nascimento(p[2])
                repo.transacao([atualizar('Usuario', uid, nome_completo=nome, data_nascimento=data)])
                return [Quadro(16385)]
            raise ValueError('Comando nao implementado.')
        except (ValueError, OverflowError) as erro:
            # Nao exponha caminhos internos, hashes ou texto arbitrario recebido.
            categoria = ERROS.get(codigo, 'ERROCONEXAO')
            mensagem = str(erro).replace('|', '/').replace('\n', ' ').replace('\r', ' ')
            return [Quadro(32768, (categoria, mensagem[:300]))]

    @staticmethod
    def _id(valor):
        if not valor.isascii() or not valor.isdecimal() or int(valor) < 1:
            raise ValueError('ID deve ser inteiro positivo.')
        return int(valor)

    def _outro(self, repo, uid, valor):
        outro = self._id(valor)
        if uid == outro:
            raise ValueError('Escolha outro usuario.')
        repo.obter('Usuario', outro)
        return outro
