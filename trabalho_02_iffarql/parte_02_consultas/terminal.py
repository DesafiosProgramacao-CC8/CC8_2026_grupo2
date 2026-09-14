#Rafael de Camargo 2023010914
#recebe os comandos e mostra as respostas do sistema


class Terminal:
    def __init__(self, sistema):
        #guarda o motor da parte 4, que integra as outras partes
        self.sistema = sistema

    def iniciar(self):
        print("IFFARQL - banco de dados pelo terminal")
        print("Digite AJUDA para ver os comandos ou SAIR para encerrar.")

        #repete até o usuário sair ou encerrar a entrada
        while True:
            try:
                comando = input("IFFARQL> ").strip()
            except EOFError:
                #também permite encerrar com ctrl+d ou ctrl+z
                print("\nSistema encerrado.")
                break
            except KeyboardInterrupt:
                print("\nEntrada cancelada. Digite SAIR para encerrar.")
                continue

            #ignora uma linha vazia
            if not comando:
                continue

            #sair e ajuda são opções do terminal
            if comando == "SAIR":
                print("Sistema encerrado. As alterações já foram salvas.")
                break
            if comando == "AJUDA":
                self.mostrar_ajuda()
                continue

            try:
                #o motor interpreta, valida e executa o comando
                resultado = self.sistema.executar(comando)
                self.mostrar_resultado(resultado)
            except Exception as erro:
                #avisa o problema e permite digitar outro comando
                #o motor só confirma alterações que terminaram sem erro
                print("Erro:", erro)

    def mostrar_resultado(self, resultado):
        #consultas devolvem os nomes das colunas, mesmo sem registros
        if resultado.colunas:
            self.mostrar_tabela(resultado)

        if resultado.mensagem:
            print(resultado.mensagem)

        #um arquivo iffarql pode devolver o resultado de várias linhas
        for linha, item in resultado.detalhes:
            print("Linha", linha)
            if isinstance(item, str):
                print("Erro:", item)
            else:
                self.mostrar_resultado(item)

    def mostrar_tabela(self, resultado):
        #a primeira linha contém os nomes das colunas
        linhas = [resultado.colunas]

        for registro in resultado.registros:
            linha = []
            for coluna in resultado.colunas:
                #cada tipo sabe se apresentar, como data e booleano
                tipo = resultado.tipos[coluna]
                texto = tipo.formatar(registro[coluna])
                linha.append(self.limpar_texto(texto))
            linhas.append(linha)

        #descobre o espaço necessário para alinhar cada coluna
        larguras = []
        for coluna in range(len(resultado.colunas)):
            maior = 0
            for linha in linhas:
                maior = max(maior, len(linha[coluna]))
            larguras.append(maior)

        for numero, linha in enumerate(linhas):
            partes = []
            for coluna, valor in enumerate(linha):
                partes.append(valor.ljust(larguras[coluna]))
            print(" | ".join(partes))
            if numero == 0:
                print("-+-".join("-" * largura for largura in larguras))

    def limpar_texto(self, texto):
        #não deixa uma quebra de linha ou comando de controle bagunçar a saída
        limpo = ""
        for caractere in texto:
            if ord(caractere) < 32 or ord(caractere) == 127:
                limpo += "\\x" + format(ord(caractere), "02x")
            else:
                limpo += caractere
        return limpo

    def mostrar_ajuda(self):
        print('CRIATABELA clientes ( nome TEXTO idade INTEIRO )')
        print('INSERIREM clientes VALOR ( "Rafael" 21 )')
        print('MOSTRADADOSDE clientes ONDE id == 1')
        print('ATUALIZATABELA clientes COM idade = idade + 1 ONDE id == 1')
        print('APAGADADOSDE clientes ONDE id == 1')
        print('APAGATABELA clientes')
        print('SALVARBD banco.json')
        print('CARREGARBD banco.json')
        print('CARREGARIFFARQL exemplos/demonstracao.iffarql.txt')
        print('Tipos: INTEIRO, DECIMAL, BOOLEANO, TEXTO e DATA.')
        print('Booleanos: VERDADEIRO ou FALSO. Datas: "dd/mm/aaaa".')
