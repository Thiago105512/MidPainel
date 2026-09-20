"""VIABILIDADE — o que falta, quem fecha, e quanto do projeto depende disso.

Uma lista de pendencias diz o que falta. Ela nao diz a unica coisa que decide se
um projeto pode andar: QUANTO DELE DEPENDE DE CADA UMA. Um item aberto que
move 2 % do orcamento e uma nota de rodape; um que move 30 % e um risco de
contrato, e os dois aparecem iguais numa lista com bolinha.

Este modulo mede a EXPOSICAO de cada pendencia: a fatia do custo, da massa ou da
area que muda quando o dado chegar. E onde a mudanca e calculavel, ele a
calcula — o radier de 180 mm e parametro, entao da para perguntar o que
acontece se a sondagem pedir 250.

O QUE ELE NAO FAZ. Nao estima probabilidade de a pendencia dar certo ou errado.
Nao ha base para isso, e inventa-la transformaria uma medida em palpite com
aparencia de numero.
"""
from __future__ import annotations

# Portoes, em ordem de precedencia. Um projeto nao "esta viavel" em bloco: ele
# esta liberado para uma coisa e nao para outra, e confundir os dois e como se
# atrasa obra esperando o que nao precisava esperar.
PORTOES = (
    ("fabricacao", "cortar perfil e montar painel em fabrica"),
    ("obra", "abrir canteiro, fundar e erguer"),
    ("contrato", "assinar preco e prazo com fornecedor"),
)


def _brl(v: float) -> str:
    """R$ no padrao brasileiro.

    Existia, espalhado pelas simulacoes, o idioma `f"R$ {v:,.2f}".replace(",",
    ".")` aplicado a STRING INTEIRA. Ele acertava o separador de milhar e
    destruia toda virgula do texto em volta: a pendencia 13 dizia "comprados
    por REGRA de area. nao por calculo" porque a virgula da frase virou ponto.
    Formatar moeda e trabalho de uma funcao, nao de um replace sobre prosa.
    """
    return f"R$ {v:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _exposicao(pj, r: dict, n: str) -> dict:
    """Quanto do projeto muda quando ESTE dado chegar."""
    custo = r["custo"] or 1.0
    bom = r["bom"]
    def familia(*fs):
        return sum(i.total_compra for i in bom if i.familia in fs)

    if n == "2":       # sondagem e radier
        f = r["camadas"]["fundacao"]
        base = familia("fundacao")
        # o radier e parametro: da para perguntar quanto custa engrossar
        esp = f.get("espessura", 180)
        conc = next((i for i in bom if i.sku == "FUN-CONC"), None)
        delta = 0.0
        if conc:
            delta = conc.total_compra * (250.0 / esp - 1.0)
        return dict(valor=base, fracao=base / custo,
                    grandeza=f"{f.get('volume_m3', 0)} m3 de concreto e "
                             f"{f.get('aco_kg', 0)} kg de aco",
                    simulacao=f"se a sondagem pedir radier de 250 mm em vez de "
                              f"{esp}, o concreto sozinho sobe {_brl(delta)} "
                              f"({delta / custo * 100:.1f} % do total) — e a "
                              f"taxa de armadura pode subir junto")
    if n == "3":       # ART do calculo estrutural
        base = familia("estrutura", "ligacao")
        v = r["verificacao"]
        return dict(valor=base, fracao=base / custo,
                    grandeza=f"{v['n']} montantes verificados, utilizacao "
                             f"mediana {sorted(v['utilizacoes'])[v['n'] // 2]:.2f} "
                             f"e maxima {max(v['utilizacoes']):.2f}",
                    simulacao="o modelo ja verifica cada montante pela NBR "
                              "14762 com a carga que de fato desce. O que a ART "
                              "acrescenta e a RESPONSABILIDADE e a verificacao "
                              "do hibrido com perfil laminado, que este modelo "
                              "nao faz: flambagem lateral de viga laminada e o "
                              "apoio da caixa d'agua")
    if n == "8":       # nesting codificado
        pl = r["plano"]
        base = familia("estrutura")
        ap = pl["aproveitamento"]
        # se o nesting real render 80 % em vez do atual
        delta = base * (ap / 0.80 - 1.0)
        return dict(valor=base, fracao=base / custo,
                    grandeza=f"{pl['n_barras']} barras, aproveitamento "
                             f"{ap * 100:.1f} %",
                    simulacao=f"se o nesting da maquina real render 80 % em vez "
                              f"de {ap * 100:.1f} %, o aco sobe {_brl(delta)} "
                              f"({delta / custo * 100:.1f} %). O plano atual e "
                              f"de estudo: fecha a identidade bruto = usado + "
                              f"perda, e nao conhece a maquina")
    if n == "12":      # cotacao
        cob = r["cotacao"]["cobertura"]
        return dict(valor=custo, fracao=1.0,
                    grandeza=f"{cob['cotado_pct']:.0f} % do custo cotado",
                    simulacao="100 % do orcamento e (H). Nao ha simulacao "
                              "possivel: o valor inteiro e a exposicao, e e "
                              "por isso que esta pendencia tranca CONTRATO e "
                              "nao fabricacao")
    if n == "1":       # certidao do SU16
        return dict(valor=custo, fracao=1.0,
                    grandeza=f"taxa de ocupacao {pj.CADASTRO.area_m2 and ''}"
                             f"{r['camadas'].get('area_total', 0) and ''}"
                             "33,21 % contra 50 % adotados",
                    simulacao="se a certidao trouxer taxa menor que 33,21 % ou "
                              "gabarito abaixo de dois pavimentos, a "
                              "implantacao muda e TUDO e refeito. E a unica "
                              "pendencia cuja falha invalida o projeto inteiro, "
                              "e nao um sistema dele")
    if n in ("4", "5"):
        ext = familia("externo")
        return dict(valor=ext, fracao=ext / custo,
                    grandeza="reuso pluvial e retencao no lote",
                    simulacao="afeta cisterna, drenagem e area permeavel — o "
                              "bloco externo. Nao afeta a casa")
    if n == "6":
        ext = familia("externo", "fachada")
        return dict(valor=ext, fracao=ext / custo,
                    grandeza="fachada, muro, recuo e especie vegetal",
                    simulacao="regulamento de condominio mexe em fachada, muro "
                              "e paisagismo: e o bloco que R48 e R49 acabaram "
                              "de levantar, e por isso a exposicao agora e "
                              "mensuravel")
    if n == "7":
        el = r["camadas"]["instalacoes"]["eletrica"]
        base = sum(i.total_compra for i in bom if i.sku.startswith("MEP-"))
        return dict(valor=base, fracao=base / custo,
                    grandeza=f"{el['pontos']} pontos, {el['cabo_m']} m de cabo",
                    simulacao="sem trifasico, a demanda de 36,4 kVA precisa de "
                              "outro arranjo de circuitos e de padrao de "
                              "entrada: muda quadro e alimentador, nao muda a "
                              "casa")
    if n == "13":      # luminotecnica
        lum = sum(i.total_compra for i in bom if i.sku == "ELE-LUM")
        ele = familia("eletrica")
        return dict(valor=ele, fracao=ele / custo,
                    grandeza="luminaria, interruptor e ponto de luz",
                    simulacao=f"{_brl(lum)} de luminaria estao comprados por "
                              f"REGRA de area, nao por calculo. O "
                              f"luminotecnico nao muda a casa: muda quantas "
                              f"luminarias, de que fluxo, e onde — e pode "
                              f"dobrar ou reduzir pela metade a linha")
    if n == "14":      # rota de conformidade termica da parede externa
        import nucleo.termica as tm
        pe = next((l for l in tm.levantar(pj) if l["cod"] == "PE-1"), None)
        xps = sum(i.total_compra for i in bom if i.sku.startswith("XPS"))
        lim = pj.LIMITES_ZB8["parede_externa"]
        return dict(valor=xps, fracao=xps / custo,
                    grandeza="ISO strip de XPS na parede externa",
                    simulacao=f"a parede entrega U = {pe['u']:.3f} contra o "
                              f"U <= {lim['U']:.2f} da categoria, e e por ser "
                              f"boa demais para a linha que seu atraso de "
                              f"{pe['atraso_h']:.2f} h estoura os "
                              f"{lim['atraso']:.1f} h dela. Ler a NBR 15575-4 "
                              f"nao muda um parafuso da casa: decide se o "
                              f"caminho de aprovacao e a tabela prescritiva "
                              f"ou o criterio de transmitancia. Se um dia a "
                              f"resposta for que falta inercia, quem paga e "
                              f"esta linha — os {_brl(xps)} de XPS sao a "
                              f"unica camada do envelope que se discutiria")
    return dict(valor=0.0, fracao=0.0, grandeza="", simulacao="")


def avaliar(pj, r: dict) -> dict:
    """Pendencia a pendencia: quem fecha, o que muda, e quanto pesa."""
    itens = []
    for d in pj.PENDENCIAS:
        aberta = d["status"] == "ABERTA"
        ex = _exposicao(pj, r, d["n"]) if aberta else dict(
            valor=0.0, fracao=0.0, grandeza="", simulacao="")
        itens.append(dict(
            n=d["n"], titulo=d["titulo"], norma=d["norma"],
            impacto=d["impacto"], status=d["status"], bloqueia=d["bloqueia"],
            # a fracao vai com SEIS casas, e nao quatro: com quatro, o
            # arredondamento sozinho descolava fracao x custo da exposicao em
            # alguns reais, e a identidade entre as duas e o que permite
            # conferir que a exposicao foi medida contra o total e nao atribuida
            exposicao=round(ex["valor"], 2), fracao=round(ex["fracao"], 6),
            grandeza=ex["grandeza"], simulacao=ex["simulacao"]))
    abertas = [i for i in itens if i["status"] == "ABERTA"]
    portoes = []
    for cod, oq in PORTOES:
        trava = [i for i in abertas if i["bloqueia"] == cod]
        portoes.append(dict(
            portao=cod, o_que_libera=oq, travado=bool(trava),
            n=len(trava), itens=[i["n"] for i in trava],
            exposicao=round(sum(i["exposicao"] for i in trava), 2)))
    return dict(
        itens=itens, abertas=len(abertas), resolvidas=len(itens) - len(abertas),
        portoes=portoes,
        criterio="exposicao e a fatia do custo que muda quando o dado chegar, "
                 "nao a probabilidade de ele chegar errado. Probabilidade aqui "
                 "seria palpite com aparencia de numero",
        leitura="um projeto nao esta viavel em bloco: esta liberado para uma "
                "coisa e nao para outra. Confundir os dois e como se atrasa "
                "obra esperando o que nao precisava esperar")
