"""JavaScript do visualizador: motor 3D e abas. O motor 2D esta em viewer_parte4.py."""

JS_3D = r'''
// =====================================================================
// 3D — motor proprio sobre three.js
// =====================================================================
let R = null;           // {scene, cam, renderer, grupos, alvo, dist, azim, elev}
let M3 = null;          // dados do modelo

const CAMADAS = [
  ["terreo", "Térreo", true], ["superior", "Superior", true],
  ["lajes", "Lajes", true], ["platibandas", "Platibanda", true],
  ["cobertura", "Cobertura", true], ["externo", "Externo", true],
  ["tecnico", "Técnico", true], ["mob", "Mobiliário", true],
  ["escada", "Escada", true],
  // A estrutura entra DESLIGADA: ela e a mesma parede vista por dentro, e as
  // duas ligadas ao mesmo tempo dao uma sopa. Ligar a estrutura e desligar o
  // terreo e o superior e o gesto que mostra o esqueleto.
  ["lsf", "Estrutura LSF", false],
];

function solVetor(decl, hora) {
  const lat = -3.10 * Math.PI / 180, d = decl * Math.PI / 180;
  const H = (hora - 12) * 15 * Math.PI / 180;
  const alt = Math.asin(Math.sin(lat) * Math.sin(d) +
                        Math.cos(lat) * Math.cos(d) * Math.cos(H));
  let az = Math.atan2(-Math.cos(d) * Math.sin(H),
                      Math.sin(d) * Math.cos(lat) -
                      Math.cos(d) * Math.sin(lat) * Math.cos(H));
  // modelo: +X = norte, -Y = leste, +Z = cima
  return {
    v: new THREE.Vector3(Math.cos(az) * Math.cos(alt),
                         -Math.sin(az) * Math.cos(alt),
                         Math.sin(alt)),
    alt: alt * 180 / Math.PI, az: (az * 180 / Math.PI + 360) % 360
  };
}

function montar3D(dados) {
  M3 = dados;
  const el = document.getElementById("stage3d");
  const ren = new THREE.WebGLRenderer({antialias: true, alpha: false});
  ren.setPixelRatio(Math.min(devicePixelRatio, 2));
  ren.shadowMap.enabled = true;
  ren.shadowMap.type = THREE.PCFSoftShadowMap;
  ren.localClippingEnabled = true;
  // Sem tone mapping de proposito: o MeshLambertMaterial de r128 nao converte
  // a cor de sRGB para linear, entao qualquer compressao de alta luz lava a
  // cena. O controle e feito na soma das intensidades, abaixo, de modo que
  // ceu + sol nao passem de 1,0 numa face voltada para cima.
  el.appendChild(ren.domElement);

  const cena = new THREE.Scene();
  const escuro = matchMedia("(prefers-color-scheme: dark)").matches &&
                 document.documentElement.dataset.theme !== "light";
  cena.background = new THREE.Color(escuro ? 0x0e1113 : 0xdfe3e7);

  const cam = new THREE.PerspectiveCamera(38, 1, 100, 200000);
  const hemi = new THREE.HemisphereLight(0xdfeaf2, 0x6b6257, escuro ? 0.34 : 0.45);
  hemi.position.set(0, 0, 1);
  cena.add(hemi);
  const sol = new THREE.DirectionalLight(0xfff3e0, 0.5);
  sol.castShadow = true;
  sol.shadow.mapSize.set(2048, 2048);
  // acne de sombra: sem bias as lajes ganhavam aneis concentricos, porque a
  // superficie se auto-sombreava na precisao do mapa. O normalBias esta em
  // milimetros, como o resto do modelo.
  sol.shadow.bias = -0.0004;
  sol.shadow.normalBias = 80;
  const S = 26000;
  Object.assign(sol.shadow.camera, {left: -S, right: S, top: S, bottom: -S,
                                    near: 1000, far: 90000});
  sol.shadow.camera.updateProjectionMatrix();
  cena.add(sol, sol.target);

  // terreno
  const lote = dados.meta.lote;
  const chao = new THREE.Mesh(
    new THREE.PlaneGeometry(lote[0] * 2.4, lote[1] * 1.5),
    new THREE.MeshLambertMaterial({color: escuro ? 0x1b2420 : 0xc9d3c6}));
  chao.position.set(lote[0] / 2, lote[1] / 2, -200);
  chao.receiveShadow = true;
  cena.add(chao);
  const borda = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(lote[0], lote[1], 10)),
    new THREE.LineBasicMaterial({color: escuro ? 0x3a4a42 : 0x9aa89a}));
  borda.position.set(lote[0] / 2, lote[1] / 2, -190);
  cena.add(borda);

  const plano = new THREE.Plane(new THREE.Vector3(0, 0, -1), 99999);
  const grupos = {};
  CAMADAS.forEach(([id]) => { grupos[id] = new THREE.Group(); cena.add(grupos[id]); });

  const caixa = new THREE.BoxGeometry(1, 1, 1);
  const mats = {};
  function material(cor, transp) {
    const k = cor + (transp ? "t" : "");
    if (!mats[k]) {
      mats[k] = new THREE.MeshLambertMaterial({
        color: new THREE.Color(cor), clippingPlanes: [plano],
        transparent: !!transp, opacity: transp ? 0.34 : 1,
        side: THREE.DoubleSide});
    }
    return mats[k];
  }
  const solidos = [];
  function add(grupo, b) {
    const transp = b.t === "vao" || b.t === "piscina";
    const m = new THREE.Mesh(caixa, material(b.c, transp));
    m.position.set(b.p[0], b.p[1], b.p[2]);
    m.scale.set(Math.max(b.s[0], 1), Math.max(b.s[1], 1), Math.max(b.s[2], 1));
    m.castShadow = !transp; m.receiveShadow = true;
    m.userData = b;
    grupos[grupo].add(m);
    solidos.push(m);
  }
  dados.terreo.forEach(b => add("terreo", b));
  dados.superior.forEach(b => add("superior", b));
  dados.lajes.forEach(b => add(b.t === "cobertura" ? "cobertura" : "lajes", b));
  dados.platibandas.forEach(b => add("platibandas", b));
  dados.externo.forEach(b => add(b.t === "tecnico" ? "tecnico" : "externo", b));
  dados.mob.forEach(b => add("mob", b));
  dados.escada.forEach(b => add("escada", b));
  (dados.lsf || []).forEach(b => add("lsf", b));

  R = {cena, cam, ren, grupos, solidos, sol, plano, el,
       alvo: new THREE.Vector3(10000, 20000, 1500),
       dist: 34000, azim: -38, elev: 24};

  function posicionar() {
    const a = R.azim * Math.PI / 180, e = R.elev * Math.PI / 180;
    cam.position.set(R.alvo.x + R.dist * Math.cos(e) * Math.cos(a),
                     R.alvo.y + R.dist * Math.cos(e) * Math.sin(a),
                     R.alvo.z + R.dist * Math.sin(e));
    cam.up.set(0, 0, 1);
    cam.lookAt(R.alvo);
  }
  R.posicionar = posicionar;

  function redimensionar() {
    const r = el.getBoundingClientRect();
    ren.setSize(r.width, r.height, false);
    cam.aspect = r.width / Math.max(r.height, 1);
    cam.updateProjectionMatrix();
  }
  R.redimensionar = redimensionar;
  addEventListener("resize", () => { if (R) { redimensionar(); render(); } });

  function render() { posicionar(); ren.render(cena, cam); }
  R.render = render;

  // ---- orbita, pan e dolly
  let ar = null;
  el.addEventListener("pointerdown", ev => {
    el.setPointerCapture(ev.pointerId);
    ar = {x: ev.clientX, y: ev.clientY, az: R.azim, el: R.elev,
          alvo: R.alvo.clone(), pan: ev.shiftKey || ev.button === 1};
    el.classList.add("dragging");
  });
  el.addEventListener("pointermove", ev => {
    if (!ar) return;
    const dx = ev.clientX - ar.x, dy = ev.clientY - ar.y;
    if (ar.pan) {
      const k = R.dist / 900;
      const a = R.azim * Math.PI / 180;
      R.alvo.copy(ar.alvo)
        .add(new THREE.Vector3(Math.sin(a) * dx * k, -Math.cos(a) * dx * k, dy * k));
    } else {
      R.azim = ar.az - dx * 0.32;
      R.elev = Math.min(88, Math.max(-8, ar.el + dy * 0.28));
    }
    render();
  });
  ["pointerup", "pointercancel"].forEach(e2 => el.addEventListener(e2, () => {
    ar = null; el.classList.remove("dragging");
  }));
  el.addEventListener("wheel", ev => {
    ev.preventDefault();
    R.dist = Math.min(90000, Math.max(3000, R.dist * (ev.deltaY > 0 ? 1.12 : 0.89)));
    render();
  }, {passive: false});

  // ---- clique revela o ambiente
  const ray = new THREE.Raycaster();
  el.addEventListener("click", ev => {
    const r = el.getBoundingClientRect();
    const m = new THREE.Vector2(((ev.clientX - r.left) / r.width) * 2 - 1,
                                -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(m, cam);
    const hit = ray.intersectObjects(R.solidos.filter(o => o.parent.visible), false)[0];
    if (!hit) return;
    const p = hit.point;
    const amb = M3.ambientes.filter(a => {
      const dz = Math.abs(a.p[2] - p.z);
      return dz < 2200;
    }).map(a => ({a, d: Math.hypot(a.p[0] - p.x, a.p[1] - p.y)}))
      .sort((u, v) => u.d - v.d)[0];
    const u = hit.object.userData;
    const cod = u.amb;
    const leitura = document.getElementById("leitura3d");
    if (u.t !== "lsf" && amb && amb.d < 4500) {
      leitura.innerHTML = `<b>${amb.a.nome}</b><span>${amb.a.cod} · ` +
        `${amb.a.area.toFixed(2).replace(".", ",")} m² · pavimento ` +
        `${amb.a.pav === "S" ? "superior" : "térreo"}</span>`;
    } else if (u.t === "lsf") {
      // clicar numa peca da estrutura le a PECA, nao o ambiente: e a mesma
      // identidade que vai para a perfiladeira e para o parafuso
      leitura.innerHTML = `<b>${u.cod}</b><span>${u.fam} · ${u.perf}<br>` +
        `${u.comp} mm · painel ${u.painel} · pavimento ` +
        `${u.pav === "S" ? "superior" : "térreo"}</span>`;
    } else if (cod) {
      leitura.innerHTML = `<b>${cod}</b><span>${hit.object.userData.t}</span>`;
    }
  });

  // ---- camadas
  const cx = document.getElementById("camadas");
  CAMADAS.forEach(([id, rot, on]) => {
    const lab = document.createElement("label");
    lab.innerHTML = `<input type="checkbox" ${on ? "checked" : ""}>${rot}`;
    lab.querySelector("input").addEventListener("change", e2 => {
      grupos[id].visible = e2.target.checked;
      render();
    });
    cx.appendChild(lab);
  });

  // ---- sol e corte
  function atualizarSol() {
    const decl = parseFloat(document.getElementById("solEpoca").value);
    const hora = parseFloat(document.getElementById("solHora").value);
    const s = solVetor(decl, hora);
    const d = 46000;
    sol.position.set(R.alvo.x + s.v.x * d, R.alvo.y + s.v.y * d,
                     Math.max(2000, s.v.z * d));
    sol.target.position.copy(R.alvo);
    sol.target.updateMatrixWorld();
    sol.intensity = s.alt > 0 ? 0.12 + 0.45 * Math.sin(s.alt * Math.PI / 180) : 0.04;
    hemi.intensity = s.alt > 0 ? (escuro ? 0.34 : 0.45) : 0.26;
    const hh = Math.floor(hora), mm = Math.round((hora - hh) * 60);
    document.getElementById("solVal").textContent =
      `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")} · ` +
      `${s.alt.toFixed(0)}°`;
    render();
  }
  ["solEpoca", "solHora"].forEach(id =>
    document.getElementById(id).addEventListener("input", atualizarSol));
  document.getElementById("corte").addEventListener("input", e2 => {
    const v = parseFloat(e2.target.value);
    plano.constant = v >= 6400 ? 99999 : v;
    document.getElementById("corteVal").textContent =
      v >= 6400 ? "sem corte" : `+${(v / 1000).toFixed(2).replace(".", ",")} m`;
    render();
  });

  redimensionar();
  atualizarSol();
  aplicarCena(M3.cenas[0]);
  document.getElementById("leitura3d").innerHTML =
    `<b>${M3.cenas[0].nome}</b><span>${M3.cenas[0].nota}</span>`;
}

function aplicarCena(c) {
  if (!R) return;
  R.alvo.set(c.alvo[0], c.alvo[1], c.alvo[2]);
  R.dist = c.dist; R.azim = c.azim; R.elev = c.elev;
  const mostra = new Set(c.mostra);
  CAMADAS.forEach(([id], i) => {
    const on = mostra.has(id) || (id === "lajes" && mostra.has("terreo"))
               || (id === "platibandas" && mostra.has("cobertura"))
               || (id === "tecnico" && mostra.has("externo"));
    R.grupos[id].visible = on;
    const inp = document.querySelectorAll("#camadas input")[i];
    if (inp) inp.checked = on;
  });
  // a cena pode trazer o proprio corte horizontal; sem isso a camera de uma
  // vista rasante acaba dentro de uma parede
  const corte = document.getElementById("corte");
  corte.value = c.corte ? c.corte : corte.max;
  corte.dispatchEvent(new Event("input"));
  if (c.hora) {
    const hr = document.getElementById("solHora");
    hr.value = c.hora;
    hr.dispatchEvent(new Event("input"));
  }
  document.getElementById("leitura3d").innerHTML =
    `<b>${c.nome}</b><span>${c.nota}</span>`;
  R.render();
}

// =====================================================================
// abas
// =====================================================================
let carregou3d = false;

// De quem e cada elemento. A aba deixou de ser um booleano quando virou tres:
// manter "e2 = qual === 3d" com uma terceira aba seria escrever o bug antes do
// codigo. A tabela diz o dono; quem nao e dono da aba corrente fica hidden.
const DONO = {
  "2d":  ["stage", "barra2d", "barra2", "rail2d", "notas2d", "dica2d"],
  "3d":  ["stage3d", "rail3d", "notas3d", "dica3d"],
  "eng": ["stageEng", "railEng", "dicaEng"],
};
function modo(qual) {
  const e2 = qual === "3d";
  Object.keys(DONO).forEach(k => DONO[k].forEach(id => {
    const n = document.getElementById(id);
    if (n) n.hidden = (k !== qual);
  }));
  document.querySelectorAll(".modos button").forEach(b =>
    b.setAttribute("aria-selected", (b.dataset.modo === qual) + ""));
  if (qual === "eng") { abrirEng(); return; }
  if (qual === "2d") { if (svg2d) ajustar(semMoldura ? caixaDesenho() : null); return; }
  if (!carregou3d) {
    carregou3d = true;
    fetch("modelo3d.json").then(r => r.json()).then(d => {
      montar3D(d);
      const ul = document.getElementById("cenas");
      d.cenas.forEach((c, i) => {
        const li = document.createElement("li");
        const b = document.createElement("button");
        b.type = "button";
        b.innerHTML = `${c.nome}<span class="sub">${c.id}</span>`;
        b.addEventListener("click", () => {
          document.querySelectorAll("#cenas button").forEach(x =>
            x.setAttribute("aria-current", "false"));
          b.setAttribute("aria-current", "true");
          aplicarCena(c);
        });
        if (i === 0) b.setAttribute("aria-current", "true");
        li.appendChild(b); ul.appendChild(li);
      });
    }).catch(() => {
      document.getElementById("leitura3d").innerHTML =
        "<b>Não foi possível carregar o modelo 3D</b><span>modelo3d.json</span>";
    });
  } else if (R) {
    R.redimensionar(); R.render();
  }
}
document.querySelectorAll(".modos button").forEach(b =>
  b.addEventListener("click", () => modo(b.dataset.modo)));

addEventListener("keydown", e2 => {
  if (e2.target.tagName === "INPUT" || e2.target.tagName === "SELECT") return;
  if (!document.getElementById("stage").hidden) {
    if (e2.key === "ArrowLeft") mostrar(idxPrancha - 1);
    if (e2.key === "ArrowRight") mostrar(idxPrancha + 1);
    if (e2.key === "+" || e2.key === "=") passo(1);
    if (e2.key === "-") passo(-1);
    if (e2.key === "0") ajustar();
  }
});
addEventListener("resize", () => { if (!document.getElementById("stage").hidden) ajustar(); });
'''
