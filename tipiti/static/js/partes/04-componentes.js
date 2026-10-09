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

function cartaoProduto(p, prioritario = false) {
  const off = p.preco_de_centavos && p.preco_de_centavos > p.preco_centavos
    ? Math.round((1 - p.preco_centavos / p.preco_de_centavos) * 100) : 0;
  return h("a", { class: "cartao-produto", href: `/produto/${p.slug}` },
    off ? h("span", { class: "selo" }, `-${off}%`) : null,
    h("img", { src: imagemProduto(p, true), alt: "", loading: prioritario ? null : "lazy", decoding: "async", width: 400, height: 400 }),
    h("div", { class: "info" },
      h("span", { class: "nome" }, p.nome),
      off ? h("span", { class: "preco-de" }, brl(p.preco_de_centavos)) : null,
      h("span", { class: "preco" }, brl(p.preco_centavos)),
      h("span", { class: "preco-pix" }, `${brl(precoPix(p.preco_centavos))} no Pix`),
      p.estoque > 0 ? h("span", { class: "parcelado" }, textoParcelas(p.preco_centavos))
        : h("span", { class: "esgotado" }, "Esgotado"),
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

function simuladorFrete(obterSubtotal) {
  const saida = h("div", { class: "resultado-frete", "aria-live": "polite" });
  const input = h("input", { id: "simulador-cep", type: "text", inputmode: "numeric", autocomplete: "postal-code", placeholder: "00000-000",
    value: lerArmazenado("tipiti:cep", "") || "", oninput: (e) => (e.target.value = mascaraCep(e.target.value)) });
  const form = h("form", {
    onsubmit: async (e) => {
      e.preventDefault();
      saida.textContent = "Calculando…";
      try {
        const f = await api(`/api/frete?cep=${encodeURIComponent(input.value)}&subtotal=${obterSubtotal()}`);
        gravar("tipiti:cep", f.cep);
        trocar(saida, h("b", {}, f.zona_nome), " — ",
          f.gratis ? h("span", { class: "desconto" }, "Frete grátis") : brl(f.valor_centavos),
          `, chega em até ${f.prazo_dias} dias úteis.`,
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
