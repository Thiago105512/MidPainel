"""Catálogo: categorias, listagem e detalhe de produtos, imagens e endereços (slugs)."""

import re

from . import horario
from .avaliacoes import SQL_NOTAS, nota_media
from .db import normaliza
from .imagens import url_imagem
from .prevenda import SQL_PREVENDA_ATIVA
from .prevenda import resumo as resumo_prevenda
from .promocoes import SQL_PROMO_ATIVA, preco_ancora, preco_com_desconto, sql_preco_final
from .prova_social import SQL_COMPRADOS_JUNTOS, SQL_NOVIDADE, SQL_VENDAS_30D, selos
from .validacao import NaoEncontrado


# Preço é o que o cliente paga (com a oferta relâmpago, se houver).
ORDENACOES = {
    "relevancia": "p.destaque DESC, p.nome",
    "menor_preco": "preco_final, p.nome",
    "maior_preco": "preco_final DESC, p.nome",
    "novidades": "p.id DESC",
    "nome": "p.nome",
    "mais_vendidos": "p.destaque DESC, p.nome",  # e depois por vendidos_30d, em listar_produtos
}


def gerar_slug(texto):
    slug = re.sub(r"[^a-z0-9]+", "-", normaliza(texto)).strip("-")
    return slug[:80].strip("-") or "produto"


def url_miniatura(row):
    """Miniatura da capa; fotos antigas, sem miniatura própria, usam o arquivo principal."""
    if not row["foto"]:
        return None
    return f"/fotos/{row['foto_miniatura'] or row['foto']}"


def _vendas_30d(conn):
    """{produto_id: (vendidos em 30 dias, posição na categoria)} — uma consulta agregada por requisição."""
    return {r["produto_id"]: (r["vendidos"], r["posicao"]) for r in conn.execute(SQL_VENDAS_30D)}


def _produto(row, vendas, admin=False, com_descricao=True):
    pct = row["promo_ativa"]
    vendidos, posicao = vendas.get(row["id"], (0, None))
    ancora = preco_ancora(row["preco_centavos"], row["preco_de_centavos"], pct)
    produto = {
        "id": row["id"],
        "slug": row["slug"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco_centavos": row["preco_centavos"],
        "preco_de_centavos": row["preco_de_centavos"],
        "preco_final_centavos": preco_com_desconto(row["preco_centavos"], pct),
        "preco_ancora_centavos": ancora,
        "promo": {"pct": pct, "fim": horario.iso_z(row["promo_fim"])} if pct else None,
        "estoque": row["estoque"],
        "icone": row["icone"],
        "destaque": bool(row["destaque"]),
        "ativo": bool(row["ativo"]),
        "imagem": url_imagem(row["slug"], row["foto"]),
        "imagem_miniatura": url_miniatura(row),
        "cor": row["categoria_cor"],
        "tem_variacoes": row["n_variacoes"] > 0,
        "categoria": {"slug": row["categoria_slug"], "nome": row["categoria_nome"]},
        "vendidos_30d": vendidos,
        "selos": selos(oferta=ancora is not None, vendidos_30d=vendidos, posicao_vendas=posicao, ativo=row["ativo"],
                       novidade=row["novidade"], estoque=row["estoque"], prevenda=bool(row["prevenda_ativa"])),
        "prevenda": resumo_prevenda(row["prevenda_ativa"]),
        "nota_media": nota_media(row["soma_notas"], row["avaliacoes_total"]),
        "avaliacoes_total": row["avaliacoes_total"],
    }
    if not com_descricao:
        del produto["descricao"]
    if admin:
        produto["custo_centavos"] = row["custo_centavos"]
        produto["promo_pct"] = row["promo_pct"]
        produto["promo_fim"] = horario.iso_z(row["promo_fim"])
        produto["prevenda_chegada"] = row["prevenda_chegada"]
    return produto


# As notas aprovadas entram por um agregado juntado à consulta; as vendas de 30 dias vêm de _vendas_30d.
# Nos dois casos é uma consulta para a listagem inteira, não uma por produto.
_SELECT_PRODUTO = f"""
    SELECT p.*, c.slug AS categoria_slug, c.nome AS categoria_nome, c.cor AS categoria_cor,
           (SELECT COUNT(*) FROM variacoes v WHERE v.produto_id = p.id AND v.ativo = 1) AS n_variacoes,
           (SELECT COUNT(*) FROM variacoes v WHERE v.produto_id = p.id) AS n_variacoes_total,
           (SELECT f.miniatura FROM fotos_produto f WHERE f.produto_id = p.id ORDER BY f.ordem, f.id LIMIT 1)
               AS foto_miniatura,
           {SQL_PROMO_ATIVA} AS promo_ativa,
           {sql_preco_final()} AS preco_final,
           {SQL_NOVIDADE} AS novidade,
           {SQL_PREVENDA_ATIVA} AS prevenda_ativa,
           av.soma_notas, COALESCE(av.total, 0) AS avaliacoes_total
    FROM produtos p JOIN categorias c ON c.id = p.categoria_id
    LEFT JOIN ({SQL_NOTAS}) av ON av.produto_id = p.id
"""


def listar_categorias(conn):
    rows = conn.execute(
        """SELECT c.slug, c.nome, c.descricao, c.icone, c.cor,
                  (SELECT COUNT(*) FROM produtos p WHERE p.categoria_id = c.id AND p.ativo = 1) AS total
           FROM categorias c ORDER BY c.ordem, c.nome"""
    ).fetchall()
    return [dict(r) for r in rows]


def obter_categoria(conn, slug):
    row = conn.execute(
        "SELECT slug, nome, descricao, icone, cor FROM categorias WHERE slug = ?", (slug,)
    ).fetchone()
    if not row:
        raise NaoEncontrado("Categoria não encontrada.")
    return dict(row)


def listar_produtos(conn, categoria=None, busca=None, ordem="relevancia", destaque=False,
                    limite=None, offset=0, incluir_inativos=False, admin=False, promo=False):
    """Listagens públicas não trazem a descrição (só a página do produto precisa dela).

    Com promo=True, só produtos com oferta relâmpago ativa, a que termina primeiro na frente.
    """
    where, params = [], []
    if not incluir_inativos:
        where.append("p.ativo = 1")
    if categoria:
        where.append("c.slug = ?")
        params.append(categoria)
    if destaque:
        where.append("p.destaque = 1")
    if promo:
        where.append(f"({SQL_PROMO_ATIVA}) IS NOT NULL")
    for termo in normaliza(busca or "").split()[:8]:
        termo = termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("p.busca LIKE ? ESCAPE '\\'")
        params.append(f"%{termo}%")
    sql = _SELECT_PRODUTO
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY " + ("p.promo_fim, " if promo else "") + ORDENACOES.get(ordem, ORDENACOES["relevancia"])
    mais_vendidos = ordem == "mais_vendidos" and not promo
    if (limite or offset) and not mais_vendidos:
        sql += " LIMIT ? OFFSET ?"
        params += [int(limite) if limite else -1, int(offset or 0)]
    vendas = _vendas_30d(conn)
    produtos = [_produto(r, vendas, admin, com_descricao=admin) for r in conn.execute(sql, params).fetchall()]
    if mais_vendidos:  # ordem estável: empates seguem destaque e nome; o catálogo cabe na memória
        produtos.sort(key=lambda p: -p["vendidos_30d"])
        inicio = int(offset or 0)
        produtos = produtos[inicio:inicio + int(limite)] if limite else produtos[inicio:]
    return produtos


def _variacoes(conn, produto_id, incluir_inativas=False):
    sql = "SELECT id, nome, sku, preco_centavos, estoque, ativo FROM variacoes WHERE produto_id = ?"
    if not incluir_inativas:
        sql += " AND ativo = 1"
    rows = conn.execute(sql + " ORDER BY ordem, id", (produto_id,)).fetchall()
    return [dict(r, ativo=bool(r["ativo"])) for r in rows]


def _fotos(conn, produto_id):
    rows = conn.execute(
        "SELECT id, arquivo, miniatura FROM fotos_produto WHERE produto_id = ? ORDER BY ordem, id", (produto_id,)
    ).fetchall()
    return [{"id": r["id"], "url": f"/fotos/{r['arquivo']}", "miniatura": f"/fotos/{r['miniatura'] or r['arquivo']}"}
            for r in rows]


def obter_produto(conn, slug, incluir_inativos=False, admin=False):
    sql = _SELECT_PRODUTO + " WHERE p.slug = ?"
    if not incluir_inativos:
        sql += " AND p.ativo = 1"
    row = conn.execute(sql, (slug,)).fetchone()
    if not row:
        raise NaoEncontrado("Produto não encontrado.")
    vendas = _vendas_30d(conn)
    produto = _produto(row, vendas, admin)
    produto["variacoes"] = _variacoes(conn, row["id"], incluir_inativas=admin)
    for v in produto["variacoes"]:
        preco = v["preco_centavos"] if v["preco_centavos"] is not None else row["preco_centavos"]
        v["preco_final_centavos"] = preco_com_desconto(preco, row["promo_ativa"])
        if not admin:
            del v["sku"], v["ativo"]
    produto["fotos"] = _fotos(conn, row["id"])
    relacionados = conn.execute(
        _SELECT_PRODUTO + " WHERE c.slug = ? AND p.slug != ? AND p.ativo = 1 ORDER BY p.destaque DESC, RANDOM() LIMIT 4",
        (row["categoria_slug"], slug),
    ).fetchall()
    produto["relacionados"] = [_produto(r, vendas, com_descricao=False) for r in relacionados]
    produto["comprados_juntos"] = _comprados_juntos(conn, row["id"], vendas)
    return produto


def _comprados_juntos(conn, produto_id, vendas):
    """Até 4 produtos (no ar e com estoque) que mais aparecem nos mesmos pedidos não cancelados."""
    rows = conn.execute(
        _SELECT_PRODUTO + f""" JOIN ({SQL_COMPRADOS_JUNTOS}) j ON j.produto_id = p.id
            WHERE p.ativo = 1 AND p.estoque > 0 ORDER BY j.vezes DESC, p.destaque DESC, p.nome LIMIT 4""",
        (produto_id,),
    ).fetchall()
    return [_produto(r, vendas, com_descricao=False) for r in rows]


def cor_e_icone(conn, slug):
    row = conn.execute(
        """SELECT p.nome, p.icone, c.cor FROM produtos p JOIN categorias c ON c.id = p.categoria_id
           WHERE p.slug = ? AND p.ativo = 1""",
        (slug,),
    ).fetchone()
    if not row:
        raise NaoEncontrado("Produto não encontrado.")
    return dict(row)


def _sincronizar_estoque(conn, produto_id):
    """Produto com variações: o estoque do produto é a soma do estoque das variações ativas.

    Se todas as variações foram desativadas, o estoque zera — o estoque antigo do produto não volta a ser vendido.
    """
    conn.execute(
        """UPDATE produtos SET estoque = (
               SELECT COALESCE(SUM(estoque), 0) FROM variacoes WHERE produto_id = ? AND ativo = 1)
           WHERE id = ? AND EXISTS (SELECT 1 FROM variacoes WHERE produto_id = ?)""",
        (produto_id, produto_id, produto_id),
    )
