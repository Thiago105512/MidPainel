// ------------------------------------------------------------- Pix copia e cola + QR Code e rastreio do pedido

/**
 * Bloco "Pague com Pix" da página do pedido: valor, copia e cola com botão grande, QR Code e passos.
 * `alternativa()`: o bloco antigo (chave Pix para copiar), usado se o servidor recusar (409/404) ou falhar.
 */
function blocoPixPedido(p, zap, alternativa) {
  const caixa = h("div", { class: "info-box passos pix-pedido", "aria-live": "polite" },
    h("h2", {}, "Pague com Pix para confirmar"), h("p", { class: "parcelado" }, "Gerando o seu Pix…"));
  const ativo = vigencia();
  api(`/api/pedidos/${encodeURIComponent(p.codigo)}/pix`).then((pix) => {
    if (!ativo() || !caixa.isConnected) return;
    const valor = brl(pix.valor_centavos);
    const area = h("textarea", { id: "pix-copia-cola", class: "campo-texto pix-codigo", readonly: true, rows: 3, spellcheck: "false",
      "aria-describedby": "pix-dica", onfocus: (e) => e.target.select() });
    area.value = pix.copia_e_cola;
    const situacao = h("p", { class: "pix-estado", role: "status" });
    const botao = h("button", { class: "botao grande pix-copiar", type: "button", onclick: async () => {
      if (await copiarTexto(pix.copia_e_cola)) {
        botao.textContent = "✔ Código copiado!";
        situacao.textContent = "Código Pix copiado. Agora abra o app do seu banco e cole em Pix Copia e Cola.";
        setTimeout(() => { if (botao.isConnected) botao.textContent = "📋 Copiar código Pix"; }, 4000);
      } else {
        area.focus();
        area.select();
        situacao.textContent = "Não deu para copiar sozinho: o código está selecionado, use Copiar do seu celular.";
      }
    } }, "📋 Copiar código Pix");
    trocar(caixa,
      h("h2", {}, "Pague com Pix para confirmar"),
      h("p", { class: "pix-valor" }, "Valor: ", h("b", {}, valor)),
      h("label", { for: "pix-copia-cola", class: "rotulo-pix" }, "Pix copia e cola"),
      area,
      h("span", { class: "dica-campo", id: "pix-dica" }, "Toque no botão para copiar o código inteiro."),
      botao,
      situacao,
      h("div", { class: "pix-qr" },
        h("img", { src: pix.qr_svg, alt: `QR Code do Pix de ${valor} para o pedido ${p.codigo}`, width: 280, height: 280, decoding: "async" }),
        h("p", { class: "parcelado" }, "Pagando de outro aparelho? Leia o QR Code com o app do banco.")),
      h("ol", {},
        h("li", {}, "Toque em ", h("b", {}, "Copiar código Pix"), "."),
        h("li", {}, "Abra o app do seu banco e escolha ", h("b", {}, "Pix › Pix Copia e Cola"), " (ou ", h("b", {}, "Ler QR Code"), ")."),
        h("li", {}, "Cole o código, confira o valor de ", h("b", {}, valor), " e o recebedor, e confirme."),
        h("li", {}, zap ? "Envie o comprovante pelo WhatsApp e despachamos seu pedido." : "Assim que o pagamento cair, despachamos seu pedido.")));
  }).catch((err) => {
    if (!ativo() || !caixa.isConnected) return;
    const antigo = alternativa ? alternativa() : null;
    if (antigo) caixa.replaceWith(antigo);
    else trocar(caixa, h("h2", {}, "Pagamento"), h("p", {}, err.status === 409 ? err.message : "Não conseguimos gerar o Pix agora. Fale com a loja pelo WhatsApp ou tente de novo em instantes."));
  });
  return caixa;
}

const ICONES_EVENTO = { pago: "💰", separado: "📦", embarcado: "🛶", chegou_porto: "⚓", saiu_entrega: "🛵", entregue: "🏠", outro: "📝" };

/** Linha do tempo do pedido (mais recente primeiro), código de rastreio, barco e previsão de envio. */
function blocoRastreio(p, { titulo = true } = {}) {
  const eventos = Array.isArray(p.eventos) ? p.eventos : [];
  const v = p.viagem;
  if (!eventos.length && !p.codigo_rastreio && !v && !p.previsao_envio) return null;
  return h("section", { class: "painel rastreio", "aria-label": titulo ? null : `Rastreio do pedido ${p.codigo}` },
    titulo ? h("h2", {}, "Acompanhe seu pedido") : null,
    p.previsao_envio ? linhaPrevisaoEnvio(p.previsao_envio) : null,
    v ? h("p", { class: "proximo-barco" }, h("span", { "aria-hidden": "true" }, "🛶 "), "Vai no barco ", h("b", {}, v.embarcacao),
      ` rumo a ${v.zona_nome}: sai ${semanaDiaMes(v.saida)}${horaManaus(v.saida) ? ` às ${horaManaus(v.saida)}` : ""} · chega ${diaMes(v.chegada_prevista)}`) : null,
    p.codigo_rastreio ? h("div", { class: "codigo-rastreio" },
      h("span", {}, "Código de rastreio: ", h("b", { class: "codigo-cupom" }, p.codigo_rastreio)),
      h("span", { class: "acoes-rastreio" },
        botaoCopiar(p.codigo_rastreio, "Copiar", "Código de rastreio copiado ✔"),
        p.url_rastreio ? h("a", { class: "botao secundario", href: p.url_rastreio, target: "_blank", rel: "noopener" }, "Rastrear nos Correios ↗") : null)) : null,
    eventos.length ? h("ol", { class: "linha-tempo" }, eventos.map((e, k) =>
      h("li", { class: k === 0 ? "atual" : null },
        h("span", { class: "ico-evento", "aria-hidden": "true" }, ICONES_EVENTO[e.tipo] || ICONES_EVENTO.outro),
        h("div", {},
          h("p", {}, e.mensagem),
          h("time", { datetime: e.data }, dataHoraCurta(e.data)))))) : null);
}
