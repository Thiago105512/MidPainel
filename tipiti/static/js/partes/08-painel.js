// ------------------------------------------------------------- administração

const STATUS_PEDIDO = { aguardando_pagamento: "Aguardando pagamento", pago: "Pago", enviado: "Enviado", entregue: "Entregue", cancelado: "Cancelado" };
const CHAVE_ADMIN_ABA = "tipiti:admin-aba";

/** Quem está no painel (GET /api/admin/eu): {nome, papel, totp_ativo, via_token, login?, primeiro_usuario?}. */
let painelEu = null;
/** Mensagem mostrada na próxima tela de login (sessão expirada, token incorreto…). */
let avisoLogin = null;
/** "token" logo depois de tentar entrar com o token de emergência: um 401 em seguida é token incorreto. */
let tentativaLogin = null;

const ehDono = () => Boolean(painelEu && painelEu.papel === "dono");
const NOME_PAPEL = { dono: "Dono", operador: "Operador" };

function sairDoPainel(recusado = false) {
  try { sessionStorage.removeItem(CHAVE_ADMIN); } catch (_) { /* ignora */ }
  painelEu = null;
  if (recusado) {
    avisoLogin = tentativaLogin === "token" ? "Token incorreto. Confira e tente de novo."
      : "Sua sessão terminou (expirou ou o acesso foi encerrado). Entre de novo.";
  }
  tentativaLogin = null;
  navegar("/admin", true);
}

/** Botão "Sair": encerra a sessão no servidor e volta ao login. */
async function sairDaConta() {
  try { await api("/api/admin/logout", { method: "POST", headers: autenticacaoSilenciosa() }); } catch (_) { /* sai do mesmo jeito */ }
  avisoLogin = null;
  sairDoPainel(false);
  avisar("Você saiu do painel.");
}

/** Erros das ações do painel: 401 volta ao login; o resto vira aviso. */
function erroAdmin(err) {
  if (err && err.status === 401) return sairDoPainel(true);
  avisar(err && err.status === 403 ? "Seu usuário não tem permissão para isso." : (err && err.message) || "Não foi possível completar a ação.");
}

/** Mostra o login se não houver sessão; senão devolve o cabeçalho de autorização. */
function autenticacaoAdmin(main) {
  const token = lerArmazenado(CHAVE_ADMIN, "", sessionStorage);
  if (token) return { Authorization: `Bearer ${token}` };
  telaLoginAdmin(main);
  return null;
}

/** Cabeçalho de autorização sem desenhar o login (para ações em páginas já abertas). */
function autenticacaoSilenciosa() {
  const token = lerArmazenado(CHAVE_ADMIN, "", sessionStorage);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function carregarEu(auth) {
  painelEu = await api("/api/admin/eu", { headers: auth });
  tentativaLogin = null;
  return painelEu;
}

// -- menu do painel: seções em grupos; o operador não vê as do dono

const MENU_ADMIN = [
  ["Vendas", [["pedidos", "Pedidos"], ["separacao", "Separação"], ["encomendas", "Encomendas"], ["carrinhos", "Carrinhos"], ["avise-me", "Avise-me"]]],
  ["Catálogo", [["produtos", "Produtos"], ["novo", "+ Novo produto"], ["avaliacoes", "Avaliações"], ["feeds", "Feeds", true]]],
  ["Logística", [["barcos", "Barcos"]]],
  ["Parcerias", [["revendedoras", "Revendedoras", true], ["cupons", "Cupons", true]]],
  ["Loja", [["configuracoes", "Configurações", true], ["usuarios", "Usuários", true], ["privacidade", "Privacidade", true],
    ["emails", "E-mails", true], ["historico", "Histórico", true], ["calculadora", "Calculadora", true]]],
];
const ABAS_EXTRAS = { conta: "Minha conta" };

function menuVisivel() {
  return MENU_ADMIN.map(([grupo, abas]) => [grupo, abas.filter(([, , soDono]) => !soDono || ehDono())]).filter(([, abas]) => abas.length);
}

function rotuloAba(id) {
  for (const [, abas] of MENU_ADMIN) for (const [aid, rotulo] of abas) if (aid === id) return rotulo;
  return ABAS_EXTRAS[id] || id;
}

function abaPermitida(id) {
  if (id in ABAS_EXTRAS) return true;
  return menuVisivel().some(([, abas]) => abas.some(([aid]) => aid === id));
}

function abaGuardada() {
  const aba = lerArmazenado(CHAVE_ADMIN_ABA, "pedidos");
  return typeof aba === "string" && abaPermitida(aba) ? aba : "pedidos";
}

function irParaAba(id) {
  gravar(CHAVE_ADMIN_ABA, id);
  if (location.pathname === "/admin") rotear({ navegacao: true, rolar: true });
  else navegar("/admin");
}

function cabecalhoAdmin(abaAtual) {
  const grupos = menuVisivel();
  const seletor = h("select", { id: "menu-admin-celular", class: "campo-select", onchange: (e) => irParaAba(e.target.value) },
    grupos.map(([grupo, abas]) => h("optgroup", { label: grupo },
      abas.map(([id, rotulo]) => h("option", { value: id, selected: id === abaAtual }, rotulo)))),
    h("optgroup", { label: "Você" }, h("option", { value: "conta", selected: abaAtual === "conta" }, "Minha conta")));
  const eu = painelEu || {};
  return [
    h("div", { class: "admin-topo" },
      h("h1", {}, "Painel da loja"),
      h("div", { class: "admin-usuario" },
        h("span", { class: "admin-quem" }, h("span", { "aria-hidden": "true" }, "👤 "), h("b", {}, eu.nome || "—"), " ",
          h("span", { class: `etiqueta papel-${eu.papel || "x"}` }, eu.via_token ? "Dono (token)" : NOME_PAPEL[eu.papel] || "")),
        h("button", { class: "botao secundario", type: "button", "aria-current": abaAtual === "conta" ? "page" : null,
          onclick: () => irParaAba("conta") }, "Minha conta"),
        h("button", { class: "botao secundario", type: "button", onclick: () => sairDaConta() }, "Sair"))),
    h("nav", { class: "menu-admin", "aria-label": "Seções do painel" },
      h("div", { class: "menu-admin-celular" }, h("label", { for: "menu-admin-celular" }, "Seção do painel"), seletor),
      h("div", { class: "menu-admin-grupos" }, grupos.map(([grupo, abas]) => h("div", { class: "grupo-menu", role: "group", "aria-label": grupo },
        h("span", { class: "grupo-titulo", "aria-hidden": "true" }, grupo),
        h("div", { class: "grupo-abas" }, abas.map(([id, rotulo]) => h("button", { class: "botao secundario", type: "button",
          "aria-current": abaAtual === id ? "page" : null, onclick: () => irParaAba(id) }, rotulo))))))),
  ];
}

async function comTratamento(conteudo, ativo, fn) {
  try { await fn(); } catch (err) {
    if (!ativo()) return;
    if (err.status === 401) return sairDoPainel(true);
    trocar(conteudo, h("div", { class: "alerta" }, err.status === 403 ? "Seu usuário não tem permissão para ver esta seção." : err.message));
  }
}

/** Conteúdo de cada seção (funções declaradas nas partes 08*). */
async function renderizarAba(aba, auth) {
  switch (aba) {
    case "novo": return formularioNovoProduto(auth);
    case "produtos": return listaProdutosAdmin(auth);
    case "calculadora": {
      const aj = await api("/api/admin/ajustes", { headers: auth });
      return h("div", { class: "painel" }, h("h2", {}, "Calculadora de preço do importado"),
        h("p", { class: "parcelado" }, "Descubra o custo real de cada unidade no Brasil e o preço de venda para a margem que você quer."),
        calculadora(auth, aj));
    }
    case "configuracoes": return formularioAjustes(auth);
    case "cupons": return painelCupons(auth);
    case "avaliacoes": return painelAvaliacoes(auth);
    case "separacao": return painelSeparacao(auth);
    case "encomendas": return painelEncomendas(auth);
    case "carrinhos": return painelCarrinhos(auth);
    case "avise-me": return painelAviseMe(auth);
    case "feeds": return painelFeeds(auth);
    case "barcos": return painelViagens(auth);
    case "revendedoras": return painelRevendedoras(auth);
    case "usuarios": return painelUsuarios(auth);
    case "privacidade": return painelPrivacidade(auth);
    case "emails": return painelEmails(auth);
    case "historico": return painelHistorico(auth);
    case "conta": return painelMinhaConta(auth);
    default: return painelPedidos(auth);
  }
}

/** Seção aberta agora: `atualizarAba()` redesenha só o conteúdo dela, sem voltar ao topo. */
let abaEmTela = null;

async function atualizarAba() {
  const e = abaEmTela;
  if (!e || !e.ativo() || !e.conteudo.isConnected) return rotear();
  const y = window.scrollY;
  try {
    const novo = await renderizarAba(e.aba, e.auth);
    if (!e.ativo()) return;
    trocar(e.conteudo, novo);
    window.scrollTo(0, y);
  } catch (err) { erroAdmin(err); }
}

async function paginaAdmin(main) {
  const ativo = vigencia();
  document.title = "Painel | Tipiti";
  const auth = autenticacaoAdmin(main);
  if (!auth) return;
  try { await carregarEu(auth); } catch (err) {
    if (!ativo()) return;
    if (err.status === 401) return sairDoPainel(true);
    tentativaLogin = null;
    trocar(main, h("div", { class: "painel login-admin" }, h("h1", {}, "Painel da loja"), h("div", { class: "alerta", role: "alert" }, err.message),
      h("button", { class: "botao", type: "button", onclick: () => rotear() }, "Tentar novamente")));
    return;
  }
  if (!ativo()) return;
  const aba = abaGuardada();
  document.title = `${rotuloAba(aba)} | Painel Tipiti`;
  const conteudo = h("div", { class: "conteudo-admin" }, h("div", { class: "carregando" }, "Carregando…"));
  trocar(main, cabecalhoAdmin(aba), avisosDeAcesso(auth), conteudo);
  abaEmTela = { aba, auth, conteudo, ativo };
  await comTratamento(conteudo, ativo, async () => {
    const novo = await renderizarAba(aba, auth);
    if (ativo()) trocar(conteudo, novo);
  });
}

function cartaoNumero(rotulo, valor, detalhe, aba = null) {
  const filhos = [h("small", {}, rotulo), h("b", {}, valor), detalhe ? h("small", {}, detalhe) : null];
  return aba ? h("button", { class: "cartao-numero cartao-link", type: "button", onclick: () => irParaAba(aba) }, filhos)
    : h("div", { class: "cartao-numero" }, filhos);
}

/** Célula com rótulo para a tabela virar cartão no celular. */
const celula = (rotulo, attrs, ...filhos) => h("td", { "data-rotulo": rotulo, ...attrs }, h("div", { class: "celula-conteudo" }, ...filhos));

async function listaProdutosAdmin(auth) {
  const produtos = await api("/api/admin/produtos", { headers: auth });
  const margem = (p) => (p.custo_centavos ? `${Math.round(((p.preco_centavos - p.custo_centavos) / p.preco_centavos) * 100)}%` : "—");
  const dono = ehDono();  // operador não recebe custo nem margem: as colunas nem aparecem
  if (!produtos.length) return h("p", { class: "painel" }, "Nenhum produto ainda. Use “+ Novo produto”.");
  return h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-produtos" },
    h("thead", {}, h("tr", {}, h("th", {}, "Produto"), h("th", {}, "Preço"), dono ? h("th", {}, "Custo") : null,
      dono ? h("th", {}, "Margem bruta", h("small", { class: "dica-coluna" }, "lucro ÷ preço")) : null, h("th", {}, "Estoque"), h("th", {}, "Situação"), h("th", {}, h("span", { class: "sr" }, "Ações")))),
    h("tbody", {}, produtos.map((p) => h("tr", {},
      celula("", { class: "celula-produto" }, h("div", { class: "produto-admin" }, h("img", { src: imagemProduto(p, true), alt: "", class: "miniatura", width: 48, height: 48, loading: "lazy" }),
        h("div", {}, h("a", { href: `/admin/produto/${p.slug}` }, p.nome),
          h("div", { class: "parcelado" }, p.categoria.nome, p.tem_variacoes ? " · com opções" : "")))),
      celula("Preço", {}, brl(p.preco_centavos)),
      dono ? celula("Custo", {}, p.custo_centavos ? brl(p.custo_centavos) : h("span", { class: "parcelado" }, "—")) : null,
      dono ? celula("Margem bruta (lucro ÷ preço)", {}, margem(p)) : null,
      celula("Estoque", { class: p.estoque <= 3 ? "esgotado" : "" }, p.estoque),
      celula("Situação", {}, p.ativo ? "No ar" : "Fora do ar", p.destaque ? " · ⭐" : "",
        p.prevenda ? h("div", { class: "parcelado" }, `📦 Pré-venda: chega em ${dataBrAdm(p.prevenda.chegada)}`) : null,
        p.promo_pct && msAte(p.promo_fim) > 0 ? h("div", { class: "parcelado" }, `⚡ −${p.promo_pct}% até ${textoManaus(p.promo_fim)}`) : null),
      celula("", { class: "celula-acao" }, h("a", { class: "botao secundario", href: `/admin/produto/${p.slug}` }, "Editar")))))));
}

async function paginaEditorProduto(main, slug) {
  const ativo = vigencia();
  document.title = "Editar produto | Tipiti";
  const auth = autenticacaoAdmin(main);
  if (!auth) return;
  const conteudo = h("div", { class: "conteudo-admin" }, h("div", { class: "carregando" }, "Carregando…"));
  try { await carregarEu(auth); } catch (err) { if (ativo()) erroAdmin(err); return; }
  if (!ativo()) return;
  gravar(CHAVE_ADMIN_ABA, "produtos");
  trocar(main, cabecalhoAdmin("produtos"), conteudo);
  await comTratamento(conteudo, ativo, async () => {
    const dono = ehDono();  // operador: sem custo, oferta relâmpago e calculadora (o servidor recusaria)
    const [p, aj] = await Promise.all([api(`/api/admin/produtos/${slug}`, { headers: auth }),
      dono ? api("/api/admin/ajustes", { headers: auth }) : null]);
    if (!ativo()) return;
    document.title = `${p.nome} | Painel Tipiti`;
    trocar(conteudo,
      h("p", {}, h("a", { href: "/admin" }, "← Voltar aos produtos"), " · ", h("a", { href: `/produto/${p.slug}`, target: "_blank", rel: "noopener" }, "Ver na loja ↗")),
      p.avise_me_total ? h("p", { class: "info-box" }, `🔔 ${p.avise_me_total} ${p.avise_me_total === 1 ? "pessoa pediu" : "pessoas pediram"} para ser avisada quando chegar. `,
        h("button", { class: "link-botao", type: "button", onclick: () => irParaAba("avise-me") }, "Ver avise-me")) : null,
      h("div", { class: "editor" },
        h("div", {}, secaoDadosProduto(auth, p), secaoPrevenda(auth, p), dono ? secaoOfertaRelampago(auth, p) : null),
        h("div", {},
          secaoFotos(auth, p),
          secaoVariacoes(auth, p),
          dono ? h("section", { class: "painel" }, h("h2", {}, "Calculadora de preço"),
            h("p", { class: "parcelado" }, "Calcule o custo real deste produto e aplique o preço sugerido."),
            calculadora(auth, aj, { precoAtual: p.preco_centavos, aoAplicar: async (preco, custo) => {
              try {
                await api(`/api/admin/produtos/${p.slug}`, { method: "PATCH", headers: auth, body: JSON.stringify({ preco_centavos: preco, custo_centavos: custo }) });
                avisar("Preço e custo aplicados ✔");
                rotear();
              } catch (err) { erroAdmin(err); }
            } })) : null)));
  });
}

function seletorCategoria(atual) {
  return h("div", { class: "campo c3", "data-campo": "categoria" },
    h("label", { for: "campo-categoria" }, "Categoria"),
    h("select", { id: "campo-categoria", name: "categoria", class: "campo-select", "aria-describedby": "erro-categoria" },
      h("option", { value: "" }, "Escolha…"), estado.categorias.map((c) => h("option", { value: c.slug, selected: c.slug === atual }, `${c.icone} ${c.nome}`))),
    h("span", { class: "msg-erro", id: "erro-categoria" }));
}

/** O custo só aparece para o dono (o servidor não o mostra nem grava para o operador). */
function camposPreco(p = {}) {
  return [
    campo("preco_centavos", "Preço de venda (R$)", { inputmode: "decimal", placeholder: "49,90", value: textoReais(p.preco_centavos) }, "c2"),
    campo("preco_de_centavos", "Preço antigo (riscado, opcional)", { inputmode: "decimal", placeholder: "69,90", value: textoReais(p.preco_de_centavos) }, "c2"),
    ehDono() ? campo("custo_centavos", "Custo por unidade (R$, só você vê)", { inputmode: "decimal", placeholder: "22,50", value: textoReais(p.custo_centavos) }, "c2") : null,
  ];
}

function valoresPreco(f) {
  const dados = { preco_centavos: reais(f.preco_centavos.value), preco_de_centavos: reais(f.preco_de_centavos.value) };
  if (f.custo_centavos) dados.custo_centavos = reais(f.custo_centavos.value);
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
      if (err.status === 401) return sairDoPainel(true);
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

const UFS_ADMIN = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"];

/** CNPJ (14) ou CPF (11) só com dígitos -> formatado; outro tamanho fica como veio. */
function documentoAdm(d) {
  const n = String(d || "").replace(/\D/g, "");
  if (n.length === 14) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8, 12)}-${n.slice(12)}`;
  if (n.length === 11) return mascaraCpf(n);
  return String(d || "");
}

/** Faixa vermelha "Antes de abrir a loja, preencha: …" (dados obrigatórios da empresa que faltam). */
function faixaPendenciasLegais(pendencias, comLink = true) {
  if (!Array.isArray(pendencias) || !pendencias.length) return null;
  return h("div", { class: "faixa-pendencias", role: "alert" },
    h("b", {}, "Antes de abrir a loja, preencha: "), pendencias.join(", "), ".",
    h("span", { class: "parcelado-claro" }, " São exigidos por lei (Decreto 7.962/2013) e aparecem na Política de Privacidade e nos Termos."),
    comLink ? h("button", { class: "botao", type: "button", onclick: () => irParaAba("configuracoes") }, "Preencher agora") : null);
}

/** Situação do envio de e-mails (o SMTP é configurado no servidor, não no painel). */
function caixaEmail(resumo) {
  if (!resumo || !("email_configurado" in resumo)) return null;
  const pendentes = resumo.emails_pendentes || 0;
  return h("div", { class: `caixa-email ${resumo.email_configurado ? "ok" : "desligado"}` },
    h("b", {}, resumo.email_configurado ? "✉️ E-mail ligado" : "✉️ E-mail desligado"),
    h("p", {}, resumo.email_configurado
      ? `Os e-mails aos clientes estão saindo pelo servidor. ${pendentes ? `${pendentes} na fila agora.` : "Nenhum na fila."}`
      : `Sem servidor de e-mail, as mensagens ficam guardadas na fila (${pendentes} pendente${pendentes === 1 ? "" : "s"}) e saem quando ele for configurado.`),
    h("p", { class: "parcelado" }, "O e-mail é configurado no servidor da loja (variáveis TIPITI_SMTP_HOST, TIPITI_SMTP_USUARIO, TIPITI_SMTP_SENHA…), não aqui. Peça a quem cuida do servidor; veja o LEIA-ME."),
    ehDono() ? h("button", { class: "link-botao", type: "button", onclick: () => irParaAba("emails") }, "Ver a fila de e-mails") : null);
}

async function formularioAjustes(auth) {
  const [aj, resumo] = await Promise.all([api("/api/admin/ajustes", { headers: auth }),
    api("/api/admin/resumo", { headers: auth }).catch(() => null)]);
  const faixa = h("div", {}, faixaPendenciasLegais(resumo && resumo.pendencias_legais, false));
  const alerta = h("div", { class: "alerta", hidden: true, role: "alert" });
  const form = h("form", { class: "painel", novalidate: true },
    h("h2", {}, "WhatsApp da loja"),
    h("p", { class: "parcelado" }, "Com o número preenchido, aparecem o botão flutuante de atendimento e as opções “Pedir pelo WhatsApp” no produto, no carrinho e na confirmação do pedido."),
    h("div", { class: "grade-form" },
      campo("whatsapp", "Número com DDD", { type: "tel", inputmode: "numeric", placeholder: "(92) 99123-4567",
        value: aj.whatsapp ? mascaraTelefone(aj.whatsapp.slice(2)) : "" }, "c2"),
      campo("whatsapp_mensagem", "Mensagem inicial do botão de atendimento", { maxlength: 300, value: aj.whatsapp_mensagem }, "c4")),

    h("h2", { class: "espaco-topo-grande" }, "Pagamento por Pix"),
    h("p", { class: "parcelado" }, "Com a chave e o nome do recebedor preenchidos, cada pedido no Pix ganha o “copia e cola” e o QR Code com o valor certo."),
    h("div", { class: "grade-form" },
      campo("chave_pix", "Chave Pix", { maxlength: 120, autocomplete: "off", spellcheck: "false", placeholder: "e-mail, CPF, CNPJ, celular ou chave aleatória", value: aj.chave_pix ?? "" }, "c6",
        "Celular com DDD entre parênteses — (92) 99123-4567 —, CPF com pontos e traço, CNPJ, e-mail ou chave aleatória."),
      campo("pix_nome", "Nome do recebedor (como no banco)", { maxlength: 25, autocomplete: "off", placeholder: "TIPITI IMPORTADOS", value: aj.pix_nome ?? "" }, "c4",
        "Até 25 letras. Gravamos sem acentos e em maiúsculas."),
      campo("pix_cidade", "Cidade do recebedor", { maxlength: 15, placeholder: "MANAUS", value: aj.pix_cidade ?? "" }, "c2", "Até 15 letras.")),

    h("h2", { class: "espaco-topo-grande" }, "Identificação da loja"),
    h("p", { class: "parcelado" }, "Obrigatório para vender pela internet: aparece no rodapé, na Política de Privacidade, nos Termos e como remetente das etiquetas."),
    h("div", { class: "grade-form" },
      campo("empresa_razao_social", "Razão social (ou seu nome, se for CPF)", { maxlength: 200, value: aj.empresa_razao_social ?? "" }, "c4"),
      campo("empresa_nome_fantasia", "Nome fantasia", { maxlength: 200, value: aj.empresa_nome_fantasia ?? "" }, "c2"),
      campo("empresa_documento", "CNPJ ou CPF", { inputmode: "numeric", maxlength: 18, value: documentoAdm(aj.empresa_documento) }, "c2"),
      campo("empresa_endereco", "Endereço (rua, número, complemento, bairro)", { maxlength: 200, autocomplete: "street-address", value: aj.empresa_endereco ?? "" }, "c4"),
      campo("empresa_cidade", "Cidade", { maxlength: 200, value: aj.empresa_cidade ?? "" }, "c2"),
      h("div", { class: "campo c2", "data-campo": "empresa_uf" },
        h("label", { for: "campo-empresa_uf" }, "UF"),
        h("select", { id: "campo-empresa_uf", name: "empresa_uf", class: "campo-select", "aria-describedby": "erro-empresa_uf" },
          h("option", { value: "" }, "Escolha…"), UFS_ADMIN.map((uf) => h("option", { value: uf, selected: uf === aj.empresa_uf }, uf))),
        h("span", { class: "msg-erro", id: "erro-empresa_uf" })),
      campo("empresa_cep", "CEP", { inputmode: "numeric", maxlength: 9, value: aj.empresa_cep ? mascaraCep(aj.empresa_cep) : "" }, "c2"),
      campo("empresa_email", "E-mail de atendimento", { type: "email", maxlength: 200, value: aj.empresa_email ?? "" }, "c3"),
      campo("empresa_telefone", "Telefone", { type: "tel", inputmode: "numeric", value: aj.empresa_telefone ? mascaraTelefone(aj.empresa_telefone.replace(/^55(?=\d{10,11}$)/, "")) : "" }, "c3"),
      campo("encarregado_dados", "Encarregado de dados (LGPD): nome e e-mail", { maxlength: 200, value: aj.encarregado_dados ?? "",
        placeholder: aj.empresa_email || "Maria Silva — privacidade@tipiti.com.br" }, "c6",
        "Quem responde aos pedidos dos clientes sobre os dados pessoais. Vazio: usamos o e-mail de atendimento.")),

    h("h2", { class: "espaco-topo-grande" }, "Padrões da calculadora"),
    h("div", { class: "grade-form" },
      campo("cambio_usd", "Câmbio do dólar (R$)", { inputmode: "decimal", value: aj.cambio_usd }, "c2"),
      campo("cambio_cny", "Câmbio do yuan (R$)", { inputmode: "decimal", value: aj.cambio_cny }, "c2"),
      campo("impostos_pct", "Impostos e taxas de importação (%)", { inputmode: "decimal", value: aj.impostos_pct }, "c2"),
      campo("taxa_pagamento_pct", "Taxa do meio de pagamento (%)", { inputmode: "decimal", value: aj.taxa_pagamento_pct }, "c2"),
      campo("margem_pct", "Margem desejada (%)", { inputmode: "decimal", value: aj.margem_pct }, "c2")),
    camposGatilhosAjustes(aj),
    alerta,
    h("button", { class: "botao grande espaco-topo", type: "submit" }, "Salvar configurações"));
  const f = form.elements;
  f.whatsapp.addEventListener("input", (e) => (e.target.value = mascaraTelefone(e.target.value)));
  f.empresa_telefone.addEventListener("input", (e) => (e.target.value = mascaraTelefone(e.target.value)));
  f.empresa_cep.addEventListener("input", (e) => (e.target.value = mascaraCep(e.target.value)));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    alerta.hidden = true;
    const dados = Object.fromEntries(new FormData(form).entries());
    if (f.prova_social) dados.prova_social = f.prova_social.checked ? "1" : "0";
    for (const nome of ["cambio_usd", "cambio_cny", "impostos_pct", "taxa_pagamento_pct", "margem_pct"]) {
      const n = lerNumero(dados[nome], { pontoDecimal: true });
      if (n !== null && !Number.isNaN(n)) dados[nome] = String(n);  // inválido segue como está e o servidor aponta o erro
    }
    const botao = form.querySelector("button[type=submit]");
    botao.disabled = true;
    try {
      const salvo = await api("/api/admin/ajustes", { method: "PUT", headers: auth, body: JSON.stringify(dados) });
      mostrarErros(form, {});
      estado.loja.whatsapp = salvo.whatsapp;
      estado.loja.whatsapp_mensagem = salvo.whatsapp_mensagem;
      if (typeof salvo.chave_pix === "string") estado.loja.chave_pix = salvo.chave_pix;
      if (typeof salvo.prova_social === "string") estado.loja.prova_social = salvo.prova_social === "1";
      atualizarWhatsAppFlutuante();
      // o servidor normaliza (nome do Pix em maiúsculas, documento só com dígitos): mostra como ficou gravado
      if (typeof salvo.pix_nome === "string") f.pix_nome.value = salvo.pix_nome;
      if (typeof salvo.pix_cidade === "string") f.pix_cidade.value = salvo.pix_cidade;
      if (typeof salvo.empresa_documento === "string") f.empresa_documento.value = documentoAdm(salvo.empresa_documento);
      const novoResumo = await api("/api/admin/resumo", { headers: auth }).catch(() => null);
      if (novoResumo) trocar(faixa, faixaPendenciasLegais(novoResumo.pendencias_legais, false));
      avisar("Configurações salvas ✔");
    } catch (err) {
      if (err.status === 401) return sairDoPainel(true);
      mostrarErros(form, err.campos);
      const msgs = Object.values(err.campos || {}).filter((m) => typeof m === "string");
      alerta.replaceChildren(h("b", {}, err.message), ...msgs.map((m) => h("div", {}, m)));
      alerta.hidden = false;
      avisar(err.message);
    } finally {
      botao.disabled = false;
    }
  });
  return h("div", { class: "pilha" }, faixa, caixaEmail(resumo), form);
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
