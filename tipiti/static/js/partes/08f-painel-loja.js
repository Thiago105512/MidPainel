// ------------------------------------------------------------- painel: pré-venda, feeds, revendedoras, LGPD, e-mails e histórico

/** Hoje no horário de Manaus (UTC−4), "AAAA-MM-DD". */
const hojeManausAdm = (dias = 0) => new Date(Date.now() - FUSO_MANAUS_HORAS * 3600000 + dias * 86400000).toISOString().slice(0, 10);

// -- pré-venda (editor do produto)

function secaoPrevenda(auth, p) {
  if (!("prevenda" in p)) return null;  // servidor antigo
  const ativa = Boolean(p.prevenda && p.prevenda.chegada);
  const alerta = h("div", { class: "alerta", hidden: true, role: "alert" });
  const form = h("form", { class: "painel", novalidate: true, "aria-labelledby": "titulo-prevenda" },
    h("h2", { id: "titulo-prevenda" }, "📦 Pré-venda do próximo lote"),
    h("p", { class: "parcelado" }, "Venda antes de o lote chegar. Com a data de chegada preenchida, o ", h("b", {}, "estoque passa a ser as vagas do lote"),
      " (quantas unidades você vai trazer), o produto ganha o selo “Pré-venda” e o prazo de entrega conta a partir da chegada. Quando a data passar, o produto volta ao normal: ajuste o estoque quando o lote chegar."),
    ativa ? h("p", { class: "estado-oferta ativa" }, `Em pré-venda: o lote chega em ${dataBrAdm(p.prevenda.chegada)}. Estoque atual = ${p.estoque} vaga(s).`)
      : h("p", { class: "estado-oferta" }, "Este produto não está em pré-venda."),
    h("div", { class: "grade-form" },
      campo("prevenda_chegada", "Chegada do lote (data)", { type: "date", min: hojeManausAdm(1), value: ativa ? p.prevenda.chegada : "" }, "c3")),
    alerta,
    h("div", { class: "compra" },
      h("button", { class: "botao", type: "submit" }, ativa ? "Mudar a data" : "Começar pré-venda"),
      ativa ? h("button", { class: "botao secundario", type: "button", onclick: async () => {
        if (!confirm("Encerrar a pré-venda? O estoque volta a ser o estoque normal do produto.")) return;
        try {
          await enviarAdmin(auth, `/api/admin/produtos/${p.slug}`, "PATCH", { prevenda_chegada: null });
          avisar("Pré-venda encerrada ✔");
          rotear();
        } catch (err) { erroFormAdm(form, alerta, err); }
      } }, "Encerrar pré-venda") : null));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    alerta.hidden = true;
    const data = form.elements.prevenda_chegada.value;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(data)) return mostrarErros(form, { prevenda_chegada: "Escolha a data de chegada do lote." });
    if (data <= hojeManausAdm()) return mostrarErros(form, { prevenda_chegada: "A chegada precisa ser depois de hoje." });
    try {
      await enviarAdmin(auth, `/api/admin/produtos/${p.slug}`, "PATCH", { prevenda_chegada: data });
      avisar("Pré-venda salva ✔ Confira o estoque: agora ele vale como vagas do lote.");
      rotear();
    } catch (err) { erroFormAdm(form, alerta, err); }
  });
  return form;
}

// -- feeds Google / Instagram

async function painelFeeds(auth) {
  const f = await api("/api/admin/feeds", { headers: auth });
  const linhaFeed = (titulo, url, dica) => h("div", { class: "feed-linha" },
    h("h3", {}, titulo), h("code", { class: "url-feed" }, url),
    h("div", { class: "acoes-cupom" }, botaoCopiar(url, "Copiar endereço", "Endereço copiado ✔"),
      h("a", { class: "botao secundario", href: url, target: "_blank", rel: "noopener noreferrer" }, "Abrir ↗")),
    h("p", { class: "parcelado" }, dica));
  const semFoto = Array.isArray(f.sem_foto) ? f.sem_foto : [];
  return h("div", { class: "pilha" },
    h("section", { class: "painel" },
      h("h2", {}, "Feeds de produtos (Google e Instagram)"),
      h("p", {}, h("b", {}, `${f.produtos_no_feed} produto${f.produtos_no_feed === 1 ? "" : "s"}`), " no feed. Só entram produtos no ar e com foto de verdade (Google e Meta não aceitam as imagens provisórias)."),
      linhaFeed("Google Shopping", f.google, "No Google Merchant Center: Produtos → Feeds → adicionar feed → “Busca programada” → cole este endereço."),
      linhaFeed("Instagram / Facebook (Meta)", f.meta, "No Gerenciador de Comércio da Meta: Catálogo → Fontes de dados → Feed de dados → “Usar URL” → cole este endereço.")),
    h("section", { class: "painel" },
      h("h2", {}, semFoto.length ? `Fora do feed por falta de foto (${semFoto.length})` : "Todos os produtos no ar têm foto ✔"),
      semFoto.length ? h("ul", { class: "lista-links" }, semFoto.map((p) => h("li", {},
        h("a", { href: `/admin/produto/${p.slug}` }, p.nome), " — ", h("span", { class: "parcelado" }, "abrir o editor e adicionar fotos")))) : null));
}

// -- revendedoras

const STATUS_REVENDEDORA_ADM = { pendente: "Pendente", ativa: "Ativa", inativa: "Inativa" };
let filtroRevendedoras = "";
const pagamentosFeitos = new Map();  // id -> resultado do último "pagar até" (sobrevive ao redesenho)

function linhaCopiar(rotulo, valor, aviso) {
  return valor ? h("div", { class: "linha-copiar" }, h("small", {}, rotulo), h("code", {}, valor), botaoCopiar(valor, "Copiar", aviso)) : null;
}

function cartaoRevendedora(auth, r) {
  const id = r.id;
  const patch = async (dados, ok) => {
    try { await enviarAdmin(auth, `/api/admin/revendedoras/${id}`, "PATCH", dados); avisar(ok); atualizarAba(); }
    catch (err) { if (err.status !== 401) avisar(err.message); }
  };
  const alerta = h("div", { class: "alerta", hidden: true, role: "alert" });
  const formPct = h("form", { class: "form-linha", novalidate: true },
    campo(`comissao-${id}`, "Comissão dela (%)", { name: "comissao", type: "number", min: 0, max: 50, inputmode: "numeric", value: r.comissao_pct ?? 10 }, ""),
    campo(`desconto-${id}`, "Desconto do cliente (%)", { name: "desconto", type: "number", min: 0, max: 50, inputmode: "numeric", value: r.desconto_cliente_pct ?? 5 }, ""),
    h("button", { class: "botao", type: "submit" }, r.status === "pendente" ? "Aprovar revendedora" : r.status === "inativa" ? "Reativar" : "Salvar porcentagens"));
  formPct.addEventListener("submit", async (e) => {
    e.preventDefault();
    alerta.hidden = true;
    const comissao = Number(formPct.elements.comissao.value);
    const desconto = Number(formPct.elements.desconto.value);
    const erros = {};
    if (!Number.isInteger(comissao) || comissao < 0 || comissao > 50) erros[`comissao-${id}`] = "De 0 a 50%.";
    if (!Number.isInteger(desconto) || desconto < 0 || desconto > 50) erros[`desconto-${id}`] = "De 0 a 50%.";
    if (Object.keys(erros).length) return mostrarErros(formPct, erros);
    try {
      await enviarAdmin(auth, `/api/admin/revendedoras/${id}`, "PATCH", { status: "ativa", comissao_pct: comissao, desconto_cliente_pct: desconto });
      avisar(r.status === "ativa" ? "Porcentagens salvas ✔" : "Revendedora ativa ✔ Mande as boas-vindas pelo WhatsApp.");
      atualizarAba();
    } catch (err) {
      const mapa = { comissao_pct: `comissao-${id}`, desconto_cliente_pct: `desconto-${id}` };
      erroFormAdm(formPct, alerta, { message: err.message, status: err.status,
        campos: Object.fromEntries(Object.entries(err.campos || {}).map(([k, m]) => [mapa[k] || k, m])) });
    }
  });
  const pago = pagamentosFeitos.get(id);
  const formPagar = h("form", { class: "form-linha", novalidate: true },
    campo(`ate-${id}`, "Pagar comissões dos pedidos feitos até", { name: "ate", type: "date", max: hojeManausAdm(), value: hojeManausAdm() }, ""),
    h("button", { class: "botao secundario", type: "submit" }, "Registrar pagamento"));
  formPagar.addEventListener("submit", async (e) => {
    e.preventDefault();
    const ate = formPagar.elements.ate.value;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(ate)) return mostrarErros(formPagar, { [`ate-${id}`]: "Escolha a data." });
    if (!confirm(`Registrar como pagas as comissões de ${r.nome} dos pedidos até ${dataBrAdm(ate)}? (Faça o Pix para ela antes ou depois, fora do painel.)`)) return;
    try {
      const res = await enviarAdmin(auth, `/api/admin/revendedoras/${id}/pagamentos`, "POST", { ate });
      pagamentosFeitos.set(id, res);
      avisar(res.pago_centavos ? `Pagamento registrado: ${brl(res.pago_centavos)} ✔` : "Nada a pagar até essa data.");
      atualizarAba();
    } catch (err) { if (err.status !== 401) avisar(err.message); }
  });
  const t = r.totais || {};
  const boasVindas = r.whatsapp_boas_vindas ? zapAdm(r.whatsapp, r.whatsapp_boas_vindas) : null;
  return h("article", { class: `cartao-admin rev-${r.status}`, "aria-labelledby": `rev-${id}` },
    h("header", { class: "pedido-cabeca" },
      h("div", {}, h("b", { id: `rev-${id}` }, r.nome), " ", h("span", { class: `etiqueta ${r.status === "ativa" ? "ativo" : r.status === "pendente" ? "agendado" : "inativo"}` }, STATUS_REVENDEDORA_ADM[r.status] || r.status),
        h("div", { class: "parcelado" }, `${r.cidade}/${r.uf} · cadastro em ${quandoAdm(r.criado_em)}`)),
      r.codigo ? h("div", { class: "pedido-total" }, h("code", {}, r.codigo)) : null),
    h("div", { class: "pedido-corpo" },
      h("section", {}, h("h3", {}, "Contato"), h("div", {}, telefoneAdm(r.whatsapp)),
        r.cpf ? h("div", { class: "parcelado" }, `CPF ${mascaraCpf(r.cpf)}`) : null,
        r.instagram ? h("div", { class: "parcelado" }, `Instagram: ${r.instagram}`) : null,
        r.mensagem ? h("p", { class: "texto-cliente" }, r.mensagem) : null),
      r.status !== "pendente" ? h("section", {}, h("h3", {}, "Vendas e comissões"),
        h("div", {}, `${t.vendas || 0} venda(s) que contam`),
        h("div", {}, "A receber: ", h("b", {}, brl(t.a_receber_centavos || 0))),
        h("div", { class: "parcelado" }, `Já pago: ${brl(t.pago_centavos || 0)}`),
        h("div", { class: "parcelado" }, `Comissão ${r.comissao_pct}% · desconto do cliente ${r.desconto_cliente_pct}%`),
        r.cupom ? h("div", { class: "parcelado" }, `Cupom ${r.cupom.codigo} (${r.cupom.descricao})`) : null) : null,
      r.status === "ativa" ? h("section", { class: "largo" }, h("h3", {}, "Links"),
        linhaCopiar("Link para ela divulgar", r.link_divulgacao, "Link de divulgação copiado ✔"),
        r.link_painel ? h("details", { class: "detalhes-admin" }, h("summary", {}, "Link do painel dela (secreto: só para ela)"),
          linhaCopiar("Painel da revendedora", r.link_painel, "Link do painel copiado ✔"),
          h("button", { class: "link-botao", type: "button", onclick: () => {
            if (confirm(`Gerar um novo link do painel para ${r.nome}? O link antigo para de funcionar.`)) patch({ novo_token: true }, "Novo link gerado ✔ Mande para ela.");
          } }, "Gerar novo link (o antigo deixa de funcionar)")) : null) : null),
    h("div", { class: "pilha-form" },
      formPct, alerta,
      r.status === "ativa" ? [formPagar,
        pago ? h("p", { class: "resultado-pagamento", role: "status" }, `Último pagamento registrado: ${brl(pago.pago_centavos)} em ${pago.pedidos} pedido(s), até ${dataBrAdm(pago.ate)}.`) : null] : null),
    h("div", { class: "pedido-acoes" },
      boasVindas ? botaoZapAdm(boasVindas, "Mandar boas-vindas no WhatsApp") : botaoZapAdm(zapAdm(r.whatsapp, `Olá, ${(r.nome || "").split(" ")[0]}! Aqui é da Tipiti, sobre o seu cadastro de revendedora.`), "WhatsApp dela"),
      r.status === "pendente" ? h("button", { class: "botao secundario perigo", type: "button", onclick: () => {
        if (confirm(`Recusar o cadastro de ${r.nome}?`)) patch({ status: "inativa" }, "Cadastro recusado.");
      } }, "Recusar") : null,
      r.status === "ativa" ? h("button", { class: "botao secundario perigo", type: "button", onclick: () => {
        if (confirm(`Desativar ${r.nome}? O link e o cupom dela param de funcionar.`)) patch({ status: "inativa" }, "Revendedora desativada.");
      } }, "Desativar") : null));
}

async function painelRevendedoras(auth) {
  const url = filtroRevendedoras ? `/api/admin/revendedoras?status=${encodeURIComponent(filtroRevendedoras)}` : "/api/admin/revendedoras";
  const lista = await api(url, { headers: auth });
  const revendedoras = Array.isArray(lista) ? lista : [];
  const pendentes = revendedoras.filter((r) => r.status === "pendente").length;
  return h("div", { class: "pilha" },
    h("div", { class: "barra-admin" },
      filtroAdm("filtro-revendedoras", "Mostrar", [["", "Todas"], ...Object.entries(STATUS_REVENDEDORA_ADM)], filtroRevendedoras, (v) => { filtroRevendedoras = v; atualizarAba(); }),
      h("span", { class: "parcelado" }, pendentes ? `${pendentes} aguardando aprovação` : `${revendedoras.length} revendedora${revendedoras.length === 1 ? "" : "s"}`)),
    h("p", { class: "parcelado" }, "Cadastros chegam pela página “Seja revendedora”. Ao aprovar, ela ganha o link de divulgação, um painel próprio e, com desconto para o cliente, um cupom com o código dela. A comissão conta sobre os produtos (sem o frete) dos pedidos pagos."),
    revendedoras.length ? revendedoras.map((r) => cartaoRevendedora(auth, r))
      : h("p", { class: "painel" }, filtroRevendedoras ? "Nenhuma com este status." : "Nenhum cadastro de revendedora ainda."));
}

// -- privacidade (LGPD)

const STATUS_LGPD_ADM = { aberta: "Aberta", em_andamento: "Em andamento", concluida: "Concluída" };
let filtroPrivacidade = "";

function cartaoSolicitacao(auth, s) {
  const aviso = h("div", { class: "alerta", hidden: true, role: "alert" });
  const mostrarAviso = (texto) => { aviso.textContent = texto; aviso.hidden = false; aviso.scrollIntoView({ block: "nearest" }); };
  const vencida = s.status !== "concluida" && s.prazo_resposta && s.prazo_resposta < hojeManausAdm();
  const id = s.protocolo.toLowerCase();
  const form = h("form", { class: "pilha-form", novalidate: true },
    h("div", { class: "campo" }, h("label", { for: `st-${id}` }, "Situação"),
      h("select", { id: `st-${id}`, name: "status", class: "campo-select" },
        Object.entries(STATUS_LGPD_ADM).map(([v, t]) => h("option", { value: v, selected: v === s.status }, t)))),
    h("div", { class: "campo" }, h("label", { for: `resp-${id}` }, "Resposta ao titular (vai por e-mail)"),
      h("textarea", { id: `resp-${id}`, name: "resposta", rows: 3, maxlength: 5000, class: "campo-texto", placeholder: "Ex.: Enviamos a cópia dos seus dados para este e-mail." })),
    h("button", { class: "botao", type: "submit" }, "Salvar resposta"));
  form.elements.resposta.value = s.resposta || "";
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    aviso.hidden = true;
    const resposta = form.elements.resposta.value.trim();
    try {
      await enviarAdmin(auth, `/api/admin/privacidade/${s.protocolo}`, "PATCH", { status: form.elements.status.value, ...(resposta ? { resposta } : {}) });
      avisar(resposta && resposta !== (s.resposta || "") ? "Resposta salva ✔ O titular recebe por e-mail." : "Solicitação atualizada ✔");
      atualizarAba();
    } catch (err) { if (err.status !== 401) mostrarAviso(err.message); }
  });
  const exportar = async () => {
    if (!confirm("Você confirmou a identidade de quem pediu (é o titular do e-mail e do CPF)? Os dados pessoais só podem ir para o próprio titular.")) return;
    try {
      const dados = await enviarAdmin(auth, `/api/admin/privacidade/${s.protocolo}/dados`, "GET");
      baixarJsonAdm(`dados-${s.protocolo}.json`, dados);
      avisar("Arquivo baixado ✔ Envie só para o titular.");
    } catch (err) { if (err.status !== 401) mostrarAviso(err.message); }
  };
  const anonimizar = async () => {
    const digitado = prompt(`ANONIMIZAR é definitivo: nome, e-mail, CPF, telefone e endereço de ${s.email} são apagados de pedidos, encomendas e cadastro (os valores ficam, por obrigação fiscal). Confirme a identidade do titular antes.\n\nPara confirmar, digite o protocolo ${s.protocolo}:`);
    if (digitado === null) return;
    if (digitado.trim().toUpperCase() !== s.protocolo.toUpperCase()) { mostrarAviso("O protocolo digitado não confere. Nada foi alterado."); return; }
    try {
      await enviarAdmin(auth, `/api/admin/privacidade/${s.protocolo}/anonimizar`, "POST", {});
      avisar("Dados anonimizados ✔");
      atualizarAba();
    } catch (err) { if (err.status !== 401) mostrarAviso(err.message); }  // o motivo da recusa, como veio do servidor
  };
  return h("article", { class: `cartao-admin${vencida ? " vencida" : ""}`, "aria-labelledby": `lgpd-${id}` },
    h("header", { class: "pedido-cabeca" },
      h("div", {}, h("b", { id: `lgpd-${id}`, class: "codigo-pedido" }, s.protocolo), " ",
        h("span", { class: `etiqueta ${s.status === "concluida" ? "ativo" : s.status === "aberta" ? "agendado" : "inativo"}` }, s.status_nome || STATUS_LGPD_ADM[s.status]),
        h("div", { class: "parcelado" }, `${s.tipo_nome} · recebida em ${quandoAdm(s.criado_em)}`)),
      h("div", { class: "pedido-total" }, h("small", {}, "Responder até"), h("b", { class: vencida ? "atrasado" : "" }, dataBrAdm(s.prazo_resposta)))),
    h("div", { class: "pedido-corpo" },
      h("section", {}, h("h3", {}, "Titular"), h("div", {}, s.email), h("div", { class: "parcelado" }, `CPF ${mascaraCpf(s.cpf || "")}`),
        s.anonimizado_em ? h("div", { class: "etiqueta inativo" }, `Anonimizado em ${quandoAdm(s.anonimizado_em)}`) : null),
      h("section", { class: "largo" }, h("h3", {}, "Mensagem"), s.mensagem ? h("p", { class: "texto-cliente" }, s.mensagem) : h("p", { class: "parcelado" }, "Sem mensagem."))),
    aviso,
    form,
    h("div", { class: "pedido-acoes" },
      h("button", { class: "botao secundario", type: "button", onclick: exportar }, "⬇️ Exportar dados (JSON)"),
      s.anonimizado_em ? null : h("button", { class: "botao secundario perigo", type: "button", onclick: anonimizar }, "Anonimizar dados")));
}

async function painelPrivacidade(auth) {
  const url = filtroPrivacidade ? `/api/admin/privacidade?status=${encodeURIComponent(filtroPrivacidade)}` : "/api/admin/privacidade";
  const lista = await api(url, { headers: auth });
  const solicitacoes = Array.isArray(lista) ? lista : [];
  return h("div", { class: "pilha" },
    h("div", { class: "info-box" }, h("b", {}, "Antes de exportar ou anonimizar: "),
      "confirme que quem pediu é mesmo o titular (por exemplo, responda pelo e-mail do pedido e peça para confirmar dados que só ele sabe). O prazo para responder é de 15 dias."),
    h("div", { class: "barra-admin" },
      filtroAdm("filtro-privacidade", "Mostrar", [["", "Todas"], ...Object.entries(STATUS_LGPD_ADM)], filtroPrivacidade, (v) => { filtroPrivacidade = v; atualizarAba(); }),
      h("span", { class: "parcelado" }, `${solicitacoes.length} solicitaç${solicitacoes.length === 1 ? "ão" : "ões"}`)),
    solicitacoes.length ? solicitacoes.map((s) => cartaoSolicitacao(auth, s))
      : h("p", { class: "painel" }, filtroPrivacidade ? "Nenhuma com este status." : "Nenhuma solicitação de titular. Elas chegam pela página “Meus dados”."));
}

// -- e-mails

const STATUS_EMAIL_ADM = { pendente: "Pendente", enviando: "Enviando", enviado: "Enviado", falhou: "Falhou" };
let filtroEmails = "";

async function painelEmails(auth) {
  const url = filtroEmails ? `/api/admin/emails?status=${encodeURIComponent(filtroEmails)}` : "/api/admin/emails";
  const [lista, resumo] = await Promise.all([api(url, { headers: auth }), api("/api/admin/resumo", { headers: auth }).catch(() => null)]);
  const emails = Array.isArray(lista) ? lista : [];
  const reenviar = (m) => async () => {
    try { await enviarAdmin(auth, `/api/admin/emails/${m.id}/reenviar`, "POST", {}); avisar("E-mail colocado na fila de novo ✔"); atualizarAba(); }
    catch (err) { if (err.status !== 401) avisar(err.message); }
  };
  return h("div", { class: "pilha" },
    caixaEmail(resumo),
    h("div", { class: "barra-admin" },
      filtroAdm("filtro-emails", "Mostrar", [["", "Todos"], ...Object.entries(STATUS_EMAIL_ADM)], filtroEmails, (v) => { filtroEmails = v; atualizarAba(); }),
      h("span", { class: "parcelado" }, `${emails.length} e-mail${emails.length === 1 ? "" : "s"}`)),
    emails.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-emails" },
      h("thead", {}, h("tr", {}, ["Para", "Assunto", "Situação", "Criado", ""].map((t) => h("th", {}, t)))),
      h("tbody", {}, emails.map((m) => h("tr", { class: m.status === "falhou" ? "pendente" : "" },
        celula("Para", {}, h("span", { class: "quebra" }, m.para)),
        celula("Assunto", {}, m.assunto, m.erro ? h("div", { class: "msg-erro" }, `Erro: ${m.erro}`) : null),
        celula("Situação", {}, h("span", { class: `etiqueta ${m.status === "enviado" ? "ativo" : m.status === "falhou" ? "erro" : "agendado"}` }, STATUS_EMAIL_ADM[m.status] || m.status),
          m.tentativas ? h("div", { class: "parcelado" }, `${m.tentativas} tentativa(s)`) : null,
          m.enviado_em ? h("div", { class: "parcelado" }, `Enviado ${quandoAdm(m.enviado_em)}`) : null),
        celula("Criado", {}, quandoAdm(m.criado_em)),
        celula("", { class: "celula-acao" }, m.status === "enviando" ? null
          : h("button", { class: "botao secundario", type: "button", onclick: reenviar(m) }, m.status === "enviado" ? "Enviar de novo" : "Reenviar")))))))
      : h("p", { class: "painel" }, filtroEmails ? "Nenhum e-mail com este status." : "Nenhum e-mail na fila ainda."));
}

// -- histórico

const filtroHistorico = { usuario: "", alvo: "", pagina: 1 };

function textoDetalhes(d) {
  if (d === null || d === undefined || d === "") return "";
  return typeof d === "string" ? d : JSON.stringify(d);
}

async function painelHistorico(auth) {
  const q = new URLSearchParams({ pagina: String(filtroHistorico.pagina), por_pagina: "50" });
  if (filtroHistorico.usuario) q.set("usuario", filtroHistorico.usuario);
  if (filtroHistorico.alvo) q.set("alvo", filtroHistorico.alvo);
  const [res, usuarios] = await Promise.all([api(`/api/admin/historico?${q}`, { headers: auth }), api("/api/admin/usuarios", { headers: auth }).catch(() => [])]);
  const itens = res.itens || [];
  const paginas = Math.max(1, Math.ceil((res.total || 0) / (res.por_pagina || 50)));
  const irPagina = (n) => () => { filtroHistorico.pagina = n; atualizarAba(); };
  const form = h("form", { class: "form-linha painel", novalidate: true, role: "search" },
    h("div", { class: "campo" }, h("label", { for: "hist-usuario" }, "Quem"),
      h("select", { id: "hist-usuario", name: "usuario", class: "campo-select" },
        h("option", { value: "" }, "Todos"), h("option", { value: "token", selected: filtroHistorico.usuario === "token" }, "Token de emergência / sem login"),
        (Array.isArray(usuarios) ? usuarios : []).map((u) => h("option", { value: String(u.id), selected: filtroHistorico.usuario === String(u.id) }, u.nome)))),
    h("div", { class: "campo cresce" }, h("label", { for: "hist-alvo" }, "Onde (parte do endereço: pedidos, TPT-…, produtos…)"),
      h("input", { id: "hist-alvo", name: "alvo", type: "search", maxlength: 200, value: filtroHistorico.alvo })),
    h("button", { class: "botao", type: "submit" }, "Filtrar"));
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    filtroHistorico.usuario = form.elements.usuario.value;
    filtroHistorico.alvo = form.elements.alvo.value.trim();
    filtroHistorico.pagina = 1;
    atualizarAba();
  });
  const navegacao = h("div", { class: "paginacao" },
    h("button", { class: "botao secundario", type: "button", disabled: res.pagina <= 1, onclick: irPagina(res.pagina - 1) }, "← Anteriores"),
    h("span", {}, `Página ${res.pagina} de ${paginas} · ${res.total} registro${res.total === 1 ? "" : "s"}`),
    h("button", { class: "botao secundario", type: "button", disabled: res.pagina >= paginas, onclick: irPagina(res.pagina + 1) }, "Próximos →"));
  return h("div", { class: "pilha" },
    h("p", { class: "parcelado" }, "Tudo o que foi alterado no painel (e os logins), com quem, quando e de onde. Senhas e códigos nunca aparecem."),
    form,
    itens.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-historico" },
      h("thead", {}, h("tr", {}, ["Quando", "Quem", "O quê", "Onde", "Detalhes"].map((t) => h("th", {}, t)))),
      h("tbody", {}, itens.map((it) => {
        const det = textoDetalhes(it.detalhes);
        return h("tr", {},
          celula("Quando", {}, quandoAdm(it.data)),
          celula("Quem", {}, (it.usuario && it.usuario.nome) || "—", it.ip ? h("div", { class: "parcelado" }, it.ip) : null),
          celula("O quê", {}, h("code", {}, it.acao)),
          celula("Onde", {}, h("span", { class: "quebra" }, it.alvo)),
          celula("Detalhes", {}, det ? (det.length > 80 ? h("details", {}, h("summary", {}, `${det.slice(0, 60)}…`), h("pre", { class: "detalhes-json" }, det)) : h("code", { class: "quebra" }, det)) : "—"));
      })))) : h("p", { class: "painel" }, "Nenhum registro com estes filtros."),
    paginas > 1 ? navegacao : h("p", { class: "parcelado" }, `${res.total} registro${res.total === 1 ? "" : "s"}`));
}
