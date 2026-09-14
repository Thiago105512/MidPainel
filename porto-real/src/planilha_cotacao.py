# -*- coding: utf-8 -*-
"""Planilha de cotacao do Projeto Porto Real, gerada do modelo parametrico."""
import json, unicodedata
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, FormulaRule, ColorScaleRule
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.comments import Comment

import os

AQUI = os.path.dirname(os.path.abspath(__file__))


def dados() -> dict:
    """Tudo sai do modelo. A planilha nao tem numero proprio — se a quantidade
    mudar no projeto, ela muda aqui na proxima geracao."""
    import fixture as fx
    import projeto as pj
    import nucleo.cotacao as ct
    import nucleo.mercado as mk
    r = fx.liberacao()
    mp = ct.mapa(r)
    return dict(
        itens=[dict(sku=i.sku, descricao=i.descricao, unidade=i.unidade,
                    quantidade=i.quantidade, preco_h=i.preco_unit,
                    familia=i.familia, fonte=i.fonte, compra=i.compra)
               for i in r["bom"]],
        mapa={l["sku"]: l for l in mp["linhas"]},
        alternativas=mp["alternativas"], instrucao=mp["instrucao"],
        min_propostas=mp["min_propostas"],
        fornecedores=mk.FORNECEDORES, indices=mk.INDICES,
        fora=mk.FORA_DO_ORCAMENTO, sem_praca=mk.SEM_PRACA_LOCAL,
        aderencia=mk.aderencia(pj, r),
        cobertura=mk.cobertura_de_fornecedores(r),
        area=pj.CADASTRO.area_m2, revisao=pj.EMISSAO["revisao"],
        pendencias=list(pj.PENDENCIAS))


D = dados()
ALVO = os.path.join(AQUI, "..", "out", "PORTO_REAL_COTACAO.xlsx")

def tx(s):
    """Acentua o que veio sem acento do modelo (o codigo e ASCII por decisao)."""
    return s

FONTE = "Arial"
AZUL = "1F3864"; AZUL_CLARO = "D9E2F3"; CINZA = "F2F2F2"
AMARELO = "FFF2CC"; VERDE = "E2EFDA"; VERMELHO = "FCE4E4"
TIT = Font(name=FONTE, size=16, bold=True, color=AZUL)
SUB = Font(name=FONTE, size=10, italic=True, color="595959")
CAB = Font(name=FONTE, size=9, bold=True, color="FFFFFF")
TXT = Font(name=FONTE, size=9)
TXT_B = Font(name=FONTE, size=9, bold=True)
TXT_IN = Font(name=FONTE, size=9, color="0000FF")   # entrada do usuario
FILL_CAB = PatternFill("solid", fgColor=AZUL)
FILL_IN = PatternFill("solid", fgColor=AMARELO)
FILL_CALC = PatternFill("solid", fgColor=CINZA)
FILL_TOT = PatternFill("solid", fgColor=AZUL_CLARO)
BORDA = Border(*[Side(style="thin", color="BFBFBF")] * 4)
WRAP = Alignment(wrap_text=True, vertical="top")
CTR = Alignment(horizontal="center", vertical="center")
MOEDA = 'R$ #,##0.00;[Red]-R$ #,##0.00;"—"'
MOEDA0 = 'R$ #,##0;[Red]-R$ #,##0;"—"'
NUM = '#,##0.00;-#,##0.00;"—"'
PCT = '0.0%;[Red]-0.0%;"—"'

wb = Workbook()

# =====================================================================
# 1. INSTRUCOES
# =====================================================================
ws = wb.active; ws.title = "INSTRUÇÕES"
ws.sheet_view.showGridLines = False
linhas = [
    ("PROJETO PORTO REAL — PLANILHA DE COTAÇÃO DE MATERIAIS", "titulo"),
    (f"Residência unifamiliar em Light Steel Frame · Manaus/AM · {D['area']:.2f} m² fechados · revisão {D['revisao']}", "sub"),
    ("", None),
    ("COMO USAR", "h"),
    ("1.", "Envie a aba ESPECIFICAÇÕES para cada fornecedor. É ela que torna o pedido cotável: quantidade sem especificação não é cotação, é palpite."),
    ("2.", "Peça no mínimo CINCO propostas por família (a aba FORNECEDORES já traz os nomes pesquisados, com praça)."),
    ("3.", "Lance o preço unitário de cada fornecedor nas colunas amarelas da aba COTAÇÃO. Só isso — o resto é calculado."),
    ("4.", "A planilha escolhe sozinha o menor preço, o fornecedor vencedor, o total por item, o total por família e o total da obra."),
    ("5.", "Confira a aba REFERÊNCIAS: ela compara o total obtido com índices públicos da praça. Orçamento fora da faixa é sinal de linha faltando, não de preço ruim."),
    ("", None),
    ("CÓDIGO DE CORES", "h"),
    ("AMARELO", "Célula de ENTRADA — é onde você digita. Nenhuma outra célula deve ser editada."),
    ("AZUL (texto)", "Valor digitado por você."),
    ("PRETO", "Valor calculado por fórmula."),
    ("CINZA", "Dado vindo do modelo do projeto (quantidade, especificação, norma). Não editar."),
    ("", None),
    ("REGRAS DE COTAÇÃO", "h"),
    ("Preço sem data não é preço.", "Toda proposta precisa de data, validade, prazo de entrega e condição de pagamento. Registre na aba FORNECEDORES."),
    ("Frete dentro do preço.", "Peça CIF Manaus. Em praça do Norte o frete chega a 30 % do valor final e aparecer depois inviabiliza a comparação."),
    ("Três propostas é o piso legal.", "Lei 14.133 art. 23 usa três como parâmetro de preço de mercado; cinco é a meta desta planilha."),
    ("Quantidade é do projeto.", "As quantidades saem do modelo paramétrico, não de estimativa. Perda de corte já está embutida onde a especificação diz."),
    ("", None),
    ("O QUE ESTA PLANILHA NÃO COBRE", "h"),
    ("", "A aba FORA DO ESCOPO lista nove frentes que NÃO estão aqui — louças, climatização, pintura, revestimento interno, marcenaria, mão de obra de acabamento, equipamento de piscina, projetos e BDI. Esta planilha cobre os sistemas construtivos modelados. Ignorar essa aba é o erro que custa caro: orçamento erra mais por linha faltando do que por preço alto."),
]
r = 1
for a, b in linhas:
    if b == "titulo":
        ws.cell(r, 1, a).font = TIT
    elif b == "sub":
        ws.cell(r, 1, a).font = SUB
    elif b == "h":
        c = ws.cell(r, 1, a); c.font = Font(name=FONTE, size=11, bold=True, color=AZUL)
    elif b is None:
        pass
    else:
        ws.cell(r, 1, a).font = TXT_B
        c = ws.cell(r, 2, b); c.font = TXT; c.alignment = WRAP
    r += 1
ws.column_dimensions["A"].width = 26
ws.column_dimensions["B"].width = 118
for rr in range(1, r):
    ws.row_dimensions[rr].height = None
ws.row_dimensions[1].height = 24

# =====================================================================
# 2. COTACAO
# =====================================================================
itens = [i for i in D["itens"] if i["compra"]]
ordem = {"estrutura": 1, "vedacao": 2, "cobertura": 3, "esquadria": 4,
         "fundacao": 5, "instalacao": 6, "ligacao": 7, "fachada": 8,
         "externo": 9, "servico": 10}
itens.sort(key=lambda i: (ordem.get(i["familia"], 99), -i["quantidade"] * i["preco_h"]))

ws = wb.create_sheet("COTAÇÃO")
ws.sheet_view.showGridLines = False
ws.freeze_panes = "E4"

cabs = ["ITEM", "FAMÍLIA", "DESCRIÇÃO", "UN", "QUANT.\nPROJETO", "PERDA\n%",
        "QUANT. A\nCOMPRAR", "PREÇO REF.\n(H)", "TOTAL REF.\n(H)",
        "FORN. 1", "FORN. 2", "FORN. 3", "FORN. 4", "FORN. 5",
        "Nº DE\nPROPOSTAS", "MENOR\nPREÇO", "FORNECEDOR\nVENCEDOR",
        "PREÇO\nMÉDIO", "DISPERSÃO\n(máx/mín)", "TOTAL\nCOTADO",
        "Δ vs REF.", "STATUS"]
ws.cell(1, 1, "COTAÇÃO DE MATERIAIS — preencha apenas as colunas amarelas").font = TIT
ws.cell(2, 1, "Quantidades geradas pelo modelo paramétrico do projeto. Preço de referência (H) é hipótese declarada, nunca base de contrato.").font = SUB
for j, c in enumerate(cabs, start=1):
    cel = ws.cell(3, j, c); cel.font = CAB; cel.fill = FILL_CAB
    cel.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
    cel.border = BORDA
ws.row_dimensions[3].height = 34

larg = [16, 12, 42, 6, 12, 8, 12, 12, 14, 11, 11, 11, 11, 11, 10, 12, 16, 12, 11, 14, 10, 11]
for j, w in enumerate(larg, start=1):
    ws.column_dimensions[get_column_letter(j)].width = w

lin0 = 4
for k, it in enumerate(itens):
    r = lin0 + k
    m = D["mapa"].get(it["sku"], {})
    ws.cell(r, 1, it["sku"]).font = TXT_B
    ws.cell(r, 2, it["familia"]).font = TXT
    c = ws.cell(r, 3, it["descricao"]); c.font = TXT; c.alignment = WRAP
    ws.cell(r, 4, it["unidade"]).font = TXT
    c = ws.cell(r, 5, round(it["quantidade"], 2)); c.font = TXT; c.number_format = NUM; c.fill = FILL_CALC
    c = ws.cell(r, 6, 0.0); c.font = TXT_IN; c.number_format = PCT; c.fill = FILL_IN
    c = ws.cell(r, 7, f"=E{r}*(1+F{r})"); c.font = TXT; c.number_format = NUM
    c = ws.cell(r, 8, it["preco_h"]); c.font = TXT; c.number_format = MOEDA; c.fill = FILL_CALC
    c = ws.cell(r, 9, f"=G{r}*H{r}"); c.font = TXT; c.number_format = MOEDA
    for j in range(10, 15):
        c = ws.cell(r, j); c.font = TXT_IN; c.number_format = MOEDA; c.fill = FILL_IN; c.border = BORDA
    c = ws.cell(r, 15, f"=COUNT(J{r}:N{r})"); c.font = TXT; c.alignment = CTR
    c = ws.cell(r, 16, f'=IF(O{r}=0,"",MIN(J{r}:N{r}))'); c.font = TXT_B; c.number_format = MOEDA
    c = ws.cell(r, 17, f'=IF(O{r}=0,"",INDEX($J$3:$N$3,MATCH(P{r},J{r}:N{r},0)))'); c.font = TXT
    c = ws.cell(r, 18, f'=IF(O{r}=0,"",AVERAGE(J{r}:N{r}))'); c.font = TXT; c.number_format = MOEDA
    c = ws.cell(r, 19, f'=IF(O{r}<2,"",MAX(J{r}:N{r})/P{r})'); c.font = TXT; c.number_format = '0.00"x"'
    c = ws.cell(r, 20, f'=IF(O{r}=0,"",G{r}*P{r})'); c.font = TXT_B; c.number_format = MOEDA
    c = ws.cell(r, 21, f'=IF(OR(O{r}=0,I{r}=0),"",T{r}/I{r}-1)'); c.font = TXT; c.number_format = PCT
    c = ws.cell(r, 22, f'=IF(O{r}=0,"PENDENTE",IF(O{r}>=5,"COMPLETO","PARCIAL"))'); c.font = TXT; c.alignment = CTR
    for j in range(1, 23):
        ws.cell(r, j).border = BORDA
    if m.get("especificacao"):
        cm = Comment(m["especificacao"][:900] +
                     ("\n\nNORMAS: " + ", ".join(m.get("normas", [])) if m.get("normas") else "") +
                     ("\n\nLACUNA: " + "; ".join(m.get("lacunas", [])) if m.get("lacunas") else ""),
                     "Modelo Porto Real", width=420, height=180)
        ws.cell(r, 3).comment = cm

rN = lin0 + len(itens)
ws.cell(rN, 3, "TOTAL GERAL").font = Font(name=FONTE, size=10, bold=True, color=AZUL)
for j, f in ((9, f"=SUM(I{lin0}:I{rN-1})"), (20, f"=SUM(T{lin0}:T{rN-1})")):
    c = ws.cell(rN, j, f); c.font = Font(name=FONTE, size=10, bold=True)
    c.number_format = MOEDA0; c.fill = FILL_TOT
c = ws.cell(rN, 21, f'=IF(T{rN}=0,"",T{rN}/I{rN}-1)')
c.font = Font(name=FONTE, size=10, bold=True); c.number_format = PCT; c.fill = FILL_TOT
for j in range(1, 23):
    ws.cell(rN, j).fill = FILL_TOT; ws.cell(rN, j).border = BORDA

ws.cell(rN + 2, 3, f"Itens: {len(itens)} · linhas cotáveis com especificação completa: {sum(1 for i in itens if D['mapa'].get(i['sku'],{}).get('cotavel'))} · com lacuna a esclarecer com o fornecedor: {sum(1 for i in itens if D['mapa'].get(i['sku'],{}).get('lacunas'))}").font = SUB
ws.cell(rN + 3, 3, "Passe o mouse sobre a DESCRIÇÃO para ver a especificação completa, as normas e a lacuna de cada item.").font = SUB

ws.conditional_formatting.add(f"V{lin0}:V{rN-1}",
    CellIsRule(operator="equal", formula=['"PENDENTE"'], fill=PatternFill("solid", fgColor=VERMELHO)))
ws.conditional_formatting.add(f"V{lin0}:V{rN-1}",
    CellIsRule(operator="equal", formula=['"PARCIAL"'], fill=PatternFill("solid", fgColor=AMARELO)))
ws.conditional_formatting.add(f"U{lin0}:U{rN-1}",
    CellIsRule(operator="greaterThan", formula=["0.15"], fill=PatternFill("solid", fgColor=VERMELHO)))
ws.conditional_formatting.add(f"U{lin0}:U{rN-1}",
    CellIsRule(operator="lessThan", formula=["-0.15"], fill=PatternFill("solid", fgColor=VERDE)))
ws.conditional_formatting.add(f"S{lin0}:S{rN-1}",
    CellIsRule(operator="greaterThan", formula=["1.5"], fill=PatternFill("solid", fgColor=VERMELHO)))
ws.conditional_formatting.add(f"V{lin0}:V{rN-1}",
    CellIsRule(operator="equal", formula=['"COMPLETO"'], fill=PatternFill("solid", fgColor=VERDE)))
ws.auto_filter.ref = f"A3:V{rN-1}"

# painel de progresso: quantos itens ja tem cinco propostas, e quanto do CUSTO
# eles representam — que e a pergunta util, porque item barato cotado nao
# adianta nada e item caro sem cotar decide o orcamento
ws.cell(2, 16, "PROGRESSO").font = Font(name=FONTE, size=9, bold=True, color=AZUL)
ws.cell(2, 17, f'=COUNTIF(V{lin0}:V{rN-1},"COMPLETO")&" de "&{rN-lin0}&" itens com 5 propostas"').font = TXT_B
c = ws.cell(2, 20, f'=IF(I{rN}=0,0,SUMIF(V{lin0}:V{rN-1},"COMPLETO",I{lin0}:I{rN-1})/I{rN})')
c.font = TXT_B; c.number_format = PCT
ws.cell(2, 21, "do custo").font = SUB

print("COTACAO ok", len(itens), "itens, total linha", rN)

# =====================================================================
# 3. RESUMO POR FAMILIA
# =====================================================================
ws = wb.create_sheet("RESUMO")
ws.sheet_view.showGridLines = False
ws.cell(1, 1, "RESUMO POR FAMÍLIA").font = TIT
ws.cell(2, 1, "Tudo aqui é fórmula sobre a aba COTAÇÃO: lançou um preço lá, muda aqui.").font = SUB
cab2 = ["FAMÍLIA", "ITENS", "TOTAL REF. (H)", "% DO CUSTO", "ABC",
        "TOTAL COTADO", "Δ vs REF.", "ITENS COTADOS", "COBERTURA"]
for j, c in enumerate(cab2, 1):
    cel = ws.cell(4, j, c); cel.font = CAB; cel.fill = FILL_CAB; cel.alignment = CTR; cel.border = BORDA
fams = []
for i in itens:
    if i["familia"] not in fams:
        fams.append(i["familia"])
fams.sort(key=lambda f: -sum(i["quantidade"] * i["preco_h"] for i in itens if i["familia"] == f))
r = 5
for f in fams:
    n = sum(1 for i in itens if i["familia"] == f)
    ws.cell(r, 1, f).font = TXT_B
    ws.cell(r, 2, n).font = TXT; ws.cell(r, 2).alignment = CTR
    c = ws.cell(r, 3, f"=SUMIF(COTAÇÃO!$B${lin0}:$B${rN-1},$A{r},COTAÇÃO!$I${lin0}:$I${rN-1})"); c.font = TXT; c.number_format = MOEDA0
    c = ws.cell(r, 4, f"=IF($C${5+len(fams)}=0,0,C{r}/$C${5+len(fams)})"); c.font = TXT; c.number_format = PCT
    c = ws.cell(r, 5, f'=IF(D{r}>=0.1,"A",IF(D{r}>=0.03,"B","C"))'); c.font = TXT; c.alignment = CTR
    c = ws.cell(r, 6, f"=SUMIF(COTAÇÃO!$B${lin0}:$B${rN-1},$A{r},COTAÇÃO!$T${lin0}:$T${rN-1})"); c.font = TXT; c.number_format = MOEDA0
    c = ws.cell(r, 7, f'=IF(OR(F{r}=0,C{r}=0),"",F{r}/C{r}-1)'); c.font = TXT; c.number_format = PCT
    c = ws.cell(r, 8, f'=COUNTIFS(COTAÇÃO!$B${lin0}:$B${rN-1},$A{r},COTAÇÃO!$O${lin0}:$O${rN-1},">0")'); c.font = TXT; c.alignment = CTR
    c = ws.cell(r, 9, f"=IF(B{r}=0,0,H{r}/B{r})"); c.font = TXT; c.number_format = PCT
    for j in range(1, 10):
        ws.cell(r, j).border = BORDA
    r += 1
rf = r
ws.cell(rf, 1, "TOTAL").font = Font(name=FONTE, size=10, bold=True, color=AZUL)
ws.cell(rf, 2, f"=SUM(B5:B{rf-1})").font = TXT_B; ws.cell(rf, 2).alignment = CTR
for j, col in ((3, "C"), (6, "F")):
    c = ws.cell(rf, j, f"=SUM({col}5:{col}{rf-1})"); c.font = Font(name=FONTE, size=11, bold=True); c.number_format = MOEDA0
c = ws.cell(rf, 4, f"=IF(C{rf}=0,0,SUM(D5:D{rf-1}))"); c.font = TXT_B; c.number_format = PCT
c = ws.cell(rf, 7, f'=IF(OR(F{rf}=0,C{rf}=0),"",F{rf}/C{rf}-1)'); c.font = TXT_B; c.number_format = PCT
c = ws.cell(rf, 8, f"=SUM(H5:H{rf-1})"); c.font = TXT_B; c.alignment = CTR
c = ws.cell(rf, 9, f"=IF(B{rf}=0,0,H{rf}/B{rf})"); c.font = TXT_B; c.number_format = PCT
for j in range(1, 10):
    ws.cell(rf, j).fill = FILL_TOT; ws.cell(rf, j).border = BORDA

r = rf + 2
ws.cell(r, 1, "INDICADORES").font = Font(name=FONTE, size=11, bold=True, color=AZUL)
base = r + 1
ind = [
    ("Área fechada do projeto (m²)", D["area"], NUM,
     "dado do modelo: soma dos ambientes fechados dos dois pavimentos"),
    ("Total adotado (cotado se houver; senão referência)",
     f"=IF(F{rf}=0,C{rf},F{rf})", MOEDA0,
     "enquanto não houver proposta, a planilha trabalha com o preço (H)"),
    ("Serviço (mão de obra de montagem já orçada)",
     f"=IF(F{rf}=0,SUMIF($A$5:$A${rf-1},\"servico\",$C$5:$C${rf-1}),"
     f"SUMIF($A$5:$A${rf-1},\"servico\",$F$5:$F${rf-1}))", MOEDA0, None),
    ("Material (total menos serviço)", f"=C{base+1}-C{base+2}", MOEDA0, None),
    ("Parcela de material na obra entregue", 0.60, PCT,
     "(H) de prática corrente. É a ponte entre orçamento de insumo e índice de obra pronta — mexa aqui para testar a sensibilidade"),
    ("Obra entregue estimada", f"=IF(C{base+4}=0,0,C{base+3}/C{base+4})", MOEDA0,
     "quanto a casa custaria pronta, incluindo o que NÃO está nesta planilha"),
    ("Custo desta planilha por m²", f"=C{base+1}/C{base}", MOEDA, None),
    ("Obra entregue estimada por m²", f"=IF(C{base}=0,0,C{base+5}/C{base})", MOEDA,
     "compare com a aba REFERÊNCIAS: tem de ficar ABAIXO do índice de obra entregue, porque o escopo daqui é menor"),
]
for k, (nome, val, fmt, obs) in enumerate(ind):
    rr = base + k
    ws.cell(rr, 1, nome).font = TXT_B
    c = ws.cell(rr, 3, val); c.font = TXT; c.number_format = fmt
    if nome.startswith("Parcela"):
        c.font = TXT_IN; c.fill = FILL_IN
    if obs:
        c2 = ws.cell(rr, 4, obs); c2.font = SUB; c2.alignment = WRAP
for j, w in enumerate([34, 8, 18, 14, 8, 18, 12, 14, 12], 1):
    ws.column_dimensions[get_column_letter(j)].width = w
ws.column_dimensions["D"].width = 62

# =====================================================================
# 4. ESPECIFICACOES (o que se manda ao fornecedor)
# =====================================================================
ws = wb.create_sheet("ESPECIFICAÇÕES")
ws.sheet_view.showGridLines = False
ws.freeze_panes = "A4"
ws.cell(1, 1, "ESPECIFICAÇÕES — o texto que vai ao fornecedor").font = TIT
ws.cell(2, 1, D["instrucao"]).font = SUB
cab3 = ["ITEM", "FAMÍLIA", "DESCRIÇÃO", "UN", "QUANTIDADE",
        "ESPECIFICAÇÃO PARA COTAÇÃO", "NORMAS", "LACUNA A ESCLARECER", "COTÁVEL"]
for j, c in enumerate(cab3, 1):
    cel = ws.cell(3, j, c); cel.font = CAB; cel.fill = FILL_CAB; cel.alignment = CTR; cel.border = BORDA
r = 4
for it in itens:
    m = D["mapa"].get(it["sku"], {})
    ws.cell(r, 1, it["sku"]).font = TXT_B
    ws.cell(r, 2, it["familia"]).font = TXT
    c = ws.cell(r, 3, it["descricao"]); c.font = TXT; c.alignment = WRAP
    ws.cell(r, 4, it["unidade"]).font = TXT
    c = ws.cell(r, 5, round(it["quantidade"], 2)); c.font = TXT; c.number_format = NUM
    c = ws.cell(r, 6, m.get("especificacao", "")); c.font = TXT; c.alignment = WRAP
    c = ws.cell(r, 7, ", ".join(m.get("normas", []))); c.font = TXT; c.alignment = WRAP
    c = ws.cell(r, 8, "; ".join(m.get("lacunas", []))); c.font = TXT; c.alignment = WRAP
    c = ws.cell(r, 9, "sim" if m.get("cotavel") else "com lacuna"); c.font = TXT; c.alignment = CTR
    for j in range(1, 10):
        ws.cell(r, j).border = BORDA
    r += 1
for j, w in enumerate([16, 12, 34, 6, 12, 72, 22, 46, 11], 1):
    ws.column_dimensions[get_column_letter(j)].width = w
ws.conditional_formatting.add(f"I4:I{r-1}",
    CellIsRule(operator="equal", formula=['"com lacuna"'], fill=PatternFill("solid", fgColor=AMARELO)))
ws.auto_filter.ref = f"A3:I{r-1}"

# rota alternativa: peca pronta em vez de barra
ws.cell(r + 1, 1, "ROTA ALTERNATIVA — peça cortada e furada em vez de barra").font = Font(name=FONTE, size=11, bold=True, color=AZUL)
ws.cell(r + 2, 1, "Estes itens NÃO entram no total: são a mesma estrutura comprada pronta. Cotar os dois e comparar contra o custo de corte próprio.").font = SUB
rr = r + 3
for j, c in enumerate(["ITEM", "DESCRIÇÃO", "UN", "QUANTIDADE", "ESPECIFICAÇÃO", "NORMAS"], 1):
    cel = ws.cell(rr, j, c); cel.font = CAB; cel.fill = FILL_CAB; cel.alignment = CTR; cel.border = BORDA
for a in D["alternativas"]:
    rr += 1
    ws.cell(rr, 1, a["sku"]).font = TXT_B
    c = ws.cell(rr, 2, a["descricao"]); c.font = TXT; c.alignment = WRAP
    ws.cell(rr, 3, a["unidade"]).font = TXT
    c = ws.cell(rr, 4, a["quantidade"]); c.font = TXT; c.number_format = NUM
    c = ws.cell(rr, 5, a.get("especificacao", "")); c.font = TXT; c.alignment = WRAP
    c = ws.cell(rr, 6, ", ".join(a.get("normas", []))); c.font = TXT
    for j in range(1, 7):
        ws.cell(rr, j).border = BORDA

# =====================================================================
# 5. FORNECEDORES
# =====================================================================
ws = wb.create_sheet("FORNECEDORES")
ws.sheet_view.showGridLines = False
ws.freeze_panes = "A4"
ws.cell(1, 1, "FORNECEDORES PESQUISADOS").font = TIT
ws.cell(2, 1, "Nomes levantados por pesquisa de mercado. Preço NÃO foi coletado: loja de material não publica valor em página indexável. Complete contato, proposta e prazo ao pedir.").font = SUB
cab4 = ["FAMÍLIA", "Nº", "FORNECEDOR", "PRAÇA", "O QUE FORNECE",
        "CONTATO", "TELEFONE / E-MAIL", "DATA DA PROPOSTA", "VALIDADE",
        "PRAZO DE ENTREGA", "FRETE INCLUSO?", "CONDIÇÃO DE PAGAMENTO", "OBSERVAÇÃO"]
for j, c in enumerate(cab4, 1):
    cel = ws.cell(3, j, c); cel.font = CAB; cel.fill = FILL_CAB; cel.alignment = CTR; cel.border = BORDA
r = 4
for fam in fams:
    lst = D["fornecedores"].get(fam, [])
    for n, (nome, praca, oque) in enumerate(lst, 1):
        ws.cell(r, 1, fam).font = TXT_B if n == 1 else TXT
        ws.cell(r, 2, n).font = TXT; ws.cell(r, 2).alignment = CTR
        ws.cell(r, 3, nome).font = TXT
        c = ws.cell(r, 4, praca); c.font = TXT
        if "Manaus" in praca:
            c.fill = PatternFill("solid", fgColor=VERDE); c.font = TXT_B
        c = ws.cell(r, 5, oque); c.font = TXT; c.alignment = WRAP
        for j in range(6, 14):
            cc = ws.cell(r, j); cc.font = TXT_IN; cc.fill = FILL_IN
        ws.cell(r, 8).number_format = "DD/MM/YYYY"
        ws.cell(r, 9).number_format = "DD/MM/YYYY"
        for j in range(1, 14):
            ws.cell(r, j).border = BORDA
        r += 1
dv = DataValidation(type="list", formula1='"sim,não,parcial"', allow_blank=True)
ws.add_data_validation(dv); dv.add(f"K4:K{r-1}")
for j, w in enumerate([12, 5, 34, 14, 40, 20, 24, 15, 12, 16, 13, 22, 28], 1):
    ws.column_dimensions[get_column_letter(j)].width = w
ws.cell(r + 1, 1, "Sem fabricante na praça de Manaus:").font = TXT_B
ws.cell(r + 1, 3, "; ".join(f"{k} — {v}" for k, v in D["sem_praca"].items())).font = SUB

# =====================================================================
# 6. REFERENCIAS (conferencia de cima para baixo)
# =====================================================================
ws = wb.create_sheet("REFERÊNCIAS")
ws.sheet_view.showGridLines = False
ws.cell(1, 1, "REFERÊNCIAS PÚBLICAS — a conferência de cima para baixo").font = TIT
ws.cell(2, 1, "Cinco propostas dizem se o preço de cada item está bom. O índice diz se o orçamento INTEIRO está no lugar certo — e é o erro de orçamento inteiro, não o de item, que quebra obra.").font = SUB
cab5 = ["ÍNDICE", "VALOR", "UNIDADE", "DATA", "PRAÇA", "FONTE", "ESCOPO (o que está dentro e o que não está)"]
for j, c in enumerate(cab5, 1):
    cel = ws.cell(4, j, c); cel.font = CAB; cel.fill = FILL_CAB; cel.alignment = CTR; cel.border = BORDA
r = 5
for i in D["indices"]:
    ws.cell(r, 1, i["nome"]).font = TXT_B
    c = ws.cell(r, 2, i["valor"]); c.font = TXT; c.number_format = MOEDA
    ws.cell(r, 3, i["unidade"]).font = TXT
    ws.cell(r, 4, i["data"]).font = TXT; ws.cell(r, 4).alignment = CTR
    ws.cell(r, 5, i["praca"]).font = TXT
    c = ws.cell(r, 6, i["fonte"]); c.font = TXT; c.alignment = WRAP
    c = ws.cell(r, 7, i["escopo"]); c.font = TXT; c.alignment = WRAP
    for j in range(1, 8):
        ws.cell(r, j).border = BORDA
    r += 1
r += 1
ws.cell(r, 1, "POSIÇÃO DESTE ORÇAMENTO").font = Font(name=FONTE, size=11, bold=True, color=AZUL)
r += 1
pos = [
    ("Obra entregue estimada por m² (da aba RESUMO)", "=RESUMO!C" + str(base + 7), MOEDA),
    ("Índice steel frame, padrão popular", D["indices"][2]["valor"], MOEDA),
    ("Índice steel frame, padrão médio", D["indices"][3]["valor"], MOEDA),
    ("CUB Amazonas R8-N", D["indices"][1]["valor"], MOEDA),
    ("Posição contra o padrão popular", f"=IF(B{r}=0,\"\",B{r}/B{r+1}-1)", PCT),
]
for k, (nome, val, fmt) in enumerate(pos):
    rr = r + k
    ws.cell(rr, 1, nome).font = TXT_B
    c = ws.cell(rr, 2, val); c.font = TXT; c.number_format = fmt
ws.cell(r + len(pos), 1, "Fator de praça (frete para o Norte)").font = TXT_B
c = ws.cell(r + len(pos), 2, 1.20); c.font = TXT_IN; c.fill = FILL_IN; c.number_format = '0.00"x"'
ws.cell(r + len(pos), 4, "Se os preços vierem de tabela do Sudeste, o total erra por este fator. Peça CIF Manaus e ele deixa de existir.").font = SUB
ws.cell(r + len(pos) + 2, 1,
        "LEITURA: o valor extrapolado TEM de ficar abaixo do índice de obra entregue, porque o escopo desta planilha é menor "
        "(ver aba FORA DO ESCOPO). Ficar ACIMA é sinal de erro — de quantidade, de preço ou de linha duplicada.").font = SUB
for j, w in enumerate([44, 16, 12, 10, 14, 30, 78], 1):
    ws.column_dimensions[get_column_letter(j)].width = w

# =====================================================================
# 7. FORA DO ESCOPO
# =====================================================================
ws = wb.create_sheet("FORA DO ESCOPO")
ws.sheet_view.showGridLines = False
ws.cell(1, 1, "O QUE NÃO ESTÁ NESTA PLANILHA").font = TIT
ws.cell(2, 1, "Esta planilha cobre os sistemas construtivos modelados. Orçamento erra mais por LINHA FALTANDO do que por preço alto — por isso a lista existe, e por isso ela é curta e explícita.").font = SUB
for j, c in enumerate(["ESCOPO FORA", "SITUAÇÃO NO PROJETO", "ORÇAR SEPARADAMENTE COM"], 1):
    cel = ws.cell(4, j, c); cel.font = CAB; cel.fill = FILL_CAB; cel.alignment = CTR; cel.border = BORDA
quem = {
    "loucas e metais": "loja de material / distribuidor de louças",
    "equipamento de climatizacao": "instalador de ar-condicionado (7 máquinas dimensionadas em projeto)",
    "pintura": "empreiteira de pintura — material e mão de obra",
    "revestimento interno de piso e parede": "loja de revestimento + assentador",
    "marcenaria e armarios": "marcenaria sob medida",
    "mao de obra de instalacoes e acabamento": "empreiteiro geral ou por frente",
    "equipamento de piscina": "fornecedor de piscina (bomba, filtro, tratamento)",
    "projetos complementares, ART e taxas": "projetista estrutural com ART, prefeitura, concessionárias",
    "BDI, administracao e canteiro": "construtora / administração da obra",
}
r = 5
for nome, sit in D["fora"]:
    c = ws.cell(r, 1, nome); c.font = TXT_B; c.alignment = WRAP
    c = ws.cell(r, 2, sit); c.font = TXT; c.alignment = WRAP
    c = ws.cell(r, 3, quem.get(nome, "")); c.font = TXT; c.alignment = WRAP
    for j in range(1, 4):
        ws.cell(r, j).border = BORDA; ws.cell(r, j).fill = PatternFill("solid", fgColor=VERMELHO)
    r += 1
for j, w in enumerate([36, 72, 52], 1):
    ws.column_dimensions[get_column_letter(j)].width = w
ws.cell(r + 1, 1, "PENDÊNCIAS DO PROJETO QUE AFETAM A COMPRA").font = Font(name=FONTE, size=11, bold=True, color=AZUL)
r += 2
for j, c in enumerate(["Nº", "PENDÊNCIA", "NORMA / ORIGEM", "TRAVA", "SITUAÇÃO"], 1):
    cel = ws.cell(r, j, c); cel.font = CAB; cel.fill = FILL_CAB; cel.alignment = CTR; cel.border = BORDA
r += 1
for p in D["pendencias"]:
    if p["status"] != "ABERTA":
        continue
    ws.cell(r, 1, p["n"]).font = TXT; ws.cell(r, 1).alignment = CTR
    c = ws.cell(r, 2, p["titulo"]); c.font = TXT_B; c.alignment = WRAP
    c = ws.cell(r, 3, p["norma"]); c.font = TXT; c.alignment = WRAP
    ws.cell(r, 4, p["bloqueia"]).font = TXT; ws.cell(r, 4).alignment = CTR
    c = ws.cell(r, 5, p["impacto"]); c.font = TXT; c.alignment = WRAP
    for j in range(1, 6):
        ws.cell(r, j).border = BORDA
    r += 1
ws.column_dimensions["D"].width = 14
ws.column_dimensions["E"].width = 60


# =====================================================================
# 8. PECAS E CORTE — o que o proprietario chamou de "cortes e tamanhos
#    padronizados". Nao e cotacao: e fabricacao. Mas e a mesma lista, e
#    quem cota perfil precisa saber que barra vai ser cortada em quantos
#    pedacos, e de que tamanhos.
# =====================================================================
import fixture as _fx
_r = _fx.liberacao()
ws = wb.create_sheet("PEÇAS E CORTE")
ws.sheet_view.showGridLines = False
ws.freeze_panes = "A5"
ws.cell(1, 1, "LISTA DE PEÇAS — agrupada por perfil e comprimento").font = TIT
ws.cell(2, 1, "O aço é comprado em barra de 6.000 mm e cortado. Esta é a lista de corte: cada linha é um tamanho padronizado e quantas vezes ele se repete.").font = SUB
pl = _r["plano"]
ws.cell(3, 1, f"{len(_r['pecas'])} peças · {pl['n_barras']} barras de 6.000 mm · aproveitamento {pl['aproveitamento']*100:.1f} % · perda {pl['perda']/1000:.1f} m").font = TXT_B
for j, c in enumerate(["PERFIL", "COMPRIMENTO (mm)", "QUANT. DE PEÇAS",
                       "FAMÍLIA ESTRUTURAL", "MASSA UNIT. (kg)",
                       "MASSA TOTAL (kg)"], 1):
    cel = ws.cell(4, j, c); cel.font = CAB; cel.fill = FILL_CAB
    cel.alignment = CTR; cel.border = BORDA
import collections as _co
grupo = _co.defaultdict(lambda: [0, 0.0, set()])
for pc in _r["pecas"]:
    g = grupo[(pc.perfil, int(round(pc.comp)))]
    g[0] += 1; g[1] += pc.massa; g[2].add(pc.familia)
r = 5
for (perf, comp), (n, massa, fams_) in sorted(
        grupo.items(), key=lambda kv: (kv[0][0], -kv[0][1])):
    ws.cell(r, 1, perf).font = TXT
    c = ws.cell(r, 2, comp); c.font = TXT; c.number_format = "#,##0"
    c = ws.cell(r, 3, n); c.font = TXT_B; c.alignment = CTR
    ws.cell(r, 4, ", ".join(sorted(fams_))).font = TXT
    c = ws.cell(r, 5, round(massa / n, 3)); c.font = TXT; c.number_format = "0.000"
    c = ws.cell(r, 6, f"=C{r}*E{r}"); c.font = TXT; c.number_format = NUM
    for j in range(1, 7):
        ws.cell(r, j).border = BORDA
    r += 1
ws.cell(r, 4, "TOTAL").font = TXT_B
c = ws.cell(r, 3, f"=SUM(C5:C{r-1})"); c.font = TXT_B; c.alignment = CTR
c = ws.cell(r, 6, f"=SUM(F5:F{r-1})"); c.font = TXT_B; c.number_format = NUM
for j in range(1, 7):
    ws.cell(r, j).fill = FILL_TOT; ws.cell(r, j).border = BORDA
ws.cell(r + 2, 1, "BARRAS POR PERFIL").font = Font(name=FONTE, size=11, bold=True, color=AZUL)
rr = r + 3
for j, c in enumerate(["PERFIL", "BARRAS DE 6.000 mm", "PEÇAS CORTADAS"], 1):
    cel = ws.cell(rr, j, c); cel.font = CAB; cel.fill = FILL_CAB; cel.alignment = CTR; cel.border = BORDA
por_perfil = _co.Counter(b.perfil for b in pl["barras"])
pecas_perfil = _co.Counter(pc.perfil for pc in _r["pecas"])
for perf, nb in sorted(por_perfil.items()):
    rr += 1
    ws.cell(rr, 1, perf).font = TXT
    c = ws.cell(rr, 2, nb); c.font = TXT_B; c.alignment = CTR
    c = ws.cell(rr, 3, pecas_perfil[perf]); c.font = TXT; c.alignment = CTR
    for j in range(1, 4):
        ws.cell(rr, j).border = BORDA
for j, w in enumerate([26, 18, 16, 30, 16, 16], 1):
    ws.column_dimensions[get_column_letter(j)].width = w
ws.auto_filter.ref = f"A4:F{r-1}"
ws.cell(rr + 2, 1, "Esta lista NÃO substitui o nesting codificado do fabricante (pendência 8): ela é de estudo, e o fabricante corta pela dele.").font = SUB

wb.save(ALVO)
print(f"  {os.path.abspath(ALVO)}  {os.path.getsize(ALVO)//1024} KB  (planilha de cotacao)")
