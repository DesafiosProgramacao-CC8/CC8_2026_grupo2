# Guia de estudo da parte 4

## Responsabilidade

A parte 4 integra o sistema e impede que uma alteração inválida seja confirmada. Também salva o banco, carrega arquivos JSON e executa os comandos de um TXT com retorno por linha.

## Roteiro com o código aberto

1. Em comandos.py, mostre Comando, executar e altera_banco. Cada operação implementa a mesma interface, e o motor escolhe o objeto pelo nome da instrução. MostrarRegistros usa Consultas da parte do Rafael.
2. Em motor.py, mostre executar. O analisador devolve a instrução, consultas são executadas diretamente e alterações passam pelo fluxo de transação.
3. Aponte para deepcopy, comando.executar, validar_integridade, salvar e self.banco = candidato. Essa ordem é o centro da apresentação: primeiro prepara e verifica, depois grava, por último confirma em memória.
4. Em persistencia.py, mostre para_dados e salvar. O JSON inclui esquema, registros e proximo_id. A gravação usa arquivo auxiliar, flush, fsync e os.replace para preservar a versão anterior até a substituição.
5. Mostre carregar e de_dados. O arquivo é validado e as árvores são reconstruídas em outro banco. Tipos, ids e referências incorretas impedem a troca do estado ativo.
6. Volte a executar_arquivo. Cada linha do TXT chama executar e registra resultado ou erro. Linhas anteriores válidas permanecem, e linhas seguintes continuam. Carregamentos exigem sessão sem tabela criada.

## Exemplo para explicar

Uma atualização divide saldos pela coluna divisor. O primeiro registro tem divisor 2 e o segundo, zero. O primeiro cálculo acontece na cópia; quando o segundo falha, a cópia é descartada. Nem o primeiro registro do banco ativo nem o arquivo salvo ficam alterados.

## Perguntas e respostas

- O try/except do terminal garante atomicidade? Não. A atomicidade vem da cópia transacional e da confirmação somente depois da validação e da gravação.
- Se salvar falhar, o banco em memória muda? Não. A atribuição self.banco = candidato ocorre após salvar retornar com sucesso.
- O TXT inteiro é uma transação? Não. Cada linha interna é atômica. Um erro não desfaz os comandos anteriores, e a execução continua com identificação da linha.
- Como preserva o próximo id após excluir o maior registro? O contador proximo_id é persistido explicitamente e validado no carregamento.
- Por que não usar pickle? O JSON permite formato explícito, inspeção e validação dos dados, sem desserializar objetos executáveis de Python.
- Por que carregar em outro objeto? Para não danificar o banco ativo se o arquivo estiver incompleto, corrompido ou inconsistente.
- O que acontece antes de escolher um nome de arquivo? Alterações gravam em iffarql_temporario.json. SALVARBD e CARREGARBD definem o destino ativo.
- E se apagar todas as tabelas e depois carregar? Nesta interpretação do enunciado, ainda houve tabela criada na sessão; é necessário reiniciar.
- Quais propriedades ACID são atendidas? Atomicidade por comando, consistência pelos validadores e durabilidade pelo salvamento automático. Concorrência e isolamento entre processos foram dispensados na atividade e não são implementados.
- Qual é o custo da cópia? Cresce com o banco inteiro, assim como a serialização. É uma solução didática clara, com limitação para bases grandes.

## Conexões

O terminal do Rafael chama o motor. Thiago produz as instruções e os erros de linguagem. Geovane fornece o banco, as operações e a verificação de integridade. A parte 4 coordena esses objetos e devolve Resultado.
