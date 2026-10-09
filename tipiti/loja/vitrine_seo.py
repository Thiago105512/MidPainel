"""Dados estruturados para Google/Instagram Shopping: JSON-LD (Product, BreadcrumbList, Organization, WebSite) e
og:image/og:type das páginas.

Tudo em URLs absolutas a partir de `config.SITE_URL`. O servidor injeta o resultado no <head> de forma segura.
"""

from datetime import datetime

from . import config, horario
from .pwa import ICONES, IMAGEM_COMPARTILHAR

SCHEMA = "https://schema.org"


def absoluta(caminho):
    return config.SITE_URL + caminho


def reais(centavos):
    """"119.90" — preço com ponto decimal, como pedem schema.org e os feeds."""
    return f"{centavos // 100}.{centavos % 100:02d}"


def imagens_do_produto(produto):
    """URLs absolutas das fotos reais (a capa primeiro); vazio se o produto só tem a imagem provisória (SVG)."""
    return [absoluta(f["url"]) for f in produto.get("fotos") or []]


def og_imagem(produto=None):
    """Capa do produto ou, sem foto, a imagem de compartilhamento da marca (redes sociais não aceitam SVG)."""
    if produto and str(produto.get("imagem") or "").startswith("/fotos/"):
        return absoluta(produto["imagem"])
    return absoluta(IMAGEM_COMPARTILHAR)


def data_local(iso_z):
    """'2026-10-12T03:00:00Z' -> '2026-10-11' (data em Manaus)."""
    momento = datetime.fromisoformat(iso_z.replace("Z", "+00:00"))
    return momento.astimezone(horario.FUSO_LOJA).date().isoformat()


def disponibilidade(produto):
    if produto.get("prevenda"):
        return "PreOrder"
    return "InStock" if produto["estoque"] > 0 else "OutOfStock"


def _migalhas(itens):
    return {
        "@context": SCHEMA,
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": nome, "item": absoluta(caminho)}
            for i, (nome, caminho) in enumerate(itens, start=1)
        ],
    }


def json_ld_produto(produto):
    url = absoluta(f"/produto/{produto['slug']}")
    oferta = {
        "@type": "Offer",
        "url": url,
        "priceCurrency": "BRL",
        "price": reais(produto["preco_final_centavos"]),
        "availability": f"{SCHEMA}/{disponibilidade(produto)}",
        "itemCondition": f"{SCHEMA}/NewCondition",
        "seller": {"@type": "Organization", "name": config.NOME_LOJA},
    }
    if produto.get("promo"):
        oferta["priceValidUntil"] = data_local(produto["promo"]["fim"])
    if produto.get("prevenda"):
        oferta["availabilityStarts"] = produto["prevenda"]["chegada"]
    dados = {
        "@context": SCHEMA,
        "@type": "Product",
        "name": produto["nome"],
        "image": imagens_do_produto(produto) or [og_imagem()],
        "description": produto.get("descricao") or produto["nome"],
        "sku": produto["slug"],
        "brand": {"@type": "Brand", "name": config.NOME_LOJA},
        "url": url,
        "offers": oferta,
    }
    if produto.get("avaliacoes_total"):
        dados["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": produto["nota_media"],
            "reviewCount": produto["avaliacoes_total"],
            "bestRating": 5,
            "worstRating": 1,
        }
    categoria = produto["categoria"]
    return [dados, _migalhas([("Início", "/"), (categoria["nome"], f"/categoria/{categoria['slug']}"),
                              (produto["nome"], f"/produto/{produto['slug']}")])]


def json_ld_categoria(categoria):
    return [_migalhas([("Início", "/"), (categoria["nome"], f"/categoria/{categoria['slug']}")])]


def json_ld_inicio():
    inicio = absoluta("/")
    return [
        {
            "@context": SCHEMA,
            "@type": "Organization",
            "name": config.NOME_LOJA,
            "url": inicio,
            "logo": absoluta(ICONES["512"]),
            "email": config.EMAIL_CONTATO,
        },
        {
            "@context": SCHEMA,
            "@type": "WebSite",
            "name": config.NOME_LOJA,
            "url": inicio,
            "inLanguage": "pt-BR",
            "potentialAction": {
                "@type": "SearchAction",
                "target": {"@type": "EntryPoint", "urlTemplate": absoluta("/busca?q={search_term_string}")},
                "query-input": "required name=search_term_string",
            },
        },
    ]


def cabecalho(caminho, produto=None, categoria=None):
    """{"og_tipo", "og_imagem", "json_ld": [...]} da página (json_ld vazio quando não há o que descrever)."""
    if produto is not None:
        return {"og_tipo": "product", "og_imagem": og_imagem(produto), "json_ld": json_ld_produto(produto)}
    json_ld = []
    if categoria is not None:
        json_ld = json_ld_categoria(categoria)
    elif caminho.rstrip("/") == "":
        json_ld = json_ld_inicio()
    return {"og_tipo": "website", "og_imagem": og_imagem(), "json_ld": json_ld}
