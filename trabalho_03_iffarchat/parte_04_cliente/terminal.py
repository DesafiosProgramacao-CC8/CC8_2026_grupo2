"""Interface de terminal, sem dependencias externas ou GUI obrigatoria."""
import argparse
import getpass
from queue import Empty
from threading import Thread, Event
from .cliente import ClienteChat, ErroServidor

AJUDA = '''
IFFARCHAT - comandos
  /registrar              Cadastro guiado (senha de 6 letras/digitos)
  /login                  Login guiado
  /online                 Listar usuarios online e seus IDs
  /amigos                 Listar amigos aceitos
  /convidar ID            Solicitar amizade
  /aceitar ID             Aceitar convite recebido
  /recusar ID             Recusar convite recebido
  /silenciar ID           Alternar notificacoes deste amigo
  /abrir ID               Acompanhar conversa privada (polling)
  /geral                  Voltar a acompanhar a conversa geral
  /privado ID mensagem    Enviar mensagem privada sem mudar a conversa
  /historico ID           Consultar historico privado completo
  /perfil ID              Consultar dados publicos
  /atualizar              Alterar nome/nascimento com a senha atual
  /conectar               Reconectar ao mesmo servidor
  /sair                   Fazer logoff e sair
  /ajuda                  Mostrar comandos
Texto sem / envia para a conversa aberta (geral ou privada).
'''


def apresentar(quadro):
    if isinstance(quadro, tuple):
        return f'[DESCONECTADO] {quadro[1]} Use /conectar.'
    c, p = quadro.codigo, quadro.parametros
    if c == 257:
        return f'[CONVITE] Usuario {p[0]} quer ser seu amigo: /aceitar {p[0]} ou /recusar {p[0]}'
    if c == 259:
        return f'[AMIZADE] Usuario {p[0]}: ' + ('aceitou' if p[1] == 'VERDADEIRO' else 'recusou')
    if c == 129:
        return '[NOTIFICACOES] Mensagens dos usuarios: ' + (', '.join(p) or 'nenhum')
    if c in (1025, 4097):
        linhas = []
        for i in range(0, len(p), 5):
            if c == 1025:
                uid, mensagem, data, hora, minuto = p[i:i+5]
            else:
                uid, data, hora, minuto, mensagem = p[i:i+5]
            linhas.append(f'[{data} {int(hora):02d}:{int(minuto):02d}] Usuario {uid}: {mensagem}')
        return '\n'.join(linhas) or '(sem mensagens)'
    if c == 65:
        return '\n'.join(f'{p[i]} - {p[i+1]}' for i in range(0, len(p), 2)) or '(lista vazia)'
    if c == 8193:
        return f'ID {p[0]} | Nome: {p[1]} | Apelido: {p[2]} | Idade: {p[3]}'
    if c == 32768:
        return f'[ERRO] {p[0]}: {p[1]}'
    return {9: 'Cadastro realizado.', 513: 'Silenciamento alternado.',
            16385: 'Perfil atualizado.', 2049: 'Mensagem enviada.'}.get(c, str(c))


def executar_comando(cliente, linha, host, porta):
    """Separado da leitura do terminal para permitir testes da interface real."""
    comando, _, resto = linha.partition(' ')
    resto = resto.strip()
    if comando == '/ajuda':
        return AJUDA
    if comando == '/conectar':
        cliente.conectar(host, porta)
        return 'Conectado. Use /login ou /registrar.'
    if comando == '/registrar':
        q = cliente.registrar(input('Nome completo: '), input('Apelido: '),
                              input('Nascimento (dd/mm/aaaa): '), getpass.getpass('Senha: '))
        return apresentar(q)
    if comando == '/login':
        uid = cliente.login(input('Apelido: '), getpass.getpass('Senha: '))
        return f'Autenticado. Seu ID: {uid}.'
    if comando in ('/online', '/amigos'):
        return apresentar(cliente.usuarios(comando == '/amigos'))
    if comando in ('/convidar', '/aceitar', '/recusar', '/silenciar', '/abrir', '/historico', '/perfil'):
        outro = int(resto)
        if outro < 1:
            raise ValueError('Informe um ID positivo.')
        if comando == '/convidar':
            cliente.convidar(outro)
            return 'Convite enviado; aguarde a resposta ou uma notificacao de erro.'
        if comando in ('/aceitar', '/recusar'):
            cliente.responder(outro, comando == '/aceitar')
            return 'Resposta enviada; consulte /amigos para confirmar.'
        if comando == '/silenciar':
            return apresentar(cliente.silenciar(outro))
        if comando == '/abrir':
            # Confirma a amizade antes de ativar consultas periodicas.
            novas = cliente.mensagens(outro)
            cliente.ativo = outro
            return f'Conversa privada com {outro}.\n' + apresentar(novas)
        if comando == '/historico':
            return apresentar(cliente.historico(outro))
        return apresentar(cliente.perfil(outro))
    if comando == '/geral':
        cliente.ativo = None
        return 'Conversa geral aberta.'
    if comando == '/privado':
        destino, separador, mensagem = resto.partition(' ')
        if not separador:
            raise ValueError('Use /privado ID mensagem.')
        return apresentar(cliente.enviar(mensagem, int(destino)))
    if comando == '/atualizar':
        return apresentar(cliente.atualizar(input('Novo nome: '), input('Nascimento (dd/mm/aaaa): '),
                                            getpass.getpass('Senha atual: ')))
    if comando.startswith('/'):
        raise ValueError('Comando desconhecido. Use /ajuda.')
    return apresentar(cliente.enviar(linha, cliente.ativo or ''))


def main():
    parser = argparse.ArgumentParser(description='Cliente de terminal IFFARCHAT')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--porta', type=int, default=42000)
    parser.add_argument('--intervalo', type=float, default=1.0)
    args = parser.parse_args()
    if args.intervalo <= 0:
        parser.error('Intervalo deve ser positivo.')
    cliente = ClienteChat(args.intervalo)
    fim = Event()
    print(AJUDA)
    try:
        cliente.conectar(args.host, args.porta)
        print('Conectado. Use /registrar ou /login.')
    except (OSError, ErroServidor) as erro:
        print(f'[DESCONECTADO] {erro}. Use /conectar.')

    def eventos():
        while not fim.is_set():
            try:
                print('\n' + apresentar(cliente.eventos.get(timeout=0.2)), flush=True)
            except Empty:
                continue

    Thread(target=eventos, daemon=True).start()
    try:
        while True:
            linha = input('chat> ').strip()
            if linha == '/sair':
                break
            if not linha:
                continue
            try:
                print(executar_comando(cliente, linha, args.host, args.porta), flush=True)
            except (OSError, ValueError) as erro:
                print(f'[ERRO] {erro}', flush=True)
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        fim.set()
        try:
            cliente.logout()
        except (OSError, ValueError):
            cliente.fechar()
        print('\nAte logo!')


if __name__ == '__main__':
    main()
