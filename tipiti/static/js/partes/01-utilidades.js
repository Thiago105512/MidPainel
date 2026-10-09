/* Tipiti — loja virtual. JavaScript puro, sem dependências. */
"use strict";

const estado = { loja: null, categorias: [], carrinho: [] };
const CHAVE_CARRINHO = "tipiti:carrinho";
const CHAVE_ADMIN = "tipiti:admin";
const POR_PAGINA = 24;

// ------------------------------------------------------------- utilidades

const brl = (centavos) => (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const $ = (sel, raiz = document) => raiz.querySelector(sel);
const reduzMovimento = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Geração da navegação atual: cada chamada de rotear() cria uma nova. */
let geracaoNavegacao = 0;
/** Geração em que o <main> recebeu conteúdo pela última vez (para o esqueleto de carregamento). */
let geracaoRenderizada = -1;

/**
 * Chame no início da página, antes de qualquer await. Devolve `ativo()`, que diz se a página
 * ainda é a atual — respostas atrasadas de uma página anterior não podem sobrescrever a nova.
 */
function vigencia() {
  const g = geracaoNavegacao;
  return () => g === geracaoNavegacao;
}

/** Cria elementos sem innerHTML (evita injeção de HTML). */
function h(tag, attrs, ...filhos) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v;
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  for (const f of filhos.flat(Infinity)) {
    if (f === null || f === undefined || f === false) continue;
    el.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return el;
}

/** Ícone SVG simples (traços), sem innerHTML. */
function icone(d, rotulo = null) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  for (const [k, v] of Object.entries({ viewBox: "0 0 24 24", width: 22, height: 22, fill: "none", stroke: "currentColor",
    "stroke-width": 2, "stroke-linecap": "round", "stroke-linejoin": "round", focusable: "false" })) svg.setAttribute(k, v);
  if (rotulo) { svg.setAttribute("role", "img"); svg.setAttribute("aria-label", rotulo); } else svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", d);
  svg.append(path);
  return svg;
}
const ICONE_LIXEIRA = "M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14M10 11v6M14 11v6";

/** replaceChildren que aceita listas aninhadas e ignora vazios. */
function trocar(el, ...filhos) {
  if (el.id === "conteudo") geracaoRenderizada = geracaoNavegacao;
  el.replaceChildren(...filhos.flat(Infinity).filter((f) => f !== null && f !== undefined && f !== false)
    .map((f) => (f instanceof Node ? f : document.createTextNode(String(f)))));
}

async function api(caminho, opcoes = {}) {
  let resp;
  try {
    resp = await fetch(caminho, {
      ...opcoes,
      headers: { "Content-Type": "application/json", ...(opcoes.headers || {}) },
    });
  } catch (_) {
    throw new Error("Sem conexão com a loja. Verifique a internet e tente novamente.");
  }
  let dados = null;
  try { dados = await resp.json(); } catch (_) { /* corpo vazio */ }
  if (!resp.ok) {
    const padrao = resp.status === 429 ? "Muitas tentativas seguidas. Aguarde um pouco e tente de novo." : "Não foi possível completar a ação.";
    const erro = new Error((dados && dados.erro) || padrao);
    erro.status = resp.status;
    erro.campos = dados && dados.campos;
    throw erro;
  }
  return dados;
}

function avisar(texto) {
  const t = $("#aviso-flutuante");
  t.textContent = texto;
  t.classList.add("visivel");
  clearTimeout(avisar.timer);
  avisar.timer = setTimeout(() => t.classList.remove("visivel"), 2600);
}

async function copiarTexto(texto) {
  try {
    await navigator.clipboard.writeText(texto);
    return true;
  } catch (_) {
    const area = h("textarea", { readonly: true, class: "sr", "aria-hidden": "true" });
    area.value = texto;
    document.body.append(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (_) { ok = false; }
    area.remove();
    return ok;
  }
}

function botaoCopiar(texto, rotulo, aviso) {
  return h("button", { class: "botao secundario", type: "button", onclick: async () => {
    avisar(await copiarTexto(texto) ? aviso : `Não deu para copiar. Selecione e copie: ${texto}`);
  } }, "📋 ", rotulo);
}

function mascaraCep(v) {
  const d = v.replace(/\D/g, "").slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
}
function mascaraCpf(v) {
  const d = v.replace(/\D/g, "").slice(0, 11);
  return d.replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d{1,2})$/, "$1-$2");
}
function mascaraTelefone(v) {
  const d = v.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

function cpfValido(cpf) {
  const d = String(cpf || "").replace(/\D/g, "");
  if (d.length !== 11 || d === d[0].repeat(11)) return false;
  for (const n of [9, 10]) {
    let soma = 0;
    for (let i = 0; i < n; i++) soma += Number(d[i]) * (n + 1 - i);
    if (((soma * 10) % 11) % 10 !== Number(d[n])) return false;
  }
  return true;
}

/**
 * Lê um número digitado à mão. Com vírgula, ela é o decimal e os pontos são milhar ("1.234,56").
 * Sem vírgula, o ponto só é milhar no formato "1.299" / "12.345.678"; senão é decimal ("0.765", "49.90").
 * `pontoDecimal`: câmbio e percentuais, em que o ponto é sempre decimal.
 * Vazio -> null; lixo ("12abc") -> NaN.
 */
function lerNumero(v, { pontoDecimal = false } = {}) {
  let t = String(v ?? "").trim().replace(/^R\$/i, "").replace(/\s+/g, "");
  if (!t) return null;
  if (t.includes(",")) t = t.replace(/\./g, "").replace(",", ".");
  else if (!pontoDecimal && /^[1-9]\d{0,2}(\.\d{3})+$/.test(t)) t = t.replace(/\./g, "");
  return /^\d+(\.\d+)?$/.test(t) ? Number(t) : NaN;
}

/** "49,90", "49.90", "1.299" ou "1.234,56" -> centavos; vazio -> null; inválido -> NaN. */
function reais(v) {
  const n = lerNumero(v);
  return n === null || Number.isNaN(n) ? n : Math.round(n * 100);
}
const textoReais = (c) => (c === null || c === undefined ? "" : (c / 100).toFixed(2).replace(".", ","));

function lerArmazenado(chave, padrao, armazenamento = localStorage) {
  try { return JSON.parse(armazenamento.getItem(chave)) ?? padrao; } catch (_) { return padrao; }
}
function gravar(chave, valor, armazenamento = localStorage) {
  try { armazenamento.setItem(chave, JSON.stringify(valor)); } catch (_) { /* modo privado */ }
}

// ------------------------------------------------------------- imagens

/** Espelha loja/imagens.py: a imagem provisória do produto é gerada aqui, sem ir ao servidor. */
const cacheSvg = new Map();
function escurecer(cor, fator = 0.62) {
  return "#" + [1, 3, 5].map((i) => Math.floor(parseInt(cor.slice(i, i + 2), 16) * fator).toString(16).padStart(2, "0")).join("");
}
function svgProduto(emoji, cor) {
  const base = /^#[0-9a-fA-F]{6}$/.test(cor || "") ? cor : "#1f5c45";
  const chave = `${base}|${emoji}`;
  if (cacheSvg.has(chave)) return cacheSvg.get(chave);
  const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">`
    + `<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${base}"/><stop offset="1" stop-color="${escurecer(base)}"/></linearGradient>`
    + `<pattern id="trama" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">`
    + `<rect width="14" height="28" fill="#fff" fill-opacity=".06"/><rect y="0" width="28" height="14" fill="#000" fill-opacity=".05"/></pattern></defs>`
    + `<rect width="400" height="400" fill="url(#g)"/><rect width="400" height="400" fill="url(#trama)"/>`
    + `<circle cx="200" cy="200" r="118" fill="#fff" fill-opacity=".16"/>`
    + `<text x="200" y="208" font-size="132" text-anchor="middle" dominant-baseline="middle" font-family="'Noto Color Emoji','Apple Color Emoji','Segoe UI Emoji',sans-serif">${esc(emoji || "📦")}</text></svg>`;
  const uri = `data:image/svg+xml,${encodeURIComponent(svg)}`;
  cacheSvg.set(chave, uri);
  return uri;
}

/** URL da imagem do produto; sem foto e com a cor disponível, gera o SVG no navegador. */
function imagemProduto(p, miniatura = false) {
  const semFoto = typeof p.imagem === "string" && p.imagem.startsWith("/img/produto/");
  if (semFoto && p.cor) return svgProduto(p.icone, p.cor);
  return (miniatura && p.imagem_miniatura) || p.imagem;
}
