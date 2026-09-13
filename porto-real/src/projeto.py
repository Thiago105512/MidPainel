"""Fachada de compatibilidade: o caso em edicao.

Ate R12 este arquivo ERA a obra: 159 tabelas e 53 funcoes descrevendo a mesma
residencia em Manaus. Enquanto foi assim, todo recurso novo nascia amarrado a
esse caso e teria de ser reescrito no projeto seguinte.

A partir de R13 a obra mora em projetos/porto_real.py e o motor em nucleo/.
Este arquivo continua existindo por uma razao pratica: as 35 pranchas, a
auditoria e o visualizador fazem `import projeto as pj`, e o criterio de aceite
da separacao e que NADA no desenho mude. Trocar o caso em edicao e trocar a
linha abaixo.
"""
from projetos.porto_real import *          # noqa: F401,F403
from projetos import porto_real as _caso

CASO = _caso
