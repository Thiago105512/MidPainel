"""Servidor HTTP da Tipiti: API JSON, arquivos estáticos e páginas da loja (SPA)."""

import hmac
import json
import mimetypes
import re
import secrets
from html import escape
from pathlib import Path
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

from . import ajustes, config, db, fotos, frete, precificacao, regras
from .imagens import svg_produto

TAMANHO_MAX_CORPO = 64 * 1024
TAMANHO_MAX_UPLOAD = fotos.TAMANHO_MAX_FOTO * 4 // 3 + 4096  # base64 + folga

CSP = (
    "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; "
    "connect-src 'self' https://viacep.com.br; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


class ErroHttp(Exception):
    def __init__(self, status, mensagem):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


ROTAS = []


def rota(metodo, padrao, admin=False, corpo_max=TAMANHO_MAX_CORPO):
    def registrar(func):
        func.corpo_max = corpo_max
        ROTAS.append((metodo, re.compile(f"^{padrao}$"), admin, func))
        return func
    return registrar


# ---------------------------------------------------------------- API pública

@rota("GET", r"/api/loja")
def api_loja(conn, req):
    return {
        "nome": config.NOME_LOJA,
        "site": config.SITE_URL,
        "email": config.EMAIL_CONTATO,
        "frete_gratis_a_partir": config.FRETE_GRATIS_A_PARTIR,
        "desconto_pix_pct": config.DESCONTO_PIX_PCT,
        "parcelas_max": config.PARCELAS_MAX,
        "parcela_minima": config.PARCELA_MINIMA,
        "cidades_destaque": frete.CIDADES_DESTAQUE,
        "whatsapp": (a := ajustes.obter(conn))["whatsapp"],
        "whatsapp_mensagem": a["whatsapp_mensagem"],
        "zonas_frete": [
            {"nome": nome, "valor_centavos": valor, "prazo_dias": prazo + config.PRAZO_MANUSEIO_DIAS}
            for nome, valor, prazo in dict.fromkeys((z[3], z[4], z[5]) for z in frete.ZONAS)
        ],
    }


@rota("GET", r"/api/categorias")
def api_categorias(conn, req):
    return regras.listar_categorias(conn)


@rota("GET", r"/api/categorias/(?P<slug>[a-z0-9-]+)")
def api_categoria(conn, req, slug):
    return regras.obter_categoria(conn, slug)


@rota("GET", r"/api/produtos")
def api_produtos(conn, req):
    q = req.query
    return regras.listar_produtos(
        conn,
        categoria=q.get("categoria"),
        busca=q.get("q"),
        ordem=q.get("ordem", "relevancia"),
        destaque=q.get("destaque") == "1",
        limite=int(q["limite"]) if q.get("limite", "").isdigit() else None,
    )


@rota("GET", r"/api/produtos/(?P<slug>[a-z0-9-]+)")
def api_produto(conn, req, slug):
    return regras.obter_produto(conn, slug)


@rota("GET", r"/api/frete")
def api_frete(conn, req):
    try:
        subtotal = int(req.query.get("subtotal", "0"))
    except ValueError:
        subtotal = 0
    return frete.cotar(regras.cep_digitos(req.query.get("cep")), max(0, subtotal))


@rota("POST", r"/api/carrinho/cotacao")
def api_cotacao(conn, req):
    corpo = req.json()
    return regras.cotar_carrinho(conn, corpo.get("itens"), cep=corpo.get("cep") or None,
                                 pagamento=corpo.get("pagamento") or "pix")


@rota("POST", r"/api/pedidos")
def api_criar_pedido(conn, req):
    codigo = regras.criar_pedido(conn, req.json())
    return HTTPStatus.CREATED, regras.obter_pedido_publico(conn, codigo)


@rota("GET", r"/api/pedidos/(?P<codigo>[A-Za-z0-9-]{4,20})")
def api_pedido(conn, req, codigo):
    return regras.obter_pedido_publico(conn, codigo)


# ---------------------------------------------------------------- API administrativa

@rota("GET", r"/api/admin/pedidos", admin=True)
def api_admin_pedidos(conn, req):
    return regras.listar_pedidos(conn, status=req.query.get("status"))


@rota("PATCH", r"/api/admin/pedidos/(?P<codigo>[A-Z0-9-]{4,20})", admin=True)
def api_admin_status(conn, req, codigo):
    regras.atualizar_status(conn, codigo, req.json().get("status"))
    return regras.obter_pedido_publico(conn, codigo)


@rota("GET", r"/api/admin/resumo", admin=True)
def api_admin_resumo(conn, req):
    return regras.resumo_vendas(conn)


@rota("GET", r"/api/admin/produtos", admin=True)
def api_admin_produtos(conn, req):
    return regras.listar_produtos(conn, ordem="nome", incluir_inativos=True, admin=True)


@rota("GET", r"/api/admin/produtos/(?P<slug>[a-z0-9-]+)", admin=True)
def api_admin_obter_produto(conn, req, slug):
    return regras.obter_produto(conn, slug, incluir_inativos=True, admin=True)


@rota("PATCH", r"/api/admin/produtos/(?P<slug>[a-z0-9-]+)", admin=True)
def api_admin_produto(conn, req, slug):
    return regras.atualizar_produto(conn, slug, req.json())


@rota("POST", r"/api/admin/produtos", admin=True)
def api_admin_criar_produto(conn, req):
    return HTTPStatus.CREATED, regras.criar_produto(conn, req.json())


@rota("PUT", r"/api/admin/produtos/(?P<slug>[a-z0-9-]+)/variacoes", admin=True)
def api_admin_variacoes(conn, req, slug):
    return regras.salvar_variacoes(conn, slug, req.json().get("variacoes"))


@rota("POST", r"/api/admin/produtos/(?P<slug>[a-z0-9-]+)/foto", admin=True, corpo_max=TAMANHO_MAX_UPLOAD)
def api_admin_foto(conn, req, slug):
    produto = regras.obter_produto(conn, slug, incluir_inativos=True)  # 404 antes de gravar arquivo
    if len(produto["fotos"]) >= config.FOTOS_POR_PRODUTO:
        raise regras.ErroValidacao({"foto": f"Máximo de {config.FOTOS_POR_PRODUTO} fotos por produto."})
    pasta = req.handler.server.fotos_dir
    arquivo = fotos.salvar(pasta, slug, req.json().get("dados"))
    try:
        return regras.adicionar_foto(conn, slug, arquivo)
    except Exception:
        (pasta / arquivo).unlink(missing_ok=True)
        raise


@rota("DELETE", r"/api/admin/produtos/(?P<slug>[a-z0-9-]+)/fotos/(?P<foto_id>[0-9]+)", admin=True)
def api_admin_remover_foto(conn, req, slug, foto_id):
    arquivo, produto = regras.remover_foto(conn, slug, int(foto_id))
    (req.handler.server.fotos_dir / arquivo).unlink(missing_ok=True)
    return produto


@rota("POST", r"/api/admin/produtos/(?P<slug>[a-z0-9-]+)/fotos/(?P<foto_id>[0-9]+)/capa", admin=True)
def api_admin_capa(conn, req, slug, foto_id):
    return regras.definir_capa(conn, slug, int(foto_id))


@rota("POST", r"/api/admin/calculadora", admin=True)
def api_admin_calculadora(conn, req):
    return precificacao.calcular(req.json())


@rota("GET", r"/api/admin/ajustes", admin=True)
def api_admin_ajustes(conn, req):
    return ajustes.obter(conn)


@rota("PUT", r"/api/admin/ajustes", admin=True)
def api_admin_salvar_ajustes(conn, req):
    return ajustes.salvar(conn, req.json())


# ---------------------------------------------------------------- servidor

PAGINAS_SPA = re.compile(
    r"^/(|categoria/[a-z0-9-]+|produto/[a-z0-9-]+|busca|carrinho|checkout|pedido/[A-Za-z0-9-]+|"
    r"entregas|sobre|trocas|admin|admin/produto/[a-z0-9-]+)/?$"
)


class Requisicao:
    def __init__(self, handler, query, corpo_max=TAMANHO_MAX_CORPO):
        self.handler = handler
        self.query = query
        self.corpo_max = corpo_max
        self._json = None

    def json(self):
        if self._json is None:
            tamanho = int(self.handler.headers.get("Content-Length") or 0)
            if tamanho > self.corpo_max:
                raise ErroHttp(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Requisição grande demais.")
            bruto = self.handler.rfile.read(tamanho) if tamanho else b"{}"
            try:
                dados = json.loads(bruto.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ErroHttp(HTTPStatus.BAD_REQUEST, "JSON inválido.")
            if not isinstance(dados, dict):
                raise ErroHttp(HTTPStatus.BAD_REQUEST, "Esperado um objeto JSON.")
            self._json = dados
        return self._json


class TipitiHandler(BaseHTTPRequestHandler):
    server_version = "Tipiti/1.0"
    sys_version = ""

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

    def log_message(self, formato, *args):
        if not getattr(self.server, "silencioso", False):
            super().log_message(formato, *args)

    # -- respostas

    def _enviar(self, status, corpo, tipo, extras=None):
        if isinstance(corpo, str):
            corpo = corpo.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Content-Security-Policy", CSP)
        for chave, valor in (extras or {}).items():
            self.send_header(chave, valor)
        self.end_headers()
        if not self._cabecalho_apenas:
            self.wfile.write(corpo)

    def _json(self, status, dados):
        self._enviar(status, json.dumps(dados, ensure_ascii=False), "application/json; charset=utf-8",
                     {"Cache-Control": "no-store"})

    # -- roteamento

    def _despachar(self, metodo, cabecalho_apenas=False):
        self._cabecalho_apenas = cabecalho_apenas
        partes = urlsplit(self.path)
        caminho = unquote(partes.path)
        query = {k: v[0] for k, v in parse_qs(partes.query).items()}
        try:
            if caminho.startswith("/api/"):
                self._api(metodo, caminho, query)
            elif metodo != "GET":
                raise ErroHttp(HTTPStatus.METHOD_NOT_ALLOWED, "Método não permitido.")
            elif caminho.startswith("/static/"):
                self._estatico(caminho[len("/static/"):])
            elif caminho.startswith("/img/produto/") and caminho.endswith(".svg"):
                self._imagem(caminho[len("/img/produto/"):-4])
            elif caminho.startswith("/fotos/"):
                self._foto(caminho[len("/fotos/"):])
            elif caminho == "/favicon.ico":
                self._estatico("img/favicon.svg")
            elif caminho == "/robots.txt":
                self._enviar(200, f"User-agent: *\nDisallow: /admin\nDisallow: /api/\n"
                                  f"Sitemap: {config.SITE_URL}/sitemap.xml\n", "text/plain; charset=utf-8")
            elif caminho == "/sitemap.xml":
                self._sitemap()
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

    def _autorizado(self):
        cabecalho = self.headers.get("Authorization", "")
        token = cabecalho[7:] if cabecalho.startswith("Bearer ") else ""
        return bool(token) and hmac.compare_digest(token.encode(), self.server.admin_token.encode())

    def _api(self, metodo, caminho, query):
        metodo_errado = False
        for m, padrao, admin, func in ROTAS:
            achou = padrao.match(caminho)
            if not achou:
                continue
            if m != metodo:
                metodo_errado = True
                continue
            if admin and not self._autorizado():
                raise ErroHttp(HTTPStatus.UNAUTHORIZED, "Acesso restrito.")
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
            return self._json(status, resultado)
        if metodo_errado:
            raise ErroHttp(HTTPStatus.METHOD_NOT_ALLOWED, "Método não permitido.")
        raise ErroHttp(HTTPStatus.NOT_FOUND, "Recurso não encontrado.")

    def _estatico(self, relativo):
        raiz = config.STATIC_DIR.resolve()
        alvo = (raiz / relativo).resolve()
        if raiz not in alvo.parents or not alvo.is_file():
            raise ErroHttp(HTTPStatus.NOT_FOUND, "Arquivo não encontrado.")
        tipo = mimetypes.guess_type(alvo.name)[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo in ("application/javascript", "image/svg+xml"):
            tipo += "; charset=utf-8"
        self._enviar(200, alvo.read_bytes(), tipo, {"Cache-Control": "public, max-age=300"})

    def _foto(self, nome):
        if not re.fullmatch(r"[a-z0-9-]+\.(jpg|png|webp)", nome):
            raise ErroHttp(HTTPStatus.NOT_FOUND, "Foto não encontrada.")
        alvo = self.server.fotos_dir / nome
        if not alvo.is_file():
            raise ErroHttp(HTTPStatus.NOT_FOUND, "Foto não encontrada.")
        self._enviar(200, alvo.read_bytes(), fotos.TIPOS[nome.rsplit(".", 1)[1]],
                     {"Cache-Control": "public, max-age=86400"})

    def _imagem(self, slug):
        conn = db.conectar(self.server.db_path)
        try:
            dados = regras.cor_e_icone(conn, slug)
        except regras.NaoEncontrado:
            raise ErroHttp(HTTPStatus.NOT_FOUND, "Imagem não encontrada.")
        finally:
            conn.close()
        self._enviar(200, svg_produto(dados["nome"], dados["icone"], dados["cor"]),
                     "image/svg+xml; charset=utf-8", {"Cache-Control": "public, max-age=3600"})

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

    def _pagina(self, caminho, status=HTTPStatus.OK):
        """Entrega o index.html com título/descrição da página, para buscadores e compartilhamento."""
        titulo = f"{config.NOME_LOJA} — importados com entrega rápida no Norte"
        descricao = ("Achadinhos, eletrônicos, casa, beleza e muito mais importados, com entrega para Manaus, Parintins, "
                     "Boa Vista, Santarém, Macapá e toda a Região Norte. Frete grátis acima de R$ 199.")
        conn = db.conectar(self.server.db_path)
        try:
            if caminho.startswith("/produto/"):
                p = regras.obter_produto(conn, caminho.split("/")[2])
                titulo, descricao = f"{p['nome']} | {config.NOME_LOJA}", p["descricao"]
            elif caminho.startswith("/categoria/"):
                c = regras.obter_categoria(conn, caminho.split("/")[2])
                titulo, descricao = f"{c['nome']} | {config.NOME_LOJA}", c["descricao"]
        except regras.NaoEncontrado:
            status = HTTPStatus.NOT_FOUND
        finally:
            conn.close()
        canonico = config.SITE_URL + (caminho.rstrip("/") or "/")
        html = (config.STATIC_DIR / "index.html").read_text(encoding="utf-8")
        html = (html.replace("__TITULO__", escape(titulo))
                    .replace("__DESCRICAO__", escape(descricao[:160]))
                    .replace("__CANONICO__", escape(canonico)))
        self._enviar(status, html, "text/html; charset=utf-8", {"Cache-Control": "no-cache"})


def criar_servidor(host=None, porta=None, db_path=None, admin_token=None, silencioso=False):
    caminho_db = db_path or config.DB_PATH
    conn = db.conectar(caminho_db)
    try:
        db.inicializar(conn)
    finally:
        conn.close()
    servidor = ThreadingHTTPServer((host or config.HOST, config.PORT if porta is None else porta), TipitiHandler)
    servidor.db_path = caminho_db
    servidor.fotos_dir = Path(caminho_db).parent / "fotos"
    servidor.admin_token = admin_token or config.ADMIN_TOKEN or secrets.token_urlsafe(18)
    servidor.silencioso = silencioso
    return servidor


def main():
    servidor = criar_servidor()
    host, porta = servidor.server_address[:2]
    print(f"Tipiti no ar em http://{host}:{porta}")
    if not config.ADMIN_TOKEN:
        print(f"Token do painel /admin (gerado nesta execução): {servidor.admin_token}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
