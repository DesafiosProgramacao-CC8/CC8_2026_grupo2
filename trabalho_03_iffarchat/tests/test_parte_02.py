import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from parte_02_persistencia.repositorio import Repositorio, inserir, atualizar
from parte_02_persistencia.fila import FilaBanco


class PersistenciaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.arquivo = Path(self.tmp.name)/'chat.json'
        self.repo = Repositorio(self.arquivo)

    def tearDown(self):
        self.tmp.cleanup()

    def usuario(self, nome='Ana'):
        self.repo.transacao([inserir('Usuario', nome, 'ana', '29/02/2000', 'deadbeef')])

    def test_esquema_e_iffarql(self):
        self.assertEqual(set(self.repo.motor.banco.tabelas), {'Usuario', 'Amizade', 'Conversa', 'Evento'})
        self.assertIn('"formato": "IFFARQL"', self.arquivo.read_text())

    def test_recuperacao(self):
        self.usuario()
        self.assertEqual(Repositorio(self.arquivo).obter('Usuario', 1)['nome_completo'], 'Ana')

    def test_texto_aspas_barras_e_acentos(self):
        nome = 'João "D\'Ávila" \\ teste; ATUALIZATABELA'
        self.usuario(nome)
        self.assertEqual(Repositorio(self.arquivo).obter('Usuario', 1)['nome_completo'], nome)

    def test_rollback_lote(self):
        antes = self.arquivo.read_bytes()
        with self.assertRaises(ValueError):
            self.repo.transacao([inserir('Usuario', 'Ana', 'ana', '01/01/2000', 'hash'),
                                 inserir('Amizade', 1, 999, True, False, False, True, 1, 0)])
        self.assertEqual(self.arquivo.read_bytes(), antes)
        self.assertEqual(self.repo.todos('Usuario'), [])

    def test_rollback_falha_disco(self):
        antes = self.arquivo.read_bytes()
        with patch.object(self.repo.motor.persistencia, 'salvar', side_effect=OSError('disco indisponivel')):
            with self.assertRaises(OSError):
                self.usuario()
        self.assertEqual(self.repo.todos('Usuario'), [])
        self.assertEqual(self.arquivo.read_bytes(), antes)

    def test_banco_corrompido_nao_sobrescrito(self):
        self.arquivo.write_text('{quebrado')
        with self.assertRaises(ValueError):
            Repositorio(self.arquivo)
        self.assertEqual(self.arquivo.read_text(), '{quebrado')

    def test_fk(self):
        with self.assertRaises(ValueError):
            self.repo.transacao([inserir('Conversa', 99, '01/01/2026', 10, 20, 'oi')])

    def test_atualizacao(self):
        self.usuario()
        self.repo.transacao([atualizar('Usuario', 1, nome_completo='Ana Maria')])
        self.assertEqual(self.repo.obter('Usuario', 1)['nome_completo'], 'Ana Maria')

    def test_fila_concorrente_consumidor_unico(self):
        from threading import get_ident
        fila = FilaBanco(self.arquivo)
        try:
            def tarefa(repo, numero):
                repo.transacao([inserir('Usuario', str(numero), str(numero), '01/01/2000', 'hash')])
                return get_ident()
            with ThreadPoolExecutor(max_workers=12) as executor:
                threads = list(executor.map(lambda n: fila.executar(tarefa, n), range(36)))
            self.assertEqual(len(set(threads)), 1)
            self.assertEqual(fila.executar(lambda r: len(r.todos('Usuario'))), 36)
        finally:
            fila.fechar()
        with self.assertRaises(RuntimeError):
            fila.executar(lambda r: True)
