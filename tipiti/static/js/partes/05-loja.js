// ------------------------------------------------------------- páginas

async function paginaInicial(main) {
  const ativo = vigencia();
  const l = estado.loja;
  document.title = "Tipiti — importados com entrega rápida no Norte";
  const destaques = h("div", {}, esqueletoCartoes(4));
  const novidades = h("div", {}, esqueletoCartoes(4));
  // seções que só aparecem se houver dados reais
  const ofertas = h("section", { class: "secao secao-ofertas", "aria-labelledby": "titulo-ofertas", hidden: true });
  const maisVendidos = h("section", { class: "secao", "aria-labelledby": "titulo-mais-vendidos", hidden: true });
  const vistos = produtosVistos();
  trocar(main,
    avisoCarrinhoAbandonado(),
    h("section", { class: "hero" },
      h("div", {},
        h("h1", {}, "Importados com preço baixo, entregues rápido no Norte."),
        h("p", {}, "Achadinhos, eletrônicos, casa, beleza e muito mais direto da China — sem esperar semanas: enviamos de Manaus para toda a região."),
        h("a", { class: "botao", href: "#destaques" }, "Ver ofertas"),
      ),
      h("div", { class: "hero-cidades", "aria-label": "Cidades atendidas" },
        l.cidades_destaque.map((c) => h("span", {}, `📍 ${c}`))),
    ),
    faixaCupomDestaque(),
    h("div", { class: "beneficios" },
      [["🚚", "Frete grátis no Norte", `Em compras acima de ${brl(l.frete_gratis_a_partir)}`],
       ["⚡", `${l.desconto_pix_pct}% de desconto no Pix`, "Aprovação imediata"],
       ["💳", `Até ${l.parcelas_max}x sem juros`, "No cartão de crédito"],
       ["🔁", "7 dias para trocar", "Direito de arrependimento"]]
        .map(([ico, t, s]) => h("div", { class: "beneficio" }, h("span", { class: "ico" }, ico), h("div", {}, h("b", {}, t), h("small", {}, s))))),
    ofertas,
    h("section", { class: "secao" },
      h("h2", {}, "Categorias"),
      h("div", { class: "grade-categorias" }, estado.categorias.map((c) =>
        h("a", { class: "cartao-categoria", href: `/categoria/${c.slug}`, style: `--cor:${c.cor}` },
          h("span", { class: "ico" }, c.icone), h("b", {}, c.nome), h("small", {}, `${c.total} produtos`))))),
    blocoEncomendaInicio(),
    h("section", { class: "secao", id: "destaques" },
      h("div", { class: "secao-cabecalho" }, h("h2", {}, "Destaques da semana")), destaques),
    maisVendidos,
    h("section", { class: "secao" }, h("h2", {}, "Novidades"), novidades),
    vistos.length >= 2 ? h("section", { class: "secao" }, h("h2", {}, "Vistos recentemente"), gradeProdutos(vistos, 0)) : null,
  );
  const opcional = (url) => api(url).catch(() => []);
  const [listaDestaques, listaNovidades, listaOfertas, listaMaisVendidos] = await Promise.all([
    api("/api/produtos?destaque=1&limite=8"), api("/api/produtos?ordem=novidades&limite=8"),
    opcional("/api/produtos?promo=1&limite=8"), opcional("/api/produtos?ordem=mais_vendidos&limite=8"),
  ]);
  if (!ativo()) return;
  trocar(destaques, gradeProdutos(listaDestaques));
  trocar(novidades, gradeProdutos(listaNovidades, 0));
  // o servidor antigo ignora `promo=1`: só entra o que tem oferta com prazo ainda correndo
  const emOferta = (Array.isArray(listaOfertas) ? listaOfertas : []).filter(promoAtiva);
  if (emOferta.length) {
    trocar(ofertas, h("div", { class: "secao-cabecalho" },
      h("h2", { id: "titulo-ofertas" }, h("span", { "aria-hidden": "true" }, "⚡ "), "Ofertas relâmpago"),
      h("span", { class: "parcelado" }, "Preços por tempo limitado")),
    h("div", { class: "grade-produtos" }, emOferta.map((p) => cartaoProduto(p, false, { contagem: true }))));
    ofertas.hidden = false;
  }
  const comVendas = (Array.isArray(listaMaisVendidos) ? listaMaisVendidos : []).filter((p) => p.vendidos_30d > 0);
  if (comVendas.length) {
    trocar(maisVendidos, h("h2", { id: "titulo-mais-vendidos" }, "Mais vendidos"), gradeProdutos(comVendas, 0));
    maisVendidos.hidden = false;
  }
}

function seletorOrdem(atual, aoMudar) {
  const opcoes = { relevancia: "Mais relevantes", menor_preco: "Menor preço", maior_preco: "Maior preço", mais_vendidos: "Mais vendidos", novidades: "Novidades", nome: "Nome (A–Z)" };
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
        h("a", { class: "botao", href: `/encomenda${q ? `?q=${encodeURIComponent(q)}` : ""}` }, "📦 Peça uma encomenda"),
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
  registrarVisto(p);
  const opcoes = p.variacoes || [];
  // pré-seleciona a primeira opção com estoque (a escolha fica visível na legenda e na barra)
  let escolhida = opcoes.find((v) => v.estoque > 0) || (opcoes.length === 1 ? opcoes[0] : null);
  let qtd = 1;
  const precosAtuais = () => precosOpcao(p, escolhida);
  const precoAtual = () => precosAtuais().final;
  const estoqueAtual = () => (escolhida ? escolhida.estoque : p.estoque);
  const prevenda = prevendaDe(p);

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
    const { final: preco, ancora } = precosAtuais();
    const estoque = estoqueAtual();
    const off = pctDesconto(preco, ancora);
    trocar(blocoPreco,
      ancora ? h("div", { class: "linha-ancora" }, h("span", { class: "preco-de" }, `De ${brl(ancora)}`),
        h("span", { class: "economia" }, `Economize ${brl(ancora - preco)} (${off}%)`)) : null,
      h("div", { class: "preco" }, ancora ? h("span", { class: "sr" }, "Por ") : null, brl(preco)),
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
            h("button", { class: "botao", type: "button", onclick: () => adicionar(false) }, prevenda ? "Reservar na pré-venda" : "Adicionar ao carrinho"),
            h("button", { class: "botao secundario", type: "button", onclick: () => adicionar(true) }, prevenda ? "Reservar e finalizar" : "Comprar agora"))
        : [h("p", { class: "esgotado" }, esgotada ? "Esta opção está esgotada. Escolha outra."
            : prevenda ? "As vagas desta pré-venda acabaram." : "Produto esgotado no momento."),
          formularioAviseMe(p, opcoes, escolhida)],
      disponivel ? avisoOpcoesEsgotadas(p, opcoes) : null,
      estoque > 0 && estoque <= 5 && (escolhida || !opcoes.length) ? h("p", { class: "esgotado" }, `Últimas ${estoque} unidades!`) : null,
      botaoWhatsApp(textoZap, "Pedir pelo WhatsApp", "botao whatsapp"),
      disponivel ? envioHoje : null);
    trocar(barra,
      h("div", { class: "barra-compra-preco" },
        h("b", {}, ancora ? h("s", { class: "barra-ancora" }, h("span", { class: "sr" }, "De "), brl(ancora)) : null,
          ancora ? h("span", { class: "sr" }, " por ") : null, brl(preco)),
        h("small", {}, `${brl(precoPix(preco))} no Pix`),
        escolhida && opcoes.length > 1 ? h("small", { class: "barra-opcao" }, escolhida.nome) : null),
      botaoWhatsApp(textoZap, "Pedir pelo WhatsApp", "botao whatsapp so-icone", true),
      disponivel ? h("button", { class: "botao", type: "button", onclick: () => adicionar(false) }, prevenda ? "Reservar" : "Adicionar")
        : h("span", { class: "esgotado" }, "Esgotado"));
  };

  const envioHoje = avisoEnvioHoje();
  const contagem = promoAtiva(p) ? contagemOferta(p.promo.fim) : null;
  const n = vendidos(p);
  const selos = selosProduto(p, { maximo: 4 });
  const nota = resumoNota(p);
  const comAvaliacoes = "avaliacoes_total" in p;  // servidor novo
  atualizar();
  trocar(main, h("div", { class: "caminho" }, h("a", { href: "/" }, "Início"), " › ",
      h("a", { href: `/categoria/${p.categoria.slug}` }, p.categoria.nome), " › ", p.nome),
    h("article", { class: "produto" },
      h("div", { class: "galeria" }, principal, miniaturas),
      h("div", { class: "produto-info" },
        selos.length ? h("div", { class: "selos-produto" }, selos.map((s) => h("span", { class: `selo selo-${s.replace("_", "-")}` }, SELOS[s]))) : null,
        h("h1", {}, p.nome),
        nota || n ? h("div", { class: "prova-produto" },
          nota ? h("a", { class: "link-nota", href: "#avaliacoes" }, nota) : null,
          n ? h("span", { class: "vendidos" }, h("span", { "aria-hidden": "true" }, "🔥 "), `${n} vendidos nos últimos 30 dias`) : null) : null,
        blocoPreco,
        prevenda ? h("div", { class: "info-prevenda" },
          h("p", {}, h("b", {}, `📦 Pré-venda: chega em ${diaMes(prevenda.chegada)} — reserve agora`)),
          h("p", { class: "parcelado" }, "Você garante a sua unidade do próximo lote pelo preço de hoje. O envio sai assim que o lote chegar e for separado; a data prevista aparece no carrinho.")) : null,
        contagem ? h("p", { class: "contagem-produto" }, contagem) : null,
        grupo,
        blocoCompra,
        blocoConfianca(),
        prevenda ? null : h("p", { class: "selo-importado" }, "📦 Produto importado · em estoque no Brasil"),
        p.descricao ? h("p", { class: "descricao" }, p.descricao) : null,
        simuladorFrete(() => precoAtual() * qtd, prevenda
          ? () => ({ slug: p.slug, variacao: escolhida ? escolhida.id : null, quantidade: Math.max(1, Math.min(qtd, estoqueAtual() || 1)) }) : null),
      ),
    ),
    secaoCompradosJuntos(p, () => {
      if (!exigirOpcao()) return null;
      if (escolhida && !(escolhida.estoque > 0)) { avisar("Esta opção está esgotada. Escolha outra."); return null; }
      return { variacao: escolhida ? escolhida.id : null, qtd };
    }),
    comAvaliacoes ? secaoAvaliacoes(p) : null,
    p.relacionados && p.relacionados.length ? h("section", { class: "secao" }, h("h2", {}, "Você também pode gostar"), gradeProdutos(p.relacionados, 0)) : null,
    barra,
  );
  observarBarraCompra(blocoCompra, barra);
}

/** "Quem comprou também levou": dados reais do servidor (`comprados_juntos`). */
function secaoCompradosJuntos(p, escolhaAtual) {
  const lista = Array.isArray(p.comprados_juntos) ? p.comprados_juntos.filter((o) => o && o.slug && o.slug !== p.slug) : [];
  if (!lista.length) return null;
  return h("section", { class: "secao comprados-juntos", "aria-labelledby": "titulo-juntos" },
    h("h2", { id: "titulo-juntos" }, "Quem comprou também levou"),
    h("div", { class: "grade-produtos" }, lista.slice(0, 4).map((o) => {
      const semOpcoes = !o.tem_variacoes && !(Array.isArray(o.variacoes) && o.variacoes.length);
      let acao;
      if (!(o.estoque > 0)) acao = null;
      else if (semOpcoes && p.estoque > 0) {
        acao = h("button", { class: "botao secundario", type: "button", onclick: () => {
          const atual = escolhaAtual();
          if (!atual) return;
          adicionarAoCarrinho(p.slug, atual.qtd, atual.variacao);
          adicionarAoCarrinho(o.slug, 1, null);
          mostrarFolhaCarrinho(`${atual.qtd}× ${p.nome} + 1× ${o.nome}`);
        } }, "Adicionar os dois ao carrinho");
      } else if (!semOpcoes) acao = h("a", { class: "botao secundario", href: `/produto/${o.slug}` }, "Escolher opção");
      return h("div", { class: "junto" }, cartaoProduto(o), acao);
    })));
}
