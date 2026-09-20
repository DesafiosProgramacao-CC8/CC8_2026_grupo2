# Parte 4 Julio

Esta parte coordena a execução, a atomicidade e os arquivos. Arquivos: comandos.py, motor.py e persistencia.py. O padrão segue a organização, os imports, pathlib e tratamento de exceções observados na parte_04_imagens_web do projeto anterior.

MotorIFFARQL.executar é a entrada central do sistema. Operações de alteração trabalham em uma cópia, validam e salvam antes de trocar o banco ativo. Persistencia grava JSON e reconstrói as árvores; comandos.py define objetos de comando com uma interface comum.

Estude a ordem de confirmação e os erros de carregamento no GUIA_DE_ESTUDO.md. Execute pela raiz com `python app.py`, junto das demais partes.
