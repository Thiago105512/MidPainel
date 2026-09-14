"""DOCUMENTOS — memorial, manual e listas (secoes 52, 110, 152 a 154).

Nenhum numero destes documentos e digitado. O memorial de calculo mostra a
formula, o coeficiente, a clausula e a SUBSTITUICAO numerica — porque memorial
que so apresenta o resultado nao e memorial, e afirmacao.

Os tres modos de leitura da especificacao (educacional, especialista e
executivo) sao o MESMO conteudo com profundidade diferente, e nao textos
paralelos que divergem na terceira revisao.
"""
from __future__ import annotations

import nucleo.verificacao as vr
import nucleo.interop as io

MODOS = {
    "executivo": "custo, peso, prazo, progresso, risco e pendencia",
    "educacional": "por que a peca existe, que esforco recebe e o que a governa",
    "especialista": "formula, coeficiente, clausula e substituicao numerica",
}


def memorial_compressao(perfil, aco, L: float, modo: str = "especialista",
                        **kw) -> str:
    """Memorial de um montante comprimido, no nivel de profundidade pedido."""
    c = vr.compressao(perfil, aco, L=L, **kw)
    p = perfil.props()
    if modo == "executivo":
        return (f"{perfil.cod}: resiste {c['nrd']:.2f} kN em {L:.0f} mm. "
                f"Governa a flambagem {c['modo']}.")
    if modo == "educacional":
        return (
            f"O montante {perfil.cod} trabalha comprimido: recebe o peso do que\n"
            f"esta acima e tenta encurtar. Uma chapa de {perfil.t:.2f} mm nao\n"
            f"esmaga — ela ENCURVA antes, e por tres caminhos diferentes ao\n"
            f"mesmo tempo:\n"
            f"  global       a barra inteira encurva ou torce ({c['modo_global']})\n"
            f"  local        a {c['elemento_local']} ondula sozinha, esbeltez "
            f"{c['esbeltez_local']:.0f}\n"
            f"  distorcional a aba e o labio giram levando a forma junto\n"
            f"A resistencia e a MENOR das tres, e aqui governa a "
            f"{c['modo']}:\n  Nrd = {c['nrd']:.2f} kN.\n"
            f"Travar a parede no meio da altura reduz o comprimento de\n"
            f"flambagem e aumenta esse numero — e por isso que existe blocking.")
    return (
        f"MEMORIAL DE CALCULO — COMPRESSAO\n"
        f"Perfil {perfil.cod}   Aco {aco.cod}   L = {L:.0f} mm\n"
        f"NBR 14762:2010, anexo C (Metodo da Resistencia Direta)\n\n"
        f"1. Propriedades da secao (metodo linear, NBR 6355 anexo)\n"
        f"   A   = {p['A']:.2f} mm2        Ix  = {p['Ix']:.4e} mm4\n"
        f"   Iy  = {p['Iy']:.4e} mm4   J   = {p['J']:.2f} mm4\n"
        f"   Cw  = {p['Cw']:.4e} mm6   xo  = {p['xo']:.2f} mm\n"
        f"   ro  = {p['ro']:.2f} mm\n\n"
        f"2. Escoamento\n"
        f"   Ny = A.fy = {p['A']:.2f} x {aco.fy:.0f} / 1000 = {c['ny']:.2f} kN\n\n"
        f"3. Flambagem global elastica\n"
        f"   modo critico: {c['modo_global']}\n"
        f"   Ne = {c['ne']:.2f} kN\n"
        f"   lambda0 = raiz(Ny/Ne) = raiz({c['ny']:.2f}/{c['ne']:.2f}) = "
        f"{c['lam0']:.4f}\n"
        f"   {'lambda0 <= 1,5:  Nc = 0,658^(lambda0^2) . Ny' if c['lam0'] <= 1.5 else 'lambda0 > 1,5:   Nc = (0,877/lambda0^2) . Ny'}\n"
        f"   Nc = {c['modos']['global']:.2f} kN\n\n"
        f"4. Flambagem local\n"
        f"   elemento critico: {c['elemento_local']}, esbeltez "
        f"{c['esbeltez_local']:.1f}\n"
        f"   Nl = {c['nl']:.2f} kN      lambda_l = {c['laml']:.4f}\n"
        f"   Ncl = {c['modos']['local']:.2f} kN\n\n"
        f"5. Flambagem distorcional\n"
        f"   Nd (elastica) = {c['nd']:.2f} kN   lambda_d = {c['lamd']:.4f}\n"
        f"   Ndist = {c['modos']['distorcional']:.2f} kN\n"
        f"   {c['nota_distorcional']}\n\n"
        f"6. Resistencia de calculo\n"
        f"   Nc,Rk = min(global, local, distorcional) = {c['nrk']:.2f} kN "
        f"(governa a {c['modo']})\n"
        f"   Nc,Rd = Nc,Rk / gama = {c['nrk']:.2f} / {vr.GAMA:.2f} = "
        f"{c['nrd']:.2f} kN\n")


def lista_de_pecas(pecas: list) -> str:
    linhas = [dict(id=p.cod, familia=p.familia, perfil=p.perfil,
                   comprimento=f"{p.comp:.0f}", massa=f"{p.massa:.3f}",
                   painel=p.painel, pavimento=p.pav, furos=len(p.furos),
                   revisao=p.revisao) for p in pecas]
    return io.exportar("CSV", linhas,
                       ["id", "familia", "perfil", "comprimento", "massa",
                        "painel", "pavimento", "furos", "revisao"])


def plano_de_corte(plano: dict) -> str:
    linhas = []
    for b in plano["barras"]:
        linhas.append(dict(barra=b.cod, perfil=b.perfil, origem=b.origem,
                           bruto=f"{b.comp_bruto:.0f}", usado=f"{b.usado:.0f}",
                           perda=f"{b.perda:.0f}",
                           aproveitamento=f"{b.aproveitamento*100:.1f}",
                           pecas=" ".join(c for c, _ in b.pecas)))
    return io.exportar("CSV", linhas,
                       ["barra", "perfil", "origem", "bruto", "usado", "perda",
                        "aproveitamento", "pecas"])


def packing_list(carga: dict, paineis: list, cat_massa: dict) -> str:
    linhas = []
    for i, p in enumerate(paineis, 1):
        linhas.append(dict(pack=f"PACK-{(i-1)//12+1:03d}", painel=p.cod,
                           comp=f"{p.comp:.0f}", altura=f"{p.altura:.0f}",
                           massa=f"{p.massa(cat_massa):.1f}",
                           pecas=len(p.pecas), ordem_descarga=len(paineis) - i + 1))
    return io.exportar("CSV", linhas,
                       ["pack", "painel", "comp", "altura", "massa", "pecas",
                        "ordem_descarga"])


def manual_de_montagem(passos: list, modo: str = "educacional") -> str:
    out = ["# Manual de montagem", ""]
    if modo == "executivo":
        out.append(f"{len(passos)} passos, "
                   f"{passos[-1]['acumulado_h']:.0f} h de mao de obra.")
        return "\n".join(out)
    for p in passos:
        out.append(f"## Passo {p['passo']:03d} — {p['descricao']}")
        out.append(f"- tipo: {p['tipo']}")
        out.append(f"- ferramenta: {p['ferramenta']}")
        if p["massa"]:
            out.append(f"- massa a movimentar: {p['massa']:.1f} kg")
        out.append(f"- duracao estimada: {p['duracao_h']:.1f} h "
                   f"(acumulado {p['acumulado_h']:.1f} h, "
                   f"{p['progresso']*100:.0f} %)")
        out.append("")
    return "\n".join(out)


def relatorio_inspecao(pecas: list, amostra: int = 20) -> str:
    linhas = []
    for p in pecas[:amostra]:
        linhas.append(dict(peca=p.cod, item="comprimento",
                           nominal=f"{p.comp:.0f}", tolerancia="2.0",
                           medido="", status="A MEDIR"))
        for f in p.furos:
            linhas.append(dict(peca=p.cod, item="posicao de furo",
                               nominal=f"{f.x:.0f}", tolerancia="1.0",
                               medido="", status="A MEDIR"))
    return io.exportar("CSV", linhas,
                       ["peca", "item", "nominal", "tolerancia", "medido",
                        "status"])


def memorial_descritivo(pj, res: dict) -> str:
    c = pj.CADASTRO
    return (
        f"# Memorial descritivo — {c.nome}\n\n"
        f"{c.tipo.nome} de {c.pavimentos} pavimentos, {c.area_m2:.2f} m2, em "
        f"{c.localizacao}.\nSistema: {c.sistema}.\n\n"
        f"## Estrutura\n"
        f"{len(res['pecas'])} pecas de perfil formado a frio, "
        f"{res['massa_util']:.0f} kg uteis e {res['massa_comprada']:.0f} kg "
        f"comprados — a diferenca e a perda do plano de corte, que foi paga.\n"
        f"{len(res['paineis'])} paineis, aproveitamento de corte "
        f"{res['plano']['aproveitamento']*100:.1f} %.\n\n"
        f"## Montagem\n"
        f"{len(res['passos'])} passos, {res['horas']:.0f} h. Em nenhum deles a "
        f"estrutura fica instavel.\n\n"
        f"## Desempenho\n"
        f"CO2e incorporado {res['emissao']['total']:.0f} kg "
        f"({res['emissao']['total']/c.area_m2:.1f} kg/m2, fatores (H)); "
        f"desmontabilidade {res['desmontabilidade']['indice']:.2f} "
        f"({res['desmontabilidade']['classe']}).\n\n"
        f"## Situacao\n{res['liberacao']['situacao']}. "
        f"Score geral {res['score_geral']}/100.\n\n"
        f"Normas: {', '.join(c.normas[:8])} e outras {len(c.normas)-8}.\n")


def mapa_de_cotacao(mapa: dict, pj=None) -> str:
    """O documento que sai para o fornecedor (secao 136).

    Nao e o BOM. O BOM responde "quanto tem"; a cotacao pergunta "quanto
    custa", e para perguntar e preciso ESPECIFICAR. Por isso este documento
    carrega norma e formato em cada linha, e por isso ele termina com as
    lacunas: o que o modelo nao soube especificar nao pode ser cotado, e um
    preco recebido para uma linha mal especificada e pior que nenhum.
    """
    L = ["MAPA DE COTACAO",
         "=" * 78,
         f"Projeto: {getattr(getattr(pj, 'CADASTRO', None), 'nome', '—')}"
         f"   Revisao: {getattr(pj, 'EMISSAO', {}).get('revisao', '—')}",
         "",
         "COMO RESPONDER",
         f"  {mapa['instrucao']}.",
         f"  Minimo de {mapa['min_propostas']} propostas por item para que a "
         f"comparacao seja competitiva.",
         "",
         f"ITENS PARA COTACAO ({mapa['n']})",
         "-" * 78]
    for l in mapa["linhas"]:
        L.append(f"{l['sku']:<18} {l['quantidade']:>12,.2f} {l['unidade']:<4} "
                 f"{l['descricao'][:38]}")
        if l["especificacao"]:
            L.append(f"{'':<18} esp.: {l['especificacao']}")
        if l["normas"]:
            L.append(f"{'':<18} norma: {', '.join(l['normas'])}")
        if l["lacunas"]:
            for x in l["lacunas"]:
                L.append(f"{'':<18} FALTA: {x}")
        L.append(f"{'':<18} preco unitario: ____________  "
                 f"data: ____/____/______  validade: _____ dias  "
                 f"prazo: _____ dias")
    L += ["", f"ROTAS ALTERNATIVAS ({mapa['n_alternativas']}) — nao somar com "
              f"as de cima", "-" * 78]
    for l in mapa["alternativas"]:
        L.append(f"{l['sku']:<18} {l['quantidade']:>12,.2f} {l['unidade']:<4} "
                 f"{l['descricao'][:38]}")
    L += ["", f"LACUNAS DE ESPECIFICACAO ({mapa['n_lacunas']})", "-" * 78,
          "O que segue nao esta pronto para virar preco. Cotar assim mesmo "
          "produz",
          "numero comparavel com nada:"]
    for x in mapa["lacunas"]:
        L.append(f"  {x['sku']:<16} {'; '.join(x['faltam'])}")
    return "\n".join(L)
