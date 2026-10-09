// ------------------------------------------------------------- gatilhos de venda
// Tudo aqui mostra só o que a API devolve (dados reais). Campo ausente, nulo ou zero: o elemento não aparece.
// Assim o front funciona com o servidor antigo (sem esses campos) e com o novo.

const CHAVE_VISTOS = "tipiti:vistos";
const CHAVE_CUPOM = "tipiti:cupom";
const CHAVE_ULTIMA_VISITA = "tipiti:ultima-visita";
const CHAVE_TOASTS = "tipiti:vendas-mostradas";

// -- preços (contrato: preco_final ?? preco; âncora ?? (preco_de > preco ? preco_de : null))

function precoFinal(p) {
  return typeof p.preco_final_centavos === "number" ? p.preco_final_centavos : p.preco_centavos;
}

function precoAncora(p) {
  const final = precoFinal(p);
  const ancora = typeof p.preco_ancora_centavos === "number" ? p.preco_ancora_centavos
    : (p.preco_de_centavos != null && p.preco_de_centavos > p.preco_centavos ? p.preco_de_centavos : null);
  return ancora != null && ancora > final ? ancora : null;
}

/** Preço e âncora de uma opção do produto (a opção sem preço próprio segue o produto). */
function precosOpcao(p, v) {
  if (!v) return { final: precoFinal(p), ancora: precoAncora(p) };
  if (v.preco_centavos == null) {
    const final = typeof v.preco_final_centavos === "number" ? v.preco_final_centavos : precoFinal(p);
    return { final, ancora: final === precoFinal(p) ? precoAncora(p) : null };
  }
  const final = typeof v.preco_final_centavos === "number" ? v.preco_final_centavos : v.preco_centavos;
  // preço próprio em oferta: o preço normal da opção é a referência riscada
  return { final, ancora: v.preco_centavos > final ? v.preco_centavos : null };
}

const pctDesconto = (final, ancora) => (ancora && ancora > final ? Math.round((1 - final / ancora) * 100) : 0);

// -- relógio único: uma só contagem por segundo para a página inteira; limpo a cada navegação

const relogio = { tarefas: new Set(), id: null };

function tique() {
  for (const t of [...relogio.tarefas]) {
    if (t.el && !t.el.isConnected) {
      if (t.visto) { relogio.tarefas.delete(t); continue; }  // saiu da página
    } else t.visto = true;
    t.fn();
  }
  if (!relogio.tarefas.size) { clearInterval(relogio.id); relogio.id = null; }
}

/** Roda `fn` agora e a cada segundo enquanto `el` estiver na página. Devolve a função que para. */
function aCadaSegundo(el, fn) {
  const t = { el, fn, visto: false };
  relogio.tarefas.add(t);
  if (!relogio.id) relogio.id = setInterval(tique, 1000);
  fn();
  return () => relogio.tarefas.delete(t);
}

function pararRelogios() {
  relogio.tarefas.clear();
  clearInterval(relogio.id);
  relogio.id = null;
}

const doisDigitos = (n) => String(n).padStart(2, "0");

/** 8133 s -> "02:15:33"; com mais de 24 h -> "2 dias e 03:15:20". */
function textoContagem(segundos) {
  const d = Math.floor(segundos / 86400);
  const resto = segundos % 86400;
  const hms = `${doisDigitos(Math.floor(resto / 3600))}:${doisDigitos(Math.floor((resto % 3600) / 60))}:${doisDigitos(resto % 60)}`;
  return d > 0 ? `${d} ${d === 1 ? "dia" : "dias"} e ${hms}` : hms;
}

function msAte(iso) {
  const t = Date.parse(iso || "");
  return Number.isNaN(t) ? NaN : t - Date.now();
}

/** A oferta tem data de fim válida e ainda não acabou (pelo relógio do aparelho). */
const promoAtiva = (p) => Boolean(p && p.promo && p.promo.fim && msAte(p.promo.fim) > 0);

/** Fins de oferta que já recarregaram a página (evita recarregar em laço se o relógio do aparelho estiver adiantado). */
const finsRecarregados = new Set();

/**
 * Contagem regressiva até `fim`. Ao zerar, recarrega os dados da página (o preço volta ao normal).
 * Fim inválido ou no passado: não mostra nada.
 */
function contagemOferta(fim, { prefixo = "Oferta termina em ", classe = "contagem" } = {}) {
  if (!(msAte(fim) > 0)) return null;
  const texto = h("span", {});
  const el = h("span", { class: classe, role: "timer" }, h("span", { "aria-hidden": "true" }, "⏱ "), prefixo, texto);
  const parar = aCadaSegundo(el, () => {
    const ms = msAte(fim);
    if (ms > 0) { texto.textContent = textoContagem(Math.ceil(ms / 1000)); return; }
    parar();
    el.hidden = true;
    if (finsRecarregados.has(fim)) return;
    finsRecarregados.add(fim);
    if (el.isConnected) rotear();
  });
  return el;
}

// -- selos, estrelas, vendidos

const SELOS = { oferta: "Oferta", mais_vendido: "Mais vendido", novidade: "Novidade", ultimas_unidades: "Últimas unidades" };

/** No máximo `maximo` selos, na ordem de prioridade do contrato. `semOferta`: o "-Y%" já diz que é oferta. */
function selosProduto(p, { maximo = 2, semOferta = false } = {}) {
  const lista = Array.isArray(p.selos) ? p.selos : [];
  return Object.keys(SELOS).filter((s) => lista.includes(s) && !(semOferta && s === "oferta")).slice(0, maximo);
}

const notaTexto = (n) => n.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

function temAvaliacoes(p) {
  return typeof p.nota_media === "number" && p.nota_media > 0 && p.avaliacoes_total > 0;
}

/** Cinco estrelas preenchidas na proporção da nota; leitores de tela ouvem o texto. */
function estrelas(nota, rotulo) {
  const pct = Math.max(0, Math.min(100, (nota / 5) * 100));
  return h("span", { class: "estrelas", role: "img", "aria-label": rotulo },
    h("span", { class: "estrelas-fundo", "aria-hidden": "true" }, "★★★★★"),
    h("span", { class: "estrelas-cheias", "aria-hidden": "true", style: `width:${pct}%` }, "★★★★★"));
}

function resumoNota(p, { curto = false } = {}) {
  if (!temAvaliacoes(p)) return null;
  const total = p.avaliacoes_total;
  const rotulo = `Nota ${notaTexto(p.nota_media)} de 5, ${total} ${total === 1 ? "avaliação" : "avaliações"}`;
  return h("span", { class: "resumo-nota" }, estrelas(p.nota_media, rotulo),
    h("span", { "aria-hidden": "true" }, curto ? ` ${notaTexto(p.nota_media)} (${total})` : ` ${notaTexto(p.nota_media)} · ${total} ${total === 1 ? "avaliação" : "avaliações"}`));
}

const MINIMO_VENDIDOS = 5;
const vendidos = (p) => (Number.isInteger(p.vendidos_30d) && p.vendidos_30d >= MINIMO_VENDIDOS ? p.vendidos_30d : 0);

// -- confiança e envio no mesmo dia

function blocoConfianca(classe = "") {
  return h("ul", { class: `confianca ${classe}`, "aria-label": "Garantias da compra" },
    [["🔒", "Compra segura"], ["🔁", "7 dias para trocar"], ["🛡️", "Garantia de 90 dias"], ["📍", "Enviado de Manaus"]]
      .map(([ico, t]) => h("li", {}, h("span", { "aria-hidden": "true" }, ico), " ", t)));
}

/** "Peça em 2h 15min e enviamos hoje", a partir de `envio_hoje.ate` da loja; some quando o horário passa. */
function avisoEnvioHoje() {
  const ate = estado.loja && estado.loja.envio_hoje && estado.loja.envio_hoje.ate;
  if (!(msAte(ate) > 0)) return null;
  const texto = h("span", {});
  const el = h("p", { class: "envio-hoje" }, h("span", { "aria-hidden": "true" }, "🚀 "), texto);
  const parar = aCadaSegundo(el, () => {
    const ms = msAte(ate);
    if (!(ms > 0)) { parar(); el.hidden = true; return; }
    const min = Math.max(1, Math.ceil(ms / 60000));
    const horas = Math.floor(min / 60);
    texto.textContent = `Peça em ${horas ? `${horas}h ` : ""}${min % 60}min e enviamos hoje`;
  });
  return el;
}

// -- vistos recentemente (só no aparelho da pessoa)

const CAMPOS_VISTO = ["slug", "nome", "preco_centavos", "preco_de_centavos", "preco_final_centavos", "preco_ancora_centavos", "promo",
  "estoque", "imagem", "imagem_miniatura", "cor", "icone"];

function registrarVisto(p) {
  const foto = (p.fotos || [])[0];
  const instantaneo = Object.fromEntries(CAMPOS_VISTO.filter((k) => p[k] !== undefined).map((k) => [k, p[k]]));
  if (foto) { instantaneo.imagem = foto.url; instantaneo.imagem_miniatura = foto.miniatura || foto.url; }
  const lista = lerArmazenado(CHAVE_VISTOS, []);
  gravar(CHAVE_VISTOS, [instantaneo, ...(Array.isArray(lista) ? lista : []).filter((v) => v && v.slug !== p.slug)].slice(0, 8));
}

/** Os produtos vistos, sem dados de oferta que já venceram (o preço volta ao normal). */
function produtosVistos() {
  const lista = lerArmazenado(CHAVE_VISTOS, []);
  if (!Array.isArray(lista)) return [];
  return lista.filter((v) => v && typeof v.slug === "string" && typeof v.nome === "string" && typeof v.preco_centavos === "number")
    .map((v) => {
      if (!v.promo || promoAtiva(v)) return v;
      const resto = { ...v };
      delete resto.preco_final_centavos; delete resto.preco_ancora_centavos; delete resto.promo;
      return resto;
    });
}

// -- cupom guardado na sessão (cotação do carrinho, checkout e o "Copiar" da página inicial)

const cupomGuardado = () => {
  const c = lerArmazenado(CHAVE_CUPOM, "", sessionStorage);
  return typeof c === "string" ? c : "";
};
function guardarCupom(codigo) {
  if (codigo) gravar(CHAVE_CUPOM, String(codigo).trim().toUpperCase(), sessionStorage);
  else try { sessionStorage.removeItem(CHAVE_CUPOM); } catch (_) { /* ignora */ }
}

// -- carrinho abandonado: lê a última visita ao abrir o site e passa a marcar a atual

let visitaAnterior = null;
function marcarVisita(inicio = false) {
  if (inicio) {
    const v = lerArmazenado(CHAVE_ULTIMA_VISITA, null);
    visitaAnterior = typeof v === "number" ? v : null;
  }
  gravar(CHAVE_ULTIMA_VISITA, Date.now());
}

let avisoCarrinhoFechado = false;
function avisoCarrinhoAbandonado() {
  const itens = estado.carrinho.reduce((s, i) => s + i.quantidade, 0);
  if (avisoCarrinhoFechado || !itens || !visitaAnterior || Date.now() - visitaAnterior < 30 * 60 * 1000) return null;
  const el = h("div", { class: "faixa-aviso faixa-carrinho", role: "region", "aria-label": "Carrinho guardado" },
    h("span", { "aria-hidden": "true", class: "faixa-ico" }, "🛒"),
    h("p", {}, `Você deixou ${itens} ${itens === 1 ? "item" : "itens"} no carrinho.`),
    h("a", { class: "botao", href: "/carrinho" }, "Finalizar compra"),
    h("button", { class: "fechar", type: "button", "aria-label": "Fechar aviso do carrinho",
      onclick: () => { avisoCarrinhoFechado = true; el.remove(); } }, "×"));
  return el;
}

function faixaCupomDestaque() {
  const c = estado.loja && estado.loja.cupom_destaque;
  if (!c || typeof c.codigo !== "string" || !c.codigo) return null;
  return h("div", { class: "faixa-aviso faixa-cupom", role: "region", "aria-label": "Cupom de desconto" },
    h("span", { "aria-hidden": "true", class: "faixa-ico" }, "🎟️"),
    h("p", {}, c.descricao ? [c.descricao, " · "] : null, "Use o cupom ", h("b", { class: "codigo-cupom" }, c.codigo)),
    h("button", { class: "botao", type: "button", onclick: async () => {
      guardarCupom(c.codigo);
      const ok = await copiarTexto(c.codigo);
      avisar(ok ? `Cupom ${c.codigo} copiado ✔ Ele já vai aplicado no carrinho.` : `Cupom ${c.codigo} guardado: ele já vai aplicado no carrinho.`);
    } }, "Copiar"));
}

// -- frete grátis no painel "adicionado ao carrinho"

async function faltaFreteGratis(saida) {
  try {
    const c = await api("/api/carrinho/cotacao", { method: "POST", body: JSON.stringify({ itens: estado.carrinho, cep: null }) });
    if (!saida.isConnected || typeof c.falta_para_frete_gratis !== "number" || !c.subtotal_centavos) return;
    const l = estado.loja;
    const pct = Math.min(100, Math.round((c.subtotal_centavos / l.frete_gratis_a_partir) * 100));
    trocar(saida, h("div", { class: "barra-frete" },
      c.falta_para_frete_gratis > 0 ? ["Faltam ", h("b", {}, brl(c.falta_para_frete_gratis)), " para frete grátis na Região Norte"]
        : "🎉 Você ganhou frete grátis na Região Norte!",
      h("div", { class: "barra-progresso" }, h("span", { style: `width:${pct}%` }))));
  } catch (_) { /* sem a barra: não atrapalha a compra */ }
}

// -- compras recentes (anônimas), só quando a loja liga e o servidor tem vendas reais

const prova = { lista: null, proxima: 0, timer: null, esconder: null, el: null };
const PAGINAS_SEM_PROVA = /^\/(carrinho|checkout|pedido|admin)(\/|$)/;

function tempoAtras(min) {
  if (!(min >= 1)) return "agora há pouco";
  if (min < 60) return `${Math.round(min)} min`;
  if (min < 1440) { const horas = Math.round(min / 60); return `${horas} ${horas === 1 ? "hora" : "horas"}`; }
  const d = Math.round(min / 1440);
  return `${d} ${d === 1 ? "dia" : "dias"}`;
}

function esconderProva() {
  clearTimeout(prova.esconder);
  if (prova.el) { prova.el.replaceChildren(); prova.el = null; }
}

/** A região "polite" entra vazia na página antes do texto, para o leitor de tela anunciar a mudança. */
function regiaoProva() {
  let regiao = $("#prova-social");
  if (!regiao) {
    regiao = h("div", { id: "prova-social", class: "prova-social", role: "status", "aria-live": "polite" });
    document.body.append(regiao);
  }
  return regiao;
}

function mostrarProva() {
  const mostradas = Number(lerArmazenado(CHAVE_TOASTS, 0, sessionStorage)) || 0;
  if (mostradas >= 3 || !prova.lista || prova.proxima >= prova.lista.length) return false;
  if (PAGINAS_SEM_PROVA.test(location.pathname) || folhaAberta || document.hidden) return true;  // tenta no próximo intervalo
  const v = prova.lista[prova.proxima++];
  gravar(CHAVE_TOASTS, mostradas + 1, sessionStorage);
  esconderProva();
  const tempo = tempoAtras(v.minutos_atras);
  const regiao = regiaoProva();
  const foto = v.imagem ? imagemProduto(v, true) : (v.cor ? svgProduto(v.icone, v.cor) : null);
  const link = h("a", { class: "prova-link", href: `/produto/${v.slug}`, onclick: esconderProva },
    foto ? h("img", { src: foto, alt: "", width: 48, height: 48 }) : null,
    h("span", {}, `Alguém de ${v.cidade} (${v.uf}) comprou `, h("b", {}, v.produto),
      h("small", {}, tempo === "agora há pouco" ? " · agora há pouco" : ` · há ${tempo}`)));
  regiao.classList.remove("entrar");
  trocar(regiao, link, h("button", { class: "fechar", type: "button", "aria-label": "Fechar aviso de compra recente",
    onclick: () => { esconderProva(); prova.lista = null; clearInterval(prova.timer); } }, "×"));
  prova.el = regiao;
  if (!reduzMovimento()) requestAnimationFrame(() => regiao.classList.add("entrar"));
  prova.esconder = setTimeout(esconderProva, 6000);
  return true;
}

/** Busca as vendas recentes uma vez e mostra no máximo 3 por sessão: a 1ª após 8 s, depois a cada 25 s. */
async function iniciarProvaSocial() {
  if (!estado.loja || estado.loja.prova_social !== true) return;
  if ((Number(lerArmazenado(CHAVE_TOASTS, 0, sessionStorage)) || 0) >= 3) return;
  let lista;
  try { lista = await api("/api/vendas-recentes"); } catch (_) { return; }
  if (!Array.isArray(lista)) return;
  prova.lista = lista.filter((v) => v && v.produto && v.slug && v.cidade && v.uf);
  if (!prova.lista.length) return;
  regiaoProva();
  setTimeout(() => {
    if (!mostrarProva()) return;
    prova.timer = setInterval(() => { if (!mostrarProva()) clearInterval(prova.timer); }, 25000);
  }, 8000);
}

// -- barra fixa de compra: só aparece quando os botões de compra da página saem da tela

let observadorBarra = null;
function soltarBarraCompra() {
  if (observadorBarra) observadorBarra.disconnect();
  observadorBarra = null;
  document.body.classList.remove("com-barra-compra");
}

function observarBarraCompra(alvo, barra) {
  soltarBarraCompra();
  const mostrar = (sim) => {
    barra.classList.toggle("visivel", sim);
    document.body.classList.toggle("com-barra-compra", sim && getComputedStyle(barra).display !== "none");
  };
  if (!("IntersectionObserver" in window)) return mostrar(true);
  const topo = $(".topo");
  const altura = topo && getComputedStyle(topo).position === "sticky" ? topo.offsetHeight : 0;
  observadorBarra = new IntersectionObserver(([e]) => mostrar(!e.isIntersecting), { rootMargin: `-${altura}px 0px 0px 0px` });
  observadorBarra.observe(alvo);
}
