"""
PROGRAMA DE AUDITORIAS — mapa de cobertura.

Cada auditoria pedida pelo proprietario e classificada em quatro situacoes:

  AUTOMATIZADA  roda no modelo a cada execucao e reprova sozinha
  PARCIAL       parte roda, parte depende de dado que o modelo ainda nao guarda
  ANALISE       e julgamento, nao medida: cabe a mim responder e registrar
  BLOQUEADA     depende de terceiro (sondagem, calculo, concessionaria, laudo)

A classificacao e honesta por construcao: uma auditoria so e AUTOMATIZADA se ha
funcao de verificacao apontada para ela. Nao existe "verificado" sem verificador.
"""
from __future__ import annotations

import inspect

import auditoria as au
import auditoria2 as a2
import auditoria3 as a3

# (numero, titulo, [funcoes], situacao, observacao)
PROGRAMA = [
    (1, "Historico e decisoes", ["checar_integridade_referencial"], "PARCIAL",
     "codigos orfaos e duplicados sao automaticos; conflito de DECISAO e "
     "rastreado em docs/DIVERGENCIAS.md, 20 revisoes com motivo escrito"),
    (2, "Coerencia global", ["checar_colisoes", "checar_projecao_superior",
                             "checar_integridade_referencial", "checar_fechamento"],
     "AUTOMATIZADA", "terreo x superior, arquitetura x instalacoes e decisao "
     "antiga x nova saem do mesmo modelo: divergir e impossivel por construcao"),
    (3, "Programa", ["checar_metas", "checar_subdivisoes"], "PARCIAL",
     "area por ambiente contra alvo e automatica; 'ambiente sem funcao clara' e "
     "julgamento — hoje nao ha nenhum"),
    (4, "Localizacao dos ambientes", ["checar_acesso_por_molhado",
                                      "checar_conectividade", "checar_fluxos"],
     "AUTOMATIZADA", "adjacencia, privacidade e apoio verificados pelo grafo de vaos"),
    (5, "Fluxos", ["checar_fluxos", "checar_conectividade"], "AUTOMATIZADA",
     "cruzamento servico x social, percurso longo e gargalo"),
    (6, "Areas mortas", ["checar_espacos_mortos", "checar_colisao_porta"],
     "AUTOMATIZADA", "residuo por celula de malha e espaco atras de porta"),
    (7, "Eficiencia de area", ["checar_metas"], "AUTOMATIZADA",
     "proporcao social/intimo/servico/circulacao contra a meta de 8 %"),
    (8, "Mobiliario", ["checar_bancadas", "checar_loucas", "checar_colisao_porta",
                       "checar_janela_mobiliario", "checar_marcenaria_fila",
                       "checar_peninsula"], "AUTOMATIZADA",
     "dimensao, posicao, varredura de porta, interferencia com janela e corredor"),
    (9, "Ergonomia", ["checar_bancadas", "checar_acessibilidade", "checar_cozinha"],
     "PARCIAL", "alturas e alcances estao na especificacao; uso sentado e "
     "manobra so em rota acessivel"),
    (10, "Cozinha", ["checar_cozinha", "checar_bancadas", "checar_loucas",
                     "checar_coccao", "checar_equipamento_sob_bancada",
                     "checar_peninsula"], "AUTOMATIZADA",
     "triangulo de trabalho, apoio, equipamentos locados, ponto de coccao unico "
     "no volume integrado, equipamento sob a bancada certa e peninsula ancorada"),
    (11, "Gourmet", ["checar_cortina_vidro", "checar_exaustao_odor",
                     "checar_fronteira_climatica", "checar_coccao"], "AUTOMATIZADA",
     "churrasqueira, exaustao, abertura para a piscina, chuva e fumaca"),
    (12, "Banheiros", ["checar_loucas", "checar_subdivisoes", "checar_hidraulica",
                       "checar_prumadas", "checar_drenagem"], "AUTOMATIZADA",
     "layout, circulacao, ventilacao, ralo, impermeabilizacao e prumada"),
    (13, "Suite master", ["checar_subdivisoes", "checar_prumadas",
                          "checar_tecnicos", "checar_espacos_mortos"],
     "AUTOMATIZADA", "area, compartimentos, prumada, ar condicionado e area morta"),
    (14, "Mini lounge", ["checar_lounge"], "AUTOMATIZADA",
     "dimensao medida contra o televisor, acustica pela parede do painel, "
     "climatizacao e necessidade real"),
    (15, "Suites 02 e 03", ["checar_padronizacao", "checar_subdivisoes"],
     "AUTOMATIZADA", "espelhamento conferido compartimento a compartimento"),
    (16, "Paredes", ["checar_vedacao", "checar_malha", "checar_colisoes"],
     "AUTOMATIZADA", "as paredes sao DERIVADAS da malha: nao existe parede "
     "desenhada a mao para conferir"),
    (17, "Portas", ["checar_vaos", "checar_colisao_porta", "checar_acessibilidade",
                    "checar_padronizacao"], "AUTOMATIZADA",
     "largura, sentido, colisao, acessibilidade e numero de familias"),
    (18, "Janelas e esquadrias", ["checar_vaos", "checar_iluminacao",
                                  "checar_janela_mobiliario", "checar_privacidade",
                                  "checar_padronizacao"], "AUTOMATIZADA",
     "posicao, area, insolacao, privacidade, drenagem e padronizacao"),
    (19, "Ventilacao cruzada", ["checar_ventilacao_cruzada", "checar_chamine"],
     "AUTOMATIZADA", "faces opostas por grupo integrado, mais o efeito chamine"),
    (20, "Conforto termico", [], "ANALISE",
     "calculado na prancha 11 (U, FSo, sombreamento) e na carga de climatizacao; "
     "nao ha verificacao binaria porque nao ha limite binario"),
    (21, "Iluminacao natural", ["checar_iluminacao", "checar_profundidade_luz"],
     "AUTOMATIZADA", "fracao de area por compartimento e profundidade util"),
    (22, "Acustica", ["checar_vedacao", "checar_lounge", "checar_tecnicos"],
     "PARCIAL", "adjacencias criticas e famílias de parede sao automaticas; "
     "Rw composto e calculo, na prancha 11"),
    (23, "Estrutura", ["checar_estrutura", "checar_projecao_superior",
                       "checar_altura_livre"], "PARCIAL",
     "flecha, tensao, vao, apoio e junta de deslizamento; flambagem lateral e "
     "fundacao dependem de calculo com ART"),
    (24, "Modulacao", ["checar_malha", "checar_paginacao", "checar_padronizacao"],
     "AUTOMATIZADA", "toda coordenada multipla de 300, recorte minimo e SKUs"),
    (25, "Hidraulica", ["checar_hidraulica", "checar_prumadas", "checar_penetracoes"],
     "AUTOMATIZADA", "pesos, vazao, diametro, velocidade, pressao e alinhamento"),
    (26, "Esgoto", ["checar_hidraulica", "checar_penetracoes", "checar_tecnicos"],
     "PARCIAL", "UHC, diametro, shaft e caixas; declividade de cada trecho so "
     "no projeto executivo de instalacoes"),
    (27, "Drenagem", ["checar_drenagem", "checar_piscina", "checar_cortina_vidro"],
     "AUTOMATIZADA", "vazao, calha, descida, ralo por ambiente e trilho da cortina"),
    (28, "Impermeabilizacao", ["checar_drenagem", "checar_paginacao"], "PARCIAL",
     "sistema, subida e teste declarados; detalhe de cada transicao e prancha "
     "de detalhe, nao verificacao"),
    (29, "Eletrica — carga", ["checar_eletrica"], "AUTOMATIZADA",
     "demanda, simultaneidade, fator por grupo, condutor e padrao de entrada"),
    (30, "Eletrica — pontos", ["checar_eletrica"], "PARCIAL",
     "quantidade por perimetro e automatica; posicao de cada tomada e prancha 27"),
    (31, "Iluminacao artificial", [], "ANALISE",
     "cenas, temperatura de cor e IRC estao na prancha 16; lux por ambiente "
     "depende de luminaria escolhida"),
    (32, "Protecoes eletricas", [], "BLOQUEADA",
     "DR, DPS, aterramento e equipotencializacao declarados; dimensionamento "
     "definitivo exige projeto eletrico com ART"),
    (33, "Dados, automacao e wi-fi", ["checar_tecnicos"], "PARCIAL",
     "rack, cameras e access points locados; cabeamento ponto a ponto e executivo"),
    (34, "HVAC", ["checar_tecnicos", "checar_fronteira_climatica"], "AUTOMATIZADA",
     "carga por ambiente, capacidade, linha frigorigena, dreno, nicho e ruido"),
    (35, "Exaustao", ["checar_exaustao_odor", "checar_fronteira_climatica"],
     "AUTOMATIZADA", "vazao, saida declarada e retorno de odor por vao"),
    (36, "Cobertura", ["checar_drenagem", "checar_chamine"], "PARCIAL",
     "area de contribuicao, calha, descida e lanternim; rufo e acesso sao detalhe"),
    (37, "Fachadas", ["checar_privacidade", "checar_padronizacao"], "ANALISE",
     "proporcao e coerencia frente/fundos sao julgamento; materiais limitados a "
     "tres familias, conferido"),
    (38, "Estanqueidade", ["checar_cortina_vidro", "checar_drenagem"], "PARCIAL",
     "trilho, ralo e membrana declarados; flashing por encontro e detalhe"),
    (39, "Piscina", ["checar_piscina"], "AUTOMATIZADA",
     "dimensao, faixa seca, recirculacao, drenos, succao e casa de maquinas"),
    (40, "Garagem", ["checar_metas", "checar_estrutura", "checar_drenagem"],
     "AUTOMATIZADA", "vao sem pilar, manobra, drenagem e reserva de veiculo eletrico"),
    (41, "Lavanderia e servico", ["checar_loucas", "checar_fluxos",
                                  "checar_exaustao_odor"], "AUTOMATIZADA",
     "maquinas, tanque, ventilacao, drenagem e circulacao de servico"),
    (42, "Armazenamento", ["checar_subdivisoes", "checar_cozinha"], "AUTOMATIZADA",
     "despensa, rouparia, closet, deposito externo e armarios, todos locados"),
    (43, "Acessibilidade", ["checar_acessibilidade", "checar_niveis",
                            "checar_altura_livre"], "AUTOMATIZADA",
     "vao livre, giro, rota, degrau e altura livre"),
    (44, "Seguranca", ["checar_seguranca", "checar_altura_livre", "checar_escada"],
     "AUTOMATIZADA", "guarda-corpo, vidro sinalizado, piso molhado e piscina"),
    (45, "Manutencao", ["checar_tecnicos", "checar_penetracoes"], "AUTOMATIZADA",
     "acesso, zona livre de quadro, shaft inspecionavel e faixa tecnica"),
    (46, "Construtibilidade", ["checar_penetracoes", "checar_paginacao",
                               "checar_malha"], "PARCIAL",
     "furacao, paginacao e modulacao; sequencia de obra e planejamento, nao projeto"),
    (47, "Compatibilizacao", ["checar_penetracoes", "checar_altura_livre",
                              "checar_estrutura", "checar_prumadas"],
     "AUTOMATIZADA", "e o cruzamento que o modelo unico resolve na origem"),
    (48, "Forros", ["checar_fechamento", "checar_penetracoes", "checar_altura_livre"],
     "AUTOMATIZADA", "altura, entreforro, interferencia e acesso tecnico"),
    (49, "Pisos e niveis", ["checar_niveis", "checar_paginacao", "checar_drenagem"],
     "AUTOMATIZADA", "cota, transicao, caimento, soleira e paginacao"),
    (50, "Marcenaria", ["checar_bancadas", "checar_janela_mobiliario",
                        "checar_colisao_porta", "checar_marcenaria_fila",
                        "checar_equipamento_sob_bancada"], "AUTOMATIZADA",
     "modulacao, posicao, interferencia e ALINHAMENTO DE FRENTE em fila; "
     "ferragem e detalhe de fabricacao seguem fora"),
    (51, "Padronizacao", ["checar_padronizacao"], "AUTOMATIZADA",
     "numero de familias por sistema, contra alvo declarado"),
    (52, "BOM e quantitativos", [], "BLOQUEADA",
     "quantitativo sai do modelo, mas so faz sentido depois do congelamento; "
     "perdas e embalagem dependem de fornecedor"),
    (53, "Custo e value engineering", [], "BLOQUEADA",
     "sem tabela de precos nao ha auditoria de custo — so a hierarquia de "
     "investimento da prancha 13"),
    (54, "Importacao", [], "BLOQUEADA",
     "tensao, certificacao e reposicao dependem de produto escolhido"),
    (55, "Legal e urbanistico", ["checar_fechamento"], "PARCIAL",
     "recuo, taxa, coeficiente e gabarito conferidos contra parametros (H); "
     "certidao oficial do SU16 e pendencia 1"),
    (56, "Durabilidade", [], "ANALISE",
     "UV, umidade e corrosao orientaram a especificacao; nao ha limite binario"),
    (57, "Privacidade", ["checar_privacidade"], "AUTOMATIZADA",
     "vao intimo contra rua e divisa, com brise como mitigacao aceita"),
    (58, "Vistas e eixos visuais", ["checar_cortina_vidro"], "AUTOMATIZADA",
     "eixo estar-cozinha-gourmet-cortina-piscina, medido em milimetros"),
    (59, "Flexibilidade futura", ["checar_eletrica", "checar_tecnicos"],
     "AUTOMATIZADA", "reservas declaradas: veiculo eletrico, fotovoltaica, "
     "aquecimento de piscina, climatizacao da oficina e da fita social"),
    (60, "Pos-modificacao", ["*"], "AUTOMATIZADA",
     "e a execucao INTEIRA do conjunto apos cada mudanca — foi assim que a "
     "despensa e a cortina de vidro foram validadas"),
    (61, "Repeticao de solucoes", ["checar_padronizacao"], "PARCIAL",
     "numero de familias e automatico; 'deve repetir?' e decisao registrada"),
    (62, "Regressao", ["checar_integridade_referencial", "checar_padronizacao"],
     "PARCIAL", "orfao e duplicado sao automaticos; perda de decisao validada e "
     "rastreada pelo historico de revisoes"),
    # R12 — a folha entra no programa. Ate aqui o programa auditava o MODELO;
    # a peca que o cliente efetivamente le e a PRANCHA, e ela nunca havia sido
    # verificada. Catorze das 35 desenhavam fora da moldura.
    (64, "Representacao: conteudo dentro da moldura",
     ["checar_extravasamento"], "AUTOMATIZADA",
     "NBR 10068: o que passa da moldura nao chega ao papel nem a tela. "
     "Cortar e legitimo quando declarado por linha de ruptura (NBR 8403)."),
    (65, "Representacao: procedencia do traco",
     ["checar_procedencia"], "AUTOMATIZADA",
     "Cada traco carrega de onde veio (data-tipo/data-cod). Sem isso a prancha "
     "na tela e uma figura: da para amplia-la e nada mais."),
    (66, "Cadastro e tipologia do projeto",
     ["checar_cadastro"], "AUTOMATIZADA",
     "Secao 02: identidade deixa de ser texto de carimbo e vira dado. A "
     "tipologia carrega a sobrecarga da NBR 6120 e o pe-direito minimo."),
    (67, "Separacao entre motor e caso",
     ["checar_separacao_motor"], "AUTOMATIZADA",
     "Basta um import de projeto dentro de nucleo/ para a separacao se desfazer. "
     "A regra impede que isso passe despercebido."),
    (68, "Biblioteca de perfis: solver de secao",
     ["checar_solver_secao"], "AUTOMATIZADA",
     "Secoes 08 e 09. Nao ha formula por forma: ha um solver de linha media. "
     "Validado contra solucao fechada do U simples — centro de torcao e "
     "empenamento — e contra identidades (A = t.L, J = L.t3/3, eixos paralelos)."),
    (69, "Biblioteca de perfis: catalogo",
     ["checar_catalogo", "checar_familias_lsf"], "AUTOMATIZADA",
     "Todo perfil calculavel e fisicamente possivel; toda funcao de LSF com "
     "papel estrutural declarado. Disponibilidade por fabricante e (H)."),
    (70, "Materiais, acos e revestimentos",
     ["checar_materiais"], "AUTOMATIZADA",
     "Secao 10. Sem fy nao existe NBR 14762. Revestimento deixa de ser "
     "'galvanizado' e passa a ser Z275, com consequencia dimensional medida."),
    (71, "Sistema normativo por pais",
     ["checar_normas"], "AUTOMATIZADA",
     "Secao 11. Misturar combinacao do Eurocode com resistencia da NBR e erro "
     "que nao aparece no desenho: as duas repartem a seguranca de modos "
     "diferentes."),
    (72, "Resistencia ao fogo",
     ["checar_incendio"], "PARCIAL",
     "Secao 44. TRRF pela NBR 14432 e calculavel; a resistencia efetiva da "
     "composicao depende de ENSAIO do fabricante e entra (H)."),
    (73, "Cargas normativas",
     ["checar_cargas"], "AUTOMATIZADA",
     "Secao 12. Uso sem sobrecarga tabelada levanta erro em vez de assumir um "
     "valor — e a mesma regra do resto do projeto."),
    (74, "Gerador de vento NBR 6123",
     ["checar_vento"], "AUTOMATIZADA",
     "Secao 13. Ancorado na definicao: categoria II, classe A, 10 m e o terreno "
     "de referencia e ali S2 vale exatamente 1,000. Interpolacao entre faixas da "
     "Tabela 4 e declarada, nunca silenciosa."),
    (75, "Combinacoes NBR 8681",
     ["checar_combinacoes"], "AUTOMATIZADA",
     "Secao 14. gama pondera a incerteza; psi a simultaneidade. A verificacao "
     "central e a do permanente FAVORAVEL: sem ela o levantamento da cobertura "
     "pelo vento nunca aparece."),
    (76, "Solver de porticos espaciais",
     ["checar_solver"], "AUTOMATIZADA",
     "Secoes 15, 16 e 18. Rigidez direta com 12 graus de liberdade por barra, "
     "sem dependencia externa: a fatoracao LDL^T em perfil e escrita aqui. "
     "Conferido contra seis solucoes fechadas e contra o equilibrio global."),
    (77, "Segunda ordem (P-Delta)",
     ["checar_segunda_ordem"], "AUTOMATIZADA",
     "Secao 15. A carga vertical sobre a geometria ja deslocada amplifica o "
     "proprio deslocamento. Conferido contra 1/(1 - N/Ncr) em tres fracoes da "
     "carga critica de Euler."),
    (78, "Resistencia NBR 14762 — Metodo da Resistencia Direta",
     ["checar_mrd"], "AUTOMATIZADA",
     "Secao 15. Tres instabilidades competem: global, local e distorcional, e "
     "qual governa muda com o comprimento. Conferido contra a continuidade das "
     "proprias curvas da norma e contra os limites fisicos."),
    (79, "Cisalhamento e enrugamento de alma",
     ["checar_cisalhamento"], "AUTOMATIZADA",
     "Secao 15. A resistencia por unidade de esbeltez cai monotonicamente — "
     "alma fina demais deixa de trabalhar por escoamento."),
    (80, "Painelizacao automatica",
     ["checar_painelizacao"], "AUTOMATIZADA",
     "Secoes 05, 23, 24 e 25. A parede vira produto de fabrica: guias, "
     "montantes na modulacao, king e jack stud, verga, peitoril, cripples e "
     "blocking. Painel grande demais so passa com o motivo declarado."),
    (81, "Verga dimensionada com as alternativas rejeitadas",
     ["checar_verga"], "AUTOMATIZADA",
     "Secoes 26 e 20. A escolha vem com o que falhou e por que. A flecha pela "
     "formula e cruzada com o solver da E5 — foi desse cruzamento que sairam um "
     "erro de unidade e um erro de sinal no proprio solver."),
    (82, "Contraventamento, shear wall e trelicas",
     ["checar_contraventamento"], "AUTOMATIZADA",
     "Secoes 27, 28 e 29. Montante e guia formam um quadrilatero articulado, "
     "que e um MECANISMO. A verificacao central nao e a diagonal: e o "
     "tombamento, que desce pelo montante de extremidade e arranca a parede."),
    (83, "Ligacoes, ancoragem e acessibilidade de montagem",
     ["checar_ligacoes"], "AUTOMATIZADA",
     "Secoes 30 a 33 e 37. Cinco modos de ruina e nenhum e o parafuso: em chapa "
     "de 0,95 mm a ligacao falha na CHAPA. Mais o sexto modo que nenhuma norma "
     "verifica e toda obra encontra — a parafusadeira que nao entra."),
    (84, "Pecas, furacao, numeracao e passaporte",
     ["checar_pecas"], "AUTOMATIZADA",
     "Secoes 47 a 51 e 66. O codigo deriva da POSICAO no painel, nao da ordem "
     "de geracao — senao inserir uma peca renumera todas e a rastreabilidade se "
     "perde. Campo de passaporte sem fonte fica None, nunca inventado."),
    (85, "Clash entre disciplinas",
     ["checar_clash"], "AUTOMATIZADA",
     "Secao 46. Conflito dentro da mesma disciplina nao e clash: dois montantes "
     "vizinhos se tocam por projeto."),
    (86, "Nesting de barra, chapa e bobina",
     ["checar_nesting"], "AUTOMATIZADA",
     "Secoes 61 a 63, 85 e 86. A verificacao central e uma identidade: bruto = "
     "usado + perda. A sobra do deposito e consultada antes de abrir barra nova."),
    (87, "BOM, curva ABC, landed cost e risco",
     ["checar_bom"], "PARCIAL",
     "Secoes 59, 60, 87 e 91 a 95. As QUANTIDADES sao derivadas das pecas e do "
     "plano de corte; os PRECOS sao (H). A massa comprada e a util dividida "
     "pelo aproveitamento — a perda foi paga."),
    (88, "CNC, producao, linha e qualidade",
     ["checar_fabricacao"], "PARCIAL",
     "Secoes 67 a 75, 129 e 130. O formato NEUTRO e verificavel por ida e "
     "volta; o dialeto de cada maquina e (H). O ciclo da linha e o da estacao "
     "mais lenta, nunca a soma — somar e o erro que faz prometer prazo."),
    (89, "Logistica, icamento e transporte",
     ["checar_logistica"], "PARCIAL",
     "Secoes 96 a 102. O centro de gravidade sai da soma dos momentos das "
     "pecas: um painel com as aberturas de um lado nao sobe equilibrado, e o "
     "montador descobre isso com o painel pendurado."),
    (90, "Sequenciamento e montagem guiada",
     ["checar_montagem"], "AUTOMATIZADA",
     "Secoes 32, 33, 55 a 58. Ordenacao topologica com estabilidade passo a "
     "passo. Ciclo de dependencia e reportado como montagem impossivel, nao "
     "resolvido em ordem arbitraria. A desmontagem e a inversa exata."),
    (91, "Otimizacao global e decisao explicada",
     ["checar_otimizacao"], "AUTOMATIZADA",
     "Secoes 19 a 22, 124 e 147 a 150. Verificado contra o exemplo da propria "
     "especificacao (secao 148): vence a solucao mais PESADA, porque 5 SKUs "
     "contra 11 e 110 h a menos de montagem pagam os 250 kg de aco."),
    (92, "Revisoes, impacto e congelamento",
     ["checar_revisao"], "AUTOMATIZADA",
     "Secoes 79 a 83 e 135. Comparar revisoes em CAD e trabalho manual; aqui e "
     "computavel porque tudo e funcao do modelo. A MESMA alteracao tem "
     "gravidade baixa em projeto e alta com a peca ja cortada."),
    (93, "Interoperabilidade: DXF, IFC4, OBJ, STL, CSV, XML",
     ["checar_interop"], "AUTOMATIZADA",
     "Secoes 138 e 139. Todo formato verificado por ida e volta. DWG, RVT e SKP "
     "falham dizendo por que — entregar arquivo aproximado de formato "
     "proprietario seria pior que nao entregar."),
    (94, "Banco de dados de 28 entidades",
     ["checar_banco"], "AUTOMATIZADA",
     "Secao 137. O esquema separa as naturezas: 17 tabelas de PROJETO sao "
     "espelho do modelo e se regeneram; 11 de EVENTO registram o que aconteceu "
     "no mundo e nao podem ser perdidas."),
    (95, "Checklist de liberacao e motor de erros",
     ["checar_liberacao"], "AUTOMATIZADA",
     "Secoes 111 a 118. A liberacao nao e opiniao: 16 itens verificados na "
     "cadeia inteira, e um ERRO bloqueia trazendo as solucoes ordenadas."),
    (96, "Scores e sustentabilidade",
     ["checar_sustentabilidade"], "AUTOMATIZADA",
     "Secoes 121 e 141 a 146. Cada score carrega a formula que o produziu, e "
     "reage ao projeto: padronizar SKU e elevar aproveitamento movem o numero."),
    (97, "Documentos gerados do modelo",
     ["checar_documentos"], "AUTOMATIZADA",
     "Secao 110. Memorial, lista de pecas, plano de corte, packing list, manual "
     "de montagem e relatorio de inspecao saem do mesmo dado; os tres modos "
     "de leitura mudam a explicacao, nunca o valor de calculo."),
    (98, "Contratos do que e bloqueado",
     ["checar_contratos"], "AUTOMATIZADA",
     "Secoes 3, 4, 76 a 78, 111 a 118, 120, 125, 131 a 134 e 136. As 20 secoes "
     "que dependem do mundo externo tem esquema, adaptador vazio e criterio de "
     "aceite. Nenhum adaptador devolve numero; todos dizem o que falta e como "
     "suprir. Simulacao disfarcada de funcionalidade e pior que a ausencia, "
     "porque a ausencia se ve."),
    (99, "Descida de cargas e verificacao de todos os montantes",
     ["checar_descida"], "PARCIAL",
     "Secoes 15, 16 e 38. A carga que chega a cada montante sai de area de "
     "influencia, do que ha acima e da combinacao NBR 8681 — nao de uma "
     "constante. Os 415 montantes sao verificados um a um, sem teto na "
     "utilizacao. PARCIAL porque a direcao do vigamento e desconhecida: o "
     "excesso esta medido (1,54x no terreo) e declarado, nunca suposto."),
    (100, "Programa de parafusos: cada junta, cada quantidade, cada origem",
     ["checar_juntas"], "AUTOMATIZADA",
     "Secoes 30, 31 e 59. As 1.520 juntas entre pecas sao enumeradas e cada "
     "uma declara DE ONDE veio a quantidade: FORCA (esforco calculado), MINIMO "
     "(minimo construtivo) ou DECLARADO (regra escrita para esforco que o "
     "modelo ainda nao calcula). Somar as tres num numero so esconderia "
     "exatamente o que precisa ser sabido."),
    (101, "Vigamento de entrepiso, cobertura e contraventamento",
     ["checar_vigamento"], "PARCIAL",
     "Secoes 38, 39 e 28. Ate R30 as 805 pecas da estrutura eram TODAS de "
     "parede: o piso do superior nao se apoiava em nada. Entram 178 pecas de "
     "vigamento e 28 fitas em X, conferidas contra a forca global de vento da "
     "NBR 6123. PARCIAL porque V0 e a categoria de rugosidade sao leitura, "
     "nao medicao."),
    (102, "Plausibilidade: a grandeza e possivel?",
     ["checar_plausibilidade"], "PARCIAL",
     "Terceira classe de verificacao. As anteriores conferiam IDENTIDADE e "
     "FORMA FECHADA, e eram cegas para o erro em que a conta esta certa e o "
     "resultado e absurdo: 9,4 kg/m2 num sobrado em LSF passou 31 revisoes. "
     "PARCIAL porque 8 das 9 faixas sao pratica corrente, nao norma."),
    (103, "Completude: o sistema esta presente?",
     ["checar_completude"], "AUTOMATIZADA",
     "Quarta classe. As 447 condicoes verificavam o que existia e nao sentiam "
     "falta do que nunca foi escrito. A lista e do SISTEMA CONSTRUTIVO, escrita "
     "antes de olhar o modelo — senao vira inventario do que ja existe e "
     "confirma tudo por construcao."),
    (104, "Coerencia de modelo: auditoria, exportacao e desenho",
     ["checar_coerencia_de_modelo"], "AUTOMATIZADA",
     "A resposta ja foi NAO duas vezes, e das duas ninguem percebeu por meses: "
     "a auditoria verificou painel sem jamba dimensionada, e depois verificou "
     "805 pecas enquanto o projeto tinha 1.033. As duas foram corrigidas "
     "movendo codigo — o que evita o erro daquela vez, nao o proximo. Esta "
     "condicao compara peca a peca o que cada consumidor enxerga."),
    (105, "Composicao de parede: camada, espessura e area derivada",
     ["checar_camadas"], "AUTOMATIZADA",
     "Secoes 40, 41 e 59. O fechamento saia de seis coeficientes — "
     "area_m2 * 2,4 e mais cinco fatores — onde havia geometria para derivar. "
     "Cada painel passa a apontar para a composicao que a PR-12 lhe atribui, e "
     "a area de cada camada sai do proprio painel, descontada a abertura. "
     "Inclui paginacao de placa, esquadria, cobertura e impermeabilizacao."),
    (106, "Fundacao: quantidade derivada de uma espessura declarada",
     ["checar_radier"], "PARCIAL",
     "Secoes 36 e 37. A espessura de 180 mm vivia como literal no modulo de "
     "desenho e em copia dentro da ancoragem, e nenhum dos dois era dado. "
     "Concreto, aco, lastro e lona nunca entraram no BOM. PARCIAL porque "
     "espessura, fck e taxa de armadura sao (H) ate a sondagem: o modulo "
     "deriva QUANTIDADE, nao dimensiona radier."),
    (107, "Instalacoes: percurso, quantidade e interferencia com a estrutura",
     ["checar_instalacoes"], "PARCIAL",
     "Secoes 26 a 29. O tracado existia no desenho e nao no modelo: pontos sem "
     "percurso, e portanto zero metro de tubo, de eletroduto e de linha "
     "frigorigena no BOM. Com percurso medido, o item 'clashes' do checklist "
     "deixa de ser True literal e passa a confrontar volume a volume. PARCIAL "
     "porque o percurso e Manhattan vezes fator declarado — limite INFERIOR, "
     "nao projeto executivo de instalacoes."),
    (108, "Combinacoes: fator recalculado e acao sem consumidor",
     ["checar_combinacoes"], "AUTOMATIZADA",
     "Secao 4. O ultimo literal do checklist. \"combinacoes\": True nao era "
     "mentira — as combinacoes existem, sao geradas e sao usadas — mas um item "
     "que nao pode reprovar nao verifica nada. Sao duas perguntas: os fatores "
     "sao os das Tabelas 1 e 2 da NBR 8681, recalculados sem passar pelo "
     "gerador? E toda acao declarada no caso entra em alguma verificacao? Cada "
     "verificacao declara o que consumiu a partir da chamada que fez."),
    (109, "Impermeabilizacao do superior: a lacuna era de leitura",
     ["checar_impermeabilizacao_do_superior"], "AUTOMATIZADA",
     "Secoes 40 e 59. O cruzamento com o quadro de esquadrias acusava 3 banhos "
     "no superior sem area impermeabilizada, e a explicacao escrita era que a "
     "suite e retangulo unico e a area teria de ser arbitrada. Estava errada: "
     "a subdivisao existe desde R06, com x, y, w e h exatos. O dado estava "
     "numa lista e a verificacao olhava outra — sexta ocorrencia do mesmo "
     "defeito de duas fontes para um fato."),
    (110, "Pendencias: o que o caderno declara aberto tranca a fabricacao",
     ["checar_pendencias"], "AUTOMATIZADA",
     "Secoes 140 e 141. A lista de pendencias vivia dentro de pranchas7.py, "
     "com copia DIVERGENTE dentro de pranchas3.py, e o checklist nao tinha "
     "como consulta-la: dezessete verificacoes de coerencia interna "
     "produziam a frase LIBERADO PARA FABRICACAO com a ART do calculo "
     "estrutural e o nesting codificado abertos no proprio caderno. "
     "Consistencia interna nao e autorizacao."),
    (111, "Cotacao: do preco (H) ao preco que alguem assina",
     ["checar_cotacao"], "PARCIAL",
     "Secoes 91 a 95 e 136. Perguntar se da para cotar obrigou a responder o "
     "que exatamente se compra — e a resposta achou o aco contado DUAS VEZES, "
     "em duas unidades: 6.230,8 kg de barra e 1.033 pecas cortadas, as duas "
     "com preco, as duas somadas. Nenhuma faixa de plausibilidade pegaria "
     "isso: 1.571 e 1.359 R$/m2 cabem ambos em 600 a 1.800. O que pega e "
     "identidade. PARCIAL porque 100 % dos precos continuam (H): o modulo "
     "monta o mapa, valida, compara e substitui, e nao inventa preco."),
    (112, "Por comodo: o eixo em que a verificacao nao existia",
     ["checar_ambientes"], "PARCIAL",
     "Secoes 30, 40, 100 e 136. As 510 condicoes anteriores verificam por "
     "SISTEMA — estrutura, camadas, MEP, fundacao, cotacao — e nenhuma por "
     "comodo, que e a unidade em que a casa e vivida e em que o pedreiro "
     "trabalha. Defeito nao se distribui por sistema: concentra-se onde dois "
     "sistemas se encontram, e os dois se encontram dentro de um comodo. Na "
     "primeira execucao o eixo achou 24 divergencias — 14 de um defeito real "
     "(duas regras para contar tomada) e 10 de grossura da propria "
     "conferencia. PARCIAL porque iluminacao e ventilacao dependem do Codigo "
     "de Obras municipal, que e a pendencia 1: as fracoes sao (H) declaradas."),
    (113, "Nicho de condensadora e familia de esquadria orfa",
     ["checar_nichos_e_familias"], "AUTOMATIZADA",
     "Secoes 28, 30 e 103. Duas conferencias nascidas da caminhada por comodo. "
     "O nicho TC-09 trazia ESCRITO '2 condensadoras ativas + 1 reservada' e a "
     "lista lhe mandava cinco: prosa nao roda e nao reprova, envelhece em "
     "silencio enquanto a lista muda. A ocupacao passa a ser derivada da lista "
     "e conferida contra a geometria. E familia de esquadria que existe no "
     "catalogo e em vao nenhum nao chega ao BOM, que le VAOS — chega ao "
     "QUADRO, que e o que o fornecedor cota."),
    (114, "Fachada: o que foi combinado, o que foi desenhado e o que tem "
          "estrutura", ["checar_fachada"], "PARCIAL",
     "Secoes 7, 19 e 45. Tres perguntas diferentes, e o projeto so respondia a "
     "segunda. As regras de fachada estao declaradas desde R06 — tres familias "
     "no maximo, vidro concentrado atras, nenhuma superficie que exija pintura "
     "em altura — e regra declarada que ninguem confere e preferencia, nao "
     "regra. A conferencia achou duas: o acabamento externo especificado era "
     "PINTURA num volume de 6,15 m, contra a propria regra, e os cinco brises "
     "existiam no desenho e no 3D sem material, sem massa e sem carga. PARCIAL "
     "porque o coeficiente de forma de ripado e o mecanismo do brise movel sao "
     "(H) ate o fornecedor."),
    (115, "Area externa e platibanda: 286 m2 e 550 mm que nao existiam",
     ["checar_externo"], "PARCIAL",
     "Secoes 31, 32 e 34. Quinze areas abertas, piscina com sistema completo, "
     "deck, muro de 2,2 m em todo o perimetro, oito itens de paisagismo e tres "
     "zonas de piso com material escolhido e razao escrita — nada com "
     "quantidade, e nenhuma familia 'externo' no BOM. Em residencia deste "
     "porte a area externa e 10 a 20 % do custo e e onde o orcamento estoura. "
     "Mais a platibanda: 550 mm de parede em 64,8 m de perimetro, aparecendo "
     "nas quatro fachadas, sem montante, sem guia, sem fechamento e sem massa. "
     "PARCIAL porque equipamento de piscina e mobiliario externo continuam "
     "fora do levantamento."),
    (116, "Viabilidade: o que falta, quem fecha e quanto depende disso",
     ["checar_viabilidade"], "PARCIAL",
     "Secoes 140 a 142. Uma lista de pendencias diz o que falta; ela nao diz a "
     "unica coisa que decide se o projeto pode andar, que e quanto dele "
     "depende de cada uma. Item que move 2 % do orcamento e nota de rodape; "
     "item que move 100 % e risco de contrato, e os dois aparecem iguais numa "
     "lista com bolinha. Exposicao e a fatia do custo que muda quando o dado "
     "chegar — nao a probabilidade de ele chegar errado, que aqui seria "
     "palpite com aparencia de numero. PARCIAL porque nove pendencias seguem "
     "abertas e seis dependem de terceiros."),
    (117, "Completude do DESENHO: o caderno mostra o que o modelo sabe?",
     ["checar_completude_do_desenho"], "AUTOMATIZADA",
     "Secoes 1 a 35. A completude de R32 pergunta se o sistema esta no MODELO; "
     "esta pergunta o inverso — se o que esta no modelo chegou ao PAPEL. Sao "
     "falhas de sentido oposto e nenhuma das duas pega a outra: um sistema "
     "pode estar modelado, orcado e verificado, e nao aparecer em prancha "
     "nenhuma. Foi o caso do catalogo de pecas entre R47 e R50, que existia "
     "como vista de tela — e a fabrica recebe o PDF, nao a tela."),
    (118, "Indice do caderno: as tres listas de pranchas dizem o mesmo?",
     ["checar_indice_do_caderno"], "AUTOMATIZADA",
     "Secao 143. Quem emite o caderno e build.CADERNO; quem o carimbo conta e "
     "TOTAL_PRANCHAS; quem o leitor navega e viewer_texto.json. Tres fontes "
     "para o mesmo fato — QUAIS pranchas existem — e em R51 a prancha 36 "
     "entrou nas duas primeiras e nao na terceira: o caderno saiu completo e o "
     "visualizador ficou com 35, sem que nada reclamasse. O titulo nao e "
     "comparado de proposito: o carimbo traz o titulo descritivo da folha e o "
     "indice o rotulo curto de navegacao, textos com funcoes diferentes. O que "
     "tem de ser identico e a identidade da folha, que e o numero."),
    (119, "Geotecnia: o solo deixou de ser hipotese",
     ["checar_geotecnia"], "AUTOMATIZADA",
     "Secao 144. Tres sondagens do proprietario, NSPT ate 8 m. O radier era o "
     "sistema mais caro apoiado no dado mais fraco — espessura, fck e taxa "
     "eram (H) e a pendencia 2 dizia isso. Agora ha pressao de contato contra "
     "tensao admissivel por tres correlacoes (adota-se a MENOR, porque "
     "nenhuma das tres nasceu deste solo), recalque por camadas com E do SPT, "
     "distorcao angular e — pergunta que quase ninguem faz — se a sondagem "
     "foi FUNDO o bastante. O que o solo mandou mudar nao foi o radier: foi o "
     "que esta debaixo dele."),
    (120, "Pluvial: as superficies do lote e a retencao",
     ["checar_pluvial"], "AUTOMATIZADA",
     "Secao 145. O proprietario trocou reuso por retencao — sistemas de "
     "dimensionamento OPOSTO: um quer o reservatorio cheio antes da seca, o "
     "outro vazio antes da chuva. Para dimensionar qualquer um dos dois "
     "faltava o que nunca existiu no modelo: a superficie do lote INTEIRO. "
     "333,44 m2 do terreno, 42 % dele, nao tinham classe nenhuma. Agora a "
     "soma das superficies tem de dar o lote, e o gatilho de 500 m2 da Lei "
     "1.192/2007 de Manaus e conferido contra a area que o modelo calcula."),
    (121, "Acustica: o eixo que o morador achou antes do programa",
     ["checar_acustica"], "AUTOMATIZADA",
     "Secao 146. A pergunta veio de quem mora: quem entra na casa ouve o "
     "chuveiro do banho da entrada. Nenhuma das 101 verificacoes podia "
     "responder. Havia Rw por familia de parede desde R12 e nada que "
     "percorresse os pares fonte-receptor. A conferencia nova reprovou "
     "QUATRO passagens na primeira execucao, e a pior nao era a que se via: "
     "era o banho contra o DORMITORIO, com folha oca de 20 dB. Em acustica o "
     "elo fraco domina — 44 dB de parede com 15 dB de porta entregam 20."),
    (122, "Completude da CENA: o 3D mostra o que o modelo sabe?",
     ["checar_completude_da_cena"], "AUTOMATIZADA",
     "Secao 147. R51 perguntou se o que esta no modelo chega ao PAPEL; esta "
     "pergunta se chega a CENA, e um sistema pode passar numa e falhar na "
     "outra. Foi o caso do muro: 113 m de bloco aparente de 2,20 m, no "
     "orcamento e na prancha desde R49, e ausente do 3D — o elemento que mais "
     "define o que se ve da rua, fora da vista que existe para mostrar o que "
     "se ve. Ha lista de EXCLUSAO declarada: sem ela, bastaria nao listar o "
     "sistema para ele nunca reprovar."),
    (123, "Eletrica: 220/127 confirmado, e o desequilibrio que ele traz",
     ["checar_eletrica_trifasica"], "AUTOMATIZADA",
     "Secao 148. A pendencia 7 fechou com a decisao do proprietario — "
     "trifasico, 127 V para os eletrodomesticos correntes e 220 V para ar e "
     "chuveiro — e isso confere com o que a concessionaria fornece em BT "
     "trifasica. Tirar o (H) foi o menor efeito: num 220/127 a carga de 127 "
     "fica entre fase e neutro e a de 220 entre duas fases, e aparece um "
     "problema que instalacao monofasica nao tem e que nenhuma verificacao "
     "enxergava — o desequilibrio. 58 circuitos distribuidos com 0,43 % de "
     "diferenca entre a fase mais e a menos carregada, e a atribuicao escrita "
     "no projeto em vez de delegada ao eletricista."),
    (124, "Mercado: de quem se compra, e contra que numero publico",
     ["checar_mercado"], "PARCIAL",
     "Secao 149. O proprietario pediu preco em cinco fornecedores de cada "
     "material, com um de Manaus. A pesquisa devolveu a IDENTIDADE dos "
     "fornecedores — 51 nomes em 10 familias, cobrindo 100 % do custo, com "
     "praca local em nove delas — e os INDICES PUBLICOS regionais. Nao "
     "devolveu preco unitario: loja de material nao publica valor em pagina "
     "indexavel, e transcrever faixa de blog como cotacao seria inventar "
     "numero. PARCIAL por isso, e nao por falta de pesquisa. Em troca, os "
     "indices permitiram a conferencia de CIMA PARA BAIXO — que cinco "
     "propostas por item nunca dao — e foi ela que obrigou a escrever a lista "
     "do que NAO esta no orcamento: loucas, climatizacao, pintura, "
     "revestimento interno, marcenaria, mao de obra de acabamento, "
     "equipamento de piscina, projetos e BDI."),
    (63, "Congelamento final", ["*"], "PARCIAL",
     "todas as criticas passam; o congelamento depende das 8 pendencias abertas"),
]


def _funcoes():
    d = {}
    for mod in (au, a2, a3):
        for nome, fn in inspect.getmembers(mod, inspect.isfunction):
            if nome.startswith("checar_"):
                d[nome] = fn
    return d


def todas() -> list:
    """Todas as funcoes de verificacao dos dois blocos."""
    fs = _funcoes()
    return [fs[n] for n in sorted(fs)]


def executar() -> dict:
    """Roda tudo uma vez e devolve achados por funcao."""
    return {n: fn() for n, fn in sorted(_funcoes().items())}


def cobertura() -> dict:
    fs = _funcoes()
    por_sit = {}
    orfas = []
    usadas = set()
    for num, titulo, chks, sit, _ in PROGRAMA:
        por_sit[sit] = por_sit.get(sit, 0) + 1
        for c in chks:
            if c == "*":
                usadas |= set(fs)
            elif c in fs:
                usadas.add(c)
            else:
                orfas.append((num, c))
    return dict(situacoes=por_sit, funcoes=len(fs),
                funcoes_usadas=len(usadas),
                nao_referenciadas=sorted(set(fs) - usadas),
                referencias_quebradas=orfas,
                condicoes=sum(inspect.getsource(f).count("Achado(")
                              for f in fs.values()))


if __name__ == "__main__":
    res = executar()
    niveis = {"ERRO": 0, "ATENCAO": 0, "NOTA": 0}
    for achs in res.values():
        for a in achs:
            niveis[a.nivel] += 1
    cob = cobertura()
    print("=" * 72)
    print(f"PROGRAMA DE {len(PROGRAMA)} AUDITORIAS — COBERTURA")
    print("=" * 72)
    for sit in ("AUTOMATIZADA", "PARCIAL", "ANALISE", "BLOQUEADA"):
        n = cob["situacoes"].get(sit, 0)
        print(f"  {sit:14} {n:2} auditorias  ({n/len(PROGRAMA)*100:4.1f} %)")
    print(f"\n  {cob['funcoes']} funcoes de verificacao, {cob['condicoes']} condicoes")
    print(f"  {cob['funcoes_usadas']} funcoes referenciadas pelo programa")
    if cob["referencias_quebradas"]:
        print(f"  REFERENCIAS QUEBRADAS: {cob['referencias_quebradas']}")
    if cob["nao_referenciadas"]:
        print(f"  nao referenciadas: {', '.join(cob['nao_referenciadas'])}")
    print(f"\n  RESULTADO: {niveis['ERRO']} erro(s), {niveis['ATENCAO']} atencao(oes), "
          f"{niveis['NOTA']} nota(s)")
    print("=" * 72)
    for num, titulo, chks, sit, obs in PROGRAMA:
        achs = [a for c in chks if c in res for a in res[c]]
        mau = [a for a in achs if a.nivel != "NOTA"]
        marca = "!!" if mau else ("ok" if achs else "--")
        print(f"  {num:2} {marca} {sit:12} {titulo}")
        for a in mau:
            print(f"        {a.nivel}: {a.item} — {a.detalhe[:90]}")
