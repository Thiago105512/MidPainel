// ------------------------------------------------------------- painel: pedidos, rastreio, separação e etiquetas

const EVENTOS_ADM = { pago: "Pagamento confirmado", separado: "Pedido separado", embarcado: "Embarcou", chegou_porto: "Chegou ao porto",
  saiu_entrega: "Saiu para entrega", entregue: "Entregue", outro: "Outra atualização" };
const ICONES_EVENTO_ADM = { pago: "💰", separado: "📦", embarcado: "🚢", chegou_porto: "⚓", saiu_entrega: "🛵", entregue: "✅", outro: "📝" };

/** Filtro de status da lista de pedidos e pedidos com o rastreio aberto (sobrevivem ao redesenho). */
let filtroPedidos = "";
const pedidosAbertos = new Set();

function linhaTempoAdm(eventos) {
  if (!eventos || !eventos.length) return h("p", { class: "parcelado" }, "Nenhum evento ainda.");
  return h("ol", { class: "linha-tempo" }, eventos.map((ev) => h("li", {},
    h("span", { class: "ponto", "aria-hidden": "true" }, ICONES_EVENTO_ADM[ev.tipo] || "•"),
    h("div", {}, h("b", {}, EVENTOS_ADM[ev.tipo] || ev.tipo), " ", h("small", { class: "parcelado" }, quandoAdm(ev.data)),
      ev.mensagem ? h("div", {}, ev.mensagem) : null))));
}

/** Próximas viagens da zona do pedido (a atual sempre aparece); sem viagem na zona, as próximas de todas. */
function opcoesViagem(viagens, p) {
  const futuras = viagens.filter((v) => v.ativo && msAte(v.saida) > 0);
  let lista = futuras.filter((v) => v.zona_nome === p.zona_frete);
  const outras = !lista.length;
  if (outras) lista = futuras;
  const atual = p.viagem && !lista.some((v) => v.id === p.viagem.id) ? [p.viagem] : [];
  return { lista: [...atual, ...lista], outras };
}

function secaoRastreio(auth, p, viagens) {
  const aberto = pedidosAbertos.has(p.codigo);
  const cancelado = p.status === "cancelado";
  const acao = async (fn, ok) => {
    pedidosAbertos.add(p.codigo);
    try { await fn(); avisar(ok); atualizarAba(); } catch (err) { if (err.status !== 401) avisar(err.message); }
  };
  const idb = p.codigo.toLowerCase();
  const tipo = h("select", { id: `ev-tipo-${idb}`, class: "campo-select", name: "tipo" },
    Object.entries(EVENTOS_ADM).map(([v, t]) => h("option", { value: v }, t)));
  const mensagem = h("input", { id: `ev-msg-${idb}`, type: "text", name: "mensagem", maxlength: 300, placeholder: "opcional: usamos o texto padrão" });
  const formEvento = h("form", { class: "form-linha", novalidate: true, onsubmit: (e) => {
    e.preventDefault();
    if (tipo.value === "outro" && !mensagem.value.trim()) { avisar("Escreva a mensagem do evento “Outra atualização”."); mensagem.focus(); return; }
    acao(() => enviarAdmin(auth, `/api/admin/pedidos/${p.codigo}/eventos`, "POST", { tipo: tipo.value, mensagem: mensagem.value.trim() || undefined }),
      "Evento lançado ✔ O cliente recebe por e-mail.");
  } },
    h("div", { class: "campo" }, h("label", { for: `ev-tipo-${idb}` }, "Novo evento"), tipo),
    h("div", { class: "campo cresce" }, h("label", { for: `ev-msg-${idb}` }, "Mensagem para o cliente"), mensagem),
    h("button", { class: "botao", type: "submit", disabled: cancelado }, "Lançar evento"));
  const codigoRastreio = h("input", { id: `rastreio-${idb}`, type: "text", maxlength: 40, value: p.codigo_rastreio || "", placeholder: "AA123456789BR",
    autocapitalize: "characters", spellcheck: "false" });
  const formRastreio = h("form", { class: "form-linha", novalidate: true, onsubmit: (e) => {
    e.preventDefault();
    acao(() => enviarAdmin(auth, `/api/admin/pedidos/${p.codigo}`, "PATCH", { codigo_rastreio: codigoRastreio.value.trim() || null }),
      "Código de rastreio salvo ✔");
  } },
    h("div", { class: "campo cresce" }, h("label", { for: `rastreio-${idb}` }, "Código de rastreio (Correios ou transportadora)"), codigoRastreio),
    h("button", { class: "botao secundario", type: "submit" }, "Salvar código"),
    p.url_rastreio ? h("a", { class: "botao secundario", href: p.url_rastreio, target: "_blank", rel: "noopener noreferrer" }, "Rastrear ↗") : null);
  const { lista, outras } = opcoesViagem(viagens, p);
  const viagem = h("select", { id: `viagem-${idb}`, class: "campo-select" },
    h("option", { value: "" }, "Sem barco"),
    lista.map((v) => h("option", { value: v.id, selected: p.viagem && p.viagem.id === v.id },
      `${v.embarcacao} — sai ${quandoAdm(v.saida)}${outras || v.zona_nome !== p.zona_frete ? ` (${v.zona_nome})` : ""}`)));
  const formViagem = h("form", { class: "form-linha", novalidate: true, onsubmit: (e) => {
    e.preventDefault();
    acao(() => enviarAdmin(auth, `/api/admin/pedidos/${p.codigo}`, "PATCH", { viagem_id: viagem.value ? Number(viagem.value) : null }),
      viagem.value ? "Barco definido ✔" : "Barco retirado ✔");
  } },
    h("div", { class: "campo cresce" }, h("label", { for: `viagem-${idb}` }, outras ? "Barco (nenhuma saída para esta zona: mostrando todas)" : "Barco (próximas saídas desta zona)"), viagem),
    h("button", { class: "botao secundario", type: "submit" }, "Salvar barco"));
  const det = h("details", { class: "detalhes-admin", open: aberto, ontoggle: (e) => {
    if (e.target.open) pedidosAbertos.add(p.codigo); else pedidosAbertos.delete(p.codigo);
  } },
    h("summary", {}, `Rastreio e avisos${p.eventos && p.eventos.length ? ` (${p.eventos.length} ${p.eventos.length === 1 ? "evento" : "eventos"})` : ""}`),
    h("div", { class: "rastreio-admin" },
      h("div", {}, h("h3", {}, "Linha do tempo"), linhaTempoAdm(p.eventos)),
      h("div", { class: "pilha-form" },
        cancelado ? h("p", { class: "parcelado" }, "Pedido cancelado: não recebe novos eventos.") : formEvento,
        formRastreio, formViagem)));
  return det;
}

function cartaoPedido(auth, p, viagens) {
  const dono = ehDono();
  const primeiroNome = (p.cliente.nome || "").split(" ")[0];
  const nomeItem = (i) => `${i.quantidade}× ${i.nome}${i.variacao_nome ? ` (${i.variacao_nome})` : ""}`;
  const possiveis = Array.isArray(p.proximos_status) ? [p.status, ...p.proximos_status.filter((s) => s !== p.status)] : Object.keys(STATUS_PEDIDO);
  const travado = p.status === "cancelado" || possiveis.length < 2;
  const zapCliente = zapAdm(p.cliente.telefone, `Olá, ${primeiroNome}! Aqui é da Tipiti, sobre o seu pedido ${p.codigo}.`);
  const zapAviso = p.whatsapp_aviso ? zapAdm(p.cliente.telefone, p.whatsapp_aviso) : null;
  const e = p.entrega || {};
  return h("article", { class: `pedido-admin status-${p.status}`, "aria-labelledby": `ped-${p.codigo}` },
    h("header", { class: "pedido-cabeca" },
      h("div", {}, h("b", { id: `ped-${p.codigo}`, class: "codigo-pedido" }, p.codigo), " ",
        h("span", { class: `etiqueta st-${p.status}` }, STATUS_PEDIDO[p.status] || p.status),
        h("div", { class: "parcelado" }, quandoAdm(p.criado_em))),
      h("div", { class: "pedido-total" }, h("b", {}, brl(p.total_centavos)),
        h("div", { class: "parcelado" }, `${p.pagamento_nome}${p.parcelas > 1 ? ` ${p.parcelas}x` : ""}`))),
    h("div", { class: "pedido-corpo" },
      h("section", {}, h("h3", {}, "Cliente"), h("div", {}, p.cliente.nome),
        h("div", { class: "parcelado" }, p.cliente.email), h("div", { class: "parcelado" }, telefoneAdm(p.cliente.telefone)),
        p.aceites ? h("div", { class: "parcelado" },
          p.aceites.termos_em ? `✔ Aceitou os termos em ${quandoAdm(p.aceites.termos_em)}` : "Sem registro de aceite dos termos",
          h("br"), p.aceites.whatsapp ? "✔ Autorizou contato por WhatsApp" : "✖ Não autorizou mensagens de WhatsApp") : null),
      h("section", {}, h("h3", {}, "Entrega"),
        h("div", {}, `${e.endereco || ""}, ${e.numero || ""} ${e.complemento || ""}`),
        h("div", { class: "parcelado" }, `${e.bairro || ""} · ${e.cidade || ""}/${e.uf || ""} · ${mascaraCep(e.cep || "")}`),
        h("div", { class: "parcelado" }, p.zona_frete, p.prazo_dias ? ` · prazo ${p.prazo_dias} dias` : ""),
        p.previsao_envio ? h("div", { class: "parcelado" }, `📦 Pré-venda: envio previsto em ${dataBrAdm(p.previsao_envio)}`) : null,
        p.viagem ? h("div", {}, `🚢 ${p.viagem.embarcacao}, sai ${quandoAdm(p.viagem.saida)}`) : null,
        p.codigo_rastreio ? h("div", {}, "Rastreio: ", p.url_rastreio ? h("a", { href: p.url_rastreio, target: "_blank", rel: "noopener noreferrer" }, p.codigo_rastreio) : p.codigo_rastreio) : null,
        p.separado_em ? h("div", { class: "parcelado" }, `Separado em ${quandoAdm(p.separado_em)}`) : null),
      h("section", {}, h("h3", {}, "Itens"), p.itens.map((i) => h("div", {}, nomeItem(i))),
        p.cupom_codigo ? h("div", { class: "parcelado" }, `🎟️ Cupom ${p.cupom_codigo}${p.desconto_cupom_centavos ? ` (−${brl(p.desconto_cupom_centavos)})` : ""}`) : null,
        dono && p.revendedora ? h("div", { class: "parcelado" }, `🤝 Revendedora: ${p.revendedora.nome}`,
          typeof p.comissao_centavos === "number" && p.comissao_centavos ? ` · comissão ${brl(p.comissao_centavos)}${p.comissao_paga ? " (paga)" : ""}` : "") : null,
        dono && "lucro_centavos" in p ? h("div", { class: "parcelado" }, "Lucro: ", p.lucro_centavos === null ? "sem custo cadastrado" : brl(p.lucro_centavos)) : null)),
    h("div", { class: "pedido-acoes" },
      h("div", { class: "campo" }, h("label", { for: `status-${p.codigo}` }, "Status"),
        h("select", { id: `status-${p.codigo}`, class: "campo-select", disabled: travado,
          onchange: async (ev) => {
            const novo = ev.target.value;
            if (novo === "cancelado" && !confirm("Cancelar o pedido e devolver os itens ao estoque?")) { ev.target.value = p.status; return; }
            try {
              await enviarAdmin(auth, `/api/admin/pedidos/${p.codigo}`, "PATCH", { status: novo });
              avisar("Status atualizado ✔");
              atualizarAba();
            } catch (err) { if (err.status !== 401) avisar(err.message); ev.target.value = p.status; }
          } }, possiveis.map((v) => h("option", { value: v, selected: v === p.status }, STATUS_PEDIDO[v] || v)))),
      botaoZapAdm(zapCliente, `WhatsApp de ${primeiroNome}`),
      zapAviso ? botaoZapAdm(zapAviso, "Avisar no WhatsApp") : null),
    zapAviso ? h("p", { class: "aviso-pronto" }, h("small", {}, "Mensagem do aviso: "), p.whatsapp_aviso.split("\n")[1] || "") : null,
    secaoRastreio(auth, p, viagens));
}

async function painelPedidos(auth) {
  const dono = ehDono();
  const url = filtroPedidos ? `/api/admin/pedidos?status=${encodeURIComponent(filtroPedidos)}` : "/api/admin/pedidos";
  const [pedidos, resumo, viagens] = await Promise.all([api(url, { headers: auth }), api("/api/admin/resumo", { headers: auth }),
    api("/api/admin/viagens", { headers: auth }).catch(() => [])]);
  const contagem = (n, um, varios) => `${n} ${n === 1 ? um : varios}`;
  return h("div", {},
    dono ? faixaPendenciasLegais(resumo.pendencias_legais) : null,
    h("div", { class: "cartoes-numeros" },
      cartaoNumero("Pedidos", resumo.pedidos, "sem contar cancelados"),
      cartaoNumero("Faturamento", brl(resumo.faturamento_centavos), "com frete"),
      dono && "lucro_centavos" in resumo ? cartaoNumero("Lucro estimado", brl(resumo.lucro_centavos),
        resumo.pedidos_sem_custo ? `${resumo.pedidos_sem_custo} pedido(s) sem custo cadastrado` : "produtos − custo, sem o frete") : null,
      cartaoNumero("Ticket médio", brl(resumo.ticket_medio_centavos)),
      "encomendas_novas" in resumo ? cartaoNumero("Encomendas novas", resumo.encomendas_novas, resumo.encomendas_novas ? "para cotar →" : "nada para cotar", "encomendas") : null,
      dono && "revendedoras_pendentes" in resumo ? cartaoNumero("Revendedoras", resumo.revendedoras_pendentes,
        resumo.revendedoras_pendentes ? "aguardando aprovação →" : "nenhuma pendente", "revendedoras") : null,
      dono && "emails_pendentes" in resumo ? cartaoNumero("E-mails na fila", resumo.emails_pendentes,
        resumo.email_configurado ? "envio ligado" : "e-mail desligado no servidor", "emails") : null),
    resumo.estoque_baixo && resumo.estoque_baixo.length ? h("div", { class: "info-box espaco-baixo" },
      h("b", {}, "⚠️ Estoque baixo: "),
      resumo.estoque_baixo.map((p, k) => [k ? ", " : "", h("a", { href: `/admin/produto/${p.slug}` }, p.nome), ` (${p.estoque})`])) : null,
    h("div", { class: "barra-admin" },
      filtroAdm("filtro-pedidos", "Mostrar", [["", "Todos os pedidos"], ...Object.entries(STATUS_PEDIDO)], filtroPedidos,
        (v) => { filtroPedidos = v; atualizarAba(); }),
      h("span", { class: "parcelado" }, contagem(pedidos.length, "pedido", "pedidos")),
      h("button", { class: "botao secundario", type: "button", onclick: () => irParaAba("separacao") }, "📦 Separação e etiquetas")),
    pedidos.length ? h("div", { class: "lista-pedidos-admin" }, pedidos.map((p) => cartaoPedido(auth, p, Array.isArray(viagens) ? viagens : [])))
      : h("p", { class: "painel" }, filtroPedidos ? "Nenhum pedido com este status." : "Nenhum pedido ainda."));
}

// -- Code128 (conjunto B): código do pedido na etiqueta, desenhado em SVG

/** Larguras (barra, espaço, barra…) de cada símbolo 0–105 e do stop (106), em módulos. */
const CODE128_PADROES = ("212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 112232 122132 122231 113222 "
  + "123122 123221 223211 221132 221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 212123 212321 232121 111323 131123 "
  + "131321 112313 132113 132311 211313 231113 231311 112133 112331 132131 113123 113321 133121 313121 211331 231131 213113 213311 213131 "
  + "311123 311321 331121 312113 312311 332111 314111 221411 431111 111224 111422 121124 121421 141122 141221 112214 112412 122114 122411 "
  + "142112 142211 241211 221114 413111 241112 134111 111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 214121 412121 "
  + "111143 111341 131141 114113 114311 411113 411311 113141 114131 311141 411131 211412 211214 211232 2331112").split(" ");

/** Valores dos símbolos: start B, caracteres, dígito verificador (módulo 103) e stop. Só ASCII 32–126. */
function code128BValores(texto) {
  const valores = [104];
  for (const ch of String(texto)) {
    const c = ch.charCodeAt(0);
    if (c < 32 || c > 126) throw new Error("Code128-B aceita só letras, números e símbolos ASCII.");
    valores.push(c - 32);
  }
  const soma = valores.reduce((s, v, i) => s + v * (i || 1), 0);
  return [...valores, soma % 103, 106];
}

/** "11010010000…": 1 = barra, 0 = espaço, um caractere por módulo. */
function code128BModulos(texto) {
  return code128BValores(texto).map((v) => CODE128_PADROES[v].split("").map((w, k) => (k % 2 ? "0" : "1").repeat(Number(w))).join("")).join("");
}

function svgCode128(texto, { altura = 56, rotulo = true } = {}) {
  const ns = "http://www.w3.org/2000/svg";
  const modulos = code128BModulos(texto);
  const margem = 10;  // zona de silêncio: 10 módulos de cada lado
  const largura = modulos.length + margem * 2;
  const svg = document.createElementNS(ns, "svg");
  const alturaTotal = altura + (rotulo ? 14 : 0);
  for (const [k, v] of Object.entries({ viewBox: `0 0 ${largura} ${alturaTotal}`, class: "codigo-barras", role: "img",
    "aria-label": `Código de barras ${texto}`, preserveAspectRatio: "none", "shape-rendering": "crispEdges" })) svg.setAttribute(k, v);
  const fundo = document.createElementNS(ns, "rect");
  for (const [k, v] of Object.entries({ x: 0, y: 0, width: largura, height: alturaTotal, fill: "#fff" })) fundo.setAttribute(k, v);
  svg.append(fundo);
  let d = "";
  for (let i = 0; i < modulos.length;) {
    if (modulos[i] !== "1") { i++; continue; }
    let j = i;
    while (modulos[j] === "1") j++;
    d += `M${margem + i} 0h${j - i}v${altura}h-${j - i}z`;
    i = j;
  }
  const barras = document.createElementNS(ns, "path");
  barras.setAttribute("d", d);
  barras.setAttribute("fill", "#000");
  svg.append(barras);
  if (rotulo) {
    const t = document.createElementNS(ns, "text");
    for (const [k, v] of Object.entries({ x: largura / 2, y: alturaTotal - 2, "text-anchor": "middle", "font-size": 12, "font-family": "monospace", fill: "#000" })) t.setAttribute(k, v);
    t.textContent = texto;
    svg.append(t);
  }
  return svg;
}

// -- separação e etiquetas

let statusSeparacao = "pago";
const CHAVE_FORMATO_ETIQUETA = "tipiti:admin-etiqueta";

function imprimirAdm(modo) {
  const corpo = document.body.classList;
  corpo.remove("imprimir-lista", "imprimir-etiquetas");
  corpo.add(modo);
  const limpar = () => { corpo.remove(modo); window.removeEventListener("afterprint", limpar); };
  window.addEventListener("afterprint", limpar);
  window.print();
}

function etiquetaEnvio(r, p) {
  const linha = (...partes) => partes.filter(Boolean).join(" ");
  const qtd = p.itens.reduce((s, i) => s + i.quantidade, 0);
  return h("article", { class: "etiqueta-envio", "data-codigo": p.codigo },
    h("div", { class: "etq-remetente" }, h("small", {}, "REMETENTE"),
      h("b", {}, r.nome || "[razão social em Configurações]"),
      r.documento ? h("div", {}, r.documento) : null,
      h("div", {}, r.endereco || "[endereço em Configurações]"),
      h("div", {}, linha(r.cep ? `CEP ${r.cep}` : null, r.cidade && r.uf ? `${r.cidade}/${r.uf}` : r.cidade || "")),
      r.telefone ? h("div", {}, `Tel. ${r.telefone}`) : null),
    h("div", { class: "etq-destinatario" }, h("small", {}, "DESTINATÁRIO"),
      h("b", { class: "etq-nome" }, p.destinatario),
      h("div", {}, linha(`${p.endereco},`, p.numero, p.complemento ? `— ${p.complemento}` : null)),
      h("div", {}, p.bairro),
      h("div", { class: "etq-cidade" }, h("b", {}, `CEP ${p.cep}`), ` ${p.cidade}/${p.uf}`),
      p.telefone ? h("div", {}, `Tel. ${telefoneAdm(p.telefone)}`) : null),
    h("div", { class: "etq-pedido" },
      svgCode128(p.codigo, { rotulo: false }),
      h("div", { class: "etq-codigo" }, p.codigo),
      h("div", { class: "etq-info" },
        h("span", {}, `Pedido ${p.codigo}`), h("span", {}, `${qtd} ${qtd === 1 ? "item" : "itens"}`),
        p.viagem ? h("span", {}, `🚢 ${p.viagem.embarcacao} · ${quandoAdm(p.viagem.saida)}`) : h("span", {}, p.zona || ""))));
}

async function painelSeparacao(auth) {
  const dados = await api(`/api/admin/separacao?status=${encodeURIComponent(statusSeparacao)}`, { headers: auth });
  const pedidos = dados.pedidos || [];
  const r = dados.remetente || {};
  let formato = lerArmazenado(CHAVE_FORMATO_ETIQUETA, "a4");
  if (formato !== "a4" && formato !== "10x15") formato = "a4";
  const marcados = new Set(pedidos.filter((p) => !p.separado_em).map((p) => p.codigo));
  const areaEtiquetas = h("div", { class: `area-etiquetas formato-${formato}` });
  const desenharEtiquetas = () => trocar(areaEtiquetas, pedidos.filter((p) => marcados.has(p.codigo)).map((p) => etiquetaEnvio(r, p)));
  const contador = h("span", { class: "parcelado", "aria-live": "polite" });
  const atualizarContador = () => { contador.textContent = `${marcados.size} de ${pedidos.length} selecionado${marcados.size === 1 ? "" : "s"}`; };
  const faltaRemetente = !r.nome || !r.endereco || !r.cep;
  const botaoSeparados = h("button", { class: "botao", type: "button", onclick: async () => {
    if (!marcados.size) return avisar("Selecione pelo menos um pedido.");
    if (!confirm(`Marcar ${marcados.size} pedido(s) como separados? Cada cliente recebe o aviso “Pedido separado”.`)) return;
    try {
      const res = await enviarAdmin(auth, "/api/admin/pedidos/separados", "POST", { codigos: [...marcados] });
      avisar(`${res.separados.length} pedido(s) marcados como separados ✔${res.nao_encontrados.length ? ` · não encontrados: ${res.nao_encontrados.join(", ")}` : ""}`);
      atualizarAba();
    } catch (err) { if (err.status !== 401) avisar(err.message); }
  } }, "✔ Marcar selecionados como separados");
  const seletorFormato = h("div", { class: "formato-etiqueta", role: "radiogroup", "aria-label": "Tamanho da etiqueta" },
    [["a4", "Folha A4 (4 por folha)"], ["10x15", "Etiqueta 10 × 15 cm"]].map(([v, t]) => h("label", { class: "caixa" },
      h("input", { type: "radio", name: "formato-etiqueta", value: v, checked: v === formato, onchange: () => {
        formato = v;
        gravar(CHAVE_FORMATO_ETIQUETA, v);
        areaEtiquetas.className = `area-etiquetas formato-${v}`;
      } }), ` ${t}`)));
  atualizarContador();
  desenharEtiquetas();
  return h("div", { class: "pilha separacao" },
    h("div", { class: "barra-admin nao-imprimir" },
      filtroAdm("filtro-separacao", "Pedidos", [["pago", "Pagos (para separar)"], ["enviado", "Enviados"], ["aguardando_pagamento", "Aguardando pagamento"]],
        statusSeparacao, (v) => { statusSeparacao = v; atualizarAba(); }),
      h("span", { class: "parcelado" }, `${pedidos.length} pedido${pedidos.length === 1 ? "" : "s"}`)),
    faltaRemetente ? h("div", { class: "alerta nao-imprimir" }, "O remetente das etiquetas vem dos dados da empresa, que estão incompletos. ",
      ehDono() ? h("button", { class: "link-botao", type: "button", onclick: () => irParaAba("configuracoes") }, "Preencher em Configurações") : "Peça ao dono para preencher em Configurações.") : null,
    !pedidos.length ? h("p", { class: "painel" }, statusSeparacao === "pago" ? "Nenhum pedido pago esperando separação. 🎉" : "Nenhum pedido com este status.") : [
      h("section", { class: "painel area-lista", "aria-labelledby": "titulo-lista-sep" },
        h("div", { class: "secao-cabecalho" }, h("h2", { id: "titulo-lista-sep" }, "Lista de separação"),
          h("button", { class: "botao secundario nao-imprimir", type: "button", onclick: () => imprimirAdm("imprimir-lista") }, "🖨️ Imprimir lista")),
        h("p", { class: "parcelado" }, `Tudo o que sai nos ${pedidos.length} pedido(s), somado por produto e opção.`),
        h("table", { class: "tabela-admin tabela-separacao" },
          h("thead", {}, h("tr", {}, ["", "Produto", "Opção", "SKU", "Qtd."].map((t, k) => h("th", { class: k === 4 ? "num" : null }, t || h("span", { class: "sr" }, "Pegou"))))),
          h("tbody", {}, (dados.consolidado || []).map((c, k) => h("tr", {},
            h("td", {}, h("input", { type: "checkbox", "aria-label": `Separei ${c.produto}${c.variacao ? ` ${c.variacao}` : ""}`, id: `pegou-${k}` })),
            h("td", {}, h("label", { for: `pegou-${k}` }, c.produto)), h("td", {}, c.variacao || "—"), h("td", { class: "sku" }, c.sku || "—"),
            h("td", { class: "num" }, h("b", {}, c.quantidade))))))),
      h("section", { class: "painel nao-imprimir", "aria-labelledby": "titulo-pedidos-sep" },
        h("h2", { id: "titulo-pedidos-sep" }, "Pedidos e etiquetas"),
        h("div", { class: "lista-separacao" }, pedidos.map((p) => h("label", { class: "pedido-sep" },
          h("input", { type: "checkbox", checked: marcados.has(p.codigo), onchange: (e) => {
            if (e.target.checked) marcados.add(p.codigo); else marcados.delete(p.codigo);
            atualizarContador();
            desenharEtiquetas();
          } }),
          h("span", {}, h("b", {}, p.codigo), ` · ${p.destinatario} · ${p.cidade}/${p.uf}`,
            h("small", { class: "parcelado" }, p.itens.map((i) => `${i.quantidade}× ${i.produto}${i.variacao ? ` (${i.variacao})` : ""}`).join(", ")),
            p.separado_em ? h("small", { class: "etiqueta ativo" }, `separado ${quandoAdm(p.separado_em)}`) : null)))),
        h("div", { class: "barra-admin" }, contador),
        seletorFormato,
        h("div", { class: "compra" },
          h("button", { class: "botao secundario", type: "button", onclick: () => {
            if (!marcados.size) return avisar("Selecione pelo menos um pedido.");
            imprimirAdm("imprimir-etiquetas");
          } }, "🖨️ Imprimir etiquetas"),
          botaoSeparados)),
      h("section", { class: "area-impressao-etiquetas", "aria-label": "Prévia das etiquetas" },
        h("h2", { class: "nao-imprimir" }, "Prévia das etiquetas"), areaEtiquetas)]);
}
