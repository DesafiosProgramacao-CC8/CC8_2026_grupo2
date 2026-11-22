"""Adapta o cliente TCP para uma janela com um único fluxo de operações."""
from queue import Empty, Queue
from threading import Thread

from .cliente import ClienteChat


class SessaoVisual(ClienteChat):
    def _polling(self):
        # A janela agenda as consultas em conjunto com as ações dos botões.
        # O receptor TCP original continua ativo.
        pass

    def entrar(self, host, porta, apelido, senha):
        try:
            self.conectar(host, porta)
            return self.login(apelido, senha)
        except (OSError, ValueError):
            self.fechar()
            raise

    def cadastrar(self, host, porta, nome, apelido, data, senha):
        try:
            self.conectar(host, porta)
            self.registrar(nome, apelido, data, senha)
        finally:
            self.fechar()

    def contatos(self):
        def pares(quadro):
            campos = quadro.parametros
            return dict(zip(campos[::2], campos[1::2]))

        return pares(self.usuarios()), pares(self.usuarios(amigos=True))

    def tentar_convite(self, outro, aceitar=None):
        if aceitar is None:
            self.convidar(outro)
        else:
            self.responder(outro, aceitar)
        # O protocolo não define ACK para estes comandos. PONG chega depois
        # do processamento dos comandos anteriores no mesmo socket.
        self.requisitar(4, esperado=5)

    def sincronizar(self, conversa, atualizar_contatos):
        geral = self.mensagens()
        privado = None
        if conversa and self.mensagens(conversa).parametros:
            # Consulta um retrato completo. Assim, mensagens idênticas enviadas
            # no mesmo minuto continuam distintas, sem duplicar ao reabrir.
            privado = self.historico(conversa)
        avisos = self.notificacoes()
        contatos = self.contatos() if atualizar_contatos else None
        return geral, privado, avisos, contatos


class TrabalhoRede:
    """Serializa chamadas de rede e devolve resultados à thread do Tk."""
    def __init__(self):
        self.cliente = SessaoVisual()
        self.pedidos = Queue()
        self.resultados = Queue()
        self.thread = Thread(target=self._executar, daemon=True, name="iffarchat-visual")
        self.thread.start()

    def _executar(self):
        while True:
            item = self.pedidos.get()
            if item is None:
                self.cliente.fechar()
                return
            operacao, retorno = item
            try:
                valor = operacao()
            except Exception as erro:
                self.resultados.put((retorno, None, erro))
            else:
                self.resultados.put((retorno, valor, None))

    def pedir(self, operacao, retorno):
        self.pedidos.put((operacao, retorno))

    def eventos(self):
        while True:
            try:
                yield self.cliente.eventos.get_nowait()
            except Empty:
                return
