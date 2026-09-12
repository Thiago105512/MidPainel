"""Motor 2D do visualizador: a prancha como documento, nao como figura.

Ate a revisao R11 a prancha era carregada numa <img>. O SVG era vetorial, mas
o navegador o tratava como fotografia: nada dentro dele era alcancavel. A
partir de R12 o SVG entra no DOM, e como o Canvas passou a emitir procedencia
(data-tipo / data-cod / data-*), cada traco sabe de onde veio. Dai saem, sem
biblioteca nenhuma, camadas, ficha do ambiente, busca, medicao, minimapa e o
modo sem moldura.
"""

CSS_2D = r'''
  /* ---------- palco 2D com o SVG dentro do DOM ---------- */
  .folha{position:absolute; top:0; left:0; transform-origin:0 0;
         background:#fff; box-shadow:0 2px 10px rgba(0,0,0,.28)}
  .folha svg{display:block}
  .folha img{display:block; width:100%; height:100%}
  .folha g[data-cod]{cursor:pointer}
  .folha .realce{fill:var(--accent); fill-opacity:.13; stroke:var(--accent);
                 stroke-width:.5; pointer-events:none}
  .folha .achado{fill:#f5a623; fill-opacity:.30; stroke:#c77700;
                 stroke-width:.4; pointer-events:none}
  .folha .regua{stroke:var(--alert); stroke-width:.45; fill:none; pointer-events:none}
  .folha .reguatxt{fill:var(--alert); font-family:monospace; pointer-events:none}
  .stage.medindo{cursor:crosshair}

  /* ---------- painel lateral do 2D ---------- */
  .ficha{
    position:absolute; top:12px; right:12px; width:236px; max-height:calc(100% - 24px);
    overflow-y:auto; background:var(--surface); border:1px solid var(--rule);
    padding:10px 12px; border-radius:2px; box-shadow:var(--shadow); font-size:12.5px;
  }
  .ficha h3{margin:0 0 2px; font-family:var(--display); font-size:14px; letter-spacing:-.01em}
  .ficha .cod{font-family:var(--mono); font-size:10.5px; letter-spacing:.08em;
              text-transform:uppercase; color:var(--accent); margin:0 0 8px}
  .ficha dl{margin:0; display:grid; grid-template-columns:auto 1fr; gap:4px 10px}
  .ficha dt{font-family:var(--mono); font-size:10px; letter-spacing:.06em;
            text-transform:uppercase; color:var(--ink-faint)}
  .ficha dd{margin:0; font-size:12px; color:var(--ink-soft)}
  .ficha .vazio{color:var(--ink-faint); font-size:12px; margin:0}
  .ficha .fechar{position:absolute; top:6px; right:8px; background:none; border:none;
                 color:var(--ink-faint); cursor:pointer; font-size:15px; line-height:1}

  /* ---------- minimapa e escala grafica ---------- */
  .rodape2d{
    position:absolute; left:12px; bottom:12px; display:flex; align-items:flex-end;
    gap:12px; pointer-events:none;
  }
  .rodape2d > *{pointer-events:auto}
  .minimapa{position:relative; width:150px; border:1px solid var(--rule);
            background:#fff; box-shadow:var(--shadow); cursor:pointer}
  .minimapa img{display:block; width:100%; opacity:.85}
  .minimapa .janela{position:absolute; border:1.5px solid var(--accent);
                    background:rgba(10,106,74,.12); pointer-events:none}
  .escalag{background:var(--surface); border:1px solid var(--rule); padding:5px 8px;
           border-radius:2px; font-family:var(--mono); font-size:10px;
           letter-spacing:.06em; color:var(--ink-soft)}
  .escalag .barra{height:6px; border:1px solid var(--ink-soft); border-top:none;
                  margin-bottom:3px; position:relative}
  .escalag .barra::after{content:""; position:absolute; left:0; top:0; bottom:0;
                         width:50%; background:var(--ink-soft); opacity:.55}

  /* ---------- camadas e busca do 2D ---------- */
  .barra2 {display:flex; flex-wrap:wrap; gap:8px 14px; align-items:center;
           padding:8px 12px; border-bottom:1px solid var(--rule-soft);
           background:var(--surface)}
  .camadas2d{display:flex; flex-wrap:wrap; gap:2px}
  .camadas2d label{display:flex; align-items:center; gap:5px; font-family:var(--mono);
    font-size:10px; letter-spacing:.05em; text-transform:uppercase;
    color:var(--ink-soft); cursor:pointer; padding:2px 5px; white-space:nowrap}
  .camadas2d input{accent-color:var(--accent); margin:0}
  .busca{display:flex; align-items:center; gap:6px; margin-left:auto}
  .busca input{font-family:var(--mono); font-size:11.5px; border:1px solid var(--rule);
    background:var(--surface); color:var(--ink); padding:4px 8px; width:150px;
    border-radius:2px}
  .busca input:focus{outline:2px solid var(--accent); outline-offset:1px}
  .busca .conta{font-family:var(--mono); font-size:10.5px; color:var(--ink-faint);
                min-width:58px}
  .btn[aria-pressed="true"]{background:var(--accent); border-color:var(--accent); color:#fff}
'''

HTML_2D = r'''
      <div class="barra2" id="barra2">
        <div class="camadas2d" id="camadas2d"></div>
        <div class="busca">
          <input type="search" id="busca" placeholder="buscar na prancha"
                 aria-label="Buscar texto na prancha">
          <span class="conta" id="buscaConta"></span>
        </div>
      </div>
'''

HTML_PALCO_2D = r'''
      <div class="stage" id="stage">
        <div class="folha" id="folha"></div>
        <div class="ficha" id="ficha" hidden></div>
        <div class="rodape2d">
          <div class="minimapa" id="mini" title="Clique para deslocar">
            <img id="miniImg" alt="">
            <div class="janela" id="miniJanela"></div>
          </div>
          <div class="escalag" id="escalag" hidden>
            <div class="barra" id="escalagBarra"></div>
            <span id="escalagTxt"></span>
          </div>
        </div>
      </div>
'''

JS_2D = r'''
// =====================================================================
// 2D — a prancha como DOCUMENTO
//
// O SVG entra no DOM em vez de ficar dentro de uma <img>. Duas consequencias:
// o zoom passa a redesenhar o vetor (a <img> rasteriza uma vez e estica), e
// cada <g data-tipo/data-cod> emitido pelo Canvas vira um objeto alcancavel.
// Camadas, ficha, busca, medicao e minimapa saem dai, sem biblioteca nenhuma.
// =====================================================================
const NIVEIS = [1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24];
let escala = 1, base = 1, tx = 0, ty = 0, nat = {w: 841, h: 594};
let svg2d = null, realce = null, capaRegua = null;
let semMoldura = false, medindo = false, pontoA = null, denom = 0;

const folha = document.getElementById("folha"),
      stage = document.getElementById("stage"),
      zval = document.getElementById("zval"),
      ficha = document.getElementById("ficha"),
      mini = document.getElementById("mini"),
      miniImg = document.getElementById("miniImg"),
      miniJanela = document.getElementById("miniJanela"),
      escalag = document.getElementById("escalag");

// camadas: rotulo e se comeca ligada
const CAMADAS2D = [
  ["ambiente", "Ambientes", true], ["parede", "Paredes", true],
  ["vao", "Vãos", true], ["piso", "Pisos", true],
  ["bancada", "Bancadas", true], ["louca", "Louças", true],
  ["equipamento", "Equip.", true], ["marcenaria", "Marcenaria", true],
  ["escada", "Escada", true], ["piscina", "Piscina", true],
  ["cota", "Cotas", true], ["moldura", "Moldura", true],
];
const ocultas = new Set();

function NS(tag) { return document.createElementNS("http://www.w3.org/2000/svg", tag); }

// ---------------------------------------------------------------- carga
async function carregarFolha(arquivo) {
  try {
    const r = await fetch(arquivo);
    if (!r.ok) throw new Error(r.status);
    const txt = await r.text();
    folha.innerHTML = txt.replace(/<\?xml[^?]*\?>/, "");
    svg2d = folha.querySelector("svg");
    svg2d.removeAttribute("width");
    svg2d.removeAttribute("height");
    const vb = (svg2d.getAttribute("viewBox") || "0 0 841 594").trim().split(/[\s,]+/);
    nat = {w: parseFloat(vb[2]), h: parseFloat(vb[3])};
    prepararFolha();
  } catch (e) {
    // file:// bloqueia fetch; a <img> continua servindo de plano B, so que
    // sem nada do que vem do DOM
    folha.innerHTML = `<img src="${arquivo}" alt="">`;
    svg2d = null;
    nat = {w: 841, h: 594};
  }
  miniImg.src = arquivo;
  ajustar();
}

function prepararFolha() {
  // fundo da pagina ganha procedencia para poder sair no modo sem moldura
  const fundo = svg2d.querySelector(":scope > rect");
  if (fundo && !fundo.dataset.tipo) fundo.dataset.tipo = "fundo";

  realce = NS("rect"); realce.setAttribute("class", "realce");
  realce.style.display = "none";
  svg2d.appendChild(realce);
  capaRegua = NS("g"); svg2d.appendChild(capaRegua);

  montarCamadas();
  aplicarCamadas();
  aplicarSemMoldura();
}

// ------------------------------------------------------------- zoom/pan
function calcBase() {
  const r = stage.getBoundingClientRect();
  base = Math.min(r.width / nat.w, r.height / nat.h) * 0.94;
}
function aplicar() {
  const alvo = svg2d || folha.querySelector("img");
  if (alvo) {
    alvo.style.width = (nat.w * escala) + "px";
    alvo.style.height = (nat.h * escala) + "px";
  }
  folha.style.transform = `translate(${Math.round(tx)}px,${Math.round(ty)}px)`;
  zval.textContent = Math.round(escala / base * 100) + "%";
  atualizarMini();
  atualizarEscalaGrafica();
}
function ajustar(caixa) {
  calcBase();
  const r = stage.getBoundingClientRect();
  if (caixa) {
    escala = Math.min(r.width / caixa.width, r.height / caixa.height) * 0.94;
    tx = (r.width - caixa.width * escala) / 2 - caixa.x * escala;
    ty = (r.height - caixa.height * escala) / 2 - caixa.y * escala;
  } else {
    escala = base;
    tx = (r.width - nat.w * escala) / 2;
    ty = (r.height - nat.h * escala) / 2;
  }
  aplicar();
}
function zoomPara(nova, cx, cy) {
  const r = stage.getBoundingClientRect();
  const px = (cx ?? r.width / 2 + r.left) - r.left;
  const py = (cy ?? r.height / 2 + r.top) - r.top;
  nova = Math.min(Math.max(nova, base * 0.6), base * 40);
  tx = px - (px - tx) * (nova / escala);
  ty = py - (py - ty) * (nova / escala);
  escala = nova;
  aplicar();
}
function passo(dir, cx, cy) {
  const atual = escala / base;
  let alvo;
  if (dir > 0) alvo = NIVEIS.find(n => n > atual + 0.01) ?? NIVEIS[NIVEIS.length - 1];
  else alvo = [...NIVEIS].reverse().find(n => n < atual - 0.01) ?? NIVEIS[0];
  zoomPara(base * alvo, cx, cy);
}
function papel(ev) {
  const r = stage.getBoundingClientRect();
  return {x: (ev.clientX - r.left - tx) / escala, y: (ev.clientY - r.top - ty) / escala};
}
function centrarEm(x, y) {
  const r = stage.getBoundingClientRect();
  tx = r.width / 2 - x * escala;
  ty = r.height / 2 - y * escala;
  aplicar();
}

stage.addEventListener("wheel", e => {
  e.preventDefault();
  if (e.ctrlKey) zoomPara(escala * Math.pow(0.99, e.deltaY), e.clientX, e.clientY);
  else passo(e.deltaY < 0 ? 1 : -1, e.clientX, e.clientY);
}, {passive: false});

let arr = null;
stage.addEventListener("pointerdown", e => {
  if (medindo) return;
  stage.setPointerCapture(e.pointerId);
  arr = {x: e.clientX, y: e.clientY, tx, ty, mov: false};
  stage.classList.add("dragging");
});
stage.addEventListener("pointermove", e => {
  if (!arr) return;
  if (Math.abs(e.clientX - arr.x) + Math.abs(e.clientY - arr.y) > 3) arr.mov = true;
  tx = arr.tx + (e.clientX - arr.x);
  ty = arr.ty + (e.clientY - arr.y);
  aplicar();
});
["pointerup", "pointercancel"].forEach(ev => stage.addEventListener(ev, () => {
  arr = null; stage.classList.remove("dragging");
}));
stage.addEventListener("dblclick", e => { if (!medindo) passo(1, e.clientX, e.clientY); });
document.getElementById("zin").onclick = () => passo(1);
document.getElementById("zout").onclick = () => passo(-1);
document.getElementById("fit").onclick = () => ajustar(semMoldura ? caixaDesenho() : null);

// ------------------------------------------------------------- camadas
function montarCamadas() {
  const cx = document.getElementById("camadas2d");
  const presentes = new Set(
    [...svg2d.querySelectorAll("[data-tipo]")].map(g => g.dataset.tipo));
  cx.innerHTML = "";
  CAMADAS2D.forEach(([id, rot]) => {
    if (!presentes.has(id) && !(id === "moldura" && presentes.has("carimbo"))) return;
    const lab = document.createElement("label");
    lab.innerHTML = `<input type="checkbox" ${ocultas.has(id) ? "" : "checked"}>${rot}`;
    lab.querySelector("input").addEventListener("change", ev => {
      if (ev.target.checked) ocultas.delete(id); else ocultas.add(id);
      aplicarCamadas();
    });
    cx.appendChild(lab);
  });
}
function aplicarCamadas() {
  if (!svg2d) return;
  const grupo = t => (t === "moldura" ? ["moldura", "carimbo", "notas"] : [t]);
  CAMADAS2D.forEach(([id]) => {
    const esconde = ocultas.has(id);
    grupo(id).forEach(t => svg2d.querySelectorAll(`[data-tipo="${t}"]`)
      .forEach(g => { g.style.display = esconde ? "none" : ""; }));
  });
  aplicarSemMoldura();
}

// ------------------------------------------------- modo sem moldura (MVP-3)
function caixaDesenho() {
  // mede o desenho sem a pagina: o retangulo de fundo cobre o A1 inteiro e
  // falsearia a medida
  if (!svg2d) return null;
  const fora = ["fundo", "moldura", "carimbo", "notas"];
  const guarda = [];
  fora.forEach(t => svg2d.querySelectorAll(`[data-tipo="${t}"]`).forEach(g => {
    guarda.push([g, g.style.display]); g.style.display = "none";
  }));
  let bb = null;
  try { bb = svg2d.getBBox(); } catch (e) { bb = null; }
  guarda.forEach(([g, d]) => { g.style.display = d; });
  if (!bb || !bb.width) return null;
  // getBBox ignora clip-path: devolve a geometria ANTES do recorte. O que esta
  // fora da pagina ja nao aparece, entao a caixa util e a intersecao com ela.
  const m = 8;
  const x0 = Math.max(0, bb.x - m), y0 = Math.max(0, bb.y - m);
  const x1 = Math.min(nat.w, bb.x + bb.width + m);
  const y1 = Math.min(nat.h, bb.y + bb.height + m);
  if (x1 <= x0 || y1 <= y0) return null;
  return {x: x0, y: y0, width: x1 - x0, height: y1 - y0};
}
function aplicarSemMoldura() {
  if (!svg2d) return;
  ["moldura", "carimbo", "notas"].forEach(t =>
    svg2d.querySelectorAll(`[data-tipo="${t}"]`).forEach(g => {
      if (semMoldura) g.style.display = "none";
      else if (!ocultas.has("moldura")) g.style.display = "";
    }));
}
document.getElementById("semmold").onclick = e => {
  semMoldura = !semMoldura;
  e.currentTarget.setAttribute("aria-pressed", semMoldura + "");
  aplicarSemMoldura();
  ajustar(semMoldura ? caixaDesenho() : null);
};

// ------------------------------------------------------- ficha do elemento
const ROTULO = {
  ambiente: "Ambiente", parede: "Parede", vao: "Vão", piso: "Piso",
  bancada: "Bancada", louca: "Louça", equipamento: "Equipamento",
  marcenaria: "Marcenaria", escada: "Escada", piscina: "Piscina",
  cota: "Cota", carimbo: "Carimbo", notas: "Notas", moldura: "Moldura",
};
const CAMPO = {
  rot: "nome", area: "área", larg: "largura", prof: "profundidade",
  alt: "altura", peitoril: "peitoril", esp: "espessura", face: "face",
  familia: "família", amb: "ambiente", desc: "descrição", pav: "pavimento",
  molhado: "área molhada", aberto: "área aberta", cubas: "cubas",
  coccao: "cocção", lamina: "lâmina", volume: "volume", espelhos: "espelhos",
  piso: "piso", patamar: "patamar", parciais: "cotas parciais", rev: "revisão",
  box: null,
};
const UNID = {area: " m²", larg: " mm", prof: " mm", alt: " mm", peitoril: " mm",
              esp: " mm", lamina: " m²", volume: " m³", piso: " mm", patamar: " mm"};

function mostrarFicha(g) {
  const d = g.dataset, tipo = d.tipo;
  const linhas = [];
  for (const k in d) {
    if (k === "tipo" || k === "cod" || CAMPO[k] === null) continue;
    const nome = CAMPO[k] || k;
    linhas.push(`<dt>${nome}</dt><dd>${d[k]}${UNID[k] || ""}</dd>`);
  }
  const extra = (tipo === "ambiente" && FICHAS[d.cod]) ? FICHAS[d.cod] : null;
  if (extra) for (const k in extra) linhas.push(`<dt>${k}</dt><dd>${extra[k]}</dd>`);
  ficha.innerHTML =
    `<button class="fechar" type="button" aria-label="Fechar">×</button>` +
    `<h3>${d.rot || ROTULO[tipo] || tipo}</h3>` +
    `<p class="cod">${d.cod ? d.cod + " · " : ""}${ROTULO[tipo] || tipo}</p>` +
    (linhas.length ? `<dl>${linhas.join("")}</dl>`
                   : `<p class="vazio">Sem dados declarados.</p>`);
  ficha.hidden = false;
  ficha.querySelector(".fechar").onclick = () => { ficha.hidden = true; esconderRealce(); };
}
function caixaDoGrupo(g) {
  if (g.dataset.box) {
    const v = g.dataset.box.split(" ").map(Number);
    return {x: v[0], y: v[1], width: v[2], height: v[3]};
  }
  try { return g.getBBox(); } catch (e) { return null; }
}
function porRealce(g, classe) {
  const bb = caixaDoGrupo(g);
  if (!bb || !realce) return;
  realce.setAttribute("class", classe || "realce");
  realce.setAttribute("x", bb.x - 1); realce.setAttribute("y", bb.y - 1);
  realce.setAttribute("width", bb.width + 2); realce.setAttribute("height", bb.height + 2);
  realce.style.display = "";
}
function esconderRealce() { if (realce) realce.style.display = "none"; }

folha.addEventListener("click", e => {
  if (medindo || (arr && arr.mov)) return;
  const g = e.target.closest("g[data-cod]");
  if (!g) { ficha.hidden = true; esconderRealce(); return; }
  porRealce(g);
  mostrarFicha(g);
});
folha.addEventListener("mousemove", e => {
  if (medindo || !ficha.hidden) return;
  const g = e.target.closest("g[data-cod]");
  if (g) porRealce(g); else esconderRealce();
});

// ------------------------------------------------------------- minimapa
function atualizarMini() {
  const r = stage.getBoundingClientRect();
  const k = mini.clientWidth / nat.w;
  const alt = nat.h * k;
  mini.style.height = alt + "px";
  const x = (-tx / escala) * k, y = (-ty / escala) * k;
  const w = (r.width / escala) * k, h = (r.height / escala) * k;
  miniJanela.style.left = Math.max(0, x) + "px";
  miniJanela.style.top = Math.max(0, y) + "px";
  miniJanela.style.width = Math.min(w, mini.clientWidth) + "px";
  miniJanela.style.height = Math.min(h, alt) + "px";
}
mini.addEventListener("click", e => {
  const r = mini.getBoundingClientRect();
  centrarEm((e.clientX - r.left) / r.width * nat.w,
            (e.clientY - r.top) / r.height * nat.h);
});

// -------------------------------------------------- escala grafica (MVP-3)
// A barra existe porque no modo sem moldura o carimbo — que declara a escala —
// sai da tela. E porque "1:50" so vale no papel impresso: na tela, quem diz o
// tamanho e o zoom.
const REDONDOS = [0.5, 1, 2, 5, 10, 20, 50, 100];
function atualizarEscalaGrafica() {
  if (!denom) { escalag.hidden = true; return; }
  escalag.hidden = false;
  let m = REDONDOS[0], px = 0;
  for (const cand of REDONDOS) {
    const p = cand * 1000 / denom * escala;
    if (p > 170) break;
    m = cand; px = p;
  }
  px = m * 1000 / denom * escala;
  document.getElementById("escalagBarra").style.width = Math.max(px, 12) + "px";
  document.getElementById("escalagTxt").textContent =
    `0 ${(m / 2).toString().replace(".", ",")} ${m} m  ·  1:${denom}`;
}

// ------------------------------------------------------------ medir (MVP-4)
function limparRegua() {
  if (capaRegua) capaRegua.innerHTML = "";
  pontoA = null;
}
document.getElementById("medir").onclick = e => {
  medindo = !medindo;
  e.currentTarget.setAttribute("aria-pressed", medindo + "");
  stage.classList.toggle("medindo", medindo);
  if (!medindo) limparRegua();
};
stage.addEventListener("click", e => {
  if (!medindo || !svg2d || !denom) return;
  const p = papel(e);
  if (!pontoA) { limparRegua(); pontoA = p; marcarPonto(p); return; }
  const mm = Math.hypot(p.x - pontoA.x, p.y - pontoA.y) * denom;
  const l = NS("line");
  l.setAttribute("class", "regua");
  l.setAttribute("x1", pontoA.x); l.setAttribute("y1", pontoA.y);
  l.setAttribute("x2", p.x); l.setAttribute("y2", p.y);
  capaRegua.appendChild(l);
  const t = NS("text");
  t.setAttribute("class", "reguatxt");
  t.setAttribute("x", (pontoA.x + p.x) / 2);
  t.setAttribute("y", (pontoA.y + p.y) / 2 - 1.5);
  t.setAttribute("text-anchor", "middle");
  t.setAttribute("font-size", "2.6");
  t.textContent = mm >= 1000 ? (mm / 1000).toFixed(2).replace(".", ",") + " m"
                             : Math.round(mm) + " mm";
  capaRegua.appendChild(t);
  marcarPonto(p);
  pontoA = null;
});
function marcarPonto(p) {
  const c = NS("circle");
  c.setAttribute("class", "regua");
  c.setAttribute("cx", p.x); c.setAttribute("cy", p.y); c.setAttribute("r", 0.9);
  capaRegua.appendChild(c);
}

// -------------------------------------------------------------- busca
let achados = [], achadoAtual = -1;
const buscaInp = document.getElementById("busca"),
      buscaConta = document.getElementById("buscaConta");
function buscar(termo) {
  achados = []; achadoAtual = -1;
  if (!svg2d || termo.trim().length < 2) {
    buscaConta.textContent = ""; esconderRealce(); return;
  }
  const t = termo.trim().toLowerCase();
  svg2d.querySelectorAll("text").forEach(el => {
    if ((el.textContent || "").toLowerCase().includes(t)) achados.push(el);
  });
  svg2d.querySelectorAll("g[data-cod]").forEach(g => {
    const alvo = `${g.dataset.cod} ${g.dataset.rot || ""} ${g.dataset.desc || ""}`;
    if (alvo.toLowerCase().includes(t) && !achados.includes(g)) achados.push(g);
  });
  buscaConta.textContent = achados.length
    ? `${achados.length} ocorrência${achados.length > 1 ? "s" : ""}` : "nada";
  if (achados.length) proximoAchado();
}
function proximoAchado() {
  if (!achados.length) return;
  achadoAtual = (achadoAtual + 1) % achados.length;
  const el = achados[achadoAtual];
  const bb = caixaDoGrupo(el);
  if (bb) {
    porRealce(el, "achado");
    if (escala / base < 3) zoomPara(base * 3);
    centrarEm(bb.x + bb.width / 2, bb.y + bb.height / 2);
  }
  buscaConta.textContent = `${achadoAtual + 1}/${achados.length}`;
}
buscaInp.addEventListener("input", e => buscar(e.target.value));
buscaInp.addEventListener("keydown", e => {
  if (e.key === "Enter") { e.preventDefault(); proximoAchado(); }
  if (e.key === "Escape") { buscaInp.value = ""; buscar(""); }
});
'''
