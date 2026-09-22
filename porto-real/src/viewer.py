#!/usr/bin/env python3
"""Visualizador do caderno: 35 pranchas em 2D + o modelo em 3D, num HTML unico.

O visualizador nao e um anexo: e a trigesima sexta vista do mesmo modelo. Os
numeros do cabecalho, o historico de revisoes e as pendencias NAO sao digitados
aqui — sao lidos de projeto.py, pranchas7.py e programa.py, pelo mesmo motivo
que uma prancha nao pode divergir da outra. Somente o texto editorial de cada
prancha (o que ela mostra, e as quatro chaves de leitura) vive num arquivo de
dados, viewer_texto.json, porque e redacao, nao geometria.

Uso:  python3 viewer.py [destino.html]
"""
from __future__ import annotations

import json
import os

import projeto as pj
import pranchas7 as p7
import programa as pg
import especificacao as ep
import viewer_parte2 as v2
import viewer_parte3 as v3
import viewer_parte4 as v4
import viewer_parte5 as v5
import viewer_parte6 as v6

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "..", "out", "porto-real-caderno.html")
TRES = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
# R60 — o three.js vai EMBUTIDO no HTML quando o arquivo vendorizado existe.
# Um visualizador que depende de CDN e um visualizador que nao abre no
# celular do proprietario sem sinal, nem no container de teste, nem daqui a
# dez anos quando a URL mudar. O caderno e um arquivo so, e continua sendo.
TRES_VENDOR = os.path.join(AQUI, "vendor", "three.min.js")


def _script_three() -> str:
    if os.path.exists(TRES_VENDOR):
        with open(TRES_VENDOR, encoding="utf-8") as f:
            return "<script>/* three.js r128 — MIT — embutido (R60) */\n" + f.read() + "\n</script>"
    return f'<script src="{TRES}"></script>'


# ---------------------------------------------------------------------------
# dados derivados do modelo
# ---------------------------------------------------------------------------
def _br(v: float, casas: int = 2) -> str:
    return f"{v:,.{casas}f}".replace(",", "@").replace(".", ",").replace("@", ".")


def figuras() -> list[tuple[str, str, str]]:
    """Os oito numeros do cabecalho, todos calculados, nenhum digitado."""
    fechado = sum(a.area_mod for a in pj.TERREO) + sum(a.area_mod for a in pj.SUPERIOR)
    coberta = pj.projecao_coberta_m2()
    taxa = coberta / pj.LOTE_AREA_M2 * 100
    btu = sum(c["capacidade"] for c in pj.CLIMATIZACAO if not c.get("reserva"))
    el = pj.demanda_eletrica()
    cob = pg.cobertura()
    erros = sum(1 for v in pg.executar().values() for a in v if a.nivel == "ERRO")
    eixo = pj.eixo_visual()
    return [
        ("Fechado total", _br(fechado), "m²"),
        ("Projeção coberta", _br(coberta), "m²"),
        ("Taxa de ocupação", _br(taxa), "% · máx 50"),
        ("Climatização", _br(btu / 1000, 0), "mil BTU/h"),
        ("Demanda elétrica", _br(el["demanda_va"] / 1000, 1),
         f"kVA · {el['padrao_a']} A"),
        ("Auditoria", str(cob["condicoes"]), f"condições · {erros} erro"),
        ("Eixo social", _br(eixo["profundidade_total"] / 1000, 1), "m contínuos"),
        ("Pranchas", p7.TOTAL_PRANCHAS, "· A1"),
    ]


def fichas() -> dict:
    """O que a interface mostra ao clicar num ambiente da planta.

    Nada aqui e redigido: forro vem de especificacao, climatizacao e paginacao
    vem de projeto. Clicar na COZINHA devolve o que as pranchas 11, 16, 24 e 28
    ja dizem sobre ela — sem que o leitor precise ir ate elas."""
    forro = {c: d for c, d, *_ in ep.FORROS}
    clima: dict[str, list] = {}
    for c in pj.CLIMATIZACAO:
        clima.setdefault(c["amb"], []).append(c)
    zona = {}
    for z in pj.ZONAS_PAGINACAO:
        for a in z.get("ambientes", []):
            zona.setdefault(a, []).append(z["cod"])
    out = {}
    for a in pj.TERREO + pj.SUPERIOR + pj.TERREO_ABERTO + pj.SUPERIOR_ABERTO:
        f = {}
        if a.cod in forro:
            f["forro"] = forro[a.cod]
        if a.cod in clima:
            btu = sum(c["capacidade"] for c in clima[a.cod])
            f["climatização"] = f"{btu:,} BTU/h".replace(",", ".") + \
                                f" · {clima[a.cod][0]['tipo']}"
        if a.cod in zona:
            f["paginação"] = ", ".join(zona[a.cod])
        if getattr(a, "molhado", False):
            f["revestimento"] = "impermeabilizado; ver prancha 22/23"
        if f:
            out[a.cod] = f
    return out


def dados() -> dict:
    """Tudo o que o HTML precisa, montado a partir do modelo."""
    sheets = json.load(open(os.path.join(AQUI, "viewer_texto.json"), encoding="utf-8"))
    pend = [(n, f"{t} — {ond}", st) for n, t, _norma, ond, st in p7.PENDENCIAS]
    return dict(sheets=sheets, figures=figuras(), pend=pend,
                fichas=fichas(),
                revisoes=[list(r) for r in pj.REVISOES],
                revisao=pj.EMISSAO["revisao"])


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
HEAD = r'''<title>Caderno Porto Real</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
  :root{
    --ground:#eef0f2; --surface:#ffffff; --stage:#dfe3e7;
    --ink:#16191d; --ink-soft:#5c666f; --ink-faint:#8b949c;
    --rule:#cfd5da; --rule-soft:#e3e7ea;
    --accent:#0a6a4a; --accent-soft:#e2f0ea;
    --alert:#b3261e; --alert-soft:#fbe9e7;
    --ok:#0a6a4a; --ok-soft:#e2f0ea;
    --shadow:0 1px 2px rgba(18,24,30,.10), 0 8px 28px rgba(18,24,30,.10);
    --display:"Archivo",system-ui,sans-serif;
    --body:"IBM Plex Sans",system-ui,sans-serif;
    --mono:"IBM Plex Mono",ui-monospace,monospace;
  }
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]){
      --ground:#15181b; --surface:#1d2125; --stage:#0e1113;
      --ink:#e8eaec; --ink-soft:#9aa4ad; --ink-faint:#6d777f;
      --rule:#2e353b; --rule-soft:#23282d;
      --accent:#2fbf8f; --accent-soft:#12291f;
      --alert:#ff7a6d; --alert-soft:#2b1614;
      --ok:#2fbf8f; --ok-soft:#12291f;
      --shadow:0 1px 2px rgba(0,0,0,.5), 0 10px 30px rgba(0,0,0,.45);
    }
  }
  :root[data-theme="dark"]{
    --ground:#15181b; --surface:#1d2125; --stage:#0e1113;
    --ink:#e8eaec; --ink-soft:#9aa4ad; --ink-faint:#6d777f;
    --rule:#2e353b; --rule-soft:#23282d;
    --accent:#2fbf8f; --accent-soft:#12291f;
    --alert:#ff7a6d; --alert-soft:#2b1614;
    --ok:#2fbf8f; --ok-soft:#12291f;
    --shadow:0 1px 2px rgba(0,0,0,.5), 0 10px 30px rgba(0,0,0,.45);
  }

  *{box-sizing:border-box}
  body{
    margin:0; background:var(--ground); color:var(--ink);
    font-family:var(--body); font-size:15px; line-height:1.55;
    -webkit-font-smoothing:antialiased;
  }
  .wrap{max-width:1440px; margin:0 auto; padding-inline:20px; padding-block:0}

  header{border-bottom:1px solid var(--rule); background:var(--surface)}
  .head{
    display:flex; flex-wrap:wrap; gap:20px 32px;
    align-items:flex-end; justify-content:space-between;
    padding-block:22px 18px;
  }
  .id h1{
    font-family:var(--display); font-weight:700; font-size:clamp(26px,4vw,38px);
    letter-spacing:-.02em; margin:0; text-wrap:balance;
  }
  .id p{margin:4px 0 0; color:var(--ink-soft); font-size:14px}
  .eyebrow{
    font-family:var(--mono); font-size:11px; letter-spacing:.14em;
    text-transform:uppercase; color:var(--accent); margin:0 0 2px;
  }
  .stamp{
    border:1px solid var(--alert); color:var(--alert); background:var(--alert-soft);
    font-family:var(--mono); font-size:11px; line-height:1.35; letter-spacing:.04em;
    padding:8px 12px; max-width:290px;
  }
  .stamp b{display:block; letter-spacing:.1em; text-transform:uppercase}

  .figures{
    display:grid; grid-template-columns:repeat(auto-fit,minmax(132px,1fr));
    border-top:1px solid var(--rule-soft); background:var(--surface);
  }
  .fig{padding:14px 18px; border-right:1px solid var(--rule-soft)}
  .fig:last-child{border-right:none}
  .fig dt{
    font-family:var(--mono); font-size:10.5px; letter-spacing:.1em;
    text-transform:uppercase; color:var(--ink-faint); margin:0 0 3px;
  }
  .fig dd{
    margin:0; font-family:var(--mono); font-variant-numeric:tabular-nums;
    font-size:19px; font-weight:500; letter-spacing:-.01em;
  }
  .fig dd span{font-size:12px; color:var(--ink-soft); font-weight:400}

  .work{display:grid; grid-template-columns:246px 1fr; gap:22px; padding-block:22px 32px; align-items:start}
  @media (max-width:860px){ .work{grid-template-columns:1fr} }

  .rail h2, .notes h2{
    font-family:var(--mono); font-size:10.5px; letter-spacing:.13em;
    text-transform:uppercase; color:var(--ink-faint);
    margin:0 0 10px; font-weight:500;
  }
  /* min-width:0 nao e detalhe: item de grid tem min-width AUTO por padrao, e
     por isso a coluna crescia ate o min-content da lista horizontal de 35
     pranchas. A 390 px a pagina inteira rolava na horizontal — 489 px de
     conteudo num visor de 390 — e o efeito era o caderno "escorregando" para
     o lado no telefone. */
  .rail{position:sticky; top:12px; max-height:calc(100vh - 24px); overflow-y:auto;
        padding-right:4px; min-width:0}
  .work > *{min-width:0}
  @media (max-width:860px){ .rail{position:static; max-height:none} }
  .sheets{list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:3px}
  .sheets .group{
    font-family:var(--mono); font-size:10px; letter-spacing:.13em;
    text-transform:uppercase; color:var(--accent);
    padding:12px 0 4px; border-top:1px solid var(--rule-soft); margin-top:5px;
  }
  .sheets li:first-child .group{border-top:none; margin-top:0; padding-top:0}
  @media (max-width:860px){
    .sheets{flex-direction:row; overflow-x:auto; padding-bottom:8px; gap:8px;
            min-width:0}
    .sheets li{flex:0 0 198px; min-width:0}
    .sheets .group{display:none}
  }
  .sheets button{
    width:100%; display:grid; grid-template-columns:30px 1fr; gap:10px; align-items:center;
    background:none; border:1px solid transparent; border-radius:2px;
    padding:6px 8px; cursor:pointer; text-align:left; color:inherit;
    font-family:inherit; font-size:12.5px; line-height:1.3;
  }
  .sheets button:hover{background:var(--rule-soft)}
  .sheets button[aria-current="true"]{background:var(--accent-soft); border-color:var(--accent)}
  .sheets button:focus-visible{outline:2px solid var(--accent); outline-offset:1px}
  .sheets .num{
    font-family:var(--mono); font-size:11px; font-weight:600; letter-spacing:.02em;
    color:var(--ink-faint); text-align:right;
  }
  .sheets button[aria-current="true"] .num{color:var(--accent)}
  .sheets .esc{display:block; font-family:var(--mono); font-size:10.5px; color:var(--ink-faint)}

  .stage-box{border:1px solid var(--rule); background:var(--surface); box-shadow:var(--shadow)}
  .toolbar{display:flex; flex-wrap:wrap; gap:10px; align-items:center;
           padding:9px 12px; border-bottom:1px solid var(--rule-soft)}
  .toolbar .title{font-family:var(--display); font-weight:600; font-size:15px;
                  margin-right:auto; letter-spacing:-.01em}
  .toolbar .title small{display:block; font-family:var(--mono); font-weight:400;
    font-size:10.5px; color:var(--ink-faint); letter-spacing:.06em; text-transform:uppercase}
  .btn{font-family:var(--mono); font-size:11.5px; letter-spacing:.03em;
       border:1px solid var(--rule); background:var(--surface); color:var(--ink);
       padding:5px 10px; cursor:pointer; border-radius:2px}
  .btn:hover{border-color:var(--accent); color:var(--accent)}
  .btn:focus-visible{outline:2px solid var(--accent); outline-offset:1px}
  .zoomval{font-family:var(--mono); font-size:11.5px; color:var(--ink-soft);
           font-variant-numeric:tabular-nums; min-width:52px; text-align:center}
  .stage{position:relative; overflow:hidden; background:var(--stage);
         height:min(72vh,660px); cursor:grab; touch-action:none}
  .stage.dragging{cursor:grabbing}
  .stage img{position:absolute; top:0; left:0; transform-origin:0 0;
    background:#fff; box-shadow:0 2px 10px rgba(0,0,0,.28);
    max-width:none; user-select:none; -webkit-user-drag:none}
  .hint{padding:7px 12px; border-top:1px solid var(--rule-soft);
        font-family:var(--mono); font-size:10.5px; color:var(--ink-faint); letter-spacing:.03em;
        margin:0}

  .notes{margin-top:22px}
  .note-grid{display:grid; grid-template-columns:1fr 1fr; gap:0 28px}
  @media (max-width:720px){ .note-grid{grid-template-columns:1fr} }
  .notes p{margin:0 0 12px; max-width:64ch}
  .notes .lead{font-size:16px}
  .keys{list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:0}
  .keys li{display:grid; grid-template-columns:auto 1fr; gap:14px;
    padding:9px 0; border-top:1px solid var(--rule-soft); align-items:baseline}
  .keys li:first-child{border-top:none}
  .keys .k{font-family:var(--mono); font-size:12px; font-variant-numeric:tabular-nums;
           color:var(--accent); font-weight:500; white-space:nowrap}
  .keys .v{font-size:13.5px; color:var(--ink-soft)}

  footer{border-top:1px solid var(--rule); background:var(--surface); margin-top:8px}
  .foot{padding-block:22px 30px; display:grid; gap:26px}
  .foot h2{font-family:var(--mono); font-size:10.5px; letter-spacing:.13em;
    text-transform:uppercase; color:var(--ink-faint); margin:0 0 12px; font-weight:500}
  .revs{list-style:none; margin:0; padding:0;
        display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:0 26px}
  .revs li{display:grid; grid-template-columns:40px 1fr; gap:8px;
           padding:7px 0; border-top:1px solid var(--rule-soft); font-size:13px}
  .revs .r{font-family:var(--mono); font-size:11.5px; color:var(--accent); font-weight:500}
  .pend{list-style:none; margin:0; padding:0;
        display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:0 26px}
  .pend li{display:grid; grid-template-columns:20px 1fr auto; gap:10px;
           padding:7px 0; border-top:1px solid var(--rule-soft); font-size:13px;
           align-items:baseline}
  .pend .n{font-family:var(--mono); font-size:11px; color:var(--ink-faint)}
  .pend .s{font-family:var(--mono); font-size:9.5px; letter-spacing:.1em;
           padding:2px 6px; border:1px solid currentColor; white-space:nowrap}
  .pend .s.aberta{color:var(--alert); background:var(--alert-soft)}
  .pend .s.resolvida{color:var(--ok); background:var(--ok-soft)}
  .colofon{font-size:12.5px; color:var(--ink-faint); max-width:76ch; margin:0}
  .colofon code{font-family:var(--mono); font-size:11.5px; color:var(--ink-soft)}
  .colofon + .colofon{margin-top:10px}
  @media (prefers-reduced-motion:reduce){ *{transition:none!important; animation:none!important} }

  /* ---------- celular (R76): o caderno cabe na mao ----------
     A pagina ja nao rolava de lado; o que faltava era o desenho comecar
     acima da dobra, uma navegacao que nao fosse uma fita de 69 botoes e
     zoom de pinca. Nada aqui muda o desktop. */
  .selnav{display:none}
  @media (max-width:860px){
    .wrap{padding-inline:14px}
    .head{padding-block:12px 10px; gap:8px}
    .head h1{font-size:26px; margin:2px 0}
    .stamp{max-width:none; font-size:10.5px; padding:6px 10px}
    .figures{display:flex; overflow-x:auto; scroll-snap-type:x proximity;
             -webkit-overflow-scrolling:touch; scrollbar-width:thin}
    .fig{flex:0 0 46%; scroll-snap-align:start; padding:9px 12px}
    .fig dd{font-size:16px}
    .rail{display:none}
    .work{padding-block:10px 20px; gap:12px}
    .stage-box{margin-inline:-6px}
    .toolbar{position:sticky; top:env(safe-area-inset-top,0px); z-index:6;
             background:var(--surface); gap:6px; padding:7px 8px}
    .toolbar .title{flex:1 1 100%; order:-1; font-size:14px}
    .btn{padding:7px 9px; font-size:11px; min-height:38px}
    .selnav{display:flex; gap:6px; flex:1 1 100%; align-items:stretch; min-width:0; width:100%}
    .selnav select{flex:1 1 0; width:100%; min-width:0; font-family:var(--mono); font-size:12px;
      padding:8px; border:1px solid var(--rule); border-radius:2px;
      background:var(--surface); color:var(--ink); min-height:38px}
    /* no celular a barra guarda so o essencial: setas de prancha, "sem
       moldura" e "medir" ficam atras do botao Paineis, com as camadas */
    #prev, #next, #semmold, #medir{display:none}
    #barra2, .hud, .leitura{display:none !important}
    .stage-box.paineis #barra2, .stage-box.paineis .leitura{display:block !important}
    .stage-box.paineis .hud{display:flex !important}
    .stage-box.paineis #semmold, .stage-box.paineis #medir{display:inline-block}
    .selnav .btn[aria-pressed="true"]{border-color:var(--accent); color:var(--accent); background:var(--accent-soft)}
    /* prancha A1 e apaisada: num visor em pe, a altura do palco segue a largura
       (proporcao da folha mais a minimapa), nao a tela inteira */
    .stage{height:min(calc(100svh - 200px), calc(78vw + 130px)); min-height:340px}
    .stage3d{height:calc(100svh - 200px) !important; min-height:360px}
    .ficha{top:auto; bottom:0; left:0; right:0; width:auto; max-height:46%;
           border-radius:6px 6px 0 0}
    .leitura{max-width:72%; font-size:11px}
    #engConteudo table{display:block; overflow-x:auto; max-width:100%; white-space:nowrap}
    .cartoes{grid-template-columns:repeat(2,1fr)}
    .modos-leitura{margin-left:0; flex-wrap:wrap}
    .hint{font-size:10px}
  }
__CSS_EXTRA__
__CSS_2D__
__CSS_ENG__
__CSS_COMODO__
</style>
'''


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


BODY = r'''
<header>
  <div class="wrap head">
    <div class="id">
      <p class="eyebrow">Projeto arquitetônico · revisão __REV__ · coordenação</p>
      <h1>Porto Real</h1>
      <p>Residência unifamiliar · Manaus/AM · SU16 Tarumã <span style="color:var(--ink-faint)">(H)</span>
         · lote 20,00 × 40,00 m · Light Steel Frame sobre radier</p>
    </div>
    <div class="stamp">
      <b>Não liberado para obra</b>
      Sem ART/RRT, sondagem e nesting codificado. Itens marcados (H) são hipóteses
      técnicas, não levantamento.
    </div>
  </div>
  <dl class="wrap figures" style="padding-inline:0">
__FIGS__
  </dl>
</header>

<main class="wrap work">
  <nav class="rail" aria-label="Índice do caderno">
    <div id="rail2d">
      <h2>Caderno · __N__ pranchas</h2>
      <ul class="sheets" id="rail"></ul>
    </div>
    <div id="railEng" hidden>
      <h2>Do modelo à fábrica</h2>
      <ul class="cenas" id="vistasEng"></ul>
      <p class="dica">Sete vistas do mesmo motor: o que a prancha não cabe.
         Três modos de leitura mudam a explicação, nunca o número.</p>
    </div>
    <div id="railComodo" hidden>
      <h2>Cômodo a cômodo</h2>
      <ul class="cenas" id="comodos"></ul>
      <p class="dica">Cada cartão é a prancha recortada em volta do cômodo; os
         quadros vêm do modelo. Toque no título para abrir ou fechar.</p>
    </div>
    <div id="rail3d" hidden>
      <h2>Cenas do modelo</h2>
      <ul class="cenas" id="cenas"></ul>
      <p class="dica">Arraste para orbitar · shift + arraste desloca ·
         roda aproxima · clique num sólido lê o ambiente.</p>
    </div>
  </nav>

  <div>
    <div class="stage-box">
      <div class="toolbar">
        <div class="modos" role="tablist" aria-label="Modo de visualização">
          <button type="button" data-modo="2d" role="tab" aria-selected="true">2D</button>
          <button type="button" data-modo="3d" role="tab" aria-selected="false">3D</button>
          <button type="button" data-modo="eng" role="tab" aria-selected="false">Engenharia</button>
          <button type="button" data-modo="comodo" role="tab" aria-selected="false">Cômodo</button>
        </div>
        <div class="title" id="sheetTitle">—<small id="sheetMeta"></small></div>
        <div class="barra" id="barra2d">
          <button class="btn" id="prev" type="button" aria-label="Prancha anterior">◀</button>
          <button class="btn" id="next" type="button" aria-label="Próxima prancha">▶</button>
          <button class="btn" id="zout" type="button" aria-label="Reduzir">−</button>
          <span class="zoomval" id="zval">100%</span>
          <button class="btn" id="zin" type="button" aria-label="Ampliar">+</button>
          <button class="btn" id="fit" type="button">Ajustar</button>
          <button class="btn" id="semmold" type="button" aria-pressed="false"
                  title="Esconde moldura e carimbo e usa a tela inteira">Sem moldura</button>
          <button class="btn" id="medir" type="button" aria-pressed="false"
                  title="Dois cliques medem a distância real em milímetros">Medir</button>
        </div>
      </div>
__HTML2D__
__PALCO2D__
__HTML3D__
__HTMLENG__
__HTMLCOMODO__
      <p class="hint" id="dicaEng" hidden>Os 801 códigos de peça vêm da posição, não da
        ordem de geração · o painel é desenhado a partir de (x, z) e comprimento, os mesmos
        números que vão para a perfiladeira · nada nesta aba é digitado</p>
      <p class="hint" id="dica2d">Clique em qualquer parede, vão ou ambiente para abrir a ficha ·
        as camadas ligam e desligam cotas, mobiliário e a própria moldura ·
        a busca acha texto dentro do desenho · roda amplia em passos fixos ancorados no cursor ·
        <kbd>+</kbd> <kbd>−</kbd> <kbd>0</kbd> e <kbd>←</kbd> <kbd>→</kbd> pelo teclado</p>
      <p class="hint" id="dica3d" hidden>Oito cenas na coluna ao lado · época e hora movem o sol
        de verdade (latitude −3,10°) · o corte horizontal sobe de 0 a +6,40 m ·
        as camadas ligam e desligam pavimento, laje, cobertura, mobiliário e escada</p>
    </div>

    <section class="notes" id="notas2d">
      <h2>O que esta prancha mostra</h2>
      <div class="note-grid">
        <div><p class="lead" id="noteText"></p></div>
        <ul class="keys" id="noteKeys"></ul>
      </div>
    </section>

    <section class="notes notas3d" id="notas3d" hidden>
      <h2>O que o 3D é — e o que ele não é</h2>
      <div class="note-grid">
        <div>
          <p class="lead">O modelo 3D não foi modelado: foi <b>exportado</b>. Os 329 sólidos
          saem das mesmas paredes deduzidas da malha de 600&nbsp;mm que desenham a planta, com
          os mesmos vãos, as mesmas lajes e o mesmo mobiliário. Se a planta mudar, o 3D muda
          na mesma execução — não existe um segundo modelo para divergir do primeiro.</p>
          <p>Por isso ele serve para <i>verificar</i>: altura livre sob a escada, sombra da
          platibanda sobre a varanda às 15 h, continuidade do eixo da piscina. E por isso
          <b>não</b> serve como imagem de apresentação: não há textura, vegetação real,
          caixilho, rodapé nem arredondamento — cada sólido é uma caixa alinhada aos eixos.</p>
        </div>
        <dl>
          <dt>329 sólidos</dt><dd>142 paredes, 40 vãos, 38 móveis, 21 planos de cobertura,
            19 peças de escada, 18 pisos, 10 pilares, 6 lajes, 6 platibandas</dd>
          <dt>mm, eixo X</dt><dd>largura do lote; 0 na divisa sul</dd>
          <dt>mm, eixo Y</dt><dd>profundidade; 0 na testada leste</dd>
          <dt>+3,15 / +6,15</dt><dd>topo do térreo e topo do superior, os mesmos dos cortes</dd>
          <dt>sol</dt><dd>declinação e ângulo horário reais, sem aproximação de estúdio</dd>
        </dl>
      </div>
    </section>
  </div>
</main>

<footer>
  <div class="wrap foot">
    <div>
      <h2>Histórico de revisões</h2>
      <ol class="revs">
__REVS__
      </ol>
    </div>
    <div>
      <h2>Pendências</h2>
      <ol class="pend">
__PEND__
      </ol>
    </div>
    <div>
      <h2>Como este caderno é feito</h2>
      <p class="colofon">
        As __N__ pranchas e o modelo 3D são vistas de um único modelo geométrico em milímetros.
        As paredes não são desenhadas: são deduzidas do preenchimento da malha de 600&nbsp;mm
        pelos ambientes — cada face entre dois ambientes vira divisória de 100&nbsp;mm, cada
        face entre ambiente e exterior vira parede externa de 150&nbsp;mm. Planta, corte,
        fachada, quadro de cargas, carta solar e volumetria leem a mesma fonte, de modo que uma
        vista não pode divergir da outra. Convenções conforme <code>NBR 10068</code>,
        <code>10582</code>, <code>8403</code>, <code>8402</code> e <code>6492</code>.
      </p>
      <p class="colofon">
        A auditoria roda sobre o modelo, não sobre o traço — e é por isso que encontra coisas que
        nenhum olho vê numa prancha: altura livre de 1.500&nbsp;mm num patamar, caixa d'água de
        25&nbsp;kN apoiada sobre um vazio, chuva calculada sobre 174&nbsp;m² quando caem 289,
        árvore de 12&nbsp;m num canteiro de 1,8&nbsp;m, dois cooktops a 6,7&nbsp;m um do outro.
        Dezenove defeitos desse tipo estão documentados em <code>docs/DIVERGENCIAS.md</code>.
        O corolário vale como método: o que não está no modelo a auditoria não alcança.
        Reproduzível por <code>python3 build.py</code> e <code>python3 viewer.py</code>.
      </p>
    </div>
  </div>
</footer>

__SCRIPT_THREE__
<script>
const SHEETS = __SHEETS__;
const FICHAS = __FICHAS__;
__JS_2D__
__JS_3D__
__JS_ENG__
__JS_COMODO__

// =====================================================================
// navegacao das pranchas
// =====================================================================
const rail = document.getElementById("rail"),
      titleEl = document.getElementById("sheetTitle"),
      metaEl = document.getElementById("sheetMeta"),
      noteText = document.getElementById("noteText"),
      noteKeys = document.getElementById("noteKeys");
let idxPrancha = 0;

let etapa = null;
SHEETS.forEach((s, i) => {
  const li = document.createElement("li");
  if (s.etapa !== etapa) {
    etapa = s.etapa;
    const h = document.createElement("div");
    h.className = "group"; h.textContent = s.etapa;
    li.appendChild(h);
  }
  const b = document.createElement("button");
  b.type = "button";
  b.innerHTML = `<span class="num">${s.n}</span><span>${s.t}<span class="esc">${s.esc}</span></span>`;
  b.addEventListener("click", () => mostrar(i));
  li.appendChild(b); rail.appendChild(li);
});
const botoes = [...rail.querySelectorAll("button")];

function mostrar(i) {
  idxPrancha = (i + SHEETS.length) % SHEETS.length;
  const s = SHEETS[idxPrancha];
  botoes.forEach((b, j) => b.setAttribute("aria-current", j === idxPrancha ? "true" : "false"));
  titleEl.childNodes[0].nodeValue = s.t;
  metaEl.textContent = `Prancha ${s.n}/__N__ · ${s.etapa} · escala ${s.esc} · A1 841 × 594 mm`;
  const m = /1:\s*(\d+)/.exec(s.esc);
  denom = m ? parseInt(m[1], 10) : 0;
  ficha.hidden = true;
  limparRegua();
  buscaInp.value = ""; buscar("");
  carregarFolha(`PR-${s.n}.svg`);
  noteText.textContent = s.d;
  noteKeys.innerHTML = s.k.map(([k, v]) =>
    `<li><span class="k">${k}</span><span class="v">${v}</span></li>`).join("");
  botoes[idxPrancha].scrollIntoView({block: "nearest"});
  if (typeof gravarRota === "function") gravarRota();
}
document.getElementById("prev").onclick = () => mostrar(idxPrancha - 1);
document.getElementById("next").onclick = () => mostrar(idxPrancha + 1);

mostrar(1);
</script>

<script>
// R76 — navegacao de celular: um <select> que espelha o indice visivel (pranchas,
// vistas de engenharia ou cenas 3D) e dois botoes de passo. Le os botoes do
// proprio indice; nao ha segunda lista para divergir.
(function () {
  const bar = document.querySelector(".toolbar");
  if (!bar) return;
  const box = document.createElement("div");
  box.className = "selnav";
  box.innerHTML = `<button class="btn" id="navPrev" type="button" aria-label="Anterior">◀</button>
    <select id="selNav" aria-label="Ir para"></select>
    <button class="btn" id="navNext" type="button" aria-label="Próximo">▶</button>
    <button class="btn" id="navPaineis" type="button" aria-pressed="false"
            title="Camadas, busca, sol e medição">☰</button>`;
  bar.appendChild(box);
  const sel = box.querySelector("#selNav");
  const caixa = document.querySelector(".stage-box");
  box.querySelector("#navPaineis").onclick = ev => {
    const on = !caixa.classList.contains("paineis");
    caixa.classList.toggle("paineis", on);
    ev.currentTarget.setAttribute("aria-pressed", on ? "true" : "false");
  };
  function fonte() {
    for (const id of ["rail2d", "railEng", "railComodo", "rail3d"]) {
      const d = document.getElementById(id);
      if (d && !d.hidden) return d;
    }
    return document.getElementById("rail2d");
  }
  let enchendo = false;
  function encher() {
    if (enchendo) return;
    enchendo = true;
    const bs = [...fonte().querySelectorAll("button")];
    const rotulo = b => {
      // "02 · Planta baixa — terreo · 1:50": separador antes da escala/subtitulo
      // e depois do numero, onde quer que eles estejam aninhados
      const c = b.cloneNode(true);
      c.querySelectorAll(".esc, .sub").forEach(e => e.insertAdjacentText("beforebegin", " · "));
      c.querySelectorAll(".num").forEach(e => e.insertAdjacentText("afterend", " · "));
      return c.textContent.replace(/\s+/g, " ").replace(/( · )+/g, " · ").trim().slice(0, 64);
    };
    sel.innerHTML = bs.map((b, i) =>
      `<option value="${i}" ${b.getAttribute("aria-current") === "true" ? "selected" : ""}>${rotulo(b)}</option>`).join("");
    enchendo = false;
  }
  sel.addEventListener("change", () => {
    const b = [...fonte().querySelectorAll("button")][+sel.value];
    if (b) { b.click(); setTimeout(encher, 80); }
  });
  function passoNav(k) {
    const i = +sel.value + k;
    if (i >= 0 && i < sel.options.length) { sel.value = i; sel.dispatchEvent(new Event("change")); }
  }
  box.querySelector("#navPrev").onclick = () => passoNav(-1);
  box.querySelector("#navNext").onclick = () => passoNav(1);
  const mo = new MutationObserver(() => encher());
  ["rail2d", "railEng", "railComodo", "rail3d"].forEach(id => {
    const d = document.getElementById(id);
    if (d) mo.observe(d, {attributes: true, subtree: true, childList: true,
                          attributeFilter: ["aria-current", "hidden"]});
  });
  document.querySelectorAll("button[data-modo]").forEach(b => b.addEventListener("click", () => setTimeout(encher, 60)));
  encher();
  // no celular a prancha abre "sem moldura": a moldura e o carimbo cabem numa
  // tela de 1.440 px, num visor de 390 so tiram espaco do desenho
  if (matchMedia("(max-width:860px)").matches) {
    const sm = document.getElementById("semmold");
    if (sm && sm.getAttribute("aria-pressed") !== "true") setTimeout(() => sm.click(), 400);
  }
})();
</script>
'''


def partes() -> tuple[str, str]:
    """(cabeca, corpo) — o que vai no <head> e o que vai no <body>."""
    D = dados()
    figs = "\n".join(
        f'    <div class="fig"><dt>{esc(t)}</dt><dd>{esc(v)} <span>{esc(u)}</span></dd></div>'
        for t, v, u in D["figures"])
    revs = "\n".join(
        f'      <li><span class="r">{esc(r)}</span><span>{esc(c)}</span></li>'
        for r, c in D["revisoes"])
    pend = "\n".join(
        f'      <li><span class="n">{esc(n)}</span><span>{esc(txt)}</span>'
        f'<span class="s {st.lower()}">{esc(st)}</span></li>'
        for n, txt, st in D["pend"])
    cabeca = HEAD.replace("__CSS_EXTRA__", v2.CSS_EXTRA).replace("__CSS_2D__", v4.CSS_2D).replace("__CSS_ENG__", v5.CSS_ENG).replace("__CSS_COMODO__", v6.CSS_COMODO)
    corpo = (BODY.replace("__N__", str(len(D["sheets"])))
                 .replace("__REV__", D["revisao"])
                 .replace("__FIGS__", figs)
                 .replace("__REVS__", revs)
                 .replace("__PEND__", pend)
                 .replace("__HTML2D__", v4.HTML_2D)
                 .replace("__PALCO2D__", v4.HTML_PALCO_2D)
                 .replace("__HTML3D__", v2.HTML_3D)
                 .replace("__HTMLENG__", v5.HTML_ENG)
                 .replace("__HTMLCOMODO__", v6.HTML_COMODO)
                 .replace("__SCRIPT_THREE__", _script_three())
                 .replace("__JS_2D__", v4.JS_2D)
                 .replace("__JS_ENG__", v5.JS_ENG)
                 .replace("__JS_COMODO__", v6.JS_COMODO)
                 .replace("__JS_3D__", v3.JS_3D)
                 .replace("__FICHAS__", json.dumps(D["fichas"], ensure_ascii=False))
                 .replace("__SHEETS__", json.dumps(D["sheets"], ensure_ascii=False)))
    return cabeca, corpo


RECURSOS_JS = r'''<script>
// R72 — a pagina carrega folhas e modelos por fetch(); aberta do disco
// (file://) ou mandada sozinha pelo celular, o fetch nao acha nada e nenhum
// botao faz nada. Quando os recursos vem EMBUTIDOS, lerRecurso() os entrega
// sem rede; senao, cai no fetch de sempre. Uma unica leitura para os dois.
window.EMBUTIDO = window.EMBUTIDO || {};
window.lerRecurso = async function (nome) {
  if (nome in EMBUTIDO) return EMBUTIDO[nome];
  const r = await fetch(nome);
  if (!r.ok) throw new Error(r.status);
  return await r.text();
};
window.urlRecurso = function (nome) {
  if (!(nome in EMBUTIDO)) return nome;
  const tipo = nome.endsWith(".svg") ? "image/svg+xml" : "application/json";
  return URL.createObjectURL(new Blob([EMBUTIDO[nome]], {type: tipo}));
};
</script>
'''


def _embutidos() -> str:
    """Os SVGs das pranchas e os dois modelos, como texto, num <script>."""
    out = os.path.dirname(OUT)
    rec = {}
    for n, _t, _f in __import__("build").CADERNO:
        cam = os.path.join(out, f"PR-{n}.svg")
        if os.path.exists(cam):
            rec[f"PR-{n}.svg"] = open(cam, encoding="utf-8").read()
    for nome in ("modelo3d.json", "engenharia.json"):
        cam = os.path.join(out, nome)
        if os.path.exists(cam):
            rec[nome] = open(cam, encoding="utf-8").read()
    js = json.dumps(rec, ensure_ascii=False).replace("</", "<\\/")
    return f"<script>window.EMBUTIDO = {js};</script>\n"


def html(embutir: bool = False) -> str:
    """Fragmento para publicar como artefato: o host injeta <head> e <body>.
    O <title> fica no comeco (o host so le os primeiros 8 KB) e os recursos
    embutidos vem depois da folha de estilo."""
    cabeca, corpo = partes()
    return cabeca + RECURSOS_JS + (_embutidos() if embutir else "") + corpo


def documento(embutir: bool = False) -> str:
    """Pagina completa, para abrir do disco. O fragmento do artefato nao traz
    charset nem viewport porque o host os injeta; aberto em file:// sem eles o
    navegador assume windows-1252 e o acento vira lixo.

    embutir=True poe as 59 folhas e os dois modelos dentro do proprio arquivo:
    e o que se manda por mensagem e abre em qualquer lugar sem servidor."""
    cabeca, corpo = partes()
    return ('<!doctype html>\n<html lang="pt-BR">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            + (_embutidos() if embutir else "") + RECURSOS_JS
            + cabeca + '</head>\n<body>\n' + corpo + '\n</body>\n</html>\n')


def main(destino: str | None = None) -> str:
    alvo = os.path.abspath(destino or OUT)
    os.makedirs(os.path.dirname(alvo), exist_ok=True)
    texto = documento()
    open(alvo, "w", encoding="utf-8").write(texto)
    print(f"  {alvo}  {len(texto) // 1024} KB  (pagina completa)")

    frag = os.path.join(os.path.dirname(alvo), "caderno-artefato.html")
    t2 = html(embutir=True)
    open(frag, "w", encoding="utf-8").write(t2)
    print(f"  {frag}  {len(t2) // 1024} KB  (fragmento para artefato)")
    unico = os.path.join(os.path.dirname(alvo), "porto-real-caderno-unico.html")
    t3 = documento(embutir=True)
    open(unico, "w", encoding="utf-8").write(t3)
    print(f"  {unico}  {len(t3) // 1024} KB  (arquivo unico, com as folhas dentro)")
    return alvo


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
