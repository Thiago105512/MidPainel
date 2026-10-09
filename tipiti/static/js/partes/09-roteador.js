// ------------------------------------------------------------- roteador

function pagina404(main) {
  document.title = "Página não encontrada | Tipiti";
  trocar(main, h("div", { class: "vazio" }, h("div", { class: "ico" }, "🧭"),
    h("h1", {}, "Página não encontrada"), h("p", {}, "O endereço pode ter mudado ou o produto saiu do catálogo."),
    h("a", { class: "botao", href: "/" }, "Ir para o início")));
}

const ROTAS = [
  [/^\/$/, paginaInicial],
  [/^\/categoria\/([a-z0-9-]+)\/?$/, paginaCategoria],
  [/^\/produto\/([a-z0-9-]+)\/?$/, paginaProduto],
  [/^\/busca\/?$/, paginaBusca],
  [/^\/carrinho\/?$/, paginaCarrinho],
  [/^\/checkout\/?$/, paginaCheckout],
  [/^\/pedido\/([A-Za-z0-9-]+)\/?$/, paginaPedido],
  [/^\/entregas\/?$/, paginaEntregas],
  [/^\/sobre\/?$/, paginaSobre],
  [/^\/trocas\/?$/, paginaTrocas],
  [/^\/admin\/?$/, paginaAdmin],
  [/^\/admin\/produto\/([a-z0-9-]+)\/?$/, paginaEditorProduto],
];

/**
 * `navegacao`: mudou de página (foca o h1 e mostra esqueleto se demorar);
 * `rolar`: volta ao topo depois de desenhar. Sem opções, só atualiza a página atual.
 */
async function rotear({ navegacao = false, rolar = false, esqueleto = navegacao } = {}) {
  const geracao = ++geracaoNavegacao;
  const atual = () => geracao === geracaoNavegacao;
  const main = $("#conteudo");
  const caminho = location.pathname;
  fecharFolha();
  pararRelogios();  // contagens da página anterior
  soltarBarraCompra();
  marcarVisita();
  if (PAGINAS_SEM_PROVA.test(caminho)) esconderProva();
  const corpo = document.body.classList;
  corpo.toggle("em-admin", caminho.startsWith("/admin"));
  corpo.toggle("foco-compra", /^\/(carrinho|checkout)\/?$/.test(caminho));
  corpo.toggle("sem-whatsapp-flutuante", /^\/(checkout\/?$|pedido\/)/.test(caminho));
  corpo.toggle("pagina-produto", caminho.startsWith("/produto/"));
  document.querySelectorAll("#menu-categorias a").forEach((a) => {
    const ativo = a.getAttribute("href") === caminho;
    a.classList.toggle("ativo", ativo);
    if (ativo) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  main.setAttribute("aria-busy", "true");
  const timer = esqueleto ? setTimeout(() => {
    if (!atual() || geracaoRenderizada === geracao) return;
    main.replaceChildren(...esqueletoPagina());
    if (rolar) window.scrollTo(0, 0);
  }, 150) : null;

  const rota = ROTAS.map(([padrao, fn]) => [caminho.match(padrao), fn]).find(([m]) => m);
  try {
    if (rota) await rota[1](main, ...rota[0].slice(1));
    else pagina404(main);
  } catch (err) {
    if (!atual()) return;  // erro de uma página que já foi trocada: ignora
    if (err.status === 404) pagina404(main);
    else trocar(main, h("div", { class: "vazio" }, h("div", { class: "ico" }, "⚠️"), h("h1", { class: "titulo-erro" }, "Algo deu errado"), h("p", {}, err.message),
      h("button", { class: "botao", type: "button", onclick: () => rotear({ navegacao: true }) }, "Tentar novamente")));
  }
  if (!atual()) return;
  clearTimeout(timer);
  main.removeAttribute("aria-busy");
  if (rolar) window.scrollTo(0, 0);
  if (navegacao && !main.contains(document.activeElement)) {
    const titulo = main.querySelector("h1");
    if (titulo) {
      titulo.tabIndex = -1;
      titulo.focus({ preventScroll: true });
    }
  }
}

function navegar(url, substituir = false) {
  if (substituir) history.replaceState(null, "", url);
  else history.pushState(null, "", url);
  rotear({ navegacao: true, rolar: !substituir });
}

document.addEventListener("click", (e) => {
  const a = e.target.closest("a");
  if (!a || a.target || a.hasAttribute("download") || e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
  const url = new URL(a.href, location.href);
  if (url.origin !== location.origin || url.pathname.startsWith("/static/") || url.pathname.startsWith("/api/")) return;
  if (url.hash && url.pathname === location.pathname) return;
  e.preventDefault();
  navegar(url.pathname + url.search);
});

window.addEventListener("popstate", () => rotear({ navegacao: true }));

/** Dados embutidos pelo servidor no index.html (evita duas requisições na primeira visita). */
function lerDadosIniciais() {
  const el = document.getElementById("dados-iniciais");
  if (!el) return null;
  try {
    const d = JSON.parse(el.textContent);
    if (d && typeof d.loja === "object" && d.loja && Array.isArray(d.categorias)) return d;
  } catch (_) { /* ainda é o marcador __DADOS_INICIAIS__ ou veio inválido */ }
  return null;
}

async function iniciar() {
  $("#ano").textContent = new Date().getFullYear();
  estado.carrinho = lerArmazenado(CHAVE_CARRINHO, []).filter((i) => i && typeof i.slug === "string" && i.quantidade > 0)
    .map((i) => ({ slug: i.slug, variacao: Number.isInteger(i.variacao) ? i.variacao : null, quantidade: i.quantidade }));
  salvarCarrinho();
  $(".busca").addEventListener("submit", (e) => {
    e.preventDefault();
    const campoBusca = $("#campo-busca");
    campoBusca.blur();  // fecha o teclado do celular
    navegar(`/busca?q=${encodeURIComponent(campoBusca.value.trim())}`);
  });
  const iniciais = lerDadosIniciais();
  if (iniciais) {
    estado.loja = iniciais.loja;
    estado.categorias = iniciais.categorias;
  } else {
    try {
      [estado.loja, estado.categorias] = await Promise.all([api("/api/loja"), api("/api/categorias")]);
    } catch (err) {
      trocar($("#conteudo"), h("div", { class: "vazio" }, h("p", {}, "Não foi possível carregar a loja. Tente novamente em instantes."),
        h("button", { class: "botao", type: "button", onclick: () => location.reload() }, "Tentar novamente")));
      return;
    }
  }
  trocar($("#menu-categorias"), ...estado.categorias.map((c) => h("a", { href: `/categoria/${c.slug}` }, `${c.icone} ${c.nome}`)),
    h("a", { href: "/entregas" }, "🚚 Entregas no Norte"));
  atualizarWhatsAppFlutuante();
  marcarVisita(true);
  document.addEventListener("visibilitychange", () => { if (document.hidden) marcarVisita(); });
  rotear({ esqueleto: true });
  iniciarProvaSocial();
}

iniciar();
