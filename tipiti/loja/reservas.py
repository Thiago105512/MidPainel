"""Status dos pedidos e reserva de estoque: transições, cancelamento (devolve estoque e uso do cupom) e expiração
dos não pagos."""

from . import config, cupons, rastreio, revendedoras
from .catalogo import _sincronizar_estoque
from .validacao import ErroValidacao, NaoEncontrado


STATUS_PEDIDO = {
    "aguardando_pagamento": "Aguardando pagamento",
    "pago": "Pago",
    "enviado": "Enviado",
    "entregue": "Entregue",
    "cancelado": "Cancelado",
}

# Mudanças de status permitidas no painel. Cancelar devolve as unidades ao estoque.
TRANSICOES = {
    "aguardando_pagamento": ("pago", "cancelado"),
    "pago": ("enviado", "cancelado", "aguardando_pagamento"),
    "enviado": ("entregue",),
    "entregue": (),
    "cancelado": (),
}


def _devolver_estoque(conn, pedido_id):
    itens = conn.execute(
        "SELECT produto_id, variacao_id, quantidade FROM itens_pedido WHERE pedido_id = ?", (pedido_id,)
    ).fetchall()
    for item in itens:
        if item["variacao_id"]:
            conn.execute("UPDATE variacoes SET estoque = estoque + ? WHERE id = ?",
                         (item["quantidade"], item["variacao_id"]))
        else:
            conn.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ?",
                         (item["quantidade"], item["produto_id"]))
    # também cobre pedidos antigos, sem variação, de produtos que depois ganharam variações
    for produto_id in {i["produto_id"] for i in itens}:
        _sincronizar_estoque(conn, produto_id)


def atualizar_status(conn, codigo, novo_status, somente_se=None):
    """Muda o status respeitando TRANSICOES. Com somente_se, só age se o pedido ainda estiver nesse status."""
    if not isinstance(novo_status, str) or novo_status not in STATUS_PEDIDO:
        raise ErroValidacao({"status": "Status inválido."})
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT id, status, cupom_codigo FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()
        if not row:
            raise NaoEncontrado("Pedido não encontrado.")
        atual = row["status"]
        evento = None
        if atual != novo_status and (somente_se is None or atual == somente_se):
            if novo_status not in TRANSICOES[atual]:
                raise ErroValidacao({"status": f"Um pedido “{STATUS_PEDIDO[atual]}” não pode passar para "
                                               f"“{STATUS_PEDIDO[novo_status]}”."})
            if novo_status == "cancelado":
                _devolver_estoque(conn, row["id"])
                cupons.devolver_uso(conn, row["cupom_codigo"])
                revendedoras.ao_cancelar(conn, row["id"])
            conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, row["id"]))
            evento = rastreio.evento_de_status(conn, row["id"], novo_status)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    if evento:  # um e-mail por evento, depois do COMMIT
        rastreio.notificar(conn, codigo, *evento, status=novo_status)


def expirar_pendentes(conn):
    """Cancela pedidos não pagos dentro do prazo de reserva, devolvendo as unidades ao estoque.

    Sem isso, pedidos abandonados (ou feitos de má-fé) prenderiam o estoque para sempre.
    """
    vencidos = conn.execute(
        "SELECT codigo FROM pedidos WHERE status = 'aguardando_pagamento' AND criado_em < datetime('now', ?)",
        (f"-{int(config.PRAZO_RESERVA_HORAS)} hours",),
    ).fetchall()
    for row in vencidos:
        atualizar_status(conn, row["codigo"], "cancelado", somente_se="aguardando_pagamento")
