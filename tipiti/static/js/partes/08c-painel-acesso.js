// ------------------------------------------------------------- painel: login, usuários, Minha conta e utilidades

/** "2026-10-20" -> "20/10/2026". */
function dataBrAdm(texto) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(texto || ""));
  return m ? `${m[3]}/${m[2]}/${m[1]}` : String(texto || "");
}

/** Data e hora de Manaus a partir do ISO "Z" ou do texto do banco ("2026-10-12 18:00:00", em UTC). */
function quandoAdm(texto) {
  if (!texto) return "";
  const iso = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(texto) ? `${texto.replace(" ", "T")}Z` : texto;
  return textoManaus(iso) || String(texto);
}

/** Link do WhatsApp: número só com dígitos (com ou sem o 55) e mensagem pronta. */
function zapAdm(numero, texto = "") {
  let d = String(numero || "").replace(/\D/g, "");
  if (d.length === 10 || d.length === 11) d = `55${d}`;
  return d ? `https://wa.me/${d}${texto ? `?text=${encodeURIComponent(texto)}` : ""}` : null;
}

function botaoZapAdm(href, rotulo) {
  return href ? h("a", { class: "botao whatsapp", href, target: "_blank", rel: "noopener noreferrer" },
    h("span", { "aria-hidden": "true" }, "💬"), ` ${rotulo}`) : null;
}

/** Telefone guardado só com dígitos (com ou sem 55) -> "(92) 99123-4567". */
function telefoneAdm(d) {
  const n = String(d || "").replace(/\D/g, "");
  return mascaraTelefone(n.length > 11 && n.startsWith("55") ? n.slice(2) : n);
}

/** Envia JSON para uma rota do painel e trata o 401 (sessão expirada) num lugar só. */
async function enviarAdmin(auth, url, metodo, corpo) {
  try {
    return await api(url, { method: metodo, headers: auth, body: corpo === undefined ? undefined : JSON.stringify(corpo) });
  } catch (err) {
    if (err.status === 401) sairDoPainel(true);
    throw err;
  }
}

/** Seletor de filtro de status ("Todos", …) que redesenha a seção. */
function filtroAdm(id, rotulo, opcoes, atual, aoMudar) {
  return h("div", { class: "filtro-admin" },
    h("label", { for: id }, rotulo),
    h("select", { id, class: "campo-select", onchange: (e) => aoMudar(e.target.value) },
      opcoes.map(([valor, texto]) => h("option", { value: valor, selected: valor === atual }, texto))));
}

/** Baixa um JSON como arquivo (Blob + a[download]). */
function baixarJsonAdm(nomeArquivo, dados) {
  const blob = new Blob([JSON.stringify(dados, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = h("a", { href: url, download: nomeArquivo, hidden: true });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

/** Senha aleatória legível (sem 0/O, 1/l), para a senha inicial de um usuário. */
function senhaAleatoriaAdm(tamanho = 14) {
  const letras = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789";
  const bytes = new Uint32Array(tamanho);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => letras[b % letras.length]).join("");
}

/** Mensagem de erro do servidor no formulário: campos marcados + alerta com o texto. */
function erroFormAdm(form, alerta, err) {
  if (err.status === 401) return;
  mostrarErros(form, err.campos);
  const extras = Object.entries(err.campos || {}).filter(([k, m]) => typeof m === "string" && !form.querySelector(`[data-campo="${k}"]`)).map(([, m]) => m);
  alerta.replaceChildren(err.message, ...extras.map((m) => h("div", {}, m)));
  alerta.hidden = false;
}

// -- login

async function postarLogin(corpo) {
  let resp;
  try {
    resp = await fetch("/api/admin/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) });
  } catch (_) {
    throw new Error("Sem conexão com a loja. Verifique a internet e tente novamente.");
  }
  let dados = null;
  try { dados = await resp.json(); } catch (_) { /* corpo vazio */ }
  return { ok: resp.ok, status: resp.status, dados: dados || {} };
}

function telaLoginAdmin(main) {
  const aviso = avisoLogin;
  avisoLogin = null;
  const alerta = h("div", { class: "alerta", role: "alert", hidden: !aviso }, aviso || "");
  const mostrar = (texto) => { alerta.textContent = texto; alerta.hidden = !texto; };
  let credenciais = null;

  const entrar = (sessao, nome) => {
    gravar(CHAVE_ADMIN, sessao, sessionStorage);
    tentativaLogin = null;
    avisar(nome ? `Olá, ${nome.split(" ")[0]}!` : "Bem-vindo ao painel.");
    rotear({ navegacao: true });
  };

  const formSenha = h("form", { class: "pilha-form", novalidate: true },
    campo("login", "E-mail", { type: "email", autocomplete: "username", inputmode: "email", required: true, autocapitalize: "none", spellcheck: "false" }, "c6"),
    campo("senha", "Senha", { type: "password", autocomplete: "current-password", required: true }, "c6"),
    h("button", { class: "botao grande", type: "submit" }, "Entrar"));
  const formCodigo = h("form", { class: "pilha-form", novalidate: true, hidden: true },
    h("p", {}, "Abra o aplicativo autenticador (Google Authenticator, Authy…) e digite o código de 6 números da Tipiti."),
    campo("codigo_2fa", "Código de verificação", { inputmode: "numeric", autocomplete: "one-time-code", maxlength: 6, pattern: "[0-9]*", placeholder: "123456" }, "c6"),
    h("button", { class: "botao grande", type: "submit" }, "Confirmar"),
    h("button", { class: "link-botao", type: "button", onclick: () => { formCodigo.hidden = true; formSenha.hidden = false; mostrar(""); formSenha.elements.senha.focus(); } }, "Voltar"));
  const inputToken = h("input", { id: "token-admin", type: "password", autocomplete: "off", spellcheck: "false" });
  const formToken = h("form", { class: "pilha-form", novalidate: true },
    h("p", { class: "parcelado" }, "Use só se ainda não houver usuários ou se ninguém conseguir entrar. O token fica na configuração do servidor (TIPITI_ADMIN_TOKEN)."),
    h("div", { class: "campo" }, h("label", { for: "token-admin" }, "Token de emergência"), inputToken),
    h("button", { class: "botao secundario", type: "submit" }, "Entrar com o token"));

  const tentar = async (corpo, botao) => {
    botao.disabled = true;
    try {
      const r = await postarLogin(corpo);
      if (r.ok && r.dados.sessao) return entrar(r.dados.sessao, r.dados.usuario && r.dados.usuario.nome);
      if (r.dados.precisa_2fa) {
        credenciais = { login: corpo.login, senha: corpo.senha };
        formSenha.hidden = true;
        formCodigo.hidden = false;
        mostrar(corpo.codigo_2fa ? (r.dados.erro || "Código inválido.") : "");
        formCodigo.elements.codigo_2fa.value = "";
        formCodigo.elements.codigo_2fa.focus();
        return;
      }
      mostrar(r.status === 429 ? "Muitas tentativas seguidas. Aguarde alguns minutos e tente de novo." : r.dados.erro || "Não foi possível entrar.");
    } catch (err) { mostrar(err.message); } finally { botao.disabled = false; }
  };

  formSenha.addEventListener("submit", (e) => {
    e.preventDefault();
    const f = formSenha.elements;
    const erros = {};
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(f.login.value.trim())) erros.login = "Digite o e-mail do seu usuário.";
    if (!f.senha.value) erros.senha = "Digite a senha.";
    mostrarErros(formSenha, erros);
    if (Object.keys(erros).length) return;
    tentar({ login: f.login.value.trim(), senha: f.senha.value }, formSenha.querySelector("button[type=submit]"));
  });
  formCodigo.addEventListener("submit", (e) => {
    e.preventDefault();
    const codigo = formCodigo.elements.codigo_2fa.value.replace(/\D/g, "");
    if (codigo.length !== 6) return mostrarErros(formCodigo, { codigo_2fa: "O código tem 6 números." });
    mostrarErros(formCodigo, {});
    tentar({ ...credenciais, codigo_2fa: codigo }, formCodigo.querySelector("button[type=submit]"));
  });
  formToken.addEventListener("submit", (e) => {
    e.preventDefault();
    const token = inputToken.value.trim();
    if (!token) return mostrar("Digite o token de emergência.");
    gravar(CHAVE_ADMIN, token, sessionStorage);
    tentativaLogin = "token";
    rotear({ navegacao: true });
  });

  trocar(main, h("div", { class: "painel login-admin" },
    h("h1", {}, "Painel da loja"),
    h("p", { class: "parcelado" }, "Entre com o seu e-mail e senha."),
    alerta, formSenha, formCodigo,
    h("details", { class: "login-token" }, h("summary", {}, "Entrar com token de emergência"), formToken)));
  if (aviso) formSenha.elements.login.focus();
}

// -- avisos no topo do painel: primeiro usuário, acesso pelo token

function formularioUsuario(auth, { primeiro = false, aoCriar } = {}) {
  const alerta = h("div", { class: "alerta", hidden: true, role: "alert" });
  const senha = h("input", { id: `campo-senha-novo${primeiro ? "-dono" : ""}`, name: "senha", type: "text", autocomplete: "new-password", minlength: 10, spellcheck: "false",
    "aria-describedby": `dica-senha-novo${primeiro ? "-dono" : ""} erro-senha-novo${primeiro ? "-dono" : ""}` });
  const sufixo = primeiro ? "-dono" : "";
  const form = h("form", { class: primeiro ? "painel destaque-primeiro" : "painel", novalidate: true, "aria-labelledby": `titulo-usuario${sufixo}` },
    h("h2", { id: `titulo-usuario${sufixo}` }, primeiro ? "Crie o primeiro usuário (dono)" : "Novo usuário"),
    primeiro ? h("p", {}, "Você entrou com o token de emergência. Crie agora o seu usuário de dono: depois disso você entra com e-mail e senha, e o token fica guardado só para emergências.") : null,
    h("div", { class: "grade-form" },
      campo(`nome${sufixo}`, "Nome", { name: "nome", maxlength: 80, autocomplete: "name" }, "c3"),
      campo(`login${sufixo}`, "E-mail (login)", { name: "login", type: "email", maxlength: 254, autocomplete: "email", autocapitalize: "none", spellcheck: "false" }, "c3"),
      primeiro ? null : h("div", { class: "campo c2", "data-campo": "papel" },
        h("label", { for: "campo-papel-novo" }, "Papel"),
        h("select", { id: "campo-papel-novo", name: "papel", class: "campo-select" },
          h("option", { value: "operador" }, "Operador (pedidos, produtos, separação)"), h("option", { value: "dono" }, "Dono (tudo)")),
        h("span", { class: "msg-erro" })),
      h("div", { class: `campo ${primeiro ? "c6" : "c4"}`, "data-campo": "senha" },
        h("label", { for: `campo-senha-novo${sufixo}` }, primeiro ? "Senha (mínimo 10 caracteres)" : "Senha inicial (mínimo 10 caracteres)"),
        h("div", { class: "linha-campo" }, senha,
          h("button", { class: "botao secundario", type: "button", onclick: () => { senha.value = senhaAleatoriaAdm(); senha.focus(); } }, "Gerar")),
        h("span", { class: "dica-campo", id: `dica-senha-novo${sufixo}` }, primeiro ? "Guarde-a num lugar seguro." : "Passe a senha para a pessoa por um canal seguro; ela pode trocar em “Minha conta”."),
        h("span", { class: "msg-erro", id: `erro-senha-novo${sufixo}` }))),
    alerta,
    h("button", { class: "botao grande espaco-topo", type: "submit" }, primeiro ? "Criar meu usuário de dono" : "Criar usuário"));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    alerta.hidden = true;
    const f = form.elements;
    const dados = { nome: f.nome.value.trim(), login: f.login.value.trim().toLowerCase(), papel: primeiro ? "dono" : f.papel.value, senha: senha.value };
    const erros = {};
    if (dados.nome.length < 2) erros[`nome${sufixo}`] = "Informe o nome.";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(dados.login)) erros[`login${sufixo}`] = "Use um e-mail como login.";
    if (dados.senha.length < 10) erros.senha = "A senha precisa ter pelo menos 10 caracteres.";
    if (Object.keys(erros).length) return mostrarErros(form, erros);
    const botao = form.querySelector("button[type=submit]");
    botao.disabled = true;
    try {
      const criado = await enviarAdmin(auth, "/api/admin/usuarios", "POST", dados);
      mostrarErros(form, {});
      if (aoCriar) await aoCriar(criado, dados);
    } catch (err) {
      const campos = {};
      for (const [k, m] of Object.entries(err.campos || {})) campos[k === "nome" || k === "login" ? `${k}${sufixo}` : k] = m;
      erroFormAdm(form, alerta, { ...err, message: err.message, status: err.status, campos });
    } finally { botao.disabled = false; }
  });
  return form;
}

function avisosDeAcesso(auth) {
  const eu = painelEu || {};
  if (eu.via_token && eu.primeiro_usuario) {
    return formularioUsuario(auth, { primeiro: true, aoCriar: async (criado, dados) => {
      const r = await postarLogin({ login: dados.login, senha: dados.senha });
      if (r.ok && r.dados.sessao) {
        gravar(CHAVE_ADMIN, r.dados.sessao, sessionStorage);
        avisar("Usuário dono criado ✔ Você já entrou com ele.");
      } else avisar("Usuário dono criado ✔ Saia e entre com o e-mail e a senha.");
      rotear();
    } });
  }
  if (eu.via_token) {
    return h("div", { class: "info-box espaco-baixo" }, h("b", {}, "Acesso de emergência. "),
      "Você entrou com o token. No dia a dia, entre com o seu e-mail e senha (cada pessoa com o seu usuário).");
  }
  return null;
}

// -- Minha conta: senha e verificação em duas etapas

function formTrocarSenha(auth) {
  const alerta = h("div", { class: "alerta", hidden: true, role: "alert" });
  const form = h("form", { class: "painel", novalidate: true, "aria-labelledby": "titulo-senha" },
    h("h2", { id: "titulo-senha" }, "Trocar a senha"),
    h("div", { class: "grade-form" },
      campo("atual", "Senha atual", { type: "password", autocomplete: "current-password" }, "c6"),
      campo("nova", "Nova senha (mínimo 10 caracteres)", { type: "password", autocomplete: "new-password", minlength: 10 }, "c3"),
      campo("nova2", "Repita a nova senha", { type: "password", autocomplete: "new-password" }, "c3")),
    h("p", { class: "parcelado" }, "Ao trocar a senha, as suas outras sessões abertas (outros aparelhos) são encerradas."),
    alerta,
    h("button", { class: "botao", type: "submit" }, "Trocar senha"));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    alerta.hidden = true;
    const f = form.elements;
    const erros = {};
    if (!f.atual.value) erros.atual = "Digite a senha atual.";
    if (f.nova.value.length < 10) erros.nova = "A nova senha precisa ter pelo menos 10 caracteres.";
    else if (f.nova.value !== f.nova2.value) erros.nova2 = "As duas senhas não são iguais.";
    if (Object.keys(erros).length) return mostrarErros(form, erros);
    try {
      await enviarAdmin(auth, "/api/admin/eu/senha", "POST", { atual: f.atual.value, nova: f.nova.value });
      form.reset();
      mostrarErros(form, {});
      avisar("Senha trocada ✔");
    } catch (err) { erroFormAdm(form, alerta, err); }
  });
  return form;
}

/** Segredo do 2FA em grupos de 4 letras, para digitar no aplicativo. */
const segredoEmGrupos = (s) => String(s || "").replace(/(.{4})/g, "$1 ").trim();

function secaoDoisFatores(auth) {
  const secao = h("section", { class: "painel", "aria-labelledby": "titulo-2fa" });
  const titulo = h("h2", { id: "titulo-2fa" }, "Verificação em duas etapas");
  const desenhar = () => {
    if (painelEu.totp_ativo) {
      const alerta = h("div", { class: "alerta", hidden: true, role: "alert" });
      const form = h("form", { novalidate: true },
        h("div", { class: "grade-form" },
          campo("senha_2fa", "Sua senha", { name: "senha", type: "password", autocomplete: "current-password" }, "c3"),
          campo("codigo_desativar", "Código do aplicativo", { name: "codigo", inputmode: "numeric", autocomplete: "one-time-code", maxlength: 6 }, "c3")),
        alerta,
        h("button", { class: "botao secundario espaco-topo", type: "submit" }, "Desativar a verificação"));
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        alerta.hidden = true;
        if (!confirm("Desativar a verificação em duas etapas? Sua conta fica protegida só pela senha.")) return;
        try {
          await enviarAdmin(auth, "/api/admin/eu/2fa/desativar", "POST", { senha: form.elements.senha.value, codigo: form.elements.codigo.value.replace(/\D/g, "") });
          painelEu.totp_ativo = false;
          avisar("Verificação em duas etapas desativada.");
          desenhar();
        } catch (err) {
          const campos = {};
          if (err.campos && err.campos.senha) campos.senha_2fa = err.campos.senha;
          if (err.campos && err.campos.codigo) campos.codigo_desativar = err.campos.codigo;
          erroFormAdm(form, alerta, { message: err.message, status: err.status, campos });
        }
      });
      trocar(secao, titulo, h("p", { class: "estado-2fa ativo" }, "✅ Ativa: além da senha, o login pede o código do aplicativo."),
        h("p", { class: "parcelado" }, "Trocou de celular? Desative aqui com o celular antigo e ative de novo no novo. Perdeu o celular? Peça ao dono para desativar em “Usuários”."),
        form);
      return;
    }
    trocar(secao, titulo,
      h("p", { class: "estado-2fa" }, "Desativada. Ative para que, além da senha, o login peça um código que muda a cada 30 segundos no seu celular."),
      h("button", { class: "botao", type: "button", onclick: async (e) => {
        e.target.disabled = true;
        try { mostrarAtivacao(await enviarAdmin(auth, "/api/admin/eu/2fa/iniciar", "POST", {})); }
        catch (err) { e.target.disabled = false; if (err.status !== 401) avisar(err.message); }
      } }, "Ativar verificação em duas etapas"));
  };
  const mostrarAtivacao = (r) => {
    const alerta = h("div", { class: "alerta", hidden: true, role: "alert" });
    const form = h("form", { novalidate: true },
      h("div", { class: "grade-form" }, campo("codigo_ativar", "Código de 6 números que aparece no aplicativo", { name: "codigo", inputmode: "numeric", autocomplete: "one-time-code", maxlength: 6, placeholder: "123456" }, "c3")),
      alerta,
      h("div", { class: "compra" }, h("button", { class: "botao", type: "submit" }, "Confirmar e ativar"),
        h("button", { class: "botao secundario", type: "button", onclick: () => desenhar() }, "Cancelar")));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      alerta.hidden = true;
      const codigo = form.elements.codigo.value.replace(/\D/g, "");
      if (codigo.length !== 6) return mostrarErros(form, { codigo_ativar: "O código tem 6 números." });
      try {
        await enviarAdmin(auth, "/api/admin/eu/2fa/confirmar", "POST", { codigo });
        painelEu.totp_ativo = true;
        avisar("Verificação em duas etapas ativada ✔");
        desenhar();
      } catch (err) {
        erroFormAdm(form, alerta, { message: err.message, status: err.status, campos: err.campos && err.campos.codigo ? { codigo_ativar: err.campos.codigo } : {} });
      }
    });
    // o QR vem do nosso servidor como SVG; vira uma imagem (data:), que não executa nada
    const qr = r.qr_svg ? h("img", { class: "qr-2fa", src: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(r.qr_svg)}`,
      alt: "QR Code para cadastrar a Tipiti no aplicativo autenticador", width: 220, height: 220 }) : null;
    trocar(secao, titulo,
      h("ol", { class: "passos-2fa" },
        h("li", {}, "Instale um aplicativo autenticador no celular (Google Authenticator, Microsoft Authenticator, Authy…)."),
        h("li", {}, "No aplicativo, toque em “+” e leia o QR Code abaixo. ",
          r.otpauth_url ? h("a", { href: r.otpauth_url }, "Está no próprio celular? Toque aqui para abrir no aplicativo.") : null),
        h("li", {}, "Ou digite a chave manualmente: ", h("code", { class: "segredo-2fa" }, segredoEmGrupos(r.segredo)), " ",
          botaoCopiar(r.segredo, "Copiar chave", "Chave copiada ✔")),
        h("li", {}, "Digite o código de 6 números que o aplicativo mostrar.")),
      qr, form);
    form.elements.codigo.focus();
  };
  desenhar();
  return secao;
}

async function painelMinhaConta(auth) {
  const eu = painelEu || {};
  const dados = h("section", { class: "painel" }, h("h2", {}, "Minha conta"),
    h("dl", { class: "dados-conta" },
      h("dt", {}, "Nome"), h("dd", {}, eu.nome || "—"),
      eu.login ? [h("dt", {}, "Login"), h("dd", {}, eu.login)] : null,
      h("dt", {}, "Papel"), h("dd", {}, NOME_PAPEL[eu.papel] || eu.papel,
        eu.papel === "operador" ? h("div", { class: "parcelado" }, "Cuida de pedidos, separação, produtos (sem custo), avaliações, avise-me, carrinhos, encomendas e barcos.") : null)));
  if (eu.via_token) {
    return h("div", { class: "pilha" }, dados, h("p", { class: "info-box" },
      "Você entrou com o token de emergência. Senha e verificação em duas etapas são de cada usuário: entre com o seu e-mail e senha para alterá-las."));
  }
  return h("div", { class: "pilha grade-conta" }, dados, formTrocarSenha(auth), secaoDoisFatores(auth));
}

// -- Usuários (só o dono)

function edicaoUsuario(auth, u) {
  const alerta = h("div", { class: "alerta", hidden: true, role: "alert" });
  const eu = painelEu && painelEu.login === u.login;
  const form = h("form", { class: "form-usuario", novalidate: true },
    h("div", { class: "grade-form" },
      campo(`nome-u${u.id}`, "Nome", { name: "nome", maxlength: 80, value: u.nome }, "c3"),
      h("div", { class: "campo c3", "data-campo": "papel" },
        h("label", { for: `papel-u${u.id}` }, "Papel"),
        h("select", { id: `papel-u${u.id}`, name: "papel", class: "campo-select" },
          h("option", { value: "operador", selected: u.papel === "operador" }, "Operador"), h("option", { value: "dono", selected: u.papel === "dono" }, "Dono")),
        h("span", { class: "msg-erro" })),
      h("label", { class: "c6 caixa" }, h("input", { type: "checkbox", name: "ativo", checked: u.ativo }), " Usuário ativo (pode entrar no painel)")),
    alerta,
    h("button", { class: "botao", type: "submit" }, "Salvar"));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    alerta.hidden = true;
    const f = form.elements;
    if (!f.ativo.checked && u.ativo && !confirm(`Desativar ${u.nome}? A pessoa sai do painel na hora.`)) return;
    if (eu && f.papel.value !== "dono" && !confirm("Você vai deixar de ser dono e perder o acesso às seções do dono. Continuar?")) return;
    try {
      await enviarAdmin(auth, `/api/admin/usuarios/${u.id}`, "PATCH", { nome: f.nome.value.trim(), papel: f.papel.value, ativo: f.ativo.checked });
      avisar("Usuário atualizado ✔");
      if (eu) return rotear();
      atualizarAba();
    } catch (err) {
      const campos = err.campos && err.campos.nome ? { ...err.campos, [`nome-u${u.id}`]: err.campos.nome } : err.campos;
      erroFormAdm(form, alerta, { message: err.message, status: err.status, campos });
    }
  });
  const alertaSenha = h("div", { class: "alerta", hidden: true, role: "alert" });
  const inputSenha = h("input", { id: `senha-u${u.id}`, name: "nova_senha", type: "text", autocomplete: "new-password", spellcheck: "false", minlength: 10 });
  const formSenha = h("form", { class: "form-usuario", novalidate: true },
    h("div", { class: "campo", "data-campo": "nova_senha" }, h("label", { for: `senha-u${u.id}` }, "Nova senha (mínimo 10 caracteres)"),
      h("div", { class: "linha-campo" }, inputSenha, h("button", { class: "botao secundario", type: "button", onclick: () => { inputSenha.value = senhaAleatoriaAdm(); } }, "Gerar")),
      h("span", { class: "msg-erro" })),
    alertaSenha,
    h("button", { class: "botao secundario", type: "submit" }, "Definir nova senha"));
  formSenha.addEventListener("submit", async (e) => {
    e.preventDefault();
    alertaSenha.hidden = true;
    if (inputSenha.value.length < 10) return mostrarErros(formSenha, { nova_senha: "A senha precisa ter pelo menos 10 caracteres." });
    if (!confirm(`Trocar a senha de ${u.nome}? As sessões abertas dela são encerradas.`)) return;
    try {
      await enviarAdmin(auth, `/api/admin/usuarios/${u.id}`, "PATCH", { nova_senha: inputSenha.value });
      avisar("Senha redefinida ✔ Passe a nova senha para a pessoa.");
      mostrarErros(formSenha, {});
    } catch (err) { erroFormAdm(formSenha, alertaSenha, err); }
  });
  return h("details", { class: "detalhes-admin" }, h("summary", {}, "Editar, redefinir senha"),
    form, h("hr", { class: "divisor" }), formSenha,
    u.totp_ativo ? [h("hr", { class: "divisor" }), h("button", { class: "botao secundario", type: "button", onclick: async () => {
      if (!confirm(`Desativar a verificação em duas etapas de ${u.nome}? Use quando a pessoa perdeu o celular. Ela entra só com a senha e pode ativar de novo.`)) return;
      try {
        await enviarAdmin(auth, `/api/admin/usuarios/${u.id}`, "PATCH", { desativar_2fa: true });
        avisar("Verificação em duas etapas desativada para este usuário.");
        if (eu) return rotear();
        atualizarAba();
      } catch (err) { if (err.status !== 401) avisar(err.message); }
    } }, "Desativar a verificação em duas etapas")] : null);
}

async function painelUsuarios(auth) {
  const usuarios = await api("/api/admin/usuarios", { headers: auth });
  const lista = Array.isArray(usuarios) ? usuarios : [];
  return h("div", { class: "pilha" },
    h("p", { class: "parcelado" }, "Cada pessoa entra com o próprio usuário. O ", h("b", {}, "dono"), " vê tudo; o ", h("b", {}, "operador"),
      " cuida de pedidos, separação, produtos (sem ver custos), avaliações, avise-me, carrinhos, encomendas e barcos."),
    lista.length ? h("div", { class: "rolagem" }, h("table", { class: "tabela-admin tabela-cartoes tabela-usuarios" },
      h("thead", {}, h("tr", {}, ["Usuário", "Papel", "Situação", "Verificação", "Último acesso", ""].map((t) => h("th", {}, t)))),
      h("tbody", {}, lista.map((u) => h("tr", {},
        celula("Usuário", {}, h("b", {}, u.nome), h("div", { class: "parcelado" }, u.login)),
        celula("Papel", {}, NOME_PAPEL[u.papel] || u.papel),
        celula("Situação", {}, h("span", { class: `etiqueta ${u.ativo ? "ativo" : "inativo"}` }, u.ativo ? "Ativo" : "Desativado")),
        celula("Verificação", {}, u.totp_ativo ? "✅ Duas etapas" : h("span", { class: "parcelado" }, "Só senha")),
        celula("Último acesso", {}, u.ultimo_acesso ? quandoAdm(u.ultimo_acesso) : h("span", { class: "parcelado" }, "nunca")),
        celula("", { class: "celula-acao" }, edicaoUsuario(auth, u))))))) : h("p", { class: "painel" }, "Nenhum usuário ainda."),
    formularioUsuario(auth, { aoCriar: async () => { avisar("Usuário criado ✔"); atualizarAba(); } }));
}
