// ------------------------------------------------------------- datas no horário de Manaus, barcos e pré-venda

/** Manaus fica em UTC−4 o ano todo (sem horário de verão): a conta é feita aqui, sem depender do Intl. */
const DIAS_DA_SEMANA = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];

/**
 * Partes de uma data da API no horário de Manaus. Aceita data pura ("2026-10-16"), ISO com "Z" e o formato do
 * banco ("2026-10-09 18:11:57", em UTC). Devolve null se não der para ler.
 */
function partesManaus(valor) {
  const texto = String(valor || "").trim();
  const pura = /^(\d{4})-(\d{2})-(\d{2})$/.exec(texto);
  let d;
  if (pura) d = new Date(Date.UTC(Number(pura[1]), Number(pura[2]) - 1, Number(pura[3])));
  else {
    const iso = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?$/.test(texto) ? `${texto.replace(" ", "T")}Z` : texto;
    const t = Date.parse(iso);
    if (!texto || Number.isNaN(t)) return null;
    d = new Date(t - 4 * 3600 * 1000);
  }
  return { dia: d.getUTCDate(), mes: d.getUTCMonth() + 1, ano: d.getUTCFullYear(), semana: DIAS_DA_SEMANA[d.getUTCDay()],
    hora: d.getUTCHours(), minuto: d.getUTCMinutes(), soData: Boolean(pura) };
}

/** "16/10" */
function diaMes(valor) {
  const p = partesManaus(valor);
  return p ? `${doisDigitos(p.dia)}/${doisDigitos(p.mes)}` : "";
}
/** "16/10/2026" */
function dataCompleta(valor) {
  const p = partesManaus(valor);
  return p ? `${doisDigitos(p.dia)}/${doisDigitos(p.mes)}/${p.ano}` : "";
}
/** "quarta 14/10" */
function semanaDiaMes(valor) {
  const p = partesManaus(valor);
  return p ? `${p.semana} ${doisDigitos(p.dia)}/${doisDigitos(p.mes)}` : "";
}
/** "14h" ou "14h30" (horário de Manaus); vazio para data pura. */
function horaManaus(valor) {
  const p = partesManaus(valor);
  return p && !p.soData ? `${p.hora}h${p.minuto ? doisDigitos(p.minuto) : ""}` : "";
}
/** "09/10 às 14h11" */
function dataHoraCurta(valor) {
  const p = partesManaus(valor);
  return p ? `${doisDigitos(p.dia)}/${doisDigitos(p.mes)}${p.soData ? "" : ` às ${p.hora}h${doisDigitos(p.minuto)}`}` : "";
}

/** "🛶 Próximo barco: B/M Amazonas Star, sai quarta 14/10 · chega 16/10" (null sem barco). */
function linhaProximoBarco(f, { link = true } = {}) {
  const b = f && f.proximo_barco;
  if (!b || !b.embarcacao) return null;
  return h("p", { class: "proximo-barco" },
    h("span", { "aria-hidden": "true" }, "🛶 "), "Próximo barco: ", h("b", {}, b.embarcacao),
    `, sai ${semanaDiaMes(b.saida)} · chega ${diaMes(b.chegada_prevista)}`,
    link ? [" ", h("a", { href: "/barcos" }, "Ver calendário")] : null);
}

/**
 * Prazo de uma cotação de frete. Com barco, vale a chegada estimada; com pré-venda, o prazo do frete conta a partir
 * da previsão de envio (é assim que o servidor calcula); senão, o prazo em dias úteis depois do pagamento.
 */
function textoPrazoFrete(f, previsaoEnvio = null) {
  if (!f) return "";
  if (f.chegada_estimada) return `chegada estimada em ${diaMes(f.chegada_estimada)}`;
  if (previsaoEnvio) return `envio previsto para ${diaMes(previsaoEnvio)} e entrega em até ${f.prazo_dias} dias úteis depois`;
  return `chega em até ${f.prazo_dias} dias úteis`;
}

/** Linha "Previsão de envio: 30/10" das cotações e pedidos com itens de pré-venda. */
function linhaPrevisaoEnvio(previsao) {
  if (!previsao) return null;
  return h("p", { class: "previsao-envio" }, h("span", { "aria-hidden": "true" }, "📦 "), "Previsão de envio: ", h("b", {}, diaMes(previsao)),
    h("span", { class: "parcelado" }, " (itens de pré-venda)"));
}

/** Produto em pré-venda ({chegada}) ou null. */
const prevendaDe = (p) => (p && p.prevenda && p.prevenda.chegada ? p.prevenda : null);
