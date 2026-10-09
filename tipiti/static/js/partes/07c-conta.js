// ------------------------------------------------------------- Minha conta (link por e-mail), avise-me e carrinho abandonado

const CHAVE_CONTA = "tipiti:conta";
const CHAVE_CARRINHO_SALVO = "tipiti:carrinho-salvo";

function sessaoConta() {
  const s = lerArmazenado(CHAVE_CONTA, null);
  if (!s || typeof s.sessao !== "string" || !s.sessao) return "";
  if (s.expira_em && Date.parse(s.expira_em) < Date.now()) { sairDaConta(false); return ""; }
  return s.sessao;
}

function sairDaConta(avisarServidor = true) {
  const sessao = lerArmazenado(CHAVE_CONTA, null);
  try { localStorage.removeItem(CHAVE_CONTA); } catch (_) { /* ignora */ }
  if (avisarServidor && sessao && sessao.sessao) {
    api("/api/conta/sessao", { method: "DELETE", headers: { Authorization: `Conta ${sessao.sessao}` } }).catch(() => {});
  }
  atualizarLinkConta();
}

/** Chamada à API da conta; sessão recusada (401) é esquecida. */
async function apiConta(caminho, opcoes = {}) {
  try {
    return await api(caminho, { ...opcoes, headers: { Authorization: `Conta ${sessaoConta()}`, ...(opcoes.headers || {}) } });
  } catch (err) {
    if (err.status === 401) sairDaConta(false);
    throw err;
  }
}

/** Botão "Minha conta" no topo (ícone no celular). */
function atualizarLinkConta() {
  let link = $("#link-conta");
  if (!link) {
    link = h("a", { id: "link-conta", class: "botao-carrinho botao-conta", "aria-label": "Minha conta" },
      h("span", { "aria-hidden": "true" }, "👤"), h("span", { class: "so-desktop" }, "Minha conta"));
    $(".botao-carrinho").before(link);
  }
  link.setAttribute("href", sessaoConta() ? "/conta" : "/minha-conta");
}

function paginaMinhaConta(main) {
  document.title = "Minha conta | Tipiti";
  if (sessaoConta()) return navegar("/conta", true);
  const geral = h("div", { class: "alerta", role: "alert", hidden: true });
  const resultado = h("div", { "aria-live": "polite" });
  const botao = h("button", { class: "botao grande", type: "submit" }, "Receber link de acesso");
  const form = h("form", { class: "painel", novalidate: true },
    h("div", { class: "grade-form" },
      campoForm("acesso", "email", "E-mail usado nas compras", { type: "email", inputmode: "email", autocomplete: "email", required: true }, "c6")),
    geral, botao);
  prepararForm(form);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    geral.hidden = true;
    const email = form.elements.email.value.trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { mostrarErros(form, { email: "Informe um e-mail válido." }); return; }
    botao.disabled = true;
    botao.textContent = "Enviando…";
    try {
      await api("/api/conta/acesso", { method: "POST", body: JSON.stringify({ email }) });
      trocar(resultado, h("div", { class: "painel sucesso-form" },
        h("h2", { tabindex: "-1" }, "📬 Confira o seu e-mail"),
        h("p", {}, "Se houver pedidos com ", h("b", {}, email), ", enviamos um link de acesso. Ele vale por 30 minutos e funciona uma vez."),
        h("p", { class: "parcelado" }, "Não chegou? Veja a caixa de spam ou promoções. Você também pode acompanhar um pedido pelo código, abaixo.")));
      form.remove();
      $("h2", resultado).focus();
    } catch (err) {
      mostrarErroForm(form, geral, err);
      botao.disabled = false;
      botao.textContent = "Receber link de acesso";
    }
  });
  const formCodigo = h("form", { class: "painel form-codigo", novalidate: true, onsubmit: (e) => {
    e.preventDefault();
    const codigo = formCodigo.elements.codigo.value.trim().toUpperCase().replace(/\s+/g, "");
    if (!/^[A-Z0-9-]{4,20}$/.test(codigo)) { mostrarErros(formCodigo, { codigo: "Informe o código do pedido, ex.: TPT-ABCD1234EFGH." }); return; }
    navegar(`/pedido/${codigo}`);
  } },
  h("h2", {}, "Acompanhar pelo código"),
  h("div", { class: "linha-cep" },
    h("div", { class: "campo", "data-campo": "codigo" },
      h("label", { class: "sr", for: "busca-codigo" }, "Código do pedido"),
      h("input", { id: "busca-codigo", name: "codigo", type: "text", placeholder: "TPT-…", autocapitalize: "characters", autocomplete: "off", "aria-describedby": "busca-codigo-erro" }),
      h("span", { class: "msg-erro", id: "busca-codigo-erro" })),
    h("button", { class: "botao secundario", type: "submit" }, "Ver pedido")));
  trocar(main, h("div", { class: "pagina-estreita" },
    h("h1", {}, "👤 Minha conta"),
    h("p", { class: "lead" }, "Sem senha: informe o e-mail usado nas compras e mandamos um link de acesso para ver seus pedidos, o rastreio e os endereços salvos."),
    resultado, form, formCodigo));
}

const NOMES_AVISE = { aguardando: "Aguardando chegar", pronto: "Chegou! Corre que é por pouco tempo", avisado: "Avisado" };

async function paginaConta(main) {
  const ativo = vigencia();
  document.title = "Minha conta | Tipiti";
  const token = location.hash.length > 1 ? location.hash.slice(1) : "";
  if (token) {
    history.replaceState(history.state, "", location.pathname + location.search);  // o link é de uso único: some da barra
    try {
      const s = await api("/api/conta/sessao", { method: "POST", body: JSON.stringify({ token }) });
      gravar(CHAVE_CONTA, s);
      atualizarLinkConta();
    } catch (err) {
      if (!ativo()) return;
      trocar(main, h("div", { class: "vazio" }, h("div", { class: "ico" }, "⏳"), h("h1", {}, "Link expirado"),
        h("p", {}, err.status === 401 ? err.message : `${err.message}`),
        h("a", { class: "botao", href: "/minha-conta" }, "Pedir um novo link")));
      return;
    }
  }
  if (!sessaoConta()) return navegar("/minha-conta", true);
  let c;
  try {
    c = await apiConta("/api/conta");
  } catch (err) {
    if (!ativo()) return;
    if (err.status === 401) {
      trocar(main, h("div", { class: "vazio" }, h("div", { class: "ico" }, "🔒"), h("h1", {}, "Sessão expirada"),
        h("p", {}, err.message), h("a", { class: "botao", href: "/minha-conta" }, "Entrar de novo")));
      return;
    }
    throw err;
  }
  if (!ativo()) return;
  const primeiro = c.nome ? c.nome.split(" ")[0] : "";
  const enderecos = h("div", {});
  const desenharEnderecos = () => trocar(enderecos,
    c.enderecos.length ? h("ul", { class: "lista-enderecos" }, c.enderecos.map((e) => h("li", { class: "painel endereco" },
      h("div", {}, e.apelido ? h("b", {}, e.apelido) : null, h("p", {}, textoEndereco(e))),
      h("button", { class: "botao-icone", type: "button", "aria-label": `Remover endereço ${e.apelido || e.endereco}`, title: "Remover",
        onclick: async (ev) => {
          ev.currentTarget.disabled = true;
          try {
            await apiConta(`/api/conta/enderecos/${e.id}`, { method: "DELETE" });
            c.enderecos = c.enderecos.filter((x) => x.id !== e.id);
            desenharEnderecos();
            avisar("Endereço removido.");
          } catch (err) { avisar(err.message); ev.currentTarget.disabled = false; }
        } }, icone(ICONE_LIXEIRA))))) : h("p", { class: "parcelado" }, "Nenhum endereço salvo. Salve um para preencher o checkout mais rápido."),
    c.enderecos.length < 10 ? formNovoEndereco((novo) => { c.enderecos.push(novo); desenharEnderecos(); avisar("Endereço salvo ✔"); }) : null);
  desenharEnderecos();

  trocar(main,
    h("div", { class: "cabecalho-pagina" },
      h("h1", {}, primeiro ? `Olá, ${primeiro}!` : "Minha conta"),
      h("button", { class: "botao secundario", type: "button", onclick: () => { sairDaConta(); navegar("/", true); avisar("Você saiu da sua conta."); } }, "Sair")),
    h("p", { class: "parcelado" }, `Conectado como ${c.email}`),
    h("section", { class: "secao", "aria-labelledby": "titulo-meus-pedidos" },
      h("h2", { id: "titulo-meus-pedidos" }, "Meus pedidos"),
      c.pedidos.length ? h("ul", { class: "lista-pedidos-conta" }, c.pedidos.map((p) => {
        const rastreio = blocoRastreio(p, { titulo: false });
        return h("li", { class: "painel pedido-conta" },
          h("div", { class: "venda-topo" }, h("a", { class: "codigo-cupom", href: `/pedido/${p.codigo}` }, p.codigo),
            h("span", { class: `etiqueta status-${p.status}` }, p.status_nome)),
          h("p", { class: "parcelado" }, `${dataCompleta(p.criado_em)} · ${p.itens.reduce((s, i) => s + i.quantidade, 0)} item(ns) · ${brl(p.total_centavos)}`),
          h("p", { class: "itens-resumo" }, p.itens.map((i) => `${i.quantidade}× ${nomeComOpcao(i)}`).join(" · ")),
          rastreio ? h("details", { class: "detalhe-rastreio", open: p.status === "enviado" },
            h("summary", {}, "Ver rastreio"), rastreio) : null,
          h("a", { class: "botao secundario", href: `/pedido/${p.codigo}` }, "Ver pedido"));
      })) : h("p", { class: "painel" }, "Nenhum pedido com este e-mail ainda.")),
    h("section", { class: "secao", "aria-labelledby": "titulo-enderecos" },
      h("h2", { id: "titulo-enderecos" }, "Endereços salvos"), enderecos),
    h("section", { class: "secao", "aria-labelledby": "titulo-avise" },
      h("h2", { id: "titulo-avise" }, "Avise-me quando chegar"),
      c.avise_me.length ? h("ul", { class: "lista-avise" }, c.avise_me.map((a) => h("li", { class: "painel" },
        h("a", { href: `/produto/${a.produto.slug}` }, a.produto.nome), a.variacao ? ` — ${a.variacao}` : "",
        h("span", { class: `etiqueta avise-${a.status}` }, NOMES_AVISE[a.status] || a.status))))
        : h("p", { class: "parcelado" }, "Você não pediu aviso de nenhum produto esgotado.")),
    h("p", { class: "parcelado" }, "Quer uma cópia ou a exclusão dos seus dados? ", h("a", { href: "/meus-dados" }, "Meus dados (LGPD)")));
}

const textoEndereco = (e) => `${e.endereco}, ${e.numero}${e.complemento ? ` (${e.complemento})` : ""} — ${e.bairro}, ${e.cidade}/${e.uf} · CEP ${mascaraCep(e.cep)}`;

/** Formulário de endereço da Minha conta (com o ViaCEP para completar a rua). */
function formNovoEndereco(aoSalvar) {
  const geral = h("div", { class: "alerta", role: "alert", hidden: true });
  const botao = h("button", { class: "botao", type: "submit" }, "Salvar endereço");
  const form = h("form", { class: "painel form-endereco", novalidate: true },
    h("div", { class: "grade-form" },
      campoForm("end", "apelido", "Apelido (opcional)", { placeholder: "Casa, trabalho…", maxlength: 40 }, "c2"),
      campoForm("end", "cep", "CEP", { inputmode: "numeric", autocomplete: "postal-code", placeholder: "00000-000", required: true }, "c2"),
      campoForm("end", "numero", "Número", { inputmode: "numeric", required: true, maxlength: 20 }, "c2"),
      campoForm("end", "endereco", "Rua / Avenida", { autocomplete: "address-line1", required: true }, "c4"),
      campoForm("end", "complemento", "Complemento", { autocomplete: "address-line2" }, "c2"),
      campoForm("end", "bairro", "Bairro", { required: true }, "c2"),
      campoForm("end", "cidade", "Cidade", { autocomplete: "address-level2", required: true }, "c3"),
      campoForm("end", "uf", "UF", { tag: "select", opcoes: opcoesUf(), autocomplete: "address-level1", required: true }, "c1")),
    geral, botao);
  prepararForm(form, { cep: mascaraCep });
  form.elements.cep.addEventListener("input", async () => {
    const d = soDigitos(form.elements.cep.value);
    if (d.length !== 8) return;
    try {
      const resp = await fetch(`https://viacep.com.br/ws/${d}/json/`);
      const e = await resp.json();
      if (!e || e.erro || soDigitos(form.elements.cep.value) !== d) return;
      for (const [campoNome, valor] of [["endereco", e.logradouro], ["bairro", e.bairro], ["cidade", e.localidade], ["uf", e.uf]]) {
        if (valor && !form.elements[campoNome].value) form.elements[campoNome].value = valor;
      }
    } catch (_) { /* sem ViaCEP: a pessoa preenche */ }
  });
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    geral.hidden = true;
    const d = Object.fromEntries(new FormData(form).entries());
    const erros = {};
    if (soDigitos(d.cep).length !== 8) erros.cep = "O CEP tem 8 dígitos.";
    for (const n of ["endereco", "numero", "bairro", "cidade"]) if (!d[n].trim()) erros[n] = "Preencha este campo.";
    if (!d.uf) erros.uf = "Selecione o estado.";
    if (Object.keys(erros).length) { mostrarErros(form, erros); return; }
    botao.disabled = true;
    try {
      aoSalvar(await apiConta("/api/conta/enderecos", { method: "POST", body: JSON.stringify(d) }));
    } catch (err) {
      mostrarErroForm(form, geral, err);
      botao.disabled = false;
    }
  });
  return h("details", { class: "novo-endereco" }, h("summary", {}, "+ Adicionar endereço"), form);
}

/** No checkout, com a conta aberta: endereços salvos para preencher e nome/e-mail da conta. */
function enderecosSalvosCheckout(ref) {
  const caixa = h("div", { class: "enderecos-salvos", hidden: true });
  if (!sessaoConta()) return caixa;
  apiConta("/api/conta").then((c) => {
    const form = ref.form;
    if (!form || !caixa.isConnected) return;
    if (!form.elements.email.value && c.email) form.elements.email.value = c.email;
    if (!form.elements.nome.value && c.nome) form.elements.nome.value = c.nome;
    if (!c.enderecos.length) return;
    const preencher = (e) => {
      const valores = { cep: mascaraCep(e.cep), endereco: e.endereco, numero: e.numero, complemento: e.complemento || "", bairro: e.bairro, cidade: e.cidade, uf: e.uf };
      for (const [n, v] of Object.entries(valores)) {
        form.elements[n].value = v;
        const bloco = form.elements[n].closest("[data-campo]");
        if (bloco) marcarErro(bloco, "");
      }
      gravar("tipiti:cep", valores.cep);
      ref.depois();
      avisar("Endereço preenchido ✔");
    };
    trocar(caixa, h("p", { class: "rotulo-simulador" }, "Usar um endereço salvo"),
      h("div", { class: "chips" }, c.enderecos.map((e) => h("button", { class: "chip chip-endereco", type: "button", onclick: () => preencher(e) },
        h("span", { "aria-hidden": "true" }, "📍 "), e.apelido ? h("b", {}, `${e.apelido}: `) : null, `${e.endereco}, ${e.numero} — ${e.cidade}/${e.uf}`))));
    caixa.hidden = false;
  }).catch(() => { /* sem a conta, o checkout segue normal */ });
  return caixa;
}

// ------------------------------------------------------------- avise-me quando chegar

/**
 * Formulário "Avise-me quando chegar". `opcoes`: as opções do produto (só as esgotadas entram na escolha);
 * `escolhida`: a opção já selecionada, se for uma esgotada.
 */
function formularioAviseMe(p, opcoes = [], escolhida = null, { titulo = true } = {}) {
  const esgotadas = (opcoes || []).filter((v) => !(v.estoque > 0));
  const rascunho = lerArmazenado("tipiti:checkout", {}, sessionStorage) || {};
  const geral = h("div", { class: "alerta", role: "alert", hidden: true });
  const botao = h("button", { class: "botao", type: "submit" }, "🔔 Avise-me quando chegar");
  const unica = esgotadas.length === 1 ? esgotadas[0] : null;
  const form = h("form", { class: "avise-me", novalidate: true, "aria-label": "Avise-me quando chegar" },
    titulo ? h("p", { class: "avise-titulo" }, h("b", {}, "🔔 Avise-me quando chegar"), h("small", {}, "Mandamos uma mensagem assim que voltar ao estoque.")) : null,
    h("div", { class: "grade-form" },
      esgotadas.length > 1 ? campoForm("aviso", "variacao", "Opção", { tag: "select", opcoes: esgotadas.map((v) => [String(v.id), v.nome]) }, "c6") : null,
      campoForm("aviso", "nome", "Seu nome (opcional)", { autocomplete: "given-name", maxlength: 80 }, "c6"),
      campoForm("aviso", "whatsapp", "WhatsApp", { type: "tel", autocomplete: "tel-national", inputmode: "numeric", placeholder: "(92) 90000-0000" }, "c3"),
      campoForm("aviso", "email", "ou e-mail", { type: "email", inputmode: "email", autocomplete: "email" }, "c3")),
    h("div", { class: "campo", "data-campo": "aceite" },
      h("label", { class: "aceite" },
        h("input", { type: "checkbox", name: "aceite", "aria-describedby": "aviso-aceite-erro" }),
        h("span", {}, "Autorizo a Tipiti a me avisar por WhatsApp ou e-mail quando este produto chegar. ",
          h("a", { href: "/privacidade", target: "_blank", rel: "noopener" }, "Privacidade"))),
      h("span", { class: "msg-erro", id: "aviso-aceite-erro" })),
    h("p", { class: "msg-erro", "data-campo": "contato", role: "alert" }),
    geral, botao);
  if (esgotadas.length > 1 && escolhida && esgotadas.includes(escolhida)) form.elements.variacao.value = String(escolhida.id);
  if (rascunho.nome) form.elements.nome.value = String(rascunho.nome).split(" ")[0];
  if (rascunho.telefone) form.elements.whatsapp.value = rascunho.telefone;
  if (rascunho.email) form.elements.email.value = rascunho.email;
  prepararForm(form, { whatsapp: mascaraTelefone });
  const contato = $('[data-campo="contato"]', form);
  form.addEventListener("input", () => { contato.textContent = ""; });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    geral.hidden = true;
    contato.textContent = "";
    const d = Object.fromEntries(new FormData(form).entries());
    const erros = {};
    const w = soDigitos(d.whatsapp);
    if (w && ![10, 11].includes(w.length)) erros.whatsapp = "Informe o WhatsApp com DDD.";
    if (d.email.trim() && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.email.trim())) erros.email = "Informe um e-mail válido.";
    if (!form.elements.aceite.checked) erros.aceite = "Marque a autorização para receber o aviso.";
    mostrarErros(form, erros);
    if (!w && !d.email.trim()) { contato.textContent = "Informe um WhatsApp ou um e-mail para receber o aviso."; form.elements.whatsapp.focus(); return; }
    if (Object.keys(erros).length) return;
    const variacao = esgotadas.length > 1 ? Number(d.variacao) : unica ? unica.id : null;
    botao.disabled = true;
    botao.textContent = "Enviando…";
    try {
      await api("/api/avise-me", { method: "POST", body: JSON.stringify({ slug: p.slug, variacao, nome: d.nome.trim(),
        whatsapp: w || null, email: d.email.trim() || null, aceite: true }) });
      const nomeOpcao = variacao ? (esgotadas.find((v) => v.id === variacao) || {}).nome : "";
      trocar(form, h("p", { class: "sucesso-avaliacao", role: "status", tabindex: "-1" },
        `✔ Pronto! Avisamos você quando ${nomeOpcao ? `a opção ${nomeOpcao}` : "este produto"} chegar.`));
      $("p", form).focus();
    } catch (err) {
      const campos = err.campos || {};
      if (campos.contato) contato.textContent = campos.contato;
      mostrarErroForm(form, geral, err);
      botao.disabled = false;
      botao.textContent = "🔔 Avise-me quando chegar";
    }
  });
  return form;
}

/** Produto à venda com alguma opção esgotada: "avise-me" recolhido para essas opções. */
function avisoOpcoesEsgotadas(p, opcoes) {
  const esgotadas = (opcoes || []).filter((v) => !(v.estoque > 0));
  if (!esgotadas.length) return null;
  const nomes = esgotadas.map((v) => v.nome).join(", ");
  return h("details", { class: "aviso-opcao-esgotada" },
    h("summary", {}, `🔔 ${esgotadas.length === 1 ? `${nomes} esgotou?` : "Sua opção esgotou?"} Avise-me quando chegar`),
    formularioAviseMe(p, opcoes, null, { titulo: false }));
}

// ------------------------------------------------------------- carrinho abandonado (com WhatsApp autorizado)

let esperaCarrinhoSalvo = null;
const carrinhoSalvo = () => {
  const c = lerArmazenado(CHAVE_CARRINHO_SALVO, null);
  return c && typeof c.token === "string" && /^[A-Za-z0-9_-]{16,64}$/.test(c.token) ? c : null;
};
const comCarrinhoSalvo = () => (carrinhoSalvo() ? { carrinho: carrinhoSalvo().token } : {});
function esquecerCarrinhoSalvo() {
  clearTimeout(esperaCarrinhoSalvo);
  try { localStorage.removeItem(CHAVE_CARRINHO_SALVO); } catch (_) { /* ignora */ }
}

/** O carrinho mudou (qualquer página): atualiza o guardado no servidor, com uma espera para juntar as mudanças. */
function sincronizarCarrinhoSalvo(extra = {}) {
  const c = carrinhoSalvo();
  if (!c || !estado.carrinho.length) return;
  clearTimeout(esperaCarrinhoSalvo);
  esperaCarrinhoSalvo = setTimeout(() => {
    api(`/api/carrinhos/${c.token}`, { method: "PUT", body: JSON.stringify({ itens: estado.carrinho, ...extra }) })
      .catch((err) => { if (err.status === 404) esquecerCarrinhoSalvo(); });
  }, 1500);
}

/** Checkout: com WhatsApp válido e autorização marcada, guarda o carrinho para o lembrete. */
function ligarCarrinhoAbandonado(form) {
  let espera;
  const tentar = () => {
    clearTimeout(espera);
    espera = setTimeout(async () => {
      const tel = soDigitos(form.elements.telefone.value);
      if (!form.elements.aceite_whatsapp.checked || ![10, 11].includes(tel.length) || !estado.carrinho.length) return;
      const nome = form.elements.nome.value.trim();
      const atual = carrinhoSalvo();
      if (atual && atual.whatsapp === tel) {
        try {
          await api(`/api/carrinhos/${atual.token}`, { method: "PUT", body: JSON.stringify({ itens: estado.carrinho, nome }) });
          return;
        } catch (err) {
          if (err.status !== 404) return;
          esquecerCarrinhoSalvo();
        }
      }
      try {
        const r = await api("/api/carrinhos", { method: "POST", body: JSON.stringify({ whatsapp: tel, nome, itens: estado.carrinho, aceite_whatsapp: true }) });
        if (r && r.id) gravar(CHAVE_CARRINHO_SALVO, { token: r.id, whatsapp: tel });
      } catch (_) { /* o lembrete é só uma ajuda: não atrapalha a compra */ }
    }, 900);
  };
  form.elements.telefone.addEventListener("input", tentar);
  form.elements.aceite_whatsapp.addEventListener("change", tentar);
  form.elements.nome.addEventListener("change", tentar);
}

/** Link do lembrete (/?c=<token>): junta os itens guardados ao carrinho deste aparelho. */
async function restaurarCarrinhoDoLink() {
  const url = new URL(location.href);
  if (!url.searchParams.has("c")) return;
  const token = url.searchParams.get("c") || "";
  url.searchParams.delete("c");
  history.replaceState(history.state, "", url.pathname + url.search + url.hash);
  if (!/^[A-Za-z0-9_-]{16,64}$/.test(token)) return;
  try {
    const r = await api(`/api/carrinhos/${token}`);
    let novos = 0;
    for (const i of Array.isArray(r.itens) ? r.itens : []) {
      if (!i || typeof i.slug !== "string" || !(i.quantidade > 0)) continue;
      const variacao = Number.isInteger(i.variacao) ? i.variacao : null;
      const atual = estado.carrinho.find((x) => chaveItem(x.slug, x.variacao) === chaveItem(i.slug, variacao));
      if (atual) atual.quantidade = Math.max(atual.quantidade, i.quantidade);
      else { estado.carrinho.push({ slug: i.slug, variacao, quantidade: i.quantidade }); novos++; }
    }
    if (!carrinhoSalvo()) gravar(CHAVE_CARRINHO_SALVO, { token, whatsapp: null });
    salvarCarrinho();
    if (location.pathname === "/") navegar("/carrinho", true);
    else if (location.pathname === "/carrinho") rotear();
    avisar(novos ? "Recuperamos o seu carrinho ✔" : "Seu carrinho está atualizado ✔");
  } catch (err) {
    avisar(err.status === 404 ? "Esse link de carrinho expirou. Os produtos continuam na loja!" : err.message);
  }
}
