"""VISUALIZADOR — parte 6: o comodo na mao (R77).

Um quarto modo, "Comodo": escolhe-se um ambiente e o visualizador monta uma
pilha vertical — a planta recortada em volta dele, o forro, a hidraulica, a
eletrica, o clima, o layout, a marcenaria, os dados, o incendio, o
contraventamento, as elevacoes e os cortes que o mostram — cada um lido da
propria prancha: o SVG e clonado e o viewBox e apertado na caixa dos grupos
que levam o codigo do ambiente (data-cod / data-amb). Nao ha tabela de
coordenadas paralela: se a prancha mudar, o recorte muda. Os quadros de
dados vem do engenharia.json ja carregado.
"""

CSS_COMODO = r'''
  /* ---------- comodo a comodo ---------- */
  #stageComodo{background:var(--stage); padding:12px}
  .ctit{background:var(--surface); border:1px solid var(--rule); padding:12px 14px; margin-bottom:10px}
  .ctit h3{margin:0 0 2px; font-family:var(--display); font-size:18px; letter-spacing:-.01em}
  .ctit .sub{font-family:var(--mono); font-size:10.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--ink-faint)}
  .ctit .fig{display:inline-block; padding:8px 14px 0 0; border:none}
  .ccard{background:var(--surface); border:1px solid var(--rule); margin-bottom:10px}
  .ccard summary{padding:10px 12px; font-family:var(--display); font-weight:600; font-size:14px;
                 cursor:pointer; list-style:none; display:flex; justify-content:space-between; align-items:center}
  .ccard summary::-webkit-details-marker{display:none}
  .ccard summary .pr{font-family:var(--mono); font-size:10.5px; color:var(--ink-faint); letter-spacing:.06em}
  .ccard summary::after{content:"+"; font-family:var(--mono); color:var(--ink-faint); margin-left:8px}
  .ccard[open] summary::after{content:"−"}
  .crop{background:#fff; border-top:1px solid var(--rule-soft); min-height:60px}
  .crop svg{display:block; width:100%; height:auto; max-height:72vh}
  .crop .conta{padding:10px 12px}
  .cdados{border-top:1px solid var(--rule-soft); padding:8px 12px 12px; overflow-x:auto}
  .cdados table{width:100%; border-collapse:collapse; font-size:12.5px}
  .cdados td, .cdados th{padding:4px 6px; border-top:1px solid var(--rule-soft); text-align:left; vertical-align:top}
  .cdados th{font-family:var(--mono); font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:var(--ink-faint); border-top:none}
  .cdados td.num{text-align:right; font-family:var(--mono); font-variant-numeric:tabular-nums}
  @media (min-width:861px){
    #stageComodo{display:grid; grid-template-columns:1fr 1fr; gap:10px; align-items:start}
    #stageComodo .ctit{grid-column:1 / -1}
    .ccard{margin-bottom:0}
  }
'''

HTML_COMODO = r'''
      <div id="stageComodo" hidden></div>
'''

JS_COMODO = r'''
// =====================================================================
// COMODO — tudo de um ambiente, numa pilha vertical
// =====================================================================
let carregouComodo = false, comodoSel = null;
// [prancha do terreo, prancha do superior, titulo]; a mesma para os dois quando so ha uma
const PLANTAS_COMODO = [
  ["02", "03", "Planta baixa"], ["04", "42", "Layout"], ["16", "16", "Forro e iluminação"],
  ["26", "26", "Hidráulica"], ["27", "27", "Elétrica e dados"], ["28", "28", "Climatização"],
  ["54", "54", "Humanizada"], ["55", "55", "Marcenaria em planta"],
  ["56", "57", "Marcenaria — elevações"], ["51", "51", "Elevações internas"], ["50", "50", "Cortes"],
  ["65", "65", "Dados, CFTV e alarme"], ["66", "66", "Incêndio"], ["67", "67", "Contraventamento"],
];

function abrirComodo() {
  garantirENG().then(() => {
    if (!carregouComodo) {
      carregouComodo = true;
      const ul = document.getElementById("comodos");
      ENG.ambientes.dossies.forEach((d, i) => {
        const li = document.createElement("li");
        const b = document.createElement("button");
        b.type = "button"; b.dataset.amb = d.cod;
        b.innerHTML = `${esc2(d.nome)}<span class="sub">${esc2(d.cod)} · ${num(d.area, 1)} m²</span>`;
        b.addEventListener("click", () => {
          document.querySelectorAll("#comodos button").forEach(x => x.setAttribute("aria-current", "false"));
          b.setAttribute("aria-current", "true");
          comodoSel = d.cod; renderComodo();
        });
        if (i === 0) b.setAttribute("aria-current", "true");
        li.appendChild(b); ul.appendChild(li);
      });
      comodoSel = comodoSel || ENG.ambientes.dossies[0].cod;
    }
    renderComodo();
  });
}

function montarRecorte(div, pr, cod) {
  div.innerHTML = "<p class='conta'>lendo a prancha…</p>";
  lerRecurso(`PR-${pr}.svg`).then(txt => {
    const doc = new DOMParser().parseFromString(txt, "image/svg+xml");
    const svg = document.importNode(doc.documentElement, true);
    svg.removeAttribute("width"); svg.removeAttribute("height");
    div.innerHTML = ""; div.appendChild(svg);
    const els = [...svg.querySelectorAll(`[data-cod="${cod}"], [data-amb="${cod}"]`)];
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    els.forEach(e => {
      let b; try { b = e.getBBox(); } catch (_) { return; }
      if (b.width < 0.5 && b.height < 0.5) return;
      x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y);
      x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height);
    });
    if (x1 < x0) {
      div.innerHTML = "<p class='conta'>este cômodo não aparece nesta prancha</p>";
      return;
    }
    // margem de 12 mm de papel: o contexto em volta (a parede do vizinho, a cota)
    const m = 12;
    svg.setAttribute("viewBox", `${(x0 - m).toFixed(1)} ${(y0 - m).toFixed(1)} ${(x1 - x0 + 2 * m).toFixed(1)} ${(y1 - y0 + 2 * m).toFixed(1)}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  }).catch(() => { div.innerHTML = "<p class='conta'>prancha indisponível</p>"; });
}

function renderComodo() {
  const alvo = document.getElementById("stageComodo");
  const A = ENG.ambientes;
  const d = A.dossies.find(x => x.cod === comodoSel) || A.dossies[0];
  const X = ENG.executivo || {}, M = ENG.marcenaria || {};
  const tab = (cab, linhas) => linhas.length
    ? `<table><thead><tr>${cab.map(c => `<th>${c}</th>`).join("")}</tr></thead><tbody>${
        linhas.map(l => `<tr>${l.map((v, i) => `<td class="${typeof v === "number" ? "num" : ""}">${
          typeof v === "number" ? num(v, Number.isInteger(v) ? 0 : 1) : esc2(String(v ?? "—"))}</td>`).join("")}</tr>`).join("")}</tbody></table>`
    : "<p class='conta'>nada declarado para este cômodo</p>";
  const cartao = (titulo, corpo, pr, aberto) =>
    `<details class="ccard"${aberto ? " open" : ""}${pr ? ` data-pr="${pr}" data-cod="${esc2(d.cod)}"` : ""}>
       <summary>${titulo}${pr ? `<span class="pr">PR-${pr}</span>` : ""}</summary>
       ${pr ? `<div class="crop"></div>` : `<div class="cdados">${corpo}</div>`}</details>`;
  const pav = d.pav === "S" ? 1 : 0;
  let html = `<div class="ctit"><span class="sub">${esc2(d.cod)} · ${d.pav === "S" ? "superior" : "térreo"} · ${esc2(d.categoria)}</span>
    <h3>${esc2(d.nome)}</h3>
    <div class="fig"><dt>Área útil</dt><dd>${num(d.area_util, 2)} <span>m²</span></dd></div>
    <div class="fig"><dt>Vãos</dt><dd>${d.n_vaos} <span>${d.externos} externo(s)</span></dd></div>
    <div class="fig"><dt>Iluminação</dt><dd>${(d.frac_ilum * 100).toFixed(0)} <span>% do piso · mín. ${(d.exige_ilum * 100).toFixed(1)}</span></dd></div>
    <div class="fig"><dt>Forro</dt><dd>${num(d.forro_h, 0)} <span>mm</span></dd></div></div>`;
  PLANTAS_COMODO.forEach(([pt, ps, tit], i) => { html += cartao(tit, "", pav ? ps : pt, i === 0); });
  html += cartao("Acabamentos", tab(["superfície", "especificação"], [
    ["piso", d.piso], ["parede", d.parede], ["forro", d.forro], ["rodapé", d.rodape],
    ["revestimento até", d.revest_h ? `${d.revest_h} mm` : "—"]]));
  html += cartao("Vãos", tab(["tipo", "l × a", "peitoril", "m²", "onde"],
    (d.vaos || []).map(v => [v.tipo, `${v.larg} × ${v.alt}`, v.peitoril || "—", v.area, v.externo ? "externo" : "interno"])));
  const circ = ((X.circuitos || {}).circuitos || []).filter(c => c.amb === d.cod);
  html += cartao("Elétrica", `<p class="conta">${d.tugs_norma} tomadas de uso geral (${d.tug_va} VA) · iluminação ${d.ilum_va} VA${d.molhada_eletrica ? " · área molhada: DR" : ""}</p>` +
    tab(["circuito", "VA", "V", "disj", "mm²", "queda"], circ.map(c => [c.cod, c.va, c.v, `${c.disjuntor_a} A`, c.secao_mm2, `${c.queda_pct.toFixed(1)} %`])));
  const agua = ((X.agua || {}).pecas || []).filter(p => p.amb === d.cod);
  const esg = ((X.esgoto || {}).ramais || []).filter(r => r.amb === d.cod);
  html += cartao("Hidráulica e esgoto",
    tab(["peça", "tipo", "pressão kPa", "como"], agua.map(p => [p.cod, p.tipo, p.dinamica_kpa, p.gravidade_ok ? "gravidade" : "TC-14"])) +
    tab(["ramal", "DN", "caimento", "destino", "vent."], esg.map(r => [r.peca, `DN${r.dn}`, `${(r.caimento * 100).toFixed(0)} %`, r.destino, r.ventilado ? "ok" : "ramal DN50"])));
  html += cartao("Climatização", tab(["equipamento", "BTU/h", "pessoas", "obs."],
    (d.clima || []).map(c => [c.tipo || c.equip || "split", c.capacidade, c.pessoas, c.obs || ""])));
  const mov = (M.moveis || []).filter(m => m.amb === d.cod);
  html += cartao("Marcenaria", tab(["móvel", "família", "frente", "mód", "portas", "gav"],
    mov.map(m => [m.cod, m.familia, `${num(m.frente, 0)} mm`, m.n_modulos, m.n_portas, m.n_gavetas])));
  const S = X.seguranca || {};
  const dados = (S.dados || []).filter(p => p.amb === d.cod).map(p => [p.cod, p.uso, p.n]);
  const inc = ((S.incendio || {}).detectores || []).filter(p => p.amb === d.cod).map(p => [p.cod, p.tipo, 1])
    .concat(((S.incendio || {}).extintores || []).filter(p => p.amb === d.cod).map(p => [p.cod, p.item, 1]));
  html += cartao("Dados e segurança", tab(["item", "uso / tipo", "n"], dados.concat(inc)));
  const cs = ((X.lsf || {}).cargas_suspensas || []).filter(c => c.amb === d.cod);
  html += cartao("Reforços na parede (LSF)", tab(["item", "família", "kg", "parede", "faixa mm"],
    cs.map(c => [c.cod, c.familia, c.carga_kg, c.parede || "—", `${c.z0}–${c.z1}`])));
  const ach = A.achados.filter(x => x.amb === d.cod);
  html += cartao("Conferências", ach.length
    ? ach.map(x => `<div class="selo ${x.nivel === "ERRO" ? "nao" : ""}" style="margin-bottom:6px"><b>${esc2(x.item)}</b><span>${esc2(x.texto)}</span></div>`).join("")
    : "<div class='selo'><b>sem divergência</b><span>acabamento, vão, tomada, peça hidráulica, ralo, clima e parede conferem entre si</span></div>");
  alvo.innerHTML = html;
  alvo.querySelectorAll("details[data-pr]").forEach(det => {
    const crop = det.querySelector(".crop");
    const carregar = () => { if (det.open && !crop.querySelector("svg")) montarRecorte(crop, det.dataset.pr, det.dataset.cod); };
    det.addEventListener("toggle", () => { if (!det.open) crop.innerHTML = ""; else carregar(); });
    carregar();
  });
  // a barra de endereco acompanha o comodo: o link "#comodo/T-COZ" abre a cozinha
  // (o <select> do celular se refaz sozinho: ele observa o aria-current da lista)
  if (typeof gravarRota === "function") gravarRota();
}
'''
