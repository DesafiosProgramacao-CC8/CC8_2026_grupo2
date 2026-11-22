"""Servidor TCP concorrente; o IFFARQL e acessado somente pela fila FIFO."""
import argparse
import logging
import socket
import socketserver
from threading import Lock, Thread
from parte_01_protocolo.protocolo import LeitorQuadros, Quadro, ErroProtocolo
from parte_02_persistencia.fila import FilaBanco
from .servico import ServicoChat, Sessao

LOG = logging.getLogger('iffarchat')


class Tratador(socketserver.BaseRequestHandler):
    def handle(self):
        sessao = Sessao()
        leitor = LeitorQuadros()
        self.request.settimeout(90)
        try:
            while True:
                dados = self.request.recv(65536)
                if not dados:
                    leitor.finalizar()
                    break
                for quadro in leitor.alimentar(dados):
                    respostas = self.server.servico.tratar_sem_banco(sessao, quadro)
                    if respostas is None:
                        respostas = self.server.fila.executar(self.server.servico.tratar, sessao, quadro)
                    for resposta in respostas:
                        self.request.sendall(resposta.bytes())
                    if any(r.codigo == 33 for r in respostas):
                        return
        except ErroProtocolo as erro:
            self._erro(str(erro))
        except (ConnectionError, socket.timeout, OSError):
            pass
        except Exception:
            LOG.exception('Erro interno ao processar conexao')
            self._erro('Falha interna; operacao nao confirmada.')
        finally:
            self.server.fila.executar(self.server.servico.sair, sessao)

    def _erro(self, mensagem):
        try:
            self.request.sendall(Quadro(32768, ('ERROCONEXAO', mensagem)).bytes())
        except OSError:
            pass


class ServidorChat(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = False
    block_on_close = True

    def __init__(self, endereco=('0.0.0.0', 42000), arquivo='dados/iffarchat.json'):
        self.fila = FilaBanco(arquivo)
        self.servico = ServicoChat()
        self.conexoes = set()
        self.trava_conexoes = Lock()
        try:
            super().__init__(endereco, Tratador)
        except Exception:
            self.fila.fechar()
            raise

    def process_request(self, request, client_address):
        with self.trava_conexoes:
            self.conexoes.add(request)
        super().process_request(request, client_address)

    def shutdown_request(self, request):
        with self.trava_conexoes:
            self.conexoes.discard(request)
        super().shutdown_request(request)

    def server_close(self):
        with self.trava_conexoes:
            for conexao in list(self.conexoes):
                try:
                    conexao.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        super().server_close()
        self.fila.fechar()


def main():
    parser = argparse.ArgumentParser(description='Servidor IFFARCHAT (TCP 42000)')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--dados', default='dados/iffarchat.json')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    with ServidorChat((args.host, 42000), args.dados) as servidor:
        print(f'IFFARCHAT ouvindo {args.host}:42000', flush=True)
        try:
            servidor.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            print('\nServidor encerrado.', flush=True)


if __name__ == '__main__':
    main()
