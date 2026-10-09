// ------------------------------------------------------------- revendedoras: link ?r=, cadastro e painel

const CHAVE_REVENDEDORA = "tipiti:revendedora";
const CHAVE_TOKEN_REVENDA = "tipiti:revenda-token";
const DIAS_REVENDEDORA = 30;

/** Guarda o código do link de divulgação (?r=maria-parintins) por 30 dias e tira o parâmetro do endereço. */
function capturarRevendedora() {
  const url = new URL(location.href);
  const codigo = (url.searchParams.get("r") || "").trim().toLowerCase();
  if (!url.searchParams.has("r")) return;
  if (/^[a-z0-9][a-z0-9-]{1,59}$/.test(codigo)) gravar(CHAVE_REVENDEDORA, { codigo, ate: Date.now() + DIAS_REVENDEDORA * 864e5 });
  url.searchParams.delete("r");
  history.replaceState(history.state, "", url.pathname + url.search + url.hash);
}

function revendedoraAtual() {
  const r = lerArmazenado(CHAVE_REVENDEDORA, null);
  if (!r || typeof r.codigo !== "string" || !(r.ate > Date.now())) return null;
  return r.codigo;
}

/** Campo `revendedora` para a cotação e o pedido (vazio sem link guardado). */
const comRevendedora = () => (revendedoraAtual() ? { revendedora: revendedoraAtual() } : {});

/** "Você está comprando com Maria, de Parintins" (só quando o servidor reconhece a revendedora). */
function linhaRevendedora(c) {
  const r = c && c.revendedora;
  if (!r || !r.nome) return null;
  return h("p", { class: "linha-revendedora" }, h("span", { "aria-hidden": "true" }, "🤝 "),
    "Você está comprando com ", h("b", {}, r.nome), r.cidade ? `, de ${r.cidade}` : "");
}

// -- cadastro

function paginaSejaRevendedora(main) {
  document.title = "Seja revendedora | Tipiti";
  const geral = h("div", { class: "alerta", role: "alert", hidden: true });
  const botao = h("button", { class: "botao grande", type: "submit" }, "Quero ser revendedora");
  const resultado = h("div", { "aria-live": "polite" });
  const form = h("form", { class: "painel", novalidate: true, "aria-labelledby": "titulo-cadastro-revenda" },
    h("h2", { id: "titulo-cadastro-revenda" }, "Faça seu cadastro"),
    h("div", { class: "grade-form" },
      campoForm("rev", "nome", "Nome completo", { autocomplete: "name", required: true, maxlength: 80 }, "c6"),
      campoForm("rev", "whatsapp", "WhatsApp com DDD", { type: "tel", autocomplete: "tel-national", inputmode: "numeric", placeholder: "(92) 90000-0000", required: true }, "c3"),
      campoForm("rev", "cpf", "CPF", { inputmode: "numeric", placeholder: "000.000.000-00", required: true }, "c3", "Para pagar as suas comissões."),
      campoForm("rev", "cidade", "Cidade", { autocomplete: "address-level2", required: true, maxlength: 80 }, "c4"),
      campoForm("rev", "uf", "UF", { tag: "select", opcoes: opcoesUf(), autocomplete: "address-level1", required: true }, "c2"),
      campoForm("rev", "instagram", "Instagram (opcional)", { autocomplete: "off", placeholder: "@seu.perfil", maxlength: 60, autocapitalize: "none" }, "c6"),
      campoForm("rev", "mensagem", "Conte um pouco sobre você (opcional)", { tag: "textarea", maxlength: 500, rows: 3,
        placeholder: "Já vende? Para quem? Em quais bairros ou cidades?" }, "c6")),
    h("p", { class: "parcelado" }, "Usamos estes dados só para analisar o cadastro e falar com você. Veja a ",
      h("a", { href: "/privacidade" }, "Política de Privacidade"), "."),
    geral, botao);
  prepararForm(form, { whatsapp: mascaraTelefone, cpf: mascaraCpf });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    geral.hidden = true;
    const d = Object.fromEntries(new FormData(form).entries());
    const erros = {};
    if (d.nome.trim().length < 3) erros.nome = "Informe o nome completo.";
    if (![10, 11].includes(soDigitos(d.whatsapp).length)) erros.whatsapp = "Informe o WhatsApp com DDD, ex.: (92) 99123-4567.";
    if (!cpfValido(d.cpf)) erros.cpf = "CPF inválido. Confira os números.";
    if (d.cidade.trim().length < 2) erros.cidade = "Informe a cidade.";
    if (!d.uf) erros.uf = "Selecione o estado.";
    if (Object.keys(erros).length) { mostrarErros(form, erros); return; }
    botao.disabled = true;
    botao.textContent = "Enviando…";
    try {
      await api("/api/revendedoras", { method: "POST", body: JSON.stringify({ nome: d.nome.trim(), whatsapp: d.whatsapp, cpf: d.cpf,
        cidade: d.cidade.trim(), uf: d.uf, instagram: d.instagram.trim(), mensagem: d.mensagem.trim() }) });
      const titulo = h("h2", { tabindex: "-1" }, "✔ Cadastro recebido!");
      trocar(resultado, h("div", { class: "painel sucesso-form" }, titulo,
        h("p", {}, "Vamos analisar e chamar você no WhatsApp em breve. Quando o cadastro for aprovado, você recebe o seu link de divulgação e o acesso ao seu painel.")));
      form.remove();
      titulo.focus();
    } catch (err) {
      mostrarErroForm(form, geral, err);
      botao.disabled = false;
      botao.textContent = "Quero ser revendedora";
    }
  });

  trocar(main, h("div", { class: "pagina-estreita" },
    h("h1", {}, "🤝 Seja revendedora Tipiti"),
    h("p", { class: "lead" }, "Venda importados para as suas clientes sem ter estoque nem investir: você divulga, a Tipiti entrega e você ganha comissão em cada venda."),
    h("ul", { class: "beneficios-lista" },
      [["💰", "Comissão em cada venda", "paga sobre o valor dos produtos, sem contar o frete"],
       ["🔗", "Seu link exclusivo", "quem compra por ele fica ligado a você por 30 dias"],
       ["🎟️", "Cupom com o seu nome", "desconto para as suas clientes comprarem com você"],
       ["📊", "Painel só seu", "acompanhe vendas, comissões a receber e pagas"],
       ["🚚", "Sem estoque, sem entrega", "a gente separa e envia para todo o Norte"]]
        .map(([ico, t, s]) => h("li", {}, h("span", { class: "ico", "aria-hidden": "true" }, ico), h("div", {}, h("b", {}, t), h("small", {}, s))))),
    resultado, form));
}

// -- painel da revendedora (token no #hash do link, guardado só na aba)

const NOMES_STATUS_PEDIDO = { aguardando_pagamento: "Aguardando pagamento", pago: "Pago", enviado: "Enviado", entregue: "Entregue", cancelado: "Cancelado" };

async function paginaRevenda(main) {
  const ativo = vigencia();
  document.title = "Painel da revendedora | Tipiti";
  const doHash = location.hash.length > 1 ? location.hash.slice(1) : "";
  if (doHash) {
    gravar(CHAVE_TOKEN_REVENDA, doHash, sessionStorage);
    history.replaceState(history.state, "", location.pathname + location.search);  // o token sai da barra de endereço
  }
  const token = lerArmazenado(CHAVE_TOKEN_REVENDA, "", sessionStorage);
  const semAcesso = (msg) => trocar(main, h("div", { class: "vazio" }, h("div", { class: "ico" }, "🔒"),
    h("h1", {}, "Painel da revendedora"), h("p", {}, msg),
    botaoWhatsApp("Olá! Sou revendedora da Tipiti e preciso do link do meu painel.", "Pedir meu link no WhatsApp", "botao whatsapp"),
    h("p", {}, h("a", { href: "/seja-revendedora" }, "Ainda não é revendedora? Cadastre-se"))));
  if (typeof token !== "string" || !token) return semAcesso("Abra o painel pelo link que a Tipiti enviou para você no WhatsApp.");
  let d;
  try {
    d = await api("/api/revenda/painel", { headers: { Authorization: `Bearer ${token}` } });
  } catch (err) {
    if (!ativo()) return;
    if (err.status === 401) {
      try { sessionStorage.removeItem(CHAVE_TOKEN_REVENDA); } catch (_) { /* ignora */ }
      return semAcesso("Este link de acesso não vale mais. Peça um novo link à Tipiti pelo WhatsApp.");
    }
    if (err.status === 403 || err.status === 429) return semAcesso(err.message);
    throw err;
  }
  if (!ativo()) return;
  const link = d.link_divulgacao || "";
  const textoDivulgar = `Oi! Compre importados com entrega rápida no Norte pelo meu link da Tipiti: ${link}${d.cupom ? `\nUse o cupom ${d.cupom.codigo} (${d.cupom.descricao}).` : ""}`;
  const compartilhar = navigator.share ? h("button", { class: "botao secundario", type: "button", onclick: () => {
    navigator.share({ title: "Tipiti", text: textoDivulgar }).catch(() => {});
  } }, "Compartilhar…") : null;
  const t = d.totais || {};
  const sair = h("button", { class: "link-botao", type: "button", onclick: () => {
    try { sessionStorage.removeItem(CHAVE_TOKEN_REVENDA); } catch (_) { /* ignora */ }
    navegar("/", true);
  } }, "Sair deste aparelho");

  trocar(main,
    h("div", { class: "cabecalho-pagina" }, h("h1", {}, `Olá, ${d.nome.split(" ")[0]}!`), sair),
    h("p", { class: "parcelado" }, `Revendedora Tipiti · ${d.cidade} · comissão de ${d.comissao_pct}% sobre os produtos`),
    h("div", { class: "grade-revenda" },
      h("section", { class: "painel", "aria-labelledby": "titulo-link" },
        h("h2", { id: "titulo-link" }, "🔗 Seu link de divulgação"),
        h("label", { class: "sr", for: "link-divulgacao" }, "Link de divulgação"),
        h("input", { id: "link-divulgacao", type: "text", readonly: true, value: link, onfocus: (e) => e.target.select() }),
        h("div", { class: "acoes-encomenda" },
          botaoCopiar(link, "Copiar link", "Link copiado ✔"),
          h("a", { class: "botao whatsapp", href: `https://wa.me/?text=${encodeURIComponent(textoDivulgar)}`, target: "_blank", rel: "noopener" },
            h("span", { "aria-hidden": "true" }, "💬"), " Compartilhar no WhatsApp"),
          compartilhar),
        h("p", { class: "parcelado" }, "Quem entra pelo seu link fica ligado a você por 30 dias.")),
      h("section", { class: "painel", "aria-labelledby": "titulo-cupom-rev" },
        h("h2", { id: "titulo-cupom-rev" }, "🎟️ Seu cupom"),
        d.cupom ? [h("p", {}, h("b", { class: "codigo-cupom cupom-grande" }, d.cupom.codigo)), h("p", { class: "parcelado" }, d.cupom.descricao),
          botaoCopiar(d.cupom.codigo, "Copiar cupom", "Cupom copiado ✔")]
          : h("p", { class: "parcelado" }, "Você ainda não tem cupom de desconto. Fale com a loja se quiser um."))),
    h("div", { class: "cartoes-numeros" },
      h("div", { class: "cartao-numero" }, h("small", {}, "Vendas que contam"), h("b", {}, String(t.vendas ?? 0))),
      h("div", { class: "cartao-numero" }, h("small", {}, "A receber"), h("b", {}, brl(t.a_receber_centavos || 0))),
      h("div", { class: "cartao-numero" }, h("small", {}, "Já pago"), h("b", {}, brl(t.pago_centavos || 0)))),
    h("section", { class: "secao", "aria-labelledby": "titulo-vendas" },
      h("h2", { id: "titulo-vendas" }, "Suas vendas"),
      d.pedidos.length ? h("ul", { class: "lista-vendas" }, d.pedidos.map((p) => h("li", { class: "painel venda" },
        h("div", { class: "venda-topo" }, h("b", { class: "codigo-cupom" }, p.codigo), h("span", { class: `etiqueta status-${p.status}` }, NOMES_STATUS_PEDIDO[p.status] || p.status)),
        h("p", { class: "parcelado" }, `${dataCompleta(p.data)} · ${p.cidade} - ${p.uf}`),
        h("div", { class: "linha-total" }, h("span", {}, "Total do pedido"), h("span", {}, brl(p.total_centavos))),
        h("div", { class: "linha-total" }, h("span", {}, "Sua comissão"),
          h("b", {}, brl(p.comissao_centavos || 0), p.comissao_paga ? " ✔ paga" : ""))))) :
        h("p", { class: "painel" }, "Nenhuma venda ainda. Compartilhe o seu link! As vendas aparecem aqui assim que o pedido é feito; a comissão conta depois do pagamento.")));
}
