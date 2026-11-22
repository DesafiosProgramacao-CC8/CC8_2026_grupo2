"""Cliente gráfico do IFFARCHAT para Windows, Linux e macOS com Tk."""
import argparse
from queue import Empty
import time
import tkinter as tk
from tkinter import font, messagebox, ttk

from .sessao_visual import TrabalhoRede

FUNDO = "#edf1f7"
PAPEL = "#ffffff"
TINTA = "#171c31"
SUAVE = "#52617b"
BORDA = "#dce3ed"
MARCA = "#4536b8"
ACENTO = "#5946de"
ERRO = "#972b49"
SUCESSO = "#166554"
NAV = "#181733"
NAV_PAINEL = "#262448"
NAV_TEXTO = "#d3d0ed"


def fonte(pai, tamanho, negrito=False):
    familia = font.nametofont("TkDefaultFont", root=pai).cget("family")
    return familia, tamanho, "bold" if negrito else "normal"


def caixa(pai, fundo=PAPEL, **kwargs):
    return tk.Frame(pai, bg=fundo, **kwargs)


def texto(pai, valor, tamanho=11, cor=TINTA, fundo=PAPEL, negrito=False, **kwargs):
    return tk.Label(pai, text=valor, bg=fundo, fg=cor,
                    font=fonte(pai, tamanho, negrito), **kwargs)


def botao(pai, rotulo, acao, estilo="Suave"):
    return ttk.Button(pai, text=rotulo, command=acao, style=f"{estilo}.TButton")


def mensagens(quadro):
    campos = quadro.parametros
    for i in range(0, len(campos), 5):
        if quadro.codigo == 4097:
            uid, data, hora, minuto, corpo = campos[i:i + 5]
        else:
            uid, corpo, data, hora, minuto = campos[i:i + 5]
        yield uid, data, hora.zfill(2), minuto.zfill(2), corpo


class InterfaceChat:
    def __init__(self, raiz, host, porta):
        self.raiz = raiz
        raiz.title("IFFARCHAT")
        raiz.geometry("1100x720")
        raiz.minsize(880, 640)
        raiz.configure(bg=FUNDO)
        raiz.protocol("WM_DELETE_WINDOW", self.encerrar)
        self.estilos()

        self.rede = TrabalhoRede()
        self.cliente = self.rede.cliente
        self.host = tk.StringVar(value=host)
        self.porta = tk.StringVar(value=str(porta))
        self.apelido = tk.StringVar()
        self.uid = None
        self.ocupado = False
        self.consultando = False
        self.ultima_lista = 0
        self.fechando = False
        self.status = tk.StringVar()
        self.tela = caixa(raiz, FUNDO)
        self.tela.pack(fill="both", expand=True)
        self.mostrar_entrada()
        raiz.after(50, self.processar)
        raiz.after(600, self.polling)

    def estilos(self):
        padrao = font.nametofont("TkDefaultFont", root=self.raiz)
        familias = {nome.casefold(): nome for nome in font.families(self.raiz)}
        for nome in ("Segoe UI", "Helvetica Neue", "DejaVu Sans"):
            if nome.casefold() in familias:
                padrao.configure(family=familias[nome.casefold()], size=10)
                break
        estilo = ttk.Style(self.raiz)
        estilo.theme_use("clam")
        estilo.configure("TEntry", padding=(10, 8), fieldbackground=PAPEL,
                         foreground=TINTA, bordercolor=BORDA, insertcolor=TINTA)
        estilo.map("TEntry", bordercolor=[("focus", ACENTO)])
        for nome, fundo, cor, foco in [
            ("Suave", "#eef0fa", TINTA, "#dddffc"),
            ("Principal", MARCA, PAPEL, "#342791"),
            ("Nav", NAV_PAINEL, PAPEL, "#383463")
        ]:
            classe = f"{nome}.TButton"
            estilo.configure(classe, background=fundo, foreground=cor, padding=(12, 8),
                             borderwidth=0, font=fonte(self.raiz, 10, True))
            estilo.map(classe, background=[("disabled", "#e2e5ed"), ("active", foco)],
                       foreground=[("disabled", "#62708a")],
                       bordercolor=[("focus", ACENTO)])

    def limpar(self):
        for componente in self.tela.winfo_children():
            componente.destroy()
        self.status.set("")

    def avisar(self, mensagem, erro=False):
        self.status.set(mensagem)
        self.status_label.configure(fg=ERRO if erro else SUCESSO)

    @staticmethod
    def campo(pai, rotulo, variavel=None, senha=False):
        texto(pai, rotulo, 10, negrito=True).pack(anchor="w", pady=(8, 4))
        entrada = ttk.Entry(pai, textvariable=variavel, show="*" if senha else "")
        entrada.pack(fill="x")
        return entrada

    def mostrar_entrada(self, cadastro=False, mensagem="", erro=False):
        self.limpar()
        capa = caixa(self.tela, NAV, width=340)
        capa.pack(side="left", fill="y")
        capa.pack_propagate(False)
        marca = caixa(capa, NAV)
        marca.pack(side="bottom", fill="x", padx=34, pady=36)
        texto(marca, "IFFAR  /  Computação", 10, NAV_TEXTO, NAV).pack(anchor="w")
        bloco = caixa(capa, NAV)
        bloco.pack(anchor="nw", pady=(70, 0), padx=34)
        texto(bloco, "IFFAR", 38, PAPEL, NAV, True).pack(anchor="w")
        texto(bloco, "CHAT", 38, "#a498ff", NAV, True).pack(anchor="w")
        texto(bloco, "Chat geral e conversas privadas", 11,
              NAV_TEXTO, NAV, wraplength=260, justify="left").pack(anchor="w", pady=18)

        lado = caixa(self.tela, FUNDO)
        lado.pack(side="left", fill="both", expand=True)
        cartao = caixa(lado, highlightthickness=1, highlightbackground=BORDA, highlightcolor=BORDA)
        cartao.place(relx=.5, rely=.5, anchor="center", relwidth=.78)
        form = caixa(cartao)
        form.pack(fill="both", padx=28, pady=18)
        texto(form, "Criar conta" if cadastro else "Entrar no chat",
              23, negrito=True).pack(anchor="w")
        rede = caixa(form)
        rede.pack(fill="x")
        endereco = caixa(rede)
        endereco.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.campo(endereco, "Servidor", self.host)
        coluna_porta = caixa(rede, width=110)
        coluna_porta.pack(side="right")
        self.campo(coluna_porta, "Porta", self.porta).configure(width=7)
        nome = self.campo(form, "Nome completo") if cadastro else None
        apelido = self.campo(form, "Apelido", self.apelido)
        data = self.campo(form, "Nascimento (DD/MM/AAAA)") if cadastro else None
        senha = self.campo(form, "Senha (6 letras ou números)" if cadastro else "Senha", senha=True)

        def confirmar():
            try:
                host, porta = self.endereco()
            except ValueError as falha:
                self.avisar(str(falha), True)
                return
            credencial = senha.get()
            apelido_atual = self.apelido.get()
            if cadastro:
                valores = (nome.get(), apelido_atual, data.get(), credencial)
                self.acao(lambda: self.cliente.cadastrar(host, porta, *valores),
                          lambda _: self.mostrar_entrada(mensagem="Conta criada. Agora entre no chat."))
            else:
                self.acao(lambda: self.cliente.entrar(host, porta, apelido_atual, credencial),
                          self.mostrar_chat)
        acoes = caixa(form)
        acoes.pack(fill="x", pady=(13, 2))
        botao(acoes, "Cadastrar" if cadastro else "Entrar", confirmar, "Principal").pack(side="left")
        botao(acoes, "Voltar" if cadastro else "Criar conta",
              lambda: None if self.ocupado else self.mostrar_entrada(not cadastro)).pack(side="left", padx=8)
        self.status_label = texto(form, "", 10, wraplength=400, justify="left", anchor="w")
        self.status_label.configure(textvariable=self.status)
        self.status_label.pack(fill="x", pady=(6, 0))
        if mensagem:
            self.avisar(mensagem, erro)
        senha.bind("<Return>", lambda _: confirmar())
        apelido.focus_set()

    def endereco(self):
        host = self.host.get().strip()
        try:
            porta = int(self.porta.get())
            if not host or not 1 <= porta <= 65535:
                raise ValueError
        except ValueError:
            raise ValueError("Informe um servidor e uma porta entre 1 e 65535.") from None
        return host, porta

    def mostrar_chat(self, uid):
        self.limpar()
        self.uid = str(uid)
        self.meu_apelido = self.apelido.get().strip()
        self.alvo = None
        self.online = {}
        self.amigos = {}
        self.nomes = {self.uid: self.meu_apelido}
        self.convites = set()
        self.nao_lidas = set()
        self.geral = []
        self.historicos = {}
        self.conversa_renderizada = None
        self.aba = "Conversas"
        self.ultima_lista = 0
        self.linhas = []

        nav = caixa(self.tela, NAV, width=330)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)
        topo = caixa(nav, NAV)
        topo.pack(fill="x", padx=22, pady=(24, 18))
        texto(topo, "IFFAR", 19, PAPEL, NAV, True).pack(side="left")
        texto(topo, "CHAT", 19, "#a498ff", NAV, True).pack(side="left")
        self.online_label = texto(nav, "", 10, NAV_TEXTO, NAV)
        self.online_label.pack(anchor="w", padx=22, pady=(0, 12))
        abas = caixa(nav, NAV)
        abas.pack(fill="x", padx=12)
        self.abas = {}
        for nome in ("Conversas", "Pessoas", "Convites"):
            controle = botao(abas, nome, lambda n=nome: self.selecionar_aba(n), "Nav")
            controle.pack(side="left", expand=True, fill="x", padx=2)
            self.abas[nome] = controle
        busca = caixa(nav, NAV)
        busca.pack(fill="x", padx=16, pady=(14, 10))
        texto(busca, "Buscar por apelido ou ID", 9, NAV_TEXTO, NAV).pack(anchor="w", pady=(0, 4))
        self.filtro = tk.StringVar()
        self.filtro.trace_add("write", lambda *_: self.render_lista())
        ttk.Entry(busca, textvariable=self.filtro).pack(fill="x")

        base = caixa(nav, NAV_PAINEL)
        base.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        scroll = ttk.Scrollbar(base, orient="vertical")
        self.lista = tk.Listbox(base, bg=NAV_PAINEL, fg=PAPEL, selectbackground=ACENTO,
                               selectforeground=PAPEL, font=fonte(base, 11), exportselection=False,
                               borderwidth=0, highlightthickness=1, highlightcolor="#a498ff",
                               highlightbackground=NAV_PAINEL, activestyle="none", yscrollcommand=scroll.set)
        self.lista.pack(side="left", fill="both", expand=True)
        scroll.configure(command=self.lista.yview)
        scroll.pack(side="right", fill="y")
        self.lista.bind("<<ListboxSelect>>", self.selecao)
        self.lista.bind("<Return>", self.selecao)
        self.vazio = texto(nav, "", 9, NAV_TEXTO, NAV)
        self.vazio.pack(anchor="w", padx=18)
        self.acoes_contato = caixa(nav, NAV)
        self.acoes_contato.pack(fill="x", padx=16, pady=(0, 10))
        rodape = caixa(nav, NAV)
        rodape.pack(fill="x", padx=16, pady=(0, 16))
        texto(rodape, f"{self.meu_apelido} • ID {self.uid}", 10, PAPEL, NAV, True,
              wraplength=215, justify="left").pack(anchor="w", pady=(0, 6))
        botao(rodape, "Meu perfil", lambda: self.ver_perfil(self.uid), "Nav").pack(side="left")
        botao(rodape, "Sair", self.sair, "Nav").pack(side="right")

        principal = caixa(self.tela, FUNDO)
        principal.pack(side="left", fill="both", expand=True)
        topo = caixa(principal)
        topo.pack(fill="x")
        texto_topo = caixa(topo)
        texto_topo.pack(side="left", padx=22, pady=17)
        self.titulo = texto(texto_topo, "", 21, negrito=True, wraplength=240, justify="left")
        self.titulo.pack(anchor="w")
        self.subtitulo = texto(texto_topo, "", 10, SUAVE)
        self.subtitulo.pack(anchor="w", pady=(4, 0))
        self.acoes_chat = caixa(topo)
        self.acoes_chat.pack(side="right", padx=14)

        painel = caixa(principal, FUNDO)
        painel.pack(fill="both", expand=True)
        barra = ttk.Scrollbar(painel)
        self.chat = tk.Text(painel, wrap="word", bg=FUNDO, fg=TINTA, relief="flat",
                            padx=24, pady=18, font=fonte(painel, 11), yscrollcommand=barra.set,
                            cursor="arrow", highlightthickness=0, takefocus=True)
        self.chat.pack(side="left", fill="both", expand=True)
        barra.configure(command=self.chat.yview)
        barra.pack(side="right", fill="y")
        self.chat.tag_configure("meta", foreground=SUAVE, font=fonte(painel, 9, True))
        self.chat.tag_configure("corpo", background=PAPEL, spacing1=3, spacing3=4,
                                lmargin1=10, lmargin2=10, rmargin=48)
        self.chat.tag_configure("propria", background="#e1ddff", spacing1=3, spacing3=4,
                                lmargin1=24, lmargin2=24, rmargin=28)
        self.chat.tag_configure("vazia", foreground=SUAVE, spacing1=12, spacing3=8)
        self.chat.configure(state="disabled")

        comp = caixa(principal)
        comp.pack(fill="x", side="bottom")
        self.status_label = texto(comp, "", 10, anchor="w", wraplength=485, justify="left")
        self.status_label.configure(textvariable=self.status)
        self.status_label.pack(fill="x", padx=18, pady=(8, 2))
        area = caixa(comp)
        area.pack(fill="x", padx=18, pady=(0, 14))
        self.entrada = ttk.Entry(area, font=fonte(area, 11))
        self.entrada.pack(side="left", fill="x", expand=True)
        botao(area, "Enviar", self.enviar, "Principal").pack(side="right", padx=(10, 0))
        self.entrada.bind("<Return>", lambda _: self.enviar())
        self.atualizar_cabecalho()
        self.render_chat()
        self.render_lista()
        self.avisar(f"Conectado a {self.host.get()}:{self.porta.get()}")
        self.entrada.focus_set()
        self.sincronizar()

    def nome(self, uid):
        return self.nomes.get(uid, f"Usuário {uid}")

    def selecionar_aba(self, nome):
        self.aba = nome
        self.filtro.set("")
        self.render_lista()

    def render_lista(self):
        if self.uid is None:
            return
        for nome, controle in self.abas.items():
            label = f"Convites ({len(self.convites)})" if nome == "Convites" and self.convites else nome
            controle.configure(text=label, style=("Principal" if nome == self.aba else "Nav") + ".TButton")
        self.online_label.configure(text=f"●  {len(self.online)} online")
        selecao = self.lista.curselection()
        escolhido = self.linhas[selecao[0]] if selecao else None
        filtro = self.filtro.get().strip().casefold()
        opcoes = {
            "Conversas": set(self.amigos),
            "Pessoas": set(self.online) - {self.uid},
            "Convites": self.convites,
        }
        ids = sorted(opcoes[self.aba], key=lambda uid: (self.nome(uid).casefold(), uid))
        self.linhas = [uid for uid in ids if filtro in self.nome(uid).casefold() or filtro in uid]
        if self.aba == "Conversas" and (not filtro or filtro in "chat geral"):
            self.linhas.insert(0, "")
        self.lista.delete(0, "end")
        for uid in self.linhas:
            if not uid:
                legenda = "   #   Chat geral"
            else:
                marcador = "●" if uid in self.online else "○"
                aviso = "   • nova" if uid in self.nao_lidas else ""
                legenda = f"   {marcador}   {self.nome(uid)}{aviso}"
            self.lista.insert("end", legenda)
        if self.aba == "Conversas":
            escolhido = self.alvo or ""
        if escolhido in self.linhas:
            self.lista.selection_set(self.linhas.index(escolhido))
        vazio = {"Conversas": "Sem conversas nesta busca", "Pessoas": "Nenhuma pessoa encontrada",
                 "Convites": "Nenhum convite encontrado"}
        self.vazio.configure(text=vazio[self.aba] if not self.linhas else "")
        self.botoes_contato()

    def selecao(self, _evento=None):
        selecionados = self.lista.curselection()
        if not selecionados:
            return
        alvo = self.linhas[selecionados[0]]
        if self.aba == "Conversas":
            if self.ocupado:
                self.render_lista()
                return
            self.abrir(alvo or None)
        else:
            self.botoes_contato()

    def botoes_contato(self):
        for componente in self.acoes_contato.winfo_children():
            componente.destroy()
        selecionados = self.lista.curselection()
        if self.aba == "Conversas" or not selecionados:
            return
        alvo = self.linhas[selecionados[0]]
        if self.aba == "Pessoas":
            if alvo in self.amigos:
                botao(self.acoes_contato, "Conversar", lambda: self.abrir_contato(alvo),
                      "Nav").pack(side="left")
            elif alvo in self.convites:
                botao(self.acoes_contato, "Ver convite",
                      lambda: self.abrir_convite(alvo), "Nav").pack(side="left")
            else:
                botao(self.acoes_contato, "Convidar", lambda: self.convite(alvo),
                      "Principal").pack(side="left")
            botao(self.acoes_contato, "Perfil", lambda: self.ver_perfil(alvo), "Nav").pack(side="right")
        else:
            botao(self.acoes_contato, "Aceitar", lambda: self.convite(alvo, True),
                  "Principal").pack(side="left")
            botao(self.acoes_contato, "Recusar", lambda: self.convite(alvo, False),
                  "Nav").pack(side="right")

    def abrir_convite(self, alvo):
        self.selecionar_aba("Convites")
        self.lista.selection_set(self.linhas.index(alvo))
        self.botoes_contato()

    def abrir_contato(self, alvo):
        if not self.ocupado:
            self.selecionar_aba("Conversas")
            self.abrir(alvo)

    def atualizar_cabecalho(self):
        alvo = self.alvo
        self.titulo.configure(text=self.nome(alvo) if alvo else "Chat geral")
        self.subtitulo.configure(text="Conversa privada" if alvo else "Conversa com quem está online")
        for componente in self.acoes_chat.winfo_children():
            componente.destroy()
        if alvo:
            botao(self.acoes_chat, "Perfil", lambda: self.ver_perfil(alvo)).pack(side="left", padx=3)
            botao(self.acoes_chat, "Alternar alertas", lambda: self.alternar_alertas(alvo)).pack(side="left")

    def alternar_alertas(self, alvo):
        self.acao(lambda: self.cliente.silenciar(alvo),
                  lambda _: self.avisar("Preferência de alertas alternada pelo servidor."))

    def abrir(self, alvo):
        if self.alvo == alvo:
            return
        self.alvo = alvo
        self.status.set("")
        self.atualizar_cabecalho()
        self.render_lista()
        self.render_chat()
        if alvo:
            self.acao(lambda: self.cliente.historico(alvo),
                      lambda quadro: self.atualizar_historico(alvo, quadro))
        self.entrada.focus_set()

    def atualizar_historico(self, alvo, quadro):
        novos = list(mensagens(quadro))
        if self.historicos.get(alvo) != novos:
            self.historicos[alvo] = novos
            if self.alvo == alvo:
                self.render_chat()

    def render_chat(self):
        dados = self.historicos.get(self.alvo, []) if self.alvo else self.geral
        inicio, fim = self.chat.yview()
        preservar_posicao = self.conversa_renderizada == self.alvo and fim < .99
        self.conversa_renderizada = self.alvo
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        if not dados:
            self.chat.insert("end", "Nenhuma mensagem nesta conversa.\n", "vazia")
        for uid, data, hora, minuto, corpo in dados:
            autor = "Você" if uid == self.uid else self.nome(uid)
            self.chat.insert("end", f"{autor}   ·   {data}  {hora}:{minuto}\n", "meta")
            self.chat.insert("end", corpo + "\n", "propria" if uid == self.uid else "corpo")
            self.chat.insert("end", "\n")
        if preservar_posicao:
            self.chat.yview_moveto(inicio)
        else:
            self.chat.see("end")
        self.chat.configure(state="disabled")

    def enviar(self):
        digitado = self.entrada.get()
        if self.uid is None or not digitado.strip() or self.ocupado:
            return
        alvo = self.alvo
        def concluiu(quadro):
            if self.entrada.get() == digitado:
                self.entrada.delete(0, "end")
            self.avisar("Mensagem enviada.")
            self.sincronizar()
        self.acao(lambda: self.cliente.enviar(digitado, alvo or ""), concluiu)

    def convite(self, alvo, aceitar=None):
        def concluiu(_):
            if aceitar is None:
                self.avisar(f"Convite enviado para {self.nome(alvo)}.")
            else:
                self.convites.discard(alvo)
                self.render_lista()
                self.avisar("Convite aceito." if aceitar else "Convite recusado.")
                self.ultima_lista = 0
            self.sincronizar()
        self.acao(lambda: self.cliente.tentar_convite(alvo, aceitar), concluiu)

    def ver_perfil(self, alvo):
        self.acao(lambda: self.cliente.perfil(alvo), self.mostrar_perfil)

    def mostrar_perfil(self, quadro):
        uid, nome, apelido, idade = quadro.parametros
        janela = tk.Toplevel(self.raiz)
        janela.title("Perfil")
        janela.transient(self.raiz)
        janela.configure(bg=PAPEL)
        base = caixa(janela)
        base.pack(fill="both", padx=24, pady=16)
        texto(base, nome, 17, negrito=True, wraplength=355).pack(anchor="w")
        texto(base, f"@{apelido}  ·  {idade} anos  ·  ID {uid}", 10, SUAVE).pack(anchor="w", pady=(3, 9))
        if uid == self.uid:
            novo_nome = self.campo(base, "Nome completo", tk.StringVar(value=nome))
            data = self.campo(base, "Nascimento (DD/MM/AAAA)")
            senha = self.campo(base, "Senha atual", senha=True)
            def salvar():
                valores = (novo_nome.get(), data.get(), senha.get())
                self.acao(lambda: self.cliente.atualizar(*valores),
                          lambda _: (janela.destroy(), self.avisar("Perfil atualizado.")),
                          erro=lambda falha: messagebox.showerror("Perfil", self.explicar(falha), parent=janela)
                          if janela.winfo_exists() else None)
            botao(base, "Salvar perfil", salvar, "Principal").pack(side="left", pady=(10, 0))
        botao(base, "Fechar", janela.destroy).pack(side="right", padx=(8, 0), pady=(10, 0))
        janela.bind("<Escape>", lambda _: janela.destroy())
        janela.focus_set()

    def sincronizar(self):
        if self.uid is None or self.consultando or self.ocupado:
            return
        alvo = self.alvo
        atualizar = time.monotonic() - self.ultima_lista >= 3
        self.consultando = True

        def retorno(valor, falha):
            self.consultando = False
            if self.uid is None:
                return
            if falha:
                if self.cliente.conectado:
                    self.avisar(self.explicar(falha), True)
                return
            geral, privada, avisos, contatos = valor
            if contatos:
                self.online, self.amigos = contatos
                self.nomes.update(self.online)
                self.nomes.update(self.amigos)
                self.ultima_lista = time.monotonic()
            nao_lidas = set(avisos.parametros)
            if nao_lidas != self.nao_lidas or contatos:
                self.nao_lidas = nao_lidas
                self.render_lista()
            if geral.parametros:
                self.geral.extend(mensagens(geral))
                if not self.alvo:
                    self.render_chat()
            if privada is not None:
                self.atualizar_historico(alvo, privada)

        self.rede.pedir(lambda: self.cliente.sincronizar(alvo, atualizar), retorno)

    def polling(self):
        if not self.fechando:
            self.sincronizar()
            self.raiz.after(1000, self.polling)

    @staticmethod
    def explicar(falha):
        if isinstance(falha, OSError):
            return "Falha de conexão. Confira o servidor, a porta e se o servidor está aberto."
        return getattr(falha, "mensagem", str(falha))

    def acao(self, operacao, sucesso, erro=None):
        if self.ocupado:
            return
        self.ocupado = True
        self.avisar("Aguarde…")
        def retorno(valor, falha):
            self.ocupado = False
            if falha:
                if erro:
                    erro(falha)
                self.avisar(self.explicar(falha), True)
            else:
                sucesso(valor)
        self.rede.pedir(operacao, retorno)

    def processar(self):
        if self.fechando:
            return
        while True:
            try:
                retorno, valor, falha = self.rede.resultados.get_nowait()
            except Empty:
                break
            retorno(valor, falha)
        for evento in self.rede.eventos():
            if self.uid is None:
                continue
            if isinstance(evento, tuple):
                if not self.cliente.conectado:
                    self.voltar("Conexão perdida. Confira o servidor e entre novamente.", True)
                continue
            if evento.codigo == 257:
                self.convites.add(evento.parametros[0])
                self.render_lista()
                self.avisar(f"{self.nome(evento.parametros[0])} enviou um convite.")
            elif evento.codigo == 259:
                alvo, aceito = evento.parametros
                resposta = "aceitou" if aceito == "VERDADEIRO" else "recusou"
                self.ultima_lista = 0
                self.avisar(f"{self.nome(alvo)} {resposta} seu convite.")
            elif evento.codigo == 32768:
                self.avisar(evento.parametros[-1], True)
        self.raiz.after(50, self.processar)

    def voltar(self, mensagem, erro=False):
        for janela in self.raiz.winfo_children():
            if isinstance(janela, tk.Toplevel):
                janela.destroy()
        self.uid = None
        self.mostrar_entrada(mensagem=mensagem, erro=erro)

    def sair(self):
        def desconectar():
            try:
                self.cliente.logout()
            except OSError:
                pass  # logout() fecha a sessão local mesmo se a rede caiu.
        self.acao(desconectar, lambda _: self.voltar("Você saiu do chat."))

    def encerrar(self):
        self.fechando = True
        self.rede.pedidos.put(None)
        self.raiz.destroy()


def main():
    parser = argparse.ArgumentParser(description="Cliente gráfico do IFFARCHAT")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta", type=int, default=42000)
    args = parser.parse_args()
    raiz = tk.Tk()
    InterfaceChat(raiz, args.host, args.porta)
    raiz.mainloop()


if __name__ == "__main__":
    main()
