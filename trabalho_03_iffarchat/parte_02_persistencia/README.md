# Parte 2: persistência, fila e amizades

- esquema.iffarql: tabelas do chat no banco do Trabalho 2.
- repositorio.py: consulta os dados e grava cada lote de mudanças de uma vez.
- fila.py: atende um pedido por vez no banco.
- amizades.py: guarda convite, aceite, recusa e silenciamento de cada lado.

Com o projeto completo, rode os testes na pasta do IFFARCHAT:

```bash
python -m unittest tests.test_parte_02 -v
```

O IFFARQL em vendor/iffarql e o protocolo da Parte 1 são compartilhados pelo grupo.
