// ------------------------------------------------------------- termos, privacidade, LGPD, rodapé e início das extras

async function paginaTextoLegal(main, qual) {
  const ativo = vigencia();
  const doc = await api(`/api/legal/${qual}`);
  if (!ativo()) return;
  document.title = `${doc.titulo} | Tipiti`;
  const outro = qual === "termos" ? h("a", { href: "/privacidade" }, "Política de Privacidade") : h("a", { href: "/termos" }, "Termos de Uso");
  trocar(main, h("article", { class: "texto texto-legal" },
    h("h1", {}, doc.titulo),
    doc.atualizado_em ? h("p", { class: "parcelado" }, `Atualizado em ${dataCompleta(doc.atualizado_em)}`) : null,
    doc.secoes.length > 3 ? h("nav", { class: "indice-legal", "aria-label": "Nesta página" },
      h("p", { class: "rotulo-simulador" }, "Nesta página"),
      h("ol", {}, doc.secoes.map((s, k) => h("li", {}, h("a", { href: `#secao-${k + 1}` }, s.titulo))))) : null,
    doc.secoes.map((s, k) => h("section", { "aria-labelledby": `secao-${k + 1}` },
      h("h2", { id: `secao-${k + 1}` }, `${k + 1}. ${s.titulo}`),
      s.paragrafos.map((t) => h("p", {}, t)))),
    h("p", { class: "rodape-legal" }, "Veja também: ", outro, " · ", h("a", { href: "/meus-dados" }, "Meus dados (LGPD)"), " · ",
      h("a", { href: "/trocas" }, "Trocas e devoluções"))));
}

function paginaMeusDados(main) {
  document.title = "Meus dados (LGPD) | Tipiti";
  const geral = h("div", { class: "alerta", role: "alert", hidden: true });
  const resultado = h("div", { "aria-live": "polite" });
  const botao = h("button", { class: "botao grande", type: "submit" }, "Enviar solicitação");
  const tipos = [["copia", "Quero uma cópia dos meus dados", "Tudo o que a Tipiti guarda sobre você."],
    ["correcao", "Quero corrigir meus dados", "Nome, e-mail, telefone ou endereço errados."],
    ["exclusao", "Quero excluir meus dados", "Os dados fiscais dos pedidos ficam pelo prazo exigido em lei."]];
  const form = h("form", { class: "painel", novalidate: true },
    h("fieldset", { class: "campo", "data-campo": "tipo" },
      h("legend", {}, "O que você precisa?"),
      h("div", { class: "opcoes-pagamento" }, tipos.map(([v, t, s], k) => h("label", { class: "opcao" },
        h("input", { type: "radio", name: "tipo", value: v, checked: k === 0 }), h("span", {}, h("b", {}, t), h("small", {}, s))))),
      h("span", { class: "msg-erro" })),
    h("div", { class: "grade-form" },
      campoForm("lgpd", "email", "E-mail usado nas compras", { type: "email", inputmode: "email", autocomplete: "email", required: true }, "c3"),
      campoForm("lgpd", "cpf", "CPF", { inputmode: "numeric", placeholder: "000.000.000-00", required: true }, "c3", "Para confirmarmos que os dados são seus."),
      campoForm("lgpd", "mensagem", "Detalhes (opcional)", { tag: "textarea", maxlength: 2000, rows: 3,
        placeholder: "Ex.: meu telefone mudou para (92) 9…" }, "c6")),
    geral, botao);
  prepararForm(form, { cpf: mascaraCpf });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    geral.hidden = true;
    const d = Object.fromEntries(new FormData(form).entries());
    const erros = {};
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.email.trim())) erros.email = "Informe um e-mail válido.";
    if (!cpfValido(d.cpf)) erros.cpf = "CPF inválido. Confira os números.";
    if (Object.keys(erros).length) { mostrarErros(form, erros); return; }
    botao.disabled = true;
    botao.textContent = "Enviando…";
    try {
      const r = await api("/api/privacidade/solicitacoes", { method: "POST", body: JSON.stringify({ tipo: d.tipo, email: d.email.trim(), cpf: d.cpf, mensagem: d.mensagem.trim() }) });
      const titulo = h("h2", { tabindex: "-1" }, "✔ Solicitação registrada");
      trocar(resultado, h("div", { class: "painel sucesso-form" }, titulo,
        h("p", {}, "Seu protocolo é"),
        h("div", { class: "linha-codigo" }, h("span", { class: "codigo" }, r.protocolo), botaoCopiar(r.protocolo, "Copiar protocolo", "Protocolo copiado ✔")),
        h("p", {}, "Respondemos em até 15 dias pelo e-mail informado. Podemos pedir uma confirmação de identidade antes de enviar ou apagar os dados.")));
      form.remove();
      titulo.focus();
    } catch (err) {
      mostrarErroForm(form, geral, err);
      botao.disabled = false;
      botao.textContent = "Enviar solicitação";
    }
  });
  trocar(main, h("div", { class: "pagina-estreita" },
    h("h1", {}, "🔐 Meus dados (LGPD)"),
    h("p", { class: "lead" }, "Pela Lei Geral de Proteção de Dados, você pode pedir uma cópia, a correção ou a exclusão dos seus dados pessoais."),
    h("p", { class: "parcelado" }, "Saiba como tratamos seus dados na ", h("a", { href: "/privacidade" }, "Política de Privacidade"), "."),
    resultado, form));
}

// ------------------------------------------------------------- rodapé (links e identificação da loja)

function montarRodape() {
  const interno = $(".rodape-interno");
  if (!interno || $("#rodape-extras")) return;
  const instalar = h("button", { class: "link-rodape", type: "button", onclick: abrirInstalacao }, "📲 Instalar o app");
  const lista = (titulo, itens) => h("div", {}, h("p", { class: "rodape-titulo" }, titulo),
    h("ul", {}, itens.map(([href, texto]) => h("li", {}, typeof href === "string" ? h("a", { href }, texto) : href))));
  interno.classList.add("com-extras");
  interno.append(
    h("div", { id: "rodape-extras", class: "rodape-coluna" }, lista("Compre do seu jeito", [
      ["/barcos", "Calendário de barcos"], ["/encomenda", "Encomenda pra mim"], ["/seja-revendedora", "Seja revendedora"],
      ["/minha-conta", "Minha conta"], [instalar, ""]])),
    lista("Seus direitos", [["/termos", "Termos de Uso"], ["/privacidade", "Política de Privacidade"], ["/meus-dados", "Meus dados (LGPD)"],
      ["/trocas", "Trocas e devoluções"], ["/entregas", "Entregas e prazos"]]));
  // Decreto 7.962/2013: identificação de quem vende, visível no site (só o que já foi preenchido)
  const e = (estado.loja && estado.loja.empresa) || {};
  const partes = [e.razao_social, e.documento_formatado ? `${String(e.documento_formatado).replace(/\D/g, "").length === 11 ? "CPF" : "CNPJ"} ${e.documento_formatado}` : null,
    e.endereco_completo].filter(Boolean);
  const contatos = [
    e.email ? h("a", { href: `mailto:${e.email}` }, e.email) : null,
    e.telefone ? h("a", { href: `tel:+55${String(e.telefone).replace(/\D/g, "")}` }, e.telefone) : null].filter(Boolean);
  if (partes.length || contatos.length) {
    $(".rodape-final").before(h("address", { class: "rodape-empresa" },
      partes.join(" · "), partes.length && contatos.length ? " · " : "", contatos.map((c, k) => [k ? " · " : "", c])));
  }
}

/** Chamado uma vez pelo iniciar(), depois de carregar a loja. */
function iniciarExtrasLoja() {
  try {
    capturarRevendedora();
    atualizarLinkConta();
    montarRodape();
    iniciarPwa();
    restaurarCarrinhoDoLink();
  } catch (err) {
    if (window.console) console.warn("Tipiti: extras da loja", err);  // nunca impede a loja de abrir
  }
}
