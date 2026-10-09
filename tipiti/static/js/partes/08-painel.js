// ------------------------------------------------------------- administração

const STATUS_PEDIDO = { aguardando_pagamento: "Aguardando pagamento", pago: "Pago", enviado: "Enviado", entregue: "Entregue", cancelado: "Cancelado" };

let tokenRecusado = false;

function sairDoPainel(recusado = false) {
  try { sessionStorage.removeItem(CHAVE_ADMIN); } catch (_) { /* ignora */ }
  tokenRecusado = recusado;
  navegar("/admin", true);
}

/** Mostra o login se não houver token; senão devolve o cabeçalho de autorização. */
function autenticacaoAdmin(main) {
  const token = lerArmazenado(CHAVE_ADMIN, "", sessionStorage);
  if (token) return { Authorization: `Bearer ${token}` };
  const recusado = tokenRecusado;
  tokenRecusado = false;
  const input = h("input", { id: "token-admin", type: "password", autocomplete: "current-password", "aria-describedby": recusado ? "erro-token" : null,
    "aria-invalid": recusado ? "true" : null });
  trocar(main, h("div", { class: "painel login-admin" },
    h("h1", {}, "Painel da loja"),
    h("form", { onsubmit: (e) => { e.preventDefault(); gravar(CHAVE_ADMIN, input.value.trim(), sessionStorage); rotear(); } },
      h("div", { class: "campo" + (recusado ? " com-erro" : "") },
        h("label", { for: "token-admin" }, "Token de acesso"), input,
        recusado ? h("span", { class: "msg-erro", id: "erro-token", role: "alert" }, "Token incorreto. Confira e tente de novo.") : null),
      h("button", { class: "botao grande espaco-topo" }, "Entrar"))));
  if (recusado) input.focus();
  return null;
}

function cabecalhoAdmin(abaAtual) {
  const abas = [["pedidos", "Pedidos"], ["produtos", "Produtos"], ["novo", "+ Novo produto"], ["calculadora", "Calculadora"], ["configuracoes", "Configurações"]];
  return [
    h("div", { class: "secao-cabecalho" }, h("h1", {}, "Painel da loja"), h("button", { class: "link-botao", type: "button", onclick: () => sairDoPainel() }, "Sair")),
    h("div", { class: "abas", role: "tablist" }, abas.map(([id, rotulo]) =>
      h("button", { class: "botao secundario", role: "tab", type: "button", "aria-selected": String(abaAtual === id),
        onclick: () => { gravar("tipiti:admin-aba", id, sessionStorage); navegar("/admin"); } }, rotulo))),
  ];
}

async function comTratamento(conteudo, ativo, fn) {
  try { await fn(); } catch (err) {
    if (!ativo()) return;
    if (err.status === 401) return sairDoPainel(true);
    trocar(conteudo, h("div", { class: "alerta" }, err.message));
  }
}

async function paginaAdmin(main) {
  const ativo = vigencia();
  document.title = "Painel | Tipiti";
  const auth = autenticacaoAdmin(main);
  if (!auth) return;
  const aba = lerArmazenado("tipiti:admin-aba", "pedidos", sessionStorage);
  const conteudo = h("div", {}, h("div", { class: "carregando" }, "Carregando…"));
  trocar(main, cabecalhoAdmin(aba), conteudo);
  await comTratamento(conteudo, ativo, async () => {
    let novo;
    if (aba === "novo") novo = formularioNovoProduto(auth);
    else if (aba === "produtos") novo = await listaProdutosAdmin(auth);
    else if (aba === "calculadora") {
      const aj = await api("/api/admin/ajustes", { headers: auth });
      novo = h("div", { class: "painel" }, h("h2", {}, "Calculadora de preço do importado"),
        h("p", { class: "parcelado" }, "Descubra o custo real de cada unidade no Brasil e o preço de venda para a margem que você quer."),
        calculadora(auth, aj));
    } else if (aba === "configuracoes") novo = await formularioAjustes(auth);
    else novo = await painelPedidos(auth);
    if (ativo()) trocar(conteudo, novo);
  });
}

function cartaoNumero(rotulo, valor, detalhe) {
  return h("div", { class: "cartao-numero" }, h("small", {}, rotulo), h("b", {}, valor), detalhe ? h("small", {}, detalhe) : null);
}

/** Célula com rótulo para a tabela virar cartão no celular. */
const celula = (rotulo, attrs, ...filhos) => h("td", { "data-rotulo": rotulo, ...attrs }, h("div", { class: "celula-conteudo" }, ...filhos));

async function painelPedidos(auth) {
  const [pedidos, resumo] = await Promise.all([api("/api/admin/pedidos", { headers: auth }), api("/api/admin/resumo", { headers: auth })]);
  const nomeItem = (i) => `${i.quantidade}× ${i.nome}${i.variacao_nome ? ` (${i.variacao_nome})` : ""}`;
  return h("div", {},
    h("div", { class: "cartoes-numeros" },
      cartaoNumero("Pedidos", resumo.pedidos, "sem contar cancelados"),
      cartaoNumero("Faturamento", brl(resumo.faturamento_centavos), "com frete"),
      cartaoNumero("Lucro estimado", brl(resumo.lucro_centavos),
        resumo.pedidos_sem_custo ? `${resumo.pedidos_sem_custo} pedido(s) sem custo cadastrado` : "produtos − custo, sem o frete"),
      cartaoNumero("Ticket médio", brl(resumo.ticket_medio_centavos))),
    resumo.estoque_baixo.length ? h("div", { class: "info-box espaco-baixo" },
      h("b", {}, "⚠️ Estoque baixo: "),
      resumo.estoque_baixo.map((p, k) => [k ? ", " : "", h("a", { href: `/admin/produto/${p.slug}` }, p.nome), ` (${p.estoque})`])) : null,
    pedidos.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-pedidos" },
      h("thead", {}, h("tr", {}, ["Pedido", "Cliente", "Entrega", "Itens", "Total", "Lucro", "Status"].map((t) => h("th", {}, t)))),
      h("tbody", {}, pedidos.map((p) => {
        const primeiroNome = p.cliente.nome.split(" ")[0];
        const zap = `https://wa.me/55${p.cliente.telefone}?text=${encodeURIComponent(`Olá, ${primeiroNome}! Aqui é da Tipiti, sobre o seu pedido ${p.codigo}.`)}`;
        // com `proximos_status`, só oferece o status atual e os próximos permitidos
        const possiveis = Array.isArray(p.proximos_status)
          ? [p.status, ...p.proximos_status.filter((s) => s !== p.status)] : Object.keys(STATUS_PEDIDO);
        const travado = p.status === "cancelado" || possiveis.length < 2;
        return h("tr", {},
          celula("Pedido", {}, h("b", {}, p.codigo), h("div", { class: "parcelado" }, p.criado_em)),
          celula("Cliente", {}, p.cliente.nome, h("div", { class: "parcelado" }, p.cliente.email),
            h("div", { class: "parcelado" }, mascaraTelefone(p.cliente.telefone))),
          celula("Entrega", {}, `${p.entrega.endereco}, ${p.entrega.numero} ${p.entrega.complemento}`,
            h("div", { class: "parcelado" }, `${p.entrega.bairro} · ${p.entrega.cidade}/${p.entrega.uf} · ${mascaraCep(p.entrega.cep)}`),
            h("div", { class: "parcelado" }, p.zona_frete)),
          celula("Itens", {}, p.itens.map((i) => h("div", {}, nomeItem(i)))),
          celula("Total", {}, brl(p.total_centavos), h("div", { class: "parcelado" }, `${p.pagamento_nome}${p.parcelas > 1 ? ` ${p.parcelas}x` : ""}`)),
          celula("Lucro", {}, p.lucro_centavos === null ? h("span", { class: "parcelado" }, "sem custo") : brl(p.lucro_centavos)),
          celula("", { class: "celula-status" },
            h("select", { class: "campo-select", disabled: travado, "aria-label": `Status do pedido ${p.codigo}`,
              onchange: async (e) => {
                if (e.target.value === "cancelado" && !confirm("Cancelar o pedido e devolver os itens ao estoque?")) { e.target.value = p.status; return; }
                try { await api(`/api/admin/pedidos/${p.codigo}`, { method: "PATCH", headers: auth, body: JSON.stringify({ status: e.target.value }) }); avisar("Status atualizado ✔"); rotear(); }
                catch (err) { if (err.status === 401) return sairDoPainel(true); avisar(err.message); e.target.value = p.status; }
              } }, possiveis.map((v) => h("option", { value: v, selected: v === p.status }, STATUS_PEDIDO[v] || v))),
            h("a", { class: "botao whatsapp", href: zap, target: "_blank", rel: "noopener" }, h("span", { "aria-hidden": "true" }, "💬"), ` WhatsApp de ${primeiroNome}`)));
      }))))
      : h("p", {}, "Nenhum pedido ainda."));
}

async function listaProdutosAdmin(auth) {
  const produtos = await api("/api/admin/produtos", { headers: auth });
  const margem = (p) => (p.custo_centavos ? `${Math.round(((p.preco_centavos - p.custo_centavos) / p.preco_centavos) * 100)}%` : "—");
  return h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-produtos" },
    h("thead", {}, h("tr", {}, h("th", {}, "Produto"), h("th", {}, "Preço"), h("th", {}, "Custo"),
      h("th", {}, "Margem bruta", h("small", { class: "dica-coluna" }, "lucro ÷ preço")), h("th", {}, "Estoque"), h("th", {}, "Situação"), h("th", {}, h("span", { class: "sr" }, "Ações")))),
    h("tbody", {}, produtos.map((p) => h("tr", {},
      celula("", { class: "celula-produto" }, h("div", { class: "produto-admin" }, h("img", { src: imagemProduto(p, true), alt: "", class: "miniatura", width: 48, height: 48, loading: "lazy" }),
        h("div", {}, h("a", { href: `/admin/produto/${p.slug}` }, p.nome),
          h("div", { class: "parcelado" }, p.categoria.nome, p.tem_variacoes ? " · com opções" : "")))),
      celula("Preço", {}, brl(p.preco_centavos)),
      celula("Custo", {}, p.custo_centavos ? brl(p.custo_centavos) : h("span", { class: "parcelado" }, "—")),
      celula("Margem bruta (lucro ÷ preço)", {}, margem(p)),
      celula("Estoque", { class: p.estoque <= 3 ? "esgotado" : "" }, p.estoque),
      celula("Situação", {}, p.ativo ? "No ar" : "Fora do ar", p.destaque ? " · ⭐" : ""),
      celula("", { class: "celula-acao" }, h("a", { class: "botao secundario", href: `/admin/produto/${p.slug}` }, "Editar")))))));
}

async function paginaEditorProduto(main, slug) {
  const ativo = vigencia();
  document.title = "Editar produto | Tipiti";
  const auth = autenticacaoAdmin(main);
  if (!auth) return;
  const conteudo = h("div", {}, h("div", { class: "carregando" }, "Carregando…"));
  trocar(main, cabecalhoAdmin("produtos"), conteudo);
  await comTratamento(conteudo, ativo, async () => {
    const [p, aj] = await Promise.all([api(`/api/admin/produtos/${slug}`, { headers: auth }), api("/api/admin/ajustes", { headers: auth })]);
    if (!ativo()) return;
    document.title = `${p.nome} | Painel Tipiti`;
    trocar(conteudo,
      h("p", {}, h("a", { href: "/admin" }, "← Voltar aos produtos"), " · ", h("a", { href: `/produto/${p.slug}`, target: "_blank", rel: "noopener" }, "Ver na loja ↗")),
      h("div", { class: "editor" },
        secaoDadosProduto(auth, p),
        h("div", {},
          secaoFotos(auth, p),
          secaoVariacoes(auth, p),
          h("section", { class: "painel" }, h("h2", {}, "Calculadora de preço"),
            h("p", { class: "parcelado" }, "Calcule o custo real deste produto e aplique o preço sugerido."),
            calculadora(auth, aj, { precoAtual: p.preco_centavos, aoAplicar: async (preco, custo) => {
              try {
                await api(`/api/admin/produtos/${p.slug}`, { method: "PATCH", headers: auth, body: JSON.stringify({ preco_centavos: preco, custo_centavos: custo }) });
                avisar("Preço e custo aplicados ✔");
                rotear();
              } catch (err) { avisar(err.message); }
            } })))));
  });
}

function seletorCategoria(atual) {
  return h("div", { class: "campo c3", "data-campo": "categoria" },
    h("label", { for: "campo-categoria" }, "Categoria"),
    h("select", { id: "campo-categoria", name: "categoria", class: "campo-select", "aria-describedby": "erro-categoria" },
      h("option", { value: "" }, "Escolha…"), estado.categorias.map((c) => h("option", { value: c.slug, selected: c.slug === atual }, `${c.icone} ${c.nome}`))),
    h("span", { class: "msg-erro", id: "erro-categoria" }));
}

function camposPreco(p = {}) {
  return [
    campo("preco_centavos", "Preço de venda (R$)", { inputmode: "decimal", placeholder: "49,90", value: textoReais(p.preco_centavos) }, "c2"),
    campo("preco_de_centavos", "Preço antigo (riscado, opcional)", { inputmode: "decimal", placeholder: "69,90", value: textoReais(p.preco_de_centavos) }, "c2"),
    campo("custo_centavos", "Custo por unidade (R$, só você vê)", { inputmode: "decimal", placeholder: "22,50", value: textoReais(p.custo_centavos) }, "c2"),
  ];
}

function valoresPreco(f) {
  const dados = { preco_centavos: reais(f.preco_centavos.value), preco_de_centavos: reais(f.preco_de_centavos.value), custo_centavos: reais(f.custo_centavos.value) };
  const erros = {};
  for (const [k, v] of Object.entries(dados)) if (Number.isNaN(v)) erros[k] = "Valor inválido. Use o formato 49,90.";
  if (dados.preco_centavos === null) erros.preco_centavos = "Informe o preço.";
  return [dados, erros];
}

function secaoDadosProduto(auth, p) {
  const form = h("form", { class: "painel", novalidate: true },
    h("h2", {}, "Dados do produto"),
    h("div", { class: "grade-form" },
      campo("nome", "Nome", { maxlength: 120, value: p.nome }, "c6"),
      seletorCategoria(p.categoria.slug),
      campo("icone", "Emoji (se não houver foto)", { maxlength: 8, value: p.icone }, "c3"),
      camposPreco(p),
      campo("estoque", p.tem_variacoes ? "Estoque (soma das opções)" : "Estoque (unidades)",
        { type: "number", min: 0, value: p.estoque, disabled: p.tem_variacoes }, "c2"),
      h("div", { class: "campo c6", "data-campo": "descricao" },
        h("label", { for: "campo-descricao" }, "Descrição"),
        h("textarea", { id: "campo-descricao", name: "descricao", rows: 5, maxlength: 2000, class: "campo-texto", "aria-describedby": "erro-descricao" }),
        h("span", { class: "msg-erro", id: "erro-descricao" })),
      h("label", { class: "c3 caixa" }, h("input", { type: "checkbox", name: "ativo", checked: p.ativo }), " Produto no ar"),
      h("label", { class: "c3 caixa" }, h("input", { type: "checkbox", name: "destaque", checked: p.destaque }), " Destaque na página inicial")),
    h("div", { class: "alerta", hidden: true }),
    h("button", { class: "botao grande espaco-topo", type: "submit" }, "Salvar dados"));
  form.elements.descricao.value = p.descricao || "";
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = form.elements;
    const alerta = $(".alerta", form);
    alerta.hidden = true;
    const [precos, erros] = valoresPreco(f);
    if (Object.keys(erros).length) return mostrarErros(form, erros);
    const dados = { nome: f.nome.value, categoria: f.categoria.value, icone: f.icone.value, descricao: f.descricao.value,
      ativo: f.ativo.checked, destaque: f.destaque.checked, ...precos };
    if (!p.tem_variacoes) dados.estoque = parseInt(f.estoque.value, 10);
    try {
      await api(`/api/admin/produtos/${p.slug}`, { method: "PATCH", headers: auth, body: JSON.stringify(dados) });
      mostrarErros(form, {});
      avisar("Produto salvo ✔");
    } catch (err) {
      mostrarErros(form, err.campos);
      alerta.textContent = err.message;
      alerta.hidden = false;
    }
  });
  return form;
}

// -- fotos: reduzidas no navegador antes do envio (menos dados no 4G e no servidor)

function lerArquivoBase64(arquivo) {
  return new Promise((resolver, rejeitar) => {
    const leitor = new FileReader();
    leitor.onload = () => resolver(String(leitor.result).split(",")[1] || "");
    leitor.onerror = () => rejeitar(new Error("Não foi possível ler o arquivo."));
    leitor.readAsDataURL(arquivo);
  });
}

function abrirImagem(arquivo) {
  const comImg = () => new Promise((resolver, rejeitar) => {
    const url = URL.createObjectURL(arquivo);
    const img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); resolver(img); };
    img.onerror = () => { URL.revokeObjectURL(url); rejeitar(new Error(`Não foi possível abrir “${arquivo.name}”. Use JPG, PNG ou WEBP.`)); };
    img.src = url;
  });
  return window.createImageBitmap ? createImageBitmap(arquivo).catch(comImg) : comImg();
}

const canvasParaBlob = (canvas, tipo, qualidade) => new Promise((resolver) => canvas.toBlob(resolver, tipo, qualidade));

/** Reduz para no máximo `maximo` px no maior lado; WEBP 0,82 (JPEG se o navegador não gerar WEBP). */
async function reduzirImagem(fonte, maximo) {
  const largura = fonte.naturalWidth || fonte.width;
  const altura = fonte.naturalHeight || fonte.height;
  const escala = Math.min(1, maximo / Math.max(largura, altura));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(largura * escala));
  canvas.height = Math.max(1, Math.round(altura * escala));
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff";  // PNG transparente vira fundo branco (o JPEG não tem transparência)
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(fonte, 0, 0, canvas.width, canvas.height);
  let blob = await canvasParaBlob(canvas, "image/webp", 0.82);
  if (!blob || blob.type !== "image/webp") blob = await canvasParaBlob(canvas, "image/jpeg", 0.82);
  if (!blob) throw new Error("Não foi possível processar a foto.");
  return blob;
}

async function enviarFoto(auth, slug, arquivo) {
  const fonte = await abrirImagem(arquivo);
  let principal, miniatura;
  try {
    principal = await reduzirImagem(fonte, 1200);
    miniatura = await reduzirImagem(fonte, 400);
  } finally {
    if (fonte.close) fonte.close();
  }
  if (principal.size > 3 * 1024 * 1024) throw new Error(`“${arquivo.name}” passa de 3 MB mesmo depois de reduzida.`);
  const [dados, mini] = await Promise.all([lerArquivoBase64(principal), lerArquivoBase64(miniatura)]);
  return api(`/api/admin/produtos/${slug}/foto`, { method: "POST", headers: auth, body: JSON.stringify({ dados, miniatura: mini }) });
}

function secaoFotos(auth, produto) {
  const secao = h("section", { class: "painel" });
  const desenhar = (p) => {
    const input = h("input", { type: "file", accept: "image/jpeg,image/png,image/webp", multiple: true, class: "sr",
      onchange: async (e) => {
        const arquivos = [...e.target.files];
        let atual = p;
        let enviadas = 0;
        for (const [k, arquivo] of arquivos.entries()) {
          avisar(`Enviando foto ${k + 1} de ${arquivos.length}…`);
          try { atual = await enviarFoto(auth, p.slug, arquivo); enviadas++; } catch (err) {
            if (err.status === 401) return sairDoPainel(true);
            avisar(err.message);
            break;
          }
        }
        desenhar(atual);
        if (enviadas === arquivos.length) avisar("Fotos atualizadas ✔");
      } });
    const acao = async (metodo, url) => {
      try { desenhar(await api(url, { method: metodo, headers: auth })); } catch (err) { avisar(err.message); }
    };
    trocar(secao,
      h("h2", {}, "Fotos"),
      h("p", { class: "parcelado" }, "A primeira é a capa. JPG, PNG ou WEBP; reduzimos para 1200 px antes de enviar. Até 8 fotos. Fotos quadradas ficam melhores."),
      h("div", { class: "galeria-admin" },
        p.fotos.map((f, k) => h("figure", {},
          h("img", { src: f.miniatura || f.url, alt: `Foto ${k + 1}`, width: 120, height: 120, loading: "lazy" }),
          k === 0 ? h("span", { class: "selo" }, "Capa") : null,
          h("figcaption", {},
            k > 0 ? h("button", { class: "link-botao", type: "button", onclick: () => acao("POST", `/api/admin/produtos/${p.slug}/fotos/${f.id}/capa`) }, "Usar como capa") : null,
            h("button", { class: "link-botao", type: "button", onclick: () => confirm("Remover esta foto?") && acao("DELETE", `/api/admin/produtos/${p.slug}/fotos/${f.id}`) }, "Remover")))),
        p.fotos.length < 8 ? h("label", { class: "adicionar-foto" }, input, h("span", {}, "＋"), "Adicionar fotos") : null));
  };
  desenhar(produto);
  return secao;
}

function secaoVariacoes(auth, produto) {
  const secao = h("section", { class: "painel" });
  let linhas = produto.variacoes.filter((v) => v.ativo).map((v) => ({ ...v }));
  const desenhar = () => {
    const corpo = linhas.map((v, k) => h("tr", { "data-campo": `variacao_${k}` },
      celula("Opção", {}, h("input", { type: "text", value: v.nome, placeholder: "Ex.: Preto / 220 V", "aria-label": `Nome da opção ${k + 1}`, oninput: (e) => (v.nome = e.target.value) })),
      celula("Código (SKU)", {}, h("input", { type: "text", value: v.sku || "", placeholder: "opcional", "aria-label": `Código (SKU) da opção ${k + 1}`, oninput: (e) => (v.sku = e.target.value) })),
      celula("Preço próprio (R$)", {}, h("input", { type: "text", inputmode: "decimal", value: v.preco_texto ?? textoReais(v.preco_centavos), placeholder: "igual ao produto",
        "aria-label": `Preço próprio da opção ${k + 1}`, oninput: (e) => (v.preco_texto = e.target.value) })),
      celula("Estoque", {}, h("input", { type: "number", min: 0, value: v.estoque ?? 0, "aria-label": `Estoque da opção ${k + 1}`, oninput: (e) => (v.estoque = parseInt(e.target.value, 10) || 0) })),
      celula("", { class: "celula-acao" }, h("button", { class: "botao-icone", type: "button", "aria-label": `Remover opção ${v.nome || k + 1}`, title: "Remover",
        onclick: () => { linhas.splice(k, 1); desenhar(); } }, icone(ICONE_LIXEIRA)))));
    const erro = h("div", { class: "alerta", hidden: true });
    trocar(secao,
      h("h2", {}, "Opções (cor, voltagem, tamanho)"),
      h("p", { class: "parcelado" }, "Cada opção tem estoque próprio e o cliente escolhe na página do produto. Para combinar, use nomes como “Preto / 220 V”. Deixe o preço vazio para usar o preço do produto."),
      linhas.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-variacoes tabela-cartoes" },
        h("thead", {}, h("tr", {}, ["Opção", "Código (SKU)", "Preço próprio (R$)", "Estoque", ""].map((t) => h("th", {}, t)))),
        h("tbody", {}, corpo))) : h("p", {}, "Este produto não tem opções: o estoque é controlado direto nos dados do produto."),
      erro,
      h("div", { class: "compra" },
        h("button", { class: "botao secundario", type: "button", onclick: () => { linhas.push({ nome: "", estoque: 0 }); desenhar(); } }, "+ Adicionar opção"),
        h("button", { class: "botao", type: "button", onclick: async () => {
          const lista = linhas.map((v) => {
            const preco = v.preco_texto !== undefined ? reais(v.preco_texto) : v.preco_centavos ?? null;
            return { id: v.id, nome: v.nome, sku: v.sku || "", preco_centavos: Number.isNaN(preco) ? -1 : preco, estoque: v.estoque ?? 0 };
          });
          try {
            const p = await api(`/api/admin/produtos/${produto.slug}/variacoes`, { method: "PUT", headers: auth, body: JSON.stringify({ variacoes: lista }) });
            avisar("Opções salvas ✔");
            rotear();  // atualiza estoque total nos dados do produto
            return p;
          } catch (err) {
            erro.replaceChildren(err.message, ...Object.entries(err.campos || {}).map(([k, m]) => h("div", {}, `Linha ${Number(k.split("_")[1]) + 1}: ${m}`)));
            erro.hidden = false;
          }
        } }, "Salvar opções")));
  };
  desenhar();
  return secao;
}

/** Campos da calculadora em que o ponto é sempre decimal (câmbio e percentuais). */
const CALC_PONTO_DECIMAL = new Set(["cambio", "quantidade", "impostos_pct", "taxa_pagamento_pct", "margem_pct"]);
const CALC_CAMPOS = ["custo_unitario", "cambio", "quantidade", "frete_lote", "impostos_pct", "outros_lote", "embalagem_unidade", "taxa_pagamento_pct", "margem_pct"];

function calculadora(auth, aj, { precoAtual = null, aoAplicar = null } = {}) {
  const cambios = { USD: aj.cambio_usd, CNY: aj.cambio_cny, BRL: "1" };
  const resultado = h("div", { class: "calc-resultado", "aria-live": "polite" });
  const form = h("form", { class: "grade-form", novalidate: true, onsubmit: (e) => e.preventDefault() },
    h("div", { class: "campo c2" }, h("label", { for: "calc-moeda" }, "Moeda do fornecedor"),
      h("select", { id: "calc-moeda", name: "moeda", class: "campo-select" },
        h("option", { value: "USD" }, "Dólar (US$)"), h("option", { value: "CNY" }, "Yuan (¥)"), h("option", { value: "BRL" }, "Real (R$)"))),
    campo("custo_unitario", "Preço por unidade no fornecedor", { inputmode: "decimal", placeholder: "3,20" }, "c2"),
    campo("cambio", "Câmbio (R$ por 1 unidade da moeda)", { inputmode: "decimal", value: cambios.USD }, "c2"),
    campo("quantidade", "Unidades no lote", { type: "number", min: 1, value: 100 }, "c2"),
    campo("frete_lote", "Frete internacional do lote (R$)", { inputmode: "decimal", placeholder: "800,00" }, "c2"),
    campo("impostos_pct", "Impostos e taxas de importação (%)", { inputmode: "decimal", value: aj.impostos_pct }, "c2"),
    campo("outros_lote", "Outros custos do lote (R$)", { inputmode: "decimal", placeholder: "despachante, armazenagem…" }, "c2"),
    campo("embalagem_unidade", "Embalagem por unidade (R$)", { inputmode: "decimal", placeholder: "1,50" }, "c2"),
    campo("taxa_pagamento_pct", "Taxa do meio de pagamento (%)", { inputmode: "decimal", value: aj.taxa_pagamento_pct }, "c2"),
    campo("margem_pct", "Margem de lucro desejada (%)", { inputmode: "decimal", value: aj.margem_pct }, "c6"));
  form.elements.moeda.addEventListener("change", (e) => {
    form.elements.cambio.value = cambios[e.target.value];
    form.elements.cambio.disabled = e.target.value === "BRL";
  });
  let espera;
  let sequencia = 0;
  const calcular = async () => {
    const f = form.elements;
    if (!f.custo_unitario.value.trim()) {
      trocar(resultado, h("p", { class: "parcelado" }, "Preencha o preço por unidade para ver o resultado."));
      return;
    }
    const corpo = { moeda: f.moeda.value, preco_centavos: precoAtual };
    const erros = {};
    for (const nome of CALC_CAMPOS) {
      if (f[nome].disabled) continue;
      const n = lerNumero(f[nome].value, { pontoDecimal: CALC_PONTO_DECIMAL.has(nome) });
      if (Number.isNaN(n)) erros[nome] = "Número inválido. Use, por exemplo, 0,765 ou 1.250,00.";
      corpo[nome] = n === null || Number.isNaN(n) ? "" : String(n);
    }
    if (Object.keys(erros).length) {
      mostrarErros(form, erros, false);
      trocar(resultado, h("div", { class: "alerta" }, "Corrija os campos marcados."));
      return;
    }
    const n = ++sequencia;
    try {
      const r = await api("/api/admin/calculadora", { method: "POST", headers: auth, body: JSON.stringify(corpo) });
      if (n !== sequencia) return;
      mostrarErros(form, {}, false);
      const linha = (rotulo, valor, classe = "") => h("div", { class: `linha-total ${classe}` }, h("span", {}, rotulo), h("span", {}, valor));
      const analise = (titulo, a) => h("div", { class: "calc-cartao" }, h("small", {}, titulo), h("b", {}, brl(a.preco_centavos)),
        h("small", {}, `Lucro ${brl(a.lucro_centavos)} por unidade · margem ${String(a.margem_pct).replace(".", ",")}%`));
      trocar(resultado,
        h("div", { class: "calc-colunas" },
          h("div", {},
            h("h3", {}, "Custo por unidade no Brasil"),
            linha("Produto", brl(r.custo.produto_centavos)), linha("Frete internacional", brl(r.custo.frete_centavos)),
            linha("Impostos e taxas", brl(r.custo.impostos_centavos)), linha("Outros custos", brl(r.custo.outros_centavos)),
            linha("Embalagem", brl(r.custo.embalagem_centavos)), linha("Custo total", brl(r.custo.total_centavos), "total")),
          h("div", {},
            analise("Preço sugerido", r.sugerido),
            r.atual ? analise("Com o preço atual", r.atual) : null,
            r.atual && r.atual.lucro_centavos < 0 ? h("div", { class: "alerta" }, "Com o preço atual você vende no prejuízo.") : null,
            aoAplicar ? h("button", { class: "botao grande", type: "button",
              onclick: () => aoAplicar(r.sugerido.preco_centavos, r.custo.total_centavos) },
              `Aplicar preço ${brl(r.sugerido.preco_centavos)} e custo ${brl(r.custo.total_centavos)}`) : null)));
    } catch (err) {
      if (n !== sequencia) return;
      mostrarErros(form, err.campos, false);
      trocar(resultado, h("div", { class: "alerta" }, err.message));
    }
  };
  form.addEventListener("input", () => { clearTimeout(espera); espera = setTimeout(calcular, 300); });
  form.addEventListener("change", () => { clearTimeout(espera); espera = setTimeout(calcular, 50); });
  calcular();
  return h("div", { class: "calculadora" }, form, resultado);
}

async function formularioAjustes(auth) {
  const aj = await api("/api/admin/ajustes", { headers: auth });
  const form = h("form", { class: "painel", novalidate: true },
    h("h2", {}, "WhatsApp da loja"),
    h("p", { class: "parcelado" }, "Com o número preenchido, aparecem o botão flutuante de atendimento e as opções “Pedir pelo WhatsApp” no produto, no carrinho e na confirmação do pedido."),
    h("div", { class: "grade-form" },
      campo("whatsapp", "Número com DDD", { type: "tel", inputmode: "numeric", placeholder: "(92) 99123-4567",
        value: aj.whatsapp ? mascaraTelefone(aj.whatsapp.slice(2)) : "" }, "c2"),
      campo("whatsapp_mensagem", "Mensagem inicial do botão de atendimento", { maxlength: 300, value: aj.whatsapp_mensagem }, "c4")),
    h("h2", { class: "espaco-topo-grande" }, "Pagamento por Pix"),
    h("div", { class: "grade-form" },
      campo("chave_pix", "Chave Pix", { maxlength: 140, autocomplete: "off", placeholder: "CNPJ, e-mail, telefone ou chave aleatória", value: aj.chave_pix ?? "" }, "c6",
        "Aparece para o cliente na confirmação do pedido, com o valor e o botão “Copiar chave Pix”. Deixe vazio para mandar as instruções pelo WhatsApp.")),
    h("h2", { class: "espaco-topo-grande" }, "Padrões da calculadora"),
    h("div", { class: "grade-form" },
      campo("cambio_usd", "Câmbio do dólar (R$)", { inputmode: "decimal", value: aj.cambio_usd }, "c2"),
      campo("cambio_cny", "Câmbio do yuan (R$)", { inputmode: "decimal", value: aj.cambio_cny }, "c2"),
      campo("impostos_pct", "Impostos e taxas de importação (%)", { inputmode: "decimal", value: aj.impostos_pct }, "c2"),
      campo("taxa_pagamento_pct", "Taxa do meio de pagamento (%)", { inputmode: "decimal", value: aj.taxa_pagamento_pct }, "c2"),
      campo("margem_pct", "Margem desejada (%)", { inputmode: "decimal", value: aj.margem_pct }, "c2")),
    h("button", { class: "botao grande espaco-topo", type: "submit" }, "Salvar configurações"));
  form.elements.whatsapp.addEventListener("input", (e) => (e.target.value = mascaraTelefone(e.target.value)));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const dados = Object.fromEntries(new FormData(form).entries());
    for (const nome of ["cambio_usd", "cambio_cny", "impostos_pct", "taxa_pagamento_pct", "margem_pct"]) {
      const n = lerNumero(dados[nome], { pontoDecimal: true });
      if (n !== null && !Number.isNaN(n)) dados[nome] = String(n);  // inválido segue como está e o servidor aponta o erro
    }
    try {
      const salvo = await api("/api/admin/ajustes", { method: "PUT", headers: auth, body: JSON.stringify(dados) });
      mostrarErros(form, {});
      estado.loja.whatsapp = salvo.whatsapp;
      estado.loja.whatsapp_mensagem = salvo.whatsapp_mensagem;
      if (typeof salvo.chave_pix === "string") estado.loja.chave_pix = salvo.chave_pix;
      atualizarWhatsAppFlutuante();
      avisar("Configurações salvas ✔");
    } catch (err) {
      if (err.status === 401) return sairDoPainel(true);
      mostrarErros(form, err.campos);
      avisar(err.message);
    }
  });
  return form;
}

function formularioNovoProduto(auth) {
  const previa = h("div", { class: "galeria-admin" });
  let urlsPrevia = [];
  const inputFoto = h("input", { type: "file", name: "foto", id: "campo-foto", accept: "image/jpeg,image/png,image/webp", multiple: true,
    onchange: (e) => {
      urlsPrevia.forEach((u) => URL.revokeObjectURL(u));
      urlsPrevia = [...e.target.files].map((a) => URL.createObjectURL(a));
      trocar(previa, urlsPrevia.map((u, k) => h("figure", {}, h("img", { src: u, alt: `Prévia da foto ${k + 1}`, width: 120, height: 120 }))));
    } });
  const form = h("form", { class: "painel", novalidate: true },
    h("h2", {}, "Cadastrar produto"),
    h("p", { class: "parcelado" }, "Preencha os dados do produto que você importou. Preços em reais (ex.: 49,90). Depois de cadastrar você pode adicionar opções como cor e voltagem."),
    h("div", { class: "grade-form" },
      campo("nome", "Nome do produto", { required: true, maxlength: 120, placeholder: "Ex.: Fone Bluetooth com estojo" }, "c6"),
      seletorCategoria(""),
      campo("icone", "Emoji (se não houver foto)", { maxlength: 8, placeholder: "📦" }, "c3"),
      camposPreco(),
      campo("estoque", "Estoque (unidades)", { type: "number", min: 0, value: 0, required: true }, "c2"),
      h("div", { class: "campo c6", "data-campo": "descricao" },
        h("label", { for: "campo-descricao" }, "Descrição"),
        h("textarea", { id: "campo-descricao", name: "descricao", rows: 4, maxlength: 2000, class: "campo-texto", "aria-describedby": "erro-descricao",
          placeholder: "Principais características, medidas, voltagem, o que vem na caixa…" }),
        h("span", { class: "msg-erro", id: "erro-descricao" })),
      h("div", { class: "campo c6", "data-campo": "foto" },
        h("label", { for: "campo-foto" }, "Fotos (JPG, PNG ou WEBP; a primeira é a capa — reduzimos antes de enviar)"), inputFoto, previa, h("span", { class: "msg-erro" })),
      h("label", { class: "c6 caixa" }, h("input", { type: "checkbox", name: "destaque" }), " Mostrar nos destaques da página inicial"),
    ),
    h("div", { class: "alerta", hidden: true, id: "erro-novo" }),
    h("button", { class: "botao grande espaco-topo", type: "submit" }, "Cadastrar produto"),
  );
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = form.elements;
    const erro = $("#erro-novo", form);
    const botao = form.querySelector("button[type=submit]");
    erro.hidden = true;
    const [precos, errosPreco] = valoresPreco(f);
    if (Object.keys(errosPreco).length) return mostrarErros(form, errosPreco);
    botao.disabled = true;
    try {
      const produto = await api("/api/admin/produtos", { method: "POST", headers: auth, body: JSON.stringify({
        nome: f.nome.value, categoria: f.categoria.value, icone: f.icone.value || "📦", descricao: f.descricao.value,
        estoque: parseInt(f.estoque.value, 10), destaque: f.destaque.checked, ...precos }) });
      for (const arquivo of inputFoto.files) {
        try { await enviarFoto(auth, produto.slug, arquivo); }
        catch (err) { avisar(`Produto criado, mas uma foto falhou: ${err.message}`); break; }
      }
      urlsPrevia.forEach((u) => URL.revokeObjectURL(u));
      avisar("Produto cadastrado ✔");
      navegar(`/admin/produto/${produto.slug}`);
    } catch (err) {
      if (err.status === 401) return sairDoPainel(true);
      mostrarErros(form, err.campos);
      erro.textContent = err.message;
      erro.hidden = false;
    } finally {
      botao.disabled = false;
    }
  });
  return form;
}
