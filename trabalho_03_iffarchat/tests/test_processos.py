"""Persistencia depois de termino forcado de um processo separado."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from .apoio import Fio, aceitar
from parte_01_protocolo.seguranca import codificar_senha


class ProcessosTest(unittest.TestCase):
    def test_kill_e_recuperacao(self):
        with tempfile.TemporaryDirectory() as tmp:
            banco = str(Path(tmp)/'chat.json')
            comando = [sys.executable, '-u', '-c',
                       'from parte_03_servidor.servidor import ServidorChat; import sys; '
                       's=ServidorChat(("127.0.0.1", 0), sys.argv[1]); '
                       'print(s.server_address[1], flush=True); s.serve_forever()', banco]
            processos, clientes = [], []
            def iniciar():
                p = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                processos.append(p)
                linha = p.stdout.readline()
                if not linha:
                    self.fail(p.stderr.read())
                return int(linha)
            def conectar(porta):
                c = Fio(porta)
                clientes.append(c)
                self.assertEqual(c.pedir(2).codigo, 3)
                return c
            try:
                porta = iniciar()
                a, b = conectar(porta), conectar(porta)
                for c, apelido in ((a, 'ana'), (b, 'bruno')):
                    self.assertEqual(c.pedir(8, apelido, apelido, '01/01/2000', codificar_senha('Ab12Cd')).codigo, 9)
                    c.uid = c.pedir(16, apelido, codificar_senha('Ab12Cd')).parametros[0]
                aceitar(a, b)
                self.assertEqual(a.pedir(2048, 1, 2, 'Confirmada antes do kill').codigo, 2049)
                processos[0].kill()
                processos[0].wait(timeout=5)
                for c in clientes:
                    c.close()
                clientes.clear()
                porta = iniciar()
                c = conectar(porta)
                self.assertEqual(c.pedir(16, 'bruno', codificar_senha('Ab12Cd')).codigo, 17)
                self.assertEqual(c.pedir(4096, 2, 1).parametros[4], 'Confirmada antes do kill')
            finally:
                for c in clientes:
                    c.close()
                for p in processos:
                    if p.poll() is None:
                        p.kill()
                    p.wait(timeout=5)
                    p.stdout.close()
                    p.stderr.close()
