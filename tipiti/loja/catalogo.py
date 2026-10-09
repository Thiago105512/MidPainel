"""Catálogo: categorias, listagem e detalhe de produtos, imagens e endereços (slugs)."""

import re

from .db import normaliza
from .validacao import NaoEncontrado


ORDENACOES = {
    "relevancia": "p.destaque DESC, p.nome",
    "menor_preco": "p.preco_centavos, p.nome",
    "maior_preco": "p.preco_centavos DESC, p.nome",
    "novidades": "p.id DESC",
    "nome": "p.nome",
}


def url_imagem(slug, foto=""):
    return f"/fotos/{foto}" if foto else f"/img/produto/{slug}.svg"


def gerar_slug(texto):
    slug = re.sub(r"[^a-z0-9]+", "-", normaliza(texto)).strip("-")
    return slug[:80].strip("-") or "produto"


def url_miniatura(row):
    """Miniatura da capa; fotos antigas, sem miniatura própria, usam o arquivo principal."""
    if not row["foto"]:
        return None
    return f"/fotos/{row['foto_miniatura'] or row['foto']}"


def _produto(row, admin=False, com_descricao=True):
    produto = {
        "id": row["id"],
        "slug": row["slug"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco_centavos": row["preco_centavos"],
        "preco_de_centavos": row["preco_de_centavos"],
        "estoque": row["estoque"],
        "icone": row["icone"],
        "destaque": bool(row["destaque"]),
        "ativo": bool(row["ativo"]),
        "imagem": url_imagem(row["slug"], row["foto"]),
        "imagem_miniatura": url_miniatura(row),
        "cor": row["categoria_cor"],
        "tem_variacoes": row["n_variacoes"] > 0,
        "categoria": {"slug": row["categoria_slug"], "nome": row["categoria_nome"]},
    }
    if not com_descricao:
        del produto["descricao"]
    if admin:
        produto["custo_centavos"] = row["custo_centavos"]
    return produto


_SELECT_PRODUTO = """
    SELECT p.*, c.slug AS categoria_slug, c.nome AS categoria_nome, c.cor AS categoria_cor,
           (SELECT COUNT(*) FROM variacoes v WHERE v.produto_id = p.id AND v.ativo = 1) AS n_variacoes,
           (SELECT COUNT(*) FROM variacoes v WHERE v.produto_id = p.id) AS n_variacoes_total,
           (SELECT f.miniatura FROM fotos_produto f WHERE f.produto_id = p.id ORDER BY f.ordem, f.id LIMIT 1)
               AS foto_miniatura
    FROM produtos p JOIN categorias c ON c.id = p.categoria_id
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
                    limite=None, offset=0, incluir_inativos=False, admin=False):
    """Listagens públicas não trazem a descrição (só a página do produto precisa dela)."""
    where, params = [], []
    if not incluir_inativos:
        where.append("p.ativo = 1")
    if categoria:
        where.append("c.slug = ?")
        params.append(categoria)
    if destaque:
        where.append("p.destaque = 1")
    for termo in normaliza(busca or "").split()[:8]:
        termo = termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("p.busca LIKE ? ESCAPE '\\'")
        params.append(f"%{termo}%")
    sql = _SELECT_PRODUTO
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY " + ORDENACOES.get(ordem, ORDENACOES["relevancia"])
    if limite or offset:
        sql += " LIMIT ? OFFSET ?"
        params += [int(limite) if limite else -1, int(offset or 0)]
    return [_produto(r, admin, com_descricao=admin) for r in conn.execute(sql, params).fetchall()]


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
    produto = _produto(row, admin)
    produto["variacoes"] = _variacoes(conn, row["id"], incluir_inativas=admin)
    if not admin:
        for v in produto["variacoes"]:
            del v["sku"], v["ativo"]
    produto["fotos"] = _fotos(conn, row["id"])
    relacionados = conn.execute(
        _SELECT_PRODUTO + " WHERE c.slug = ? AND p.slug != ? AND p.ativo = 1 ORDER BY p.destaque DESC, RANDOM() LIMIT 4",
        (row["categoria_slug"], slug),
    ).fetchall()
    produto["relacionados"] = [_produto(r, com_descricao=False) for r in relacionados]
    return produto


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
