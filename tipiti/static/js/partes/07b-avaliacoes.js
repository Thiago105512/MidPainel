// ------------------------------------------------------------- avaliações (só de quem comprou; publicadas após aprovação)

function dataCurta(texto) {
  const t = Date.parse(texto || "");
  return Number.isNaN(t) ? String(texto || "") : new Date(t).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
}

/** Seção de avaliações da página do produto. */
function secaoAvaliacoes(p) {
  const lista = h("div", { class: "lista-avaliacoes", "aria-live": "polite" }, h("p", { class: "parcelado" }, "Carregando avaliações…"));
  const secao = h("section", { class: "secao avaliacoes", id: "avaliacoes", "aria-labelledby": "titulo-avaliacoes" },
    h("div", { class: "secao-cabecalho" }, h("h2", { id: "titulo-avaliacoes" }, "Avaliações"), resumoNota(p)),
    lista);
  const ativo = vigencia();
  api(`/api/produtos/${encodeURIComponent(p.slug)}/avaliacoes`).then((avaliacoes) => {
    if (!ativo()) return;
    const itens = (Array.isArray(avaliacoes) ? avaliacoes : []).filter((a) => a && a.nota >= 1 && a.nota <= 5);
    if (!itens.length) {
      trocar(lista, h("p", { class: "sem-avaliacoes" }, "Ainda sem avaliações — compre e seja o primeiro a avaliar."));
      return;
    }
    const VISIVEIS = 5;
    const cartao = (a) => h("article", { class: "avaliacao" },
      h("div", { class: "avaliacao-topo" },
        estrelas(a.nota, `Nota ${a.nota} de 5`),
        h("b", {}, a.nome || "Cliente"),
        a.data ? h("span", { class: "parcelado" }, dataCurta(a.data)) : null),
      a.comentario ? h("p", {}, a.comentario) : null,
      h("span", { class: "compra-verificada" }, "✔ Compra verificada"));
    const restantes = itens.slice(VISIVEIS);
    const mais = restantes.length ? h("button", { class: "botao secundario", type: "button", onclick: () => {
      const novos = restantes.map(cartao);
      mais.replaceWith(...novos);
      novos[0].tabIndex = -1;
      novos[0].focus({ preventScroll: true });
    } }, `Ver mais ${restantes.length} ${restantes.length === 1 ? "avaliação" : "avaliações"}`) : null;
    trocar(lista, itens.slice(0, VISIVEIS).map(cartao), mais);
  }).catch(() => {
    if (ativo()) trocar(lista, h("p", { class: "parcelado" }, "Não foi possível carregar as avaliações agora."));
  });
  return secao;
}

/** Cinco botões de rádio (1 a 5 estrelas), com nome acessível em cada um. */
function escolhaEstrelas(nome, rotulo) {
  const grupo = h("div", { class: "escolha-estrelas" });
  const acender = (n) => grupo.querySelectorAll("label").forEach((l, k) => l.classList.toggle("acesa", k < n));
  for (let n = 1; n <= 5; n++) {
    grupo.append(h("label", { title: `${n} ${n === 1 ? "estrela" : "estrelas"}` },
      h("input", { type: "radio", name: nome, value: n, class: "sr", onchange: () => acender(n) }),
      h("span", { "aria-hidden": "true" }, "★"),
      h("span", { class: "sr" }, `${n} ${n === 1 ? "estrela" : "estrelas"}`)));
  }
  return h("fieldset", { class: "campo-estrelas", "data-campo": "nota" }, h("legend", {}, rotulo), grupo, h("span", { class: "msg-erro" }));
}

/** "Avalie sua compra" na página do pedido: um e-mail e, por produto, nota de 1 a 5 e comentário opcional. */
function formularioAvaliacao(pedido) {
  const vistos = new Set();
  const itens = (pedido.itens || []).filter((i) => i.pode_avaliar && i.slug && !vistos.has(i.slug) && vistos.add(i.slug));
  if (!itens.length) return null;
  const geral = h("div", { class: "alerta", role: "alert", hidden: true });
  const blocos = itens.map((i, k) => {
    const resultado = h("p", { class: "resultado-avaliacao", role: "status" });
    const bloco = h("div", { class: "item-avaliacao", "data-slug": i.slug },
      h("p", { class: "nome-item" }, i.nome),
      escolhaEstrelas(`nota-${k}`, `Sua nota para ${i.nome}`),
      h("div", { class: "campo", "data-campo": "comentario" },
        h("label", { for: `comentario-${k}` }, "Comentário (opcional)"),
        h("textarea", { id: `comentario-${k}`, name: `comentario-${k}`, rows: 3, maxlength: 1000, class: "campo-texto",
          placeholder: "O que achou do produto? Chegou bem?" }),
        h("span", { class: "msg-erro" })),
      resultado);
    return { i, k, bloco, resultado, enviado: false };
  });
  const botao = h("button", { class: "botao grande", type: "submit" }, "Enviar avaliação");
  const form = h("form", { class: "painel avaliar-compra", novalidate: true, "aria-labelledby": "titulo-avaliar" },
    h("h2", { id: "titulo-avaliar" }, "⭐ Avalie sua compra"),
    h("p", { class: "parcelado" }, "Sua opinião ajuda outros clientes do Norte. Confirme o e-mail usado no pedido."),
    campo("email", "E-mail do pedido", { type: "email", inputmode: "email", autocomplete: "email", required: true }, "c6"),
    blocos.map((b) => b.bloco),
    geral,
    botao);

  form.addEventListener("change", (e) => {
    const c = e.target.closest("[data-campo]");
    if (c && c.classList.contains("com-erro")) marcarErro(c, "");
  });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    geral.hidden = true;
    const email = form.elements.email.value.trim();
    const campoEmail = form.querySelector('[data-campo="email"]');
    const pendentes = blocos.filter((b) => !b.enviado);
    const escolhidos = pendentes.filter((b) => form.querySelector(`input[name="nota-${b.k}"]:checked`));
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      marcarErro(campoEmail, "Informe o e-mail usado no pedido.");
      form.elements.email.focus();
      return;
    }
    if (!escolhidos.length) {
      const primeiro = pendentes[0];
      marcarErro($(".campo-estrelas", primeiro.bloco), "Escolha de 1 a 5 estrelas.");
      $("input", primeiro.bloco).focus();
      return;
    }
    botao.disabled = true;
    botao.textContent = "Enviando…";
    for (const b of escolhidos) {
      const nota = Number(form.querySelector(`input[name="nota-${b.k}"]:checked`).value);
      const comentario = form.elements[`comentario-${b.k}`].value.trim();
      b.resultado.textContent = "";
      b.resultado.classList.remove("esgotado");
      try {
        await api("/api/avaliacoes", { method: "POST", body: JSON.stringify({ codigo: pedido.codigo, email, slug: b.i.slug, nota, comentario }) });
        b.enviado = true;
        marcarErro(campoEmail, "");
        trocar(b.bloco, h("p", { class: "nome-item" }, b.i.nome),
          h("p", { class: "sucesso-avaliacao", role: "status" }, "✔ Obrigado! Sua avaliação aparece após aprovação."));
      } catch (err) {
        const campos = err.campos || {};
        if (campos.email) marcarErro(campoEmail, campos.email);
        if (campos.nota) marcarErro($(".campo-estrelas", b.bloco), campos.nota);
        if (campos.comentario) marcarErro($('[data-campo="comentario"]', b.bloco), campos.comentario);
        const outros = Object.entries(campos).filter(([k, v]) => !["email", "nota", "comentario"].includes(k) && typeof v === "string").map(([, v]) => v);
        b.resultado.textContent = [err.message, ...outros].join(" ");
        b.resultado.classList.add("esgotado");
        if (campos.email) break;  // o mesmo e-mail falharia nos outros
      }
    }
    botao.disabled = false;
    botao.textContent = "Enviar avaliação";
    if (blocos.every((b) => b.enviado)) {
      trocar(form, h("h2", {}, "⭐ Avalie sua compra"), h("p", { class: "sucesso-avaliacao", role: "status" }, "Obrigado! Sua avaliação aparece após aprovação."));
    } else if (blocos.some((b) => !b.enviado && b.resultado.textContent)) {
      geral.textContent = "Algumas avaliações não foram enviadas. Confira as mensagens acima.";
      geral.hidden = false;
    }
  });
  return form;
}
