"""Rotas da API JSON: cada função @rota recebe (conn, req, **grupos da URL) e devolve os dados da resposta."""

import re
import time
from http import HTTPStatus

from . import ajustes, config, encomendas, fotos, frete, legal, pix, precificacao, regras
from .limites import MSG_LIMITE
from . import rastreio, revendedoras, viagens

TAMANHO_MAX_CORPO = 64 * 1024
TAMANHO_MAX_UPLOAD = (fotos.TAMANHO_MAX_FOTO + fotos.TAMANHO_MAX_MINIATURA) * 4 // 3 + 8192  # base64 + folga
CACHE_VENDAS_RECENTES_S = 60


class ErroHttp(Exception):
    def __init__(self, status, mensagem):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


def _limitar(req, nome):
    if req.handler.server.limites[nome].excedido(req.handler.ip_cliente):
        raise ErroHttp(HTTPStatus.TOO_MANY_REQUESTS, MSG_LIMITE)


def _registrar(req, nome):
    req.handler.server.limites[nome].registrar(req.handler.ip_cliente)


ROTAS = []


def rota(metodo, padrao, admin=False, corpo_max=TAMANHO_MAX_CORPO, papel=None):
    """papel (só rotas admin): None segue usuarios.OPERADOR_PODE; "operador" libera o operador; "dono" só o dono."""
    def registrar(func):
        func.corpo_max = corpo_max
        func.papel = papel
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
        "chave_pix": a["chave_pix"],
        "pix_ativo": pix.pix_ativo(a),
        "prazo_reserva_horas": config.PRAZO_RESERVA_HORAS,
        "prova_social": a["prova_social"] == "1",
        "envio_hoje": ajustes.envio_hoje(a),
        "cupom_destaque": regras.cupom_destaque(conn),
        "empresa": legal.empresa(a),
        "pendencias_legais": legal.pendencias(a),
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


def _inteiro_da_query(query, nome):
    valor = query.get(nome)
    if valor is None:
        return None
    if not re.fullmatch(r"[0-9]{1,9}", valor):
        raise ErroHttp(HTTPStatus.BAD_REQUEST, f"Parâmetro “{nome}” inválido.")
    return int(valor)


@rota("GET", r"/api/produtos")
def api_produtos(conn, req):
    q = req.query
    limite = _inteiro_da_query(q, "limite")
    return regras.listar_produtos(
        conn,
        categoria=q.get("categoria"),
        busca=q.get("q"),
        ordem=q.get("ordem", "relevancia"),
        destaque=q.get("destaque") == "1",
        promo=q.get("promo") == "1",
        limite=None if limite is None else min(max(limite, 1), 100),
        offset=_inteiro_da_query(q, "offset") or 0,
    )


@rota("GET", r"/api/produtos/(?P<slug>[a-z0-9-]+)")
def api_produto(conn, req, slug):
    return regras.obter_produto(conn, slug)


@rota("GET", r"/api/produtos/(?P<slug>[a-z0-9-]+)/avaliacoes")
def api_avaliacoes_produto(conn, req, slug):
    return regras.listar_avaliacoes(conn, slug)


@rota("POST", r"/api/avaliacoes")
def api_criar_avaliacao(conn, req):
    _limitar(req, "avaliacoes")
    _registrar(req, "avaliacoes")  # toda tentativa conta: dificulta testar códigos e e-mails de pedidos
    return HTTPStatus.CREATED, regras.criar_avaliacao(conn, req.json())


@rota("GET", r"/api/vendas-recentes")
def api_vendas_recentes(conn, req):
    """Compras reais recentes (sem nome de cliente). Guardadas por 60 s para não consultar a cada visita."""
    if ajustes.obter(conn)["prova_social"] != "1":
        return []
    servidor = req.handler.server
    guardado = getattr(servidor, "cache_vendas_recentes", None)
    agora = time.monotonic()
    if guardado and guardado[0] > agora:
        return guardado[1]
    vendas = regras.vendas_recentes(conn)
    servidor.cache_vendas_recentes = (agora + CACHE_VENDAS_RECENTES_S, vendas)
    return vendas


@rota("GET", r"/api/frete")
def api_frete(conn, req):
    try:
        subtotal = int(req.query.get("subtotal", "0"))
    except ValueError:
        subtotal = 0
    return viagens.anexar_ao_frete(conn, frete.cotar(regras.cep_digitos(req.query.get("cep")), max(0, subtotal)))


@rota("POST", r"/api/carrinho/cotacao")
def api_cotacao(conn, req):
    corpo = req.json()
    if corpo.get("cpf") and corpo.get("cupom"):
        # a regra de "primeira compra" revela se o CPF já comprou: limita consultas em série
        _limitar(req, "cpf_cupom")
        _registrar(req, "cpf_cupom")
    return regras.cotar_carrinho(conn, corpo.get("itens"), cep=corpo.get("cep") or None,
                                 pagamento=corpo.get("pagamento") or "pix", cupom=corpo.get("cupom"),
                                 cpf=corpo.get("cpf"), revendedora=corpo.get("revendedora"))


@rota("POST", r"/api/pedidos")
def api_criar_pedido(conn, req):
    # cada pedido reserva estoque até o prazo de pagamento; o limite impede esvaziar a loja com pedidos falsos
    _limitar(req, "pedidos")
    codigo = regras.criar_pedido(conn, req.json())
    _registrar(req, "pedidos")
    return HTTPStatus.CREATED, regras.obter_pedido_publico(conn, codigo)


@rota("GET", r"/api/pedidos/(?P<codigo>[A-Za-z0-9-]{4,20})")
def api_pedido(conn, req, codigo):
    _limitar(req, "consulta")  # só erros contam: dificulta adivinhar códigos de pedido
    try:
        return regras.obter_pedido_publico(conn, codigo)
    except regras.NaoEncontrado:
        _registrar(req, "consulta")
        raise


# ---------------------------------------------------------------- API administrativa

@rota("GET", r"/api/admin/pedidos", admin=True)
def api_admin_pedidos(conn, req):
    return regras.listar_pedidos(conn, status=req.query.get("status"))


@rota("PATCH", r"/api/admin/pedidos/(?P<codigo>[A-Z0-9-]{4,20})", admin=True)
def api_admin_status(conn, req, codigo):
    # {status?, codigo_rastreio?, viagem_id?}
    rastreio.atualizar_pedido_admin(conn, codigo, req.json())
    return {**regras.obter_pedido_publico(conn, codigo), "whatsapp_aviso": rastreio.aviso_whatsapp(conn, codigo)}


@rota("GET", r"/api/admin/resumo", admin=True)
def api_admin_resumo(conn, req):
    from . import emails
    resumo = regras.resumo_vendas(conn)
    resumo["revendedoras_pendentes"] = revendedoras.pendentes(conn)
    resumo["encomendas_novas"] = encomendas.contar_novas(conn)
    resumo["pendencias_legais"] = legal.pendencias(ajustes.obter(conn))
    resumo["email_configurado"] = emails.configurado()
    resumo["emails_pendentes"] = emails.pendentes(conn)
    return resumo


@rota("GET", r"/api/admin/produtos", admin=True)
def api_admin_produtos(conn, req):
    return regras.listar_produtos(conn, ordem="nome", incluir_inativos=True, admin=True)


@rota("GET", r"/api/admin/produtos/(?P<slug>[a-z0-9-]+)", admin=True)
def api_admin_obter_produto(conn, req, slug):
    from . import avise_me
    produto = regras.obter_produto(conn, slug, incluir_inativos=True, admin=True)
    produto["avise_me_total"] = avise_me.total_produto(conn, produto["id"])
    return produto


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
    corpo = req.json()
    arquivo, miniatura = fotos.salvar(pasta, slug, corpo.get("dados"), corpo.get("miniatura"))
    try:
        return regras.adicionar_foto(conn, slug, arquivo, miniatura)
    except Exception:
        for nome in (arquivo, miniatura):
            if nome:
                (pasta / nome).unlink(missing_ok=True)
        raise


@rota("DELETE", r"/api/admin/produtos/(?P<slug>[a-z0-9-]+)/fotos/(?P<foto_id>[0-9]{1,18})", admin=True)
def api_admin_remover_foto(conn, req, slug, foto_id):
    arquivos, produto = regras.remover_foto(conn, slug, int(foto_id))
    for nome in arquivos:
        (req.handler.server.fotos_dir / nome).unlink(missing_ok=True)
    return produto


@rota("POST", r"/api/admin/produtos/(?P<slug>[a-z0-9-]+)/fotos/(?P<foto_id>[0-9]{1,18})/capa", admin=True)
def api_admin_capa(conn, req, slug, foto_id):
    return regras.definir_capa(conn, slug, int(foto_id))


@rota("GET", r"/api/admin/avaliacoes", admin=True)
def api_admin_avaliacoes(conn, req):
    return regras.listar_avaliacoes_admin(conn, status=req.query.get("status"))


@rota("PATCH", r"/api/admin/avaliacoes/(?P<avaliacao_id>[0-9]{1,18})", admin=True)
def api_admin_moderar_avaliacao(conn, req, avaliacao_id):
    return regras.moderar_avaliacao(conn, int(avaliacao_id), req.json().get("status"))


@rota("GET", r"/api/admin/cupons", admin=True)
def api_admin_cupons(conn, req):
    return regras.listar_cupons(conn)


@rota("POST", r"/api/admin/cupons", admin=True)
def api_admin_criar_cupom(conn, req):
    return HTTPStatus.CREATED, regras.criar_cupom(conn, req.json())


@rota("PATCH", r"/api/admin/cupons/(?P<codigo>[A-Za-z0-9-]{3,20})", admin=True)
def api_admin_cupom(conn, req, codigo):
    return regras.atualizar_cupom(conn, codigo, req.json())


@rota("POST", r"/api/admin/calculadora", admin=True)
def api_admin_calculadora(conn, req):
    return precificacao.calcular(req.json())


@rota("GET", r"/api/admin/ajustes", admin=True)
def api_admin_ajustes(conn, req):
    return ajustes.obter(conn)


@rota("PUT", r"/api/admin/ajustes", admin=True)
def api_admin_salvar_ajustes(conn, req):
    return ajustes.salvar(conn, req.json())


from . import rotas_barcos_revenda  # noqa: E402,F401 — calendário de barcos, rastreio e revendedoras
