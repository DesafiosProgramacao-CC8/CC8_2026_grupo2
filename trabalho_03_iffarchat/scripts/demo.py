"""Demonstracao real e reproduzivel com dois clientes TCP e banco temporario.
Execute: python -m scripts.demo. Nao modifica os dados normais do servidor.
"""
import tempfile
import threading
from pathlib import Path
from queue import Empty
from parte_03_servidor.servidor import ServidorChat
from parte_04_cliente.cliente import ClienteChat
from parte_04_cliente.terminal import executar_comando, apresentar


def main():
    with tempfile.TemporaryDirectory() as tmp:
        servidor = ServidorChat(('127.0.0.1', 0), Path(tmp)/'demo.json')
        thread = threading.Thread(target=servidor.serve_forever,
                                  kwargs={'poll_interval': 0.02}, daemon=True)
        thread.start()
        a, b = ClienteChat(intervalo=60), ClienteChat(intervalo=60)
        try:
            for c, nome, apelido in ((a, 'Ana Souza', 'ana'), (b, 'Bruno Silva', 'bruno')):
                c.conectar('127.0.0.1', servidor.server_address[1])
                print(f'{apelido}> Conectado ao servidor TCP.')
                print(apresentar(c.registrar(nome, apelido, '01/01/2000', 'Ab12Cd')))
                print(f'Autenticado. Seu ID: {c.login(apelido, "Ab12Cd")}.')
            def comando(c, apelido, linha):
                print(f'\n{apelido}> {linha}')
                print(executar_comando(c, linha, '127.0.0.1', servidor.server_address[1]))
            def eventos(c, apelido):
                print(apelido + '> verificar notificacoes')
                q = c.notificacoes()
                while True:
                    try:
                        print(apresentar(c.eventos.get_nowait()))
                    except Empty:
                        break
                print(apresentar(q))
            comando(a, 'ana', '/online')
            comando(a, 'ana', '/convidar 2')
            a.requisitar(4, esperado=5)
            eventos(b, 'bruno')
            comando(b, 'bruno', '/aceitar 1')
            b.requisitar(4, esperado=5)
            eventos(a, 'ana')
            comando(a, 'ana', '/amigos')
            comando(a, 'ana', '/privado 2 Olá Bruno! Nosso IFFARCHAT funciona.')
            eventos(b, 'bruno')
            comando(b, 'bruno', '/abrir 1')
            comando(b, 'bruno', 'Olá Ana! Mensagem recebida.')
            comando(a, 'ana', '/historico 2')
            comando(b, 'bruno', '/silenciar 1')
            comando(a, 'ana', '/privado 2 Esta mensagem continua salva com o chat silenciado.')
            eventos(b, 'bruno')
            comando(b, 'bruno', '/historico 1')
            comando(a, 'ana', 'Bem-vindos à conversa geral!')
            print('bruno> receber conversa geral')
            print(apresentar(b.mensagens()))
            comando(a, 'ana', '/perfil 2')
            a.logout()
            b.logout()
            print('\nDois clientes desconectados. Demonstracao concluida.')
        finally:
            a.fechar()
            b.fechar()
            servidor.shutdown()
            servidor.server_close()
            thread.join(5)


if __name__ == '__main__':
    main()
