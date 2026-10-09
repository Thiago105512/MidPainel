/* Tipiti — loja virtual. JavaScript puro, sem dependências. */
"use strict";

const estado = { loja: null, categorias: [], carrinho: [] };
const CHAVE_CARRINHO = "tipiti:carrinho";
const CHAVE_ADMIN = "tipiti:admin";

// ------------------------------------------------------------- utilidades

const brl = (centavos) => (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const $ = (sel, raiz = document) => raiz.querySelector(sel);

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

/** replaceChildren que aceita listas aninhadas e ignora vazios. */
function trocar(el, ...filhos) {
  el.replaceChildren(...filhos.flat(Infinity).filter((f) => f !== null && f !== undefined && f !== false)
    .map((f) => (f instanceof Node ? f : document.createTextNode(String(f)))));
}

async function api(caminho, opcoes = {}) {
  const resp = await fetch(caminho, {
    ...opcoes,
    headers: { "Content-Type": "application/json", ...(opcoes.headers || {}) },
  });
  let dados = null;
  try { dados = await resp.json(); } catch (_) { /* corpo vazio */ }
  if (!resp.ok) {
    const erro = new Error((dados && dados.erro) || "Não foi possível completar a ação.");
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

function lerArmazenado(chave, padrao, armazenamento = localStorage) {
  try { return JSON.parse(armazenamento.getItem(chave)) ?? padrao; } catch (_) { return padrao; }
}
function gravar(chave, valor, armazenamento = localStorage) {
  try { armazenamento.setItem(chave, JSON.stringify(valor)); } catch (_) { /* modo privado */ }
}

// ------------------------------------------------------------- carrinho

function salvarCarrinho() {
  gravar(CHAVE_CARRINHO, estado.carrinho);
  const total = estado.carrinho.reduce((s, i) => s + i.quantidade, 0);
  $("#contador-carrinho").textContent = total;
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

// ------------------------------------------------------------- WhatsApp

function linkWhatsApp(texto) {
  const numero = estado.loja && estado.loja.whatsapp;
  return numero ? `https://wa.me/${numero}?text=${encodeURIComponent(texto)}` : null;
}

/** `texto` pode ser uma função, para a mensagem refletir o estado na hora do clique (ex.: quantidade). */
function botaoWhatsApp(texto, rotulo, classe = "botao whatsapp") {
  const gerar = typeof texto === "function" ? texto : () => texto;
  const url = linkWhatsApp(gerar());
  return url ? h("a", { class: classe, href: url, target: "_blank", rel: "noopener",
    onclick: (e) => { e.currentTarget.href = linkWhatsApp(gerar()); } }, "💬 ", rotulo) : null;
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

function textoParcelas(centavos) {
  const n = Math.max(1, Math.min(estado.loja.parcelas_max, Math.floor(centavos / estado.loja.parcela_minima)));
  return n > 1 ? `ou ${n}x de ${brl(Math.ceil(centavos / n))} sem juros` : "";
}

function cartaoProduto(p) {
  const off = p.preco_de_centavos && p.preco_de_centavos > p.preco_centavos
    ? Math.round((1 - p.preco_centavos / p.preco_de_centavos) * 100) : 0;
  return h("a", { class: "cartao-produto", href: `/produto/${p.slug}` },
    off ? h("span", { class: "selo" }, `-${off}%`) : null,
    h("img", { src: p.imagem, alt: "", loading: "lazy", width: 400, height: 400 }),
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

function gradeProdutos(lista) {
  if (!lista.length) {
    return h("div", { class: "vazio" }, h("div", { class: "ico" }, "🔎"), h("p", {}, "Nenhum produto encontrado."));
  }
  return h("div", { class: "grade-produtos" }, lista.map(cartaoProduto));
}

function campo(nome, rotulo, attrs = {}, classe = "c3") {
  const id = `campo-${nome}`;
  return h("div", { class: `campo ${classe}`, "data-campo": nome },
    h("label", { for: id }, rotulo),
    h("input", { id, name: nome, type: "text", ...attrs }),
    h("span", { class: "msg-erro", id: `erro-${nome}` }),
  );
}

function mostrarErros(form, campos, focar = true) {
  form.querySelectorAll(".campo").forEach((c) => c.classList.remove("com-erro"));
  form.querySelectorAll(".msg-erro").forEach((m) => (m.textContent = ""));
  let primeiro = null;
  for (const [nome, msg] of Object.entries(campos || {})) {
    const c = form.querySelector(`[data-campo="${nome}"]`);
    if (!c || typeof msg !== "string") continue;
    c.classList.add("com-erro");
    $(".msg-erro", c).textContent = msg;
    primeiro = primeiro || c.querySelector("input, select");
  }
  if (primeiro && focar) primeiro.focus();
}

function simuladorFrete(obterSubtotal) {
  const saida = h("div", { class: "resultado-frete", "aria-live": "polite" });
  const input = h("input", { type: "text", inputmode: "numeric", placeholder: "00000-000", "aria-label": "CEP",
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
    h("b", {}, "🚚 Calcular frete e prazo"), form, saida,
    h("a", { href: "https://buscacepinter.correios.com.br/", target: "_blank", rel: "noopener", class: "parcelado" }, "Não sei meu CEP"));
}

// ------------------------------------------------------------- páginas

async function paginaInicial(main) {
  const l = estado.loja;
  document.title = "Tipiti — importados com entrega rápida no Norte";
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
      h("div", { class: "secao-cabecalho" }, h("h2", {}, "Destaques da semana")),
      h("div", { class: "carregando" }, "Carregando…")),
    h("section", { class: "secao" },
      h("h2", {}, "Novidades"), h("div", { class: "carregando" }, "Carregando…")),
  );
  const [destaques, novidades] = await Promise.all([
    api("/api/produtos?destaque=1&limite=8"), api("/api/produtos?ordem=novidades&limite=8"),
  ]);
  const secoes = main.querySelectorAll(".secao");
  secoes[1].querySelector(".carregando").replaceWith(gradeProdutos(destaques));
  secoes[2].querySelector(".carregando").replaceWith(gradeProdutos(novidades));
}

function seletorOrdem(atual, aoMudar) {
  const opcoes = { relevancia: "Mais relevantes", menor_preco: "Menor preço", maior_preco: "Maior preço", novidades: "Novidades", nome: "Nome (A–Z)" };
  return h("label", {}, "Ordenar: ",
    h("select", { onchange: (e) => aoMudar(e.target.value) },
      Object.entries(opcoes).map(([v, t]) => h("option", { value: v, selected: v === atual }, t))));
}

async function paginaCategoria(main, slug) {
  const ordem = new URLSearchParams(location.search).get("ordem") || "relevancia";
  const [cat, produtos] = await Promise.all([
    api(`/api/categorias/${slug}`),
    api(`/api/produtos?categoria=${slug}&ordem=${ordem}`),
  ]);
  document.title = `${cat.nome} | Tipiti`;
  trocar(main, h("div", { class: "caminho" }, h("a", { href: "/" }, "Início"), " › ", cat.nome),
    h("h1", {}, `${cat.icone} ${cat.nome}`),
    h("p", { class: "parcelado" }, cat.descricao),
    h("div", { class: "barra-filtros" },
      h("span", {}, `${produtos.length} produto(s)`),
      seletorOrdem(ordem, (o) => navegar(`/categoria/${slug}?ordem=${o}`, true))),
    gradeProdutos(produtos),
  );
}

async function paginaBusca(main) {
  const params = new URLSearchParams(location.search);
  const q = params.get("q") || "";
  const ordem = params.get("ordem") || "relevancia";
  $("#campo-busca").value = q;
  const produtos = await api(`/api/produtos?q=${encodeURIComponent(q)}&ordem=${ordem}`);
  document.title = `Busca: ${q} | Tipiti`;
  trocar(main, h("h1", {}, q ? `Resultados para “${q}”` : "Todos os produtos"),
    h("div", { class: "barra-filtros" },
      h("span", {}, `${produtos.length} produto(s)`),
      seletorOrdem(ordem, (o) => navegar(`/busca?q=${encodeURIComponent(q)}&ordem=${o}`, true))),
    gradeProdutos(produtos),
  );
}

async function paginaProduto(main, slug) {
  const p = await api(`/api/produtos/${slug}`);
  document.title = `${p.nome} | Tipiti`;
  const opcoes = p.variacoes;
  let escolhida = opcoes.length === 1 ? opcoes[0] : null;
  let qtd = 1;
  const precoAtual = () => (escolhida && escolhida.preco_centavos !== null ? escolhida.preco_centavos : p.preco_centavos);
  const estoqueAtual = () => (opcoes.length ? (escolhida ? escolhida.estoque : p.estoque) : p.estoque);

  // galeria
  const imagens = p.fotos.length ? p.fotos.map((f) => f.url) : [p.imagem];
  const principal = h("img", { src: imagens[0], alt: p.nome, width: 400, height: 400, class: "foto-principal" });
  const miniaturas = imagens.length > 1 ? h("div", { class: "miniaturas" }, imagens.map((url, k) =>
    h("button", { type: "button", class: "miniatura-botao", "aria-label": `Foto ${k + 1}`, "aria-current": String(k === 0),
      onclick: (e) => {
        principal.src = url;
        e.currentTarget.parentElement.querySelectorAll("button").forEach((b) => b.setAttribute("aria-current", "false"));
        e.currentTarget.setAttribute("aria-current", "true");
      } }, h("img", { src: url, alt: "" })))) : null;

  const blocoPreco = h("div", {});
  const blocoCompra = h("div", {});
  const inputQtd = h("input", { type: "number", min: 1, value: 1, "aria-label": "Quantidade",
    onchange: (e) => { qtd = Math.max(1, Math.min(estoqueAtual() || 1, parseInt(e.target.value, 10) || 1)); e.target.value = qtd; } });
  const mudar = (d) => { qtd = Math.max(1, Math.min(estoqueAtual() || 1, qtd + d)); inputQtd.value = qtd; };
  const aviso = h("p", { class: "esgotado", hidden: true }, "Escolha uma opção acima.");

  const exigirOpcao = () => {
    if (opcoes.length && !escolhida) { aviso.hidden = false; return false; }
    return true;
  };
  const adicionar = (ir) => {
    if (!exigirOpcao()) return;
    adicionarAoCarrinho(p.slug, qtd, escolhida ? escolhida.id : null);
    if (ir) navegar("/carrinho"); else avisar("Produto adicionado ao carrinho ✔");
  };
  const textoZap = () => `Olá! Tenho interesse neste produto da Tipiti:\n${p.nome}${escolhida ? ` — ${escolhida.nome}` : ""}\nQuantidade: ${qtd}\n${location.href}`;

  const atualizar = () => {
    const preco = precoAtual();
    const estoque = estoqueAtual();
    const temOferta = !escolhida?.preco_centavos && p.preco_de_centavos && p.preco_de_centavos > preco;
    trocar(blocoPreco,
      temOferta ? h("div", { class: "preco-de" }, `De ${brl(p.preco_de_centavos)}`) : null,
      h("div", { class: "preco" }, brl(preco)),
      h("div", { class: "preco-pix" }, `${brl(precoPix(preco))} no Pix (${estado.loja.desconto_pix_pct}% off)`),
      h("div", { class: "parcelado" }, textoParcelas(preco)));
    qtd = Math.max(1, Math.min(qtd, estoque || 1));
    inputQtd.value = qtd;
    inputQtd.max = Math.max(1, estoque);
    const esgotada = escolhida && escolhida.estoque === 0;
    trocar(blocoCompra,
      p.estoque > 0 && !esgotada
        ? h("div", { class: "compra" },
            h("div", { class: "quantidade" },
              h("button", { type: "button", "aria-label": "Diminuir", onclick: () => mudar(-1) }, "−"), inputQtd,
              h("button", { type: "button", "aria-label": "Aumentar", onclick: () => mudar(1) }, "+")),
            h("button", { class: "botao", onclick: () => adicionar(false) }, "Adicionar ao carrinho"),
            h("button", { class: "botao secundario", onclick: () => adicionar(true) }, "Comprar agora"))
        : h("p", { class: "esgotado" }, esgotada ? "Esta opção está esgotada. Escolha outra." : "Produto esgotado no momento."),
      aviso,
      estoque > 0 && estoque <= 5 && (escolhida || !opcoes.length) ? h("p", { class: "esgotado" }, `Últimas ${estoque} unidades!`) : null,
      botaoWhatsApp(textoZap, "Pedir pelo WhatsApp", "botao whatsapp"));
  };

  const seletorOpcoes = opcoes.length ? h("div", { class: "opcoes-produto", role: "radiogroup", "aria-label": "Opções" },
    h("p", { class: "rotulo-opcoes" }, "Opção: ", h("b", {}, escolhida ? escolhida.nome : "escolha abaixo")),
    h("div", { class: "botoes-opcoes" }, opcoes.map((v) => h("button", {
      type: "button", role: "radio", class: `opcao-produto${v.estoque === 0 ? " opcao-esgotada" : ""}`,
      "aria-checked": String(escolhida === v), title: v.estoque === 0 ? "Esgotado" : "",
      onclick: (e) => {
        escolhida = v;
        aviso.hidden = true;
        const grupo = e.currentTarget.closest(".opcoes-produto");
        grupo.querySelectorAll(".opcao-produto").forEach((b) => b.setAttribute("aria-checked", "false"));
        e.currentTarget.setAttribute("aria-checked", "true");
        $(".rotulo-opcoes b", grupo).textContent = v.nome;
        atualizar();
      } }, v.nome)))) : null;

  atualizar();
  trocar(main, h("div", { class: "caminho" }, h("a", { href: "/" }, "Início"), " › ",
      h("a", { href: `/categoria/${p.categoria.slug}` }, p.categoria.nome), " › ", p.nome),
    h("article", { class: "produto" },
      h("div", { class: "galeria" }, principal, miniaturas),
      h("div", {},
        h("h1", {}, p.nome),
        blocoPreco,
        seletorOpcoes,
        blocoCompra,
        h("p", { class: "selo-importado" }, "📦 Produto importado · em estoque no Brasil · garantia de 90 dias"),
        h("p", { class: "descricao" }, p.descricao),
        simuladorFrete(() => precoAtual() * qtd),
      ),
    ),
    p.relacionados.length ? h("section", { class: "secao" }, h("h2", {}, "Você também pode gostar"), gradeProdutos(p.relacionados)) : null,
  );
}

function blocoResumo(c, { comCep, aoMudarCep } = {}) {
  const linhas = [
    h("div", { class: "linha-total" }, h("span", {}, "Subtotal"), h("span", {}, brl(c.subtotal_centavos))),
  ];
  if (c.desconto_centavos) {
    linhas.push(h("div", { class: "linha-total desconto" }, h("span", {}, `Desconto Pix (${estado.loja.desconto_pix_pct}%)`), h("span", {}, `− ${brl(c.desconto_centavos)}`)));
  }
  linhas.push(h("div", { class: "linha-total" }, h("span", {}, "Frete"),
    h("span", {}, c.frete ? (c.frete.gratis ? "Grátis" : brl(c.frete.valor_centavos)) : "Informe o CEP")));
  if (c.frete) linhas.push(h("div", { class: "parcelado" }, `${c.frete.zona_nome} · até ${c.frete.prazo_dias} dias úteis`));
  linhas.push(h("div", { class: "linha-total total" }, h("span", {}, "Total"), h("span", {}, brl(c.total_centavos))));

  const faltam = c.falta_para_frete_gratis;
  const pct = Math.min(100, Math.round((c.subtotal_centavos / estado.loja.frete_gratis_a_partir) * 100));
  const barra = (!c.frete || c.frete.regiao_norte) ? h("div", { class: "barra-frete" },
    faltam > 0 ? [`Faltam `, h("b", {}, brl(faltam)), ` para frete grátis na Região Norte`] : "🎉 Você ganhou frete grátis na Região Norte!",
    h("div", { class: "barra-progresso" }, h("span", { style: `width:${pct}%` }))) : null;

  let cep = null;
  if (comCep) {
    const input = h("input", { type: "text", inputmode: "numeric", placeholder: "CEP", "aria-label": "CEP", value: (c.frete && c.frete.cep) || lerArmazenado("tipiti:cep", ""),
      oninput: (e) => (e.target.value = mascaraCep(e.target.value)) });
    cep = h("form", { class: "simulador", style: "display:flex;gap:8px", onsubmit: (e) => { e.preventDefault(); aoMudarCep(input.value); } },
      input, h("button", { class: "botao secundario", type: "submit" }, "OK"));
  }
  return [barra, cep, ...linhas];
}

async function paginaCarrinho(main) {
  document.title = "Carrinho | Tipiti";
  if (!estado.carrinho.length) {
    trocar(main, h("div", { class: "vazio" }, h("div", { class: "ico" }, "🛒"),
      h("h1", {}, "Seu carrinho está vazio"), h("p", {}, "Que tal dar uma olhada nos destaques?"),
      h("a", { class: "botao", href: "/" }, "Continuar comprando")));
    return;
  }
  let cep = lerArmazenado("tipiti:cep", "");
  let erroCep = "";
  let cotacao;
  try {
    cotacao = await api("/api/carrinho/cotacao", { method: "POST", body: JSON.stringify({ itens: estado.carrinho, cep: cep || null }) });
  } catch (err) {
    if (err.campos && err.campos.cep) {
      gravar("tipiti:cep", "");
      erroCep = err.campos.cep;
      cotacao = await api("/api/carrinho/cotacao", { method: "POST", body: JSON.stringify({ itens: estado.carrinho }) });
    } else throw err;
  }
  // remove do carrinho local o que deixou de existir
  const existentes = new Set(cotacao.itens.filter((i) => i.produto_id).map((i) => i.chave));
  if (existentes.size !== estado.carrinho.length) {
    estado.carrinho = estado.carrinho.filter((i) => existentes.has(chaveItem(i.slug, i.variacao)));
    salvarCarrinho();
  }
  const validos = cotacao.itens.filter((i) => i.produto_id);
  const textoZap = `Olá! Quero finalizar este pedido na Tipiti:\n${validos.map((i) => `• ${i.quantidade}× ${nomeComOpcao(i)} — ${brl(i.total_centavos)}`).join("\n")}\nSubtotal: ${brl(cotacao.subtotal_centavos)}${cotacao.frete ? `\nCEP: ${cotacao.frete.cep}` : ""}`;

  trocar(main, h("h1", {}, "Meu carrinho"),
    h("div", { class: "layout-carrinho" },
      h("div", { class: "painel" }, cotacao.itens.filter((i) => i.produto_id).map((i) =>
        h("div", { class: "linha-item" },
          h("img", { src: i.imagem, alt: "" }),
          h("div", {},
            h("a", { class: "nome", href: `/produto/${i.slug}` }, i.nome),
            i.variacao_nome ? h("div", {}, "Opção: ", h("b", {}, i.variacao_nome)) : null,
            h("div", { class: "parcelado" }, `${brl(i.preco_unit_centavos)} cada`),
            i.erro ? h("div", { class: "esgotado" }, i.erro) : null,
            h("div", { class: "acoes" },
              h("div", { class: "quantidade" },
                h("button", { type: "button", "aria-label": "Diminuir", onclick: () => { alterarQuantidade(i.chave, i.quantidade - 1); rotear(); } }, "−"),
                h("input", { type: "number", value: i.quantidade, min: 1, "aria-label": "Quantidade",
                  onchange: (e) => { alterarQuantidade(i.chave, parseInt(e.target.value, 10) || 0); rotear(); } }),
                h("button", { type: "button", "aria-label": "Aumentar", onclick: () => { alterarQuantidade(i.chave, i.quantidade + 1); rotear(); } }, "+")),
              h("button", { class: "link-botao", onclick: () => { alterarQuantidade(i.chave, 0); rotear(); } }, "Remover"))),
          h("b", {}, brl(i.total_centavos))))),
      h("aside", { class: "painel resumo" },
        h("h2", {}, "Resumo"),
        h("p", { class: "parcelado" }, "Valores com Pix. No cartão, o desconto não se aplica."),
        erroCep ? h("div", { class: "alerta" }, erroCep) : null,
        blocoResumo(cotacao, { comCep: true, aoMudarCep: (v) => { gravar("tipiti:cep", mascaraCep(v)); rotear(); } }),
        !cotacao.valido ? h("div", { class: "alerta" }, "Ajuste os itens sem estoque para continuar.") : null,
        h("button", { class: "botao grande", disabled: !cotacao.valido, onclick: () => navegar("/checkout") }, "Finalizar compra"),
        botaoWhatsApp(textoZap, "Prefiro finalizar pelo WhatsApp", "botao whatsapp grande espaco-topo"),
        h("a", { href: "/", style: "display:block;text-align:center;margin-top:12px" }, "Continuar comprando"),
      ),
    ),
  );
}

const UFS = ["AM", "PA", "RR", "AP", "AC", "RO", "TO", "AL", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PB", "PE", "PI", "PR", "RJ", "RN", "RS", "SC", "SE", "SP"];

async function paginaCheckout(main) {
  document.title = "Finalizar compra | Tipiti";
  if (!estado.carrinho.length) return navegar("/carrinho", true);

  const rascunho = lerArmazenado("tipiti:checkout", {}, sessionStorage);
  const resumo = h("aside", { class: "painel resumo" }, h("h2", {}, "Resumo do pedido"), h("div", { class: "carregando" }, "Calculando…"));
  const selParcelas = h("select", { name: "parcelas", class: "campo-select", "aria-label": "Parcelas" });
  const blocoParcelas = h("div", { class: "campo", "data-campo": "parcelas", hidden: true },
    h("label", {}, "Parcelas"), selParcelas, h("span", { class: "msg-erro" }));

  const form = h("form", { class: "painel", novalidate: true },
    h("fieldset", {}, h("legend", {}, "1. Seus dados"),
      h("div", { class: "grade-form" },
        campo("nome", "Nome completo", { autocomplete: "name", required: true }, "c6"),
        campo("email", "E-mail", { type: "email", autocomplete: "email", required: true }, "c3"),
        campo("telefone", "Celular com DDD", { type: "tel", autocomplete: "tel", inputmode: "numeric", placeholder: "(92) 90000-0000", required: true }, "c3"),
        campo("cpf", "CPF", { inputmode: "numeric", placeholder: "000.000.000-00", required: true }, "c3"))),
    h("fieldset", {}, h("legend", {}, "2. Endereço de entrega"),
      h("div", { class: "grade-form" },
        campo("cep", "CEP", { inputmode: "numeric", autocomplete: "postal-code", placeholder: "00000-000", required: true }, "c2"),
        campo("endereco", "Rua / Avenida", { autocomplete: "address-line1", required: true }, "c4"),
        campo("numero", "Número", { required: true }, "c2"),
        campo("complemento", "Complemento", { autocomplete: "address-line2" }, "c4"),
        campo("bairro", "Bairro", { required: true }, "c2"),
        campo("cidade", "Cidade", { autocomplete: "address-level2", required: true }, "c3"),
        h("div", { class: "campo c1", "data-campo": "uf" },
          h("label", { for: "campo-uf" }, "UF"),
          h("select", { id: "campo-uf", name: "uf", class: "campo-select", autocomplete: "address-level1" },
            h("option", { value: "" }, "—"), UFS.map((u) => h("option", { value: u }, u))),
          h("span", { class: "msg-erro" })))),
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
    h("div", { class: "alerta", id: "erro-geral", hidden: true }),
    h("button", { class: "botao grande", type: "submit" }, "Confirmar pedido"),
    h("p", { class: "parcelado", style: "text-align:center" }, "Ao confirmar, você concorda com a política de trocas da Tipiti."),
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
  form.addEventListener("input", () => gravar("tipiti:checkout", { ...dadosForm(), cpf: "" }, sessionStorage));

  let ultimaCotacao = null;
  async function atualizarResumo() {
    const d = dadosForm();
    const cepValido = (d.cep || "").replace(/\D/g, "").length === 8;
    try {
      ultimaCotacao = await api("/api/carrinho/cotacao", { method: "POST",
        body: JSON.stringify({ itens: estado.carrinho, cep: cepValido ? d.cep : null, pagamento: d.pagamento }) });
    } catch (err) {
      trocar(resumo, h("h2", {}, "Resumo do pedido"), h("div", { class: "alerta" }, err.message));
      return;
    }
    const c = ultimaCotacao;
    trocar(resumo, h("h2", {}, "Resumo do pedido"),
      c.itens.filter((i) => i.produto_id).map((i) => h("div", { class: "linha-total" },
        h("span", {}, `${i.quantidade}× ${nomeComOpcao(i)}`), h("span", {}, brl(i.total_centavos)))),
      h("hr", { style: "border:0;border-top:1px solid var(--linha)" }),
      blocoResumo(c),
      !c.valido ? h("div", { class: "alerta" }, "Há itens sem estoque. ", h("a", { href: "/carrinho" }, "Revise o carrinho.")) : null,
    );
    blocoParcelas.hidden = d.pagamento !== "cartao";
    const atual = parseInt(selParcelas.value, 10) || 1;
    trocar(selParcelas, ...Array.from({ length: c.parcelas_max }, (_, k) => k + 1).map((n) =>
      h("option", { value: n, selected: n === Math.min(atual, c.parcelas_max) },
        n === 1 ? `1x de ${brl(c.total_centavos)} (à vista)` : `${n}x de ${brl(Math.ceil(c.total_centavos / n))} sem juros`)));
  }

  let ultimoCep = "";
  async function buscarCep() {
    const d = form.elements.cep.value.replace(/\D/g, "");
    if (d.length !== 8 || d === ultimoCep) return;
    ultimoCep = d;
    gravar("tipiti:cep", mascaraCep(d));
    atualizarResumo();
    try {
      const resp = await fetch(`https://viacep.com.br/ws/${d}/json/`);
      const e = await resp.json();
      if (e.erro) return;
      if (e.logradouro) form.elements.endereco.value = e.logradouro;
      if (e.bairro) form.elements.bairro.value = e.bairro;
      if (e.localidade) form.elements.cidade.value = e.localidade;
      if (e.uf) form.elements.uf.value = e.uf;
      form.elements.numero.focus();
    } catch (_) { /* preenchimento manual */ }
  }
  form.elements.cep.addEventListener("change", buscarCep);
  form.elements.cep.addEventListener("keyup", () => { if (form.elements.cep.value.length === 9) buscarCep(); });
  form.querySelectorAll("input[name=pagamento]").forEach((r) => r.addEventListener("change", atualizarResumo));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const botao = form.querySelector("button[type=submit]");
    const erroGeral = $("#erro-geral", form);
    erroGeral.hidden = true;
    botao.disabled = true;
    botao.textContent = "Enviando pedido…";
    try {
      const pedido = await api("/api/pedidos", { method: "POST", body: JSON.stringify({ ...dadosForm(), itens: estado.carrinho }) });
      estado.carrinho = [];
      salvarCarrinho();
      try { sessionStorage.removeItem("tipiti:checkout"); } catch (_) { /* ignora */ }
      navegar(`/pedido/${pedido.codigo}`);
    } catch (err) {
      mostrarErros(form, err.campos);
      erroGeral.textContent = err.message;
      erroGeral.hidden = false;
      if (err.campos && err.campos.itens) atualizarResumo();
      botao.disabled = false;
      botao.textContent = "Confirmar pedido";
    }
  });

  trocar(main, h("h1", {}, "Finalizar compra"), h("div", { class: "layout-carrinho" }, form, resumo));
  atualizarResumo();
}

async function paginaPedido(main, codigo) {
  const p = await api(`/api/pedidos/${encodeURIComponent(codigo)}`);
  document.title = `Pedido ${p.codigo} | Tipiti`;
  const instrucoes = {
    pix: "Pagamento via Pix: o QR Code será exibido aqui assim que o meio de pagamento for integrado.",
    cartao: `Cartão de crédito em ${p.parcelas}x: a cobrança será processada após a integração com o meio de pagamento.`,
    boleto: "Boleto: o documento para pagamento será disponibilizado aqui após a integração com o meio de pagamento.",
  };
  trocar(main, h("div", { class: "confirmacao" },
      h("div", { style: "font-size:3rem" }, "🎉"),
      h("h1", {}, `Obrigado, ${p.primeiro_nome}!`),
      h("p", {}, "Seu pedido foi registrado com o código"),
      h("p", {}, h("span", { class: "codigo" }, p.codigo)),
      h("p", {}, "Status: ", h("b", {}, p.status_nome)),
      p.status === "aguardando_pagamento" ? h("div", { class: "info-box" }, instrucoes[p.pagamento]) : null,
      h("div", { class: "painel", style: "text-align:left;margin-top:20px" },
        h("h2", {}, "Itens"),
        p.itens.map((i) => h("div", { class: "linha-total" }, h("span", {}, `${i.quantidade}× ${nomeComOpcao(i)}`), h("span", {}, brl(i.preco_unit_centavos * i.quantidade)))),
        h("hr", { style: "border:0;border-top:1px solid var(--linha)" }),
        h("div", { class: "linha-total" }, h("span", {}, "Subtotal"), h("span", {}, brl(p.subtotal_centavos))),
        p.desconto_centavos ? h("div", { class: "linha-total desconto" }, h("span", {}, "Desconto Pix"), h("span", {}, `− ${brl(p.desconto_centavos)}`)) : null,
        h("div", { class: "linha-total" }, h("span", {}, "Frete"), h("span", {}, p.frete_centavos ? brl(p.frete_centavos) : "Grátis")),
        h("div", { class: "linha-total total" }, h("span", {}, "Total"), h("span", {}, brl(p.total_centavos))),
        h("p", { class: "parcelado" }, `Entrega em ${p.destino} · prazo de até ${p.prazo_dias} dias úteis após a confirmação do pagamento.`)),
      botaoWhatsApp(`Olá! Fiz o pedido ${p.codigo} no site da Tipiti (total ${brl(p.total_centavos)}, ${p.pagamento_nome}).`,
        "Enviar meu pedido no WhatsApp", "botao whatsapp espaco-topo"),
      h("p", {}, "Guarde o código para acompanhar o pedido. Dúvidas: ", h("a", { href: `mailto:${estado.loja.email}` }, estado.loja.email)),
      h("a", { class: "botao", href: "/" }, "Voltar à loja"),
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

/** "49,90", "49.90" ou "1.234,56" -> centavos; vazio -> null. */
function reais(v) {
  let t = String(v ?? "").trim();
  if (!t) return null;
  if (t.includes(",")) t = t.replace(/\./g, "").replace(",", ".");
  const n = Math.round(parseFloat(t) * 100);
  return Number.isFinite(n) ? n : NaN;
}
const textoReais = (c) => (c === null || c === undefined ? "" : (c / 100).toFixed(2).replace(".", ","));

function sairDoPainel() {
  try { sessionStorage.removeItem(CHAVE_ADMIN); } catch (_) { /* ignora */ }
  navegar("/admin", true);
}

/** Mostra o login se não houver token; senão devolve o cabeçalho de autorização. */
function autenticacaoAdmin(main) {
  const token = lerArmazenado(CHAVE_ADMIN, "", sessionStorage);
  if (token) return { Authorization: `Bearer ${token}` };
  const input = h("input", { type: "password", "aria-label": "Token de acesso", placeholder: "Token de acesso", autocomplete: "off" });
  trocar(main, h("div", { class: "painel", style: "max-width:420px;margin:40px auto" },
    h("h1", {}, "Painel da loja"),
    h("form", { onsubmit: (e) => { e.preventDefault(); gravar(CHAVE_ADMIN, input.value.trim(), sessionStorage); rotear(); } },
      input, h("button", { class: "botao grande", style: "margin-top:12px" }, "Entrar"))));
  return null;
}

function cabecalhoAdmin(abaAtual) {
  const abas = [["pedidos", "Pedidos"], ["produtos", "Produtos"], ["novo", "+ Novo produto"], ["calculadora", "Calculadora"], ["configuracoes", "Configurações"]];
  return [
    h("div", { class: "secao-cabecalho" }, h("h1", {}, "Painel da loja"), h("button", { class: "link-botao", onclick: sairDoPainel }, "Sair")),
    h("div", { class: "abas", role: "tablist" }, abas.map(([id, rotulo]) =>
      h("button", { class: "botao secundario", role: "tab", "aria-selected": String(abaAtual === id),
        onclick: () => { gravar("tipiti:admin-aba", id, sessionStorage); navegar("/admin"); } }, rotulo))),
  ];
}

async function comTratamento(conteudo, fn) {
  try { await fn(); } catch (err) {
    if (err.status === 401) return sairDoPainel();
    trocar(conteudo, h("div", { class: "alerta" }, err.message));
  }
}

async function paginaAdmin(main) {
  document.title = "Painel | Tipiti";
  const auth = autenticacaoAdmin(main);
  if (!auth) return;
  const aba = lerArmazenado("tipiti:admin-aba", "pedidos", sessionStorage);
  const conteudo = h("div", {}, h("div", { class: "carregando" }, "Carregando…"));
  trocar(main, cabecalhoAdmin(aba), conteudo);
  await comTratamento(conteudo, async () => {
    if (aba === "novo") trocar(conteudo, formularioNovoProduto(auth));
    else if (aba === "produtos") trocar(conteudo, await listaProdutosAdmin(auth));
    else if (aba === "calculadora") {
      const aj = await api("/api/admin/ajustes", { headers: auth });
      trocar(conteudo, h("div", { class: "painel" }, h("h2", {}, "Calculadora de preço do importado"),
        h("p", { class: "parcelado" }, "Descubra o custo real de cada unidade no Brasil e o preço de venda para a margem que você quer."),
        calculadora(auth, aj)));
    } else if (aba === "configuracoes") trocar(conteudo, await formularioAjustes(auth));
    else trocar(conteudo, await painelPedidos(auth));
  });
}

function cartaoNumero(rotulo, valor, detalhe) {
  return h("div", { class: "cartao-numero" }, h("small", {}, rotulo), h("b", {}, valor), detalhe ? h("small", {}, detalhe) : null);
}

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
    resumo.estoque_baixo.length ? h("div", { class: "info-box", style: "margin-bottom:16px" },
      h("b", {}, "⚠️ Estoque baixo: "),
      resumo.estoque_baixo.map((p, k) => [k ? ", " : "", h("a", { href: `/admin/produto/${p.slug}` }, p.nome), ` (${p.estoque})`])) : null,
    pedidos.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin" },
      h("thead", {}, h("tr", {}, ["Pedido", "Cliente", "Entrega", "Itens", "Total", "Lucro", "Status"].map((t) => h("th", {}, t)))),
      h("tbody", {}, pedidos.map((p) => {
        const zap = `https://wa.me/55${p.cliente.telefone}?text=${encodeURIComponent(`Olá, ${p.cliente.nome.split(" ")[0]}! Aqui é da Tipiti, sobre o seu pedido ${p.codigo}.`)}`;
        return h("tr", {},
          h("td", {}, h("b", {}, p.codigo), h("div", { class: "parcelado" }, p.criado_em)),
          h("td", {}, p.cliente.nome, h("div", { class: "parcelado" }, p.cliente.email),
            h("div", { class: "parcelado" }, mascaraTelefone(p.cliente.telefone), " · ", h("a", { href: zap, target: "_blank", rel: "noopener" }, "WhatsApp"))),
          h("td", {}, `${p.entrega.endereco}, ${p.entrega.numero} ${p.entrega.complemento}`,
            h("div", { class: "parcelado" }, `${p.entrega.bairro} · ${p.entrega.cidade}/${p.entrega.uf} · ${mascaraCep(p.entrega.cep)}`),
            h("div", { class: "parcelado" }, p.zona_frete)),
          h("td", {}, p.itens.map((i) => h("div", {}, nomeItem(i)))),
          h("td", {}, brl(p.total_centavos), h("div", { class: "parcelado" }, `${p.pagamento_nome}${p.parcelas > 1 ? ` ${p.parcelas}x` : ""}`)),
          h("td", {}, p.lucro_centavos === null ? h("span", { class: "parcelado" }, "sem custo") : brl(p.lucro_centavos)),
          h("td", {}, h("select", { class: "campo-select", disabled: p.status === "cancelado", "aria-label": "Status",
            onchange: async (e) => {
              if (e.target.value === "cancelado" && !confirm("Cancelar o pedido e devolver os itens ao estoque?")) { e.target.value = p.status; return; }
              try { await api(`/api/admin/pedidos/${p.codigo}`, { method: "PATCH", headers: auth, body: JSON.stringify({ status: e.target.value }) }); avisar("Status atualizado ✔"); rotear(); }
              catch (err) { avisar(err.message); e.target.value = p.status; }
            } }, Object.entries(STATUS_PEDIDO).map(([v, t]) => h("option", { value: v, selected: v === p.status }, t)))));
      }))))
      : h("p", {}, "Nenhum pedido ainda."));
}

async function listaProdutosAdmin(auth) {
  const produtos = await api("/api/admin/produtos", { headers: auth });
  const margem = (p) => (p.custo_centavos ? `${Math.round(((p.preco_centavos - p.custo_centavos) / p.preco_centavos) * 100)}%` : "—");
  return h("div", { class: "rolagem" }, h("table", { class: "tabela-admin" },
    h("thead", {}, h("tr", {}, ["Produto", "Preço", "Custo", "Margem bruta", "Estoque", "Situação", ""].map((t) => h("th", {}, t)))),
    h("tbody", {}, produtos.map((p) => h("tr", {},
      h("td", {}, h("div", { class: "produto-admin" }, h("img", { src: p.imagem, alt: "", class: "miniatura" }),
        h("div", {}, h("a", { href: `/admin/produto/${p.slug}` }, p.nome),
          h("div", { class: "parcelado" }, p.categoria.nome, p.tem_variacoes ? " · com opções" : "")))),
      h("td", {}, brl(p.preco_centavos)),
      h("td", {}, p.custo_centavos ? brl(p.custo_centavos) : h("span", { class: "parcelado" }, "—")),
      h("td", {}, margem(p)),
      h("td", { class: p.estoque <= 3 ? "esgotado" : "" }, p.estoque),
      h("td", {}, p.ativo ? "No ar" : "Fora do ar", p.destaque ? " · ⭐" : ""),
      h("td", {}, h("a", { class: "botao secundario", href: `/admin/produto/${p.slug}` }, "Editar")))))));
}

async function paginaEditorProduto(main, slug) {
  document.title = "Editar produto | Tipiti";
  const auth = autenticacaoAdmin(main);
  if (!auth) return;
  const conteudo = h("div", {}, h("div", { class: "carregando" }, "Carregando…"));
  trocar(main, cabecalhoAdmin("produtos"), conteudo);
  await comTratamento(conteudo, async () => {
    const [p, aj] = await Promise.all([api(`/api/admin/produtos/${slug}`, { headers: auth }), api("/api/admin/ajustes", { headers: auth })]);
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
              await api(`/api/admin/produtos/${p.slug}`, { method: "PATCH", headers: auth, body: JSON.stringify({ preco_centavos: preco, custo_centavos: custo }) });
              avisar("Preço e custo aplicados ✔");
              rotear();
            } })))));
  });
}

function seletorCategoria(atual) {
  return h("div", { class: "campo c3", "data-campo": "categoria" },
    h("label", { for: "campo-categoria" }, "Categoria"),
    h("select", { id: "campo-categoria", name: "categoria", class: "campo-select" },
      h("option", { value: "" }, "Escolha…"), estado.categorias.map((c) => h("option", { value: c.slug, selected: c.slug === atual }, `${c.icone} ${c.nome}`))),
    h("span", { class: "msg-erro" }));
}

function camposPreco(p = {}) {
  return [
    campo("preco_centavos", "Preço de venda (R$)", { inputmode: "decimal", placeholder: "49,90", value: textoReais(p.preco_centavos) }, "c2"),
    campo("preco_de_centavos", "Preço \"de\" (R$, opcional)", { inputmode: "decimal", placeholder: "69,90", value: textoReais(p.preco_de_centavos) }, "c2"),
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
      campo("icone", "Ícone (se não houver foto)", { maxlength: 8, value: p.icone }, "c3"),
      camposPreco(p),
      campo("estoque", p.tem_variacoes ? "Estoque (soma das opções)" : "Estoque (unidades)",
        { type: "number", min: 0, value: p.estoque, disabled: p.tem_variacoes }, "c2"),
      h("div", { class: "campo c6", "data-campo": "descricao" },
        h("label", { for: "campo-descricao" }, "Descrição"),
        h("textarea", { id: "campo-descricao", name: "descricao", rows: 5, maxlength: 2000, class: "campo-texto" }),
        h("span", { class: "msg-erro" })),
      h("label", { class: "c3" }, h("input", { type: "checkbox", name: "ativo", checked: p.ativo }), " Produto no ar"),
      h("label", { class: "c3" }, h("input", { type: "checkbox", name: "destaque", checked: p.destaque }), " Destaque na página inicial")),
    h("div", { class: "alerta", hidden: true }),
    h("button", { class: "botao grande", type: "submit", style: "margin-top:16px" }, "Salvar dados"));
  form.elements.descricao.value = p.descricao;
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

function lerArquivoBase64(arquivo) {
  return new Promise((resolver, rejeitar) => {
    const leitor = new FileReader();
    leitor.onload = () => resolver(String(leitor.result).split(",")[1] || "");
    leitor.onerror = () => rejeitar(new Error("Não foi possível ler o arquivo."));
    leitor.readAsDataURL(arquivo);
  });
}

async function enviarFoto(auth, slug, arquivo) {
  if (arquivo.size > 3 * 1024 * 1024) throw new Error(`“${arquivo.name}” passa de 3 MB.`);
  const dados = await lerArquivoBase64(arquivo);
  return api(`/api/admin/produtos/${slug}/foto`, { method: "POST", headers: auth, body: JSON.stringify({ dados }) });
}

function secaoFotos(auth, produto) {
  const secao = h("section", { class: "painel" });
  const desenhar = (p) => {
    const input = h("input", { type: "file", accept: "image/jpeg,image/png,image/webp", multiple: true, class: "sr",
      onchange: async (e) => {
        let atual = p;
        for (const arquivo of e.target.files) {
          try { atual = await enviarFoto(auth, p.slug, arquivo); } catch (err) { avisar(err.message); break; }
        }
        desenhar(atual);
        avisar("Fotos atualizadas ✔");
      } });
    const acao = async (metodo, url) => {
      try { desenhar(await api(url, { method: metodo, headers: auth })); } catch (err) { avisar(err.message); }
    };
    trocar(secao,
      h("h2", {}, "Fotos"),
      h("p", { class: "parcelado" }, "A primeira é a capa. JPG, PNG ou WEBP de até 3 MB; até 8 fotos. Fotos quadradas ficam melhores."),
      h("div", { class: "galeria-admin" },
        p.fotos.map((f, k) => h("figure", {},
          h("img", { src: f.url, alt: "" }),
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
      h("td", {}, h("input", { type: "text", value: v.nome, placeholder: "Ex.: Preto / 220 V", "aria-label": "Nome da opção", oninput: (e) => (v.nome = e.target.value) })),
      h("td", {}, h("input", { type: "text", value: v.sku || "", placeholder: "opcional", "aria-label": "Código (SKU)", oninput: (e) => (v.sku = e.target.value) })),
      h("td", {}, h("input", { type: "text", inputmode: "decimal", value: textoReais(v.preco_centavos), placeholder: "igual ao produto", "aria-label": "Preço próprio",
        oninput: (e) => (v.preco_texto = e.target.value) })),
      h("td", {}, h("input", { type: "number", min: 0, value: v.estoque ?? 0, "aria-label": "Estoque", oninput: (e) => (v.estoque = parseInt(e.target.value, 10) || 0) })),
      h("td", {}, h("button", { class: "link-botao", type: "button", "aria-label": "Remover opção", onclick: () => { linhas.splice(k, 1); desenhar(); } }, "Remover"))));
    const erro = h("div", { class: "alerta", hidden: true });
    trocar(secao,
      h("h2", {}, "Opções (cor, voltagem, tamanho)"),
      h("p", { class: "parcelado" }, "Cada opção tem estoque próprio e o cliente escolhe na página do produto. Para combinar, use nomes como “Preto / 220 V”. Deixe o preço vazio para usar o preço do produto."),
      linhas.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-variacoes" },
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
  const calcular = async () => {
    const f = form.elements;
    if (!f.custo_unitario.value.trim()) {
      trocar(resultado, h("p", { class: "parcelado" }, "Preencha o preço por unidade para ver o resultado."));
      return;
    }
    const corpo = { moeda: f.moeda.value, preco_centavos: precoAtual };
    for (const nome of ["custo_unitario", "cambio", "quantidade", "frete_lote", "impostos_pct", "outros_lote", "embalagem_unidade", "taxa_pagamento_pct", "margem_pct"]) {
      corpo[nome] = f[nome].value.trim().replace(/\.(?=\d{3}(\D|$))/g, "");
    }
    try {
      const r = await api("/api/admin/calculadora", { method: "POST", headers: auth, body: JSON.stringify(corpo) });
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
    h("h2", { style: "margin-top:24px" }, "Padrões da calculadora"),
    h("div", { class: "grade-form" },
      campo("cambio_usd", "Câmbio do dólar (R$)", { inputmode: "decimal", value: aj.cambio_usd }, "c2"),
      campo("cambio_cny", "Câmbio do yuan (R$)", { inputmode: "decimal", value: aj.cambio_cny }, "c2"),
      campo("impostos_pct", "Impostos e taxas de importação (%)", { inputmode: "decimal", value: aj.impostos_pct }, "c2"),
      campo("taxa_pagamento_pct", "Taxa do meio de pagamento (%)", { inputmode: "decimal", value: aj.taxa_pagamento_pct }, "c2"),
      campo("margem_pct", "Margem desejada (%)", { inputmode: "decimal", value: aj.margem_pct }, "c2")),
    h("button", { class: "botao grande", type: "submit", style: "margin-top:16px" }, "Salvar configurações"));
  form.elements.whatsapp.addEventListener("input", (e) => (e.target.value = mascaraTelefone(e.target.value)));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const dados = Object.fromEntries(new FormData(form).entries());
    try {
      const salvo = await api("/api/admin/ajustes", { method: "PUT", headers: auth, body: JSON.stringify(dados) });
      mostrarErros(form, {});
      estado.loja.whatsapp = salvo.whatsapp;
      estado.loja.whatsapp_mensagem = salvo.whatsapp_mensagem;
      atualizarWhatsAppFlutuante();
      avisar("Configurações salvas ✔");
    } catch (err) { mostrarErros(form, err.campos); avisar(err.message); }
  });
  return form;
}

function formularioNovoProduto(auth) {
  const previa = h("div", { class: "galeria-admin" });
  const inputFoto = h("input", { type: "file", name: "foto", id: "campo-foto", accept: "image/jpeg,image/png,image/webp", multiple: true,
    onchange: (e) => trocar(previa, [...e.target.files].map((a) => h("figure", {}, h("img", { src: URL.createObjectURL(a), alt: "" })))) });
  const form = h("form", { class: "painel", novalidate: true },
    h("h2", {}, "Cadastrar produto"),
    h("p", { class: "parcelado" }, "Preencha os dados do produto que você importou. Preços em reais (ex.: 49,90). Depois de cadastrar você pode adicionar opções como cor e voltagem."),
    h("div", { class: "grade-form" },
      campo("nome", "Nome do produto", { required: true, maxlength: 120, placeholder: "Ex.: Fone Bluetooth com estojo" }, "c6"),
      seletorCategoria(""),
      campo("icone", "Ícone (opcional, usado se não houver foto)", { maxlength: 8, placeholder: "📦" }, "c3"),
      camposPreco(),
      campo("estoque", "Estoque (unidades)", { type: "number", min: 0, value: 0, required: true }, "c2"),
      h("div", { class: "campo c6", "data-campo": "descricao" },
        h("label", { for: "campo-descricao" }, "Descrição"),
        h("textarea", { id: "campo-descricao", name: "descricao", rows: 4, maxlength: 2000, class: "campo-texto",
          placeholder: "Principais características, medidas, voltagem, o que vem na caixa…" }),
        h("span", { class: "msg-erro" })),
      h("div", { class: "campo c6", "data-campo": "foto" },
        h("label", { for: "campo-foto" }, "Fotos (JPG, PNG ou WEBP, até 3 MB cada; a primeira é a capa)"), inputFoto, previa, h("span", { class: "msg-erro" })),
      h("label", { class: "c6" }, h("input", { type: "checkbox", name: "destaque" }), " Mostrar nos destaques da página inicial"),
    ),
    h("div", { class: "alerta", hidden: true, id: "erro-novo" }),
    h("button", { class: "botao grande", type: "submit", style: "margin-top:16px" }, "Cadastrar produto"),
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
      avisar("Produto cadastrado ✔");
      navegar(`/admin/produto/${produto.slug}`);
    } catch (err) {
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

async function rotear() {
  const main = $("#conteudo");
  const caminho = location.pathname;
  document.body.classList.toggle("em-admin", caminho.startsWith("/admin"));
  document.querySelectorAll("#menu-categorias a").forEach((a) =>
    a.classList.toggle("ativo", a.getAttribute("href") === caminho));
  for (const [padrao, fn] of ROTAS) {
    const m = caminho.match(padrao);
    if (!m) continue;
    try {
      await fn(main, ...m.slice(1));
    } catch (err) {
      if (err.status === 404) pagina404(main);
      else trocar(main, h("div", { class: "vazio" }, h("div", { class: "ico" }, "⚠️"), h("p", {}, err.message),
        h("button", { class: "botao", onclick: rotear }, "Tentar novamente")));
    }
    return;
  }
  pagina404(main);
}

function navegar(url, substituir = false) {
  if (substituir) history.replaceState(null, "", url);
  else history.pushState(null, "", url);
  rotear();
  if (!substituir) window.scrollTo(0, 0);
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

window.addEventListener("popstate", rotear);

async function iniciar() {
  $("#ano").textContent = new Date().getFullYear();
  estado.carrinho = lerArmazenado(CHAVE_CARRINHO, []).filter((i) => i && typeof i.slug === "string" && i.quantidade > 0)
    .map((i) => ({ slug: i.slug, variacao: Number.isInteger(i.variacao) ? i.variacao : null, quantidade: i.quantidade }));
  salvarCarrinho();
  $(".busca").addEventListener("submit", (e) => {
    e.preventDefault();
    navegar(`/busca?q=${encodeURIComponent($("#campo-busca").value.trim())}`);
  });
  try {
    [estado.loja, estado.categorias] = await Promise.all([api("/api/loja"), api("/api/categorias")]);
  } catch (err) {
    trocar($("#conteudo"), h("div", { class: "vazio" }, h("p", {}, "Não foi possível carregar a loja. Tente novamente em instantes.")));
    return;
  }
  trocar($("#menu-categorias"), ...estado.categorias.map((c) => h("a", { href: `/categoria/${c.slug}` }, `${c.icone} ${c.nome}`)),
    h("a", { href: "/entregas" }, "🚚 Entregas no Norte"));
  atualizarWhatsAppFlutuante();
  rotear();
}

iniciar();
