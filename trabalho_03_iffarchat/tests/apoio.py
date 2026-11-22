import socket
import threading
import tempfile
from collections import deque
from parte_01_protocolo.protocolo import Quadro, LeitorQuadros
from parte_01_protocolo.seguranca import codificar_senha
from parte_03_servidor.servidor import ServidorChat


class Ambiente:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.arquivo = self.tmp.name + '/chat.json'
        self.clientes = []
        self.iniciar()
        return self

    def iniciar(self):
        self.servidor = ServidorChat(('127.0.0.1', 0), self.arquivo)
        self.porta = self.servidor.server_address[1]
        self.thread = threading.Thread(target=self.servidor.serve_forever,
                                       kwargs={'poll_interval': 0.02}, daemon=True)
        self.thread.start()

    def parar(self):
        for cliente in self.clientes:
            cliente.close()
        self.clientes.clear()
        self.servidor.shutdown()
        self.servidor.server_close()
        self.thread.join(5)
        assert not self.thread.is_alive(), 'Servidor nao encerrou'

    def reiniciar(self):
        self.parar()
        self.iniciar()

    def cliente(self):
        cliente = Fio(self.porta)
        self.clientes.append(cliente)
        assert cliente.pedir(2).codigo == 3
        return cliente

    def usuario(self, apelido):
        cliente = self.cliente()
        assert cliente.pedir(8, apelido.title(), apelido, '01/01/2001', codificar_senha('Ab12Cd')).codigo == 9
        autenticado = cliente.pedir(16, apelido, codificar_senha('Ab12Cd'))
        assert autenticado.codigo == 17
        cliente.uid = autenticado.parametros[0]
        return cliente

    def __exit__(self, *args):
        self.parar()
        self.tmp.cleanup()


class Fio:
    """Cliente de teste independente da implementacao ClienteChat."""
    def __init__(self, porta):
        self.socket = socket.create_connection(('127.0.0.1', porta), 3)
        self.socket.settimeout(3)
        self.leitor = LeitorQuadros(limite=64 * 1024 * 1024)
        self.recebidos = deque()
        self.uid = None

    def enviar(self, codigo, *parametros):
        self.socket.sendall(Quadro(codigo, tuple(map(str, parametros))).bytes())

    def receber(self):
        while not self.recebidos:
            dados = self.socket.recv(65536)
            if not dados:
                raise ConnectionError('EOF')
            self.recebidos.extend(self.leitor.alimentar(dados))
        return self.recebidos.popleft()

    def pedir(self, codigo, *parametros):
        self.enviar(codigo, *parametros)
        return self.receber()

    def eventos(self):
        self.enviar(128, self.uid)
        quadros = []
        while True:
            q = self.receber()
            quadros.append(q)
            if q.codigo in (129, 32768):
                return quadros

    def close(self):
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.socket.close()


def aceitar(a, b):
    a.enviar(256, a.uid, b.uid)
    # PING e barreira: o comando anterior do mesmo socket ja foi processado.
    assert a.pedir(4).codigo == 5
    assert b.eventos()[0] == Quadro(257, (a.uid,))
    b.enviar(258, b.uid, a.uid, 'VERDADEIRO')
    assert b.pedir(4).codigo == 5
    assert a.eventos()[0] == Quadro(259, (b.uid, 'VERDADEIRO'))
