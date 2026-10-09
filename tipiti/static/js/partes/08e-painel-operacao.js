// ------------------------------------------------------------- painel: barcos, encomendas, avise-me e carrinhos abandonados

/** Zonas de frete (espelha loja/frete.py): id usado pelas viagens -> nome mostrado. */
const ZONAS_VIAGEM_ADM = [["manaus", "Manaus (AM)"], ["parintins", "Parintins (AM)"], ["boa-vista", "Boa Vista (RR)"], ["santarem", "Santarém (PA)"],
  ["macapa", "Macapá (AP)"], ["belem", "Belém (PA)"], ["rio-branco", "Rio Branco (AC)"], ["porto-velho", "Porto Velho (RO)"], ["palmas", "Palmas (TO)"],
  ["interior-am", "Interior do Amazonas"], ["interior-rr", "Interior de Roraima"], ["interior-pa", "Interior do Pará"], ["interior-ap", "Interior do Amapá"],
  ["interior-ac", "Interior do Acre"], ["interior-ro", "Interior de Rondônia"], ["interior-to", "Interior do Tocantins"]];

const SEMANA_MS = 7 * 24 * 3600000;
const isoMais = (iso, ms) => new Date(Date.parse(iso) + ms).toISOString().replace(/\.\d{3}Z$/, "Z");

// -- barcos (viagens)

let viagemEditando = null;

function formularioViagem(auth, v) {
  const editando = Boolean(v && v.id);
  const alerta = h("div", { class: "alerta", hidden: true, role: "alert" });
  const form = h("form", { class: "painel", novalidate: true, id: "form-viagem", "aria-labelledby": "titulo-viagem" },
    h("h2", { id: "titulo-viagem" }, editando ? `Editar viagem: ${v.embarcacao}` : "Nova viagem"),
    h("p", { class: "parcelado" }, "Horários de Manaus. A loja usa a próxima saída da zona para mostrar ao cliente quando o pedido chega."),
    h("div", { class: "grade-form" },
      h("div", { class: "campo c2", "data-campo": "zona" },
        h("label", { for: "campo-zona" }, "Destino (zona de entrega)"),
        h("select", { id: "campo-zona", name: "zona", class: "campo-select", "aria-describedby": "erro-zona" },
          h("option", { value: "" }, "Escolha…"), ZONAS_VIAGEM_ADM.map(([id, nome]) => h("option", { value: id, selected: v && v.zona === id }, nome))),
        h("span", { class: "msg-erro", id: "erro-zona" })),
      campo("embarcacao", "Embarcação", { maxlength: 80, placeholder: "B/M Lady Belém", value: (v && v.embarcacao) || "" }, "c4"),
      campoDataHora("saida", "Saída de Manaus (horário de Manaus)", v && v.saida, "c3"),
      campoDataHora("chegada_prevista", "Chegada prevista (horário de Manaus)", v && v.chegada_prevista, "c3"),
      campo("observacao", "Observação (opcional)", { maxlength: 300, placeholder: "Porto da Manaus Moderna, embarque até 10h", value: (v && v.observacao) || "" }, "c6"),
      h("label", { class: "c6 caixa" }, h("input", { type: "checkbox", name: "ativo", checked: !v || v.ativo !== false }), " Ativa (aparece para os clientes)")),
    alerta,
    h("div", { class: "compra" },
      h("button", { class: "botao", type: "submit" }, editando ? "Salvar viagem" : "Cadastrar viagem"),
      v ? h("button", { class: "botao secundario", type: "button", onclick: () => { viagemEditando = null; atualizarAba(); } }, "Cancelar") : null));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    alerta.hidden = true;
    const f = form.elements;
    const dados = { zona: f.zona.value, embarcacao: f.embarcacao.value.trim(), saida: manausParaIso(f.saida.value),
      chegada_prevista: manausParaIso(f.chegada_prevista.value), observacao: f.observacao.value.trim(), ativo: f.ativo.checked };
    const erros = {};
    if (!dados.zona) erros.zona = "Escolha o destino.";
    if (dados.embarcacao.length < 2) erros.embarcacao = "Informe o nome da embarcação.";
    if (!dados.saida) erros.saida = "Informe a data e a hora da saída.";
    if (!dados.chegada_prevista) erros.chegada_prevista = "Informe a chegada prevista.";
    else if (dados.saida && Date.parse(dados.chegada_prevista) <= Date.parse(dados.saida)) erros.chegada_prevista = "A chegada precisa ser depois da saída.";
    if (Object.keys(erros).length) return mostrarErros(form, erros);
    try {
      if (editando) await enviarAdmin(auth, `/api/admin/viagens/${v.id}`, "PATCH", dados);
      else await enviarAdmin(auth, "/api/admin/viagens", "POST", dados);
      viagemEditando = null;
      avisar(editando ? "Viagem atualizada ✔" : "Viagem cadastrada ✔");
      atualizarAba();
    } catch (err) { erroFormAdm(form, alerta, err); }
  });
  return form;
}

async function painelViagens(auth) {
  const viagens = await api("/api/admin/viagens", { headers: auth });
  const lista = Array.isArray(viagens) ? viagens : [];
  const editar = (v) => () => {
    viagemEditando = v;
    atualizarAba().then(() => { const f = $("#form-viagem"); if (f) { f.scrollIntoView({ block: "start" }); f.elements.embarcacao.focus({ preventScroll: true }); } });
  };
  const alterar = (v, dados, ok) => async () => {
    try { await enviarAdmin(auth, `/api/admin/viagens/${v.id}`, "PATCH", dados); avisar(ok); atualizarAba(); }
    catch (err) { if (err.status !== 401) avisar(err.message); }
  };
  const duplicar = (v) => async () => {
    try {
      await enviarAdmin(auth, "/api/admin/viagens", "POST", { zona: v.zona, embarcacao: v.embarcacao, saida: isoMais(v.saida, SEMANA_MS),
        chegada_prevista: isoMais(v.chegada_prevista, SEMANA_MS), observacao: v.observacao || "", ativo: true });
      avisar(`Viagem copiada para ${quandoAdm(isoMais(v.saida, SEMANA_MS))} ✔`);
      atualizarAba();
    } catch (err) { if (err.status !== 401) avisar(err.message); }
  };
  return h("div", { class: "pilha" },
    formularioViagem(auth, viagemEditando),
    lista.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-viagens" },
      h("thead", {}, h("tr", {}, ["Destino", "Embarcação", "Saída", "Chegada prevista", "Situação", "Pedidos", ""].map((t) => h("th", {}, t)))),
      h("tbody", {}, lista.map((v) => {
        const passada = !(msAte(v.saida) > 0);
        return h("tr", { class: passada ? "passada" : "" },
          celula("Destino", {}, h("b", {}, v.zona_nome)),
          celula("Embarcação", {}, v.embarcacao, v.observacao ? h("div", { class: "parcelado" }, v.observacao) : null),
          celula("Saída", {}, quandoAdm(v.saida)),
          celula("Chegada prevista", {}, quandoAdm(v.chegada_prevista)),
          celula("Situação", {}, h("span", { class: `etiqueta ${!v.ativo ? "inativo" : passada ? "agendado" : "ativo"}` },
            !v.ativo ? "Inativa" : passada ? "Já saiu" : "Ativa")),
          celula("Pedidos", {}, String(v.pedidos ?? 0)),
          celula("", { class: "celula-acao" }, h("div", { class: "acoes-cupom" },
            h("button", { class: "botao secundario", type: "button", onclick: editar(v) }, "Editar"),
            h("button", { class: "botao secundario", type: "button", onclick: duplicar(v) }, "Duplicar +7 dias"),
            h("button", { class: "botao secundario", type: "button", "aria-pressed": String(v.ativo),
              onclick: alterar(v, { ativo: !v.ativo }, v.ativo ? "Viagem desativada" : "Viagem ativada ✔") }, v.ativo ? "Desativar" : "Ativar"))));
      })))) : h("p", { class: "painel" }, "Nenhuma viagem cadastrada. Cadastre as saídas dos barcos para mostrar ao cliente quando o pedido chega."));
}

// -- encomendas ("Encomenda pra mim")

const STATUS_ENCOMENDA_ADM = { nova: "Nova", cotada: "Cotada", aceita: "Aceita pelo cliente", recusada: "Recusada", comprada: "Comprada",
  entregue: "Entregue", cancelada: "Cancelada" };
const ACAO_ENCOMENDA_ADM = { nova: "Voltar para nova", cotada: "Marcar como cotada", aceita: "Marcar como aceita", recusada: "Marcar como recusada",
  comprada: "Marcar como comprada", entregue: "Marcar como entregue", cancelada: "Cancelar encomenda" };
let filtroEncomendas = "";

function linkSeguroAdm(link) {
  if (!link) return null;
  const http = /^https?:\/\//i.test(link);
  return http ? h("a", { class: "link-externo", href: link, target: "_blank", rel: "noopener noreferrer nofollow" }, link, " ↗")
    : h("span", { class: "link-externo" }, link);
}

function mensagemCotacao(enc) {
  const site = (estado.loja && estado.loja.site) || location.origin;
  const primeiro = (enc.nome || "").split(" ")[0];
  return [`Olá, ${primeiro}! Aqui é da Tipiti. Cotamos a sua encomenda ${enc.codigo}:`,
    `Valor: ${brl(enc.cotacao_centavos)} (${enc.quantidade} ${enc.quantidade === 1 ? "unidade" : "unidades"})`,
    `Prazo: cerca de ${enc.prazo_dias} dias`,
    enc.observacao ? enc.observacao : null,
    `Para aceitar ou recusar: ${site}/encomenda/${enc.codigo}`].filter(Boolean).join("\n");
}

function cartaoEncomenda(auth, enc) {
  const id = enc.codigo.toLowerCase();
  const cotavel = ["nova", "cotada", "recusada"].includes(enc.status);
  const alerta = h("div", { class: "alerta", hidden: true, role: "alert" });
  const form = cotavel ? h("form", { class: "form-linha", novalidate: true },
    campo(`valor-${id}`, "Valor total (R$)", { name: "valor", inputmode: "decimal", placeholder: "149,90", value: textoReais(enc.cotacao_centavos) }, ""),
    campo(`prazo-${id}`, "Prazo (dias)", { name: "prazo", type: "number", min: 1, max: 365, inputmode: "numeric", value: enc.prazo_dias ?? "" }, ""),
    campo(`obs-${id}`, "Observação para o cliente", { name: "observacao", maxlength: 1000, value: enc.observacao || "", placeholder: "opcional" }, "cresce"),
    h("button", { class: "botao", type: "submit" }, enc.status === "cotada" ? "Atualizar cotação" : "Enviar cotação")) : null;
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      alerta.hidden = true;
      const f = form.elements;
      const valor = reais(f.valor.value);
      const prazo = parseInt(f.prazo.value, 10);
      const erros = {};
      if (!(valor > 0)) erros[`valor-${id}`] = "Informe o valor, ex.: 149,90.";
      if (!(prazo >= 1 && prazo <= 365)) erros[`prazo-${id}`] = "Prazo de 1 a 365 dias.";
      if (Object.keys(erros).length) return mostrarErros(form, erros);
      try {
        await enviarAdmin(auth, `/api/admin/encomendas/${enc.codigo}`, "PATCH", { cotacao_centavos: valor, prazo_dias: prazo, observacao: f.observacao.value.trim() });
        avisar("Cotação salva ✔ Agora avise o cliente pelo WhatsApp.");
        atualizarAba();
      } catch (err) {
        const mapa = { cotacao_centavos: `valor-${id}`, prazo_dias: `prazo-${id}`, observacao: `obs-${id}` };
        const campos = Object.fromEntries(Object.entries(err.campos || {}).map(([k, m]) => [mapa[k] || k, m]));
        erroFormAdm(form, alerta, { message: err.message, status: err.status, campos });
      }
    });
  }
  const mudar = (status) => async () => {
    if (status === "cancelada" && !confirm(`Cancelar a encomenda ${enc.codigo}?`)) return;
    try {
      await enviarAdmin(auth, `/api/admin/encomendas/${enc.codigo}`, "PATCH", { status });
      avisar(`Encomenda: ${STATUS_ENCOMENDA_ADM[status] || status} ✔`);
      atualizarAba();
    } catch (err) { if (err.status !== 401) avisar(err.message); }
  };
  const proximos = (enc.proximos_status || []).filter((s) => s !== "cotada");  // cotar é pelo formulário
  const cotada = enc.cotacao_centavos !== null && enc.cotacao_centavos !== undefined && enc.prazo_dias;
  return h("article", { class: `cartao-admin enc-${enc.status}`, "aria-labelledby": `enc-${id}` },
    h("header", { class: "pedido-cabeca" },
      h("div", {}, h("b", { id: `enc-${id}`, class: "codigo-pedido" }, enc.codigo), " ",
        h("span", { class: `etiqueta enc-st-${enc.status}` }, STATUS_ENCOMENDA_ADM[enc.status] || enc.status),
        h("div", { class: "parcelado" }, `Pedida em ${quandoAdm(enc.criado_em)}`)),
      h("div", { class: "pedido-total" }, h("b", {}, `${enc.quantidade} ${enc.quantidade === 1 ? "unidade" : "unidades"}`))),
    h("div", { class: "pedido-corpo" },
      h("section", {}, h("h3", {}, "Cliente"), h("div", {}, enc.nome),
        h("div", { class: "parcelado" }, `${enc.cidade}/${enc.uf}`),
        h("div", { class: "parcelado" }, telefoneAdm(enc.whatsapp))),
      h("section", { class: "largo" }, h("h3", {}, "O que o cliente quer"),
        enc.link ? h("div", {}, linkSeguroAdm(enc.link)) : null,
        enc.descricao ? h("p", { class: "texto-cliente" }, enc.descricao) : null,
        cotada ? h("p", { class: "cotacao-admin" }, h("b", {}, `Cotação: ${brl(enc.cotacao_centavos)}`), ` · prazo ${enc.prazo_dias} dias`,
          enc.observacao ? h("span", { class: "parcelado" }, ` · ${enc.observacao}`) : null) : null)),
    form, alerta,
    h("div", { class: "pedido-acoes" },
      botaoZapAdm(zapAdm(enc.whatsapp, cotada ? mensagemCotacao(enc) : `Olá, ${(enc.nome || "").split(" ")[0]}! Aqui é da Tipiti, sobre a sua encomenda ${enc.codigo}.`),
        cotada && enc.status === "cotada" ? "Mandar cotação no WhatsApp" : "WhatsApp do cliente"),
      proximos.map((s) => h("button", { class: `botao secundario${s === "cancelada" ? " perigo" : ""}`, type: "button", onclick: mudar(s) }, ACAO_ENCOMENDA_ADM[s] || s))));
}

async function painelEncomendas(auth) {
  const url = filtroEncomendas ? `/api/admin/encomendas?status=${encodeURIComponent(filtroEncomendas)}` : "/api/admin/encomendas";
  const encomendas = await api(url, { headers: auth });
  const lista = Array.isArray(encomendas) ? encomendas : [];
  return h("div", { class: "pilha" },
    h("div", { class: "barra-admin" },
      filtroAdm("filtro-encomendas", "Mostrar", [["", "Todas"], ...Object.entries(STATUS_ENCOMENDA_ADM)], filtroEncomendas, (v) => { filtroEncomendas = v; atualizarAba(); }),
      h("span", { class: "parcelado" }, `${lista.length} encomenda${lista.length === 1 ? "" : "s"}`)),
    h("p", { class: "parcelado" }, "Pedidos de “Encomenda pra mim”. Abra o link com cuidado: ele foi enviado pelo cliente. Cote o valor e o prazo; o cliente aceita ou recusa na página da encomenda."),
    lista.length ? lista.map((enc) => cartaoEncomenda(auth, enc))
      : h("p", { class: "painel" }, filtroEncomendas ? "Nenhuma encomenda com este status." : "Nenhuma encomenda ainda."));
}

// -- avise-me

const STATUS_AVISE_ADM = { aguardando: "Aguardando estoque", pronto: "Pronto para avisar", avisado: "Avisado" };
let filtroAviseMe = "";

async function painelAviseMe(auth) {
  const url = filtroAviseMe ? `/api/admin/avise-me?status=${encodeURIComponent(filtroAviseMe)}` : "/api/admin/avise-me";
  const avisos = await api(url, { headers: auth });
  const lista = (Array.isArray(avisos) ? avisos : []).slice()
    .sort((a, b) => (a.status === "pronto" ? 0 : 1) - (b.status === "pronto" ? 0 : 1));
  const prontos = lista.filter((a) => a.status === "pronto").length;
  const mudar = (a, status, ok) => async () => {
    try { await enviarAdmin(auth, `/api/admin/avise-me/${a.id}`, "PATCH", { status }); avisar(ok); atualizarAba(); }
    catch (err) { if (err.status !== 401) avisar(err.message); }
  };
  return h("div", { class: "pilha" },
    h("div", { class: "barra-admin" },
      filtroAdm("filtro-avise", "Mostrar", [["", "Todos"], ...Object.entries(STATUS_AVISE_ADM)], filtroAviseMe, (v) => { filtroAviseMe = v; atualizarAba(); }),
      h("span", { class: "parcelado" }, prontos ? `${prontos} pronto${prontos === 1 ? "" : "s"} para avisar` : `${lista.length} pedido${lista.length === 1 ? "" : "s"} de aviso`)),
    h("p", { class: "parcelado" }, "Quando o estoque volta, quem deixou e-mail recebe o aviso sozinho (com o e-mail ligado). Quem deixou WhatsApp aparece aqui como “Pronto para avisar”: toque no botão do WhatsApp e depois marque como avisado."),
    lista.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-avise" },
      h("thead", {}, h("tr", {}, ["Produto", "Contato", "Situação", "Pedido em", ""].map((t) => h("th", {}, t)))),
      h("tbody", {}, lista.map((a) => h("tr", { class: a.status === "pronto" ? "pendente" : "" },
        celula("Produto", {}, a.produto ? h("a", { href: `/admin/produto/${a.produto.slug}` }, a.produto.nome) : "—",
          a.variacao ? h("div", { class: "parcelado" }, `Opção: ${a.variacao}`) : null),
        celula("Contato", {}, a.nome || h("span", { class: "parcelado" }, "sem nome"),
          a.email ? h("div", { class: "parcelado" }, a.email, a.email_enviado ? " · e-mail enviado" : "") : null,
          a.whatsapp ? h("div", { class: "parcelado" }, telefoneAdm(a.whatsapp)) : null),
        celula("Situação", {}, h("span", { class: `etiqueta ${a.status === "pronto" ? "agendado" : a.status === "avisado" ? "ativo" : "inativo"}` }, STATUS_AVISE_ADM[a.status] || a.status)),
        celula("Pedido em", {}, quandoAdm(a.criado_em)),
        celula("", { class: "celula-acao" }, h("div", { class: "acoes-cupom" },
          a.whatsapp_link && a.status !== "aguardando" ? botaoZapAdm(a.whatsapp_link, "Avisar no WhatsApp") : null,
          a.status !== "avisado" ? h("button", { class: "botao secundario", type: "button", onclick: mudar(a, "avisado", "Marcado como avisado ✔") }, "Marcar como avisado")
            : h("button", { class: "botao secundario", type: "button", onclick: mudar(a, "pronto", "Voltou para “pronto para avisar”") }, "Desfazer"))))))))
      : h("p", { class: "painel" }, filtroAviseMe ? "Nada com este status." : "Ninguém pediu aviso ainda. O botão “Avise-me quando chegar” aparece nos produtos sem estoque."));
}

// -- carrinhos abandonados

const STATUS_CARRINHO_ADM = { abandonado: "Abandonados (sem pedido há mais de 1 h)", aberto: "Em aberto", convertido: "Viraram pedido" };
let filtroCarrinhos = "abandonado";

async function painelCarrinhos(auth) {
  const carrinhos = await api(`/api/admin/carrinhos?status=${encodeURIComponent(filtroCarrinhos)}`, { headers: auth });
  const lista = Array.isArray(carrinhos) ? carrinhos : [];
  const marcar = (c, enviado) => async () => {
    try {
      await enviarAdmin(auth, `/api/admin/carrinhos/${encodeURIComponent(c.id)}`, "PATCH", { lembrete_enviado: enviado });
      avisar(enviado ? "Lembrete marcado como enviado ✔" : "Lembrete desmarcado");
      atualizarAba();
    } catch (err) { if (err.status !== 401) avisar(err.message); }
  };
  return h("div", { class: "pilha" },
    h("div", { class: "barra-admin" },
      filtroAdm("filtro-carrinhos", "Mostrar", Object.entries(STATUS_CARRINHO_ADM), filtroCarrinhos, (v) => { filtroCarrinhos = v; atualizarAba(); }),
      h("span", { class: "parcelado" }, `${lista.length} carrinho${lista.length === 1 ? "" : "s"}`)),
    h("p", { class: "parcelado" }, "Só aparecem clientes que autorizaram o contato por WhatsApp no checkout. A mensagem leva um link que devolve o carrinho como estava. Os dados são apagados depois de 30 dias."),
    lista.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-carrinhos" },
      h("thead", {}, h("tr", {}, ["Cliente", "Itens", "Total", "Última atividade", "Lembrete", ""].map((t) => h("th", {}, t)))),
      h("tbody", {}, lista.map((c) => h("tr", { class: c.lembrete_enviado ? "" : "pendente" },
        celula("Cliente", {}, c.nome || h("span", { class: "parcelado" }, "sem nome"), h("div", { class: "parcelado" }, telefoneAdm(c.whatsapp))),
        celula("Itens", {}, (c.itens || []).map((i) => h("div", {}, `${i.quantidade}× ${i.nome}`))),
        celula("Total", {}, brl(c.total_centavos || 0)),
        celula("Última atividade", {}, quandoAdm(c.atualizado_em)),
        celula("Lembrete", {}, c.lembrete_enviado ? h("span", { class: "etiqueta ativo" }, `Enviado${c.lembrete_em ? ` ${quandoAdm(c.lembrete_em)}` : ""}`)
          : h("span", { class: "etiqueta agendado" }, "Não enviado")),
        celula("", { class: "celula-acao" }, h("div", { class: "acoes-cupom" },
          c.status !== "convertido" && c.whatsapp_link ? botaoZapAdm(c.whatsapp_link, "Lembrar no WhatsApp") : null,
          c.lembrete_enviado ? h("button", { class: "botao secundario", type: "button", onclick: marcar(c, false) }, "Desmarcar")
            : h("button", { class: "botao secundario", type: "button", onclick: marcar(c, true) }, "Marcar lembrete enviado"))))))))
      : h("p", { class: "painel" }, filtroCarrinhos === "abandonado" ? "Nenhum carrinho abandonado agora." : "Nada por aqui."));
}
