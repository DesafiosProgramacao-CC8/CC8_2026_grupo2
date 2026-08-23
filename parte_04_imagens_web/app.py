import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from threading import Timer

from flask import Flask, redirect, render_template, request, send_file, url_for

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from parte_01_varredura.indexador import IFFagleIndexador

app = Flask(__name__)
indexador = IFFagleIndexador()
MENSAGEM = {"texto": "", "tipo": ""}


def contexto(consulta=None, resultados=None, tipo="todos", criterio="todos"):
    return {
        "pasta": indexador.pasta_indexada,
        "estatisticas": indexador.estatisticas,
        "mensagem": MENSAGEM["texto"],
        "tipo_mensagem": MENSAGEM["tipo"],
        "consulta": consulta,
        "resultados": resultados or [],
        "tipo": tipo,
        "criterio": criterio,
        "arvores": indexador.resumo_estruturas(),
    }


@app.route("/")
def inicio():
    return render_template("index.html", **contexto())


@app.route("/indexar", methods=["POST"])
def rota_indexar():
    pasta = request.form.get("pasta", "").strip()
    try:
        estatisticas = indexador.indexar_pasta(pasta)
        total = estatisticas["imagens"] + estatisticas["documentos"]
        MENSAGEM.update(texto=f"Indexação concluída: {total} arquivo(s) indexado(s).", tipo="sucesso")
    except Exception as erro:
        MENSAGEM.update(texto=str(erro), tipo="erro")
    return redirect(url_for("inicio"))


@app.route("/selecionar-pasta")
def selecionar_pasta():
    try:
        import tkinter as tk
        from tkinter import filedialog
        raiz = tk.Tk()
        raiz.withdraw()
        raiz.attributes("-topmost", True)
        pasta = filedialog.askdirectory(title="Selecione a pasta que será indexada")
        raiz.destroy()
        if pasta:
            estatisticas = indexador.indexar_pasta(pasta)
            total = estatisticas["imagens"] + estatisticas["documentos"]
            MENSAGEM.update(texto=f"Pasta selecionada. {total} arquivo(s) indexado(s).", tipo="sucesso")
    except Exception as erro:
        MENSAGEM.update(texto=f"Não foi possível abrir o seletor: {erro}", tipo="erro")
    return redirect(url_for("inicio"))


@app.route("/buscar")
def buscar():
    consulta = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "todos")
    criterio = request.args.get("criterio", "todos")

    if not indexador.pasta_indexada:
        MENSAGEM.update(texto="Primeiro selecione e indexe uma pasta.", tipo="erro")
        resultados = []
    else:
        MENSAGEM.update(texto="", tipo="")
        resultados = indexador.buscar(consulta, tipo, criterio)

    return render_template(
        "index.html",
        **contexto(consulta=consulta, resultados=resultados, tipo=tipo, criterio=criterio),
    )


@app.route("/visualizar/<id_arquivo>")
def visualizar(id_arquivo):
    arquivo = indexador.arquivos.get(id_arquivo)
    if arquivo is None:
        return "Arquivo não encontrado no índice.", 404
    if not os.path.isfile(arquivo.caminho):
        return "O arquivo não existe mais no disco.", 404
    try:
        return send_file(arquivo.caminho, as_attachment=False)
    except PermissionError:
        return "Sem permissão para acessar o arquivo.", 403


@app.route("/abrir-local/<id_arquivo>")
def abrir_local(id_arquivo):
    arquivo = indexador.arquivos.get(id_arquivo)
    if arquivo is None:
        return "Arquivo não encontrado no índice.", 404
    try:
        if sys.platform.startswith("win"):
            os.startfile(arquivo.caminho)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", arquivo.caminho])
        else:
            subprocess.Popen(["xdg-open", arquivo.caminho])
        MENSAGEM.update(texto=f'Arquivo "{arquivo.nome}" aberto no sistema.', tipo="sucesso")
    except Exception as erro:
        MENSAGEM.update(texto=f"Não foi possível abrir o arquivo: {erro}", tipo="erro")
    return redirect(request.referrer or url_for("inicio"))


def abrir_navegador():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    print("IFFagle: http://127.0.0.1:5000")
    Timer(1.0, abrir_navegador).start()
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=False)
