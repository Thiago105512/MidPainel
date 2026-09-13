#!/usr/bin/env python3
"""ENGENHARIA no visualizador — a terceira aba.

A aba 2D mostra as pranchas; a 3D mostra o volume; esta mostra o que nenhuma
das duas cabe: 801 pecas, 62 paineis, um plano de corte de 328 barras, 100
passos de montagem e seis notas com a formula aberta.

Nada e desenhado a mao aqui. O painel de parede e montado no navegador a
partir da posicao (x, z) e do comprimento de cada peca, que sao os mesmos
numeros que a maquina de perfilagem vai receber. Se o desenho sair errado, a
peca sai errada — e esse e exatamente o ponto de desenhar assim.

Sete vistas: painel de controle, paineis, pecas, corte, montagem, logistica e
documentos. Tres modos de leitura (executivo, educacional, especialista) que
mudam a explicacao e nunca o numero.
"""
from __future__ import annotations

CSS_ENG = r'''
  /* ----------------------------------------------------- aba engenharia */
  #stageEng{background:var(--stage); max-height:min(78vh,760px); overflow-y:auto;
            padding:16px}
  .eng-sec{margin:0 0 26px}
  .eng-sec > h3{font-family:var(--mono); font-size:10.5px; letter-spacing:.13em;
    text-transform:uppercase; color:var(--ink-faint); margin:0 0 10px; font-weight:500}
  .cartoes{display:grid; grid-template-columns:repeat(auto-fit,minmax(148px,1fr));
           gap:1px; background:var(--rule-soft); border:1px solid var(--rule-soft)}
  .cartao{background:var(--surface); padding:11px 13px}
  .cartao .rot{font-family:var(--mono); font-size:10px; letter-spacing:.1em;
    text-transform:uppercase; color:var(--ink-faint); display:block; margin-bottom:3px}
  .cartao .val{font-family:var(--mono); font-size:20px; font-weight:500;
    font-variant-numeric:tabular-nums; letter-spacing:-.01em}
  .cartao .uni{font-family:var(--mono); font-size:11px; color:var(--ink-soft)}

  .notas{display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:10px}
  .nota{background:var(--surface); border:1px solid var(--rule-soft); padding:12px 13px}
  .nota h4{margin:0 0 8px; font-family:var(--mono); font-size:11px; letter-spacing:.08em;
           text-transform:uppercase; color:var(--ink-soft); font-weight:500}
  .nota .n{font-family:var(--mono); font-size:26px; font-weight:600;
           font-variant-numeric:tabular-nums; line-height:1}
  .nota .n small{font-size:12px; color:var(--ink-faint); font-weight:400}
  .barra-nota{height:5px; background:var(--rule-soft); margin:8px 0 7px; overflow:hidden}
  .barra-nota i{display:block; height:100%; background:var(--accent)}
  .nota.ruim .barra-nota i{background:var(--alert)}
  .nota .form{font-family:var(--mono); font-size:10.5px; color:var(--ink-faint);
              line-height:1.45; margin:0}

  .selo{border:1px solid var(--ok); color:var(--ok); background:var(--ok-soft);
        font-family:var(--mono); font-size:12px; letter-spacing:.06em;
        padding:9px 13px; display:flex; gap:12px; align-items:center; flex-wrap:wrap}
  .selo.nao{border-color:var(--alert); color:var(--alert); background:var(--alert-soft)}
  .selo b{letter-spacing:.12em; text-transform:uppercase}

  .check{list-style:none; margin:10px 0 0; padding:0;
         display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:0 22px}
  .check li{display:grid; grid-template-columns:16px 1fr auto; gap:9px; align-items:baseline;
            padding:6px 0; border-top:1px solid var(--rule-soft); font-size:13px}
  .check .m{font-family:var(--mono); font-size:12px; color:var(--ok)}
  .check li.mau .m{color:var(--alert)}
  .check .st{font-family:var(--mono); font-size:9.5px; letter-spacing:.09em;
             color:var(--ink-faint)}

  .filtros{display:flex; flex-wrap:wrap; gap:7px; align-items:center; margin-bottom:11px}
  .filtros input, .filtros select{font-family:var(--mono); font-size:11.5px;
    border:1px solid var(--rule); background:var(--surface); color:var(--ink);
    padding:5px 8px; border-radius:2px}
  .filtros input[type="search"]{min-width:190px}
  .conta{font-family:var(--mono); font-size:11px; color:var(--ink-faint)}

  .eng-grid{display:grid; grid-template-columns:220px 1fr; gap:14px; align-items:start}
  @media (max-width:820px){ .eng-grid{grid-template-columns:1fr} }
  .lista{list-style:none; margin:0; padding:0; max-height:520px; overflow-y:auto;
         border:1px solid var(--rule-soft); background:var(--surface)}
  .lista li + li{border-top:1px solid var(--rule-soft)}
  .lista button{width:100%; text-align:left; background:none; border:none; color:inherit;
    font-family:inherit; font-size:12.5px; padding:7px 10px; cursor:pointer; line-height:1.3}
  .lista button:hover{background:var(--rule-soft)}
  .lista button[aria-current="true"]{background:var(--accent-soft);
    box-shadow:inset 2px 0 0 var(--accent)}
  .lista .sub{display:block; font-family:var(--mono); font-size:10px; color:var(--ink-faint)}

  .desenho{border:1px solid var(--rule-soft); background:var(--surface); padding:12px}
  .desenho svg{display:block; width:100%; height:auto; max-width:100%}
  .desenho .cap{font-family:var(--mono); font-size:11px; color:var(--ink-soft);
                margin:9px 0 0; line-height:1.5}
  .legenda{display:flex; flex-wrap:wrap; gap:5px 13px; margin:10px 0 0;
           font-family:var(--mono); font-size:10.5px; color:var(--ink-soft)}
  .legenda span{display:inline-flex; align-items:center; gap:5px}
  .legenda i{width:11px; height:11px; display:inline-block; border:1px solid rgba(0,0,0,.25)}

  .tabela{width:100%; border-collapse:collapse; font-family:var(--mono); font-size:11.5px;
          font-variant-numeric:tabular-nums}
  .tabela th{text-align:left; font-weight:500; font-size:10px; letter-spacing:.09em;
    text-transform:uppercase; color:var(--ink-faint); padding:6px 8px;
    border-bottom:1px solid var(--rule); position:sticky; top:0; background:var(--surface);
    cursor:pointer; white-space:nowrap}
  .tabela th:hover{color:var(--accent)}
  .tabela td{padding:5px 8px; border-bottom:1px solid var(--rule-soft)}
  .tabela tbody tr:hover{background:var(--rule-soft)}
  .rolagem{max-height:480px; overflow:auto; border:1px solid var(--rule-soft);
           background:var(--surface)}
  .chip{display:inline-block; width:9px; height:9px; margin-right:6px;
        border:1px solid rgba(0,0,0,.25)}

  .docs{display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px}
  .doc-txt{background:var(--surface); border:1px solid var(--rule-soft); padding:12px;
           font-family:var(--mono); font-size:11.5px; line-height:1.6; white-space:pre-wrap;
           max-height:520px; overflow:auto; margin:0}
  .modos-leitura{display:flex; gap:4px; margin-left:auto}
  .modos-leitura button{font-family:var(--mono); font-size:10.5px; letter-spacing:.05em;
    border:1px solid var(--rule); background:var(--surface); color:var(--ink-soft);
    padding:4px 9px; cursor:pointer; border-radius:2px}
  .modos-leitura button[aria-pressed="true"]{border-color:var(--accent);
    color:var(--accent); background:var(--accent-soft)}
'''

HTML_ENG = r'''
      <div id="stageEng" hidden>
        <div id="engConteudo"></div>
      </div>
'''


JS_ENG = r'''
// =====================================================================
// ENGENHARIA — o motor inteiro em sete vistas
// =====================================================================
let ENG = null, engVista = "painel", engModo = "educacional";
let painelSel = null, docSel = "memorial", animar = null;

const VISTAS = [
  ["painel",     "Painel de controle", "16 itens e 6 notas"],
  ["paineis",    "Painéis",            "elevação montada da peça"],
  ["pecas",      "Peças",              "801 linhas filtráveis"],
  ["corte",      "Plano de corte",     "barra a barra"],
  ["montagem",   "Montagem",           "sequência animada"],
  ["logistica",  "Logística",          "container e içamento"],
  ["documentos", "Documentos",         "gerados do modelo"],
  ["bloqueios",  "O que não faço",     "10 contratos, 20 seções"],
];

const LEITURA = {
  executivo: {
    painel: "O projeto está liberado ou não, e quanto custa. As seis notas " +
            "resumem seis riscos distintos; a menor delas é a que decide. " +
            "A verificação estrutural diz quantos montantes reprovam — e o " +
            "número que importa ali é zero.",
    paineis: "Cada painel é uma unidade de compra, de transporte e de " +
             "montagem. O que não couber no caminhão vira custo.",
    pecas: "Cada linha é uma peça que alguém vai cortar, furar e parafusar.",
    corte: "O aproveitamento é dinheiro: o que sobra da barra foi comprado.",
    montagem: "O prazo da obra é esta lista multiplicada pelo tamanho da equipe.",
    logistica: "Um container mal ocupado é frete pago por ar.",
    documentos: "O que vai para a fábrica e para o canteiro.",
    bloqueios: "O que este sistema não entrega, e o que seria preciso para " +
               "entregar. Nenhum destes itens está pela metade: estão fora, " +
               "com o preço declarado.",
  },
  educacional: {
    painel: "Os 415 montantes são verificados um a um contra a carga que de " +
            "fato desce até cada um: área de influência, o que há acima, " +
            "combinação da NBR 8681. A utilização não tem teto — até R28 ela " +
            "era relatada com min(0,99), e um montante 47 % sobrecarregado " +
            "saía como aprovado. O checklist não é opinião: cada item é uma " +
            "consulta ao resultado " +
            "de uma função do motor. Nenhum é marcável à mão — se fosse, " +
            "seria marcado. As notas trazem a fórmula que as produziu, para " +
            "que se possa discordar do critério, e não do número.",
    paineis: "O painel é desenhado aqui a partir de (x, z) e comprimento de " +
             "cada peça — os mesmos números que vão para a perfiladeira. " +
             "Montante a cada 600 mm; onde há vão, entram king, jack, verga e " +
             "cripples, e a modulação é interrompida só o necessário.",
    pecas: "A família diz a função estrutural, não a forma: dois perfis " +
           "idênticos são peças diferentes se um é montante e o outro é jack. " +
           "O código vem da posição, não da ordem de geração — por isso " +
           "sobrevive a uma revisão.",
    corte: "Cada barra de 6 m recebe peças até não caber mais a próxima. O " +
           "resto é perda, e a perda entra no BOM porque foi comprada.",
    montagem: "A ordem sai de uma ordenação topológica das dependências, e " +
              "cada passo é conferido: em nenhum instante a estrutura fica " +
              "instável. Desmontar é a mesma lista ao contrário.",
    logistica: "O centro de gravidade sai de soma de momentos das peças, e é " +
               "ele que decide onde ficam os pontos de içamento.",
    documentos: "Os seis documentos saem do mesmo dado das telas anteriores. " +
                "Trocar o modo de leitura muda a explicação; o valor de " +
                "cálculo é idêntico nos três.",
    bloqueios: "Há três respostas possíveis para o que depende do mundo " +
               "externo: simular, não entregar, ou entregar o contrato. " +
               "Simular é a pior — uma funcionalidade falsa é pior que a " +
               "ausência, porque a ausência se vê. Cada contrato traz o " +
               "esquema de dados, o adaptador que recusa inventar número e o " +
               "critério que o valida no dia em que o dado existir.",
  },
  especialista: {
    painel: "Notas normalizadas em [0,100] por funções monotônicas declaradas; " +
            "score geral é média aritmética simples — deliberadamente sem " +
            "pesos, porque peso embutido esconde juízo. Para ponderar, use " +
            "nucleo/otimizacao.ranquear().",
    paineis: "Painelização por trechos admissíveis: o corte só ocorre onde " +
             "não há abertura e onde a modulação permite; quando nenhuma " +
             "posição satisfaz comp ≤ 3600, o painel é emitido inteiro com a " +
             "razão declarada, em vez de cortado sobre o vão.",
    pecas: "Furo de serviço limitado a d ≤ 0,5·bw na alma, afastado das " +
           "extremidades; a verificação de furação é independente da geração.",
    corte: "First-fit decreasing sobre barras de 6 m, consultando sobras " +
           "antes de abrir barra nova. Identidade conferida: bruto = usado + perda.",
    montagem: "Kahn com detecção de ciclo; estabilidade avaliada no prefixo " +
              "de cada passo, não só no estado final.",
    logistica: "Empacotamento por pilhas com limite de massa e altura; o " +
               "limitante (peso ou volume) é declarado, não inferido.",
    documentos: "memorial_compressao() chama a mesma verificacao.compressao() " +
                "nos três modos; a divergência entre modos seria um defeito.",
    bloqueios: "Adaptador vazio levanta SemFonteDeDados com código, motivo e " +
               "remédio; receber() já valida tipo, unidade, domínio e campo " +
               "desconhecido hoje, antes de o dado existir. A auditoria chama " +
               "consultar() nos dez e reprova qualquer retorno, None inclusive.",
  },
};

function num(v, casas) {
  return Number(v).toLocaleString("pt-BR",
    {minimumFractionDigits: casas || 0, maximumFractionDigits: casas || 0});
}
function corFam(f) { return (ENG.cores && ENG.cores[f]) || "#8a94a6"; }
function esc2(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function leitura(v) {
  const t = LEITURA[engModo][v];
  return t ? `<p class="desenho cap" style="border:none;padding:0;margin:0 0 12px">${esc2(t)}</p>` : "";
}
function barraModos() {
  return '<div class="modos-leitura" role="group" aria-label="Modo de leitura">' +
    ["executivo", "educacional", "especialista"].map(m =>
      `<button type="button" data-leitura="${m}" aria-pressed="${m === engModo}">${m}</button>`
    ).join("") + "</div>";
}
'''
JS_ENG += r'''
// --------------------------------------------------------- painel de controle
function vistaPainel() {
  const L = ENG.liberacao, S = ENG.scores;
  const cartoes = ENG.resumo.map(r =>
    `<div class="cartao"><span class="rot">${esc2(r.rotulo)}</span>
       <span class="val">${num(r.valor, Number.isInteger(r.valor) ? 0 : 1)}</span>
       <span class="uni">${esc2(r.unidade)}</span></div>`).join("");
  const notas = Object.keys(S).map(k => {
    const s = S[k], ruim = s.nota < 70;
    return `<div class="nota${ruim ? " ruim" : ""}">
      <h4>${esc2(k)}</h4>
      <div class="n">${s.nota}<small> / 100</small></div>
      <div class="barra-nota"><i style="width:${s.nota}%"></i></div>
      <p class="form">${esc2(s.formula || s.motivo || "")}</p></div>`;
  }).join("");
  const itens = L.itens.map(i =>
    `<li class="${i.status === "OK" ? "" : "mau"}">
       <span class="m">${i.status === "OK" ? "✓" : "✕"}</span>
       <span>${esc2(i.descricao)}</span>
       <span class="st">${esc2(i.item)}</span></li>`).join("");
  return `${barraModos()}${leitura("painel")}
    <div class="eng-sec"><h3>Números do modelo</h3><div class="cartoes">${cartoes}</div></div>
    ${blocoEstrutura()}
    <div class="eng-sec"><h3>Liberação</h3>
      <div class="selo${L.liberado ? "" : " nao"}" id="seloLiberacao">
        <b>${esc2(L.situacao)}</b>
        <span>score geral ${ENG.score_geral}/100 · revisão ${esc2(ENG.revisao)}</span></div>
      <ul class="check">${itens}</ul></div>
    <div class="eng-sec"><h3>Seis notas, seis fórmulas</h3>
      <div class="notas">${notas}</div></div>`;
}

function blocoEstrutura() {
  const E = ENG.estrutura;
  if (!E) return "";
  const maior = Math.max(...E.histograma.map(h => h.n)) || 1;
  const barras = E.histograma.map(h => {
    const rot = h.ate > 1 ? "acima de 1,00" :
      `${h.de.toFixed(2).replace(".", ",")} – ${h.ate.toFixed(2).replace(".", ",")}`;
    const cor = h.ate > 1 ? "var(--alert)" : (h.de >= 0.9 ? "#d98324" : "#3f6fb5");
    return `<div style="display:grid;grid-template-columns:104px 1fr 44px;gap:8px;
      align-items:center;font-family:var(--mono);font-size:11px;padding:2px 0">
      <span>${rot}</span>
      <span style="height:10px;background:var(--rule-soft)"><i style="display:block;
        height:100%;width:${(h.n / maior * 100).toFixed(1)}%;background:${cor}"></i></span>
      <span style="text-align:right">${h.n}</span></div>`;
  }).join("");
  const g = E.governa;
  const jb = E.jambas.map(j =>
    `<li><b>${esc2(j.painel)}</b> — ${esc2(j.solucao)} ·
      N<sub>sd</sub> ${num(j.nsd, 1)} kN · u ${j.u.toFixed(2).replace(".", ",")}
      ${j.sku_nova ? "· SKU nova" : ""}
      <span class="sub">${esc2(j.motivo)}</span></li>`).join("");
  const hip = E.hipoteses.map(h => `<li>${esc2(h)}</li>`).join("");
  return `<div class="eng-sec"><h3>Verificação estrutural — ${E.n} montantes, um a um</h3>
    <div class="selo${E.aprovado ? "" : " nao"}" style="margin-bottom:12px">
      <b>${E.reprovadas} reprovam de ${E.n}</b>
      <span>mediana ${E.mediana.toFixed(2).replace(".", ",")} ·
        máxima ${E.maxima.toFixed(2).replace(".", ",")} ·
        alvo de projeto ${E.u_alvo.toFixed(2).replace(".", ",")} ·
        aprovação pela norma 1,00</span></div>
    <div class="eng-grid" style="grid-template-columns:1fr 1fr">
      <div><h3 style="margin-bottom:8px">Distribuição de utilização</h3>${barras}
        <p class="conta" style="display:block;margin-top:10px;line-height:1.5">
          Governa <b>${esc2(g.peca)}</b> (${esc2(g.familia)}, ${esc2(g.perfil)}):
          N<sub>sd</sub> ${num(g.nsd, 1)} kN de ${num(g.nrd, 1)} kN resistentes,
          modo <b>${esc2(g.modo)}</b>, k = ${g.k.toFixed(2).replace(".", ",")},
          combinação ${esc2(g.combinacao)}.</p></div>
      <div><h3 style="margin-bottom:8px">Jambas dimensionadas pela carga</h3>
        <ul class="lista" style="max-height:none">${jb || "<li><button type='button' disabled>nenhuma precisou de reforço</button></li>"}</ul>
        <h3 style="margin:14px 0 8px">Hipóteses de caminho de carga</h3>
        <ul style="margin:0;padding-left:18px;font-size:12.5px;color:var(--ink-soft);
          line-height:1.55">${hip}</ul></div>
    </div></div>`;
}

// --------------------------------------------------------------- painéis
function svgPainel(p) {
  const M = 60;
  const W = p.comp, H = p.altura;
  const pecas = p.pecas.map(q => {
    const bw = q.vertical ? 90 : 92;
    const x = q.x, y = H - q.z - (q.vertical ? q.comp : bw);
    const w = q.vertical ? bw : q.comp, h = q.vertical ? q.comp : bw;
    return `<rect x="${x}" y="${Math.max(0, y)}" width="${w}" height="${h}"
      fill="${corFam(q.familia)}" stroke="#0d1114" stroke-width="4"
      opacity=".92"><title>${esc2(q.cod)} · ${esc2(q.familia)} · ${esc2(q.perfil)} · ${q.comp} mm</title></rect>`;
  }).join("");
  const furos = p.pecas.flatMap(q => (q.furos || []).map(f => {
    const cx = q.vertical ? q.x + 45 : q.x + f.x;
    const cy = q.vertical ? H - q.z - f.x : H - q.z - 46;
    return `<circle cx="${cx}" cy="${cy}" r="${Math.max(14, f.d / 2)}"
      fill="none" stroke="#c4491f" stroke-width="5"/>`;
  })).join("");
  const abs = p.aberturas.map(a => {
    const x = a.centro - a.larg / 2;
    return `<g><rect x="${x}" y="${H - a.peitoril - a.alt}" width="${a.larg}"
      height="${a.alt}" fill="none" stroke="#c4491f" stroke-width="9"
      stroke-dasharray="40 24"/>
      <text x="${a.centro}" y="${H - a.peitoril - a.alt / 2}" fill="#c4491f"
        font-size="96" text-anchor="middle" font-family="monospace"
        dominant-baseline="middle">${esc2(a.tipo)}</text></g>`;
  }).join("");
  const cotas = `<g stroke="currentColor" stroke-width="4" opacity=".55"
      font-family="monospace" font-size="86" fill="currentColor">
      <line x1="0" y1="${H + 150}" x2="${W}" y2="${H + 150}"/>
      <text x="${W / 2}" y="${H + 250}" text-anchor="middle">${W} mm</text>
      <line x1="${-150}" y1="0" x2="${-150}" y2="${H}"/>
      <text x="${-190}" y="${H / 2}" text-anchor="end">${H} mm</text></g>`;
  return `<svg viewBox="${-M - 300} ${-M} ${W + 2 * M + 400} ${H + 2 * M + 300}"
    role="img" aria-label="Elevação do painel ${esc2(p.cod)}">
    <rect x="0" y="0" width="${W}" height="${H}" fill="none"
      stroke="currentColor" stroke-width="6" opacity=".35"/>
    ${pecas}${furos}${abs}${cotas}</svg>`;
}

function vistaPaineis() {
  const lista = ENG.paineis.map(p =>
    `<li><button type="button" data-painel="${esc2(p.cod)}"
       aria-current="${p.cod === painelSel}">${esc2(p.cod)}
       <span class="sub">${p.comp} mm · ${p.n_pecas} peças · ${num(p.massa, 1)} kg${
         p.aberturas.length ? " · vão" : ""}</span></button></li>`).join("");
  const p = ENG.paineis.find(q => q.cod === painelSel) || ENG.paineis[0];
  const fams = Object.keys(p.familias).map(f =>
    `<span><i style="background:${corFam(f)}"></i>${esc2(f)} ${p.familias[f]}</span>`).join("");
  const linhas = p.pecas.map(q =>
    `<tr><td><span class="chip" style="background:${corFam(q.familia)}"></span>${esc2(q.cod)}</td>
      <td>${esc2(q.familia)}</td><td>${esc2(q.perfil)}</td><td>${q.comp}</td>
      <td>${q.x}</td><td>${q.z}</td><td>${q.massa === undefined ? "—" : num(q.massa, 2)}</td>
      <td>${(q.furos || []).length}</td></tr>`).join("");
  return `${barraModos()}${leitura("paineis")}
    <div class="eng-grid">
      <ul class="lista">${lista}</ul>
      <div>
        <div class="desenho">${svgPainel(p)}
          <p class="cap"><b>${esc2(p.cod)}</b> · parede ${esc2(p.parede)} ·
            ${p.externa ? "externa" : "interna"} · ${p.comp} × ${p.altura} mm ·
            espessura ${p.esp} mm · ${num(p.massa, 1)} kg ·
            ${p.horizontal ? "horizontal" : "vertical"} em planta
            ${p.obs ? "<br>" + esc2(p.obs) : ""}</p>
          <div class="legenda">${fams}</div></div>
        <div class="rolagem" style="margin-top:12px">
          <table class="tabela"><thead><tr><th>peça</th><th>família</th>
            <th>perfil</th><th>comp</th><th>x</th><th>z</th><th>kg</th><th>furos</th>
            </tr></thead><tbody>${linhas}</tbody></table></div>
      </div></div>`;
}
'''
JS_ENG += r'''
// ------------------------------------------------------------------ peças
let pecaOrd = {campo: "cod", asc: true}, pecaBusca = "", pecaFam = "", pecaPav = "";
function todasPecas() {
  return ENG.paineis.flatMap(p => p.pecas.map(q =>
    Object.assign({painel: p.cod, pav: p.pav}, q)));
}
function vistaPecas() {
  const todas = todasPecas();
  const fams = [...new Set(todas.map(q => q.familia))].sort();
  let alvo = todas.filter(q =>
    (!pecaFam || q.familia === pecaFam) &&
    (!pecaPav || q.pav === pecaPav) &&
    (!pecaBusca || (q.cod + " " + q.perfil + " " + q.familia + " " + q.painel)
        .toLowerCase().includes(pecaBusca.toLowerCase())));
  alvo.sort((a, b) => {
    const x = a[pecaOrd.campo], y = b[pecaOrd.campo];
    const c = (typeof x === "number" && typeof y === "number")
      ? x - y : String(x).localeCompare(String(y));
    return pecaOrd.asc ? c : -c;
  });
  const massa = alvo.reduce((s, q) => s + (q.massa || 0), 0);
  const cols = [["cod", "peça"], ["painel", "painel"], ["familia", "família"],
                ["perfil", "perfil"], ["comp", "comp mm"], ["massa", "kg"],
                ["marcacao", "marcação"]];
  const cab = cols.map(([c, t]) =>
    `<th data-ord="${c}">${t}${pecaOrd.campo === c ? (pecaOrd.asc ? " ▲" : " ▼") : ""}</th>`).join("");
  const corpo = alvo.slice(0, 900).map(q =>
    `<tr><td><span class="chip" style="background:${corFam(q.familia)}"></span>${esc2(q.cod)}</td>
      <td>${esc2(q.painel)}</td><td>${esc2(q.familia)}</td><td>${esc2(q.perfil)}</td>
      <td>${q.comp}</td><td>${q.massa === undefined ? "—" : num(q.massa, 2)}</td>
      <td>${esc2(q.marcacao || "")}</td></tr>`).join("");
  const porFam = Object.keys(ENG.familias).sort((a, b) => ENG.familias[b] - ENG.familias[a]);
  const maior = Math.max(...porFam.map(f => ENG.familias[f]));
  const hist = porFam.map(f =>
    `<div style="display:grid;grid-template-columns:118px 1fr 46px;gap:8px;align-items:center;
       font-family:var(--mono);font-size:11px;padding:2px 0">
      <span>${esc2(f)}</span>
      <span style="height:9px;background:var(--rule-soft)"><i style="display:block;height:100%;
        width:${(ENG.familias[f] / maior * 100).toFixed(1)}%;background:${corFam(f)}"></i></span>
      <span style="text-align:right">${ENG.familias[f]}</span></div>`).join("");
  return `${barraModos()}${leitura("pecas")}
    <div class="filtros">
      <input type="search" id="buscaPeca" placeholder="peça, perfil, painel" value="${esc2(pecaBusca)}">
      <select id="filFam"><option value="">todas as famílias</option>${
        fams.map(f => `<option${f === pecaFam ? " selected" : ""}>${esc2(f)}</option>`).join("")}</select>
      <select id="filPav"><option value="">os dois pavimentos</option>
        <option value="T"${pecaPav === "T" ? " selected" : ""}>térreo</option>
        <option value="S"${pecaPav === "S" ? " selected" : ""}>superior</option></select>
      <span class="conta">${alvo.length} de ${todas.length} peças · ${num(massa, 1)} kg${
        alvo.length > 900 ? " · mostrando as 900 primeiras" : ""}</span></div>
    <div class="rolagem"><table class="tabela"><thead><tr>${cab}</tr></thead>
      <tbody>${corpo}</tbody></table></div>
    <div class="eng-sec" style="margin-top:22px"><h3>Distribuição por família</h3>${hist}</div>`;
}

// ------------------------------------------------------------- plano de corte
let corteLim = 60;
function vistaCorte() {
  const N = ENG.nesting;
  const barras = N.barras.slice(0, corteLim).map(b => {
    let acum = 0;
    const segs = b.pecas.map((q, i) => {
      const x = acum / b.bruto * 100; acum += q.comp;
      return `<span title="${esc2(q.cod)} · ${q.comp} mm" style="position:absolute;left:${x}%;
        width:${(q.comp / b.bruto * 100).toFixed(3)}%;top:0;bottom:0;
        background:${i % 2 ? "#3f6fb5" : "#4d8fd6"};border-right:1px solid var(--surface)"></span>`;
    }).join("");
    const perda = b.bruto - b.usado;
    return `<div style="margin:0 0 6px">
      <div style="font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);
        display:flex;gap:10px"><span>${esc2(b.cod)}</span><span>${esc2(b.perfil)}</span>
        <span style="margin-left:auto">sobra ${num(perda)} mm${
          b.origem !== "nova" ? " · de sobra" : ""}</span></div>
      <div style="position:relative;height:15px;background:var(--alert-soft);
        border:1px solid var(--rule-soft)">${segs}</div></div>`;
  }).join("");
  return `${barraModos()}${leitura("corte")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Aproveitamento</span>
        <span class="val">${(N.aproveitamento * 100).toFixed(1)}</span><span class="uni">%</span></div>
      <div class="cartao"><span class="rot">Barras</span>
        <span class="val">${N.n_barras}</span><span class="uni">de 6 m</span></div>
      <div class="cartao"><span class="rot">Comprado</span>
        <span class="val">${num(N.bruto / 1000)}</span><span class="uni">m lineares</span></div>
      <div class="cartao"><span class="rot">Usado</span>
        <span class="val">${num(N.usado / 1000)}</span><span class="uni">m lineares</span></div>
      <div class="cartao"><span class="rot">Perda</span>
        <span class="val">${num(N.perda / 1000)}</span><span class="uni">m lineares</span></div>
    </div>
    <div class="eng-sec"><h3>Barras — azul é peça, vermelho é o que sobra</h3>${barras}
      ${N.n_barras > corteLim ? `<button class="btn" id="maisBarras">mostrar mais
        (${N.n_barras - corteLim} restantes)</button>` : ""}</div>`;
}
'''
JS_ENG += r'''
// -------------------------------------------------------------- montagem
let passoAtual = 0;
function svgPlanta(ate) {
  const ps = ENG.paineis;
  const xs = ps.flatMap(p => [p.x, p.x + (p.horizontal ? p.comp : 0)]);
  const ys = ps.flatMap(p => [p.y, p.y + (p.horizontal ? 0 : p.comp)]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const y0 = Math.min(...ys), y1 = Math.max(...ys);
  const feitos = new Set(ENG.montagem.passos.slice(0, ate)
    .map(s => s.painel).filter(Boolean));
  const linhas = ps.map(p => {
    const X2 = p.x + (p.horizontal ? p.comp : 0);
    const Y2 = p.y + (p.horizontal ? 0 : p.comp);
    const pronto = feitos.has(p.cod);
    return `<line x1="${p.x}" y1="${p.y}" x2="${X2}" y2="${Y2}"
      stroke="${pronto ? (p.pav === "S" ? "#c4491f" : "#3f6fb5") : "currentColor"}"
      stroke-opacity="${pronto ? 1 : 0.16}" stroke-width="${pronto ? 190 : 120}"
      stroke-linecap="butt"><title>${esc2(p.cod)} · ${p.comp} mm</title></line>`;
  }).join("");
  const M = 800;
  return `<svg viewBox="${x0 - M} ${y0 - M} ${x1 - x0 + 2 * M} ${y1 - y0 + 2 * M}"
    role="img" aria-label="Planta dos painéis, passo ${ate}">${linhas}</svg>`;
}
function vistaMontagem() {
  const M = ENG.montagem;
  const p = M.passos[Math.min(passoAtual, M.passos.length - 1)] || null;
  const linhas = M.passos.map((s, i) =>
    `<li><button type="button" data-passo="${i}" aria-current="${i === passoAtual}">
      ${String(s.passo).padStart(3, "0")} · ${esc2(s.descricao)}
      <span class="sub">${esc2(s.tipo)} · ${num(s.massa, 1)} kg ·
        ${s.duracao_h.toFixed(2)} h · acum ${s.acumulado_h.toFixed(1)} h</span></button></li>`).join("");
  return `${barraModos()}${leitura("montagem")}
    <div class="filtros">
      <button class="btn" id="playMont">${animar ? "⏸ pausar" : "▶ animar"}</button>
      <button class="btn" id="passoMenos">◀</button>
      <button class="btn" id="passoMais">▶</button>
      <button class="btn" id="passoZero">reiniciar</button>
      <span class="conta">passo ${passoAtual} de ${M.n_passos} ·
        ${p ? p.acumulado_h.toFixed(1) : "0,0"} h de ${M.horas} h ·
        ${p ? (p.progresso * 100).toFixed(0) : 0} %</span></div>
    <div class="eng-grid">
      <ul class="lista" id="listaPassos">${linhas}</ul>
      <div class="desenho">${svgPlanta(passoAtual)}
        <p class="cap">${p ? `<b>${esc2(p.cod)}</b> · ${esc2(p.descricao)} ·
          ferramenta: ${esc2(p.ferramenta)} · ${num(p.massa, 1)} kg`
          : "nenhum painel montado ainda"}<br>
          azul é térreo, vermelho é superior; o que ainda não subiu fica apagado.</p></div>
    </div>`;
}

// -------------------------------------------------------------- logística
function vistaLogistica() {
  const L = ENG.logistica, E = ENG.emissao, D = ENG.desmontabilidade;
  const b = (rot, v, extra) =>
    `<div style="margin:0 0 11px"><div style="font-family:var(--mono);font-size:11px;
      display:flex"><span>${rot}</span><span style="margin-left:auto;color:var(--ink-faint)">
      ${(v * 100).toFixed(1)} %${extra || ""}</span></div>
      <div style="height:11px;background:var(--rule-soft)"><i style="display:block;height:100%;
        width:${Math.min(100, v * 100).toFixed(1)}%;background:${v > 1 ? "var(--alert)" : "var(--accent)"}"></i></div></div>`;
  const co2 = Object.keys(E).filter(k => k !== "total" && typeof E[k] === "number");
  const maiorC = Math.max(...co2.map(k => E[k]));
  const linhas = co2.map(k =>
    `<div style="display:grid;grid-template-columns:120px 1fr 78px;gap:8px;align-items:center;
      font-family:var(--mono);font-size:11px;padding:2px 0"><span>${esc2(k)}</span>
      <span style="height:9px;background:var(--rule-soft)"><i style="display:block;height:100%;
        width:${(E[k] / maiorC * 100).toFixed(1)}%;background:#6fae7c"></i></span>
      <span style="text-align:right">${num(E[k])} kg</span></div>`).join("");
  return `${barraModos()}${leitura("logistica")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Container</span>
        <span class="val" style="font-size:15px">${esc2(L.container)}</span>
        <span class="uni">${L.volumes} volumes</span></div>
      <div class="cartao"><span class="rot">Massa embarcada</span>
        <span class="val">${num(L.massa)}</span><span class="uni">kg</span></div>
      <div class="cartao"><span class="rot">Limitante</span>
        <span class="val" style="font-size:15px">${esc2(L.limitante)}</span>
        <span class="uni">é o que enche primeiro</span></div>
      <div class="cartao"><span class="rot">Rejeitados</span>
        <span class="val">${L.rejeitados}</span><span class="uni">não couberam</span></div>
      <div class="cartao"><span class="rot">Desmontabilidade</span>
        <span class="val">${D.indice.toFixed(2)}</span><span class="uni">${esc2(D.classe)}</span></div>
    </div>
    <div class="eng-sec"><h3>Ocupação do container</h3>
      ${b("peso", L.uso_peso)}${b("volume", L.uso_volume)}</div>
    <div class="eng-sec"><h3>CO₂e incorporado — ${num(E.total)} kg no total (fatores H)</h3>
      ${linhas}</div>`;
}

// ------------------------------------------------------------- documentos
const DOCS = [["memorial", "memorial descritivo"], ["lista_de_pecas", "lista de peças"],
  ["plano_de_corte", "plano de corte"], ["packing_list", "packing list"],
  ["manual", "manual de montagem"], ["inspecao", "relatório de inspeção"]];
function vistaDocumentos() {
  const botoes = DOCS.map(([k, t]) =>
    `<button class="btn" data-doc="${k}" ${k === docSel ? 'style="border-color:var(--accent);color:var(--accent)"' : ""}>${t}</button>`).join("");
  const texto = docSel === "memorial_compressao"
    ? ENG.memoriais[engModo] : ENG.documentos[docSel];
  return `${barraModos()}${leitura("documentos")}
    <div class="docs">${botoes}
      <button class="btn" data-doc="memorial_compressao"
        ${docSel === "memorial_compressao" ? 'style="border-color:var(--accent);color:var(--accent)"' : ""}>memorial de cálculo (${engModo})</button></div>
    <pre class="doc-txt">${esc2(texto || "")}</pre>`;
}
'''
JS_ENG += r'''
// --------------------------------------------------------------- bloqueios
let contratoSel = null;
function vistaBloqueios() {
  const cs = ENG.contratos || [];
  if (!cs.length) return barraModos() + "<p class='conta'>sem contratos</p>";
  const c = cs.find(x => x.cod === contratoSel) || cs[0];
  const lista = cs.map(x =>
    `<li><button type="button" data-contrato="${esc2(x.cod)}"
       aria-current="${x.cod === c.cod}">${esc2(x.cod)}
       <span class="sub">${x.secoes.length} seç${x.secoes.length > 1 ? "ões" : "ão"} ·
         ${x.esquema.length} campos</span></button></li>`).join("");
  const campos = c.esquema.map(k =>
    `<tr><td>${esc2(k.nome)}</td><td>${esc2(k.tipo)}</td>
      <td>${esc2(k.unidade || "—")}</td>
      <td>${k.obrigatorio ? "obrigatório" : "opcional"}</td>
      <td>${esc2(k.dominio.length ? k.dominio.join(" · ") : (k.descricao || ""))}</td></tr>`).join("");
  const nSec = cs.reduce((s, x) => s + x.secoes.length, 0);
  const nCam = cs.reduce((s, x) => s + x.esquema.length, 0);
  return `${barraModos()}${leitura("bloqueios")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Contratos</span>
        <span class="val">${cs.length}</span><span class="uni">bloqueios declarados</span></div>
      <div class="cartao"><span class="rot">Seções cobertas</span>
        <span class="val">${nSec}</span><span class="uni">das 155 da especificação</span></div>
      <div class="cartao"><span class="rot">Campos</span>
        <span class="val">${nCam}</span><span class="uni">com tipo e unidade</span></div>
      <div class="cartao"><span class="rot">Números inventados</span>
        <span class="val">0</span><span class="uni">e a auditoria confere</span></div>
    </div>
    <div class="eng-grid"><ul class="lista">${lista}</ul>
      <div>
        <div class="desenho">
          <p class="cap" style="font-size:13px"><b>${esc2(c.cod)} — ${esc2(c.titulo)}</b><br><br>
            <b>Bloqueio.</b> ${esc2(c.bloqueio)}.<br><br>
            <b>Fonte.</b> ${esc2(c.fonte)}.<br><br>
            <b>Aceite.</b> ${esc2(c.aceite)}.
            ${c.esforco ? "<br><br><b>Falta escrever.</b> " + esc2(c.esforco) + "." : ""}<br><br>
            <b>Seções da especificação.</b> ${c.secoes.join(", ")}.</p></div>
        <div class="rolagem" style="margin-top:12px">
          <table class="tabela"><thead><tr><th>campo</th><th>tipo</th>
            <th>unidade</th><th>exigência</th><th>domínio ou descrição</th></tr></thead>
            <tbody>${campos}</tbody></table></div>
      </div></div>`;
}

// ---------------------------------------------------------------- roteador
function renderEng() {
  const alvo = document.getElementById("engConteudo");
  if (!ENG) { alvo.innerHTML = "<p class='conta'>carregando engenharia.json…</p>"; return; }
  const f = {painel: vistaPainel, paineis: vistaPaineis, pecas: vistaPecas,
             corte: vistaCorte, montagem: vistaMontagem,
             logistica: vistaLogistica, documentos: vistaDocumentos,
             bloqueios: vistaBloqueios}[engVista];
  alvo.innerHTML = f();
  const v = VISTAS.find(x => x[0] === engVista);
  document.getElementById("sheetTitle").firstChild.nodeValue =
    "Engenharia · " + v[1];
  document.getElementById("sheetMeta").textContent = v[2];
  document.querySelectorAll("#vistasEng button").forEach(b =>
    b.setAttribute("aria-current", (b.dataset.vista === engVista) + ""));
  ligarEng();
}

function ligarEng() {
  const em = (sel, ev, fn) => document.querySelectorAll(sel).forEach(
    n => n.addEventListener(ev, fn));
  em("[data-leitura]", "click", e => {
    engModo = e.currentTarget.dataset.leitura; renderEng();
  });
  em("[data-painel]", "click", e => {
    painelSel = e.currentTarget.dataset.painel; renderEng();
  });
  em("[data-ord]", "click", e => {
    const c = e.currentTarget.dataset.ord;
    pecaOrd = {campo: c, asc: pecaOrd.campo === c ? !pecaOrd.asc : true};
    renderEng();
  });
  const busca = document.getElementById("buscaPeca");
  if (busca) {
    busca.addEventListener("input", e => {
      pecaBusca = e.target.value; renderEng();
      const n = document.getElementById("buscaPeca");
      n.focus(); n.setSelectionRange(n.value.length, n.value.length);
    });
    document.getElementById("filFam").addEventListener("change",
      e => { pecaFam = e.target.value; renderEng(); });
    document.getElementById("filPav").addEventListener("change",
      e => { pecaPav = e.target.value; renderEng(); });
  }
  const mais = document.getElementById("maisBarras");
  if (mais) mais.addEventListener("click", () => { corteLim += 60; renderEng(); });
  em("[data-passo]", "click", e => {
    passoAtual = Number(e.currentTarget.dataset.passo); pararAnim(); renderEng();
  });
  em("[data-doc]", "click", e => { docSel = e.currentTarget.dataset.doc; renderEng(); });
  em("[data-contrato]", "click", e => {
    contratoSel = e.currentTarget.dataset.contrato; renderEng();
  });
  const play = document.getElementById("playMont");
  if (play) {
    play.addEventListener("click", () => animar ? pararAnim(true) : tocarAnim());
    document.getElementById("passoMenos").addEventListener("click",
      () => { passoAtual = Math.max(0, passoAtual - 1); pararAnim(); renderEng(); });
    document.getElementById("passoMais").addEventListener("click",
      () => { passoAtual = Math.min(ENG.montagem.n_passos, passoAtual + 1);
              pararAnim(); renderEng(); });
    document.getElementById("passoZero").addEventListener("click",
      () => { passoAtual = 0; pararAnim(); renderEng(); });
  }
}

function pararAnim(redesenhar) {
  if (animar) { clearInterval(animar); animar = null; if (redesenhar) renderEng(); }
}
function tocarAnim() {
  if (passoAtual >= ENG.montagem.n_passos) passoAtual = 0;
  animar = setInterval(() => {
    passoAtual += 1;
    if (passoAtual >= ENG.montagem.n_passos) { passoAtual = ENG.montagem.n_passos; pararAnim(); }
    const d = document.querySelector("#engConteudo .desenho");
    const c = document.querySelector("#engConteudo .conta");
    if (!d) { pararAnim(); return; }
    d.innerHTML = svgPlanta(passoAtual) + d.innerHTML.slice(d.innerHTML.indexOf("<p class="));
    const s = ENG.montagem.passos[passoAtual - 1];
    if (c) c.textContent = `passo ${passoAtual} de ${ENG.montagem.n_passos} · ` +
      `${s ? s.acumulado_h.toFixed(1) : "0,0"} h de ${ENG.montagem.horas} h · ` +
      `${s ? (s.progresso * 100).toFixed(0) : 0} %`;
  }, 140);
  renderEng();
}

let carregouEng = false;
function abrirEng() {
  if (carregouEng) { renderEng(); return; }
  carregouEng = true;
  const ul = document.getElementById("vistasEng");
  VISTAS.forEach(([id, nome, sub]) => {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button"; b.dataset.vista = id;
    b.innerHTML = `${nome}<span class="sub">${sub}</span>`;
    b.addEventListener("click", () => { engVista = id; pararAnim(); renderEng(); });
    li.appendChild(b); ul.appendChild(li);
  });
  fetch("engenharia.json").then(r => r.json()).then(d => {
    ENG = d;
    painelSel = d.paineis[0].cod;
    renderEng();
  }).catch(() => {
    document.getElementById("engConteudo").innerHTML =
      "<div class='selo nao'><b>engenharia.json não carregou</b>" +
      "<span>a aba mostra o motor; sem o arquivo não há o que mostrar</span></div>";
  });
}
'''
