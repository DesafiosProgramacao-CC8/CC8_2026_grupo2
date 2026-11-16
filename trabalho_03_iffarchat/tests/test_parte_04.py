import socket
import tempfile
import threading
import time
import unittest
from io import StringIO
from pathlib import Path
from queue import Empty
from unittest.mock import patch
from parte_04_cliente.cliente import ClienteChat, ErroServidor
from parte_04_cliente.terminal import executar_comando, apresentar, main
from parte_01_protocolo.protocolo import Quadro, LeitorQuadros
from parte_03_servidor.servidor import ServidorChat


class ClienteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.servidor = ServidorChat(('127.0.0.1', 0), Path(self.tmp.name)/'chat.json')
        self.porta = self.servidor.server_address[1]
        self.thread = threading.Thread(target=self.servidor.serve_forever,
                                       kwargs={'poll_interval': 0.02}, daemon=True)
        self.thread.start()
        self.clientes = []
        self.a = self.novo('ana')
        self.b = self.novo('bruno')

    def tearDown(self):
        for c in self.clientes:
            c.fechar()
        self.servidor.shutdown()
        self.servidor.server_close()
        self.thread.join(5)
        self.tmp.cleanup()

    def novo(self, apelido):
        c = ClienteChat(intervalo=0.03, timeout=2)
        self.clientes.append(c)
        c.conectar('127.0.0.1', self.porta)
        c.registrar(apelido.title(), apelido, '01/01/2000', 'Ab12Cd')
        c.login(apelido, 'Ab12Cd')
        return c

    def aguardar(self, cliente, codigo, predicado=lambda q: True):
        fim = time.monotonic() + 3
        while time.monotonic() < fim:
            try:
                evento = cliente.eventos.get(timeout=0.1)
            except Empty:
                continue
            if isinstance(evento, Quadro) and evento.codigo == codigo and predicado(evento):
                return evento
        self.fail(f'Evento {codigo} nao recebido pelo polling.')

    def amigos(self):
        self.a.convidar(self.b.usuario)
        self.aguardar(self.b, 257)
        self.b.responder(self.a.usuario, True)
        self.assertEqual(self.aguardar(self.a, 259).parametros[1], 'VERDADEIRO')

    def test_cliente_cadastro_login_listas_perfil(self):
        self.assertEqual(self.a.usuario, 1)
        self.assertEqual(self.a.usuarios().parametros, ('1', 'ana', '2', 'bruno'))
        self.assertEqual(self.a.perfil(2).parametros[1], 'Bruno')

    def test_erro_servidor_nao_desconecta(self):
        with self.assertRaises(ErroServidor):
            self.a.login('ana', 'errada')
        self.assertTrue(self.a.conectado)
        self.assertEqual(self.a.requisitar(4, esperado=5), Quadro(5))

    def test_validacao_cliente_antes_da_rede(self):
        with self.assertRaises(ValueError):
            self.a.registrar('Nome', 'novo', '01/01/2000', 'curta')
        with self.assertRaises(ValueError):
            self.a.enviar('ola|injetado')
        self.assertEqual(self.a.requisitar(4, esperado=5), Quadro(5))

    def test_polling_geral(self):
        self.a.enviar('Olá a todos')
        evento = self.aguardar(self.b, 1025)
        self.assertEqual(evento.parametros[1], 'Olá a todos')

    def test_polling_convite_resposta_notificacao_privada(self):
        self.amigos()
        self.a.enviar('Mensagem privada', self.b.usuario)
        self.assertEqual(self.aguardar(self.b, 129).parametros, ('1',))
        self.b.ativo = self.a.usuario
        self.assertEqual(self.aguardar(self.b, 1025).parametros[1], 'Mensagem privada')

    def test_cliente_silencia_historico_atualiza(self):
        self.amigos()
        self.b.silenciar(1)
        self.a.enviar('Preservada', 2)
        self.assertEqual(self.b.historico(1).parametros[4], 'Preservada')
        self.b.atualizar('Bruno Novo', '29/02/2000', 'Ab12Cd')
        self.assertEqual(self.a.perfil(2).parametros[1], 'Bruno Novo')

    def test_erro_assincrono_convite(self):
        self.a.convidar(self.a.usuario)
        self.assertEqual(self.aguardar(self.a, 32768).parametros[0], 'ERROCONEXAO')

    def test_queda_retorna_desconectado(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        fim = time.monotonic() + 3
        while self.a.conectado and time.monotonic() < fim:
            self.a.parar.wait(0.01)
        self.assertFalse(self.a.conectado)
        self.assertIsNone(self.a.usuario)
        self.assertIsNone(self.a.ativo)
        with self.assertRaises(ConnectionError):
            self.a.requisitar(4, esperado=5)

    def test_logout_e_reconexao(self):
        self.a.logout()
        self.assertFalse(self.a.conectado)
        self.a.conectar('127.0.0.1', self.porta)
        self.assertEqual(self.a.login('ana', 'Ab12Cd'), 1)

    def test_terminal_comandos_reais(self):
        def comando(s):
            return executar_comando(self.a, s, '127.0.0.1', self.porta)
        self.assertIn('bruno', comando('/online'))
        self.assertIn('Bruno', comando('/perfil 2'))
        self.assertIn('Mensagem enviada', comando('Teste geral'))
        self.amigos()
        self.assertIn('privada', comando('/abrir 2'))
        self.assertEqual(self.a.ativo, 2)
        self.assertIn('Mensagem enviada', comando('/privado 2 Uma mensagem'))
        self.assertIn('Uma mensagem', comando('/historico 2'))
        self.assertIn('alternado', comando('/silenciar 2'))
        self.assertIn('geral', comando('/geral'))
        self.assertIsNone(self.a.ativo)
        with self.assertRaises(ValueError):
            comando('/naoexiste')
        with self.assertRaises(ValueError):
            comando('/abrir zero')

    def test_terminal_formularios(self):
        c = ClienteChat(intervalo=0.03)
        self.clientes.append(c)
        c.conectar('127.0.0.1', self.porta)
        with patch('builtins.input', side_effect=['Carla', 'carla', '29/02/2000']), \
                patch('getpass.getpass', return_value='Cd34Ef'):
            self.assertIn('Cadastro', executar_comando(c, '/registrar', '', 0))
        with patch('builtins.input', return_value='carla'), patch('getpass.getpass', return_value='Cd34Ef'):
            self.assertIn('Autenticado', executar_comando(c, '/login', '', 0))
        with patch('builtins.input', side_effect=['Carla Nova', '28/02/2000']), \
                patch('getpass.getpass', return_value='Cd34Ef'):
            self.assertIn('atualizado', executar_comando(c, '/atualizar', '', 0))

    def test_apresentacao_ordem_dos_campos(self):
        esperado = '[01/01/2026 09:05] Usuario 1: Olá'
        self.assertEqual(apresentar(Quadro(1025, ('1', 'Olá', '01/01/2026', '9', '5'))), esperado)
        self.assertEqual(apresentar(Quadro(4097, ('1', '01/01/2026', '9', '5', 'Olá'))), esperado)


class TerminalInicializacaoTest(unittest.TestCase):
    def test_recusa_inicial_permite_reconectar(self):
        erro = ErroServidor(Quadro(32768, ('ERROCONEXAO', 'Conexao recusada')))
        with (
            patch('sys.argv', ['cliente.py']),
            patch('sys.stdout', new_callable=StringIO) as saida,
            patch('builtins.input', side_effect=['/conectar', '/sair']),
            patch.object(ClienteChat, 'conectar', side_effect=[erro, None]) as conectar,
        ):
            main()

        texto = saida.getvalue()
        self.assertIn('[DESCONECTADO] ERROCONEXAO: Conexao recusada. Use /conectar.', texto)
        self.assertIn('Conectado. Use /login ou /registrar.', texto)
        self.assertEqual(conectar.call_count, 2)


class ServidorIndependenteTest(unittest.TestCase):
    def test_cliente_com_servidor_scriptado_externo(self):
        """Wire literal, sem ServidorChat: hash antes da rede e evento intercalado."""
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        recebidos = []
        erros = []
        def atender():
            try:
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(3)
                    leitor = LeitorQuadros()
                    while True:
                        dados = conn.recv(4096)
                        if not dados:
                            return
                        for q in leitor.alimentar(dados):
                            recebidos.append(q)
                            resposta = {2: b'3|#\n', 8: b'9|#\n', 16: b'17|42|#\n',
                                        64: b'257|15|#\n65|15|colega|#\n', 32: b'33|#\n'}[q.codigo]
                            # Inclusive fragmentacao da resposta de servidor externo.
                            for byte in resposta:
                                conn.sendall(bytes([byte]))
            except Exception as erro:
                erros.append(erro)
        thread = threading.Thread(target=atender, daemon=True)
        thread.start()
        c = ClienteChat(intervalo=60, timeout=3)
        try:
            c.conectar('127.0.0.1', listener.getsockname()[1])
            c.registrar('Julio', 'julio', '01/01/2000', 'abc123')
            self.assertNotEqual(recebidos[-1].parametros[-1], 'abc123')
            self.assertEqual(len(recebidos[-1].parametros[-1]), 8)
            self.assertEqual(c.login('julio', 'abc123'), 42)
            self.assertEqual(c.usuarios(), Quadro(65, ('15', 'colega')))
            self.assertEqual(c.eventos.get(timeout=2), Quadro(257, ('15',)))
            c.logout()
        finally:
            c.fechar()
            listener.close()
            thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(erros, [])
