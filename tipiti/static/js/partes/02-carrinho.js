// ------------------------------------------------------------- carrinho

function salvarCarrinho() {
  gravar(CHAVE_CARRINHO, estado.carrinho);
  const total = estado.carrinho.reduce((s, i) => s + i.quantidade, 0);
  const contador = $("#contador-carrinho");
  const anterior = Number(contador.textContent) || 0;
  contador.textContent = total;
  $(".botao-carrinho").setAttribute("aria-label", `Carrinho, ${total} ${total === 1 ? "item" : "itens"}`);
  if (total > anterior && !reduzMovimento()) {
    contador.classList.remove("pulsar");
    void contador.offsetWidth;  // reinicia a animação
    contador.classList.add("pulsar");
  }
}

/** Mesma chave que o servidor devolve em cada linha do carrinho. */
const chaveItem = (slug, variacao) => `${slug}:${variacao ?? ""}`;

function adicionarAoCarrinho(slug, quantidade = 1, variacao = null) {
  const item = estado.carrinho.find((i) => chaveItem(i.slug, i.variacao) === chaveItem(slug, variacao));
  if (item) item.quantidade = Math.min(99, item.quantidade + quantidade);
  else estado.carrinho.push({ slug, variacao, quantidade });
  salvarCarrinho();
}

function alterarQuantidade(chave, quantidade) {
  if (quantidade <= 0) estado.carrinho = estado.carrinho.filter((i) => chaveItem(i.slug, i.variacao) !== chave);
  else {
    const item = estado.carrinho.find((i) => chaveItem(i.slug, i.variacao) === chave);
    if (item) item.quantidade = Math.min(99, quantidade);
  }
  salvarCarrinho();
}

const nomeComOpcao = (i) => (i.variacao_nome ? `${i.nome} — ${i.variacao_nome}` : i.nome);

/** Painel inferior depois de adicionar ao carrinho (fica até a pessoa escolher). */
let folhaAberta = null;
function fecharFolha(devolverFoco = false) {
  if (!folhaAberta) return;
  const { el, aoTeclar, anterior } = folhaAberta;
  folhaAberta = null;
  document.removeEventListener("keydown", aoTeclar);
  el.remove();
  if (devolverFoco && anterior && anterior.isConnected) anterior.focus({ preventScroll: true });
}

function mostrarFolhaCarrinho(detalhe) {
  fecharFolha();
  const anterior = document.activeElement;
  const verCarrinho = h("a", { class: "botao", href: "/carrinho" }, "Ver carrinho");
  const el = h("div", { class: "folha-carrinho", role: "dialog", "aria-labelledby": "folha-titulo" },
    h("p", { class: "folha-titulo", id: "folha-titulo" }, "✔ Adicionado ao carrinho"),
    h("p", { class: "folha-detalhe" }, detalhe),
    h("div", { class: "folha-acoes" }, verCarrinho,
      h("button", { class: "botao secundario", type: "button", onclick: () => fecharFolha(true) }, "Continuar comprando")));
  const aoTeclar = (e) => { if (e.key === "Escape") fecharFolha(true); };
  folhaAberta = { el, aoTeclar, anterior };
  document.addEventListener("keydown", aoTeclar);
  document.body.append(el);
  requestAnimationFrame(() => el.classList.add("visivel"));
  verCarrinho.focus({ preventScroll: true });
}
