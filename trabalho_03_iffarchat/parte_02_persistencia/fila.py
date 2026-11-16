#os clientes podem pedir juntos, mas só uma thread acessa o banco
from concurrent.futures import Future
from queue import Queue
from threading import Thread, Lock
from .repositorio import Repositorio


class FilaBanco:
    def __init__(self, arquivo):
        self.fila = Queue()
        self.fechada = False
        self.trava = Lock()
        self.pronta = Future()
        self.thread = Thread(
            target=self._trabalhar,
            args=(arquivo,),
            name='iffarql-fifo',
            daemon=True,
        )
        self.thread.start()
        self.pronta.result(timeout=10)

    def _trabalhar(self, arquivo):
        try:
            repositorio = Repositorio(arquivo)
        except Exception as erro:
            self.pronta.set_exception(erro)
            return
        self.pronta.set_result(True)
        while True:
            pedido = self.fila.get()
            try:
                if pedido is None:
                    return
                futuro, funcao, argumentos = pedido
                try:
                    #o pedido inteiro termina antes de tirar o próximo da fila
                    futuro.set_result(funcao(repositorio, *argumentos))
                except Exception as erro:
                    futuro.set_exception(erro)
            finally:
                self.fila.task_done()

    def executar(self, funcao, *argumentos):
        futuro = Future()
        #a mesma trava impede enfileirar um pedido enquanto a fila fecha
        with self.trava:
            if self.fechada:
                raise RuntimeError('Fila encerrada.')
            self.fila.put((futuro, funcao, argumentos))
        return futuro.result()

    def fechar(self):
        with self.trava:
            if not self.fechada:
                self.fechada = True
                #o sinal de saída fica depois dos pedidos que já entraram
                self.fila.put(None)
        self.thread.join()
