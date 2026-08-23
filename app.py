from threading import Timer

from parte_04_imagens_web.app import abrir_navegador, app


if __name__ == "__main__":
    print("IFFagle: http://127.0.0.1:5000")
    Timer(1.0, abrir_navegador).start()
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=False)
