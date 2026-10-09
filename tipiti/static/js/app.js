/* Tipiti — loja virtual. JavaScript puro, sem dependências. */
"use strict";

const estado = { loja: null, categorias: [], carrinho: [] };
const CHAVE_CARRINHO = "tipiti:carrinho";
const CHAVE_ADMIN = "tipiti:admin";
const POR_PAGINA = 24;

// ------------------------------------------------------------- utilidades

const brl = (centavos) => (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const $ = (sel, raiz = document) => raiz.querySelector(sel);
const reduzMovimento = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Geração da navegação atual: cada chamada de rotear() cria uma nova. */
let geracaoNavegacao = 0;
/** Geração em que o <main> recebeu conteúdo pela última vez (para o esqueleto de carregamento). */
let geracaoRenderizada = -1;

/**
 * Chame no início da página, antes de qualquer await. Devolve `ativo()`, que diz se a página
 * ainda é a atual — respostas atrasadas de uma página anterior não podem sobrescrever a nova.
 */
function vigencia() {
  const g = geracaoNavegacao;
  return () => g === geracaoNavegacao;
}

/** Cria elementos sem innerHTML (evita injeção de HTML). */
function h(tag, attrs, ...filhos) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v;
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  for (const f of filhos.flat(Infinity)) {
    if (f === null || f === undefined || f === false) continue;
    el.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return el;
}

/** Ícone SVG simples (traços), sem innerHTML. */
function icone(d, rotulo = null) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  for (const [k, v] of Object.entries({ viewBox: "0 0 24 24", width: 22, height: 22, fill: "none", stroke: "currentColor",
    "stroke-width": 2, "stroke-linecap": "round", "stroke-linejoin": "round", focusable: "false" })) svg.setAttribute(k, v);
  if (rotulo) { svg.setAttribute("role", "img"); svg.setAttribute("aria-label", rotulo); } else svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", d);
  svg.append(path);
  return svg;
}
const ICONE_LIXEIRA = "M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14M10 11v6M14 11v6";

/** replaceChildren que aceita listas aninhadas e ignora vazios. */
function trocar(el, ...filhos) {
  if (el.id === "conteudo") geracaoRenderizada = geracaoNavegacao;
  el.replaceChildren(...filhos.flat(Infinity).filter((f) => f !== null && f !== undefined && f !== false)
    .map((f) => (f instanceof Node ? f : document.createTextNode(String(f)))));
}

async function api(caminho, opcoes = {}) {
  let resp;
  try {
    resp = await fetch(caminho, {
      ...opcoes,
      headers: { "Content-Type": "application/json", ...(opcoes.headers || {}) },
    });
  } catch (_) {
    throw new Error("Sem conexão com a loja. Verifique a internet e tente novamente.");
  }
  let dados = null;
  try { dados = await resp.json(); } catch (_) { /* corpo vazio */ }
  if (!resp.ok) {
    const padrao = resp.status === 429 ? "Muitas tentativas seguidas. Aguarde um pouco e tente de novo." : "Não foi possível completar a ação.";
    const erro = new Error((dados && dados.erro) || padrao);
    erro.status = resp.status;
    erro.campos = dados && dados.campos;
    throw erro;
  }
  return dados;
}

function avisar(texto) {
  const t = $("#aviso-flutuante");
  t.textContent = texto;
  t.classList.add("visivel");
  clearTimeout(avisar.timer);
  avisar.timer = setTimeout(() => t.classList.remove("visivel"), 2600);
}

async function copiarTexto(texto) {
  try {
    await navigator.clipboard.writeText(texto);
    return true;
  } catch (_) {
    const area = h("textarea", { readonly: true, class: "sr", "aria-hidden": "true" });
    area.value = texto;
    document.body.append(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (_) { ok = false; }
    area.remove();
    return ok;
  }
}

function botaoCopiar(texto, rotulo, aviso) {
  return h("button", { class: "botao secundario", type: "button", onclick: async () => {
    avisar(await copiarTexto(texto) ? aviso : `Não deu para copiar. Selecione e copie: ${texto}`);
  } }, "📋 ", rotulo);
}

function mascaraCep(v) {
  const d = v.replace(/\D/g, "").slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
}
function mascaraCpf(v) {
  const d = v.replace(/\D/g, "").slice(0, 11);
  return d.replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d{1,2})$/, "$1-$2");
}
function mascaraTelefone(v) {
  const d = v.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

function cpfValido(cpf) {
  const d = String(cpf || "").replace(/\D/g, "");
  if (d.length !== 11 || d === d[0].repeat(11)) return false;
  for (const n of [9, 10]) {
    let soma = 0;
    for (let i = 0; i < n; i++) soma += Number(d[i]) * (n + 1 - i);
    if (((soma * 10) % 11) % 10 !== Number(d[n])) return false;
  }
  return true;
}

/**
 * Lê um número digitado à mão. Com vírgula, ela é o decimal e os pontos são milhar ("1.234,56").
 * Sem vírgula, o ponto só é milhar no formato "1.299" / "12.345.678"; senão é decimal ("0.765", "49.90").
 * `pontoDecimal`: câmbio e percentuais, em que o ponto é sempre decimal.
 * Vazio -> null; lixo ("12abc") -> NaN.
 */
function lerNumero(v, { pontoDecimal = false } = {}) {
  let t = String(v ?? "").trim().replace(/^R\$/i, "").replace(/\s+/g, "");
  if (!t) return null;
  if (t.includes(",")) t = t.replace(/\./g, "").replace(",", ".");
  else if (!pontoDecimal && /^[1-9]\d{0,2}(\.\d{3})+$/.test(t)) t = t.replace(/\./g, "");
  return /^\d+(\.\d+)?$/.test(t) ? Number(t) : NaN;
}

/** "49,90", "49.90", "1.299" ou "1.234,56" -> centavos; vazio -> null; inválido -> NaN. */
function reais(v) {
  const n = lerNumero(v);
  return n === null || Number.isNaN(n) ? n : Math.round(n * 100);
}
const textoReais = (c) => (c === null || c === undefined ? "" : (c / 100).toFixed(2).replace(".", ","));

function lerArmazenado(chave, padrao, armazenamento = localStorage) {
  try { return JSON.parse(armazenamento.getItem(chave)) ?? padrao; } catch (_) { return padrao; }
}
function gravar(chave, valor, armazenamento = localStorage) {
  try { armazenamento.setItem(chave, JSON.stringify(valor)); } catch (_) { /* modo privado */ }
}

// ------------------------------------------------------------- imagens

/** Espelha loja/imagens.py: a imagem provisória do produto é gerada aqui, sem ir ao servidor. */
const cacheSvg = new Map();
function escurecer(cor, fator = 0.62) {
  return "#" + [1, 3, 5].map((i) => Math.floor(parseInt(cor.slice(i, i + 2), 16) * fator).toString(16).padStart(2, "0")).join("");
}
function svgProduto(emoji, cor) {
  const base = /^#[0-9a-fA-F]{6}$/.test(cor || "") ? cor : "#1f5c45";
  const chave = `${base}|${emoji}`;
  if (cacheSvg.has(chave)) return cacheSvg.get(chave);
  const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">`
    + `<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${base}"/><stop offset="1" stop-color="${escurecer(base)}"/></linearGradient>`
    + `<pattern id="trama" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">`
    + `<rect width="14" height="28" fill="#fff" fill-opacity=".06"/><rect y="0" width="28" height="14" fill="#000" fill-opacity=".05"/></pattern></defs>`
    + `<rect width="400" height="400" fill="url(#g)"/><rect width="400" height="400" fill="url(#trama)"/>`
    + `<circle cx="200" cy="200" r="118" fill="#fff" fill-opacity=".16"/>`
    + `<text x="200" y="208" font-size="132" text-anchor="middle" dominant-baseline="middle" font-family="'Noto Color Emoji','Apple Color Emoji','Segoe UI Emoji',sans-serif">${esc(emoji || "📦")}</text></svg>`;
  const uri = `data:image/svg+xml,${encodeURIComponent(svg)}`;
  cacheSvg.set(chave, uri);
  return uri;
}

/** URL da imagem do produto; sem foto e com a cor disponível, gera o SVG no navegador. */
function imagemProduto(p, miniatura = false) {
  const semFoto = typeof p.imagem === "string" && p.imagem.startsWith("/img/produto/");
  if (semFoto && p.cor) return svgProduto(p.icone, p.cor);
  return (miniatura && p.imagem_miniatura) || p.imagem;
}

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

// ------------------------------------------------------------- WhatsApp

function linkWhatsApp(texto) {
  const numero = estado.loja && estado.loja.whatsapp;
  return numero ? `https://wa.me/${numero}?text=${encodeURIComponent(texto)}` : null;
}

/** `texto` pode ser uma função, para a mensagem refletir o estado na hora do clique (ex.: quantidade). */
function botaoWhatsApp(texto, rotulo, classe = "botao whatsapp", soIcone = false) {
  const gerar = typeof texto === "function" ? texto : () => texto;
  const url = linkWhatsApp(gerar());
  if (!url) return null;
  return h("a", { class: classe, href: url, target: "_blank", rel: "noopener", "aria-label": soIcone ? rotulo : null,
    onclick: (e) => { e.currentTarget.href = linkWhatsApp(gerar()); } },
  h("span", { "aria-hidden": "true" }, "💬"), soIcone ? null : ` ${rotulo}`);
}

function atualizarWhatsAppFlutuante() {
  const antigo = $("#whatsapp-flutuante");
  if (antigo) antigo.remove();
  const url = linkWhatsApp(estado.loja.whatsapp_mensagem || "Olá!");
  if (!url) return;
  document.body.append(h("a", { id: "whatsapp-flutuante", class: "whatsapp-flutuante", href: url, target: "_blank", rel: "noopener",
    "aria-label": "Atendimento pelo WhatsApp" }, h("span", { "aria-hidden": "true" }, "💬"), h("span", { class: "so-desktop" }, "Atendimento")));
}

// ------------------------------------------------------------- componentes

function precoPix(centavos) {
  return Math.round(centavos - Math.floor((centavos * estado.loja.desconto_pix_pct) / 100));
}

function numeroParcelas(centavos) {
  return Math.max(1, Math.min(estado.loja.parcelas_max, Math.floor(centavos / estado.loja.parcela_minima)));
}

function textoParcelas(centavos) {
  const n = numeroParcelas(centavos);
  return n > 1 ? `ou ${n}x de ${brl(Math.ceil(centavos / n))} sem juros` : "";
}

function cartaoProduto(p, prioritario = false) {
  const off = p.preco_de_centavos && p.preco_de_centavos > p.preco_centavos
    ? Math.round((1 - p.preco_centavos / p.preco_de_centavos) * 100) : 0;
  return h("a", { class: "cartao-produto", href: `/produto/${p.slug}` },
    off ? h("span", { class: "selo" }, `-${off}%`) : null,
    h("img", { src: imagemProduto(p, true), alt: "", loading: prioritario ? null : "lazy", decoding: "async", width: 400, height: 400 }),
    h("div", { class: "info" },
      h("span", { class: "nome" }, p.nome),
      off ? h("span", { class: "preco-de" }, brl(p.preco_de_centavos)) : null,
      h("span", { class: "preco" }, brl(p.preco_centavos)),
      h("span", { class: "preco-pix" }, `${brl(precoPix(p.preco_centavos))} no Pix`),
      p.estoque > 0 ? h("span", { class: "parcelado" }, textoParcelas(p.preco_centavos))
        : h("span", { class: "esgotado" }, "Esgotado"),
    ),
  );
}

/** `prioritarios`: quantos cartões carregam a imagem sem `loading=lazy` (os que aparecem logo de cara). */
function gradeProdutos(lista, prioritarios = 4) {
  if (!lista.length) {
    return h("div", { class: "vazio" }, h("div", { class: "ico" }, "🔎"), h("p", {}, "Nenhum produto encontrado."));
  }
  return h("div", { class: "grade-produtos" }, lista.map((p, k) => cartaoProduto(p, k < prioritarios)));
}

function esqueletoCartoes(n) {
  return h("div", { class: "grade-produtos", "aria-hidden": "true" }, Array.from({ length: n }, () =>
    h("div", { class: "cartao-produto esqueleto" }, h("div", { class: "esq-img" }),
      h("div", { class: "info" }, h("span", { class: "esq-linha" }), h("span", { class: "esq-linha curta" }), h("span", { class: "esq-linha curta" })))));
}

function esqueletoPagina() {
  return [h("p", { class: "sr" }, "Carregando…"), h("div", { class: "esq-linha esq-titulo", "aria-hidden": "true" }), esqueletoCartoes(8)];
}

function campo(nome, rotulo, attrs = {}, classe = "c3", dica = null) {
  const id = `campo-${nome}`;
  return h("div", { class: `campo ${classe}`, "data-campo": nome },
    h("label", { for: id }, rotulo),
    h("input", { id, name: nome, type: "text", "aria-describedby": [dica ? `dica-${nome}` : null, `erro-${nome}`].filter(Boolean).join(" "), ...attrs }),
    dica ? h("span", { class: "dica-campo", id: `dica-${nome}` }, dica) : null,
    h("span", { class: "msg-erro", id: `erro-${nome}` }),
  );
}

/** Marca (ou limpa, com msg vazia) o erro de um bloco [data-campo]. */
function marcarErro(c, msg) {
  c.classList.toggle("com-erro", Boolean(msg));
  const m = $(".msg-erro", c);
  if (m) m.textContent = msg || "";
  c.querySelectorAll("input:not([type=radio]):not([type=checkbox]), select, textarea").forEach((ctrl) => {
    if (msg) ctrl.setAttribute("aria-invalid", "true");
    else ctrl.removeAttribute("aria-invalid");
  });
}

function mostrarErros(form, campos, focar = true) {
  form.querySelectorAll("[data-campo]").forEach((c) => marcarErro(c, ""));
  let primeiro = null;
  for (const [nome, msg] of Object.entries(campos || {})) {
    const c = form.querySelector(`[data-campo="${nome}"]`);
    if (!c || typeof msg !== "string") continue;
    marcarErro(c, msg);
    primeiro = primeiro || c.querySelector("input:not([type=hidden]), select, textarea");
  }
  if (primeiro && focar) primeiro.focus();
}

function linkNaoSeiCep() {
  return h("a", { href: "https://buscacepinter.correios.com.br/", target: "_blank", rel: "noopener", class: "parcelado link-cep" }, "Não sei meu CEP");
}

function simuladorFrete(obterSubtotal) {
  const saida = h("div", { class: "resultado-frete", "aria-live": "polite" });
  const input = h("input", { id: "simulador-cep", type: "text", inputmode: "numeric", autocomplete: "postal-code", placeholder: "00000-000",
    value: lerArmazenado("tipiti:cep", "") || "", oninput: (e) => (e.target.value = mascaraCep(e.target.value)) });
  const form = h("form", {
    onsubmit: async (e) => {
      e.preventDefault();
      saida.textContent = "Calculando…";
      try {
        const f = await api(`/api/frete?cep=${encodeURIComponent(input.value)}&subtotal=${obterSubtotal()}`);
        gravar("tipiti:cep", f.cep);
        trocar(saida, h("b", {}, f.zona_nome), " — ",
          f.gratis ? h("span", { class: "desconto" }, "Frete grátis") : brl(f.valor_centavos),
          `, chega em até ${f.prazo_dias} dias úteis.`,
          !f.regiao_norte ? h("div", { class: "parcelado" }, "Entregamos em todo o Brasil, com prioridade para a Região Norte.") : null,
        );
      } catch (err) {
        saida.textContent = err.message;
      }
    },
  }, input, h("button", { class: "botao secundario", type: "submit" }, "Calcular"));
  return h("div", { class: "simulador" },
    h("label", { for: "simulador-cep", class: "rotulo-simulador" }, "🚚 Calcular frete e prazo"), form, saida, linkNaoSeiCep());
}

// ------------------------------------------------------------- páginas

async function paginaInicial(main) {
  const ativo = vigencia();
  const l = estado.loja;
  document.title = "Tipiti — importados com entrega rápida no Norte";
  const destaques = h("div", {}, esqueletoCartoes(4));
  const novidades = h("div", {}, esqueletoCartoes(4));
  trocar(main, h("section", { class: "hero" },
      h("div", {},
        h("h1", {}, "Importados com preço baixo, entregues rápido no Norte."),
        h("p", {}, "Achadinhos, eletrônicos, casa, beleza e muito mais direto da China — sem esperar semanas: enviamos de Manaus para toda a região."),
        h("a", { class: "botao", href: "#destaques" }, "Ver ofertas"),
      ),
      h("div", { class: "hero-cidades", "aria-label": "Cidades atendidas" },
        l.cidades_destaque.map((c) => h("span", {}, `📍 ${c}`))),
    ),
    h("div", { class: "beneficios" },
      [["🚚", "Frete grátis no Norte", `Em compras acima de ${brl(l.frete_gratis_a_partir)}`],
       ["⚡", `${l.desconto_pix_pct}% de desconto no Pix`, "Aprovação imediata"],
       ["💳", `Até ${l.parcelas_max}x sem juros`, "No cartão de crédito"],
       ["🔁", "7 dias para trocar", "Direito de arrependimento"]]
        .map(([ico, t, s]) => h("div", { class: "beneficio" }, h("span", { class: "ico" }, ico), h("div", {}, h("b", {}, t), h("small", {}, s))))),
    h("section", { class: "secao" },
      h("h2", {}, "Categorias"),
      h("div", { class: "grade-categorias" }, estado.categorias.map((c) =>
        h("a", { class: "cartao-categoria", href: `/categoria/${c.slug}`, style: `--cor:${c.cor}` },
          h("span", { class: "ico" }, c.icone), h("b", {}, c.nome), h("small", {}, `${c.total} produtos`))))),
    h("section", { class: "secao", id: "destaques" },
      h("div", { class: "secao-cabecalho" }, h("h2", {}, "Destaques da semana")), destaques),
    h("section", { class: "secao" }, h("h2", {}, "Novidades"), novidades),
  );
  const [listaDestaques, listaNovidades] = await Promise.all([
    api("/api/produtos?destaque=1&limite=8"), api("/api/produtos?ordem=novidades&limite=8"),
  ]);
  if (!ativo()) return;
  trocar(destaques, gradeProdutos(listaDestaques));
  trocar(novidades, gradeProdutos(listaNovidades, 0));
}

function seletorOrdem(atual, aoMudar) {
  const opcoes = { relevancia: "Mais relevantes", menor_preco: "Menor preço", maior_preco: "Maior preço", novidades: "Novidades", nome: "Nome (A–Z)" };
  return h("label", {}, "Ordenar: ",
    h("select", { onchange: (e) => aoMudar(e.target.value) },
      Object.entries(opcoes).map(([v, t]) => h("option", { value: v, selected: v === atual }, t))));
}

/**
 * Lista de produtos que carrega 24 por vez. Pede 25 para saber se há mais.
 * Se o servidor ignorar `offset` (versão antiga), passa a pedir tudo até a próxima página e descarta repetidos.
 */
function listaPaginada(urlBase, ativo) {
  const vistos = new Set();
  let total = 0;
  let semOffset = false;
  const grade = h("div", { class: "grade-produtos" });
  const contador = h("span", {});
  const anuncio = h("p", { class: "sr", "aria-live": "polite" });

  async function buscar() {
    const url = semOffset ? `${urlBase}&limite=${total + POR_PAGINA + 1}` : `${urlBase}&limite=${POR_PAGINA + 1}&offset=${total}`;
    const lista = await api(url);
    const novos = lista.filter((p) => !vistos.has(p.slug));
    if (!semOffset && total > 0 && novos.length < lista.length) {
      semOffset = true;  // o servidor devolveu a primeira página de novo
      return buscar();
    }
    const haMais = semOffset ? lista.length > total + POR_PAGINA : lista.length > POR_PAGINA;
    return { novos: novos.slice(0, POR_PAGINA), haMais };
  }

  function acrescentar({ novos, haMais }) {
    const inicio = total;
    novos.forEach((p) => vistos.add(p.slug));
    const cartoes = novos.map((p, k) => cartaoProduto(p, inicio + k < 4));
    grade.append(...cartoes);
    total += novos.length;
    botao.hidden = !haMais;
    contador.textContent = haMais ? `Mais de ${total} produtos` : `${total} produto(s)`;
    return cartoes;
  }

  const botao = h("button", { class: "botao secundario carregar-mais", type: "button", hidden: true, onclick: async () => {
    botao.disabled = true;
    botao.textContent = "Carregando…";
    try {
      const r = await buscar();
      if (!ativo()) return;
      const cartoes = acrescentar(r);
      anuncio.textContent = `${cartoes.length} produtos carregados.`;
      if (cartoes[0]) cartoes[0].focus({ preventScroll: true });
    } catch (err) {
      if (ativo()) avisar(err.message);
    } finally {
      botao.disabled = false;
      botao.textContent = "Carregar mais";
    }
  } }, "Carregar mais");

  return {
    contador,
    elemento: h("div", {}, grade, h("div", { class: "centro" }, botao), anuncio),
    primeira: async () => { const r = await buscar(); acrescentar(r); return total; },
  };
}

async function paginaCategoria(main, slug) {
  const ativo = vigencia();
  const ordem = new URLSearchParams(location.search).get("ordem") || "relevancia";
  const lista = listaPaginada(`/api/produtos?categoria=${slug}&ordem=${encodeURIComponent(ordem)}`, ativo);
  const [cat, total] = await Promise.all([api(`/api/categorias/${slug}`), lista.primeira()]);
  if (!ativo()) return;
  document.title = `${cat.nome} | Tipiti`;
  trocar(main, h("div", { class: "caminho" }, h("a", { href: "/" }, "Início"), " › ", cat.nome),
    h("h1", {}, `${cat.icone} ${cat.nome}`),
    h("p", { class: "parcelado" }, cat.descricao),
    h("div", { class: "barra-filtros" },
      lista.contador,
      seletorOrdem(ordem, (o) => navegar(`/categoria/${slug}?ordem=${o}`, true))),
    total ? lista.elemento : gradeProdutos([]),
  );
}

async function semResultados(q, ativo) {
  let destaques = [];
  try { destaques = await api("/api/produtos?destaque=1&limite=4"); } catch (_) { /* segue sem sugestões */ }
  if (!ativo()) return null;
  const zap = botaoWhatsApp(`Olá! Procuro: ${q}`, "Pergunte no WhatsApp", "botao whatsapp");
  return h("div", { class: "sem-resultados" },
    h("div", { class: "painel" },
      h("p", {}, h("b", {}, "Dicas para encontrar:")),
      h("ul", { class: "dicas" },
        h("li", {}, "Confira se a palavra está escrita certinho."),
        h("li", {}, "Use menos palavras, por exemplo “fone” em vez de “fone de ouvido sem fio preto”."),
        h("li", {}, "Busque pelo tipo de produto: “carregador”, “luminária”, “ventilador”.")),
      h("p", {}, h("b", {}, "Ou navegue pelas categorias:")),
      h("div", { class: "chips" }, estado.categorias.map((c) => h("a", { class: "chip", href: `/categoria/${c.slug}` }, `${c.icone} ${c.nome}`))),
      h("div", { class: "nao-achou" },
        h("p", {}, h("b", {}, "Não achou? "), "A gente pode ter ou trazer para você."),
        zap || h("a", { href: `mailto:${estado.loja.email}?subject=${encodeURIComponent(`Procuro: ${q}`)}` }, `Escreva para ${estado.loja.email}`))),
    destaques.length ? h("section", { class: "secao" }, h("h2", {}, "Destaques da loja"), gradeProdutos(destaques)) : null);
}

async function paginaBusca(main) {
  const ativo = vigencia();
  const params = new URLSearchParams(location.search);
  const q = params.get("q") || "";
  const ordem = params.get("ordem") || "relevancia";
  $("#campo-busca").value = q;
  const lista = listaPaginada(`/api/produtos?q=${encodeURIComponent(q)}&ordem=${encodeURIComponent(ordem)}`, ativo);
  const total = await lista.primeira();
  if (!ativo()) return;
  document.title = `Busca: ${q} | Tipiti`;
  if (!total) {
    const vazio = await semResultados(q, ativo);
    if (!vazio) return;
    trocar(main, h("h1", {}, q ? `Nada encontrado para “${q}”` : "Nenhum produto encontrado"), vazio);
    return;
  }
  trocar(main, h("h1", {}, q ? `Resultados para “${q}”` : "Todos os produtos"),
    h("div", { class: "barra-filtros" },
      lista.contador,
      seletorOrdem(ordem, (o) => navegar(`/busca?q=${encodeURIComponent(q)}&ordem=${o}`, true))),
    lista.elemento,
  );
}

async function paginaProduto(main, slug) {
  const ativo = vigencia();
  const p = await api(`/api/produtos/${slug}`);
  if (!ativo()) return;
  document.title = `${p.nome} | Tipiti`;
  const opcoes = p.variacoes || [];
  // pré-seleciona a primeira opção com estoque (a escolha fica visível na legenda e na barra)
  let escolhida = opcoes.find((v) => v.estoque > 0) || (opcoes.length === 1 ? opcoes[0] : null);
  let qtd = 1;
  const precoAtual = () => (escolhida && escolhida.preco_centavos != null ? escolhida.preco_centavos : p.preco_centavos);
  const estoqueAtual = () => (escolhida ? escolhida.estoque : p.estoque);

  // galeria
  const fotos = (p.fotos || []).map((f) => ({ url: f.url, mini: f.miniatura || f.url }));
  const imagens = fotos.length ? fotos : [{ url: imagemProduto(p), mini: imagemProduto(p) }];
  const principal = h("img", { src: imagens[0].url, alt: p.nome, width: 400, height: 400, class: "foto-principal", fetchpriority: "high" });
  const miniaturas = imagens.length > 1 ? h("div", { class: "miniaturas" }, imagens.map((img, k) =>
    h("button", { type: "button", class: "miniatura-botao", "aria-label": `Foto ${k + 1}`, "aria-current": String(k === 0),
      onclick: (e) => {
        principal.src = img.url;
        e.currentTarget.parentElement.querySelectorAll("button").forEach((b) => b.setAttribute("aria-current", "false"));
        e.currentTarget.setAttribute("aria-current", "true");
      } }, h("img", { src: img.mini, alt: "", loading: "lazy", width: 68, height: 68 })))) : null;

  const blocoPreco = h("div", {});
  const blocoCompra = h("div", {});
  const barra = h("div", { class: "barra-compra", role: "region", "aria-label": "Compra rápida" });
  const inputQtd = h("input", { type: "number", min: 1, value: 1, "aria-label": `Quantidade de ${p.nome}`,
    onchange: (e) => { qtd = Math.max(1, Math.min(estoqueAtual() || 1, parseInt(e.target.value, 10) || 1)); e.target.value = qtd; } });
  const mudar = (d) => { qtd = Math.max(1, Math.min(estoqueAtual() || 1, qtd + d)); inputQtd.value = qtd; };
  const aviso = h("p", { class: "esgotado aviso-opcao", role: "alert", hidden: true });
  const rotuloEscolhida = h("b", {}, escolhida ? escolhida.nome : "escolha abaixo");

  const grupo = opcoes.length ? h("fieldset", { class: "opcoes-produto", id: "opcoes-produto" },
    h("legend", { class: "rotulo-opcoes" }, "Opção: ", rotuloEscolhida),
    h("div", { class: "botoes-opcoes" }, opcoes.map((v) => {
      const esgotada = !(v.estoque > 0);
      return h("label", { class: `opcao-produto${esgotada ? " opcao-esgotada" : ""}${escolhida === v ? " selecionada" : ""}` },
        h("input", { type: "radio", name: "opcao-produto", value: v.id, class: "sr", checked: escolhida === v, disabled: esgotada,
          onchange: (e) => {
            escolhida = v;
            grupo.querySelectorAll(".opcao-produto").forEach((l) => l.classList.toggle("selecionada", l.contains(e.target)));
            rotuloEscolhida.textContent = v.nome;
            aviso.hidden = true;
            grupo.classList.remove("destacar");
            atualizar();
          } }),
        h("span", {}, v.nome, esgotada ? " (esgotado)" : ""));
    })),
    aviso) : null;

  const exigirOpcao = () => {
    if (!opcoes.length || escolhida) return true;
    aviso.textContent = "Escolha uma opção para continuar.";
    aviso.hidden = false;
    grupo.classList.remove("destacar");
    void grupo.offsetWidth;
    grupo.classList.add("destacar");
    grupo.scrollIntoView({ behavior: reduzMovimento() ? "auto" : "smooth", block: "center" });
    const primeira = grupo.querySelector("input:not(:disabled)");
    if (primeira) primeira.focus({ preventScroll: true });
    return false;
  };
  const adicionar = (ir) => {
    if (!exigirOpcao()) return;
    adicionarAoCarrinho(p.slug, qtd, escolhida ? escolhida.id : null);
    if (ir) navegar("/carrinho");
    else mostrarFolhaCarrinho(`${qtd}× ${p.nome}${escolhida && opcoes.length > 1 ? ` — ${escolhida.nome}` : ""}`);
  };
  const textoZap = () => `Olá! Tenho interesse neste produto da Tipiti:\n${p.nome}${escolhida ? ` — ${escolhida.nome}` : ""}\nQuantidade: ${qtd}\n${location.href}`;

  const atualizar = () => {
    const preco = precoAtual();
    const estoque = estoqueAtual();
    const temOferta = (!escolhida || escolhida.preco_centavos == null) && p.preco_de_centavos != null && p.preco_de_centavos > preco;
    trocar(blocoPreco,
      temOferta ? h("div", { class: "preco-de" }, `De ${brl(p.preco_de_centavos)}`) : null,
      h("div", { class: "preco" }, brl(preco)),
      h("div", { class: "preco-pix" }, `${brl(precoPix(preco))} no Pix (${estado.loja.desconto_pix_pct}% off)`),
      h("div", { class: "parcelado" }, textoParcelas(preco)));
    qtd = Math.max(1, Math.min(qtd, estoque || 1));
    inputQtd.value = qtd;
    inputQtd.max = Math.max(1, estoque);
    const esgotada = escolhida && !(escolhida.estoque > 0);
    const disponivel = p.estoque > 0 && !esgotada;
    trocar(blocoCompra,
      disponivel
        ? h("div", { class: "compra" },
            h("div", { class: "quantidade" },
              h("button", { type: "button", "aria-label": `Diminuir quantidade de ${p.nome}`, onclick: () => mudar(-1) }, "−"), inputQtd,
              h("button", { type: "button", "aria-label": `Aumentar quantidade de ${p.nome}`, onclick: () => mudar(1) }, "+")),
            h("button", { class: "botao", type: "button", onclick: () => adicionar(false) }, "Adicionar ao carrinho"),
            h("button", { class: "botao secundario", type: "button", onclick: () => adicionar(true) }, "Comprar agora"))
        : h("p", { class: "esgotado" }, esgotada ? "Esta opção está esgotada. Escolha outra." : "Produto esgotado no momento."),
      estoque > 0 && estoque <= 5 && (escolhida || !opcoes.length) ? h("p", { class: "esgotado" }, `Últimas ${estoque} unidades!`) : null,
      botaoWhatsApp(textoZap, "Pedir pelo WhatsApp", "botao whatsapp"));
    trocar(barra,
      h("div", { class: "barra-compra-preco" },
        h("b", {}, brl(preco)),
        h("small", {}, `${brl(precoPix(preco))} no Pix`),
        escolhida && opcoes.length > 1 ? h("small", { class: "barra-opcao" }, escolhida.nome) : null),
      botaoWhatsApp(textoZap, "Pedir pelo WhatsApp", "botao whatsapp so-icone", true),
      disponivel ? h("button", { class: "botao", type: "button", onclick: () => adicionar(false) }, "Adicionar")
        : h("span", { class: "esgotado" }, "Esgotado"));
  };

  atualizar();
  trocar(main, h("div", { class: "caminho" }, h("a", { href: "/" }, "Início"), " › ",
      h("a", { href: `/categoria/${p.categoria.slug}` }, p.categoria.nome), " › ", p.nome),
    h("article", { class: "produto" },
      h("div", { class: "galeria" }, principal, miniaturas),
      h("div", { class: "produto-info" },
        h("h1", {}, p.nome),
        blocoPreco,
        grupo,
        blocoCompra,
        h("p", { class: "selo-importado" }, "📦 Produto importado · em estoque no Brasil · garantia de 90 dias"),
        p.descricao ? h("p", { class: "descricao" }, p.descricao) : null,
        simuladorFrete(() => precoAtual() * qtd),
      ),
    ),
    p.relacionados && p.relacionados.length ? h("section", { class: "secao" }, h("h2", {}, "Você também pode gostar"), gradeProdutos(p.relacionados, 0)) : null,
    barra,
  );
}

/** Linhas de totais. `carrinho`: mostra "Total no Pix" e o valor no cartão, em vez do total da forma escolhida. */
function blocoResumo(c, { carrinho = false } = {}) {
  const l = estado.loja;
  const linha = (rotulo, valor, classe = "") => h("div", { class: `linha-total ${classe}` }, h("span", {}, rotulo), h("span", {}, valor));
  const valorFrete = c.frete ? c.frete.valor_centavos : 0;
  const linhas = [linha("Subtotal", brl(c.subtotal_centavos))];
  const descontoPix = carrinho ? Math.floor((c.subtotal_centavos * l.desconto_pix_pct) / 100) : c.desconto_centavos;
  if (descontoPix) linhas.push(linha(`Desconto no Pix (${l.desconto_pix_pct}%)`, `− ${brl(descontoPix)}`, "desconto"));
  linhas.push(linha("Frete", c.frete ? (c.frete.gratis ? "Grátis" : brl(c.frete.valor_centavos)) : "Informe o CEP"));
  if (c.frete) linhas.push(h("div", { class: "parcelado" }, `${c.frete.zona_nome} · até ${c.frete.prazo_dias} dias úteis`));
  if (carrinho) {
    const noCartao = c.subtotal_centavos + valorFrete;
    const n = numeroParcelas(noCartao);
    linhas.push(linha("Total no Pix", brl(noCartao - descontoPix), "total"));
    linhas.push(h("p", { class: "parcelado alinhado-direita" }, n > 1
      ? `ou ${brl(noCartao)} em até ${n}x de ${brl(Math.ceil(noCartao / n))} sem juros no cartão`
      : `ou ${brl(noCartao)} no cartão ou boleto`));
  } else {
    linhas.push(linha("Total", brl(c.total_centavos), "total"));
  }

  const faltam = c.falta_para_frete_gratis;
  const pct = Math.min(100, Math.round((c.subtotal_centavos / l.frete_gratis_a_partir) * 100));
  const barra = (!c.frete || c.frete.regiao_norte) ? h("div", { class: "barra-frete" },
    faltam > 0 ? [`Faltam `, h("b", {}, brl(faltam)), ` para frete grátis na Região Norte`] : "🎉 Você ganhou frete grátis na Região Norte!",
    h("div", { class: "barra-progresso" }, h("span", { style: `width:${pct}%` }))) : null;
  return [barra, ...linhas];
}

/** Cota o carrinho; se o CEP salvo for inválido, cota sem ele e devolve a mensagem. */
async function cotarCarrinho(cep, extra = {}) {
  const pedir = (comCep) => api("/api/carrinho/cotacao", { method: "POST",
    body: JSON.stringify({ itens: estado.carrinho, cep: comCep || null, ...extra }) });
  try {
    return { cotacao: await pedir(cep), erroCep: "" };
  } catch (err) {
    if (!(err.campos && err.campos.cep)) throw err;
    gravar("tipiti:cep", "");
    return { cotacao: await pedir(null), erroCep: err.campos.cep };
  }
}

async function paginaCarrinho(main) {
  const ativo = vigencia();
  document.title = "Carrinho | Tipiti";
  const vazio = () => trocar(main, h("div", { class: "vazio" }, h("div", { class: "ico" }, "🛒"),
    h("h1", { tabindex: "-1" }, "Seu carrinho está vazio"), h("p", {}, "Que tal dar uma olhada nos destaques?"),
    h("a", { class: "botao", href: "/" }, "Continuar comprando")));
  if (!estado.carrinho.length) return vazio();
  let cep = lerArmazenado("tipiti:cep", "");
  let { cotacao, erroCep } = await cotarCarrinho(cep);
  if (!ativo()) return;

  // produto que saiu do catálogo: remove sozinho e avisa; os demais problemas ficam visíveis
  const sumiram = cotacao.itens.filter((i) => !i.produto_id && i.erro === "Produto indisponível.");
  if (sumiram.length) {
    const fora = new Set(sumiram.map((i) => i.chave));
    estado.carrinho = estado.carrinho.filter((i) => !fora.has(chaveItem(i.slug, i.variacao)));
    salvarCarrinho();
    avisar(sumiram.length === 1 ? "Um produto saiu do catálogo e foi tirado do seu carrinho."
      : `${sumiram.length} produtos saíram do catálogo e foram tirados do seu carrinho.`);
    if (!estado.carrinho.length) return vazio();
    ({ cotacao, erroCep } = await cotarCarrinho(cep));
    if (!ativo()) return;
  }

  const titulo = h("h1", {}, "Meu carrinho");
  const refs = new Map();

  let espera;
  let sequencia = 0;
  const resumo = h("aside", { class: "painel resumo", "aria-label": "Resumo do carrinho" });
  const recotar = (atraso = 300) => {
    clearTimeout(espera);
    resumo.setAttribute("aria-busy", "true");
    espera = setTimeout(async () => {
      const n = ++sequencia;
      try {
        const r = await cotarCarrinho(cep);
        if (!ativo() || n !== sequencia) return;
        ({ cotacao, erroCep } = r);
        if (erroCep) cep = "";
        for (const i of cotacao.itens) if (refs.has(i.chave)) atualizarLinha(refs.get(i.chave), i);
        desenharResumo();
      } catch (err) {
        if (ativo() && n === sequencia) avisar(err.message);
      } finally {
        if (n === sequencia) resumo.removeAttribute("aria-busy");
      }
    }, atraso);
  };

  function atualizarLinha(ref, i) {
    ref.item = i;
    if (ref.total) ref.total.textContent = brl(i.total_centavos);
    ref.erro.textContent = i.erro || "";
    ref.erro.hidden = !i.erro;
  }

  const remover = (i) => {
    alterarQuantidade(i.chave, 0);
    const ref = refs.get(i.chave);
    if (ref) ref.linha.remove();
    refs.delete(i.chave);
    if (!estado.carrinho.length) return vazio();
    avisar(`${i.nome || "Item"} removido do carrinho.`);
    titulo.tabIndex = -1;
    titulo.focus({ preventScroll: true });
    recotar(0);
  };

  const mudarQuantidade = (i, nova) => {
    const ref = refs.get(i.chave);
    nova = Math.max(1, Math.min(99, nova || 1));
    if (nova > ref.item.quantidade && ref.item.estoque != null && nova > ref.item.estoque) {
      avisar(ref.item.estoque > 0 ? `Só temos ${ref.item.estoque} unidade(s) em estoque.` : "Sem estoque no momento.");
      nova = Math.max(1, Math.min(nova, ref.item.estoque));
    }
    alterarQuantidade(i.chave, nova);
    ref.item = { ...ref.item, quantidade: nova, total_centavos: ref.item.preco_unit_centavos * nova };
    ref.input.value = nova;
    ref.menos.disabled = nova <= 1;
    ref.total.textContent = brl(ref.item.total_centavos);
    recotar();
  };

  const botaoRemover = (i) => h("button", { class: "botao-icone", type: "button", "aria-label": `Remover ${nomeComOpcao(i) || "item"}`,
    title: "Remover", onclick: () => remover(i) }, icone(ICONE_LIXEIRA));

  function linhaItem(i) {
    const erro = h("div", { class: "esgotado", hidden: !i.erro }, i.erro || "");
    if (!i.produto_id) {
      // precisa de ação: escolher opção ou produto temporariamente indisponível
      const linha = h("div", { class: "linha-item indisponivel" },
        h("div", { class: "foto-vazia", "aria-hidden": "true" }, i.icone || "📦"),
        h("div", {},
          h("a", { class: "nome", href: `/produto/${i.slug}` }, i.nome || "Produto"),
          erro,
          h("div", { class: "acoes" },
            h("a", { class: "botao secundario", href: `/produto/${i.slug}` }, i.erro === "Escolha uma opção do produto." ? "Escolher opção" : "Ver produto"),
            botaoRemover(i))),
        h("span", {}));
      refs.set(i.chave, { linha, erro, item: i });
      return linha;
    }
    const nome = nomeComOpcao(i);
    const total = h("b", { class: "total-item" }, brl(i.total_centavos));
    const menos = h("button", { type: "button", "aria-label": `Diminuir quantidade de ${nome}`, disabled: i.quantidade <= 1,
      onclick: () => mudarQuantidade(i, refs.get(i.chave).item.quantidade - 1) }, "−");
    const input = h("input", { type: "number", value: i.quantidade, min: 1, max: 99, "aria-label": `Quantidade de ${nome}`,
      onchange: (e) => mudarQuantidade(i, parseInt(e.target.value, 10)) });
    const mais = h("button", { type: "button", "aria-label": `Aumentar quantidade de ${nome}`,
      onclick: () => mudarQuantidade(i, refs.get(i.chave).item.quantidade + 1) }, "+");
    const linha = h("div", { class: "linha-item" },
      h("img", { src: imagemProduto(i, true), alt: "", width: 72, height: 72 }),
      h("div", {},
        h("a", { class: "nome", href: `/produto/${i.slug}` }, i.nome),
        i.variacao_nome ? h("div", {}, "Opção: ", h("b", {}, i.variacao_nome)) : null,
        h("div", { class: "parcelado" }, `${brl(i.preco_unit_centavos)} cada`),
        erro,
        h("div", { class: "acoes" }, h("div", { class: "quantidade" }, menos, input, mais), botaoRemover(i))),
      total);
    refs.set(i.chave, { linha, erro, total, input, menos, item: i });
    return linha;
  }

  const inputCep = h("input", { id: "carrinho-cep", type: "text", inputmode: "numeric", autocomplete: "postal-code", placeholder: "00000-000",
    value: (cotacao.frete && cotacao.frete.cep) || cep, oninput: (e) => (e.target.value = mascaraCep(e.target.value)) });
  const formCep = h("form", { class: "simulador", onsubmit: (e) => {
    e.preventDefault();
    cep = mascaraCep(inputCep.value);
    gravar("tipiti:cep", cep);
    recotar(0);
  } },
  h("label", { for: "carrinho-cep", class: "rotulo-simulador" }, "CEP de entrega"),
  h("div", { class: "linha-cep" }, inputCep, h("button", { class: "botao secundario", type: "submit" }, "Calcular frete")),
  linkNaoSeiCep());
  const topoResumo = h("div", {});
  const totais = h("div", { "aria-live": "polite" });
  const acoes = h("div", {});

  function desenharResumo() {
    const validos = cotacao.itens.filter((i) => i.produto_id);
    const textoZap = () => `Olá! Quero finalizar este pedido na Tipiti:\n${validos.map((i) => `• ${i.quantidade}× ${nomeComOpcao(i)} — ${brl(i.total_centavos)}`).join("\n")}\nSubtotal: ${brl(cotacao.subtotal_centavos)}${cotacao.frete ? `\nCEP: ${cotacao.frete.cep}` : ""}`;
    trocar(topoResumo, erroCep ? h("div", { class: "alerta" }, erroCep) : null);
    trocar(totais, blocoResumo(cotacao, { carrinho: true }));
    trocar(acoes,
      !cotacao.valido ? h("div", { class: "alerta" }, "Ajuste os itens marcados em vermelho para continuar.") : null,
      h("button", { class: "botao grande", type: "button", disabled: !cotacao.valido, onclick: () => navegar("/checkout") }, "Finalizar compra"),
      botaoWhatsApp(textoZap, "Prefiro finalizar pelo WhatsApp", "botao whatsapp grande espaco-topo"),
      h("a", { href: "/", class: "link-continuar" }, "Continuar comprando"));
  }
  trocar(resumo, h("h2", {}, "Resumo"), topoResumo, formCep, totais, acoes);
  desenharResumo();

  trocar(main, titulo,
    h("div", { class: "layout-carrinho" },
      h("div", { class: "painel" }, cotacao.itens.map(linhaItem)),
      resumo,
    ),
  );
}

const UFS = ["AM", "PA", "RR", "AP", "AC", "RO", "TO", "AL", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PB", "PE", "PI", "PR", "RJ", "RN", "RS", "SC", "SE", "SP"];
const ROTULOS_CHECKOUT = { nome: "Nome", email: "E-mail", telefone: "Celular", cpf: "CPF", cep: "CEP", endereco: "Rua", numero: "Número",
  bairro: "Bairro", cidade: "Cidade", uf: "UF", pagamento: "Pagamento", parcelas: "Parcelas" };
const OBRIGATORIOS_CHECKOUT = ["nome", "email", "telefone", "cpf", "cep", "endereco", "numero", "bairro", "cidade", "uf"];

function validarCampoCheckout(nome, valor) {
  const v = String(valor || "").trim();
  const d = v.replace(/\D/g, "");
  switch (nome) {
    case "nome": return v.length >= 3 ? "" : "Informe o nome completo.";
    case "email": return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v) ? "" : "Informe um e-mail válido.";
    case "telefone": return d.length === 10 || d.length === 11 ? "" : "Informe o celular com DDD (10 ou 11 dígitos).";
    case "cpf": return cpfValido(d) ? "" : "CPF inválido. Confira os números.";
    case "cep": return d.length === 8 ? "" : "O CEP tem 8 dígitos.";
    case "uf": return v ? "" : "Selecione o estado.";
    default: return v ? "" : "Preencha este campo.";
  }
}

/** "Faltam 3 campos: Nome, CPF, Número. Confira: E-mail." */
function textoErrosCheckout(erros, dados) {
  const nomes = Object.keys(erros).filter((n) => ROTULOS_CHECKOUT[n]);
  const faltam = nomes.filter((n) => !String(dados[n] || "").trim());
  const invalidos = nomes.filter((n) => !faltam.includes(n));
  const partes = [];
  if (faltam.length) partes.push(`${faltam.length === 1 ? "Falta 1 campo" : `Faltam ${faltam.length} campos`}: ${faltam.map((n) => ROTULOS_CHECKOUT[n]).join(", ")}`);
  if (invalidos.length) partes.push(`Confira: ${invalidos.map((n) => ROTULOS_CHECKOUT[n]).join(", ")}`);
  return partes.length ? `${partes.join(". ")}.` : "";
}

async function paginaCheckout(main) {
  const ativo = vigencia();
  document.title = "Finalizar compra | Tipiti";
  if (!estado.carrinho.length) return navegar("/carrinho", true);

  const rascunho = lerArmazenado("tipiti:checkout", {}, sessionStorage);
  const resumo = h("aside", { class: "painel resumo resumo-checkout" }, h("h2", {}, "Resumo do pedido"), h("div", { class: "carregando" }, "Calculando…"));
  const totalMovel = h("b", {}, "…");
  const conteudoMovel = h("div", {}, h("div", { class: "carregando" }, "Calculando…"));
  const resumoMovel = h("details", { class: "painel resumo-movel" },
    h("summary", {}, h("span", {}, "Resumo do pedido"), totalMovel), conteudoMovel);
  const totalConfirmar = h("p", { class: "total-confirmar", "aria-live": "polite" });
  const selParcelas = h("select", { id: "campo-parcelas", name: "parcelas", class: "campo-select", "aria-describedby": "erro-parcelas" });
  const blocoParcelas = h("div", { class: "campo", "data-campo": "parcelas", hidden: true },
    h("label", { for: "campo-parcelas" }, "Parcelas"), selParcelas, h("span", { class: "msg-erro", id: "erro-parcelas" }));
  const dicaCepFixa = h("span", {}, "Preencha o CEP e completamos o endereço. ");
  const dicaCep = h("span", { "aria-live": "polite" });

  const form = h("form", { class: "painel", novalidate: true },
    h("fieldset", {}, h("legend", {}, "1. Seus dados"),
      h("div", { class: "grade-form" },
        campo("nome", "Nome completo", { autocomplete: "name", required: true }, "c6"),
        campo("email", "E-mail", { type: "email", inputmode: "email", autocomplete: "email", required: true }, "c3"),
        campo("telefone", "Celular com DDD", { type: "tel", autocomplete: "tel-national", inputmode: "numeric", placeholder: "(92) 90000-0000", required: true }, "c3"),
        campo("cpf", "CPF", { inputmode: "numeric", placeholder: "000.000.000-00", required: true }, "c3"))),
    h("fieldset", {}, h("legend", {}, "2. Endereço de entrega"),
      h("div", { class: "grade-form" },
        campo("cep", "CEP", { inputmode: "numeric", autocomplete: "postal-code", placeholder: "00000-000", required: true }, "c2",
          [dicaCepFixa, dicaCep]),
        h("div", { class: "c4 celula-link-cep" }, linkNaoSeiCep()),
        campo("endereco", "Rua / Avenida", { autocomplete: "address-line1", required: true }, "c4"),
        campo("numero", "Número", { required: true, inputmode: "numeric" }, "c2"),
        campo("complemento", "Complemento", { autocomplete: "address-line2" }, "c4"),
        campo("bairro", "Bairro", { required: true }, "c2"),
        campo("cidade", "Cidade", { autocomplete: "address-level2", required: true }, "c3"),
        h("div", { class: "campo c1", "data-campo": "uf" },
          h("label", { for: "campo-uf" }, "UF"),
          h("select", { id: "campo-uf", name: "uf", class: "campo-select", autocomplete: "address-level1", required: true, "aria-describedby": "erro-uf" },
            h("option", { value: "" }, "—"), UFS.map((u) => h("option", { value: u }, u))),
          h("span", { class: "msg-erro", id: "erro-uf" })))),
    h("fieldset", {}, h("legend", {}, "3. Pagamento"),
      h("div", { class: "opcoes-pagamento", "data-campo": "pagamento" },
        [["pix", "Pix", `${estado.loja.desconto_pix_pct}% de desconto · aprovação imediata`],
         ["cartao", "Cartão de crédito", `Até ${estado.loja.parcelas_max}x sem juros`],
         ["boleto", "Boleto bancário", "Compensação em até 2 dias úteis"]]
          .map(([v, t, s]) => h("label", { class: "opcao" },
            h("input", { type: "radio", name: "pagamento", value: v, checked: v === (rascunho.pagamento || "pix") }),
            h("span", {}, h("b", {}, t), h("small", {}, s)))),
        h("span", { class: "msg-erro" }),
        blocoParcelas)),
    h("div", { class: "alerta", id: "erro-geral", role: "alert", hidden: true }),
    totalConfirmar,
    h("button", { class: "botao grande", type: "submit" }, "Confirmar pedido"),
    h("p", { class: "parcelado centro" }, "Ao confirmar, você concorda com a política de trocas da Tipiti."),
  );

  for (const [nome, valor] of Object.entries(rascunho)) {
    const el = form.elements[nome];
    if (el && nome !== "pagamento" && nome !== "parcelas") el.value = valor;
  }
  if (!form.elements.cep.value) form.elements.cep.value = lerArmazenado("tipiti:cep", "");

  const mascaras = { cep: mascaraCep, cpf: mascaraCpf, telefone: mascaraTelefone };
  for (const [nome, fn] of Object.entries(mascaras)) {
    form.elements[nome].addEventListener("input", (e) => (e.target.value = fn(e.target.value)));
  }

  const dadosForm = () => Object.fromEntries(new FormData(form).entries());
  const erroGeral = $("#erro-geral", form);
  form.addEventListener("input", (e) => {
    gravar("tipiti:checkout", { ...dadosForm(), cpf: "" }, sessionStorage);
    const c = e.target.closest("[data-campo]");
    if (c && c.classList.contains("com-erro")) marcarErro(c, "");
    if (!form.querySelector(".com-erro")) erroGeral.hidden = true;
  });
  // valida ao sair do campo os que têm formato (só se a pessoa digitou algo)
  form.addEventListener("focusout", (e) => {
    const nome = e.target.name;
    if (!["email", "telefone", "cpf", "cep"].includes(nome) || !e.target.value.trim()) return;
    marcarErro(e.target.closest("[data-campo]"), validarCampoCheckout(nome, e.target.value));
  });

  let ultimaCotacao = null;
  let sequencia = 0;
  async function atualizarResumo() {
    const d = dadosForm();
    const cepValido = (d.cep || "").replace(/\D/g, "").length === 8;
    const n = ++sequencia;
    try {
      ultimaCotacao = await api("/api/carrinho/cotacao", { method: "POST",
        body: JSON.stringify({ itens: estado.carrinho, cep: cepValido ? d.cep : null, pagamento: d.pagamento }) });
    } catch (err) {
      if (!ativo() || n !== sequencia) return;
      trocar(resumo, h("h2", {}, "Resumo do pedido"), h("div", { class: "alerta" }, err.message));
      trocar(conteudoMovel, h("div", { class: "alerta" }, err.message));
      return;
    }
    if (!ativo() || n !== sequencia) return;
    const c = ultimaCotacao;
    const conteudo = () => [
      c.itens.filter((i) => i.produto_id).map((i) => h("div", { class: "linha-total" },
        h("span", {}, `${i.quantidade}× ${nomeComOpcao(i)}`), h("span", {}, brl(i.total_centavos)))),
      h("hr", { class: "divisor" }),
      blocoResumo(c),
      !c.valido ? h("div", { class: "alerta" }, "Há itens indisponíveis. ", h("a", { href: "/carrinho" }, "Revise o carrinho.")) : null,
    ];
    trocar(resumo, h("h2", {}, "Resumo do pedido"), conteudo());
    trocar(conteudoMovel, conteudo());
    totalMovel.textContent = brl(c.total_centavos);
    blocoParcelas.hidden = d.pagamento !== "cartao";
    const atual = parseInt(selParcelas.value, 10) || 1;
    trocar(selParcelas, ...Array.from({ length: c.parcelas_max }, (_, k) => k + 1).map((n) =>
      h("option", { value: n, selected: n === Math.min(atual, c.parcelas_max) },
        n === 1 ? `1x de ${brl(c.total_centavos)} (à vista)` : `${n}x de ${brl(Math.ceil(c.total_centavos / n))} sem juros`)));
    trocar(totalConfirmar, "Total: ", h("b", {}, brl(c.total_centavos)), c.frete ? null : h("span", { class: "parcelado" }, " + frete (informe o CEP)"));
  }

  let ultimoCep = "";
  async function buscarCep() {
    const d = form.elements.cep.value.replace(/\D/g, "");
    if (d.length !== 8 || d === ultimoCep) return;
    ultimoCep = d;
    gravar("tipiti:cep", mascaraCep(d));
    atualizarResumo();
    dicaCepFixa.hidden = true;
    dicaCep.textContent = "Buscando o endereço…";
    const controle = new AbortController();
    const limite = setTimeout(() => controle.abort(), 8000);
    try {
      const resp = await fetch(`https://viacep.com.br/ws/${d}/json/`, { signal: controle.signal });
      if (!resp.ok) throw new Error("viacep");
      const e = await resp.json();
      if (!ativo() || form.elements.cep.value.replace(/\D/g, "") !== d) return;
      if (!e || e.erro) throw new Error("cep");
      if (e.logradouro) form.elements.endereco.value = e.logradouro;
      if (e.bairro) form.elements.bairro.value = e.bairro;
      if (e.localidade) form.elements.cidade.value = e.localidade;
      if (e.uf) form.elements.uf.value = e.uf;
      ["endereco", "bairro", "cidade", "uf"].forEach((n) => { if (form.elements[n].value) marcarErro(form.elements[n].closest("[data-campo]"), ""); });
      dicaCep.textContent = "Endereço preenchido — confira e informe o número.";
      gravar("tipiti:checkout", { ...dadosForm(), cpf: "" }, sessionStorage);
      if (document.activeElement === form.elements.cep || document.activeElement === document.body) form.elements.numero.focus();
    } catch (_) {
      if (ativo()) dicaCep.textContent = "Não encontramos o CEP — preencha o endereço.";
    } finally {
      clearTimeout(limite);
    }
  }
  form.elements.cep.addEventListener("change", buscarCep);
  form.elements.cep.addEventListener("keyup", () => { if (form.elements.cep.value.length === 9) buscarCep(); });
  form.querySelectorAll("input[name=pagamento]").forEach((r) => r.addEventListener("change", atualizarResumo));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const botao = form.querySelector("button[type=submit]");
    erroGeral.hidden = true;
    const dados = dadosForm();
    const erros = {};
    for (const nome of OBRIGATORIOS_CHECKOUT) {
      const msg = validarCampoCheckout(nome, dados[nome]);
      if (msg) erros[nome] = msg;
    }
    if (Object.keys(erros).length) {
      mostrarErros(form, erros);
      erroGeral.textContent = textoErrosCheckout(erros, dados);
      erroGeral.hidden = false;
      return;
    }
    botao.disabled = true;
    botao.textContent = "Enviando pedido…";
    try {
      const pedido = await api("/api/pedidos", { method: "POST", body: JSON.stringify({ ...dados, itens: estado.carrinho }) });
      estado.carrinho = [];
      salvarCarrinho();
      try { sessionStorage.removeItem("tipiti:checkout"); } catch (_) { /* ignora */ }
      navegar(`/pedido/${pedido.codigo}`);
    } catch (err) {
      if (!ativo()) return;
      const campos = err.campos || {};
      mostrarErros(form, campos);
      const detalhe = campos.itens ? "" : textoErrosCheckout(campos, dados);
      trocar(erroGeral, err.message, detalhe ? ` ${detalhe}` : "",
        campos.itens ? [" ", h("a", { href: "/carrinho" }, "Revise o carrinho.")] : null);
      erroGeral.hidden = false;
      if (!Object.keys(campos).some((k) => form.querySelector(`[data-campo="${k}"]`))) erroGeral.scrollIntoView({ block: "center" });
      if (campos.itens) atualizarResumo();
      botao.disabled = false;
      botao.textContent = "Confirmar pedido";
    }
  });

  trocar(main, h("h1", {}, "Finalizar compra"), h("div", { class: "layout-carrinho layout-checkout" }, resumoMovel, form, resumo));
  atualizarResumo();
}

async function paginaPedido(main, codigo) {
  const ativo = vigencia();
  const p = await api(`/api/pedidos/${encodeURIComponent(codigo)}`);
  if (!ativo()) return;
  document.title = `Pedido ${p.codigo} | Tipiti`;
  const l = estado.loja;
  const chavePix = typeof l.chave_pix === "string" ? l.chave_pix.trim() : "";
  const aguardando = p.status === "aguardando_pagamento";
  const zap = botaoWhatsApp(
    `Olá! Fiz o pedido ${p.codigo} no site da Tipiti.\n${p.itens.map((i) => `• ${i.quantidade}× ${nomeComOpcao(i)}`).join("\n")}\nTotal: ${brl(p.total_centavos)} (${p.pagamento_nome}${p.parcelas > 1 ? ` em ${p.parcelas}x` : ""}).`,
    "Enviar meu pedido no WhatsApp", "botao whatsapp grande");
  const horas = Number(l.prazo_reserva_horas);

  let passos = null;
  if (aguardando && p.pagamento === "pix" && chavePix) {
    passos = h("div", { class: "info-box passos" },
      h("h2", {}, "Pague com Pix para confirmar"),
      h("ol", {},
        h("li", {}, "Abra o app do seu banco e escolha Pix › Pagar com chave."),
        h("li", {}, "Cole a chave abaixo e pague ", h("b", {}, brl(p.total_centavos)), "."),
        h("li", {}, zap ? "Envie o comprovante pelo WhatsApp e despachamos seu pedido." : "Assim que o pagamento cair, despachamos seu pedido.")),
      h("div", { class: "chave-pix" },
        h("span", { class: "parcelado" }, "Chave Pix"),
        h("code", {}, chavePix),
        h("span", { class: "parcelado" }, "Valor: ", h("b", {}, brl(p.total_centavos)))),
      botaoCopiar(chavePix, "Copiar chave Pix", "Chave Pix copiada ✔"));
  } else if (aguardando) {
    passos = h("div", { class: "info-box passos" },
      h("h2", {}, "Próximo passo: pagamento"),
      h("p", {}, zap ? ["Toque em ", h("b", {}, "Enviar meu pedido no WhatsApp"), " e mandamos as instruções de pagamento",
        p.pagamento === "cartao" ? ` (cartão em ${p.parcelas}x)` : p.pagamento === "boleto" ? " (boleto)" : " (Pix)", "."]
        : ["Vamos entrar em contato pelo seu celular ou e-mail com as instruções de pagamento. Se preferir, escreva para ",
          h("a", { href: `mailto:${l.email}?subject=${encodeURIComponent(`Pedido ${p.codigo}`)}` }, l.email), "."]));
  }

  trocar(main, h("div", { class: "confirmacao" },
      h("div", { class: "ico-grande", "aria-hidden": "true" }, "🎉"),
      h("h1", {}, `Obrigado, ${p.primeiro_nome}!`),
      h("p", {}, "Seu pedido foi registrado com o código"),
      h("div", { class: "linha-codigo" }, h("span", { class: "codigo" }, p.codigo), botaoCopiar(p.codigo, "Copiar código", "Código copiado ✔")),
      zap ? h("div", { class: "acao-principal" }, zap) : null,
      aguardando && horas > 0 ? h("p", { class: "reserva" }, `⏳ Seu pedido fica reservado por ${horas} ${horas === 1 ? "hora" : "horas"}.`) : null,
      h("p", {}, "Status: ", h("b", {}, p.status_nome)),
      passos,
      h("div", { class: "painel itens-pedido" },
        h("h2", {}, "Itens"),
        p.itens.map((i) => h("div", { class: "linha-total" }, h("span", {}, `${i.quantidade}× ${nomeComOpcao(i)}`), h("span", {}, brl(i.preco_unit_centavos * i.quantidade)))),
        h("hr", { class: "divisor" }),
        h("div", { class: "linha-total" }, h("span", {}, "Subtotal"), h("span", {}, brl(p.subtotal_centavos))),
        p.desconto_centavos ? h("div", { class: "linha-total desconto" }, h("span", {}, "Desconto Pix"), h("span", {}, `− ${brl(p.desconto_centavos)}`)) : null,
        h("div", { class: "linha-total" }, h("span", {}, "Frete"), h("span", {}, p.frete_centavos ? brl(p.frete_centavos) : "Grátis")),
        h("div", { class: "linha-total total" }, h("span", {}, "Total"), h("span", {}, brl(p.total_centavos))),
        h("p", { class: "parcelado" }, `Entrega em ${p.destino} · prazo de até ${p.prazo_dias} dias úteis após a confirmação do pagamento.`)),
      h("p", {}, "Guarde o código para acompanhar o pedido. Dúvidas: ", h("a", { href: `mailto:${l.email}` }, l.email)),
      h("a", { class: "botao secundario", href: "/" }, "Voltar à loja"),
    ),
  );
}

function paginaEntregas(main) {
  document.title = "Entregas e prazos | Tipiti";
  const l = estado.loja;
  trocar(main, h("div", { class: "texto" },
    h("h1", {}, "Entregas e prazos"),
    h("p", {}, `A Tipiti despacha de Manaus e atende com prioridade a Região Norte. Compras acima de ${brl(l.frete_gratis_a_partir)} têm frete grátis para todos os estados do Norte.`),
    h("table", { class: "tabela-frete" },
      h("thead", {}, h("tr", {}, h("th", {}, "Destino"), h("th", {}, "Frete"), h("th", {}, "Prazo"))),
      h("tbody", {}, l.zonas_frete.map((z) => h("tr", {}, h("td", {}, z.nome), h("td", {}, brl(z.valor_centavos)), h("td", {}, `até ${z.prazo_dias} dias úteis`))))),
    h("p", { class: "parcelado" }, "Prazos contados a partir da confirmação do pagamento. Localidades atendidas por via fluvial podem variar conforme o nível dos rios. Também entregamos nas demais regiões do Brasil."),
  ));
}

function paginaSobre(main) {
  document.title = "Sobre a Tipiti";
  trocar(main, h("div", { class: "texto" },
    h("h1", {}, "Sobre a Tipiti"),
    h("p", {}, "A Tipiti nasceu para resolver um problema conhecido de quem mora no Norte: comprar online e esperar semanas, pagando um frete que às vezes custa mais que o produto."),
    h("p", {}, "Importamos da China uma seleção variada de produtos — achadinhos, eletrônicos, casa, beleza, moda, brinquedos e ferramentas —, deixamos tudo em estoque no Brasil e despachamos de perto, para que chegue rápido em Manaus, Parintins, Boa Vista, Santarém, Macapá, Belém e em toda a região."),
    h("p", {}, "O nome vem do tipiti, o trançado indígena que faz parte do dia a dia da região: um objeto simples, resistente e feito para durar. É assim que queremos atender."),
  ));
}

function paginaTrocas(main) {
  document.title = "Trocas e devoluções | Tipiti";
  trocar(main, h("div", { class: "texto" },
    h("h1", {}, "Trocas e devoluções"),
    h("p", {}, "Você pode desistir da compra em até 7 dias corridos após o recebimento, conforme o art. 49 do Código de Defesa do Consumidor, com reembolso integral."),
    h("p", {}, "Produtos com defeito podem ser trocados dentro do prazo de garantia. Fale com a gente informando o código do pedido."),
    h("p", {}, "Contato: ", h("a", { href: `mailto:${estado.loja.email}` }, estado.loja.email)),
  ));
}

// ------------------------------------------------------------- administração

const STATUS_PEDIDO = { aguardando_pagamento: "Aguardando pagamento", pago: "Pago", enviado: "Enviado", entregue: "Entregue", cancelado: "Cancelado" };

let tokenRecusado = false;

function sairDoPainel(recusado = false) {
  try { sessionStorage.removeItem(CHAVE_ADMIN); } catch (_) { /* ignora */ }
  tokenRecusado = recusado;
  navegar("/admin", true);
}

/** Mostra o login se não houver token; senão devolve o cabeçalho de autorização. */
function autenticacaoAdmin(main) {
  const token = lerArmazenado(CHAVE_ADMIN, "", sessionStorage);
  if (token) return { Authorization: `Bearer ${token}` };
  const recusado = tokenRecusado;
  tokenRecusado = false;
  const input = h("input", { id: "token-admin", type: "password", autocomplete: "current-password", "aria-describedby": recusado ? "erro-token" : null,
    "aria-invalid": recusado ? "true" : null });
  trocar(main, h("div", { class: "painel login-admin" },
    h("h1", {}, "Painel da loja"),
    h("form", { onsubmit: (e) => { e.preventDefault(); gravar(CHAVE_ADMIN, input.value.trim(), sessionStorage); rotear(); } },
      h("div", { class: "campo" + (recusado ? " com-erro" : "") },
        h("label", { for: "token-admin" }, "Token de acesso"), input,
        recusado ? h("span", { class: "msg-erro", id: "erro-token", role: "alert" }, "Token incorreto. Confira e tente de novo.") : null),
      h("button", { class: "botao grande espaco-topo" }, "Entrar"))));
  if (recusado) input.focus();
  return null;
}

function cabecalhoAdmin(abaAtual) {
  const abas = [["pedidos", "Pedidos"], ["produtos", "Produtos"], ["novo", "+ Novo produto"], ["calculadora", "Calculadora"], ["configuracoes", "Configurações"]];
  return [
    h("div", { class: "secao-cabecalho" }, h("h1", {}, "Painel da loja"), h("button", { class: "link-botao", type: "button", onclick: () => sairDoPainel() }, "Sair")),
    h("div", { class: "abas", role: "tablist" }, abas.map(([id, rotulo]) =>
      h("button", { class: "botao secundario", role: "tab", type: "button", "aria-selected": String(abaAtual === id),
        onclick: () => { gravar("tipiti:admin-aba", id, sessionStorage); navegar("/admin"); } }, rotulo))),
  ];
}

async function comTratamento(conteudo, ativo, fn) {
  try { await fn(); } catch (err) {
    if (!ativo()) return;
    if (err.status === 401) return sairDoPainel(true);
    trocar(conteudo, h("div", { class: "alerta" }, err.message));
  }
}

async function paginaAdmin(main) {
  const ativo = vigencia();
  document.title = "Painel | Tipiti";
  const auth = autenticacaoAdmin(main);
  if (!auth) return;
  const aba = lerArmazenado("tipiti:admin-aba", "pedidos", sessionStorage);
  const conteudo = h("div", {}, h("div", { class: "carregando" }, "Carregando…"));
  trocar(main, cabecalhoAdmin(aba), conteudo);
  await comTratamento(conteudo, ativo, async () => {
    let novo;
    if (aba === "novo") novo = formularioNovoProduto(auth);
    else if (aba === "produtos") novo = await listaProdutosAdmin(auth);
    else if (aba === "calculadora") {
      const aj = await api("/api/admin/ajustes", { headers: auth });
      novo = h("div", { class: "painel" }, h("h2", {}, "Calculadora de preço do importado"),
        h("p", { class: "parcelado" }, "Descubra o custo real de cada unidade no Brasil e o preço de venda para a margem que você quer."),
        calculadora(auth, aj));
    } else if (aba === "configuracoes") novo = await formularioAjustes(auth);
    else novo = await painelPedidos(auth);
    if (ativo()) trocar(conteudo, novo);
  });
}

function cartaoNumero(rotulo, valor, detalhe) {
  return h("div", { class: "cartao-numero" }, h("small", {}, rotulo), h("b", {}, valor), detalhe ? h("small", {}, detalhe) : null);
}

/** Célula com rótulo para a tabela virar cartão no celular. */
const celula = (rotulo, attrs, ...filhos) => h("td", { "data-rotulo": rotulo, ...attrs }, h("div", { class: "celula-conteudo" }, ...filhos));

async function painelPedidos(auth) {
  const [pedidos, resumo] = await Promise.all([api("/api/admin/pedidos", { headers: auth }), api("/api/admin/resumo", { headers: auth })]);
  const nomeItem = (i) => `${i.quantidade}× ${i.nome}${i.variacao_nome ? ` (${i.variacao_nome})` : ""}`;
  return h("div", {},
    h("div", { class: "cartoes-numeros" },
      cartaoNumero("Pedidos", resumo.pedidos, "sem contar cancelados"),
      cartaoNumero("Faturamento", brl(resumo.faturamento_centavos), "com frete"),
      cartaoNumero("Lucro estimado", brl(resumo.lucro_centavos),
        resumo.pedidos_sem_custo ? `${resumo.pedidos_sem_custo} pedido(s) sem custo cadastrado` : "produtos − custo, sem o frete"),
      cartaoNumero("Ticket médio", brl(resumo.ticket_medio_centavos))),
    resumo.estoque_baixo.length ? h("div", { class: "info-box espaco-baixo" },
      h("b", {}, "⚠️ Estoque baixo: "),
      resumo.estoque_baixo.map((p, k) => [k ? ", " : "", h("a", { href: `/admin/produto/${p.slug}` }, p.nome), ` (${p.estoque})`])) : null,
    pedidos.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-pedidos" },
      h("thead", {}, h("tr", {}, ["Pedido", "Cliente", "Entrega", "Itens", "Total", "Lucro", "Status"].map((t) => h("th", {}, t)))),
      h("tbody", {}, pedidos.map((p) => {
        const primeiroNome = p.cliente.nome.split(" ")[0];
        const zap = `https://wa.me/55${p.cliente.telefone}?text=${encodeURIComponent(`Olá, ${primeiroNome}! Aqui é da Tipiti, sobre o seu pedido ${p.codigo}.`)}`;
        // com `proximos_status`, só oferece o status atual e os próximos permitidos
        const possiveis = Array.isArray(p.proximos_status)
          ? [p.status, ...p.proximos_status.filter((s) => s !== p.status)] : Object.keys(STATUS_PEDIDO);
        const travado = p.status === "cancelado" || possiveis.length < 2;
        return h("tr", {},
          celula("Pedido", {}, h("b", {}, p.codigo), h("div", { class: "parcelado" }, p.criado_em)),
          celula("Cliente", {}, p.cliente.nome, h("div", { class: "parcelado" }, p.cliente.email),
            h("div", { class: "parcelado" }, mascaraTelefone(p.cliente.telefone))),
          celula("Entrega", {}, `${p.entrega.endereco}, ${p.entrega.numero} ${p.entrega.complemento}`,
            h("div", { class: "parcelado" }, `${p.entrega.bairro} · ${p.entrega.cidade}/${p.entrega.uf} · ${mascaraCep(p.entrega.cep)}`),
            h("div", { class: "parcelado" }, p.zona_frete)),
          celula("Itens", {}, p.itens.map((i) => h("div", {}, nomeItem(i)))),
          celula("Total", {}, brl(p.total_centavos), h("div", { class: "parcelado" }, `${p.pagamento_nome}${p.parcelas > 1 ? ` ${p.parcelas}x` : ""}`)),
          celula("Lucro", {}, p.lucro_centavos === null ? h("span", { class: "parcelado" }, "sem custo") : brl(p.lucro_centavos)),
          celula("", { class: "celula-status" },
            h("select", { class: "campo-select", disabled: travado, "aria-label": `Status do pedido ${p.codigo}`,
              onchange: async (e) => {
                if (e.target.value === "cancelado" && !confirm("Cancelar o pedido e devolver os itens ao estoque?")) { e.target.value = p.status; return; }
                try { await api(`/api/admin/pedidos/${p.codigo}`, { method: "PATCH", headers: auth, body: JSON.stringify({ status: e.target.value }) }); avisar("Status atualizado ✔"); rotear(); }
                catch (err) { if (err.status === 401) return sairDoPainel(true); avisar(err.message); e.target.value = p.status; }
              } }, possiveis.map((v) => h("option", { value: v, selected: v === p.status }, STATUS_PEDIDO[v] || v))),
            h("a", { class: "botao whatsapp", href: zap, target: "_blank", rel: "noopener" }, h("span", { "aria-hidden": "true" }, "💬"), ` WhatsApp de ${primeiroNome}`)));
      }))))
      : h("p", {}, "Nenhum pedido ainda."));
}

async function listaProdutosAdmin(auth) {
  const produtos = await api("/api/admin/produtos", { headers: auth });
  const margem = (p) => (p.custo_centavos ? `${Math.round(((p.preco_centavos - p.custo_centavos) / p.preco_centavos) * 100)}%` : "—");
  return h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-produtos" },
    h("thead", {}, h("tr", {}, h("th", {}, "Produto"), h("th", {}, "Preço"), h("th", {}, "Custo"),
      h("th", {}, "Margem bruta", h("small", { class: "dica-coluna" }, "lucro ÷ preço")), h("th", {}, "Estoque"), h("th", {}, "Situação"), h("th", {}, h("span", { class: "sr" }, "Ações")))),
    h("tbody", {}, produtos.map((p) => h("tr", {},
      celula("", { class: "celula-produto" }, h("div", { class: "produto-admin" }, h("img", { src: imagemProduto(p, true), alt: "", class: "miniatura", width: 48, height: 48, loading: "lazy" }),
        h("div", {}, h("a", { href: `/admin/produto/${p.slug}` }, p.nome),
          h("div", { class: "parcelado" }, p.categoria.nome, p.tem_variacoes ? " · com opções" : "")))),
      celula("Preço", {}, brl(p.preco_centavos)),
      celula("Custo", {}, p.custo_centavos ? brl(p.custo_centavos) : h("span", { class: "parcelado" }, "—")),
      celula("Margem bruta (lucro ÷ preço)", {}, margem(p)),
      celula("Estoque", { class: p.estoque <= 3 ? "esgotado" : "" }, p.estoque),
      celula("Situação", {}, p.ativo ? "No ar" : "Fora do ar", p.destaque ? " · ⭐" : ""),
      celula("", { class: "celula-acao" }, h("a", { class: "botao secundario", href: `/admin/produto/${p.slug}` }, "Editar")))))));
}

async function paginaEditorProduto(main, slug) {
  const ativo = vigencia();
  document.title = "Editar produto | Tipiti";
  const auth = autenticacaoAdmin(main);
  if (!auth) return;
  const conteudo = h("div", {}, h("div", { class: "carregando" }, "Carregando…"));
  trocar(main, cabecalhoAdmin("produtos"), conteudo);
  await comTratamento(conteudo, ativo, async () => {
    const [p, aj] = await Promise.all([api(`/api/admin/produtos/${slug}`, { headers: auth }), api("/api/admin/ajustes", { headers: auth })]);
    if (!ativo()) return;
    document.title = `${p.nome} | Painel Tipiti`;
    trocar(conteudo,
      h("p", {}, h("a", { href: "/admin" }, "← Voltar aos produtos"), " · ", h("a", { href: `/produto/${p.slug}`, target: "_blank", rel: "noopener" }, "Ver na loja ↗")),
      h("div", { class: "editor" },
        secaoDadosProduto(auth, p),
        h("div", {},
          secaoFotos(auth, p),
          secaoVariacoes(auth, p),
          h("section", { class: "painel" }, h("h2", {}, "Calculadora de preço"),
            h("p", { class: "parcelado" }, "Calcule o custo real deste produto e aplique o preço sugerido."),
            calculadora(auth, aj, { precoAtual: p.preco_centavos, aoAplicar: async (preco, custo) => {
              try {
                await api(`/api/admin/produtos/${p.slug}`, { method: "PATCH", headers: auth, body: JSON.stringify({ preco_centavos: preco, custo_centavos: custo }) });
                avisar("Preço e custo aplicados ✔");
                rotear();
              } catch (err) { avisar(err.message); }
            } })))));
  });
}

function seletorCategoria(atual) {
  return h("div", { class: "campo c3", "data-campo": "categoria" },
    h("label", { for: "campo-categoria" }, "Categoria"),
    h("select", { id: "campo-categoria", name: "categoria", class: "campo-select", "aria-describedby": "erro-categoria" },
      h("option", { value: "" }, "Escolha…"), estado.categorias.map((c) => h("option", { value: c.slug, selected: c.slug === atual }, `${c.icone} ${c.nome}`))),
    h("span", { class: "msg-erro", id: "erro-categoria" }));
}

function camposPreco(p = {}) {
  return [
    campo("preco_centavos", "Preço de venda (R$)", { inputmode: "decimal", placeholder: "49,90", value: textoReais(p.preco_centavos) }, "c2"),
    campo("preco_de_centavos", "Preço antigo (riscado, opcional)", { inputmode: "decimal", placeholder: "69,90", value: textoReais(p.preco_de_centavos) }, "c2"),
    campo("custo_centavos", "Custo por unidade (R$, só você vê)", { inputmode: "decimal", placeholder: "22,50", value: textoReais(p.custo_centavos) }, "c2"),
  ];
}

function valoresPreco(f) {
  const dados = { preco_centavos: reais(f.preco_centavos.value), preco_de_centavos: reais(f.preco_de_centavos.value), custo_centavos: reais(f.custo_centavos.value) };
  const erros = {};
  for (const [k, v] of Object.entries(dados)) if (Number.isNaN(v)) erros[k] = "Valor inválido. Use o formato 49,90.";
  if (dados.preco_centavos === null) erros.preco_centavos = "Informe o preço.";
  return [dados, erros];
}

function secaoDadosProduto(auth, p) {
  const form = h("form", { class: "painel", novalidate: true },
    h("h2", {}, "Dados do produto"),
    h("div", { class: "grade-form" },
      campo("nome", "Nome", { maxlength: 120, value: p.nome }, "c6"),
      seletorCategoria(p.categoria.slug),
      campo("icone", "Emoji (se não houver foto)", { maxlength: 8, value: p.icone }, "c3"),
      camposPreco(p),
      campo("estoque", p.tem_variacoes ? "Estoque (soma das opções)" : "Estoque (unidades)",
        { type: "number", min: 0, value: p.estoque, disabled: p.tem_variacoes }, "c2"),
      h("div", { class: "campo c6", "data-campo": "descricao" },
        h("label", { for: "campo-descricao" }, "Descrição"),
        h("textarea", { id: "campo-descricao", name: "descricao", rows: 5, maxlength: 2000, class: "campo-texto", "aria-describedby": "erro-descricao" }),
        h("span", { class: "msg-erro", id: "erro-descricao" })),
      h("label", { class: "c3 caixa" }, h("input", { type: "checkbox", name: "ativo", checked: p.ativo }), " Produto no ar"),
      h("label", { class: "c3 caixa" }, h("input", { type: "checkbox", name: "destaque", checked: p.destaque }), " Destaque na página inicial")),
    h("div", { class: "alerta", hidden: true }),
    h("button", { class: "botao grande espaco-topo", type: "submit" }, "Salvar dados"));
  form.elements.descricao.value = p.descricao || "";
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = form.elements;
    const alerta = $(".alerta", form);
    alerta.hidden = true;
    const [precos, erros] = valoresPreco(f);
    if (Object.keys(erros).length) return mostrarErros(form, erros);
    const dados = { nome: f.nome.value, categoria: f.categoria.value, icone: f.icone.value, descricao: f.descricao.value,
      ativo: f.ativo.checked, destaque: f.destaque.checked, ...precos };
    if (!p.tem_variacoes) dados.estoque = parseInt(f.estoque.value, 10);
    try {
      await api(`/api/admin/produtos/${p.slug}`, { method: "PATCH", headers: auth, body: JSON.stringify(dados) });
      mostrarErros(form, {});
      avisar("Produto salvo ✔");
    } catch (err) {
      mostrarErros(form, err.campos);
      alerta.textContent = err.message;
      alerta.hidden = false;
    }
  });
  return form;
}

// -- fotos: reduzidas no navegador antes do envio (menos dados no 4G e no servidor)

function lerArquivoBase64(arquivo) {
  return new Promise((resolver, rejeitar) => {
    const leitor = new FileReader();
    leitor.onload = () => resolver(String(leitor.result).split(",")[1] || "");
    leitor.onerror = () => rejeitar(new Error("Não foi possível ler o arquivo."));
    leitor.readAsDataURL(arquivo);
  });
}

function abrirImagem(arquivo) {
  const comImg = () => new Promise((resolver, rejeitar) => {
    const url = URL.createObjectURL(arquivo);
    const img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); resolver(img); };
    img.onerror = () => { URL.revokeObjectURL(url); rejeitar(new Error(`Não foi possível abrir “${arquivo.name}”. Use JPG, PNG ou WEBP.`)); };
    img.src = url;
  });
  return window.createImageBitmap ? createImageBitmap(arquivo).catch(comImg) : comImg();
}

const canvasParaBlob = (canvas, tipo, qualidade) => new Promise((resolver) => canvas.toBlob(resolver, tipo, qualidade));

/** Reduz para no máximo `maximo` px no maior lado; WEBP 0,82 (JPEG se o navegador não gerar WEBP). */
async function reduzirImagem(fonte, maximo) {
  const largura = fonte.naturalWidth || fonte.width;
  const altura = fonte.naturalHeight || fonte.height;
  const escala = Math.min(1, maximo / Math.max(largura, altura));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(largura * escala));
  canvas.height = Math.max(1, Math.round(altura * escala));
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff";  // PNG transparente vira fundo branco (o JPEG não tem transparência)
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(fonte, 0, 0, canvas.width, canvas.height);
  let blob = await canvasParaBlob(canvas, "image/webp", 0.82);
  if (!blob || blob.type !== "image/webp") blob = await canvasParaBlob(canvas, "image/jpeg", 0.82);
  if (!blob) throw new Error("Não foi possível processar a foto.");
  return blob;
}

async function enviarFoto(auth, slug, arquivo) {
  const fonte = await abrirImagem(arquivo);
  let principal, miniatura;
  try {
    principal = await reduzirImagem(fonte, 1200);
    miniatura = await reduzirImagem(fonte, 400);
  } finally {
    if (fonte.close) fonte.close();
  }
  if (principal.size > 3 * 1024 * 1024) throw new Error(`“${arquivo.name}” passa de 3 MB mesmo depois de reduzida.`);
  const [dados, mini] = await Promise.all([lerArquivoBase64(principal), lerArquivoBase64(miniatura)]);
  return api(`/api/admin/produtos/${slug}/foto`, { method: "POST", headers: auth, body: JSON.stringify({ dados, miniatura: mini }) });
}

function secaoFotos(auth, produto) {
  const secao = h("section", { class: "painel" });
  const desenhar = (p) => {
    const input = h("input", { type: "file", accept: "image/jpeg,image/png,image/webp", multiple: true, class: "sr",
      onchange: async (e) => {
        const arquivos = [...e.target.files];
        let atual = p;
        let enviadas = 0;
        for (const [k, arquivo] of arquivos.entries()) {
          avisar(`Enviando foto ${k + 1} de ${arquivos.length}…`);
          try { atual = await enviarFoto(auth, p.slug, arquivo); enviadas++; } catch (err) {
            if (err.status === 401) return sairDoPainel(true);
            avisar(err.message);
            break;
          }
        }
        desenhar(atual);
        if (enviadas === arquivos.length) avisar("Fotos atualizadas ✔");
      } });
    const acao = async (metodo, url) => {
      try { desenhar(await api(url, { method: metodo, headers: auth })); } catch (err) { avisar(err.message); }
    };
    trocar(secao,
      h("h2", {}, "Fotos"),
      h("p", { class: "parcelado" }, "A primeira é a capa. JPG, PNG ou WEBP; reduzimos para 1200 px antes de enviar. Até 8 fotos. Fotos quadradas ficam melhores."),
      h("div", { class: "galeria-admin" },
        p.fotos.map((f, k) => h("figure", {},
          h("img", { src: f.miniatura || f.url, alt: `Foto ${k + 1}`, width: 120, height: 120, loading: "lazy" }),
          k === 0 ? h("span", { class: "selo" }, "Capa") : null,
          h("figcaption", {},
            k > 0 ? h("button", { class: "link-botao", type: "button", onclick: () => acao("POST", `/api/admin/produtos/${p.slug}/fotos/${f.id}/capa`) }, "Usar como capa") : null,
            h("button", { class: "link-botao", type: "button", onclick: () => confirm("Remover esta foto?") && acao("DELETE", `/api/admin/produtos/${p.slug}/fotos/${f.id}`) }, "Remover")))),
        p.fotos.length < 8 ? h("label", { class: "adicionar-foto" }, input, h("span", {}, "＋"), "Adicionar fotos") : null));
  };
  desenhar(produto);
  return secao;
}

function secaoVariacoes(auth, produto) {
  const secao = h("section", { class: "painel" });
  let linhas = produto.variacoes.filter((v) => v.ativo).map((v) => ({ ...v }));
  const desenhar = () => {
    const corpo = linhas.map((v, k) => h("tr", { "data-campo": `variacao_${k}` },
      celula("Opção", {}, h("input", { type: "text", value: v.nome, placeholder: "Ex.: Preto / 220 V", "aria-label": `Nome da opção ${k + 1}`, oninput: (e) => (v.nome = e.target.value) })),
      celula("Código (SKU)", {}, h("input", { type: "text", value: v.sku || "", placeholder: "opcional", "aria-label": `Código (SKU) da opção ${k + 1}`, oninput: (e) => (v.sku = e.target.value) })),
      celula("Preço próprio (R$)", {}, h("input", { type: "text", inputmode: "decimal", value: v.preco_texto ?? textoReais(v.preco_centavos), placeholder: "igual ao produto",
        "aria-label": `Preço próprio da opção ${k + 1}`, oninput: (e) => (v.preco_texto = e.target.value) })),
      celula("Estoque", {}, h("input", { type: "number", min: 0, value: v.estoque ?? 0, "aria-label": `Estoque da opção ${k + 1}`, oninput: (e) => (v.estoque = parseInt(e.target.value, 10) || 0) })),
      celula("", { class: "celula-acao" }, h("button", { class: "botao-icone", type: "button", "aria-label": `Remover opção ${v.nome || k + 1}`, title: "Remover",
        onclick: () => { linhas.splice(k, 1); desenhar(); } }, icone(ICONE_LIXEIRA)))));
    const erro = h("div", { class: "alerta", hidden: true });
    trocar(secao,
      h("h2", {}, "Opções (cor, voltagem, tamanho)"),
      h("p", { class: "parcelado" }, "Cada opção tem estoque próprio e o cliente escolhe na página do produto. Para combinar, use nomes como “Preto / 220 V”. Deixe o preço vazio para usar o preço do produto."),
      linhas.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-variacoes tabela-cartoes" },
        h("thead", {}, h("tr", {}, ["Opção", "Código (SKU)", "Preço próprio (R$)", "Estoque", ""].map((t) => h("th", {}, t)))),
        h("tbody", {}, corpo))) : h("p", {}, "Este produto não tem opções: o estoque é controlado direto nos dados do produto."),
      erro,
      h("div", { class: "compra" },
        h("button", { class: "botao secundario", type: "button", onclick: () => { linhas.push({ nome: "", estoque: 0 }); desenhar(); } }, "+ Adicionar opção"),
        h("button", { class: "botao", type: "button", onclick: async () => {
          const lista = linhas.map((v) => {
            const preco = v.preco_texto !== undefined ? reais(v.preco_texto) : v.preco_centavos ?? null;
            return { id: v.id, nome: v.nome, sku: v.sku || "", preco_centavos: Number.isNaN(preco) ? -1 : preco, estoque: v.estoque ?? 0 };
          });
          try {
            const p = await api(`/api/admin/produtos/${produto.slug}/variacoes`, { method: "PUT", headers: auth, body: JSON.stringify({ variacoes: lista }) });
            avisar("Opções salvas ✔");
            rotear();  // atualiza estoque total nos dados do produto
            return p;
          } catch (err) {
            erro.replaceChildren(err.message, ...Object.entries(err.campos || {}).map(([k, m]) => h("div", {}, `Linha ${Number(k.split("_")[1]) + 1}: ${m}`)));
            erro.hidden = false;
          }
        } }, "Salvar opções")));
  };
  desenhar();
  return secao;
}

/** Campos da calculadora em que o ponto é sempre decimal (câmbio e percentuais). */
const CALC_PONTO_DECIMAL = new Set(["cambio", "quantidade", "impostos_pct", "taxa_pagamento_pct", "margem_pct"]);
const CALC_CAMPOS = ["custo_unitario", "cambio", "quantidade", "frete_lote", "impostos_pct", "outros_lote", "embalagem_unidade", "taxa_pagamento_pct", "margem_pct"];

function calculadora(auth, aj, { precoAtual = null, aoAplicar = null } = {}) {
  const cambios = { USD: aj.cambio_usd, CNY: aj.cambio_cny, BRL: "1" };
  const resultado = h("div", { class: "calc-resultado", "aria-live": "polite" });
  const form = h("form", { class: "grade-form", novalidate: true, onsubmit: (e) => e.preventDefault() },
    h("div", { class: "campo c2" }, h("label", { for: "calc-moeda" }, "Moeda do fornecedor"),
      h("select", { id: "calc-moeda", name: "moeda", class: "campo-select" },
        h("option", { value: "USD" }, "Dólar (US$)"), h("option", { value: "CNY" }, "Yuan (¥)"), h("option", { value: "BRL" }, "Real (R$)"))),
    campo("custo_unitario", "Preço por unidade no fornecedor", { inputmode: "decimal", placeholder: "3,20" }, "c2"),
    campo("cambio", "Câmbio (R$ por 1 unidade da moeda)", { inputmode: "decimal", value: cambios.USD }, "c2"),
    campo("quantidade", "Unidades no lote", { type: "number", min: 1, value: 100 }, "c2"),
    campo("frete_lote", "Frete internacional do lote (R$)", { inputmode: "decimal", placeholder: "800,00" }, "c2"),
    campo("impostos_pct", "Impostos e taxas de importação (%)", { inputmode: "decimal", value: aj.impostos_pct }, "c2"),
    campo("outros_lote", "Outros custos do lote (R$)", { inputmode: "decimal", placeholder: "despachante, armazenagem…" }, "c2"),
    campo("embalagem_unidade", "Embalagem por unidade (R$)", { inputmode: "decimal", placeholder: "1,50" }, "c2"),
    campo("taxa_pagamento_pct", "Taxa do meio de pagamento (%)", { inputmode: "decimal", value: aj.taxa_pagamento_pct }, "c2"),
    campo("margem_pct", "Margem de lucro desejada (%)", { inputmode: "decimal", value: aj.margem_pct }, "c6"));
  form.elements.moeda.addEventListener("change", (e) => {
    form.elements.cambio.value = cambios[e.target.value];
    form.elements.cambio.disabled = e.target.value === "BRL";
  });
  let espera;
  let sequencia = 0;
  const calcular = async () => {
    const f = form.elements;
    if (!f.custo_unitario.value.trim()) {
      trocar(resultado, h("p", { class: "parcelado" }, "Preencha o preço por unidade para ver o resultado."));
      return;
    }
    const corpo = { moeda: f.moeda.value, preco_centavos: precoAtual };
    const erros = {};
    for (const nome of CALC_CAMPOS) {
      if (f[nome].disabled) continue;
      const n = lerNumero(f[nome].value, { pontoDecimal: CALC_PONTO_DECIMAL.has(nome) });
      if (Number.isNaN(n)) erros[nome] = "Número inválido. Use, por exemplo, 0,765 ou 1.250,00.";
      corpo[nome] = n === null || Number.isNaN(n) ? "" : String(n);
    }
    if (Object.keys(erros).length) {
      mostrarErros(form, erros, false);
      trocar(resultado, h("div", { class: "alerta" }, "Corrija os campos marcados."));
      return;
    }
    const n = ++sequencia;
    try {
      const r = await api("/api/admin/calculadora", { method: "POST", headers: auth, body: JSON.stringify(corpo) });
      if (n !== sequencia) return;
      mostrarErros(form, {}, false);
      const linha = (rotulo, valor, classe = "") => h("div", { class: `linha-total ${classe}` }, h("span", {}, rotulo), h("span", {}, valor));
      const analise = (titulo, a) => h("div", { class: "calc-cartao" }, h("small", {}, titulo), h("b", {}, brl(a.preco_centavos)),
        h("small", {}, `Lucro ${brl(a.lucro_centavos)} por unidade · margem ${String(a.margem_pct).replace(".", ",")}%`));
      trocar(resultado,
        h("div", { class: "calc-colunas" },
          h("div", {},
            h("h3", {}, "Custo por unidade no Brasil"),
            linha("Produto", brl(r.custo.produto_centavos)), linha("Frete internacional", brl(r.custo.frete_centavos)),
            linha("Impostos e taxas", brl(r.custo.impostos_centavos)), linha("Outros custos", brl(r.custo.outros_centavos)),
            linha("Embalagem", brl(r.custo.embalagem_centavos)), linha("Custo total", brl(r.custo.total_centavos), "total")),
          h("div", {},
            analise("Preço sugerido", r.sugerido),
            r.atual ? analise("Com o preço atual", r.atual) : null,
            r.atual && r.atual.lucro_centavos < 0 ? h("div", { class: "alerta" }, "Com o preço atual você vende no prejuízo.") : null,
            aoAplicar ? h("button", { class: "botao grande", type: "button",
              onclick: () => aoAplicar(r.sugerido.preco_centavos, r.custo.total_centavos) },
              `Aplicar preço ${brl(r.sugerido.preco_centavos)} e custo ${brl(r.custo.total_centavos)}`) : null)));
    } catch (err) {
      if (n !== sequencia) return;
      mostrarErros(form, err.campos, false);
      trocar(resultado, h("div", { class: "alerta" }, err.message));
    }
  };
  form.addEventListener("input", () => { clearTimeout(espera); espera = setTimeout(calcular, 300); });
  form.addEventListener("change", () => { clearTimeout(espera); espera = setTimeout(calcular, 50); });
  calcular();
  return h("div", { class: "calculadora" }, form, resultado);
}

async function formularioAjustes(auth) {
  const aj = await api("/api/admin/ajustes", { headers: auth });
  const form = h("form", { class: "painel", novalidate: true },
    h("h2", {}, "WhatsApp da loja"),
    h("p", { class: "parcelado" }, "Com o número preenchido, aparecem o botão flutuante de atendimento e as opções “Pedir pelo WhatsApp” no produto, no carrinho e na confirmação do pedido."),
    h("div", { class: "grade-form" },
      campo("whatsapp", "Número com DDD", { type: "tel", inputmode: "numeric", placeholder: "(92) 99123-4567",
        value: aj.whatsapp ? mascaraTelefone(aj.whatsapp.slice(2)) : "" }, "c2"),
      campo("whatsapp_mensagem", "Mensagem inicial do botão de atendimento", { maxlength: 300, value: aj.whatsapp_mensagem }, "c4")),
    h("h2", { class: "espaco-topo-grande" }, "Pagamento por Pix"),
    h("div", { class: "grade-form" },
      campo("chave_pix", "Chave Pix", { maxlength: 140, autocomplete: "off", placeholder: "CNPJ, e-mail, telefone ou chave aleatória", value: aj.chave_pix ?? "" }, "c6",
        "Aparece para o cliente na confirmação do pedido, com o valor e o botão “Copiar chave Pix”. Deixe vazio para mandar as instruções pelo WhatsApp.")),
    h("h2", { class: "espaco-topo-grande" }, "Padrões da calculadora"),
    h("div", { class: "grade-form" },
      campo("cambio_usd", "Câmbio do dólar (R$)", { inputmode: "decimal", value: aj.cambio_usd }, "c2"),
      campo("cambio_cny", "Câmbio do yuan (R$)", { inputmode: "decimal", value: aj.cambio_cny }, "c2"),
      campo("impostos_pct", "Impostos e taxas de importação (%)", { inputmode: "decimal", value: aj.impostos_pct }, "c2"),
      campo("taxa_pagamento_pct", "Taxa do meio de pagamento (%)", { inputmode: "decimal", value: aj.taxa_pagamento_pct }, "c2"),
      campo("margem_pct", "Margem desejada (%)", { inputmode: "decimal", value: aj.margem_pct }, "c2")),
    h("button", { class: "botao grande espaco-topo", type: "submit" }, "Salvar configurações"));
  form.elements.whatsapp.addEventListener("input", (e) => (e.target.value = mascaraTelefone(e.target.value)));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const dados = Object.fromEntries(new FormData(form).entries());
    for (const nome of ["cambio_usd", "cambio_cny", "impostos_pct", "taxa_pagamento_pct", "margem_pct"]) {
      const n = lerNumero(dados[nome], { pontoDecimal: true });
      if (n !== null && !Number.isNaN(n)) dados[nome] = String(n);  // inválido segue como está e o servidor aponta o erro
    }
    try {
      const salvo = await api("/api/admin/ajustes", { method: "PUT", headers: auth, body: JSON.stringify(dados) });
      mostrarErros(form, {});
      estado.loja.whatsapp = salvo.whatsapp;
      estado.loja.whatsapp_mensagem = salvo.whatsapp_mensagem;
      if (typeof salvo.chave_pix === "string") estado.loja.chave_pix = salvo.chave_pix;
      atualizarWhatsAppFlutuante();
      avisar("Configurações salvas ✔");
    } catch (err) {
      if (err.status === 401) return sairDoPainel(true);
      mostrarErros(form, err.campos);
      avisar(err.message);
    }
  });
  return form;
}

function formularioNovoProduto(auth) {
  const previa = h("div", { class: "galeria-admin" });
  let urlsPrevia = [];
  const inputFoto = h("input", { type: "file", name: "foto", id: "campo-foto", accept: "image/jpeg,image/png,image/webp", multiple: true,
    onchange: (e) => {
      urlsPrevia.forEach((u) => URL.revokeObjectURL(u));
      urlsPrevia = [...e.target.files].map((a) => URL.createObjectURL(a));
      trocar(previa, urlsPrevia.map((u, k) => h("figure", {}, h("img", { src: u, alt: `Prévia da foto ${k + 1}`, width: 120, height: 120 }))));
    } });
  const form = h("form", { class: "painel", novalidate: true },
    h("h2", {}, "Cadastrar produto"),
    h("p", { class: "parcelado" }, "Preencha os dados do produto que você importou. Preços em reais (ex.: 49,90). Depois de cadastrar você pode adicionar opções como cor e voltagem."),
    h("div", { class: "grade-form" },
      campo("nome", "Nome do produto", { required: true, maxlength: 120, placeholder: "Ex.: Fone Bluetooth com estojo" }, "c6"),
      seletorCategoria(""),
      campo("icone", "Emoji (se não houver foto)", { maxlength: 8, placeholder: "📦" }, "c3"),
      camposPreco(),
      campo("estoque", "Estoque (unidades)", { type: "number", min: 0, value: 0, required: true }, "c2"),
      h("div", { class: "campo c6", "data-campo": "descricao" },
        h("label", { for: "campo-descricao" }, "Descrição"),
        h("textarea", { id: "campo-descricao", name: "descricao", rows: 4, maxlength: 2000, class: "campo-texto", "aria-describedby": "erro-descricao",
          placeholder: "Principais características, medidas, voltagem, o que vem na caixa…" }),
        h("span", { class: "msg-erro", id: "erro-descricao" })),
      h("div", { class: "campo c6", "data-campo": "foto" },
        h("label", { for: "campo-foto" }, "Fotos (JPG, PNG ou WEBP; a primeira é a capa — reduzimos antes de enviar)"), inputFoto, previa, h("span", { class: "msg-erro" })),
      h("label", { class: "c6 caixa" }, h("input", { type: "checkbox", name: "destaque" }), " Mostrar nos destaques da página inicial"),
    ),
    h("div", { class: "alerta", hidden: true, id: "erro-novo" }),
    h("button", { class: "botao grande espaco-topo", type: "submit" }, "Cadastrar produto"),
  );
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = form.elements;
    const erro = $("#erro-novo", form);
    const botao = form.querySelector("button[type=submit]");
    erro.hidden = true;
    const [precos, errosPreco] = valoresPreco(f);
    if (Object.keys(errosPreco).length) return mostrarErros(form, errosPreco);
    botao.disabled = true;
    try {
      const produto = await api("/api/admin/produtos", { method: "POST", headers: auth, body: JSON.stringify({
        nome: f.nome.value, categoria: f.categoria.value, icone: f.icone.value || "📦", descricao: f.descricao.value,
        estoque: parseInt(f.estoque.value, 10), destaque: f.destaque.checked, ...precos }) });
      for (const arquivo of inputFoto.files) {
        try { await enviarFoto(auth, produto.slug, arquivo); }
        catch (err) { avisar(`Produto criado, mas uma foto falhou: ${err.message}`); break; }
      }
      urlsPrevia.forEach((u) => URL.revokeObjectURL(u));
      avisar("Produto cadastrado ✔");
      navegar(`/admin/produto/${produto.slug}`);
    } catch (err) {
      if (err.status === 401) return sairDoPainel(true);
      mostrarErros(form, err.campos);
      erro.textContent = err.message;
      erro.hidden = false;
    } finally {
      botao.disabled = false;
    }
  });
  return form;
}

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
  rotear({ esqueleto: true });
}

iniciar();
