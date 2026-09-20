# Guia de estudo da parte 3

## Responsabilidade

A parte 3 transforma uma linha digitada em uma instrução estruturada e define como cada tipo de dado se comporta. Não executa Python recebido do usuário. O reconhecimento usa tokens e uma gramática própria.

## Roteiro com o código aberto

1. Em lexico.py, mostre Token e tokenizar. Explique que nome, número, texto entre aspas e símbolo são categorias diferentes. O texto "ONDE" ou "+" entre aspas continua sendo um valor, não uma palavra reservada ou operador.
2. Em analisador.py, mostre Instrucao e analisar. O primeiro comando define quais elementos a gramática espera. CRIATABELA coleta colunas; INSERIREM coleta valores; ATUALIZATABELA coleta os blocos COM; os demais comandos recebem seus parâmetros.
3. Mostre primaria, termo e expressao. Parênteses e sinais unários são tratados primeiro, depois multiplicação/divisão e por último soma/subtração. condicao lê somente um comparador e rejeita sobras como E e OU.
4. Em expressoes.py, mostre a interface Expressao e as subclasses. preparar verifica as colunas e os tipos, devolvendo a avaliação pronta para usar em cada registro. Isso permite denunciar uma coluna inválida até numa tabela vazia.
5. Em tipos.py, mostre TipoDado, TipoTexto e TipoData. O método operar tem a mesma interface, mas soma números, concatena texto ou desloca dias conforme o objeto concreto. Esse é o principal exemplo de polimorfismo dinâmico.
6. Termine em TipoData.ordinal e de_ordinal. Explique o calendário de 365 dias, fevereiro sempre com 28 dias e as comparações cronológicas.

## Exemplo para explicar

ATUALIZATABELA clientes COM idade = idade + 1 ONDE id == 2 vira uma instrução de atualização, com a coluna idade recebendo uma expressão de soma e uma condição de igualdade. O tipo de idade é validado antes da avaliação. Para o registro selecionado, a expressão lê o valor atual e soma 1.

## Perguntas e respostas

- Por que não usar split por espaços? Porque textos podem ter espaços e símbolos dentro das aspas, e os operadores podem aparecer sem espaços. Os tokens preservam essas diferenças.
- Por que não usar eval? Porque IFFARQL possui gramática e tipos próprios, e a entrada não deve executar código arbitrário de Python.
- Onde está o polimorfismo? Nas subclasses de TipoDado e Expressao. A chamada usa a interface comum; o objeto concreto determina a implementação.
- Como compara datas? Converte para um número de dias no calendário didático. Comparar diretamente dd/mm/aaaa como texto daria resultados errados.
- Como funciona 28/02/2024 + 1? Retorna 01/03/2024, pois a atividade desconsidera anos bissextos.
- Decimal e inteiro podem ser misturados? Nesta implementação, não. Operações exigem tipos iguais; a exceção é DATA com quantidade inteira de dias.
- O que ocorre em -7 / 2? O resultado inteiro é -3, truncado em direção a zero. A convenção está documentada.
- String vazia é nula? Não. "" é um TEXTO válido. Palavras NULL, NULO e None sem aspas são rejeitadas.
- Por que existe dica_tipo? Para resolver literais entre aspas em contexto de TEXTO ou DATA, usando o tipo da coluna ou do outro operando.
- Pode haver dois comparadores no ONDE? Não. A condição aceita um só; múltiplos COM não significam múltiplos filtros.

## Conexões

Geovane usa os tipos e as expressões para validar inserções e atualizações. Rafael usa a condição preparada e tipo.formatar. Júlio recebe a Instrucao e escolhe o comando que será executado.
