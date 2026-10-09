// ------------------------------------------------------------- componentes

function precoPix(centavos) {
  return Math.round(centavos - Math.floor((centavos * estado.loja.desconto_pix_pct) / 100));
}

function numeroParcelas(centavos) {
  return Math.max(1, Math.min(estado.loja.parcelas_max, Math.floor(centavos / estado.loja.parcela_minima)));
}

function textoParcelas(centavos) {
  const n = numeroParcelas(centavos);
  return n > 1 ? `ou ${n}x de ${brl(Math.ceil(centavos / n))} sem juros` : "";
}

/** `contagem`: mostra a contagem regressiva da oferta (seção "Ofertas relâmpago"). */
function cartaoProduto(p, prioritario = false, { contagem = false } = {}) {
  const final = precoFinal(p);
  const ancora = precoAncora(p);
  const off = pctDesconto(final, ancora);
  const selos = selosProduto(p, { semOferta: off > 0 });
  const n = vendidos(p);
  return h("a", { class: "cartao-produto", href: `/produto/${p.slug}` },
    off || selos.length ? h("span", { class: "selos" },
      off ? h("span", { class: "selo selo-desconto" }, `-${off}%`) : null,
      selos.map((s) => h("span", { class: `selo selo-${s.replace("_", "-")}` }, SELOS[s]))) : null,
    h("img", { src: imagemProduto(p, true), alt: "", loading: prioritario ? null : "lazy", decoding: "async", width: 400, height: 400 }),
    h("div", { class: "info" },
      h("span", { class: "nome" }, p.nome),
      resumoNota(p, { curto: true }),
      ancora ? h("span", { class: "preco-de" }, h("span", { class: "sr" }, "De "), brl(ancora)) : null,
      h("span", { class: "preco" }, ancora ? h("span", { class: "sr" }, "por ") : null, brl(final)),
      h("span", { class: "preco-pix" }, `${brl(precoPix(final))} no Pix`),
      prevendaDe(p) ? h("span", { class: "chega-prevenda" }, `Chega em ${diaMes(p.prevenda.chegada)} — reserve agora`) : null,
      p.estoque > 0 ? h("span", { class: "parcelado" }, textoParcelas(final))
        : h("span", { class: "esgotado" }, prevendaDe(p) ? "Vagas esgotadas" : "Esgotado"),
      n ? h("span", { class: "vendidos" }, h("span", { "aria-hidden": "true" }, "🔥 "), `${n} vendidos`) : null,
      contagem && p.promo ? contagemOferta(p.promo.fim, { prefixo: "Termina em ", classe: "contagem contagem-cartao" }) : null,
    ),
  );
}

/** `prioritarios`: quantos cartões carregam a imagem sem `loading=lazy` (os que aparecem logo de cara). */
function gradeProdutos(lista, prioritarios = 4) {
  if (!lista.length) {
    return h("div", { class: "vazio" }, h("div", { class: "ico" }, "🔎"), h("p", {}, "Nenhum produto encontrado."));
  }
  return h("div", { class: "grade-produtos" }, lista.map((p, k) => cartaoProduto(p, k < prioritarios)));
}

function esqueletoCartoes(n) {
  return h("div", { class: "grade-produtos", "aria-hidden": "true" }, Array.from({ length: n }, () =>
    h("div", { class: "cartao-produto esqueleto" }, h("div", { class: "esq-img" }),
      h("div", { class: "info" }, h("span", { class: "esq-linha" }), h("span", { class: "esq-linha curta" }), h("span", { class: "esq-linha curta" })))));
}

function esqueletoPagina() {
  return [h("p", { class: "sr" }, "Carregando…"), h("div", { class: "esq-linha esq-titulo", "aria-hidden": "true" }), esqueletoCartoes(8)];
}

function campo(nome, rotulo, attrs = {}, classe = "c3", dica = null) {
  const id = `campo-${nome}`;
  return h("div", { class: `campo ${classe}`, "data-campo": nome },
    h("label", { for: id }, rotulo),
    h("input", { id, name: nome, type: "text", "aria-describedby": [dica ? `dica-${nome}` : null, `erro-${nome}`].filter(Boolean).join(" "), ...attrs }),
    dica ? h("span", { class: "dica-campo", id: `dica-${nome}` }, dica) : null,
    h("span", { class: "msg-erro", id: `erro-${nome}` }),
  );
}

/** Marca (ou limpa, com msg vazia) o erro de um bloco [data-campo]. */
function marcarErro(c, msg) {
  c.classList.toggle("com-erro", Boolean(msg));
  const m = $(".msg-erro", c);
  if (m) m.textContent = msg || "";
  c.querySelectorAll("input:not([type=radio]):not([type=checkbox]), select, textarea").forEach((ctrl) => {
    if (msg) ctrl.setAttribute("aria-invalid", "true");
    else ctrl.removeAttribute("aria-invalid");
  });
}

function mostrarErros(form, campos, focar = true) {
  form.querySelectorAll("[data-campo]").forEach((c) => marcarErro(c, ""));
  let primeiro = null;
  for (const [nome, msg] of Object.entries(campos || {})) {
    const c = form.querySelector(`[data-campo="${nome}"]`);
    if (!c || typeof msg !== "string") continue;
    marcarErro(c, msg);
    primeiro = primeiro || c.querySelector("input:not([type=hidden]), select, textarea");
  }
  if (primeiro && focar) primeiro.focus();
}

function linkNaoSeiCep() {
  return h("a", { href: "https://buscacepinter.correios.com.br/", target: "_blank", rel: "noopener", class: "parcelado link-cep" }, "Não sei meu CEP");
}

/** `itemPrevenda()` (produto em pré-venda): o item do carrinho a cotar, para o prazo e o barco contarem da previsão de envio. */
function simuladorFrete(obterSubtotal, itemPrevenda = null) {
  const saida = h("div", { class: "resultado-frete", "aria-live": "polite" });
  const input = h("input", { id: "simulador-cep", type: "text", inputmode: "numeric", autocomplete: "postal-code", placeholder: "00000-000",
    value: lerArmazenado("tipiti:cep", "") || "", oninput: (e) => (e.target.value = mascaraCep(e.target.value)) });
  const form = h("form", {
    onsubmit: async (e) => {
      e.preventDefault();
      saida.textContent = "Calculando…";
      try {
        const item = itemPrevenda && itemPrevenda();
        let f;
        let previsao = null;
        if (item) {
          const c = await api("/api/carrinho/cotacao", { method: "POST", body: JSON.stringify({ itens: [item], cep: input.value }) });
          ({ frete: f, previsao_envio: previsao } = c);
        } else f = await api(`/api/frete?cep=${encodeURIComponent(input.value)}&subtotal=${obterSubtotal()}`);
        gravar("tipiti:cep", f.cep);
        trocar(saida, h("b", {}, f.zona_nome), " — ",
          f.gratis ? h("span", { class: "desconto" }, "Frete grátis") : brl(f.valor_centavos),
          `, ${textoPrazoFrete(f, previsao)}.`,
          linhaPrevisaoEnvio(previsao),
          linhaProximoBarco(f),
          !f.regiao_norte ? h("div", { class: "parcelado" }, "Entregamos em todo o Brasil, com prioridade para a Região Norte.") : null,
        );
      } catch (err) {
        saida.textContent = err.message;
      }
    },
  }, input, h("button", { class: "botao secundario", type: "submit" }, "Calcular"));
  return h("div", { class: "simulador" },
    h("label", { for: "simulador-cep", class: "rotulo-simulador" }, "🚚 Calcular frete e prazo"), form, saida, linkNaoSeiCep());
}
