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

function adicionarAoCarrinho(slug, quantidade = 1) {
  const item = estado.carrinho.find((i) => i.slug === slug);
  if (item) item.quantidade = Math.min(99, item.quantidade + quantidade);
  else estado.carrinho.push({ slug, quantidade });
  salvarCarrinho();
}

function alterarQuantidade(slug, quantidade) {
  if (quantidade <= 0) estado.carrinho = estado.carrinho.filter((i) => i.slug !== slug);
  else {
    const item = estado.carrinho.find((i) => i.slug === slug);
    if (item) item.quantidade = Math.min(99, quantidade);
  }
  salvarCarrinho();
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

function mostrarErros(form, campos) {
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
  if (primeiro) primeiro.focus();
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
  document.title = "Tipiti — produtos diversos com entrega rápida no Norte";
  trocar(main, h("section", { class: "hero" },
      h("div", {},
        h("h1", {}, "Tudo o que você precisa, entregue no Norte."),
        h("p", {}, "Eletrônicos, casa, beleza, moda e muito mais, com envio rápido de Manaus para toda a região."),
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
  let qtd = 1;
  const inputQtd = h("input", { type: "number", min: 1, max: Math.max(1, p.estoque), value: 1, "aria-label": "Quantidade",
    onchange: (e) => { qtd = Math.max(1, Math.min(p.estoque, parseInt(e.target.value, 10) || 1)); e.target.value = qtd; } });
  const mudar = (d) => { qtd = Math.max(1, Math.min(p.estoque, qtd + d)); inputQtd.value = qtd; };
  const temOferta = p.preco_de_centavos && p.preco_de_centavos > p.preco_centavos;

  trocar(main, h("div", { class: "caminho" }, h("a", { href: "/" }, "Início"), " › ",
      h("a", { href: `/categoria/${p.categoria.slug}` }, p.categoria.nome), " › ", p.nome),
    h("article", { class: "produto" },
      h("img", { src: p.imagem, alt: p.nome, width: 400, height: 400 }),
      h("div", {},
        h("h1", {}, p.nome),
        temOferta ? h("div", { class: "preco-de" }, `De ${brl(p.preco_de_centavos)}`) : null,
        h("div", { class: "preco" }, brl(p.preco_centavos)),
        h("div", { class: "preco-pix" }, `${brl(precoPix(p.preco_centavos))} no Pix (${estado.loja.desconto_pix_pct}% off)`),
        h("div", { class: "parcelado" }, textoParcelas(p.preco_centavos)),
        p.estoque > 0
          ? h("div", { class: "compra" },
              h("div", { class: "quantidade" },
                h("button", { type: "button", "aria-label": "Diminuir", onclick: () => mudar(-1) }, "−"), inputQtd,
                h("button", { type: "button", "aria-label": "Aumentar", onclick: () => mudar(1) }, "+")),
              h("button", { class: "botao", onclick: () => { adicionarAoCarrinho(p.slug, qtd); avisar("Produto adicionado ao carrinho ✔"); } }, "Adicionar ao carrinho"),
              h("button", { class: "botao secundario", onclick: () => { adicionarAoCarrinho(p.slug, qtd); navegar("/carrinho"); } }, "Comprar agora"))
          : h("p", { class: "esgotado" }, "Produto esgotado no momento."),
        p.estoque > 0 && p.estoque <= 5 ? h("p", { class: "esgotado" }, `Últimas ${p.estoque} unidades!`) : null,
        h("p", { class: "descricao" }, p.descricao),
        simuladorFrete(() => p.preco_centavos * qtd),
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
  const existentes = new Set(cotacao.itens.filter((i) => i.produto_id).map((i) => i.slug));
  if (existentes.size !== estado.carrinho.length) {
    estado.carrinho = estado.carrinho.filter((i) => existentes.has(i.slug));
    salvarCarrinho();
  }

  trocar(main, h("h1", {}, "Meu carrinho"),
    h("div", { class: "layout-carrinho" },
      h("div", { class: "painel" }, cotacao.itens.filter((i) => i.produto_id).map((i) =>
        h("div", { class: "linha-item" },
          h("img", { src: i.imagem, alt: "" }),
          h("div", {},
            h("a", { class: "nome", href: `/produto/${i.slug}` }, i.nome),
            h("div", { class: "parcelado" }, `${brl(i.preco_unit_centavos)} cada`),
            i.erro ? h("div", { class: "esgotado" }, i.erro) : null,
            h("div", { class: "acoes" },
              h("div", { class: "quantidade" },
                h("button", { type: "button", "aria-label": "Diminuir", onclick: () => { alterarQuantidade(i.slug, i.quantidade - 1); rotear(); } }, "−"),
                h("input", { type: "number", value: i.quantidade, min: 1, "aria-label": "Quantidade",
                  onchange: (e) => { alterarQuantidade(i.slug, parseInt(e.target.value, 10) || 0); rotear(); } }),
                h("button", { type: "button", "aria-label": "Aumentar", onclick: () => { alterarQuantidade(i.slug, i.quantidade + 1); rotear(); } }, "+")),
              h("button", { class: "link-botao", onclick: () => { alterarQuantidade(i.slug, 0); rotear(); } }, "Remover"))),
          h("b", {}, brl(i.total_centavos))))),
      h("aside", { class: "painel resumo" },
        h("h2", {}, "Resumo"),
        h("p", { class: "parcelado" }, "Valores com Pix. No cartão, o desconto não se aplica."),
        erroCep ? h("div", { class: "alerta" }, erroCep) : null,
        blocoResumo(cotacao, { comCep: true, aoMudarCep: (v) => { gravar("tipiti:cep", mascaraCep(v)); rotear(); } }),
        !cotacao.valido ? h("div", { class: "alerta" }, "Ajuste os itens sem estoque para continuar.") : null,
        h("button", { class: "botao grande", disabled: !cotacao.valido, onclick: () => navegar("/checkout") }, "Finalizar compra"),
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
        h("span", {}, `${i.quantidade}× ${i.nome}`), h("span", {}, brl(i.total_centavos)))),
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
        p.itens.map((i) => h("div", { class: "linha-total" }, h("span", {}, `${i.quantidade}× ${i.nome}`), h("span", {}, brl(i.preco_unit_centavos * i.quantidade)))),
        h("hr", { style: "border:0;border-top:1px solid var(--linha)" }),
        h("div", { class: "linha-total" }, h("span", {}, "Subtotal"), h("span", {}, brl(p.subtotal_centavos))),
        p.desconto_centavos ? h("div", { class: "linha-total desconto" }, h("span", {}, "Desconto Pix"), h("span", {}, `− ${brl(p.desconto_centavos)}`)) : null,
        h("div", { class: "linha-total" }, h("span", {}, "Frete"), h("span", {}, p.frete_centavos ? brl(p.frete_centavos) : "Grátis")),
        h("div", { class: "linha-total total" }, h("span", {}, "Total"), h("span", {}, brl(p.total_centavos))),
        h("p", { class: "parcelado" }, `Entrega em ${p.destino} · prazo de até ${p.prazo_dias} dias úteis após a confirmação do pagamento.`)),
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
    h("p", {}, "Trazemos uma seleção variada de produtos — eletrônicos, casa, beleza, moda, brinquedos e ferramentas — e despachamos de perto, para que chegue rápido em Manaus, Parintins, Boa Vista, Santarém, Macapá, Belém e em toda a região."),
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

async function paginaAdmin(main) {
  document.title = "Painel | Tipiti";
  const token = lerArmazenado(CHAVE_ADMIN, "", sessionStorage);
  if (!token) {
    const input = h("input", { type: "password", "aria-label": "Token de acesso", placeholder: "Token de acesso", autocomplete: "off" });
    trocar(main, h("div", { class: "painel", style: "max-width:420px;margin:40px auto" },
      h("h1", {}, "Painel da loja"),
      h("form", { onsubmit: (e) => { e.preventDefault(); gravar(CHAVE_ADMIN, input.value.trim(), sessionStorage); rotear(); } },
        input, h("button", { class: "botao grande", style: "margin-top:12px" }, "Entrar"))));
    return;
  }
  const auth = { Authorization: `Bearer ${token}` };
  const sair = () => { try { sessionStorage.removeItem(CHAVE_ADMIN); } catch (_) { /* ignora */ } rotear(); };
  const conteudo = h("div", { class: "rolagem" });
  const aba = lerArmazenado("tipiti:admin-aba", "pedidos", sessionStorage);
  const botaoAba = (id, rotulo) => h("button", { class: "botao secundario", role: "tab", "aria-selected": String(aba === id),
    onclick: () => { gravar("tipiti:admin-aba", id, sessionStorage); rotear(); } }, rotulo);

  trocar(main, h("div", { class: "secao-cabecalho" }, h("h1", {}, "Painel da loja"), h("button", { class: "link-botao", onclick: sair }, "Sair")),
    h("div", { class: "abas", role: "tablist" }, botaoAba("pedidos", "Pedidos"), botaoAba("produtos", "Produtos")),
    conteudo,
  );

  try {
    if (aba === "produtos") {
      const produtos = await api("/api/admin/produtos", { headers: auth });
      trocar(conteudo, h("table", { class: "tabela-admin" },
        h("thead", {}, h("tr", {}, ["Produto", "Preço (centavos)", "De (centavos)", "Estoque", "Ativo", "Destaque", ""].map((t) => h("th", {}, t)))),
        h("tbody", {}, produtos.map((p) => {
          const preco = h("input", { type: "number", min: 0, value: p.preco_centavos, "aria-label": "Preço" });
          const de = h("input", { type: "number", min: 0, value: p.preco_de_centavos ?? "", "aria-label": "Preço de" });
          const estoque = h("input", { type: "number", min: 0, value: p.estoque, "aria-label": "Estoque" });
          const ativo = h("input", { type: "checkbox", checked: p.ativo, "aria-label": "Ativo" });
          const destaque = h("input", { type: "checkbox", checked: p.destaque, "aria-label": "Destaque" });
          const salvar = async () => {
            try {
              await api(`/api/admin/produtos/${p.slug}`, { method: "PATCH", headers: auth, body: JSON.stringify({
                preco_centavos: parseInt(preco.value, 10), preco_de_centavos: de.value === "" ? null : parseInt(de.value, 10),
                estoque: parseInt(estoque.value, 10), ativo: ativo.checked, destaque: destaque.checked }) });
              avisar("Produto atualizado ✔");
            } catch (err) { avisar(err.message); }
          };
          return h("tr", {}, h("td", {}, h("a", { href: `/produto/${p.slug}` }, p.nome), h("div", { class: "parcelado" }, p.categoria.nome)),
            h("td", {}, preco), h("td", {}, de), h("td", {}, estoque), h("td", {}, ativo), h("td", {}, destaque),
            h("td", {}, h("button", { class: "botao secundario", onclick: salvar }, "Salvar")));
        }))));
    } else {
      const pedidos = await api("/api/admin/pedidos", { headers: auth });
      const status = { aguardando_pagamento: "Aguardando pagamento", pago: "Pago", enviado: "Enviado", entregue: "Entregue", cancelado: "Cancelado" };
      trocar(conteudo, pedidos.length ? h("table", { class: "tabela-admin" },
        h("thead", {}, h("tr", {}, ["Pedido", "Cliente", "Entrega", "Itens", "Total", "Status"].map((t) => h("th", {}, t)))),
        h("tbody", {}, pedidos.map((p) => h("tr", {},
          h("td", {}, h("b", {}, p.codigo), h("div", { class: "parcelado" }, p.criado_em)),
          h("td", {}, p.cliente.nome, h("div", { class: "parcelado" }, p.cliente.email), h("div", { class: "parcelado" }, mascaraTelefone(p.cliente.telefone))),
          h("td", {}, `${p.entrega.endereco}, ${p.entrega.numero} ${p.entrega.complemento}`, h("div", { class: "parcelado" }, `${p.entrega.bairro} · ${p.entrega.cidade}/${p.entrega.uf} · ${mascaraCep(p.entrega.cep)}`), h("div", { class: "parcelado" }, p.zona_frete)),
          h("td", {}, p.itens.map((i) => h("div", {}, `${i.quantidade}× ${i.nome}`))),
          h("td", {}, brl(p.total_centavos), h("div", { class: "parcelado" }, `${p.pagamento_nome}${p.parcelas > 1 ? ` ${p.parcelas}x` : ""}`)),
          h("td", {}, h("select", { class: "campo-select", disabled: p.status === "cancelado", "aria-label": "Status",
            onchange: async (e) => {
              if (e.target.value === "cancelado" && !confirm("Cancelar o pedido e devolver os itens ao estoque?")) { e.target.value = p.status; return; }
              try { await api(`/api/admin/pedidos/${p.codigo}`, { method: "PATCH", headers: auth, body: JSON.stringify({ status: e.target.value }) }); avisar("Status atualizado ✔"); rotear(); }
              catch (err) { avisar(err.message); e.target.value = p.status; }
            } }, Object.entries(status).map(([v, t]) => h("option", { value: v, selected: v === p.status }, t))))))))
        : h("p", {}, "Nenhum pedido ainda."));
    }
  } catch (err) {
    if (err.status === 401) return sair();
    trocar(conteudo, h("div", { class: "alerta" }, err.message));
  }
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
];

async function rotear() {
  const main = $("#conteudo");
  const caminho = location.pathname;
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
  estado.carrinho = lerArmazenado(CHAVE_CARRINHO, []).filter((i) => i && typeof i.slug === "string" && i.quantidade > 0);
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
  rotear();
}

iniciar();
