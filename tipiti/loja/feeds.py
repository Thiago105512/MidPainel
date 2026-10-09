"""Feeds de produtos para o Google Merchant Center (RSS 2.0 com o namespace g:) e para o catálogo da Meta
(Instagram/Facebook Shopping, CSV).

Só entram produtos no ar e com foto real (Google e Meta não aceitam SVG). Preços: `price` é o preço "cheio" mostrado
riscado na loja (quando há) e `sale_price` o que o cliente paga; na oferta relâmpago vai também o período.
"""

import csv
import io
import re
from xml.sax.saxutils import escape

from . import config, horario
from .catalogo import listar_produtos
from .vitrine_seo import absoluta, reais

ID_MAX = 50
TITULO_MAX = 150
DESCRICAO_MAX = 5000
IMAGENS_EXTRAS_MAX = 10
_INVALIDOS_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")


def _limpo(texto, maximo):
    return _INVALIDOS_XML.sub("", str(texto or "")).strip()[:maximo]


def _fotos_por_produto(conn):
    fotos = {}
    for r in conn.execute("SELECT produto_id, arquivo FROM fotos_produto ORDER BY produto_id, ordem, id"):
        fotos.setdefault(r["produto_id"], []).append(absoluta(f"/fotos/{r['arquivo']}"))
    return fotos


def _id_feed(produto):
    """O slug (o mesmo `sku` do JSON-LD); slugs maiores que o limite do Google viram "p<id>"."""
    return produto["slug"] if len(produto["slug"]) <= ID_MAX else f"p{produto['id']}"


def itens(conn):
    """(itens do feed, produtos no ar sem foto). Cada item já com os campos comuns aos dois feeds."""
    fotos = _fotos_por_produto(conn)
    no_feed, sem_foto = [], []
    for p in listar_produtos(conn, ordem="nome", admin=True):  # admin: traz a descrição; só produtos no ar
        imagens = fotos.get(p["id"])
        if not imagens:
            sem_foto.append({"nome": p["nome"], "slug": p["slug"]})
            continue
        if p["prevenda"]:
            disponibilidade = "preorder"
        else:
            disponibilidade = "in_stock" if p["estoque"] > 0 else "out_of_stock"
        ancora = p["preco_ancora_centavos"]
        item = {
            "id": _id_feed(p),
            "title": _limpo(p["nome"], TITULO_MAX),
            "description": _limpo(p.get("descricao") or p["nome"], DESCRICAO_MAX),
            "link": absoluta(f"/produto/{p['slug']}"),
            "image_link": imagens[0],
            "additional_image_link": imagens[1:1 + IMAGENS_EXTRAS_MAX],
            "availability": disponibilidade,
            "availability_date": f"{p['prevenda']['chegada']}T00:00-04:00" if p["prevenda"] else "",
            "price": f"{reais(ancora if ancora else p['preco_final_centavos'])} BRL",
            "sale_price": f"{reais(p['preco_final_centavos'])} BRL" if ancora else "",
            "sale_price_effective_date": "",
            "brand": config.NOME_LOJA,
            "condition": "new",
        }
        if p["promo"]:
            inicio = horario.agora().strftime("%Y-%m-%dT%H:%MZ")
            fim = p["promo"]["fim"][:16] + "Z"
            item["sale_price_effective_date"] = f"{inicio}/{fim}"
        no_feed.append(item)
    return no_feed, sem_foto


_ORDEM_GOOGLE = ("id", "title", "description", "link", "image_link", "additional_image_link", "availability",
                 "availability_date", "price", "sale_price", "sale_price_effective_date", "brand", "condition")
_SEM_PREFIXO = {"title", "description", "link"}  # elementos do próprio RSS


def google_xml(conn):
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">',
              "<channel>",
              f"<title>{escape(config.NOME_LOJA)}</title>",
              f"<link>{escape(absoluta('/'))}</link>",
              "<description>Importados com entrega rápida no Norte</description>"]
    for item in itens(conn)[0]:
        linhas.append("<item>")
        for campo in _ORDEM_GOOGLE:
            valores = item[campo] if isinstance(item[campo], list) else [item[campo]]
            for valor in valores:
                if valor == "":
                    continue
                tag = campo if campo in _SEM_PREFIXO else f"g:{campo}"
                linhas.append(f"<{tag}>{escape(str(valor))}</{tag}>")
        linhas.append("</item>")
    linhas += ["</channel>", "</rss>"]
    return "\n".join(linhas) + "\n"


_DISPONIBILIDADE_META = {"in_stock": "in stock", "out_of_stock": "out of stock", "preorder": "preorder"}
_COLUNAS_META = ("id", "title", "description", "availability", "condition", "price", "link", "image_link", "brand",
                 "additional_image_link", "sale_price", "sale_price_effective_date")


def meta_csv(conn):
    saida = io.StringIO()
    escritor = csv.writer(saida, lineterminator="\n")
    escritor.writerow(_COLUNAS_META)
    for item in itens(conn)[0]:
        linha = dict(item, availability=_DISPONIBILIDADE_META[item["availability"]],
                     additional_image_link=",".join(item["additional_image_link"]))
        escritor.writerow([linha[c] for c in _COLUNAS_META])
    return saida.getvalue()


def resumo_admin(conn):
    no_feed, sem_foto = itens(conn)
    return {
        "google": absoluta("/feeds/google.xml"),
        "meta": absoluta("/feeds/meta.csv"),
        "produtos_no_feed": len(no_feed),
        "sem_foto": sem_foto,
    }
