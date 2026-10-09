// ------------------------------------------------------------- app instalável (PWA): service worker, instalar, offline

const CHAVE_INSTALAR = "tipiti:instalar-visto";
const INTERVALO_INSTALAR_MS = 7 * 24 * 3600 * 1000;
const estadoApp = { pedidoInstalacao: null, registro: null, recarregar: false };

const appInstalado = () => (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) || navigator.standalone === true;
/** iPhone/iPad no Safari (lá não existe o convite automático de instalação). */
const ehIos = () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

/** Faixas fixas no topo (sem internet, versão nova): ficam dentro do cabeçalho, que já é fixo, e não cobrem nada. */
function faixaTopo(id) {
  let el = document.getElementById(id);
  if (!el) {
    el = h("div", { id, class: "faixa-app", role: "status", "aria-live": "polite", hidden: true });
    $(".topo").append(el);
  }
  return el;
}

function atualizarFaixaOffline() {
  const el = faixaTopo("faixa-offline");
  if (navigator.onLine === false) {
    trocar(el, h("span", { "aria-hidden": "true" }, "📡 "), "Você está sem internet — mostrando o que foi salvo.");
    el.hidden = false;
  } else el.hidden = true;
}

function mostrarNovaVersao() {
  const reg = estadoApp.registro;
  if (!reg || !reg.waiting) return;
  const el = faixaTopo("faixa-versao");
  trocar(el, h("span", {}, "✨ Nova versão disponível"),
    h("button", { class: "botao botao-faixa", type: "button", onclick: () => {
      estadoApp.recarregar = true;
      if (reg.waiting) reg.waiting.postMessage({ tipo: "SKIP_WAITING" });
      el.hidden = true;
    } }, "Atualizar"));
  el.hidden = false;
}

function registrarServiceWorker() {
  if (!("serviceWorker" in navigator)) return;
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
  if (location.protocol !== "https:" && !local) return;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (estadoApp.recarregar) { estadoApp.recarregar = false; location.reload(); }
  });
  const registrar = () => navigator.serviceWorker.register("/sw.js").then((reg) => {
    estadoApp.registro = reg;
    if (reg.waiting && navigator.serviceWorker.controller) mostrarNovaVersao();
    reg.addEventListener("updatefound", () => {
      const novo = reg.installing;
      if (!novo) return;
      novo.addEventListener("statechange", () => {
        if (novo.state === "installed" && navigator.serviceWorker.controller) mostrarNovaVersao();
      });
    });
    // quem deixa o app aberto dias seguidos também recebe a versão nova
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) reg.update().catch(() => {});
    });
  }).catch(() => { /* sem service worker: a loja funciona igual, só sem modo offline */ });
  if (document.readyState === "complete") registrar();
  else window.addEventListener("load", registrar, { once: true });
}

// -- instalar

let folhaInstalar = null;
function fecharFolhaInstalar() {
  if (!folhaInstalar) return;
  const { el, aoTeclar, anterior } = folhaInstalar;
  folhaInstalar = null;
  document.removeEventListener("keydown", aoTeclar);
  el.remove();
  if (anterior && anterior.isConnected) anterior.focus({ preventScroll: true });
}

/** Instruções para instalar quando o navegador não oferece o convite (iPhone e outros). */
function mostrarFolhaInstalar() {
  fecharFolhaInstalar();
  fecharFolha();
  const anterior = document.activeElement;
  const fechar = h("button", { class: "botao secundario", type: "button", onclick: fecharFolhaInstalar }, "Entendi");
  const passos = ehIos()
    ? [h("li", {}, "Toque em ", h("b", {}, "Compartilhar"), " ", h("span", { "aria-hidden": "true" }, "(o quadrado com a seta ⬆️)"), " na barra do Safari."),
       h("li", {}, "Escolha ", h("b", {}, "Adicionar à Tela de Início"), "."),
       h("li", {}, "Toque em ", h("b", {}, "Adicionar"), ". O ícone da Tipiti aparece junto dos seus apps.")]
    : [h("li", {}, "Abra o menu do navegador (", h("b", {}, "⋮"), " ou ", h("b", {}, "☰"), ")."),
       h("li", {}, "Toque em ", h("b", {}, "Instalar app"), " ou ", h("b", {}, "Adicionar à tela inicial"), "."),
       h("li", {}, "Confirme. O ícone da Tipiti aparece junto dos seus apps.")];
  const el = h("div", { class: "folha-carrinho folha-instalar", role: "dialog", "aria-modal": "false", "aria-labelledby": "titulo-instalar" },
    h("p", { class: "folha-titulo", id: "titulo-instalar" }, "📲 Instale o app da Tipiti"),
    h("p", { class: "folha-detalhe" }, "Abre direto da tela inicial, mais rápido, e mostra o que já foi carregado mesmo sem internet."),
    h("ol", { class: "passos-instalar" }, passos),
    fechar);
  const aoTeclar = (e) => { if (e.key === "Escape") fecharFolhaInstalar(); };
  folhaInstalar = { el, aoTeclar, anterior };
  document.addEventListener("keydown", aoTeclar);
  document.body.append(el);
  requestAnimationFrame(() => el.classList.add("visivel"));
  fechar.focus({ preventScroll: true });
}

async function abrirInstalacao() {
  if (appInstalado()) { avisar("O app da Tipiti já está instalado neste aparelho ✔"); return; }
  const pedido = estadoApp.pedidoInstalacao;
  if (!pedido) { mostrarFolhaInstalar(); return; }
  estadoApp.pedidoInstalacao = null;  // o convite só pode ser usado uma vez
  esconderFaixaInstalar();
  try {
    pedido.prompt();
    const escolha = await pedido.userChoice;
    if (escolha && escolha.outcome === "accepted") avisar("Pronto! A Tipiti está na sua tela inicial ✔");
  } catch (_) { mostrarFolhaInstalar(); }
}

function esconderFaixaInstalar() {
  const el = document.getElementById("faixa-instalar");
  if (el) el.remove();
}

/** Convite discreto para instalar: no máximo uma vez a cada 7 dias, nunca no checkout nem no painel (CSS). */
function mostrarFaixaInstalar() {
  if (appInstalado() || document.getElementById("faixa-instalar")) return;
  const visto = lerArmazenado(CHAVE_INSTALAR, 0);
  if (typeof visto === "number" && Date.now() - visto < INTERVALO_INSTALAR_MS) return;
  gravar(CHAVE_INSTALAR, Date.now());
  const el = h("div", { id: "faixa-instalar", class: "faixa-instalar", role: "region", "aria-label": "Instalar o app" },
    h("img", { src: "/static/pwa/icone-192.png", alt: "", width: 40, height: 40 }),
    h("p", {}, h("b", {}, "Instale o app da Tipiti"), h("small", {}, "Abre mais rápido e funciona até sem sinal.")),
    h("button", { class: "botao", type: "button", onclick: abrirInstalacao }, ehIos() && !estadoApp.pedidoInstalacao ? "Como instalar" : "Instalar"),
    h("button", { class: "fechar", type: "button", "aria-label": "Fechar convite para instalar o app", onclick: esconderFaixaInstalar }, "×"));
  $("#conteudo").before(el);
}

function iniciarPwa() {
  registrarServiceWorker();
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();  // a loja mostra o próprio convite, sem interromper a compra
    estadoApp.pedidoInstalacao = e;
    mostrarFaixaInstalar();
  });
  window.addEventListener("appinstalled", () => { estadoApp.pedidoInstalacao = null; esconderFaixaInstalar(); });
  // no iPhone não há convite automático: depois de um tempo navegando, a faixa explica como instalar
  if (ehIos() && !appInstalado()) setTimeout(mostrarFaixaInstalar, 20000);
  window.addEventListener("offline", atualizarFaixaOffline);
  window.addEventListener("online", atualizarFaixaOffline);
  atualizarFaixaOffline();
}
