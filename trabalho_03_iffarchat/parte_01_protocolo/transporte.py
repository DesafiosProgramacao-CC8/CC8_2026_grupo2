"""Transporte do cliente: receptor unico e correlacao sequencial das respostas."""
import socket
from queue import Queue, Empty
from .protocolo import Quadro, LeitorQuadros


class ErroServidor(ValueError):
    def __init__(self, quadro):
        self.categoria, self.mensagem = quadro.parametros
        super().__init__(f'{self.categoria}: {self.mensagem}')


class TransporteTCP:
    def _receber(self):
        leitor = LeitorQuadros(limite=64 * 1024 * 1024)
        try:
            while not self.parar.is_set():
                dados = self.socket.recv(65536)
                if not dados:
                    leitor.finalizar()
                    raise ConnectionError('Servidor encerrou a conexao.')
                for quadro in leitor.alimentar(dados):
                    with self.estado:
                        pendente = self.pendente
                        if (quadro.codigo not in (257, 259) and pendente is not None
                                and quadro.codigo in (pendente[0], 32768)):
                            self.pendente = None
                            pendente[1].put(quadro)
                        else:
                            self.eventos.put(quadro)
        except (OSError, ValueError, ConnectionError) as erro:
            self._perdeu_conexao(str(erro))

    def requisitar(self, codigo, *parametros, esperado=None):
        bruto = Quadro(codigo, tuple(map(str, parametros))).bytes()
        with self.trava:
            if not self.conectado:
                raise ConnectionError('Cliente desconectado.')
            resposta = Queue()
            if esperado is not None:
                with self.estado:
                    self.pendente = (esperado, resposta)
            try:
                self.socket.sendall(bruto)
                if esperado is None:
                    return None
                recebido = resposta.get(timeout=self.timeout)
                if isinstance(recebido, Exception):
                    raise recebido
                if recebido.codigo == 32768:
                    raise ErroServidor(recebido)
                return recebido
            except (OSError, Empty) as erro:
                self._perdeu_conexao('Conexao perdida ou servidor sem resposta.')
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                raise ConnectionError('Conexao perdida ou servidor sem resposta.') from erro
            finally:
                with self.estado:
                    self.pendente = None

