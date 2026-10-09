/* Service worker da Tipiti.
 *
 * Este arquivo é um MODELO: o servidor (loja/pwa.py) troca os marcadores VERSAO, APP_JS e ESTILO_CSS (entre
 * sublinhados duplos, logo abaixo) por textos JSON e o entrega em /sw.js. A VERSAO muda sempre que o app.js, o estilo.css ou este modelo mudam; com ela mudam os
 * nomes dos caches, e o navegador instala a versão nova (que só assume quando a página pede, com SKIP_WAITING).
 *
 * Estratégias:
 *   navegações ............................ rede primeiro; sem internet, a página inicial guardada (o "shell")
 *   GET /api/loja, /api/categorias*, /api/produtos* ... mostra o guardado e atualiza por trás (stale-while-revalidate)
 *   /static/ e /fotos/ .................... cache primeiro
 *   /api/admin*, /api/pedidos*, /api/revenda*, /api/encomendas*, outros /api/ e tudo que não é GET: nunca guardados
 */
"use strict";

const VERSAO = __VERSAO__;
const APP_JS = __APP_JS__;
const ESTILO_CSS = __ESTILO_CSS__;

const PREFIXO = "tipiti-";
const CACHE_SHELL = PREFIXO + "shell-" + VERSAO;
const CACHE_DADOS = PREFIXO + "dados-" + VERSAO;
const CACHE_ESTATICOS = PREFIXO + "estaticos-" + VERSAO;
const CACHE_FOTOS = PREFIXO + "fotos-v1"; // o nome de cada foto é único: podem sobreviver às versões
const CACHES_ATUAIS = [CACHE_SHELL, CACHE_DADOS, CACHE_ESTATICOS, CACHE_FOTOS];
const MAXIMOS = { [CACHE_DADOS]: 80, [CACHE_ESTATICOS]: 80, [CACHE_FOTOS]: 200 };

const SHELL = "/";
const PRE_CACHE = [
  SHELL,
  APP_JS,
  ESTILO_CSS,
  "/static/img/logo.svg",
  "/static/img/favicon.svg",
  "/static/pwa/icone-192.png",
  "/manifest.webmanifest",
];

// Respostas com dados pessoais ou do painel: nunca passam pelo cache.
const NUNCA_GUARDAR = ["/api/admin", "/api/pedidos", "/api/revenda", "/api/encomendas"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_SHELL).then((cache) =>
      cache.addAll(PRE_CACHE.map((url) => new Request(url, { cache: "reload" })))
    )
  );
  // sem skipWaiting aqui: a versão nova espera a página pedir (mensagem SKIP_WAITING)
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const nomes = await caches.keys();
      await Promise.all(
        nomes
          .filter((nome) => nome.startsWith(PREFIXO) && !CACHES_ATUAIS.includes(nome))
          .map((nome) => caches.delete(nome))
      );
      if (self.registration.navigationPreload) {
        try {
          await self.registration.navigationPreload.enable();
        } catch (erro) {
          // navegador sem suporte: segue sem pré-carregamento
        }
      }
      await self.clients.claim();
    })()
  );
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.tipo === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return; // POST/PUT/PATCH/DELETE vão direto à rede
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // ViaCEP e outros: direto à rede
  const caminho = url.pathname;

  if (req.mode === "navigate") {
    event.respondWith(navegar(event, !caminho.startsWith("/api/") && !caminho.startsWith("/feeds/")));
    return;
  }
  if (NUNCA_GUARDAR.some((prefixo) => caminho.startsWith(prefixo))) return;
  if (req.headers.has("range") || caminho === "/sw.js") return;

  if (
    caminho === "/api/loja" ||
    caminho === "/api/categorias" ||
    caminho.startsWith("/api/categorias/") ||
    caminho.startsWith("/api/produtos")
  ) {
    event.respondWith(revalidar(event, CACHE_DADOS));
    return;
  }
  if (caminho.startsWith("/static/")) {
    event.respondWith(primeiroCache(event, CACHE_ESTATICOS));
    return;
  }
  if (caminho.startsWith("/fotos/")) {
    event.respondWith(primeiroCache(event, CACHE_FOTOS));
    return;
  }
  // o resto (inclusive os demais /api/) segue direto à rede, sem cache
});

async function navegar(event, comShell) {
  try {
    const preCarregada = await event.preloadResponse;
    const resposta = preCarregada || (await fetch(event.request));
    if (comShell && resposta.status === 200 && new URL(event.request.url).pathname === SHELL) {
      const copia = resposta.clone();
      event.waitUntil(caches.open(CACHE_SHELL).then((cache) => cache.put(SHELL, copia)));
    }
    return resposta;
  } catch (erro) {
    if (comShell) {
      const shell = await caches.match(SHELL);
      if (shell) return shell;
    }
    return Response.error();
  }
}

async function revalidar(event, nomeCache) {
  const cache = await caches.open(nomeCache);
  const guardada = await cache.match(event.request);
  const daRede = fetch(event.request).then(async (resposta) => {
    if (resposta.status === 200) {
      await cache.put(event.request, resposta.clone());
      await aparar(cache, MAXIMOS[nomeCache]);
    }
    return resposta;
  });
  if (guardada) {
    event.waitUntil(daRede.catch(() => undefined));
    return guardada;
  }
  return daRede;
}

async function primeiroCache(event, nomeCache) {
  const guardada = await caches.match(event.request);
  if (guardada) return guardada;
  const resposta = await fetch(event.request);
  if (resposta.status === 200 && resposta.type === "basic") {
    const copia = resposta.clone();
    event.waitUntil(
      caches.open(nomeCache).then(async (cache) => {
        await cache.put(event.request, copia);
        await aparar(cache, MAXIMOS[nomeCache]);
      })
    );
  }
  return resposta;
}

async function aparar(cache, maximo) {
  const chaves = await cache.keys(); // em ordem de inclusão: as mais antigas saem primeiro
  for (let i = 0; i < chaves.length - maximo; i++) {
    await cache.delete(chaves[i]);
  }
}
