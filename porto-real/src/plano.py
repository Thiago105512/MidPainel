#!/usr/bin/env python3
"""Gera a pagina do plano a partir de escopo.py — o plano tambem e vista do modelo."""
from __future__ import annotations
import collections, html, os, sys
import escopo

SIT = {
    "FEITO": ("Entregue", "feito", "ja existe no caderno R12"),
    "AUTO":  ("Autonomo", "auto", "eu construo sozinho: matematica, norma e codigo"),
    "HIP":   ("Hipotese", "hip", "eu construo, mas um numero vem de fora — entra marcado (H)"),
    "BLOQ":  ("Fronteira", "bloq", "depende do mundo externo — entrego o contrato"),
}

def e(s): return html.escape(str(s))

def main(destino):
    r = escopo.conferir()
    cont = r["situacoes"]
    bloco_ciclos = collections.Counter()
    bloco_etapas = collections.defaultdict(list)
    for cod, bl, tit, cic, dep, ent, ace in escopo.ETAPAS:
        bloco_ciclos[bl] += cic
        bloco_etapas[bl].append((cod, tit, cic, dep, ent, ace))
    total = sum(bloco_ciclos.values())
    sec_por_etapa = collections.defaultdict(list)
    for n, t, sit, et, nota in escopo.SECOES:
        sec_por_etapa[et].append(n)

    def faixa(nums):
        """[1,2,3,7] -> '1-3, 7' — a notacao de prancha, nao uma lista crua."""
        nums = sorted(nums); out = []; i = 0
        while i < len(nums):
            j = i
            while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1: j += 1
            out.append(f"{nums[i]}" if i == j else f"{nums[i]}–{nums[j]}")
            i = j + 1
        return ", ".join(out)

    # ---- regua de ciclos
    regua = []
    for bl in ("I", "II", "III", "IV", "V", "VI", "VII"):
        pct = bloco_ciclos[bl] / total * 100
        regua.append(
            f'<div class="seg seg-{bl.lower()}" style="flex:{bloco_ciclos[bl]}">'
            f'<span class="seg-bl">{bl}</span><span class="seg-n">{bloco_ciclos[bl]}</span></div>')

    # ---- tiles
    tiles = []
    for k in ("FEITO", "AUTO", "HIP", "BLOQ"):
        rot, cls, exp = SIT[k]
        tiles.append(
            f'<div class="tile t-{cls}"><div class="tile-n">{cont[k]}</div>'
            f'<div class="tile-r">{rot}</div><p class="tile-x">{e(exp)}</p></div>')

    # ---- etapas
    etapas_html = []
    for bl in ("I", "II", "III", "IV", "V", "VI", "VII"):
        etapas_html.append(
            f'<div class="bloco"><h3><span class="bl-num">Bloco {bl}</span>'
            f'{e(escopo.BLOCOS[bl])}</h3>'
            f'<p class="bl-meta">{bloco_ciclos[bl]} ciclos · '
            f'{len(bloco_etapas[bl])} etapa{"s" if len(bloco_etapas[bl])>1 else ""}</p></div>')
        for cod, tit, cic, dep, ent, ace in bloco_etapas[bl]:
            secs = sec_por_etapa.get(cod, [])
            barras = "".join('<i></i>' for _ in range(cic))
            etapas_html.append(f'''
<article class="etapa" id="{cod}">
  <div class="et-cab">
    <span class="et-cod">{cod}</span>
    <h4>{e(tit)}</h4>
    <span class="et-ciclos" title="{cic} ciclo(s) de trabalho">{barras}<em>{cic}</em></span>
  </div>
  <dl class="et-corpo">
    <dt>Entrega</dt><dd>{e(ent)}</dd>
    <dt>Aceite</dt><dd class="aceite">{e(ace)}</dd>
    <dt>Fecha</dt><dd class="secs">{("§ " + faixa(secs)) if secs else "—"}</dd>
    <dt>Depende</dt><dd class="secs">{e(dep)}</dd>
  </dl>
</article>''')

    # ---- tabela das 155 secoes
    linhas = []
    for n, t, sit, et, nota in escopo.SECOES:
        rot, cls, _ = SIT[sit]
        linhas.append(
            f'<tr><td class="num">{n}</td><td>{e(t)}</td>'
            f'<td><span class="chip c-{cls}">{rot}</span></td>'
            f'<td class="num et">{e(et)}</td><td class="nota">{e(nota)}</td></tr>')

    doc = TPL.format(
        tiles="\n".join(tiles), regua="".join(regua), total=total,
        autonomos=r["ciclos_autonomos"], etapas="\n".join(etapas_html),
        linhas="\n".join(linhas), n_etapas=len(escopo.ETAPAS),
        n_auto=cont["AUTO"], n_hip=cont["HIP"], n_bloq=cont["BLOQ"], n_feito=cont["FEITO"])
    open(destino, "w", encoding="utf-8").write(doc)
    print(f"  {destino}  {len(doc)//1024} KB")


TPL = r'''<title>Do Caderno à Fábrica</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Chivo:wght@600;700;900&family=IBM+Plex+Mono:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>
  :root{{
    --ground:#e9ecee; --surface:#ffffff; --sunk:#f3f5f6;
    --ink:#13171a; --ink-soft:#566068; --ink-faint:#879198;
    --rule:#c9d1d6; --rule-soft:#e0e5e8;
    --feito:#0a6a4a; --feito-bg:#e0efe9;
    --auto:#1a5f8f;  --auto-bg:#e0ebf3;
    --hip:#8a5c06;   --hip-bg:#f6ecd8;
    --bloq:#93382b;  --bloq-bg:#f7e6e2;
    --display:"Chivo",system-ui,sans-serif;
    --serif:"Source Serif 4",Georgia,serif;
    --mono:"IBM Plex Mono",ui-monospace,monospace;
  }}
  @media (prefers-color-scheme:dark){{
    :root:not([data-theme="light"]){{
      --ground:#121619; --surface:#1a1f23; --sunk:#151a1e;
      --ink:#e6eaec; --ink-soft:#9aa5ad; --ink-faint:#6e7a82;
      --rule:#2c343a; --rule-soft:#222a2f;
      --feito:#3fbf93; --feito-bg:#10261f;
      --auto:#5aa8dd;  --auto-bg:#10222e;
      --hip:#d8a33c;   --hip-bg:#2a2113;
      --bloq:#e08070;  --bloq-bg:#2c1814;
    }}
  }}
  :root[data-theme="dark"]{{
    --ground:#121619; --surface:#1a1f23; --sunk:#151a1e;
    --ink:#e6eaec; --ink-soft:#9aa5ad; --ink-faint:#6e7a82;
    --rule:#2c343a; --rule-soft:#222a2f;
    --feito:#3fbf93; --feito-bg:#10261f;
    --auto:#5aa8dd;  --auto-bg:#10222e;
    --hip:#d8a33c;   --hip-bg:#2a2113;
    --bloq:#e08070;  --bloq-bg:#2c1814;
  }}
  *{{box-sizing:border-box}}
  [hidden]{{display:none!important}}
  body{{margin:0;background:var(--ground);color:var(--ink);
    font-family:var(--serif);font-size:16.5px;line-height:1.62;
    -webkit-font-smoothing:antialiased}}
  .wrap{{max-width:1120px;margin:0 auto;padding-inline:20px}}
  .prosa{{max-width:66ch}}
  h1,h2,h3,h4{{font-family:var(--display);letter-spacing:-.015em;text-wrap:balance;margin:0}}
  p{{margin:0 0 1em}}
  .rot{{font-family:var(--mono);font-size:11px;letter-spacing:.16em;
    text-transform:uppercase;color:var(--ink-faint);margin:0 0 8px}}

  /* ---- abertura ---- */
  header{{border-bottom:1px solid var(--rule);background:var(--surface)}}
  .abre{{padding-block:44px 34px;display:grid;gap:26px}}
  h1{{font-size:clamp(34px,6vw,58px);font-weight:900;line-height:1.02}}
  .sub{{font-family:var(--serif);font-size:19px;color:var(--ink-soft);
    max-width:58ch;margin:0}}
  .tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
    gap:1px;background:var(--rule-soft);border:1px solid var(--rule-soft)}}
  .tile{{background:var(--surface);padding:16px 18px 18px}}
  .tile-n{{font-family:var(--mono);font-size:38px;font-weight:600;line-height:1;
    font-variant-numeric:tabular-nums}}
  .tile-r{{font-family:var(--display);font-weight:700;font-size:14px;
    letter-spacing:.04em;text-transform:uppercase;margin:6px 0 6px}}
  .tile-x{{font-size:13.5px;color:var(--ink-soft);margin:0;line-height:1.45}}
  .t-feito .tile-n,.t-feito .tile-r{{color:var(--feito)}}
  .t-auto  .tile-n,.t-auto  .tile-r{{color:var(--auto)}}
  .t-hip   .tile-n,.t-hip   .tile-r{{color:var(--hip)}}
  .t-bloq  .tile-n,.t-bloq  .tile-r{{color:var(--bloq)}}

  /* ---- secoes ---- */
  section{{padding-block:44px}}
  section + section{{border-top:1px solid var(--rule-soft)}}
  h2{{font-size:clamp(23px,3.4vw,32px);font-weight:700;margin-bottom:14px}}
  .lead{{font-size:18px;color:var(--ink-soft);max-width:62ch}}

  /* ---- regua de ciclos ---- */
  .regua{{display:flex;height:52px;border:1px solid var(--rule);
    background:var(--surface);margin:22px 0 10px;overflow:hidden}}
  .seg{{position:relative;border-right:1px solid var(--rule);
    display:flex;flex-direction:column;justify-content:center;align-items:center;
    gap:2px;min-width:34px}}
  .seg:last-child{{border-right:none}}
  .seg-bl{{font-family:var(--display);font-weight:700;font-size:12px;
    letter-spacing:.08em}}
  .seg-n{{font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);
    font-variant-numeric:tabular-nums}}
  .seg-i{{background:var(--auto-bg)}} .seg-ii{{background:var(--sunk)}}
  .seg-iii{{background:var(--auto-bg)}} .seg-iv{{background:var(--sunk)}}
  .seg-v{{background:var(--auto-bg)}} .seg-vi{{background:var(--sunk)}}
  .seg-vii{{background:var(--bloq-bg)}}
  .regua-leg{{font-family:var(--mono);font-size:11px;color:var(--ink-faint);
    display:flex;justify-content:space-between;letter-spacing:.03em}}

  /* ---- etapas ---- */
  .bloco{{margin:34px 0 14px;padding-bottom:8px;border-bottom:2px solid var(--ink)}}
  .bloco h3{{font-size:19px;font-weight:700;display:flex;gap:12px;
    align-items:baseline;flex-wrap:wrap}}
  .bl-num{{font-family:var(--mono);font-size:11px;letter-spacing:.14em;
    text-transform:uppercase;color:var(--ink-faint);font-weight:500}}
  .bl-meta{{font-family:var(--mono);font-size:11.5px;color:var(--ink-faint);margin:4px 0 0}}
  .etapa{{background:var(--surface);border:1px solid var(--rule-soft);
    border-left:3px solid var(--rule);margin-bottom:8px;padding:14px 18px 16px}}
  .et-cab{{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;
    margin-bottom:10px}}
  .et-cod{{font-family:var(--mono);font-weight:600;font-size:13px;
    color:var(--auto);letter-spacing:.04em}}
  .et-cab h4{{font-size:17px;font-weight:700;flex:1;min-width:180px}}
  .et-ciclos{{display:flex;gap:3px;align-items:center;margin-left:auto}}
  .et-ciclos i{{width:14px;height:9px;background:var(--auto);display:block;
    border-radius:1px}}
  .et-ciclos em{{font-family:var(--mono);font-size:11px;font-style:normal;
    color:var(--ink-faint);margin-left:5px;font-variant-numeric:tabular-nums}}
  .et-corpo{{display:grid;grid-template-columns:74px 1fr;gap:6px 16px;margin:0}}
  .et-corpo dt{{font-family:var(--mono);font-size:10px;letter-spacing:.1em;
    text-transform:uppercase;color:var(--ink-faint);padding-top:4px}}
  .et-corpo dd{{margin:0;font-size:15px;color:var(--ink-soft);line-height:1.5}}
  .et-corpo dd.aceite{{color:var(--ink);border-left:2px solid var(--feito);
    padding-left:11px}}
  .secs{{font-family:var(--mono)!important;font-size:12.5px!important}}
  @media (max-width:560px){{ .et-corpo{{grid-template-columns:1fr;gap:2px 0}}
    .et-corpo dt{{padding-top:8px}} }}

  /* ---- tabela das secoes ---- */
  .rolagem{{overflow-x:auto;border:1px solid var(--rule);background:var(--surface)}}
  table{{border-collapse:collapse;width:100%;min-width:640px;
    font-family:var(--display);font-size:13.5px}}
  th{{font-family:var(--mono);font-size:10px;letter-spacing:.12em;
    text-transform:uppercase;color:var(--ink-faint);text-align:left;
    padding:10px 12px;border-bottom:1px solid var(--rule);
    position:sticky;top:0;background:var(--surface)}}
  td{{padding:7px 12px;border-bottom:1px solid var(--rule-soft);vertical-align:top}}
  tr:last-child td{{border-bottom:none}}
  td.num{{font-family:var(--mono);font-variant-numeric:tabular-nums;
    color:var(--ink-faint);text-align:right;width:42px}}
  td.et{{text-align:left;color:var(--ink-soft);width:54px}}
  td.nota{{color:var(--ink-faint);font-size:12.5px;max-width:34ch}}
  .chip{{font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;
    text-transform:uppercase;padding:2px 7px;white-space:nowrap;
    border:1px solid currentColor;border-radius:2px}}
  .c-feito{{color:var(--feito);background:var(--feito-bg)}}
  .c-auto{{color:var(--auto);background:var(--auto-bg)}}
  .c-hip{{color:var(--hip);background:var(--hip-bg)}}
  .c-bloq{{color:var(--bloq);background:var(--bloq-bg)}}

  /* ---- regras ---- */
  .regras{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
    gap:22px 30px;margin-top:8px}}
  .regra h4{{font-size:16px;font-weight:700;margin-bottom:5px}}
  .regra p{{font-size:14.5px;color:var(--ink-soft);margin:0}}
  .regra{{border-top:2px solid var(--ink);padding-top:11px}}

  .destaque{{background:var(--surface);border:1px solid var(--rule);
    border-left:4px solid var(--feito);padding:20px 24px;margin-top:20px}}
  .destaque h3{{font-size:18px;font-weight:700;margin-bottom:8px}}
  .destaque p{{font-size:15.5px;color:var(--ink-soft)}}
  .destaque p:last-child{{margin-bottom:0}}
  code{{font-family:var(--mono);font-size:.88em;color:var(--ink)}}
  footer{{border-top:1px solid var(--rule);background:var(--surface);
    padding-block:26px 34px;font-size:13px;color:var(--ink-faint)}}
  footer p{{max-width:74ch}}
  @media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style>

<header>
  <div class="wrap abre">
    <div>
      <p class="rot">Porto Real · do desenho ao chão de fábrica</p>
      <h1>Do caderno à fábrica</h1>
      <p class="sub">As 155 seções da especificação, classificadas uma a uma, e as
      {n_etapas} etapas que as fecham. Nenhuma etapa se declara pronta sem a auditoria
      verde.</p>
    </div>
    <div class="tiles">{tiles}</div>
  </div>
</header>

<main class="wrap">

<section>
  <div class="prosa">
    <h2>O que muda de natureza</h2>
    <p class="lead">O caderno atual descreve <em>uma casa</em>. A especificação
    descreve <em>um sistema</em>. São coisas diferentes, e a diferença não se
    resolve acrescentando recursos.</p>
    <p><code>projeto.py</code> tem <b>159 tabelas e 53 funções</b>, e todas as 159
    descrevem a mesma residência em Manaus. Enquanto for assim, cada recurso novo
    — perfil, carga, painel, peça — nasce amarrado a esse caso e precisa ser
    escrito de novo no próximo projeto. Por isso a primeira etapa não acrescenta
    nada: ela <b>separa o motor do caso</b>.</p>
    <p>O teste de aceite da E0 é o mais severo do plano e o mais barato de rodar:
    depois de separar, as 35 pranchas têm de sair <b>idênticas byte a byte</b>. Se
    o desenho mudou, o motor está errado.</p>
  </div>
</section>

<section>
  <h2>Cronograma</h2>
  <p class="lead">Um <b>ciclo</b> é uma rodada completa de trabalho: escrever,
  construir as 35 pranchas, rodar a auditoria inteira, corrigir o que ela acusar e
  commitar. A régua está desenhada em escala — a largura de cada bloco é o número
  de ciclos que ele custa.</p>
  <div class="regua">{regua}</div>
  <div class="regua-leg"><span>0</span><span>{total} ciclos · {autonomos} deles sem depender de nada externo</span></div>
  {etapas}
</section>

<section>
  <h2>Como o plano se governa</h2>
  <div class="regras">
    <div class="regra">
      <h4>O critério de pronto é a verificação</h4>
      <p>Cada etapa entrega funções de auditoria novas, que passam a rodar em todas
      as seguintes. Hoje são 48 funções e 238 condições; ao fim do plano o número
      importa menos que a regra: recurso sem verificação não conta como entregue.</p>
    </div>
    <div class="regra">
      <h4>Todo número de fora entra marcado (H)</h4>
      <p>Preço, tempo de máquina, fator de emissão, ensaio de incêndio, lead time.
      Entram como hipótese declarada e viram pendência listada — nunca como
      verdade. São as {n_hip} seções de fronteira macia.</p>
    </div>
    <div class="regra">
      <h4>Explicar a decisão é transversal, não é etapa</h4>
      <p>A seção 20 pede que o sistema não seja caixa-preta. Isso não pode vir no
      fim: toda escolha — perfil, verga, ligação, nesting — nasce com as
      alternativas rejeitadas e o motivo, desde a primeira etapa que a produz.</p>
    </div>
    <div class="regra">
      <h4>A fronteira não recebe simulação</h4>
      <p>Para as {n_bloq} seções bloqueadas eu entrego o contrato — esquema, adaptador e
      teste — e o adaptador falha dizendo “sem fonte de dados”. Um número inventado
      ali seria pior que a ausência dele.</p>
    </div>
  </div>

  <div class="destaque">
    <h3>O que posso executar sem novo comando</h3>
    <p>Os blocos <b>I a VI</b> — {autonomos} dos {total} ciclos, {n_auto} seções
    classificadas como autônomas mais as {n_hip} de hipótese declarada. Não dependem
    de dado externo, de licença, de máquina nem de decisão sua: são matemática,
    norma e código, e cada uma termina com a auditoria verde e um commit.</p>
    <p>O que <b>precisa</b> de você, quando chegar a hora: catálogo do fabricante
    de perfis, tabela de preços, ficha da perfiladeira, sondagem do solo e a
    certidão do SU16 — as cinco já listadas como pendências abertas do caderno.</p>
  </div>
</section>

<section>
  <h2>As 155 seções, uma a uma</h2>
  <p class="lead">Classificação completa, com a etapa que fecha cada uma. Esta
  tabela não é redigida: é gerada de <code>escopo.py</code>, que confere sozinho se
  alguma seção ficou órfã ou se alguma etapa promete seção inexistente.</p>
  <div class="rolagem">
    <table>
      <thead><tr><th>§</th><th>Seção</th><th>Situação</th><th>Etapa</th><th>Nota</th></tr></thead>
      <tbody>{linhas}</tbody>
    </table>
  </div>
</section>

</main>

<footer>
  <div class="wrap">
    <p>Projeto Porto Real · revisão R12 · plano gerado por <code>python3 plano.py</code>
    a partir de <code>escopo.py</code>. Estado atual do modelo: 48 funções de
    verificação, 238 condições, 0 erros, 35 pranchas, nenhuma desenhando fora da
    moldura. Este plano não libera fabricação: continuam abertas as pendências de
    ART/RRT, sondagem e nesting codificado.</p>
  </div>
</footer>
'''

if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else os.path.join("..", "out", "plano.html")
    main(alvo)
