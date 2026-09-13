#!/usr/bin/env python3
"""ESCOPO — as 155 secoes da especificacao, classificadas, e as etapas que as fecham.

O plano tambem e modelo. Se ele vivesse so em prosa, nao daria para auditar se
uma etapa cobre o que promete, nem para saber quanto falta. Aqui cada secao tem
uma situacao declarada e cada etapa declara quais secoes fecha — e uma
verificacao confere que nenhuma secao ficou orfa e nenhuma etapa promete secao
que nao existe.

SITUACOES
  FEITO  ja entregue no caderno atual (R12), total ou parcialmente
  AUTO   eu construo sozinho, sem dado externo: e so matematica, norma e codigo
  HIP    eu construo a estrutura, mas um numero vem de fora (preco, maquina,
         ensaio, fornecedor). Entra marcado (H) e vira pendencia declarada
  BLOQ   depende do mundo externo: formato proprietario, hardware, servidor,
         historico real. Eu entrego o CONTRATO (esquema + adaptador + teste)
"""
from __future__ import annotations

# (numero, titulo, situacao, etapa, nota)
SECOES = [
    (1, "Tipos de projeto", "AUTO", "E0", "deixa de ser uma casa e passa a ser um caso do motor"),
    (2, "Cadastro do projeto", "AUTO", "E0", ""),
    (3, "Entradas / importacao", "BLOQ", "E18", "DXF/IFC/CSV/JSON/OBJ/STL sim; DWG/RVT/SKP sao proprietarios"),
    (4, "Reconhecimento automatico da planta", "BLOQ", "E23", "visao computacional treinada"),
    (5, "Configurador automatico", "AUTO", "E7", ""),
    (6, "Modelagem parametrica", "FEITO", "—", "e o nucleo do projeto desde R00"),
    (7, "Eixos / niveis / grids", "FEITO", "E0", "malha de 600 mm e EIXOS_LOCACAO; falta grid inclinado"),
    (8, "Biblioteca de perfis", "AUTO", "E1", "propriedades pela teoria da linha media"),
    (9, "Perfis LSF", "AUTO", "E1", ""),
    (10, "Materiais", "AUTO", "E2", ""),
    (11, "Normas", "FEITO", "E2", "16 normas ja citadas; falta o seletor por pais"),
    (12, "Cargas", "AUTO", "E3", ""),
    (13, "Gerador de vento", "AUTO", "E3", "NBR 6123 completa: S1, S2, S3, Cpe, Cpi"),
    (14, "Combinacoes", "AUTO", "E4", "NBR 8681"),
    (15, "Analise estrutural", "AUTO", "E5", "rigidez direta 3D + P-Delta"),
    (16, "Caminho de cargas", "AUTO", "E5", ""),
    (17, "Resultados visuais", "AUTO", "E19", ""),
    (18, "Diagramas", "AUTO", "E5", ""),
    (19, "Comparacao automatica de perfis", "AUTO", "E16", ""),
    (20, "Explicacao de decisoes", "AUTO", "*", "requisito TRANSVERSAL, nao etapa"),
    (21, "Otimizacao multiobjetivo", "AUTO", "E16", ""),
    (22, "Padronizacao automatica", "AUTO", "E16", ""),
    (23, "Painelizacao automatica", "AUTO", "E7", ""),
    (24, "Divisao inteligente de paineis", "AUTO", "E7", ""),
    (25, "Aberturas", "AUTO", "E7", ""),
    (26, "Vergas", "AUTO", "E7", ""),
    (27, "Trelicas", "AUTO", "E8", ""),
    (28, "Contraventamento", "AUTO", "E8", ""),
    (29, "Shear wall", "AUTO", "E8", ""),
    (30, "Ligacoes", "AUTO", "E9", ""),
    (31, "Gerador automatico de ligacoes", "AUTO", "E9", ""),
    (32, "Acessibilidade de montagem", "AUTO", "E9", "verificacao geometrica do bocal da parafusadeira"),
    (33, "Deteccao de montagem impossivel", "AUTO", "E15", ""),
    (34, "Sistema de regras fisicas", "FEITO", "E21", "48 funcoes, 238 condicoes"),
    (35, "Auto-correcao", "AUTO", "E21", ""),
    (36, "Fundacoes", "AUTO", "E9", ""),
    (37, "Ancoragem", "AUTO", "E9", ""),
    (38, "Piso", "FEITO", "E6", "camadas ja declaradas; falta vibracao"),
    (39, "Cobertura", "FEITO", "E8", ""),
    (40, "Paredes", "FEITO", "—", "familias de vedacao, PR-12 e PR-13"),
    (41, "Biblioteca de composicoes", "FEITO", "—", ""),
    (42, "Termica", "FEITO", "—", "desempenho.py: U, FSo, ponte termica"),
    (43, "Acustica", "FEITO", "—", "Rw composto e reverberacao"),
    (44, "Incendio", "HIP", "E2", "TRRF depende de ensaio tabelado do fabricante"),
    (45, "MEP", "FEITO", "—", "PR-26 a PR-29"),
    (46, "Clash detection", "AUTO", "E10", ""),
    (47, "Furos em perfis", "FEITO", "E10", "FURACAO e PENETRACOES ja verificadas"),
    (48, "Detalhamento por peca", "AUTO", "E10", ""),
    (49, "Identificacao", "AUTO", "E10", ""),
    (50, "QR code / datamatrix", "AUTO", "E10", ""),
    (51, "Marcacao direta", "HIP", "E13", "depende do cabecote da maquina"),
    (52, "Shop drawings", "AUTO", "E20", ""),
    (53, "Exploded view", "AUTO", "E19", ""),
    (54, "Desenho colorido de montagem", "AUTO", "E19", ""),
    (55, "Modo de montagem", "AUTO", "E15", ""),
    (56, "Sequenciamento automatico", "AUTO", "E15", ""),
    (57, "Animacao de montagem", "AUTO", "E19", ""),
    (58, "Desmontagem", "AUTO", "E15", ""),
    (59, "BOM", "AUTO", "E12", ""),
    (60, "Quantitativos", "AUTO", "E12", ""),
    (61, "Nesting de perfis", "AUTO", "E11", ""),
    (62, "Nesting de chapas", "AUTO", "E11", ""),
    (63, "Otimizacao de bobina", "AUTO", "E11", ""),
    (64, "Rastreabilidade de bobina", "HIP", "E13", "certificado vem da usina"),
    (65, "Heat number", "HIP", "E13", ""),
    (66, "Passaporte digital da peca", "HIP", "E13", ""),
    (67, "CNC", "AUTO", "E13", "formato neutro sim; dialeto da maquina e (H)"),
    (68, "Perfiladeiras", "HIP", "E13", ""),
    (69, "Producao (status)", "AUTO", "E13", ""),
    (70, "Linha de producao", "HIP", "E13", "tempos reais vem do chao de fabrica"),
    (71, "Tempo de producao", "HIP", "E13", ""),
    (72, "Balanceamento de linha", "HIP", "E13", ""),
    (73, "OEE", "HIP", "E13", ""),
    (74, "Controle de qualidade", "AUTO", "E13", ""),
    (75, "Controle de tolerancias", "AUTO", "E13", ""),
    (76, "Visao computacional", "BLOQ", "E23", ""),
    (77, "Laser / scanner", "BLOQ", "E23", ""),
    (78, "As-designed x as-built", "BLOQ", "E23", ""),
    (79, "Revisoes", "FEITO", "E17", "13 revisoes registradas"),
    (80, "Freeze de revisao", "AUTO", "E17", ""),
    (81, "Impact analysis", "AUTO", "E17", "viavel porque tudo e funcao do modelo"),
    (82, "Change order", "AUTO", "E17", ""),
    (83, "Comparacao de revisoes", "AUTO", "E17", ""),
    (84, "Estoque", "HIP", "E12", ""),
    (85, "Sobras", "AUTO", "E11", "nesting consulta sobras antes de barra nova"),
    (86, "Multiproject nesting", "AUTO", "E11", ""),
    (87, "Compras / RFQ", "AUTO", "E12", "documento sim; preco e (H)"),
    (88, "Fornecedores", "HIP", "E12", ""),
    (89, "Comparador de fornecedores", "HIP", "E12", ""),
    (90, "Equivalencia de produtos", "AUTO", "E12", "criterio estrutural e calculavel"),
    (91, "Landed cost", "HIP", "E12", ""),
    (92, "Custos", "HIP", "E12", ""),
    (93, "Curva ABC", "AUTO", "E12", ""),
    (94, "Cenarios", "AUTO", "E12", ""),
    (95, "Simulacao de risco", "AUTO", "E12", "Monte Carlo em Python puro"),
    (96, "Logistica", "AUTO", "E14", ""),
    (97, "Container loading", "AUTO", "E14", ""),
    (98, "Packing list", "AUTO", "E14", ""),
    (99, "Centro de gravidade", "AUTO", "E14", ""),
    (100, "Pontos de icamento", "AUTO", "E14", ""),
    (101, "Simulacao de icamento", "AUTO", "E14", "usa o mesmo solver da E5"),
    (102, "Limites de transporte", "HIP", "E14", "legislacao rodoviaria por regiao"),
    (103, "Visualizador 2D", "FEITO", "E19", "R12: prancha navegavel"),
    (104, "Visualizador 3D", "FEITO", "E19", "R11: 8 cenas, sol real, corte"),
    (105, "Raio-X", "AUTO", "E19", ""),
    (106, "Filtros", "AUTO", "E19", ""),
    (107, "Selecao de elemento", "FEITO", "E19", "ficha ja existe; falta o dado industrial"),
    (108, "Dashboard", "AUTO", "E19", ""),
    (109, "Pranchas", "FEITO", "E20", "A1 pronto; A0 a A4 e parametrizacao"),
    (110, "Documentacao", "AUTO", "E20", ""),
    (111, "AR / realidade aumentada", "BLOQ", "E23", ""),
    (112, "Modo obra", "BLOQ", "E23", "precisa de app movel"),
    (113, "Modo offline", "BLOQ", "E23", ""),
    (114, "Fotos vinculadas", "BLOQ", "E23", ""),
    (115, "Punch list", "BLOQ", "E23", ""),
    (116, "Diario de obra", "BLOQ", "E23", ""),
    (117, "As-built", "BLOQ", "E23", ""),
    (118, "Digital twin", "BLOQ", "E23", ""),
    (119, "Manutencao", "AUTO", "E20", "plano de manutencao sim; operacao e BLOQ"),
    (120, "Sensoriamento", "BLOQ", "E23", ""),
    (121, "Sustentabilidade", "HIP", "E22", "fator de CO2e por kg de aco"),
    (122, "Design for disassembly", "AUTO", "E22", ""),
    (123, "Inteligencia artificial", "AUTO", "*", "sou eu; o requisito e ser auditavel, nao caixa-preta"),
    (124, "Engenharia generativa", "AUTO", "E16", ""),
    (125, "Aprendizado com projetos anteriores", "BLOQ", "E23", "precisa de historico real"),
    (126, "Biblioteca de detalhes", "AUTO", "E20", ""),
    (127, "Templates", "AUTO", "E0", ""),
    (128, "Configurador modular", "AUTO", "E0", ""),
    (129, "Regras por fabricante", "HIP", "E13", ""),
    (130, "Regras por perfiladeira", "HIP", "E13", ""),
    (131, "Controle de usuarios", "BLOQ", "E23", "precisa de servidor"),
    (132, "Permissoes", "BLOQ", "E23", ""),
    (133, "Aprovacoes", "BLOQ", "E23", ""),
    (134, "Assinatura digital", "BLOQ", "E23", ""),
    (135, "Auditoria (log de alteracoes)", "AUTO", "E17", "o git ja registra quem, o que e quando"),
    (136, "API", "BLOQ", "E23", ""),
    (137, "Banco de dados", "AUTO", "E18", "esquema + SQLite; 28 entidades"),
    (138, "Exportacao", "AUTO", "E18", "menos DWG e RVT"),
    (139, "Importacao", "AUTO", "E18", "menos DWG, RVT e SKP"),
    (140, "Verificacao automatica final", "AUTO", "E21", ""),
    (141, "Motor de erros", "FEITO", "E21", "ERRO / ATENCAO / NOTA ja existem"),
    (142, "Scoring do projeto", "AUTO", "E21", ""),
    (143, "Fabricability score", "AUTO", "E21", ""),
    (144, "Assemblability score", "AUTO", "E21", ""),
    (145, "Resiliencia de fornecimento", "HIP", "E12", ""),
    (146, "Disponibilidade de material", "HIP", "E12", ""),
    (147, "Otimizacao global", "AUTO", "E16", ""),
    (148, "Exemplo de decisao global", "AUTO", "E16", ""),
    (149, "Simulacao what-if", "AUTO", "E16", ""),
    (150, "Configuracao visual", "AUTO", "E19", ""),
    (151, "Modos de visualizacao", "AUTO", "E19", ""),
    (152, "Modo educacional", "AUTO", "E19", ""),
    (153, "Modo especialista", "AUTO", "E19", ""),
    (154, "Modo executivo", "AUTO", "E19", ""),
    (155, "Objetivo final do sistema", "AUTO", "E21", "e a soma das etapas, nao uma etapa"),
]


# ---------------------------------------------------------------- etapas
# (codigo, bloco, titulo, ciclos, depende, entrega, aceite)
#
# "ciclo" = uma rodada completa de trabalho meu: escrever, construir as 35
# pranchas, rodar a auditoria inteira, corrigir o que ela acusar e commitar.
# Nenhuma etapa se declara pronta sem a auditoria verde — e cada etapa ENTREGA
# verificacoes novas, que passam a rodar em todas as seguintes.
ETAPAS = [
    ("E0", "I", "Separar o motor do caso", 2, "—",
     "projeto.py tem 159 tabelas e 53 funcoes descrevendo UMA casa. Vira nucleo/ "
     "(motor, sem geometria de caso) + projetos/porto_real/ (dados). Entram "
     "PROJECT_ID, unidades, moeda, responsaveis, tipologia e templates.",
     "As 35 pranchas saem IDENTICAS byte a byte ao commit anterior. E o melhor "
     "teste de regressao possivel: se o motor mudou o desenho, o motor esta errado."),
    ("E1", "I", "Perfis formados a frio", 2, "E0",
     "C, Ue, U, Z, Sigma, Omega, Hat, L. Propriedades pela teoria da linha media: "
     "A, Ix, Iy, Ixy, J, Cw, xo, rx, ry, Wx, Wy, peso/m. Famılias LSF (stud, track, "
     "joist, rafter, jamb, blocking, strap, hat channel).",
     "Conferencia contra os valores tabelados da NBR 6355 para os perfis "
     "padronizados, peca por peca, com tolerancia declarada."),
    ("E2", "I", "Materiais, revestimentos e normas", 1, "E1",
     "ZAR 230/250/280/345 com fy, fu, E, G, Poisson, densidade. Revestimentos Z120 "
     "a Z350 e AZ150 com massa e espessura de camada. Seletor de norma por pais. "
     "TRRF de incendio como tabela declarada (H).",
     "Massa de zinco confere com a espessura declarada; nenhum perfil usa aco sem "
     "fy e fu declarados."),
    ("E3", "II", "Cargas e gerador de vento", 2, "E2",
     "NBR 6120 por uso. NBR 6123 completa: S1 topografia, S2 (b, Fr, p) por "
     "rugosidade/classe/altura, S3 estatistico, Vk, q, Cpe por zona de fachada e "
     "cobertura, Cpi, acao em partes. Cargas pontual/linear/distribuida/trapezoidal.",
     "Vk e q conferidos contra exemplo resolvido da norma; a soma das pressoes de "
     "fachada fecha com a forca global."),
    ("E4", "II", "Combinacoes", 1, "E3",
     "NBR 8681: ELU normal e excepcional, ELS quase-permanente/frequente/rara, com "
     "psi0/psi1/psi2 por tipo de acao. Envelopes e filtros por situacao.",
     "Nenhuma acao fica fora de combinacao; o envelope contem todas as combinacoes "
     "individuais por construcao."),
    ("E5", "II", "Solver de barras", 3, "E4",
     "Rigidez direta 3D, 12 graus de liberdade por barra: matriz local, rotacao, "
     "montagem, apoios, solucao, esforcos, reacoes. Segunda ordem por matriz "
     "geometrica (P-Delta). Diagramas N, Vx, Vy, Mx, My, T, deslocamento. "
     "Caminho de cargas da cobertura a fundacao.",
     "Casos com solucao fechada: viga biapoiada, engastada, balanco, portico. "
     "Equilibrio global: soma das reacoes = soma das cargas, em cada combinacao."),
    ("E6", "II", "Verificacao NBR 14762", 3, "E5",
     "Metodo da resistencia direta e largura efetiva. Compressao: flambagem global "
     "por flexao, torcao e flexo-torcao; local; distorcional. Flexao: FLT, local, "
     "distorcional. Cisalhamento. Enrugamento da alma. Interacao N+M. Flecha e "
     "vibracao de piso.",
     "Cada peca sai com utilizacao %, o modo critico nomeado e a clausula citada. "
     "Nenhuma peca fica sem verificacao — ausencia de verificacao vira ERRO."),
    ("E7", "III", "Painelizacao", 2, "E6",
     "Cada parede vira PANEL_ID: track inferior e superior, studs, king/jack/cripple, "
     "header, sill, blocking, bridging. Aberturas geram reforco automatico. Vergas "
     "dimensionadas por vao e carga (simples, dupla, box, back-to-back). Divisao por "
     "peso, transporte e icamento.",
     "Nenhum stud sem apoio; nenhuma abertura sem reforco; todo painel abaixo do "
     "peso e da dimensao maxima declarados."),
    ("E8", "III", "Contraventamento, shear wall e trelicas", 2, "E7",
     "Fitas em X e K, paineis OSB, portal frame. Shear wall: resistencia, "
     "comprimento efetivo, fixadores, overturning, uplift, hold-down. Trelicas "
     "Fink, Howe, Pratt, Warren, Scissor, Mono, Attic.",
     "Estabilidade global em cada direcao e em cada combinacao de vento; o uplift "
     "de cada hold-down fecha com a reacao do solver."),
    ("E9", "III", "Ligacoes, fundacao e ancoragem", 2, "E8",
     "Parafusos auto-atarraxantes: cisalhamento, esmagamento, arrancamento, "
     "rasgamento, tracao. Gerador automatico de tipo, quantidade, diametro, "
     "espacamento e posicao. Radier/sapata/baldrame com reacoes reais. Chumbadores "
     "com profundidade e distancia de borda. Acessibilidade da parafusadeira.",
     "Nenhuma ligacao com folga menor que a minima normativa; nenhum parafuso em "
     "posicao onde a parafusadeira nao entra."),
    ("E10", "III", "Pecas, furacao, numeracao e clash", 2, "E9",
     "Cada peca ganha ID, perfil, aco, comprimento, peso, angulo, cortes, furos, "
     "notches, dobras e marcacao. Numeracao ST/TR/JO/RF/HD/AN/SC. QR por peca. "
     "Clash estrutura x MEP x arquitetura x revestimento.",
     "Zero clash nao resolvido; todo furo dentro da zona permitida; todo ID unico e "
     "estavel entre revisoes."),
    ("E11", "IV", "Nesting", 2, "E10",
     "1D: barras de 6.000 mm, consulta as SOBRAS antes de abrir barra nova. 2D: "
     "guillotine para OSB, gesso e cimenticia. Bobina: largura, espessura, metros e "
     "kg por perfil. Nesting entre projetos.",
     "Aproveitamento declarado e conferido: soma dos comprimentos + perda = soma "
     "das barras. Nenhuma peca maior que a barra."),
    ("E12", "IV", "BOM, quantitativos e custo", 2, "E11",
     "BOM da peca ao m2. Quantitativos de aco, placas, parafusos, chumbadores, "
     "isolamento, membranas. Landed cost (produto + frete + tributo + despacho). "
     "Curva ABC. Cenarios A/B/C. Monte Carlo para cambio, aco e frete.",
     "O peso do BOM fecha com o peso do modelo 3D dentro de 1 %. Todo preco entra "
     "marcado (H) e listado como pendencia."),
    ("E13", "IV", "CNC, fabricacao e QC", 2, "E12",
     "Exportacao neutra (CSV/JSON) com comprimento, cortes, furos, notches, dimples, "
     "slots e marcacao, mais um dialeto NC em texto. Status DESIGN a INSTALLED. "
     "Tempos, balanceamento de linha, OEE. QC com tolerancias por dimensao. "
     "Rastreabilidade bobina → heat number → peca → painel → obra.",
     "Toda peca exportada volta a geometria original quando reimportada. Nenhuma "
     "peca fora da capacidade da maquina declarada."),
    ("E14", "IV", "Logistica", 2, "E13",
     "Peso, volume, pallet, crate. Container loading 20', 40', 40HC em 3D com "
     "sequencia de carga. Centro de gravidade por painel, modulo e container. "
     "Pontos de icamento com carga por ponto e sling angle. Simulacao de icamento "
     "pelo solver da E5. Limites rodoviarios (H).",
     "O centro de gravidade calculado fecha com a soma dos momentos das pecas; "
     "nenhum painel icado ultrapassa a flecha admissivel no icamento."),
    ("E15", "V", "Montagem", 2, "E14",
     "Sequenciamento topologico com regras de estabilidade, acesso e seguranca. "
     "Passo a passo com peca, posicao, orientacao, fixador e ferramenta. Deteccao "
     "de montagem impossivel com sugestao de correcao. Sequencia inversa de "
     "desmontagem.",
     "Em nenhum passo a estrutura fica instavel; nenhuma peca e instalada em "
     "posicao que outra ja instalada impeca."),
    ("E16", "V", "Otimizacao", 2, "E15",
     "Comparacao de perfis por peca com alternativas e motivo. Padronizacao: "
     "reduzir variedade mantendo seguranca. Otimizacao multiobjetivo ponderada "
     "(custo, peso, SKU, desperdicio, tempo de montagem, carbono). What-if. "
     "Decisao GLOBAL, nao peca a peca. Geracao de alternativas com ranking.",
     "Toda escolha vem com as alternativas rejeitadas e o motivo. Uma solucao "
     "ligeiramente mais pesada pode vencer — e o relatorio precisa dizer por que."),
    ("E17", "V", "Revisoes, impacto e freeze", 1, "E16",
     "Diff entre revisoes (verde/vermelho/amarelo). Impact analysis: mover uma "
     "janela mostra studs, verga, placas, MEP, BOM, CNC, custo e pecas ja "
     "fabricadas afetadas. Change order. Freeze impede fabricar revisao vencida.",
     "O diff de duas revisoes identicas e vazio; o impacto declarado contem todas "
     "as pecas que de fato mudaram de geometria."),
    ("E18", "VI", "Interoperabilidade e banco", 2, "E17",
     "Esquema de 28 entidades em SQLite. Exportacao DXF, IFC4 (subconjunto), OBJ, "
     "STL, CSV, XLSX, JSON, XML, PDF, ZIP. Importacao DXF, IFC, CSV, XLSX, JSON. "
     "DWG, RVT e SKP recebem adaptador declarado, nao implementacao.",
     "Ida e volta: exportar e reimportar devolve o mesmo modelo. O IFC abre em "
     "visualizador externo — conferido pelo esquema, nao por fe."),
    ("E19", "VI", "Visualizador completo", 3, "E18",
     "Modos arquitetura / estrutura / paineis / MEP / termica / acustica / "
     "fabricacao / montagem / logistica / as-built. Raio-X. Filtros. Cores por "
     "utilizacao, tensao, flecha, perfil, etapa. Diagramas. Exploded view. "
     "Animacao de montagem na timeline. Dashboard. Modos educacional, "
     "especialista e executivo.",
     "Cada modo passa pelo viewer_teste.py num navegador de verdade, como os 48 "
     "testes de hoje."),
    ("E20", "VI", "Documentacao", 2, "E19",
     "Memorial de calculo com formula, coeficiente, clausula e substituicao "
     "numerica. Memorial descritivo. Shop drawings por peca, painel e ligacao. "
     "Lista de pecas e fixadores. Plano de corte. Packing list. Manual de "
     "montagem. Relatorio de inspecao. Pranchas A0 a A4. Biblioteca de detalhes.",
     "Nenhum numero do memorial e digitado: todos sao lidos do modelo. Um numero "
     "que divirja da prancha e ERRO."),
    ("E21", "VI", "Verificacao final e scores", 1, "E20",
     "Checklist de liberacao de 16 itens. Motor de erros com CRITICO / ERRO / "
     "ATENCAO / INFO. Auto-correcao com solucoes ordenadas. Scores estrutural, "
     "fabricabilidade, montabilidade, custo, logistica e sustentabilidade.",
     "Nenhum item do checklist pode ser marcado a mao: cada um e uma funcao que "
     "roda sobre o modelo."),
    ("E22", "VI", "Sustentabilidade", 1, "E21",
     "CO2e por kg de aco (H), aco reciclado, energia incorporada, desperdicio, "
     "reutilizacao. Design for disassembly com indice de desmontabilidade.",
     "O CO2e fecha com o peso do BOM; o fator de emissao entra como pendencia "
     "declarada, nunca como verdade."),
    ("E23", "VII", "Contratos do que e bloqueado", 2, "E22",
     "Para cada item que depende do mundo externo — DWG/RVT, LiDAR, visao "
     "computacional, AR, app de obra, sensores, ERP, usuarios e permissoes — "
     "entrego o CONTRATO: esquema de dados, adaptador vazio e o teste que valida "
     "quando o dado chegar. Nao entrego simulacao disfarcada de funcionalidade.",
     "Cada adaptador falha explicitamente com 'sem fonte de dados', nunca devolve "
     "numero inventado."),
]

BLOCOS = {
    "I": "Fundacao — separar motor de caso e montar a base de engenharia",
    "II": "Engenharia — cargas, combinacoes, solver e norma",
    "III": "Produto construtivo — painel, ligacao, peca",
    "IV": "Industria — nesting, BOM, CNC, logistica",
    "V": "Obra e decisao — montagem, otimizacao, revisao",
    "VI": "Interface e entrega — interoperabilidade, visualizador, documento",
    "VII": "Fronteira — o que depende do mundo externo",
}


def conferir() -> dict:
    """O plano tambem se audita: secao orfa e etapa fantasma sao erro."""
    codigos = {e[0] for e in ETAPAS} | {"—", "*"}
    fantasmas = sorted({s[3] for s in SECOES} - codigos)
    sem_etapa = [s[0] for s in SECOES if s[3] == "—" and s[2] != "FEITO"]
    numeros = [s[0] for s in SECOES]
    faltando = [n for n in range(1, 156) if n not in numeros]
    por_sit = {}
    for s in SECOES:
        por_sit[s[2]] = por_sit.get(s[2], 0) + 1
    return dict(secoes=len(SECOES), faltando=faltando, etapas_fantasma=fantasmas,
                secoes_sem_etapa=sem_etapa, situacoes=por_sit,
                ciclos=sum(e[3] for e in ETAPAS),
                ciclos_autonomos=sum(e[3] for e in ETAPAS if e[1] != "VII"))


if __name__ == "__main__":
    r = conferir()
    print(f"  {r['secoes']} secoes | {len(ETAPAS)} etapas | {r['ciclos']} ciclos")
    print(f"  situacoes: {r['situacoes']}")
    print(f"  secoes faltando: {r['faltando'] or 'nenhuma'}")
    print(f"  etapas fantasma: {r['etapas_fantasma'] or 'nenhuma'}")
