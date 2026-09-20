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
  // R60 — luminarias (da luminotecnica, os mesmos pontos da PR-16) e rotulos
  // de ambiente entram desligados: sao leituras, nao volumetria.
  ["luz", "Luminárias", false], ["rotulos", "Rótulos", false],
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
  // R60 — ceu em gradiente (canvas), nao cor chapada: o horizonte da a
  // escala e a direcao do sol se le no proprio fundo
  cena.background = (() => {
    const c = document.createElement("canvas"); c.width = 2; c.height = 256;
    const g = c.getContext("2d"), gr = g.createLinearGradient(0, 0, 0, 256);
    if (escuro) { gr.addColorStop(0, "#0b1016"); gr.addColorStop(1, "#1c232a"); }
    else { gr.addColorStop(0, "#9fc3e6"); gr.addColorStop(0.55, "#dbe8f3"); gr.addColorStop(1, "#eef1f2"); }
    g.fillStyle = gr; g.fillRect(0, 0, 2, 256);
    const tx = new THREE.CanvasTexture(c); tx.magFilter = THREE.LinearFilter; return tx;
  })();

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
  function material(cor, transp, tipo) {
    const k = cor + (transp ? "t" : "") + (tipo === "luz" ? "l" : "");
    if (!mats[k]) {
      if (tipo === "luz") {
        // R60 — a luminaria emite: cor propria, sem depender do sol
        mats[k] = new THREE.MeshBasicMaterial({color: new THREE.Color(cor),
                                               clippingPlanes: [plano]});
      } else if (tipo === "vao" || tipo === "piscina") {
        // R60 — vidro e agua com brilho especular, nao caixa fosca
        mats[k] = new THREE.MeshPhongMaterial({
          color: new THREE.Color(cor), clippingPlanes: [plano],
          transparent: true, opacity: tipo === "vao" ? 0.42 : 0.6,
          shininess: 90, specular: new THREE.Color(0xffffff),
          side: THREE.DoubleSide, depthWrite: false});
      } else {
        mats[k] = new THREE.MeshLambertMaterial({
          color: new THREE.Color(cor), clippingPlanes: [plano],
          transparent: !!transp, opacity: transp ? 0.34 : 1,
          side: THREE.DoubleSide});
      }
    }
    return mats[k];
  }
  // R60 — ARESTAS. Um modelo de arquitetura sem aresta e uma massa de cor;
  // com aresta, cada volume se le. So nas caixas alinhadas da edificacao —
  // nao nas 800 pecas da estrutura, onde a aresta viraria ruido.
  const arestaGeo = new THREE.EdgesGeometry(caixa);
  const arestaMat = new THREE.LineBasicMaterial({color: escuro ? 0x8a949c : 0x4a4f55,
                                                 transparent: true, opacity: 0.55,
                                                 clippingPlanes: [plano]});
  const COM_ARESTA = new Set(["parede", "laje", "cobertura", "platibanda", "muro",
                              "pilar", "mob", "escada", "tecnico", "deck", "brise"]);
  const solidos = [];
  function add(grupo, b) {
    const transp = b.t === "vao" || b.t === "piscina";
    const m = new THREE.Mesh(caixa, material(b.c, transp, b.t));
    if (b.de) {
      // Peca definida pelas DUAS PONTAS — a fita em X do contraventamento.
      // O dado diz onde ela comeca e onde termina; a rotacao sai daqui, de um
      // lugar so. Deduzir angulo e eixo no exportador E no navegador seria
      // manter duas rotacoes que divergem no primeiro sinal trocado.
      const a = new THREE.Vector3(...b.de), z = new THREE.Vector3(...b.ate);
      const d = new THREE.Vector3().subVectors(z, a);
      m.position.copy(a).addScaledVector(d, 0.5);
      m.scale.set(d.length(), b.esp || 38, b.esp || 38);
      m.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0),
                                      d.clone().normalize());
      m.castShadow = true; m.receiveShadow = true;
      m.userData = b;
      grupos[grupo].add(m); solidos.push(m);
      return;
    }
    m.position.set(b.p[0], b.p[1], b.p[2]);
    m.scale.set(Math.max(b.s[0], 1), Math.max(b.s[1], 1), Math.max(b.s[2], 1));
    m.castShadow = !transp && b.t !== "luz"; m.receiveShadow = b.t !== "luz";
    m.userData = b;
    if (COM_ARESTA.has(b.t)) m.add(new THREE.LineSegments(arestaGeo, arestaMat));
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
  (dados.luz || []).forEach(b => add("luz", b));

  // R60 — ROTULOS: o nome de cada ambiente como sprite no centro dele, a
  // altura do olho. Sprite olha sempre para a camera; e o unico texto que
  // sobrevive a qualquer angulo. Entra desligado.
  function sprite(txt, sub) {
    const c = document.createElement("canvas"); c.width = 512; c.height = 160;
    const g = c.getContext("2d");
    g.fillStyle = escuro ? "rgba(20,26,30,0.82)" : "rgba(255,255,255,0.86)";
    g.strokeStyle = escuro ? "#9fb3a8" : "#0a6a4a"; g.lineWidth = 3;
    g.beginPath(); g.roundRect(6, 6, 500, 148, 18); g.fill(); g.stroke();
    g.fillStyle = escuro ? "#e6ebe8" : "#1a1f1c"; g.textAlign = "center";
    g.font = "bold 44px system-ui, sans-serif"; g.fillText(txt, 256, 70);
    g.font = "30px ui-monospace, monospace"; g.fillStyle = escuro ? "#9fb3a8" : "#0a6a4a";
    g.fillText(sub, 256, 122);
    const tx = new THREE.CanvasTexture(c);
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({map: tx, depthTest: false,
                                                          transparent: true}));
    sp.scale.set(3200, 1000, 1);
    return sp;
  }
  (dados.ambientes || []).forEach(a => {
    const sp = sprite(a.nome, `${a.cod} · ${a.area.toFixed(2).replace(".", ",")} m²`);
    sp.position.set(a.p[0], a.p[1], a.p[2] + 300);
    grupos.rotulos.add(sp);
  });

  // R60 — TRAJETO DO SOL: o arco do dia para a epoca escolhida, com o sol
  // marcado na hora do slider. Manaus esta a 3 graus do equador: no
  // equinocio o sol passa a 87 graus, e o arco quase encosta no zenite —
  // e por isso que beiral nao sombreia e brise vertical sim (PR-19).
  const solTrajeto = new THREE.Group(); cena.add(solTrajeto);
  const solMarca = new THREE.Mesh(new THREE.SphereGeometry(500, 16, 12),
                                  new THREE.MeshBasicMaterial({color: 0xffc14d}));
  cena.add(solMarca);
  function desenharTrajeto(decl) {
    while (solTrajeto.children.length) solTrajeto.remove(solTrajeto.children[0]);
    const pts = [], raio = 30000, c = new THREE.Vector3(10000, 20000, 0);
    for (let h = 5.5; h <= 18.5; h += 0.25) {
      const s = solVetor(decl, h);
      if (s.alt < -2) continue;
      pts.push(new THREE.Vector3(c.x + s.v.x * raio, c.y + s.v.y * raio, Math.max(0, s.v.z * raio)));
    }
    if (pts.length > 1) {
      solTrajeto.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineDashedMaterial({color: 0xe0a02a, dashSize: 600, gapSize: 400})));
      solTrajeto.children[0].computeLineDistances();
      [6, 9, 12, 15, 18].forEach(h => {
        const s = solVetor(decl, h); if (s.alt < 0) return;
        const m = new THREE.Mesh(new THREE.SphereGeometry(180, 8, 6),
                                 new THREE.MeshBasicMaterial({color: 0xe0a02a}));
        m.position.set(c.x + s.v.x * raio, c.y + s.v.y * raio, Math.max(0, s.v.z * raio));
        solTrajeto.add(m);
      });
    }
  }
  R = {cena, cam, ren, grupos, solidos, sol, plano, el, solTrajeto, solMarca,
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
    const hit = ray.intersectObjects(R.solidos.filter(o => o.parent.visible && o.userData.t !== "luz"), false)[0];
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
    // data-camada: sem identificador, a camada so e alcancavel pelo texto do
    // rotulo ou pela ordem na lista — as duas coisas que mudam
    lab.innerHTML = `<input type="checkbox" data-camada="${id}" ` +
                    `${on ? "checked" : ""}>${rot}`;
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
    desenharTrajeto(decl);
    solMarca.position.set(10000 + s.v.x * 30000, 20000 + s.v.y * 30000,
                          Math.max(0, s.v.z * 30000));
    solMarca.visible = s.alt > 0;
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
  if (typeof gravarRota === "function") gravarRota();
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
