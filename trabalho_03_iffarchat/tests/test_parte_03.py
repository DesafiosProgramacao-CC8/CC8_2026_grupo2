import socket
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from parte_01_protocolo.protocolo import Quadro
from parte_01_protocolo.seguranca import codificar_senha
from .apoio import Ambiente, aceitar


class ServidorTest(unittest.TestCase):
    def setUp(self):
        self.amb = Ambiente().__enter__()
        self.a = self.amb.usuario('ana')
        self.b = self.amb.usuario('bruno')

    def tearDown(self):
        self.amb.__exit__()

    def test_ping_e_lista_online(self):
        self.assertEqual(self.a.pedir(4), Quadro(5))
        self.assertEqual(self.a.pedir(64, self.a.uid, 0), Quadro(65, ('1', 'ana', '2', 'bruno')))

    def test_ping_e_conectar_nao_esperam_a_fila(self):
        from .apoio import Fio
        ocupada, liberar = threading.Event(), threading.Event()

        def bloquear(repo):
            ocupada.set()
            liberar.wait(10)

        thread = threading.Thread(target=self.amb.servidor.fila.executar, args=(bloquear,), daemon=True)
        thread.start()
        try:
            self.assertTrue(ocupada.wait(3))
            self.assertEqual(self.a.pedir(4), Quadro(5))
            novo = Fio(self.amb.porta)
            self.amb.clientes.append(novo)
            self.assertEqual(novo.pedir(2), Quadro(3))
            self.assertEqual(novo.pedir(4), Quadro(5))
        finally:
            liberar.set()
            thread.join(5)

    def test_evento_entregue_e_apagado(self):
        from parte_02_persistencia.repositorio import inserir
        aceitar(self.a, self.b)
        self.assertEqual(self.amb.servidor.fila.executar(lambda r: r.todos('Evento')), [])
        # Linha entregue herdada de uma versao anterior tambem e removida, sem novo aviso.
        self.amb.servidor.fila.executar(lambda r: r.transacao([inserir('Evento', 2, 1, True, True)]))
        self.assertEqual(self.b.eventos(), [Quadro(129)])
        self.assertEqual(self.amb.servidor.fila.executar(lambda r: r.todos('Evento')), [])

    def test_hash_e_opaco_sem_normalizacao(self):
        c = self.amb.cliente()
        self.assertEqual(c.pedir(8, 'Xis', 'xis', '01/01/2000', 'abc ').codigo, 9)
        self.assertEqual(c.pedir(16, 'xis', 'abc ').codigo, 17)

    def test_geral_pendente_tem_limite(self):
        with patch('parte_03_servidor.servico.LIMITE_GERAIS', 3):
            c = self.amb.usuario('carla')
        for n in range(1, 6):
            self.assertEqual(self.a.pedir(2048, 1, '', f'm{n}').codigo, 2049)
        self.assertEqual(c.pedir(1024, c.uid, '').parametros[1::5], ('m3', 'm4', 'm5'))

    def test_exige_handshake_e_login(self):
        from .apoio import Fio
        c = Fio(self.amb.porta)
        self.amb.clientes.append(c)
        self.assertEqual(c.pedir(4).codigo, 32768)
        self.assertEqual(c.pedir(2).codigo, 3)
        self.assertEqual(c.pedir(64, 1, 0).codigo, 32768)

    def test_senha_incorreta_e_sessao_duplicada(self):
        c = self.amb.cliente()
        self.assertEqual(c.pedir(16, 'ana', 'incorreta').parametros[0], 'ERROAUTENTICACAO')
        self.assertEqual(c.pedir(16, 'ana', codificar_senha('Ab12Cd')).codigo, 32768)
        self.assertEqual(self.a.pedir(16, 'bruno', codificar_senha('Ab12Cd')).codigo, 32768)

    def test_apelido_unico_casefold(self):
        c = self.amb.cliente()
        self.assertEqual(c.pedir(8, 'Outra', 'ANA', '01/01/2000', 'hash').parametros[0], 'ERROREGISTRO')

    def test_cadastro_invalido(self):
        c = self.amb.cliente()
        for valores in [('', 'nova', '01/01/2000', 'hash'),
                        ('Nova', 'nova', '29/02/2001', 'hash'),
                        ('Nova', 'nova', '01/01/2999', 'hash'),
                        ('Nova', 'nova', '01/01/2000', '')]:
            with self.subTest(valores=valores):
                self.assertEqual(c.pedir(8, *valores).codigo, 32768)

    def test_protecao_id_sessao(self):
        for codigo, parametros in [(32, ('2',)), (64, ('2', '0')), (128, ('2',)),
                                    (256, ('2', '1')), (512, ('2', '1')),
                                    (1024, ('2', '')), (2048, ('2', '', 'fraude')),
                                    (4096, ('2', '1')),
                                    (16384, ('2', 'Fraude', '01/01/2000', 'hash'))]:
            with self.subTest(codigo=codigo):
                self.assertEqual(self.a.pedir(codigo, *parametros).codigo, 32768)
        self.assertEqual(self.a.pedir(8192, 2).parametros[1], 'Bruno')

    def test_amizade_aceita_duas_linhas(self):
        aceitar(self.a, self.b)
        self.assertEqual(self.a.pedir(64, 1, 1), Quadro(65, ('2', 'bruno')))
        self.assertEqual(self.b.pedir(64, 2, 1), Quadro(65, ('1', 'ana')))
        registros = self.amb.servidor.fila.executar(lambda r: r.todos('Amizade'))
        self.assertEqual(len(registros), 2)
        self.assertTrue(all(not a['bloqueado'] and not a['pendente'] for a in registros))

    def test_recusa_remove_duas_linhas(self):
        self.a.enviar(256, 1, 2)
        self.a.pedir(4)
        self.assertEqual(self.b.eventos()[0], Quadro(257, ('1',)))
        self.b.enviar(258, 2, 1, 'FALSO')
        self.b.pedir(4)
        self.assertEqual(self.a.eventos()[0], Quadro(259, ('2', 'FALSO')))
        self.assertEqual(self.a.pedir(64, 1, 1), Quadro(65))
        self.assertEqual(self.amb.servidor.fila.executar(lambda r: r.todos('Amizade')), [])

    def test_convite_proprio_duplicado_e_aceite_sem_permissao(self):
        self.assertEqual(self.a.pedir(256, 1, 1).codigo, 32768)
        self.a.enviar(256, 1, 2)
        self.a.pedir(4)
        self.assertEqual(self.a.pedir(256, 1, 2).codigo, 32768)
        self.assertEqual(self.b.pedir(256, 2, 1).codigo, 32768)
        self.assertEqual(self.a.pedir(258, 1, 2, 'VERDADEIRO').codigo, 32768)
        self.assertEqual(self.b.pedir(258, 2, 1, 'TRUE').codigo, 32768)

    def test_conversa_privada_bloqueada_ate_aceite(self):
        self.assertEqual(self.a.pedir(2048, 1, 2, 'Oi').codigo, 32768)
        self.a.enviar(256, 1, 2)
        self.a.pedir(4)
        self.assertEqual(self.a.pedir(2048, 1, 2, 'Oi').codigo, 32768)
        self.assertEqual(self.a.pedir(4096, 1, 2).codigo, 32768)

    def test_geral_apenas_online_e_sem_historico(self):
        self.assertEqual(self.a.pedir(2048, 1, '', 'Olá geral').codigo, 2049)
        self.assertEqual(self.b.pedir(1024, 2, '').parametros[1], 'Olá geral')
        self.assertEqual(self.b.pedir(1024, 2, ''), Quadro(1025))
        self.assertEqual(self.a.pedir(1024, 1, '').parametros[1], 'Olá geral')
        c = self.amb.usuario('carla')
        self.assertEqual(c.pedir(1024, c.uid, ''), Quadro(1025))
        self.assertEqual(self.a.pedir(4096, 1, '').codigo, 32768)
        self.assertEqual(self.amb.servidor.fila.executar(lambda r: r.todos('Conversa')), [])

    def test_notificacoes_incremental_e_historico_ordens_distintas(self):
        aceitar(self.a, self.b)
        self.a.pedir(2048, 1, 2, 'Olá João')
        self.b.pedir(2048, 2, 1, 'Oi Ana')
        self.assertEqual(self.b.eventos()[-1], Quadro(129, ('1',)))
        novas = self.b.pedir(1024, 2, 1)
        self.assertEqual(novas.codigo, 1025)
        self.assertEqual(novas.parametros[0:2], ('1', 'Olá João'))
        self.assertEqual(novas.parametros[5:7], ('2', 'Oi Ana'))
        self.assertEqual(self.b.eventos()[-1], Quadro(129))
        self.assertEqual(self.b.pedir(1024, 2, 1), Quadro(1025))
        historico = self.a.pedir(4096, 1, 2)
        self.assertEqual(historico.codigo, 4097)
        self.assertEqual(historico.parametros[4::5], ('Olá João', 'Oi Ana'))
        self.assertEqual(historico.parametros[0::5], ('1', '2'))

    def test_silenciamento_independente_preserva_mensagens(self):
        aceitar(self.a, self.b)
        self.assertEqual(self.b.pedir(512, 2, 1), Quadro(513))
        self.a.pedir(2048, 1, 2, 'Nao notificar Bruno')
        self.b.pedir(2048, 2, 1, 'Notificar Ana')
        self.assertEqual(self.b.eventos()[-1], Quadro(129))
        self.assertEqual(self.a.eventos()[-1], Quadro(129, ('2',)))
        self.b.pedir(512, 2, 1)
        self.assertEqual(self.b.eventos()[-1], Quadro(129, ('1',)))
        self.assertEqual(len(self.b.pedir(4096, 2, 1).parametros), 10)
        self.assertEqual(len(self.b.pedir(1024, 2, 1).parametros), 10)

    def test_perfil_atualizacao_nao_altera_senha(self):
        self.assertEqual(self.a.pedir(16384, 1, 'Ana Nova', '29/02/2000', 'errada').codigo, 32768)
        self.assertEqual(self.a.pedir(16384, 1, 'Ana Nova', '29/02/2000', codificar_senha('Ab12Cd')), Quadro(16385))
        perfil = self.b.pedir(8192, 1)
        self.assertEqual(perfil.parametros[1:3], ('Ana Nova', 'ana'))
        self.assertEqual(len(perfil.parametros), 4)
        self.assertEqual(self.a.pedir(32, 1), Quadro(33))
        c = self.amb.cliente()
        self.assertEqual(c.pedir(16, 'ana', codificar_senha('Ab12Cd')).codigo, 17)

    def test_logout_retira_online(self):
        self.assertEqual(self.a.pedir(32, 1), Quadro(33))
        self.assertEqual(self.b.pedir(64, 2, 0), Quadro(65, ('2', 'bruno')))
        self.assertEqual(self.a.socket.recv(1), b'')

    def test_fragmentacao_e_coalescencia_tcp(self):
        for byte in b'4|#\n':
            self.a.socket.sendall(bytes([byte]))
        self.assertEqual(self.a.receber(), Quadro(5))
        self.a.socket.sendall(b'4|#\n4|#\n')
        self.assertEqual(self.a.receber(), Quadro(5))
        self.assertEqual(self.a.receber(), Quadro(5))

    def test_quadro_invalido_erro_sem_matar_servidor(self):
        self.a.socket.sendall(b'999|#\n')
        self.assertEqual(self.a.receber().codigo, 32768)
        self.assertEqual(self.b.pedir(4), Quadro(5))

    def test_sem_vazamento_historico_para_terceiro(self):
        aceitar(self.a, self.b)
        self.a.pedir(2048, 1, 2, 'Segredo')
        c = self.amb.usuario('carla')
        self.assertEqual(c.pedir(4096, c.uid, 1).codigo, 32768)
        self.assertEqual(c.pedir(4096, 1, 2).codigo, 32768)

    def test_mensagem_vazia_ou_longa(self):
        for mensagem in ('', ' ', 'x' * 2001):
            self.assertEqual(self.a.pedir(2048, 1, '', mensagem).codigo, 32768)

    def test_cadastros_concorrentes_mesmo_apelido(self):
        clientes = [self.amb.cliente() for _ in range(8)]
        def registrar(c):
            return c.pedir(8, 'Concorrente', 'unico', '01/01/2000', 'hash').codigo
        with ThreadPoolExecutor(max_workers=8) as pool:
            resultados = list(pool.map(registrar, clientes))
        self.assertEqual(resultados.count(9), 1)
        self.assertEqual(resultados.count(32768), 7)

    def test_envio_concorrente_sem_perda(self):
        aceitar(self.a, self.b)
        def enviar(c):
            for i in range(12):
                self.assertEqual(c.pedir(2048, c.uid, '2' if c.uid == '1' else '1', f'{c.uid}-{i}').codigo, 2049)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(enviar, [self.a, self.b]))
        historico = self.a.pedir(4096, 1, 2)
        self.assertEqual(len(historico.parametros), 120)
        self.assertEqual(len(set(historico.parametros[4::5])), 24)

    def test_reinicio_recupera_privadas_mute_e_cursor(self):
        aceitar(self.a, self.b)
        self.a.pedir(2048, 1, 2, 'Primeira')
        self.b.pedir(1024, 2, 1)
        self.b.pedir(512, 2, 1)
        self.a.pedir(2048, 1, 2, 'Segunda')
        self.a.pedir(2048, 1, '', 'Geral efemera')
        self.amb.reiniciar()
        a, b = self.amb.cliente(), self.amb.cliente()
        self.assertEqual(a.pedir(16, 'ana', codificar_senha('Ab12Cd')).codigo, 17)
        self.assertEqual(b.pedir(16, 'bruno', codificar_senha('Ab12Cd')).codigo, 17)
        a.uid, b.uid = '1', '2'
        self.assertEqual(b.eventos()[-1], Quadro(129))
        self.assertEqual(b.pedir(1024, 2, 1).parametros[1], 'Segunda')
        self.assertEqual(b.pedir(4096, 2, 1).parametros[4::5], ('Primeira', 'Segunda'))
        self.assertEqual(a.pedir(1024, 1, ''), Quadro(1025))

    def test_convite_e_resposta_sobrevivem_reinicio_offline(self):
        self.a.enviar(256, 1, 2)
        self.a.pedir(4)
        self.amb.reiniciar()
        b = self.amb.cliente()
        b.uid = b.pedir(16, 'bruno', codificar_senha('Ab12Cd')).parametros[0]
        self.assertEqual(b.eventos()[0], Quadro(257, ('1',)))
        b.enviar(258, 2, 1, 'VERDADEIRO')
        b.pedir(4)
        self.amb.reiniciar()
        a = self.amb.cliente()
        a.uid = a.pedir(16, 'ana', codificar_senha('Ab12Cd')).parametros[0]
        self.assertEqual(a.eventos()[0], Quadro(259, ('2', 'VERDADEIRO')))
        self.assertEqual(a.eventos(), [Quadro(129)])

    def test_historico_ordena_por_calendario_e_desempata_id(self):
        from parte_02_persistencia.repositorio import atualizar
        aceitar(self.a, self.b)
        self.a.pedir(2048, 1, 2, 'Fevereiro')
        self.b.pedir(2048, 2, 1, 'Janeiro')
        self.amb.servidor.fila.executar(lambda r: r.transacao([
            atualizar('Conversa', 1, data='01/02/2026', hora=10, minuto=0),
            atualizar('Conversa', 2, data='31/01/2026', hora=10, minuto=0)]))
        self.assertEqual(self.a.pedir(4096, 1, 2).parametros[4::5], ('Janeiro', 'Fevereiro'))

    def test_fechamento_abrupto_remove_online(self):
        import time
        self.a.close()
        fim = time.monotonic() + 2
        while time.monotonic() < fim:
            lista = self.b.pedir(64, 2, 0)
            if lista == Quadro(65, ('2', 'bruno')):
                return
            time.sleep(0.01)
        self.fail('Sessao encerrada continuou online.')
