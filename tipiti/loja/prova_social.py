"""Prova social com dados reais: vendas dos últimos 30 dias, selos, compras recentes e "comprados juntos".

Nada aqui é inventado: os números saem dos pedidos não cancelados gravados no banco.
"""

from .imagens import url_imagem

DIAS_VENDIDOS = 30
DIAS_NOVIDADE = 14
POSICOES_MAIS_VENDIDO = 3
MINIMO_MAIS_VENDIDO = 3
ESTOQUE_ULTIMAS_UNIDADES = 5
HORAS_VENDAS_RECENTES = 72
MAX_VENDAS_RECENTES = 8

# Unidades vendidas por produto nos últimos 30 dias e a posição dele entre os produtos da mesma categoria
# (ativos e inativos são classificados separadamente). Uma consulta agregada só, juntada à listagem.
SQL_VENDAS_30D = f"""
    SELECT i.produto_id, SUM(i.quantidade) AS vendidos,
           RANK() OVER (PARTITION BY pr.categoria_id, pr.ativo ORDER BY SUM(i.quantidade) DESC) AS posicao
    FROM pedidos pe
    CROSS JOIN itens_pedido i ON i.pedido_id = pe.id  -- CROSS: começa pelos pedidos do período (índice da data)
    JOIN produtos pr ON pr.id = i.produto_id
    WHERE pe.status != 'cancelado' AND pe.criado_em >= datetime('now', '-{DIAS_VENDIDOS} days')
    GROUP BY i.produto_id
"""

SQL_NOVIDADE = f"p.criado_em >= datetime('now', '-{DIAS_NOVIDADE} days')"

# Quantos pedidos (não cancelados) levaram cada produto junto com o produto `?`.
SQL_COMPRADOS_JUNTOS = """
    SELECT i2.produto_id, COUNT(DISTINCT i2.pedido_id) AS vezes
    FROM itens_pedido i1
    JOIN pedidos pe ON pe.id = i1.pedido_id AND pe.status != 'cancelado'
    JOIN itens_pedido i2 ON i2.pedido_id = i1.pedido_id AND i2.produto_id != i1.produto_id
    WHERE i1.produto_id = ?
    GROUP BY i2.produto_id
"""


def selos(oferta, vendidos_30d, posicao_vendas, ativo, novidade, estoque):
    """Selos do produto, sempre nesta ordem: oferta, mais_vendido, novidade, ultimas_unidades."""
    lista = []
    if oferta:
        lista.append("oferta")
    if (ativo and posicao_vendas is not None and posicao_vendas <= POSICOES_MAIS_VENDIDO
            and vendidos_30d >= MINIMO_MAIS_VENDIDO):
        lista.append("mais_vendido")
    if novidade:
        lista.append("novidade")
    if 0 < estoque <= ESTOQUE_ULTIMAS_UNIDADES:
        lista.append("ultimas_unidades")
    return lista


def vendas_recentes(conn):
    """Compras das últimas 72 h, a mais nova primeiro, no máximo uma por produto. Sem nome de cliente."""
    rows = conn.execute(
        f"""SELECT pr.nome, pr.slug, pr.foto, pr.icone, c.cor, v.cidade, v.uf, v.minutos_atras,
                   (SELECT f.miniatura FROM fotos_produto f WHERE f.produto_id = pr.id ORDER BY f.ordem, f.id LIMIT 1)
                       AS foto_miniatura
            FROM (SELECT i.produto_id, pe.cidade, pe.uf, pe.id AS pedido_id,
                         CAST((julianday('now') - julianday(pe.criado_em)) * 1440 AS INTEGER) AS minutos_atras,
                         ROW_NUMBER() OVER (PARTITION BY i.produto_id ORDER BY pe.id DESC) AS ordem
                  FROM pedidos pe CROSS JOIN itens_pedido i ON i.pedido_id = pe.id
                  WHERE pe.status != 'cancelado'
                    AND pe.criado_em >= datetime('now', '-{HORAS_VENDAS_RECENTES} hours')) v
            JOIN produtos pr ON pr.id = v.produto_id AND pr.ativo = 1
            JOIN categorias c ON c.id = pr.categoria_id
            WHERE v.ordem = 1
            ORDER BY v.pedido_id DESC
            LIMIT ?""",
        (MAX_VENDAS_RECENTES,),
    ).fetchall()
    return [{
        "produto": r["nome"], "slug": r["slug"],
        "imagem": url_imagem(r["slug"], r["foto"] and (r["foto_miniatura"] or r["foto"])),  # miniatura, se houver
        "cor": r["cor"], "icone": r["icone"], "cidade": r["cidade"], "uf": r["uf"],
        "minutos_atras": max(0, r["minutos_atras"]),
    } for r in rows]
