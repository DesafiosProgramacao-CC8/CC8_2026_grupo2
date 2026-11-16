"""Cliente reutilizavel: receptor TCP unico, eventos e polling em segundo plano."""
import socket
from queue import Queue
from threading import Thread, Lock, Event
from parte_01_protocolo.protocolo import Quadro
from parte_01_protocolo.transporte import TransporteTCP, ErroServidor
from parte_01_protocolo.seguranca import codificar_senha, texto, nascimento


class ClienteChat(TransporteTCP):
    def __init__(self, intervalo=1.0, timeout=5.0):
        self.intervalo = intervalo
        self.timeout = timeout
        self.socket = None
        self.usuario = None
        self.conectado = False
        self.ativo = None
        self.eventos = Queue()
        self.trava = Lock()
        self.estado = Lock()
        self.pendente = None
        self.parar = Event()
        self.receptor = None
        self.poller = None

    def conectar(self, host='127.0.0.1', porta=42000):
        self.fechar()
        self.parar = Event()
        self.socket = socket.create_connection((host, porta), self.timeout)
        self.socket.settimeout(None)
        self.conectado = True
        self.receptor = Thread(target=self._receber, name='chat-receptor', daemon=True)
        self.receptor.start()
        try:
            self.requisitar(2, esperado=3)
        except Exception:
            self.fechar()
            raise
        self.poller = Thread(target=self._polling, name='chat-polling', daemon=True)
        self.poller.start()

    def _perdeu_conexao(self, motivo):
        estava = self.conectado
        self.conectado = False
        self.usuario = None
        self.ativo = None
        self.parar.set()
        with self.estado:
            if self.pendente:
                self.pendente[1].put(ConnectionError(motivo))
                self.pendente = None
        if estava:
            self.eventos.put(('desconectado', motivo))

    def registrar(self, nome, apelido, data, senha):
        return self.requisitar(8, texto(nome, 'Nome'), texto(apelido, 'Apelido', 40),
                               nascimento(data), codificar_senha(senha), esperado=9)

    def login(self, apelido, senha):
        quadro = self.requisitar(16, texto(apelido, 'Apelido', 40),
                                 codificar_senha(senha), esperado=17)
        self.usuario = int(quadro.parametros[0])
        return self.usuario

    def meu_id(self):
        if self.usuario is None:
            raise ValueError('Faca login primeiro.')
        return self.usuario

    def usuarios(self, amigos=False):
        return self.requisitar(64, self.meu_id(), int(amigos), esperado=65)

    def notificacoes(self):
        return self.requisitar(128, self.meu_id(), esperado=129)

    def convidar(self, outro):
        self.requisitar(256, self.meu_id(), outro)

    def responder(self, outro, aceitar):
        self.requisitar(258, self.meu_id(), outro, 'VERDADEIRO' if aceitar else 'FALSO')

    def silenciar(self, outro):
        return self.requisitar(512, self.meu_id(), outro, esperado=513)

    def enviar(self, mensagem, outro=''):
        return self.requisitar(2048, self.meu_id(), outro, texto(mensagem, 'Mensagem', 2000), esperado=2049)

    def mensagens(self, outro=''):
        return self.requisitar(1024, self.meu_id(), outro, esperado=1025)

    def historico(self, outro):
        return self.requisitar(4096, self.meu_id(), outro, esperado=4097)

    def perfil(self, outro):
        return self.requisitar(8192, outro, esperado=8193)

    def atualizar(self, nome, data, senha):
        return self.requisitar(16384, self.meu_id(), texto(nome, 'Nome'), nascimento(data),
                               codificar_senha(senha), esperado=16385)

    def _polling(self):
        anteriores = ()
        while not self.parar.wait(self.intervalo):
            try:
                self.requisitar(4, esperado=5)
                if self.usuario is None:
                    continue
                notificacoes = self.notificacoes()
                if notificacoes.parametros != anteriores:
                    if notificacoes.parametros:
                        self.eventos.put(notificacoes)
                    anteriores = notificacoes.parametros
                geral = self.mensagens()
                if geral.parametros:
                    self.eventos.put(geral)
                if self.ativo:
                    privado = self.mensagens(self.ativo)
                    if privado.parametros:
                        self.eventos.put(privado)
            except ErroServidor as erro:
                self.eventos.put(Quadro(32768, (erro.categoria, erro.mensagem)))
            except (OSError, ValueError):
                if not self.conectado:
                    return

    def logout(self):
        try:
            if self.conectado and self.usuario is not None:
                self.requisitar(32, self.usuario, esperado=33)
        finally:
            self.fechar()

    def fechar(self):
        self.parar.set()
        self.conectado = False
        self.usuario = None
        self.ativo = None
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.socket.close()
        from threading import current_thread
        for thread in (self.receptor, self.poller):
            if thread and thread is not current_thread():
                thread.join(timeout=self.timeout + 1)
        self.socket = None
