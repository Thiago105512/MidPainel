// ------------------------------------------------------------- painel: oferta relâmpago, cupons e avaliações

/** Manaus é UTC−4 o ano todo (sem horário de verão). */
const FUSO_MANAUS_HORAS = 4;

/** "2026-10-12T18:00" (horário de Manaus, de um datetime-local) -> "2026-10-12T22:00:00Z"; inválido -> null. */
function manausParaIso(local) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(local || "");
  if (!m) return null;
  const t = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]), Number(m[4]) + FUSO_MANAUS_HORAS, Number(m[5]));
  return new Date(t).toISOString().replace(/\.\d{3}Z$/, "Z");
}

/** ISO UTC -> valor para datetime-local no horário de Manaus. */
function isoParaManaus(iso) {
  const t = Date.parse(iso || "");
  return Number.isNaN(t) ? "" : new Date(t - FUSO_MANAUS_HORAS * 3600000).toISOString().slice(0, 16);
}

function textoManaus(iso) {
  const t = Date.parse(iso || "");
  if (Number.isNaN(t)) return "";
  const d = new Date(t - FUSO_MANAUS_HORAS * 3600000);
  return `${doisDigitos(d.getUTCDate())}/${doisDigitos(d.getUTCMonth() + 1)}/${d.getUTCFullYear()} às ${doisDigitos(d.getUTCHours())}:${doisDigitos(d.getUTCMinutes())}`;
}

/** Erro 404 numa função nova: o servidor ainda é o antigo. */
async function apiNova(url, opcoes) {
  try { return await api(url, opcoes); } catch (err) {
    if (err.status === 404 && !opcoes?.method) throw new Error("Esta função precisa da versão nova do servidor da loja.");
    throw err;
  }
}

function campoDataHora(nome, rotulo, valorIso, classe = "c3", dica = null) {
  return campo(nome, rotulo, { type: "datetime-local", value: isoParaManaus(valorIso) }, classe, dica);
}

// -- oferta relâmpago no editor do produto

function secaoOfertaRelampago(auth, p) {
  if (!("promo_pct" in p)) return null;  // servidor antigo
  const ativa = p.promo_pct && msAte(p.promo_fim) > 0;
  const vencida = p.promo_pct && p.promo_fim && !ativa;
  const previa = h("p", { class: "parcelado", "aria-live": "polite" });
  const sugestao = new Date(Date.now() + 24 * 3600000).toISOString();
  const form = h("form", { class: "painel", novalidate: true, "aria-labelledby": "titulo-oferta" },
    h("h2", { id: "titulo-oferta" }, "⚡ Oferta relâmpago"),
    h("p", { class: "parcelado" }, "Desconto por tempo limitado. O cliente vê o preço riscado e a contagem regressiva; quando o prazo acaba, o preço volta sozinho."),
    ativa ? h("p", { class: "estado-oferta ativa" }, `Ativa: −${p.promo_pct}% até ${textoManaus(p.promo_fim)} (Manaus).`)
      : vencida ? h("p", { class: "estado-oferta vencida" }, `Encerrada em ${textoManaus(p.promo_fim)} (Manaus). O preço normal já voltou.`)
        : h("p", { class: "estado-oferta" }, "Nenhuma oferta programada."),
    h("div", { class: "grade-form" },
      campo("promo_pct", "Desconto (%)", { type: "number", min: 1, max: 90, step: 1, inputmode: "numeric", placeholder: "20",
        value: p.promo_pct ?? "" }, "c2"),
      campoDataHora("promo_fim", "Termina em (horário de Manaus)", ativa ? p.promo_fim : sugestao, "c4")),
    previa,
    h("div", { class: "compra" },
      h("button", { class: "botao", type: "submit" }, ativa ? "Atualizar oferta" : "Começar oferta"),
      p.promo_pct || p.promo_fim ? h("button", { class: "botao secundario", type: "button", onclick: async () => {
        if (!confirm("Encerrar a oferta agora? O preço volta ao normal.")) return;
        try {
          await api(`/api/admin/produtos/${p.slug}`, { method: "PATCH", headers: auth, body: JSON.stringify({ promo_pct: null, promo_fim: null }) });
          avisar("Oferta encerrada ✔");
          rotear();
        } catch (err) { if (err.status === 401) return sairDoPainel(true); avisar(err.message); }
      } }, "Encerrar oferta") : null));
  const atualizarPrevia = () => {
    const pct = parseInt(form.elements.promo_pct.value, 10);
    previa.textContent = pct >= 1 && pct <= 90
      ? `Preço com o desconto: cerca de ${brl(Math.round(p.preco_centavos * (1 - pct / 100)))} (normal: ${brl(p.preco_centavos)}).` : "";
  };
  form.elements.promo_pct.addEventListener("input", atualizarPrevia);
  atualizarPrevia();
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const pct = Number(form.elements.promo_pct.value);
    const fim = manausParaIso(form.elements.promo_fim.value);
    const erros = {};
    if (!Number.isInteger(pct) || pct < 1 || pct > 90) erros.promo_pct = "Use um desconto inteiro de 1 a 90%.";
    if (!fim) erros.promo_fim = "Informe quando a oferta termina.";
    else if (!(msAte(fim) > 0)) erros.promo_fim = "O fim da oferta precisa estar no futuro.";
    if (Object.keys(erros).length) return mostrarErros(form, erros);
    try {
      await api(`/api/admin/produtos/${p.slug}`, { method: "PATCH", headers: auth, body: JSON.stringify({ promo_pct: pct, promo_fim: fim }) });
      avisar("Oferta salva ✔");
      rotear();
    } catch (err) {
      if (err.status === 401) return sairDoPainel(true);
      mostrarErros(form, err.campos);
      avisar(err.message);
    }
  });
  return form;
}

// -- cupons

const TIPOS_CUPOM = { pct: "Porcentagem (%)", valor: "Valor fixo (R$)", frete: "Frete grátis" };

function textoDescontoCupom(c) {
  if (c.tipo === "pct") return `${c.valor}% de desconto`;
  if (c.tipo === "valor") return `${brl(c.valor || 0)} de desconto`;
  return "Frete grátis";
}

function situacaoCupom(c) {
  if (!c.ativo) return ["Desativado", "inativo"];
  if (c.fim && !(msAte(c.fim) > 0)) return ["Expirado", "inativo"];
  if (c.inicio && msAte(c.inicio) > 0) return ["Agendado", "agendado"];
  if (c.limite_usos && c.usos >= c.limite_usos) return ["Esgotado", "inativo"];
  return ["Ativo", "ativo"];
}

function formularioNovoCupom(auth) {
  const rotuloValor = h("label", { for: "campo-valor" }, "Desconto (%)");
  const form = h("form", { class: "painel", novalidate: true, "aria-labelledby": "titulo-novo-cupom" },
    h("h2", { id: "titulo-novo-cupom" }, "Novo cupom"),
    h("div", { class: "grade-form" },
      campo("codigo", "Código", { maxlength: 30, autocapitalize: "characters", spellcheck: "false", placeholder: "BEMVINDO10" }, "c2"),
      h("div", { class: "campo c2", "data-campo": "tipo" },
        h("label", { for: "campo-tipo" }, "Tipo"),
        h("select", { id: "campo-tipo", name: "tipo", class: "campo-select" }, Object.entries(TIPOS_CUPOM).map(([v, t]) => h("option", { value: v }, t))),
        h("span", { class: "msg-erro" })),
      h("div", { class: "campo c2", "data-campo": "valor" }, rotuloValor,
        h("input", { id: "campo-valor", name: "valor", type: "text", inputmode: "decimal", placeholder: "10", "aria-describedby": "erro-valor" }),
        h("span", { class: "msg-erro", id: "erro-valor" })),
      campo("minimo_centavos", "Compra mínima (R$, opcional)", { inputmode: "decimal", placeholder: "0,00" }, "c2"),
      campo("limite_usos", "Limite de usos (opcional)", { type: "number", min: 1, inputmode: "numeric", placeholder: "sem limite" }, "c2"),
      campo("descricao", "Descrição para o cliente", { maxlength: 120, placeholder: "10% off na primeira compra" }, "c2"),
      campoDataHora("inicio", "Começa em (Manaus, opcional)", null, "c3"),
      campoDataHora("fim", "Termina em (Manaus, opcional)", null, "c3"),
      h("label", { class: "c2 caixa" }, h("input", { type: "checkbox", name: "so_primeira_compra" }), " Só na primeira compra (pelo CPF)"),
      h("label", { class: "c2 caixa" }, h("input", { type: "checkbox", name: "destaque" }), " Mostrar na página inicial"),
      h("label", { class: "c2 caixa" }, h("input", { type: "checkbox", name: "ativo", checked: true }), " Ativo")),
    h("div", { class: "alerta", hidden: true }),
    h("button", { class: "botao grande espaco-topo", type: "submit" }, "Criar cupom"));
  const f = form.elements;
  const ajustarTipo = () => {
    const frete = f.tipo.value === "frete";
    f.valor.closest(".campo").hidden = frete;
    rotuloValor.textContent = f.tipo.value === "valor" ? "Desconto (R$)" : "Desconto (%)";
    f.valor.placeholder = f.tipo.value === "valor" ? "15,00" : "10";
  };
  f.tipo.addEventListener("change", ajustarTipo);
  f.codigo.addEventListener("input", () => { f.codigo.value = f.codigo.value.toUpperCase().replace(/\s/g, ""); });
  ajustarTipo();
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const alerta = $(".alerta", form);
    alerta.hidden = true;
    const erros = {};
    const tipo = f.tipo.value;
    let valor = 0;
    if (tipo === "pct") {
      valor = lerNumero(f.valor.value, { pontoDecimal: true });
      if (!Number.isInteger(valor) || valor < 1 || valor > 90) erros.valor = "Use uma porcentagem inteira de 1 a 90.";
    } else if (tipo === "valor") {
      valor = reais(f.valor.value);
      if (!(valor > 0)) erros.valor = "Informe o valor do desconto, ex.: 15,00.";
    }
    const minimo = reais(f.minimo_centavos.value);
    if (Number.isNaN(minimo)) erros.minimo_centavos = "Valor inválido. Use o formato 99,90.";
    if (!/^[A-Z0-9_-]{3,30}$/.test(f.codigo.value)) erros.codigo = "Use de 3 a 30 letras ou números, sem espaços.";
    const limite = f.limite_usos.value ? parseInt(f.limite_usos.value, 10) : null;
    if (limite !== null && !(limite >= 1)) erros.limite_usos = "Use um número a partir de 1, ou deixe vazio.";
    const inicio = f.inicio.value ? manausParaIso(f.inicio.value) : null;
    const fim = f.fim.value ? manausParaIso(f.fim.value) : null;
    if (fim && !(msAte(fim) > 0)) erros.fim = "O fim precisa estar no futuro.";
    if (fim && inicio && Date.parse(fim) <= Date.parse(inicio)) erros.fim = "O fim precisa ser depois do começo.";
    if (Object.keys(erros).length) return mostrarErros(form, erros);
    try {
      await api("/api/admin/cupons", { method: "POST", headers: auth, body: JSON.stringify({
        codigo: f.codigo.value, tipo, valor, minimo_centavos: minimo || 0, inicio, fim, limite_usos: limite,
        so_primeira_compra: f.so_primeira_compra.checked, destaque: f.destaque.checked, ativo: f.ativo.checked,
        descricao: f.descricao.value.trim() }) });
      avisar("Cupom criado ✔");
      rotear();
    } catch (err) {
      if (err.status === 401) return sairDoPainel(true);
      mostrarErros(form, err.campos);
      alerta.textContent = err.message;
      alerta.hidden = false;
    }
  });
  return form;
}

async function painelCupons(auth) {
  const cupons = await apiNova("/api/admin/cupons", { headers: auth });
  const alternar = (c, campoBool) => async () => {
    try {
      await api(`/api/admin/cupons/${encodeURIComponent(c.codigo)}`, { method: "PATCH", headers: auth, body: JSON.stringify({ [campoBool]: !c[campoBool] }) });
      avisar("Cupom atualizado ✔");
      rotear();
    } catch (err) { if (err.status === 401) return sairDoPainel(true); avisar(err.message); }
  };
  const lista = Array.isArray(cupons) ? cupons : [];
  return h("div", { class: "pilha" },
    lista.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-cupons" },
      h("thead", {}, h("tr", {}, ["Cupom", "Desconto", "Validade", "Usos", "Situação", ""].map((t) => h("th", {}, t)))),
      h("tbody", {}, lista.map((c) => {
        const [situacao, classe] = situacaoCupom(c);
        return h("tr", {},
          celula("Cupom", {}, h("b", { class: "codigo-cupom" }, c.codigo), c.descricao ? h("div", { class: "parcelado" }, c.descricao) : null),
          celula("Desconto", {}, textoDescontoCupom(c),
            c.minimo_centavos ? h("div", { class: "parcelado" }, `Mínimo ${brl(c.minimo_centavos)}`) : null,
            c.so_primeira_compra ? h("div", { class: "parcelado" }, "Só na primeira compra") : null),
          celula("Validade", {}, c.inicio || c.fim ? [c.inicio ? h("div", {}, `De ${textoManaus(c.inicio)}`) : null,
            c.fim ? h("div", {}, `Até ${textoManaus(c.fim)}`) : null] : h("span", { class: "parcelado" }, "Sem prazo")),
          celula("Usos", {}, `${c.usos || 0} / ${c.limite_usos || "∞"}`),
          celula("Situação", {}, h("span", { class: `etiqueta ${classe}` }, situacao), c.destaque ? h("div", { class: "parcelado" }, "⭐ Na página inicial") : null),
          celula("", { class: "celula-acao" }, h("div", { class: "acoes-cupom" },
            h("button", { class: "botao secundario", type: "button", "aria-pressed": String(Boolean(c.ativo)), onclick: alternar(c, "ativo") },
              c.ativo ? "Desativar" : "Ativar"),
            h("button", { class: "botao secundario", type: "button", "aria-pressed": String(Boolean(c.destaque)), onclick: alternar(c, "destaque") },
              c.destaque ? "Tirar da página inicial" : "Mostrar na página inicial"))));
      })))) : h("p", { class: "painel" }, "Nenhum cupom ainda. Crie o primeiro abaixo."),
    formularioNovoCupom(auth));
}

// -- avaliações

const STATUS_AVALIACAO = { pendente: "Pendente", aprovada: "Aprovada", oculta: "Oculta" };

async function painelAvaliacoes(auth) {
  const avaliacoes = await apiNova("/api/admin/avaliacoes", { headers: auth });
  const lista = (Array.isArray(avaliacoes) ? avaliacoes : []).slice()
    .sort((a, b) => (a.status === "pendente" ? 0 : 1) - (b.status === "pendente" ? 0 : 1) || String(b.data).localeCompare(String(a.data)));
  const pendentes = lista.filter((a) => a.status === "pendente").length;
  const mudar = (a, status) => async () => {
    try {
      await api(`/api/admin/avaliacoes/${a.id}`, { method: "PATCH", headers: auth, body: JSON.stringify({ status }) });
      avisar(status === "aprovada" ? "Avaliação publicada ✔" : status === "oculta" ? "Avaliação ocultada ✔" : "Avaliação atualizada ✔");
      rotear();
    } catch (err) { if (err.status === 401) return sairDoPainel(true); avisar(err.message); }
  };
  if (!lista.length) return h("p", { class: "painel" }, "Nenhuma avaliação ainda. Elas chegam pela página do pedido, depois da compra.");
  return h("div", {},
    h("p", {}, pendentes ? h("b", {}, `${pendentes} ${pendentes === 1 ? "avaliação aguarda" : "avaliações aguardam"} aprovação.`) : "Nenhuma avaliação pendente."),
    h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-avaliacoes" },
      h("thead", {}, h("tr", {}, ["Avaliação", "Produto", "Cliente", "Situação", ""].map((t) => h("th", {}, t)))),
      h("tbody", {}, lista.map((a) => h("tr", { class: a.status === "pendente" ? "pendente" : "" },
        celula("Avaliação", {}, estrelas(a.nota, `Nota ${a.nota} de 5`),
          a.comentario ? h("p", { class: "comentario-admin" }, a.comentario) : h("div", { class: "parcelado" }, "Sem comentário")),
        celula("Produto", {}, a.produto ? h("a", { href: `/produto/${a.produto.slug}`, target: "_blank", rel: "noopener" }, a.produto.nome) : "—"),
        celula("Cliente", {}, a.nome || "—", h("div", { class: "parcelado" }, `Pedido ${a.pedido || "—"}`), a.data ? h("div", { class: "parcelado" }, dataCurta(a.data)) : null),
        celula("Situação", {}, h("span", { class: `etiqueta ${a.status === "aprovada" ? "ativo" : a.status === "oculta" ? "inativo" : "agendado"}` }, STATUS_AVALIACAO[a.status] || a.status)),
        celula("", { class: "celula-acao" }, h("div", { class: "acoes-cupom" },
          a.status !== "aprovada" ? h("button", { class: "botao", type: "button", onclick: mudar(a, "aprovada") }, "Aprovar") : null,
          a.status !== "oculta" ? h("button", { class: "botao secundario", type: "button", onclick: mudar(a, "oculta") }, "Ocultar") : null))))))));
}

// -- configurações: envio no mesmo dia e compras recentes

function camposGatilhosAjustes(aj) {
  if (!("horario_corte" in aj) && !("prova_social" in aj)) return null;  // servidor antigo
  return [
    h("h2", { class: "espaco-topo-grande" }, "Gatilhos de venda"),
    h("div", { class: "grade-form" },
      "horario_corte" in aj ? campo("horario_corte", "Horário de corte para envio no mesmo dia", { type: "time", value: aj.horario_corte || "" }, "c3",
        "Horário de Manaus. Antes dele o produto mostra “Peça em … e enviamos hoje”. Deixe vazio para não mostrar.") : null,
      "prova_social" in aj ? h("label", { class: "c3 caixa" },
        h("input", { type: "checkbox", name: "prova_social", checked: aj.prova_social === "1" }),
        " Mostrar compras recentes (anônimas: só cidade e produto)") : null),
  ];
}
