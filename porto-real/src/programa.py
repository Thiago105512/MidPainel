"""
PROGRAMA DE 63 AUDITORIAS — mapa de cobertura.

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
    print("PROGRAMA DE 63 AUDITORIAS — COBERTURA")
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
