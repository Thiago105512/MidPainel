"""Servidor HTTP da Tipiti: API JSON, arquivos estáticos e páginas da loja (SPA)."""

import gzip
import hashlib
import hmac
import json
import mimetypes
import re
import secrets
import threading
from html import escape
from pathlib import Path
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from . import config, db, feeds, fotos, pwa, regras, vitrine_seo
from .imagens import svg_produto
from .limites import MSG_LIMITE, LimiteTaxa, limites_padrao  # noqa: F401 — LimiteTaxa: importável daqui também
from .rotas import ROTAS, TAMANHO_MAX_CORPO, TAMANHO_MAX_UPLOAD, ErroHttp, api_loja, rota  # noqa: F401
from .rotas_extras import RespostaBruta  # importar registra as rotas de Pix, encomendas e feeds

THREADS_MAX = 128
HOSTS_LOCAIS = ("127.0.0.1", "localhost", "::1")
CACHE_LONGO = "public, max-age=31536000, immutable"
TIPOS_COMPRIMIVEIS = ("application/javascript", "application/json", "application/xml", "image/svg+xml")

CSP = (
    "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; "
    "connect-src 'self' https://viacep.com.br; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


# ---------------------------------------------------------------- servidor

PAGINAS_SPA = re.compile(
    r"^/(|categoria/[a-z0-9-]+|produto/[a-z0-9-]+|busca|carrinho|checkout|pedido/[A-Za-z0-9-]+|"
    r"entregas|sobre|trocas|admin|admin/produto/[a-z0-9-]+|"
    r"encomenda|encomenda/[A-Za-z0-9-]+)/?$"
)

# Arquivos que o index.html referencia com ?v=<hash do conteúdo>, para o navegador guardar por um ano.
ASSETS_VERSIONADOS = ("js/app.js", "css/estilo.css")

# Assets montados no servidor: o app.js é a junção de static/js/partes/*.js, em ordem de nome. O navegador
# continua baixando um arquivo só.
ASSETS_MONTADOS = {"js/app.js": "js/partes"}

_cache_gzip = {}
_versoes = {}
_montados = {}
_trava_cache = threading.Lock()


def _comprimir(corpo, chave=None):
    """gzip do corpo; arquivos estáticos (chave = caminho, mtime, tamanho) são comprimidos uma vez só."""
    if chave is None:
        return gzip.compress(corpo, compresslevel=6, mtime=0)
    with _trava_cache:
        pronto = _cache_gzip.get(chave)
    if pronto is None:
        pronto = gzip.compress(corpo, compresslevel=6, mtime=0)
        with _trava_cache:
            if len(_cache_gzip) >= 64:  # versões antigas dos arquivos saem daqui
                _cache_gzip.clear()
            _cache_gzip[chave] = pronto
    return pronto


def _localizar_estatico(relativo):
    """Encontra um arquivo estático sem ler o conteúdo: (nome, etag, chave, ler) ou None se não existir.

    `chave` muda sempre que o conteúdo muda (caminho, mtime e tamanho) e indexa os caches de gzip e de versão;
    `ler()` devolve os bytes. Os assets montados são a junção das suas partes, guardada em memória.
    """
    raiz = config.STATIC_DIR.resolve()
    if relativo in ASSETS_MONTADOS:
        partes = sorted((raiz / ASSETS_MONTADOS[relativo]).glob("*.js"))
        if not partes:
            return None
        estados = [(p.name, p.stat()) for p in partes]
        chave = (relativo, *((nome, info.st_mtime_ns, info.st_size) for nome, info in estados))
        etag = hashlib.sha256(repr(chave).encode()).hexdigest()[:16]
        return Path(relativo).name, etag, chave, lambda: _montar(partes, chave)
    alvo = (raiz / relativo).resolve()
    if raiz not in alvo.parents or not alvo.is_file():
        return None
    info = alvo.stat()
    return (alvo.name, f"{info.st_mtime_ns:x}-{info.st_size:x}", (str(alvo), info.st_mtime_ns, info.st_size),
            alvo.read_bytes)


def _montar(partes, chave):
    """Junta as partes (separadas por uma quebra de linha); refaz só quando alguma parte muda."""
    with _trava_cache:
        guardado = _montados.get(chave[0])
    if guardado and guardado[0] == chave:
        return guardado[1]
    corpo = b"\n".join(p.read_bytes() for p in partes)
    with _trava_cache:
        _montados[chave[0]] = (chave, corpo)
    return corpo


def _versao(relativo):
    achado = _localizar_estatico(relativo)
    if achado is None:
        return None
    _, _, chave, ler = achado
    with _trava_cache:
        guardada = _versoes.get(relativo)
    if guardada and guardada[0] == chave:
        return guardada[1]
    versao = hashlib.sha256(ler()).hexdigest()[:10]
    with _trava_cache:
        _versoes[relativo] = (chave, versao)
    return versao


def _url_versionada(relativo):
    versao = _versao(relativo)
    return f"/static/{relativo}?v={versao}" if versao else f"/static/{relativo}"


def _json_no_html(dados):
    """JSON seguro dentro de <script>: sem <, > nem & literais, nada fecha a tag antes da hora."""
    texto = json.dumps(dados, ensure_ascii=False)
    return texto.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _cabecalho_seo(caminho, status, produto, categoria):
    """og:type, og:image e JSON-LD (Product, BreadcrumbList, Organization/WebSite) para o <head> da página.

    O JSON-LD passa por _json_no_html: nenhum <, > ou & literal, então um nome de produto não fecha o <script>.
    """
    if status != HTTPStatus.OK:
        produto = categoria = None
        caminho = "/404"
    seo = vitrine_seo.cabecalho(caminho, produto=produto, categoria=categoria)
    partes = [f'<meta property="og:type" content="{escape(seo["og_tipo"])}">',
              f'<meta property="og:image" content="{escape(seo["og_imagem"])}">']
    if seo["og_imagem"].endswith(pwa.IMAGEM_COMPARTILHAR):
        partes += ['<meta property="og:image:width" content="1200">',
                   '<meta property="og:image:height" content="630">']
    if seo["json_ld"]:
        partes.append(f'<script type="application/ld+json">{_json_no_html(seo["json_ld"])}</script>')
    return "  " + "\n  ".join(partes) + "\n"


class Requisicao:
    def __init__(self, handler, query, corpo_max=TAMANHO_MAX_CORPO):
        self.handler = handler
        self.query = query
        self.corpo_max = corpo_max
        self._json = None

    def json(self):
        if self._json is None:
            if "Transfer-Encoding" in self.handler.headers:  # corpo em partes não é aceito: exige Content-Length
                raise ErroHttp(HTTPStatus.LENGTH_REQUIRED, "Envie o tamanho da requisição (Content-Length).")
            try:
                tamanho = int(self.handler.headers.get("Content-Length") or 0)
            except ValueError:
                raise ErroHttp(HTTPStatus.BAD_REQUEST, "Content-Length inválido.")
            if tamanho < 0:
                raise ErroHttp(HTTPStatus.BAD_REQUEST, "Content-Length inválido.")
            if tamanho > self.corpo_max:
                raise ErroHttp(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Requisição grande demais.")
            try:
                bruto = self.handler.rfile.read(tamanho) if tamanho else b"{}"
            except TimeoutError:
                raise ErroHttp(HTTPStatus.REQUEST_TIMEOUT, "Tempo esgotado ao receber os dados.")
            if len(bruto) < tamanho:
                raise ErroHttp(HTTPStatus.BAD_REQUEST, "Requisição incompleta.")
            self.handler.corpo_pendente = False
            try:
                dados = json.loads(bruto.decode("utf-8"), parse_constant=_recusar_constante)
            except (UnicodeDecodeError, ValueError, RecursionError):  # ValueError cobre inteiros gigantes
                raise ErroHttp(HTTPStatus.BAD_REQUEST, "JSON inválido.")
            if not isinstance(dados, dict):
                raise ErroHttp(HTTPStatus.BAD_REQUEST, "Esperado um objeto JSON.")
            self._json = dados
        return self._json


def _recusar_constante(nome):
    raise ValueError(f"{nome} não é um número válido")


def _etag_confere(cabecalho, etag):
    for valor in (cabecalho or "").split(","):
        valor = valor.strip()
        if valor == "*" or valor.removeprefix("W/").strip('"') == etag:
            return True
    return False


def _aceita_gzip(cabecalho):
    for parte in (cabecalho or "").lower().split(","):
        nome, _, params = parte.partition(";")
        if nome.strip() in ("gzip", "*"):
            q = re.search(r"q=([0-9.]+)", params)
            try:
                return not q or float(q.group(1)) > 0
            except ValueError:
                return False
    return False


class TipitiHandler(BaseHTTPRequestHandler):
    server_version = "Tipiti/1.0"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    timeout = 15  # tempo máximo para receber uma requisição já iniciada (corpo lento, upload pelo 4G)
    ocioso = 5  # tempo que uma conexão keep-alive pode ficar parada ocupando uma vaga

    def handle_one_request(self):
        # espera curta pela próxima requisição; ao chegar a primeira linha, volta ao prazo normal em parse_request
        self.connection.settimeout(self.ocioso)
        super().handle_one_request()

    def parse_request(self):
        self.connection.settimeout(self.timeout)
        return super().parse_request()

    corpo_pendente = False
    _cabecalho_apenas = False

    def do_GET(self):
        self._despachar("GET")

    def do_HEAD(self):
        self._despachar("GET", cabecalho_apenas=True)

    def do_POST(self):
        self._despachar("POST")

    def do_PATCH(self):
        self._despachar("PATCH")

    def do_PUT(self):
        self._despachar("PUT")

    def do_DELETE(self):
        self._despachar("DELETE")

    @property
    def ip_cliente(self):
        if self.server.confiar_proxy:
            encaminhado = getattr(self, "headers", None) and self.headers.get("X-Forwarded-For", "")
            ultimo = (encaminhado or "").split(",")[-1].strip()
            if ultimo:  # o último valor é o que o nosso proxy acrescentou; os anteriores vêm do cliente
                return ultimo[:64]
        return self.client_address[0]

    def address_string(self):
        return self.ip_cliente

    def log_message(self, formato, *args):
        if not getattr(self.server, "silencioso", False):
            super().log_message(formato, *args)

    def send_error(self, code, message=None, explain=None):
        """Erros do próprio http.server (linha de requisição inválida, método desconhecido…) também em JSON."""
        self.corpo_pendente = True  # não sabemos o que sobrou na conexão: fecha
        self._cabecalho_apenas = self.command == "HEAD"
        mensagem = "Método não suportado." if code == HTTPStatus.NOT_IMPLEMENTED else "Requisição inválida."
        self._json(code, {"erro": mensagem})

    # -- respostas

    def _enviar(self, status, corpo, tipo, extras=None, etag=None, chave_gzip=None):
        if isinstance(corpo, str):
            corpo = corpo.encode("utf-8")
        cabecalhos = dict(extras or {})
        headers = getattr(self, "headers", None)
        if tipo.split(";")[0] in TIPOS_COMPRIMIVEIS or tipo.startswith("text/"):
            if len(corpo) > 1024:
                cabecalhos["Vary"] = "Accept-Encoding"
                if headers and _aceita_gzip(headers.get("Accept-Encoding")):
                    corpo = _comprimir(corpo, chave_gzip)
                    cabecalhos["Content-Encoding"] = "gzip"
                    etag = etag and etag + "-gz"  # cada codificação tem a sua ETag
        if etag:
            cabecalhos["ETag"] = f'"{etag}"'
            if status == HTTPStatus.OK and headers and _etag_confere(headers.get("If-None-Match"), etag):
                status, corpo = HTTPStatus.NOT_MODIFIED, None
                cabecalhos.pop("Content-Encoding", None)
        self.send_response(status)
        if corpo is not None:
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        if config.SITE_URL.startswith("https"):
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        for chave, valor in cabecalhos.items():
            self.send_header(chave, valor)
        if self.corpo_pendente:  # o corpo da requisição não foi lido; sobraria na conexão
            self.send_header("Connection", "close")
        self.end_headers()
        if corpo and not self._cabecalho_apenas:
            self.wfile.write(corpo)

    def _json(self, status, dados):
        self._enviar(status, json.dumps(dados, ensure_ascii=False), "application/json; charset=utf-8",
                     {"Cache-Control": "no-store"})

    # -- roteamento

    def _despachar(self, metodo, cabecalho_apenas=False):
        self._cabecalho_apenas = cabecalho_apenas
        self.corpo_pendente = (self.headers.get("Content-Length", "0").strip() not in ("", "0")
                               or "Transfer-Encoding" in self.headers)
        partes = urlsplit(self.path)
        caminho = unquote(partes.path)
        query = {k: v[0] for k, v in parse_qs(partes.query).items()}
        try:
            if caminho.startswith("/api/"):
                self._api(metodo, caminho, query)
            elif metodo != "GET":
                raise ErroHttp(HTTPStatus.METHOD_NOT_ALLOWED, "Método não permitido.")
            elif caminho.startswith("/static/"):
                self._estatico(caminho[len("/static/"):], query)
            elif caminho.startswith("/img/produto/") and caminho.endswith(".svg"):
                self._imagem(caminho[len("/img/produto/"):-4])
            elif caminho.startswith("/fotos/"):
                self._foto(caminho[len("/fotos/"):])
            elif caminho == "/favicon.ico":
                self._estatico("img/favicon.svg", {})
            elif caminho == "/robots.txt":
                self._enviar(200, f"User-agent: *\nDisallow: /admin\nDisallow: /api/\n"
                                  f"Sitemap: {config.SITE_URL}/sitemap.xml\n", "text/plain; charset=utf-8")
            elif caminho == "/sitemap.xml":
                self._sitemap()
            elif caminho in ("/manifest.webmanifest", "/sw.js", "/feeds/google.xml", "/feeds/meta.csv"):
                self._arquivo_gerado(caminho)
            elif PAGINAS_SPA.match(caminho):
                self._pagina(caminho)
            else:
                self._pagina(caminho, status=HTTPStatus.NOT_FOUND)
        except ErroHttp as e:
            self._json(e.status, {"erro": e.mensagem})
        except Exception:  # noqa: BLE001 — nunca vazar detalhes internos
            self.log_error("Erro interno em %s %s", metodo, caminho)
            import traceback
            traceback.print_exc()
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"erro": "Erro interno. Tente novamente."})

    def _token_enviado(self):
        cabecalho = self.headers.get("Authorization", "")
        return cabecalho[7:] if cabecalho.startswith("Bearer ") else ""

    def _autorizar_admin(self):
        """Depois de muitas tentativas erradas, recusa até o token certo, para não dar pistas a quem tenta adivinhar."""
        limite = self.server.limites["admin"]
        if limite.excedido(self.ip_cliente):
            raise ErroHttp(HTTPStatus.TOO_MANY_REQUESTS, MSG_LIMITE)
        token = self._token_enviado()
        if not token or not hmac.compare_digest(token.encode(), self.server.admin_token.encode()):
            if token:
                limite.registrar(self.ip_cliente)
            raise ErroHttp(HTTPStatus.UNAUTHORIZED, "Acesso restrito.")

    def _api(self, metodo, caminho, query):
        metodo_errado = False
        for m, padrao, admin, func in ROTAS:
            achou = padrao.match(caminho)
            if not achou:
                continue
            if m != metodo:
                metodo_errado = True
                continue
            if admin:
                self._autorizar_admin()
            conn = db.conectar(self.server.db_path)
            try:
                resultado = func(conn, Requisicao(self, query, func.corpo_max), **achou.groupdict())
            except regras.ErroValidacao as e:
                return self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"erro": e.mensagem, "campos": e.campos})
            except regras.NaoEncontrado as e:
                return self._json(HTTPStatus.NOT_FOUND, {"erro": str(e)})
            finally:
                conn.close()
            status = HTTPStatus.OK
            if isinstance(resultado, tuple):
                status, resultado = resultado
            if isinstance(resultado, RespostaBruta):
                return self._enviar(status, resultado.corpo, resultado.tipo, resultado.cabecalhos)
            return self._json(status, resultado)
        if metodo_errado:
            raise ErroHttp(HTTPStatus.METHOD_NOT_ALLOWED, "Método não permitido.")
        raise ErroHttp(HTTPStatus.NOT_FOUND, "Recurso não encontrado.")

    def _estatico(self, relativo, query):
        achado = _localizar_estatico(relativo)
        if achado is None:
            raise ErroHttp(HTTPStatus.NOT_FOUND, "Arquivo não encontrado.")
        nome, etag, chave, ler = achado
        tipo = mimetypes.guess_type(nome)[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo in ("application/javascript", "image/svg+xml"):
            tipo += "; charset=utf-8"
        # com ?v=<hash> a URL muda junto com o conteúdo, então pode ficar guardada por um ano
        cache = CACHE_LONGO if "v" in query else "public, max-age=300"
        self._enviar(200, ler(), tipo, {"Cache-Control": cache}, etag=etag, chave_gzip=chave)

    def _foto(self, nome):
        if not re.fullmatch(r"[a-z0-9-]+\.(jpg|png|webp)", nome):
            raise ErroHttp(HTTPStatus.NOT_FOUND, "Foto não encontrada.")
        alvo = self.server.fotos_dir / nome
        if not alvo.is_file():
            raise ErroHttp(HTTPStatus.NOT_FOUND, "Foto não encontrada.")
        # o nome de cada arquivo é único: uma foto nova nunca reaproveita uma URL
        self._enviar(200, alvo.read_bytes(), fotos.TIPOS[nome.rsplit(".", 1)[1]],
                     {"Cache-Control": CACHE_LONGO}, etag=nome)

    def _imagem(self, slug):
        conn = db.conectar(self.server.db_path)
        try:
            dados = regras.cor_e_icone(conn, slug)
        except regras.NaoEncontrado:
            raise ErroHttp(HTTPStatus.NOT_FOUND, "Imagem não encontrada.")
        finally:
            conn.close()
        etag = hashlib.sha256(f"{dados['nome']}|{dados['icone']}|{dados['cor']}".encode()).hexdigest()[:16]
        self._enviar(200, svg_produto(dados["nome"], dados["icone"], dados["cor"]),
                     "image/svg+xml; charset=utf-8", {"Cache-Control": "public, max-age=3600"}, etag=etag)

    def _sitemap(self):
        conn = db.conectar(self.server.db_path)
        try:
            urls = ["/", "/entregas", "/sobre", "/trocas"]
            urls += [f"/categoria/{c['slug']}" for c in regras.listar_categorias(conn)]
            urls += [f"/produto/{p['slug']}" for p in regras.listar_produtos(conn, ordem="nome")]
        finally:
            conn.close()
        corpo = "".join(f"<url><loc>{escape(config.SITE_URL + u)}</loc></url>" for u in urls)
        self._enviar(200, '<?xml version="1.0" encoding="UTF-8"?>'
                          f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{corpo}</urlset>',
                     "application/xml; charset=utf-8")

    def _arquivo_gerado(self, caminho):
        """Manifesto do app, service worker e feeds de produtos (gerados a cada pedido, com ETag)."""
        if caminho == "/manifest.webmanifest":
            corpo = json.dumps(pwa.manifesto(), ensure_ascii=False, indent=1)
            tipo, extras = "application/manifest+json; charset=utf-8", {"Cache-Control": "public, max-age=3600"}
        elif caminho == "/sw.js":
            corpo = pwa.service_worker(*(_url_versionada(r) for r in ASSETS_VERSIONADOS))
            # sempre conferido com o servidor: é assim que o navegador descobre uma versão nova da loja
            tipo, extras = "application/javascript; charset=utf-8", {"Cache-Control": "no-cache",
                                                                     "Service-Worker-Allowed": "/"}
        else:
            conn = db.conectar(self.server.db_path)
            try:
                if caminho.endswith(".xml"):
                    corpo, tipo = feeds.google_xml(conn), "application/xml; charset=utf-8"
                else:
                    corpo, tipo = feeds.meta_csv(conn), "text/csv; charset=utf-8"
            finally:
                conn.close()
            extras = {"Cache-Control": "public, max-age=900"}
        corpo = corpo.encode("utf-8")
        self._enviar(200, corpo, tipo, extras, etag=hashlib.sha256(corpo).hexdigest()[:16])

    def _pagina(self, caminho, status=HTTPStatus.OK):
        """Entrega o index.html com título/descrição da página, para buscadores e compartilhamento.

        Leva junto os dados da loja e das categorias, poupando duas idas à API antes da primeira tela.
        """
        titulo = f"{config.NOME_LOJA} — importados com entrega rápida no Norte"
        descricao = ("Achadinhos, eletrônicos, casa, beleza e muito mais importados, com entrega para Manaus, Parintins, "
                     "Boa Vista, Santarém, Macapá e toda a Região Norte. Frete grátis acima de R$ 199.")
        produto = categoria = None
        conn = db.conectar(self.server.db_path)
        try:
            dados_iniciais = {"loja": api_loja(conn, None), "categorias": regras.listar_categorias(conn)}
            if caminho.startswith("/produto/"):
                p = produto = regras.obter_produto(conn, caminho.split("/")[2])
                titulo, descricao = f"{p['nome']} | {config.NOME_LOJA}", p["descricao"]
            elif caminho.startswith("/categoria/"):
                c = categoria = regras.obter_categoria(conn, caminho.split("/")[2])
                titulo, descricao = f"{c['nome']} | {config.NOME_LOJA}", c["descricao"]
        except regras.NaoEncontrado:
            status = HTTPStatus.NOT_FOUND
        finally:
            conn.close()
        canonico = config.SITE_URL + (caminho.rstrip("/") or "/")
        valores = {
            "TITULO": escape(titulo),
            "DESCRICAO": escape(descricao[:160]),
            "CANONICO": escape(canonico),
            "DADOS_INICIAIS": _json_no_html(dados_iniciais),
        }
        html = (config.STATIC_DIR / "index.html").read_text(encoding="utf-8")
        # uma passada só: um nome de produto com "__X__" não é substituído de novo
        html = re.sub(r"__(TITULO|DESCRICAO|CANONICO|DADOS_INICIAIS)__", lambda m: valores[m.group(1)], html)
        for relativo in ASSETS_VERSIONADOS:
            versao = _versao(relativo)
            if versao:
                html = html.replace(f'"/static/{relativo}"', f'"/static/{relativo}?v={versao}"')
        html = html.replace("</head>", _cabecalho_seo(caminho, status, produto, categoria) + "</head>", 1)
        self._enviar(status, html, "text/html; charset=utf-8", {"Cache-Control": "no-cache"})


class ServidorTipiti(ThreadingHTTPServer):
    request_queue_size = 128
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # limita as threads simultâneas; o excesso espera na fila do socket em vez de esgotar a memória
        self._vagas = threading.BoundedSemaphore(THREADS_MAX)

    def process_request(self, request, client_address):
        self._vagas.acquire()
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._vagas.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._vagas.release()


def resolver_token_admin(host):
    """Devolve (token, gerado_agora). Token gerado só vale quando o servidor escuta apenas nesta máquina."""
    token = config.ADMIN_TOKEN
    if token:
        if len(token) < config.ADMIN_TOKEN_MINIMO:
            raise SystemExit(f"TIPITI_ADMIN_TOKEN muito curto: use pelo menos {config.ADMIN_TOKEN_MINIMO} caracteres "
                             f"(ex.: python3 -c 'import secrets; print(secrets.token_urlsafe(32))').")
        return token, False
    if host not in HOSTS_LOCAIS:
        raise SystemExit(f"Defina TIPITI_ADMIN_TOKEN (pelo menos {config.ADMIN_TOKEN_MINIMO} caracteres) "
                         f"para rodar a loja em {host}.")
    return secrets.token_urlsafe(24), True


def criar_servidor(host=None, porta=None, db_path=None, admin_token=None, silencioso=False):
    host = host or config.HOST
    token_gerado = False
    if not admin_token:
        admin_token, token_gerado = resolver_token_admin(host)
    caminho_db = db_path or config.DB_PATH
    conn = db.conectar(caminho_db)
    try:
        db.inicializar(conn)
    finally:
        conn.close()
    servidor = ServidorTipiti((host, config.PORT if porta is None else porta), TipitiHandler)
    servidor.db_path = caminho_db
    servidor.fotos_dir = Path(caminho_db).parent / "fotos"
    servidor.admin_token = admin_token
    servidor.token_gerado = token_gerado
    servidor.silencioso = silencioso
    servidor.confiar_proxy = config.CONFIAR_PROXY
    servidor.limites = limites_padrao()
    return servidor


def main():
    servidor = criar_servidor()
    host, porta = servidor.server_address[:2]
    print(f"Tipiti no ar em http://{host}:{porta}")
    if servidor.token_gerado:
        print(f"Token do painel /admin (gerado nesta execução): {servidor.admin_token}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
