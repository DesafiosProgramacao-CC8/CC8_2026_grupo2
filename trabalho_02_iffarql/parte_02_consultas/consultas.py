#Rafael de Camargo 2023010914
#busca os registros que devem aparecer na consulta


class Consultas:
    def buscar(self, tabela, condicao=None):
        #sem onde, pega todos os registros da tabela
        #a árvore entrega em ordem crescente de id
        if condicao is None:
            return list(tabela.registros.em_ordem())

        #a parte 3 confere as colunas, os tipos e o comparador
        #isso também encontra erros quando a tabela está vazia
        aceita = condicao.preparar(tabela.tipos())

        #se for id == um número, podemos ir direto na avl
        #a função retorna None quando não é esse tipo de filtro
        identificador = condicao.id_exato()
        if identificador is not None:
            registro = tabela.registros.buscar(identificador)

            #o id pode ser válido na condição, mas não existir na tabela
            if registro is None:
                return []
            return [registro]

        #nos outros filtros precisamos olhar registro por registro
        encontrados = []
        for registro in tabela.registros.em_ordem():
            #aceita devolve True quando o registro atende ao onde
            if aceita(registro):
                encontrados.append(registro)

        #essa lista é só o resultado da consulta, não armazena a tabela
        #os dados da tabela continuam nos nós da árvore
        return encontrados

    def mostrar(self, banco, nome_tabela, condicao=None):
        #a parte 1 verifica se a tabela existe e devolve o objeto
        tabela = banco.obter_tabela(nome_tabela)
        registros = self.buscar(tabela, condicao)

        #monta os nomes das colunas na mesma ordem da criação
        #o id também aparece porque é a primeira coluna da tabela
        colunas = []
        for coluna in tabela.colunas:
            colunas.append(coluna.nome)

        #retorna os dados para a parte 4 montar o resultado
        #depois o terminal usa os tipos para formatar cada valor
        return colunas, registros, tabela.tipos()


#busca por id exato: O(log n), porque usa a avl balanceada
#sem filtro ou com outro filtro: O(n), porque percorre a árvore
#n é a quantidade de registros da tabela
