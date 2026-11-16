#cada amizade tem um registro pra cada lado
from parte_01_protocolo.protocolo import Codigo, Quadro
from .repositorio import inserir, atualizar


def gerenciar_amizade(repo, servico, id_usuario, codigo, parametros):
    if codigo == Codigo.NOVAAMIZADE:
        outro = servico._outro(repo, id_usuario, parametros[1])
        for amizade in repo.todos('Amizade'):
            if amizade['id_usuario_1'] == id_usuario and amizade['id_usuario_2'] == outro:
                raise ValueError('Amizade ou convite ja existe.')

        #crio os dois lados juntos, bloqueados até alguém aceitar
        comandos = []
        for origem, destino in ((id_usuario, outro), (outro, id_usuario)):
            comandos.append(inserir('Amizade', origem, destino, True, False, False, True, id_usuario, 0))
        repo.transacao(comandos)
        #o destinatário recebe o convite pela consulta de notificações
        return []

    if codigo == Codigo.CONEXAOAMIZADE:
        outro = servico._outro(repo, id_usuario, parametros[1])
        meu_lado = repo.amizade(id_usuario, outro)
        outro_lado = repo.amizade(outro, id_usuario)
        if not meu_lado['pendente'] or meu_lado['solicitante'] == id_usuario:
            raise ValueError('Nao existe convite recebido deste usuario.')
        if parametros[2] not in ('VERDADEIRO', 'FALSO'):
            raise ValueError('Resposta deve ser VERDADEIRO ou FALSO.')
        aceito = parametros[2] == 'VERDADEIRO'

        #aceito ou removo os dois lados e guardo a resposta no mesmo lote
        comandos = []
        for lado in (meu_lado, outro_lado):
            if aceito:
                comando = atualizar('Amizade', lado['id'], bloqueado=False, pendente=False)
            else:
                comando = f"APAGADADOSDE Amizade ONDE id == {lado['id']}"
            comandos.append(comando)
        comandos.append(inserir('Evento', outro, id_usuario, aceito, False))
        repo.transacao(comandos)
        return []

    if codigo == Codigo.ALTERARSILENCIAMENTO:
        outro = servico._outro(repo, id_usuario, parametros[1])
        amizade = repo.amizade(id_usuario, outro, True)
        #mudo só os avisos de quem pediu; as mensagens continuam no histórico
        comando = atualizar('Amizade', amizade['id'], silenciado=not amizade['silenciado'])
        repo.transacao([comando])
        return [Quadro(Codigo.SILENCIARALTERADO)]
