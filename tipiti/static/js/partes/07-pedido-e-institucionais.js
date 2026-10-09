async function paginaPedido(main, codigo) {
  const ativo = vigencia();
  const p = await api(`/api/pedidos/${encodeURIComponent(codigo)}`);
  if (!ativo()) return;
  document.title = `Pedido ${p.codigo} | Tipiti`;
  const l = estado.loja;
  const chavePix = typeof l.chave_pix === "string" ? l.chave_pix.trim() : "";
  const aguardando = p.status === "aguardando_pagamento";
  const zap = botaoWhatsApp(
    `Olá! Fiz o pedido ${p.codigo} no site da Tipiti.\n${p.itens.map((i) => `• ${i.quantidade}× ${nomeComOpcao(i)}`).join("\n")}\nTotal: ${brl(p.total_centavos)} (${p.pagamento_nome}${p.parcelas > 1 ? ` em ${p.parcelas}x` : ""}).`,
    "Enviar meu pedido no WhatsApp", "botao whatsapp grande");
  const horas = Number(l.prazo_reserva_horas);

  let passos = null;
  const passosChave = () => h("div", { class: "info-box passos" },
      h("h2", {}, "Pague com Pix para confirmar"),
      h("ol", {},
        h("li", {}, "Abra o app do seu banco e escolha Pix › Pagar com chave."),
        h("li", {}, "Cole a chave abaixo e pague ", h("b", {}, brl(p.total_centavos)), "."),
        h("li", {}, zap ? "Envie o comprovante pelo WhatsApp e despachamos seu pedido." : "Assim que o pagamento cair, despachamos seu pedido.")),
      h("div", { class: "chave-pix" },
        h("span", { class: "parcelado" }, "Chave Pix"),
        h("code", {}, chavePix),
        h("span", { class: "parcelado" }, "Valor: ", h("b", {}, brl(p.total_centavos)))),
      botaoCopiar(chavePix, "Copiar chave Pix", "Chave Pix copiada ✔"));
  if (aguardando && p.pagamento === "pix" && l.pix_ativo) {
    // copia e cola + QR Code; se o servidor recusar (409/404), volta à chave Pix
    passos = blocoPixPedido(p, zap, chavePix ? passosChave : null);
  } else if (aguardando && p.pagamento === "pix" && chavePix) {
    passos = passosChave();
  } else if (aguardando) {
    passos = h("div", { class: "info-box passos" },
      h("h2", {}, "Próximo passo: pagamento"),
      h("p", {}, zap ? ["Toque em ", h("b", {}, "Enviar meu pedido no WhatsApp"), " e mandamos as instruções de pagamento",
        p.pagamento === "cartao" ? ` (cartão em ${p.parcelas}x)` : p.pagamento === "boleto" ? " (boleto)" : " (Pix)", "."]
        : ["Vamos entrar em contato pelo seu celular ou e-mail com as instruções de pagamento. Se preferir, escreva para ",
          h("a", { href: `mailto:${l.email}?subject=${encodeURIComponent(`Pedido ${p.codigo}`)}` }, l.email), "."]));
  }

  trocar(main, h("div", { class: "confirmacao" },
      h("div", { class: "ico-grande", "aria-hidden": "true" }, "🎉"),
      h("h1", {}, `Obrigado, ${p.primeiro_nome}!`),
      h("p", {}, "Seu pedido foi registrado com o código"),
      h("div", { class: "linha-codigo" }, h("span", { class: "codigo" }, p.codigo), botaoCopiar(p.codigo, "Copiar código", "Código copiado ✔")),
      zap ? h("div", { class: "acao-principal" }, zap) : null,
      aguardando && horas > 0 ? h("p", { class: "reserva" }, `⏳ Seu pedido fica reservado por ${horas} ${horas === 1 ? "hora" : "horas"}.`) : null,
      h("p", {}, "Status: ", h("b", {}, p.status_nome)),
      passos,
      blocoRastreio(p),
      h("div", { class: "painel itens-pedido" },
        h("h2", {}, "Itens"),
        p.itens.map((i) => h("div", { class: "linha-total" }, h("span", {}, `${i.quantidade}× ${nomeComOpcao(i)}`), h("span", {}, brl(i.preco_unit_centavos * i.quantidade)))),
        h("hr", { class: "divisor" }),
        h("div", { class: "linha-total" }, h("span", {}, "Subtotal"), h("span", {}, brl(p.subtotal_centavos))),
        p.desconto_cupom_centavos > 0 ? h("div", { class: "linha-total desconto" }, h("span", {}, `Cupom${p.cupom_codigo ? ` ${p.cupom_codigo}` : ""}`),
          h("span", {}, `− ${brl(p.desconto_cupom_centavos)}`)) : null,
        p.desconto_centavos ? h("div", { class: "linha-total desconto" }, h("span", {}, "Desconto Pix"), h("span", {}, `− ${brl(p.desconto_centavos)}`)) : null,
        h("div", { class: "linha-total" }, h("span", {}, "Frete"), h("span", {}, p.frete_centavos ? brl(p.frete_centavos) : "Grátis")),
        h("div", { class: "linha-total total" }, h("span", {}, "Total"), h("span", {}, brl(p.total_centavos))),
        h("p", { class: "parcelado" }, p.previsao_envio
          ? `Entrega em ${p.destino} · envio previsto para ${diaMes(p.previsao_envio)} (pré-venda) e entrega em até ${p.prazo_dias} dias úteis depois.`
          : `Entrega em ${p.destino} · prazo de até ${p.prazo_dias} dias úteis após a confirmação do pagamento.`)),
      formularioAvaliacao(p),
      h("p", {}, "Guarde o código para acompanhar o pedido. Dúvidas: ", h("a", { href: `mailto:${l.email}` }, l.email)),
      h("a", { class: "botao secundario", href: "/" }, "Voltar à loja"),
    ),
  );
}

function paginaEntregas(main) {
  document.title = "Entregas e prazos | Tipiti";
  const l = estado.loja;
  trocar(main, h("div", { class: "texto" },
    h("h1", {}, "Entregas e prazos"),
    h("p", {}, `A Tipiti despacha de Manaus e atende com prioridade a Região Norte. Compras acima de ${brl(l.frete_gratis_a_partir)} têm frete grátis para todos os estados do Norte.`),
    h("table", { class: "tabela-frete" },
      h("thead", {}, h("tr", {}, h("th", {}, "Destino"), h("th", {}, "Frete"), h("th", {}, "Prazo"))),
      h("tbody", {}, l.zonas_frete.map((z) => h("tr", {}, h("td", {}, z.nome), h("td", {}, brl(z.valor_centavos)), h("td", {}, `até ${z.prazo_dias} dias úteis`))))),
    h("p", { class: "parcelado" }, "Prazos contados a partir da confirmação do pagamento. Localidades atendidas por via fluvial podem variar conforme o nível dos rios. Também entregamos nas demais regiões do Brasil."),
    h("p", {}, h("a", { class: "botao secundario", href: "/barcos" }, "🛶 Ver o calendário de barcos")),
  ));
}

function paginaSobre(main) {
  document.title = "Sobre a Tipiti";
  trocar(main, h("div", { class: "texto" },
    h("h1", {}, "Sobre a Tipiti"),
    h("p", {}, "A Tipiti nasceu para resolver um problema conhecido de quem mora no Norte: comprar online e esperar semanas, pagando um frete que às vezes custa mais que o produto."),
    h("p", {}, "Importamos da China uma seleção variada de produtos — achadinhos, eletrônicos, casa, beleza, moda, brinquedos e ferramentas —, deixamos tudo em estoque no Brasil e despachamos de perto, para que chegue rápido em Manaus, Parintins, Boa Vista, Santarém, Macapá, Belém e em toda a região."),
    h("p", {}, "O nome vem do tipiti, o trançado indígena que faz parte do dia a dia da região: um objeto simples, resistente e feito para durar. É assim que queremos atender."),
  ));
}

function paginaTrocas(main) {
  document.title = "Trocas e devoluções | Tipiti";
  trocar(main, h("div", { class: "texto" },
    h("h1", {}, "Trocas e devoluções"),
    h("p", {}, "Você pode desistir da compra em até 7 dias corridos após o recebimento, conforme o art. 49 do Código de Defesa do Consumidor, com reembolso integral."),
    h("p", {}, "Produtos com defeito podem ser trocados dentro do prazo de garantia. Fale com a gente informando o código do pedido."),
    h("p", {}, "Contato: ", h("a", { href: `mailto:${estado.loja.email}` }, estado.loja.email)),
  ));
}
