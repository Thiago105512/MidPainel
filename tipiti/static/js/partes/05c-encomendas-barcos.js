// ------------------------------------------------------------- formulários das páginas do cliente, encomendas e barcos

/**
 * Como campo(), mas com ids prefixados (duas formas na mesma página não repetem ids) e para input, textarea ou select.
 * `opcoes`: lista [valor, texto] do select.
 */
function campoForm(prefixo, nome, rotulo, { tag = "input", opcoes = null, ...attrs } = {}, classe = "c3", dica = null) {
  const id = `${prefixo}-${nome}`;
  const descr = [dica ? `${id}-dica` : null, `${id}-erro`].filter(Boolean).join(" ");
  let controle;
  if (tag === "select") {
    controle = h("select", { id, name: nome, class: "campo-select", "aria-describedby": descr, ...attrs },
      (opcoes || []).map(([v, t]) => h("option", { value: v }, t)));
  } else if (tag === "textarea") {
    controle = h("textarea", { id, name: nome, class: "campo-texto", rows: 4, "aria-describedby": descr, ...attrs });
  } else {
    controle = h("input", { id, name: nome, type: "text", "aria-describedby": descr, ...attrs });
  }
  return h("div", { class: `campo ${classe}`, "data-campo": nome },
    h("label", { for: id }, rotulo), controle,
    dica ? h("span", { class: "dica-campo", id: `${id}-dica` }, dica) : null,
    h("span", { class: "msg-erro", id: `${id}-erro` }));
}

const opcoesUf = () => [["", "—"], ...UFS.map((u) => [u, u])];

/** Erro da API num formulário: marca os campos e escreve no alerta geral o que não tem campo (429, 409, …). */
function mostrarErroForm(form, geral, err) {
  const campos = err.campos || {};
  mostrarErros(form, campos);
  const soltos = Object.entries(campos).filter(([k, v]) => typeof v === "string" && !form.querySelector(`[data-campo="${k}"]`)).map(([, v]) => v);
  trocar(geral, [err.message, ...soltos.filter((m) => m !== err.message)].join(" "));
  geral.hidden = false;
}

/** Liga máscara de telefone e limpa o erro ao digitar. */
function prepararForm(form, mascaras = {}) {
  for (const [nome, fn] of Object.entries(mascaras)) {
    const el = form.elements[nome];
    if (el) el.addEventListener("input", (e) => (e.target.value = fn(e.target.value)));
  }
  form.addEventListener("input", (e) => {
    const c = e.target.closest("[data-campo]");
    if (c && c.classList.contains("com-erro")) marcarErro(c, "");
  });
}

const soDigitos = (v) => String(v || "").replace(/\D/g, "");

// ------------------------------------------------------------- "Encomenda pra mim"

const CHAVE_ENCOMENDAS = "tipiti:encomendas";
function encomendasGuardadas() {
  const lista = lerArmazenado(CHAVE_ENCOMENDAS, []);
  return Array.isArray(lista) ? lista.filter((e) => e && typeof e.codigo === "string" && typeof e.whatsapp === "string") : [];
}
function guardarEncomenda(codigo, whatsapp) {
  gravar(CHAVE_ENCOMENDAS, [{ codigo, whatsapp }, ...encomendasGuardadas().filter((e) => e.codigo !== codigo)].slice(0, 10));
}

/** Bloco da página inicial. */
function blocoEncomendaInicio() {
  return h("section", { class: "bloco-encomenda", "aria-labelledby": "titulo-encomenda-inicio" },
    h("span", { class: "faixa-ico", "aria-hidden": "true" }, "📦"),
    h("div", {},
      h("h2", { id: "titulo-encomenda-inicio" }, "Não achou o que queria?"),
      h("p", {}, "Mande o link ou a foto do produto e a gente traz pra você. Cotação sem compromisso, pelo WhatsApp.")),
    h("a", { class: "botao", href: "/encomenda" }, "Encomenda pra mim"));
}

function paginaEncomenda(main) {
  document.title = "Encomenda pra mim | Tipiti";
  const q = new URLSearchParams(location.search).get("q") || "";
  const geral = h("div", { class: "alerta", role: "alert", hidden: true });
  const botao = h("button", { class: "botao grande", type: "submit" }, "Pedir cotação");
  const form = h("form", { class: "painel", novalidate: true, "aria-labelledby": "titulo-form-encomenda" },
    h("h2", { id: "titulo-form-encomenda" }, "O que você quer encomendar?"),
    h("div", { class: "grade-form" },
      campoForm("enc", "link", "Link do produto (opcional)", { type: "url", inputmode: "url", autocomplete: "off", placeholder: "https://…", maxlength: 500 }, "c6",
        "Pode ser de qualquer loja ou rede social. A gente só usa para saber o que é."),
      campoForm("enc", "descricao", "Descrição", { tag: "textarea", maxlength: 1000,
        placeholder: "Ex.: liquidificador portátil USB, cor rosa, 380 ml" }, "c6", "Cor, tamanho, voltagem… Se não tiver link, capriche aqui."),
      campoForm("enc", "quantidade", "Quantidade", { type: "number", inputmode: "numeric", min: 1, max: 50, value: 1, required: true }, "c2"),
      campoForm("enc", "nome", "Seu nome", { autocomplete: "name", required: true, maxlength: 120 }, "c4"),
      campoForm("enc", "whatsapp", "WhatsApp com DDD", { type: "tel", autocomplete: "tel-national", inputmode: "numeric", placeholder: "(92) 90000-0000", required: true }, "c3",
        "É por ele que mandamos a cotação."),
      campoForm("enc", "cidade", "Cidade", { autocomplete: "address-level2", required: true, maxlength: 80 }, "c2"),
      campoForm("enc", "uf", "UF", { tag: "select", opcoes: opcoesUf(), autocomplete: "address-level1", required: true }, "c1")),
    geral, botao);
  if (q) form.elements.descricao.value = q;
  prepararForm(form, { whatsapp: mascaraTelefone });
  const resultado = h("div", { "aria-live": "polite" });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    geral.hidden = true;
    const d = Object.fromEntries(new FormData(form).entries());
    const erros = {};
    if (d.nome.trim().length < 3) erros.nome = "Informe seu nome.";
    if (![10, 11].includes(soDigitos(d.whatsapp).length)) erros.whatsapp = "Informe o WhatsApp com DDD, ex.: (92) 99123-4567.";
    if (d.cidade.trim().length < 2) erros.cidade = "Informe a cidade.";
    if (!d.uf) erros.uf = "Selecione o estado.";
    if (!d.link.trim() && !d.descricao.trim()) erros.descricao = "Cole o link do produto ou descreva o que você procura.";
    else if (d.link.trim() && !/^https?:\/\/\S+$/i.test(d.link.trim())) erros.link = "Cole um link que comece com http:// ou https://.";
    const qtd = parseInt(d.quantidade, 10);
    if (!(qtd >= 1 && qtd <= 50)) erros.quantidade = "Quantidade de 1 a 50.";
    if (Object.keys(erros).length) { mostrarErros(form, erros); return; }
    botao.disabled = true;
    botao.textContent = "Enviando…";
    try {
      const r = await api("/api/encomendas", { method: "POST", body: JSON.stringify({
        nome: d.nome.trim(), whatsapp: d.whatsapp, cidade: d.cidade.trim(), uf: d.uf, link: d.link.trim() || null,
        descricao: d.descricao.trim(), quantidade: qtd }) });
      guardarEncomenda(r.codigo, soDigitos(d.whatsapp));
      const titulo = h("h2", { tabindex: "-1" }, "✔ Pedido de encomenda recebido!");
      trocar(resultado, h("div", { class: "painel sucesso-form" },
        titulo,
        h("p", {}, "Seu código é"),
        h("div", { class: "linha-codigo" }, h("span", { class: "codigo" }, r.codigo), botaoCopiar(r.codigo, "Copiar código", "Código copiado ✔")),
        h("p", {}, "Vamos cotar e responder pelo WhatsApp. Você também pode acompanhar por aqui:"),
        h("a", { class: "botao", href: `/encomenda/${r.codigo}` }, "Acompanhar minha encomenda")));
      form.remove();
      titulo.focus();
    } catch (err) {
      mostrarErroForm(form, geral, err);
      botao.disabled = false;
      botao.textContent = "Pedir cotação";
    }
  });

  const guardadas = encomendasGuardadas();
  trocar(main, h("div", { class: "pagina-estreita" },
    h("h1", {}, "📦 Encomenda pra mim"),
    h("p", { class: "lead" }, "Viu um produto em outro site ou no Instagram e não achou aqui? A Tipiti traz pra você, com entrega no Norte."),
    h("ol", { class: "como-funciona" },
      h("li", {}, h("b", {}, "Você manda"), " o link ou a descrição do produto."),
      h("li", {}, h("b", {}, "A gente cota"), " o valor final (já com frete até Manaus) e o prazo, e responde pelo WhatsApp."),
      h("li", {}, h("b", {}, "Você decide:"), " aceita ou recusa por aqui, sem compromisso."),
      h("li", {}, h("b", {}, "Chegou?"), " Avisamos e enviamos para a sua cidade.")),
    guardadas.length ? h("p", { class: "parcelado" }, "Suas encomendas: ",
      guardadas.map((g, k) => [k ? ", " : "", h("a", { href: `/encomenda/${g.codigo}` }, g.codigo)])) : null,
    resultado, form));
}

const ROTULO_STATUS_ENCOMENDA = { nova: "andamento", cotada: "atencao", aceita: "ok", comprada: "ok", entregue: "ok", recusada: "fim", cancelada: "fim" };

async function paginaEncomendaStatus(main, codigo) {
  const ativo = vigencia();
  codigo = codigo.toUpperCase();
  document.title = `Encomenda ${codigo} | Tipiti`;
  const guardada = encomendasGuardadas().find((e) => e.codigo === codigo);
  const resultado = h("div", { "aria-live": "polite" });
  const geral = h("div", { class: "alerta", role: "alert", hidden: true });

  const pedirWhatsApp = (mensagem = "") => {
    const botao = h("button", { class: "botao", type: "submit" }, "Ver encomenda");
    const form = h("form", { class: "painel", novalidate: true },
      h("p", {}, "Para ver a encomenda, confirme o WhatsApp que você informou no pedido."),
      h("div", { class: "grade-form" },
        campoForm("consulta", "whatsapp", "WhatsApp com DDD", { type: "tel", autocomplete: "tel-national", inputmode: "numeric", placeholder: "(92) 90000-0000", required: true }, "c6")),
      geral, botao);
    prepararForm(form, { whatsapp: mascaraTelefone });
    if (mensagem) { geral.textContent = mensagem; geral.hidden = false; }
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const w = soDigitos(form.elements.whatsapp.value);
      if (![10, 11, 12, 13].includes(w.length)) { mostrarErros(form, { whatsapp: "Informe o WhatsApp com DDD." }); return; }
      carregar(w, botao);
    });
    trocar(resultado, form);
    return form;
  };

  async function carregar(whatsapp, botao = null) {
    if (botao) { botao.disabled = true; botao.textContent = "Buscando…"; }
    try {
      const e = await api(`/api/encomendas/${encodeURIComponent(codigo)}?whatsapp=${encodeURIComponent(whatsapp)}`);
      if (!ativo()) return;
      guardarEncomenda(codigo, whatsapp);
      mostrar(e, whatsapp);
    } catch (err) {
      if (!ativo()) return;
      const form = pedirWhatsApp(err.message);
      if (botao) form.elements.whatsapp.value = mascaraTelefone(whatsapp.replace(/^55(?=\d{10,11}$)/, ""));
    }
  }

  function mostrar(e, whatsapp) {
    const respostaGeral = h("div", { class: "alerta", role: "alert", hidden: true });
    const responder = async (aceitar, botao) => {
      botao.disabled = true;
      try {
        const r = await api(`/api/encomendas/${encodeURIComponent(codigo)}/resposta`, { method: "POST", body: JSON.stringify({ whatsapp, aceitar }) });
        if (!ativo()) return;
        mostrar(r, whatsapp);
        avisar(aceitar ? "Encomenda aceita ✔ Vamos falar com você pelo WhatsApp." : "Cotação recusada.");
      } catch (err) {
        botao.disabled = false;
        respostaGeral.textContent = err.message;
        respostaGeral.hidden = false;
      }
    };
    const confirmarRecusa = h("div", { class: "confirmar-recusa", hidden: true },
      h("p", {}, "Recusar esta cotação? Se mudar de ideia, fale com a gente."),
      h("div", { class: "acoes-encomenda" },
        h("button", { class: "botao secundario", type: "button", onclick: (ev) => responder(false, ev.currentTarget) }, "Sim, recusar"),
        h("button", { class: "link-botao", type: "button", onclick: () => { confirmarRecusa.hidden = true; } }, "Voltar")));
    const zap = botaoWhatsApp(`Olá! Sobre a minha encomenda ${codigo} na Tipiti.`, "Falar no WhatsApp", "botao whatsapp");
    trocar(resultado, h("div", { class: "painel encomenda" },
      h("p", { class: `situacao situacao-${ROTULO_STATUS_ENCOMENDA[e.status] || "andamento"}` }, e.status_nome),
      h("dl", { class: "dados-encomenda" },
        e.descricao ? [h("dt", {}, "Descrição"), h("dd", {}, e.descricao)] : null,
        e.link ? [h("dt", {}, "Link"), h("dd", {}, h("a", { href: e.link, target: "_blank", rel: "noopener noreferrer nofollow", class: "link-quebra" }, e.link))] : null,
        h("dt", {}, "Quantidade"), h("dd", {}, String(e.quantidade)),
        h("dt", {}, "Pedido em"), h("dd", {}, dataCompleta(e.criado_em)),
        e.cotacao_centavos != null ? [h("dt", {}, "Valor cotado"), h("dd", {}, h("b", { class: "valor-cotado" }, brl(e.cotacao_centavos)))] : null,
        e.prazo_dias != null ? [h("dt", {}, "Prazo"), h("dd", {}, `até ${e.prazo_dias} dias para chegar`)] : null,
        e.observacao ? [h("dt", {}, "Observação da loja"), h("dd", {}, e.observacao)] : null),
      e.status === "nova" ? h("p", { class: "parcelado" }, "Estamos cotando. Você recebe a resposta pelo WhatsApp e ela aparece aqui também.") : null,
      e.status === "cotada" ? h("div", { class: "acoes-encomenda" },
        h("button", { class: "botao", type: "button", onclick: (ev) => responder(true, ev.currentTarget) }, "✔ Aceitar cotação"),
        h("button", { class: "botao secundario", type: "button", onclick: () => { confirmarRecusa.hidden = false; } }, "Recusar")) : null,
      confirmarRecusa,
      e.status === "aceita" ? h("p", {}, "Combinado! Vamos chamar você no WhatsApp para o pagamento.") : null,
      respostaGeral,
      zap));
  }

  trocar(main, h("div", { class: "pagina-estreita" },
    h("div", { class: "caminho" }, h("a", { href: "/encomenda" }, "Encomenda pra mim"), " › ", codigo),
    h("h1", {}, "Sua encomenda"),
    h("p", {}, "Código: ", h("b", { class: "codigo-cupom" }, codigo)),
    resultado));
  if (guardada) {
    trocar(resultado, h("p", { class: "parcelado" }, "Carregando…"));
    await carregar(guardada.whatsapp);
  } else pedirWhatsApp();
}

// ------------------------------------------------------------- calendário de barcos

async function paginaBarcos(main) {
  const ativo = vigencia();
  document.title = "Calendário de barcos | Tipiti";
  const todas = await api("/api/viagens");
  if (!ativo()) return;
  const zonas = [...new Map(todas.map((v) => [v.zona, v.zona_nome])).entries()].sort((a, b) => a[1].localeCompare(b[1], "pt-BR"));
  const lista = h("div", { class: "lista-viagens", "aria-live": "polite" });
  const seletor = h("select", { id: "barcos-zona", class: "campo-select", onchange: () => escolher(seletor.value) },
    h("option", { value: "" }, "Escolha o destino"), zonas.map(([id, nome]) => h("option", { value: id }, nome)));

  async function escolher(zona) {
    if (!zona) { trocar(lista, h("p", { class: "parcelado" }, "Escolha um destino para ver as próximas saídas.")); return; }
    trocar(lista, h("p", { class: "parcelado" }, "Carregando…"));
    try {
      const viagens = await api(`/api/viagens?zona=${encodeURIComponent(zona)}`);
      if (!ativo() || seletor.value !== zona) return;
      trocar(lista, viagens.length ? h("ol", { class: "viagens" }, viagens.map((v, k) => h("li", { class: "viagem" },
        h("div", { class: "viagem-topo" }, h("b", {}, `🛶 ${v.embarcacao}`), k === 0 ? h("span", { class: "etiqueta ativo" }, "Próxima saída") : null),
        h("p", {}, h("span", { class: "parcelado" }, "Sai de Manaus "), h("b", {}, semanaDiaMes(v.saida)), horaManaus(v.saida) ? ` às ${horaManaus(v.saida)}` : ""),
        h("p", {}, h("span", { class: "parcelado" }, `Chega em ${v.zona_nome} `), h("b", {}, semanaDiaMes(v.chegada_prevista)),
          horaManaus(v.chegada_prevista) ? ` por volta das ${horaManaus(v.chegada_prevista)}` : ""),
        v.observacao ? h("p", { class: "parcelado" }, v.observacao) : null)))
        : h("p", {}, "Nenhuma saída marcada para este destino agora."));
    } catch (err) {
      if (ativo()) trocar(lista, h("div", { class: "alerta" }, err.message));
    }
  }

  trocar(main, h("div", { class: "pagina-estreita" },
    h("h1", {}, "🛶 Calendário de barcos"),
    h("p", { class: "lead" }, "Para Parintins, Santarém e o interior, muitos pedidos seguem de barco a partir de Manaus. Veja as próximas saídas e quando cada barco deve chegar."),
    zonas.length ? [
      h("div", { class: "campo seletor-barcos" }, h("label", { for: "barcos-zona" }, "Destino"), seletor),
      lista,
      h("p", { class: "parcelado" }, "Pedidos pagos embarcam no primeiro barco depois da separação. As datas são previstas e podem mudar com o nível dos rios; acompanhe pelo rastreio do pedido."),
    ] : h("div", { class: "painel" }, h("p", {}, "Ainda não há saídas de barco marcadas. Os prazos de cada região estão em ", h("a", { href: "/entregas" }, "Entregas e prazos"), ".")),
    h("p", {}, h("a", { href: "/entregas" }, "Ver fretes e prazos por região"))));

  // destino pré-escolhido: o do CEP já informado na loja, se tiver barco; senão, o único destino
  let inicial = zonas.length === 1 ? zonas[0][0] : "";
  const cep = lerArmazenado("tipiti:cep", "");
  if (zonas.length > 1 && typeof cep === "string" && soDigitos(cep).length === 8) {
    try {
      const f = await api(`/api/frete?cep=${encodeURIComponent(cep)}&subtotal=0`);
      if (zonas.some(([id]) => id === f.zona)) inicial = f.zona;
    } catch (_) { /* segue sem pré-escolha */ }
    if (!ativo()) return;
  }
  seletor.value = inicial;
  escolher(inicial);
}
