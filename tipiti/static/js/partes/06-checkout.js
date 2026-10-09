/** Linhas de totais. `carrinho`: mostra "Total no Pix" e o valor no cartão, em vez do total da forma escolhida. */
function blocoResumo(c, { carrinho = false } = {}) {
  const l = estado.loja;
  const linha = (rotulo, valor, classe = "") => h("div", { class: `linha-total ${classe}` }, h("span", {}, rotulo), h("span", {}, valor));
  const valorFrete = c.frete ? c.frete.valor_centavos : 0;
  const linhas = [linha("Subtotal", brl(c.subtotal_centavos))];
  if (c.desconto_cupom_centavos > 0) {
    linhas.push(linha(`Cupom${c.cupom && c.cupom.codigo ? ` ${c.cupom.codigo}` : ""}`, `− ${brl(c.desconto_cupom_centavos)}`, "desconto"));
  }
  // o carrinho é cotado no Pix: o servidor já devolve o desconto (e o total) do Pix, com o cupom
  const cotadoNoPix = c.pagamento === "pix";
  const descontoPix = carrinho && !cotadoNoPix ? Math.floor((c.subtotal_centavos * l.desconto_pix_pct) / 100) : c.desconto_centavos;
  if (descontoPix) linhas.push(linha(`Desconto no Pix (${l.desconto_pix_pct}%)`, `− ${brl(descontoPix)}`, "desconto"));
  linhas.push(linha("Frete", c.frete ? (c.frete.gratis ? "Grátis" : brl(c.frete.valor_centavos)) : "Informe o CEP"));
  if (c.frete) linhas.push(h("div", { class: "parcelado" }, `${c.frete.zona_nome} · até ${c.frete.prazo_dias} dias úteis`));
  if (carrinho) {
    const totalPix = cotadoNoPix ? c.total_centavos : c.subtotal_centavos + valorFrete - descontoPix;
    const noCartao = totalPix + descontoPix;
    const n = numeroParcelas(noCartao);
    linhas.push(linha("Total no Pix", brl(totalPix), "total"));
    linhas.push(h("p", { class: "parcelado alinhado-direita" }, n > 1
      ? `ou ${brl(noCartao)} em até ${n}x de ${brl(Math.ceil(noCartao / n))} sem juros no cartão`
      : `ou ${brl(noCartao)} no cartão ou boleto`));
  } else {
    linhas.push(linha("Total", brl(c.total_centavos), "total"));
  }

  const faltam = c.falta_para_frete_gratis;
  const pct = Math.min(100, Math.round((c.subtotal_centavos / l.frete_gratis_a_partir) * 100));
  if (c.economia_centavos > 0) {
    linhas.push(h("p", { class: "economia-total" }, h("span", { "aria-hidden": "true" }, "💰 "), "Você está economizando ", h("b", {}, brl(c.economia_centavos))));
  }
  if (c.cupom && c.cupom.frete_gratis) {
    return [h("div", { class: "barra-frete" }, `🎉 Frete grátis com o cupom ${c.cupom.codigo}!`), ...linhas];
  }
  const barra = (!c.frete || c.frete.regiao_norte) ? h("div", { class: "barra-frete" },
    faltam > 0 ? [`Faltam `, h("b", {}, brl(faltam)), ` para frete grátis na Região Norte`] : "🎉 Você ganhou frete grátis na Região Norte!",
    h("div", { class: "barra-progresso" }, h("span", { style: `width:${pct}%` }))) : null;
  return [barra, ...linhas];
}

/** Cota o carrinho; se o CEP salvo for inválido, cota sem ele e devolve a mensagem. */
async function cotarCarrinho(cep, extra = {}) {
  const pedir = (comCep) => api("/api/carrinho/cotacao", { method: "POST",
    body: JSON.stringify({ itens: estado.carrinho, cep: comCep || null, ...extra }) });
  try {
    return { cotacao: await pedir(cep), erroCep: "" };
  } catch (err) {
    if (!(err.campos && err.campos.cep)) throw err;
    gravar("tipiti:cep", "");
    return { cotacao: await pedir(null), erroCep: err.campos.cep };
  }
}

async function paginaCarrinho(main) {
  const ativo = vigencia();
  document.title = "Carrinho | Tipiti";
  const vazio = () => trocar(main, h("div", { class: "vazio" }, h("div", { class: "ico" }, "🛒"),
    h("h1", { tabindex: "-1" }, "Seu carrinho está vazio"), h("p", {}, "Que tal dar uma olhada nos destaques?"),
    h("a", { class: "botao", href: "/" }, "Continuar comprando")));
  if (!estado.carrinho.length) return vazio();
  let cep = lerArmazenado("tipiti:cep", "");
  let cupom = cupomGuardado();
  let erroCupom = "";
  const extra = () => (cupom ? { cupom } : {});
  let { cotacao, erroCep } = await cotarCarrinho(cep, extra());
  if (!ativo()) return;

  // produto que saiu do catálogo: remove sozinho e avisa; os demais problemas ficam visíveis
  const sumiram = cotacao.itens.filter((i) => !i.produto_id && i.erro === "Produto indisponível.");
  if (sumiram.length) {
    const fora = new Set(sumiram.map((i) => i.chave));
    estado.carrinho = estado.carrinho.filter((i) => !fora.has(chaveItem(i.slug, i.variacao)));
    salvarCarrinho();
    avisar(sumiram.length === 1 ? "Um produto saiu do catálogo e foi tirado do seu carrinho."
      : `${sumiram.length} produtos saíram do catálogo e foram tirados do seu carrinho.`);
    if (!estado.carrinho.length) return vazio();
    ({ cotacao, erroCep } = await cotarCarrinho(cep, extra()));
    if (!ativo()) return;
  }

  const titulo = h("h1", {}, "Meu carrinho");
  const refs = new Map();

  let espera;
  let sequencia = 0;
  const resumo = h("aside", { class: "painel resumo", "aria-label": "Resumo do carrinho" });
  const recotar = (atraso = 300) => {
    clearTimeout(espera);
    resumo.setAttribute("aria-busy", "true");
    espera = setTimeout(async () => {
      const n = ++sequencia;
      try {
        const r = await cotarCarrinho(cep, extra());
        if (!ativo() || n !== sequencia) return;
        ({ cotacao, erroCep } = r);
        if (erroCep) cep = "";
        for (const i of cotacao.itens) if (refs.has(i.chave)) atualizarLinha(refs.get(i.chave), i);
        desenharResumo();
      } catch (err) {
        if (ativo() && n === sequencia) avisar(err.message);
      } finally {
        if (n === sequencia) resumo.removeAttribute("aria-busy");
      }
    }, atraso);
  };

  function atualizarLinha(ref, i) {
    ref.item = i;
    if (ref.total) ref.total.textContent = brl(i.total_centavos);
    ref.erro.textContent = i.erro || "";
    ref.erro.hidden = !i.erro;
  }

  const remover = (i) => {
    alterarQuantidade(i.chave, 0);
    const ref = refs.get(i.chave);
    if (ref) ref.linha.remove();
    refs.delete(i.chave);
    if (!estado.carrinho.length) return vazio();
    avisar(`${i.nome || "Item"} removido do carrinho.`);
    titulo.tabIndex = -1;
    titulo.focus({ preventScroll: true });
    recotar(0);
  };

  const mudarQuantidade = (i, nova) => {
    const ref = refs.get(i.chave);
    nova = Math.max(1, Math.min(99, nova || 1));
    if (nova > ref.item.quantidade && ref.item.estoque != null && nova > ref.item.estoque) {
      avisar(ref.item.estoque > 0 ? `Só temos ${ref.item.estoque} unidade(s) em estoque.` : "Sem estoque no momento.");
      nova = Math.max(1, Math.min(nova, ref.item.estoque));
    }
    alterarQuantidade(i.chave, nova);
    ref.item = { ...ref.item, quantidade: nova, total_centavos: ref.item.preco_unit_centavos * nova };
    ref.input.value = nova;
    ref.menos.disabled = nova <= 1;
    ref.total.textContent = brl(ref.item.total_centavos);
    recotar();
  };

  const botaoRemover = (i) => h("button", { class: "botao-icone", type: "button", "aria-label": `Remover ${nomeComOpcao(i) || "item"}`,
    title: "Remover", onclick: () => remover(i) }, icone(ICONE_LIXEIRA));

  function linhaItem(i) {
    const erro = h("div", { class: "esgotado", hidden: !i.erro }, i.erro || "");
    if (!i.produto_id) {
      // precisa de ação: escolher opção ou produto temporariamente indisponível
      const linha = h("div", { class: "linha-item indisponivel" },
        h("div", { class: "foto-vazia", "aria-hidden": "true" }, i.icone || "📦"),
        h("div", {},
          h("a", { class: "nome", href: `/produto/${i.slug}` }, i.nome || "Produto"),
          erro,
          h("div", { class: "acoes" },
            h("a", { class: "botao secundario", href: `/produto/${i.slug}` }, i.erro === "Escolha uma opção do produto." ? "Escolher opção" : "Ver produto"),
            botaoRemover(i))),
        h("span", {}));
      refs.set(i.chave, { linha, erro, item: i });
      return linha;
    }
    const nome = nomeComOpcao(i);
    const total = h("b", { class: "total-item" }, brl(i.total_centavos));
    const menos = h("button", { type: "button", "aria-label": `Diminuir quantidade de ${nome}`, disabled: i.quantidade <= 1,
      onclick: () => mudarQuantidade(i, refs.get(i.chave).item.quantidade - 1) }, "−");
    const input = h("input", { type: "number", value: i.quantidade, min: 1, max: 99, "aria-label": `Quantidade de ${nome}`,
      onchange: (e) => mudarQuantidade(i, parseInt(e.target.value, 10)) });
    const mais = h("button", { type: "button", "aria-label": `Aumentar quantidade de ${nome}`,
      onclick: () => mudarQuantidade(i, refs.get(i.chave).item.quantidade + 1) }, "+");
    const linha = h("div", { class: "linha-item" },
      h("img", { src: imagemProduto(i, true), alt: "", width: 72, height: 72 }),
      h("div", {},
        h("a", { class: "nome", href: `/produto/${i.slug}` }, i.nome),
        i.variacao_nome ? h("div", {}, "Opção: ", h("b", {}, i.variacao_nome)) : null,
        h("div", { class: "parcelado" }, i.preco_ancora_unit_centavos > i.preco_unit_centavos
          ? [h("s", {}, h("span", { class: "sr" }, "De "), brl(i.preco_ancora_unit_centavos)), " "] : null, `${brl(i.preco_unit_centavos)} cada`),
        erro,
        h("div", { class: "acoes" }, h("div", { class: "quantidade" }, menos, input, mais), botaoRemover(i))),
      total);
    refs.set(i.chave, { linha, erro, total, input, menos, item: i });
    return linha;
  }

  const inputCep = h("input", { id: "carrinho-cep", type: "text", inputmode: "numeric", autocomplete: "postal-code", placeholder: "00000-000",
    value: (cotacao.frete && cotacao.frete.cep) || cep, oninput: (e) => (e.target.value = mascaraCep(e.target.value)) });
  const formCep = h("form", { class: "simulador", onsubmit: (e) => {
    e.preventDefault();
    cep = mascaraCep(inputCep.value);
    gravar("tipiti:cep", cep);
    recotar(0);
  } },
  h("label", { for: "carrinho-cep", class: "rotulo-simulador" }, "CEP de entrega"),
  h("div", { class: "linha-cep" }, inputCep, h("button", { class: "botao secundario", type: "submit" }, "Calcular frete")),
  linkNaoSeiCep());
  const topoResumo = h("div", {});

  // cupom: só aparece se o servidor souber cotar com cupom
  const suportaCupom = "cupom" in cotacao || "cupom_erro" in cotacao;
  const inputCupom = h("input", { id: "carrinho-cupom", type: "text", autocomplete: "off", autocapitalize: "characters", spellcheck: "false",
    maxlength: 40, value: cupom, "aria-describedby": "msg-cupom", oninput: () => { erroCupom = ""; msgCupom.textContent = ""; inputCupom.removeAttribute("aria-invalid"); } });
  const msgCupom = h("p", { class: "msg-erro", id: "msg-cupom", "aria-live": "polite" });
  const botaoCupom = h("button", { class: "botao secundario", type: "submit" }, "Aplicar");
  const detalhesCupom = h("details", { class: "cupom" },
    h("summary", {}, "🎟️ Tem cupom?"),
    h("form", { class: "form-cupom", onsubmit: (e) => {
      e.preventDefault();
      const codigo = inputCupom.value.trim().toUpperCase();
      if (!codigo) { erroCupom = "Digite o código do cupom."; desenharCupom(); inputCupom.focus(); return; }
      cupom = codigo;
      erroCupom = "";
      msgCupom.textContent = "";
      recotar(0);
    } },
    h("label", { for: "carrinho-cupom", class: "sr" }, "Código do cupom"),
    h("div", { class: "linha-cep" }, inputCupom, botaoCupom), msgCupom));
  const cupomAplicado = h("div", { class: "cupom-aplicado", "aria-live": "polite" });
  const blocoCupom = suportaCupom ? h("div", { class: "bloco-cupom" }, cupomAplicado, detalhesCupom) : null;

  function desenharCupom() {
    if (!suportaCupom) return;
    if (cotacao.cupom && cupom) {
      guardarCupom(cotacao.cupom.codigo);
      erroCupom = "";
      detalhesCupom.hidden = true;
      trocar(cupomAplicado, h("div", {},
        h("b", {}, `🎟️ Cupom ${cotacao.cupom.codigo} aplicado`),
        cotacao.cupom.descricao ? h("div", { class: "parcelado" }, cotacao.cupom.descricao) : null),
      h("button", { class: "link-botao", type: "button", "aria-label": `Remover cupom ${cotacao.cupom.codigo}`, onclick: () => {
        cupom = "";
        guardarCupom("");
        inputCupom.value = "";
        detalhesCupom.hidden = false;
        detalhesCupom.open = true;
        recotar(0);
        inputCupom.focus({ preventScroll: true });
      } }, "Remover"));
      cupomAplicado.hidden = false;
      return;
    }
    if (cupom && cotacao.cupom_erro) erroCupom = cotacao.cupom_erro;
    if (erroCupom) guardarCupom("");
    cupomAplicado.hidden = true;
    detalhesCupom.hidden = false;
    if (erroCupom) detalhesCupom.open = true;
    msgCupom.textContent = erroCupom;
    if (erroCupom) inputCupom.setAttribute("aria-invalid", "true"); else inputCupom.removeAttribute("aria-invalid");
  }
  const totais = h("div", { "aria-live": "polite" });
  const acoes = h("div", {});

  function desenharResumo() {
    const validos = cotacao.itens.filter((i) => i.produto_id);
    const textoZap = () => `Olá! Quero finalizar este pedido na Tipiti:\n${validos.map((i) => `• ${i.quantidade}× ${nomeComOpcao(i)} — ${brl(i.total_centavos)}`).join("\n")}\nSubtotal: ${brl(cotacao.subtotal_centavos)}${cotacao.cupom ? `\nCupom: ${cotacao.cupom.codigo}` : ""}${cotacao.frete ? `\nCEP: ${cotacao.frete.cep}` : ""}`;
    trocar(topoResumo, erroCep ? h("div", { class: "alerta" }, erroCep) : null);
    trocar(totais, blocoResumo(cotacao, { carrinho: true }));
    desenharCupom();
    trocar(acoes,
      !cotacao.valido ? h("div", { class: "alerta" }, "Ajuste os itens marcados em vermelho para continuar.") : null,
      h("button", { class: "botao grande", type: "button", disabled: !cotacao.valido, onclick: () => navegar("/checkout") }, "Finalizar compra"),
      botaoWhatsApp(textoZap, "Prefiro finalizar pelo WhatsApp", "botao whatsapp grande espaco-topo"),
      h("a", { href: "/", class: "link-continuar" }, "Continuar comprando"));
  }
  trocar(resumo, h("h2", {}, "Resumo"), topoResumo, formCep, blocoCupom, totais, acoes);
  desenharResumo();

  trocar(main, titulo,
    h("div", { class: "layout-carrinho" },
      h("div", { class: "painel" }, cotacao.itens.map(linhaItem)),
      resumo,
    ),
  );
}

const UFS = ["AM", "PA", "RR", "AP", "AC", "RO", "TO", "AL", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PB", "PE", "PI", "PR", "RJ", "RN", "RS", "SC", "SE", "SP"];
const ROTULOS_CHECKOUT = { nome: "Nome", email: "E-mail", telefone: "Celular", cpf: "CPF", cep: "CEP", endereco: "Rua", numero: "Número",
  bairro: "Bairro", cidade: "Cidade", uf: "UF", pagamento: "Pagamento", parcelas: "Parcelas", cupom: "Cupom" };
const OBRIGATORIOS_CHECKOUT = ["nome", "email", "telefone", "cpf", "cep", "endereco", "numero", "bairro", "cidade", "uf"];

function validarCampoCheckout(nome, valor) {
  const v = String(valor || "").trim();
  const d = v.replace(/\D/g, "");
  switch (nome) {
    case "nome": return v.length >= 3 ? "" : "Informe o nome completo.";
    case "email": return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v) ? "" : "Informe um e-mail válido.";
    case "telefone": return d.length === 10 || d.length === 11 ? "" : "Informe o celular com DDD (10 ou 11 dígitos).";
    case "cpf": return cpfValido(d) ? "" : "CPF inválido. Confira os números.";
    case "cep": return d.length === 8 ? "" : "O CEP tem 8 dígitos.";
    case "uf": return v ? "" : "Selecione o estado.";
    default: return v ? "" : "Preencha este campo.";
  }
}

/** "Faltam 3 campos: Nome, CPF, Número. Confira: E-mail." */
function textoErrosCheckout(erros, dados) {
  const nomes = Object.keys(erros).filter((n) => ROTULOS_CHECKOUT[n]);
  const faltam = nomes.filter((n) => !String(dados[n] || "").trim());
  const invalidos = nomes.filter((n) => !faltam.includes(n));
  const partes = [];
  if (faltam.length) partes.push(`${faltam.length === 1 ? "Falta 1 campo" : `Faltam ${faltam.length} campos`}: ${faltam.map((n) => ROTULOS_CHECKOUT[n]).join(", ")}`);
  if (invalidos.length) partes.push(`Confira: ${invalidos.map((n) => ROTULOS_CHECKOUT[n]).join(", ")}`);
  return partes.length ? `${partes.join(". ")}.` : "";
}

async function paginaCheckout(main) {
  const ativo = vigencia();
  document.title = "Finalizar compra | Tipiti";
  if (!estado.carrinho.length) return navegar("/carrinho", true);

  const rascunho = lerArmazenado("tipiti:checkout", {}, sessionStorage);
  const resumo = h("aside", { class: "painel resumo resumo-checkout" }, h("h2", {}, "Resumo do pedido"), h("div", { class: "carregando" }, "Calculando…"));
  const totalMovel = h("b", {}, "…");
  const conteudoMovel = h("div", {}, h("div", { class: "carregando" }, "Calculando…"));
  const resumoMovel = h("details", { class: "painel resumo-movel" },
    h("summary", {}, h("span", {}, "Resumo do pedido"), totalMovel), conteudoMovel);
  const totalConfirmar = h("p", { class: "total-confirmar", "aria-live": "polite" });
  const selParcelas = h("select", { id: "campo-parcelas", name: "parcelas", class: "campo-select", "aria-describedby": "erro-parcelas" });
  const blocoParcelas = h("div", { class: "campo", "data-campo": "parcelas", hidden: true },
    h("label", { for: "campo-parcelas" }, "Parcelas"), selParcelas, h("span", { class: "msg-erro", id: "erro-parcelas" }));
  const dicaCepFixa = h("span", {}, "Preencha o CEP e completamos o endereço. ");
  const dicaCep = h("span", { "aria-live": "polite" });
  const dicaCupom = h("span", { "aria-live": "polite" });
  const blocoCupom = h("div", { class: "grade-form bloco-cupom-checkout", hidden: true },
    campo("cupom", "Cupom de desconto (opcional)", { autocomplete: "off", autocapitalize: "characters", spellcheck: "false", maxlength: 40 }, "c6", dicaCupom));

  const form = h("form", { class: "painel", novalidate: true },
    h("fieldset", {}, h("legend", {}, "1. Seus dados"),
      h("div", { class: "grade-form" },
        campo("nome", "Nome completo", { autocomplete: "name", required: true }, "c6"),
        campo("email", "E-mail", { type: "email", inputmode: "email", autocomplete: "email", required: true }, "c3"),
        campo("telefone", "Celular com DDD", { type: "tel", autocomplete: "tel-national", inputmode: "numeric", placeholder: "(92) 90000-0000", required: true }, "c3"),
        campo("cpf", "CPF", { inputmode: "numeric", placeholder: "000.000.000-00", required: true }, "c3"))),
    h("fieldset", {}, h("legend", {}, "2. Endereço de entrega"),
      h("div", { class: "grade-form" },
        campo("cep", "CEP", { inputmode: "numeric", autocomplete: "postal-code", placeholder: "00000-000", required: true }, "c2",
          [dicaCepFixa, dicaCep]),
        h("div", { class: "c4 celula-link-cep" }, linkNaoSeiCep()),
        campo("endereco", "Rua / Avenida", { autocomplete: "address-line1", required: true }, "c4"),
        campo("numero", "Número", { required: true, inputmode: "numeric" }, "c2"),
        campo("complemento", "Complemento", { autocomplete: "address-line2" }, "c4"),
        campo("bairro", "Bairro", { required: true }, "c2"),
        campo("cidade", "Cidade", { autocomplete: "address-level2", required: true }, "c3"),
        h("div", { class: "campo c1", "data-campo": "uf" },
          h("label", { for: "campo-uf" }, "UF"),
          h("select", { id: "campo-uf", name: "uf", class: "campo-select", autocomplete: "address-level1", required: true, "aria-describedby": "erro-uf" },
            h("option", { value: "" }, "—"), UFS.map((u) => h("option", { value: u }, u))),
          h("span", { class: "msg-erro", id: "erro-uf" })))),
    h("fieldset", {}, h("legend", {}, "3. Pagamento"),
      h("div", { class: "opcoes-pagamento", "data-campo": "pagamento" },
        [["pix", "Pix", `${estado.loja.desconto_pix_pct}% de desconto · aprovação imediata`],
         ["cartao", "Cartão de crédito", `Até ${estado.loja.parcelas_max}x sem juros`],
         ["boleto", "Boleto bancário", "Compensação em até 2 dias úteis"]]
          .map(([v, t, s]) => h("label", { class: "opcao" },
            h("input", { type: "radio", name: "pagamento", value: v, checked: v === (rascunho.pagamento || "pix") }),
            h("span", {}, h("b", {}, t), h("small", {}, s)))),
        h("span", { class: "msg-erro" }),
        blocoParcelas)),
    blocoCupom,
    h("fieldset", { class: "aceites" },
      h("legend", { class: "sr" }, "Termos e autorizações"),
      h("div", { class: "campo", "data-campo": "aceite_termos" },
        h("label", { class: "aceite" },
          h("input", { type: "checkbox", name: "aceite_termos", id: "campo-aceite_termos", "aria-describedby": "erro-aceite_termos" }),
          h("span", {}, "Li e aceito os ", h("a", { href: "/termos", target: "_blank", rel: "noopener" }, "Termos de Uso"),
            " e a ", h("a", { href: "/privacidade", target: "_blank", rel: "noopener" }, "Política de Privacidade"), ".")),
        h("span", { class: "msg-erro", id: "erro-aceite_termos" })),
      h("label", { class: "aceite" },
        h("input", { type: "checkbox", name: "aceite_whatsapp" }),
        h("span", {}, "Quero receber pelo WhatsApp as atualizações do pedido e ofertas da Tipiti (opcional)."))),
    h("div", { class: "alerta", id: "erro-geral", role: "alert", hidden: true }),
    totalConfirmar,
    h("button", { class: "botao grande", type: "submit" }, "Confirmar pedido"),
    blocoConfianca("confianca-checkout"),
  );

  for (const [nome, valor] of Object.entries(rascunho)) {
    const el = form.elements[nome];
    if (el && nome !== "pagamento" && nome !== "parcelas") el.value = valor;
  }
  if (!form.elements.cep.value) form.elements.cep.value = lerArmazenado("tipiti:cep", "");
  if (!form.elements.cupom.value) form.elements.cupom.value = cupomGuardado();

  const mascaras = { cep: mascaraCep, cpf: mascaraCpf, telefone: mascaraTelefone };
  for (const [nome, fn] of Object.entries(mascaras)) {
    form.elements[nome].addEventListener("input", (e) => (e.target.value = fn(e.target.value)));
  }

  const dadosForm = () => Object.fromEntries(new FormData(form).entries());
  const erroGeral = $("#erro-geral", form);
  form.addEventListener("input", (e) => {
    gravar("tipiti:checkout", { ...dadosForm(), cpf: "", cupom: "" }, sessionStorage);
    const c = e.target.closest("[data-campo]");
    if (c && c.classList.contains("com-erro")) marcarErro(c, "");
    if (!form.querySelector(".com-erro")) erroGeral.hidden = true;
  });
  // valida ao sair do campo os que têm formato (só se a pessoa digitou algo)
  form.addEventListener("focusout", (e) => {
    const nome = e.target.name;
    if (!["email", "telefone", "cpf", "cep"].includes(nome) || !e.target.value.trim()) return;
    marcarErro(e.target.closest("[data-campo]"), validarCampoCheckout(nome, e.target.value));
  });

  let ultimaCotacao = null;
  let sequencia = 0;
  async function atualizarResumo() {
    const d = dadosForm();
    const cepValido = (d.cep || "").replace(/\D/g, "").length === 8;
    const n = ++sequencia;
    const cupom = (d.cupom || "").trim().toUpperCase();
    try {
      ultimaCotacao = await api("/api/carrinho/cotacao", { method: "POST",
        body: JSON.stringify({ itens: estado.carrinho, cep: cepValido ? d.cep : null, pagamento: d.pagamento,
          ...(cupom ? { cupom } : {}), ...(cpfValido(d.cpf) ? { cpf: d.cpf } : {}) }) });
    } catch (err) {
      if (!ativo() || n !== sequencia) return;
      trocar(resumo, h("h2", {}, "Resumo do pedido"), h("div", { class: "alerta" }, err.message));
      trocar(conteudoMovel, h("div", { class: "alerta" }, err.message));
      return;
    }
    if (!ativo() || n !== sequencia) return;
    const c = ultimaCotacao;
    if ("cupom" in c || "cupom_erro" in c) {
      blocoCupom.hidden = false;
      const campoCupom = form.querySelector('[data-campo="cupom"]');
      if (cupom && c.cupom_erro) { marcarErro(campoCupom, c.cupom_erro); dicaCupom.textContent = ""; guardarCupom(""); }
      else {
        marcarErro(campoCupom, "");
        dicaCupom.textContent = c.cupom ? `✔ Cupom ${c.cupom.codigo} aplicado${c.cupom.descricao ? `: ${c.cupom.descricao}` : ""}.` : "";
        if (c.cupom) guardarCupom(c.cupom.codigo);
      }
    }
    const conteudo = () => [
      c.itens.filter((i) => i.produto_id).map((i) => h("div", { class: "linha-total" },
        h("span", {}, `${i.quantidade}× ${nomeComOpcao(i)}`), h("span", {}, brl(i.total_centavos)))),
      h("hr", { class: "divisor" }),
      blocoResumo(c),
      !c.valido ? h("div", { class: "alerta" }, "Há itens indisponíveis. ", h("a", { href: "/carrinho" }, "Revise o carrinho.")) : null,
    ];
    trocar(resumo, h("h2", {}, "Resumo do pedido"), conteudo());
    trocar(conteudoMovel, conteudo());
    totalMovel.textContent = brl(c.total_centavos);
    blocoParcelas.hidden = d.pagamento !== "cartao";
    const atual = parseInt(selParcelas.value, 10) || 1;
    trocar(selParcelas, ...Array.from({ length: c.parcelas_max }, (_, k) => k + 1).map((n) =>
      h("option", { value: n, selected: n === Math.min(atual, c.parcelas_max) },
        n === 1 ? `1x de ${brl(c.total_centavos)} (à vista)` : `${n}x de ${brl(Math.ceil(c.total_centavos / n))} sem juros`)));
    trocar(totalConfirmar, "Total: ", h("b", {}, brl(c.total_centavos)), c.frete ? null : h("span", { class: "parcelado" }, " + frete (informe o CEP)"));
  }

  let ultimoCep = "";
  async function buscarCep() {
    const d = form.elements.cep.value.replace(/\D/g, "");
    if (d.length !== 8 || d === ultimoCep) return;
    ultimoCep = d;
    gravar("tipiti:cep", mascaraCep(d));
    atualizarResumo();
    dicaCepFixa.hidden = true;
    dicaCep.textContent = "Buscando o endereço…";
    const controle = new AbortController();
    const limite = setTimeout(() => controle.abort(), 8000);
    try {
      const resp = await fetch(`https://viacep.com.br/ws/${d}/json/`, { signal: controle.signal });
      if (!resp.ok) throw new Error("viacep");
      const e = await resp.json();
      if (!ativo() || form.elements.cep.value.replace(/\D/g, "") !== d) return;
      if (!e || e.erro) throw new Error("cep");
      if (e.logradouro) form.elements.endereco.value = e.logradouro;
      if (e.bairro) form.elements.bairro.value = e.bairro;
      if (e.localidade) form.elements.cidade.value = e.localidade;
      if (e.uf) form.elements.uf.value = e.uf;
      ["endereco", "bairro", "cidade", "uf"].forEach((n) => { if (form.elements[n].value) marcarErro(form.elements[n].closest("[data-campo]"), ""); });
      dicaCep.textContent = "Endereço preenchido — confira e informe o número.";
      gravar("tipiti:checkout", { ...dadosForm(), cpf: "", cupom: "" }, sessionStorage);
      if (document.activeElement === form.elements.cep || document.activeElement === document.body) form.elements.numero.focus();
    } catch (_) {
      if (ativo()) dicaCep.textContent = "Não encontramos o CEP — preencha o endereço.";
    } finally {
      clearTimeout(limite);
    }
  }
  form.elements.cep.addEventListener("change", buscarCep);
  form.elements.cep.addEventListener("keyup", () => { if (form.elements.cep.value.length === 9) buscarCep(); });
  form.querySelectorAll("input[name=pagamento]").forEach((r) => r.addEventListener("change", atualizarResumo));
  form.elements.cupom.addEventListener("change", () => {
    form.elements.cupom.value = form.elements.cupom.value.trim().toUpperCase();
    if (!form.elements.cupom.value) guardarCupom("");
    atualizarResumo();
  });
  // com o CPF válido, a cotação confere cupons de primeira compra
  let ultimoCpf = "";
  form.elements.cpf.addEventListener("input", () => {
    const d = form.elements.cpf.value.replace(/\D/g, "");
    if (d === ultimoCpf || !cpfValido(d)) return;
    ultimoCpf = d;
    if (form.elements.cupom.value.trim()) atualizarResumo();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const botao = form.querySelector("button[type=submit]");
    erroGeral.hidden = true;
    const dados = dadosForm();
    dados.cupom = (dados.cupom || "").trim().toUpperCase();
    if (!dados.cupom) delete dados.cupom;
    const erros = {};
    for (const nome of OBRIGATORIOS_CHECKOUT) {
      const msg = validarCampoCheckout(nome, dados[nome]);
      if (msg) erros[nome] = msg;
    }
    dados.aceite_termos = form.elements.aceite_termos.checked;
    dados.aceite_whatsapp = form.elements.aceite_whatsapp.checked;
    if (Object.keys(erros).length) {
      if (!dados.aceite_termos) erros.aceite_termos = "Para concluir, aceite os Termos de Uso e a Política de Privacidade.";
      mostrarErros(form, erros);
      erroGeral.textContent = textoErrosCheckout(erros, dados);
      erroGeral.hidden = false;
      return;
    }
    if (!dados.aceite_termos) {
      mostrarErros(form, { aceite_termos: "Para concluir, aceite os Termos de Uso e a Política de Privacidade." });
      erroGeral.textContent = "Falta aceitar os Termos de Uso e a Política de Privacidade.";
      erroGeral.hidden = false;
      return;
    }
    botao.disabled = true;
    botao.textContent = "Enviando pedido…";
    try {
      const pedido = await api("/api/pedidos", { method: "POST", body: JSON.stringify({ ...dados, itens: estado.carrinho }) });
      estado.carrinho = [];
      salvarCarrinho();
      try { sessionStorage.removeItem("tipiti:checkout"); } catch (_) { /* ignora */ }
      navegar(`/pedido/${pedido.codigo}`);
    } catch (err) {
      if (!ativo()) return;
      const campos = err.campos || {};
      mostrarErros(form, campos);
      const detalhe = campos.itens ? "" : textoErrosCheckout(campos, dados);
      trocar(erroGeral, err.message, detalhe ? ` ${detalhe}` : "",
        campos.itens ? [" ", h("a", { href: "/carrinho" }, "Revise o carrinho.")] : null);
      erroGeral.hidden = false;
      if (!Object.keys(campos).some((k) => form.querySelector(`[data-campo="${k}"]`))) erroGeral.scrollIntoView({ block: "center" });
      if (campos.itens) atualizarResumo();
      botao.disabled = false;
      botao.textContent = "Confirmar pedido";
    }
  });

  trocar(main, h("h1", {}, "Finalizar compra"), h("div", { class: "layout-carrinho layout-checkout" }, resumoMovel, form, resumo));
  atualizarResumo();
}
