"""Rastreio dos pedidos: código de rastreio, viagem (barco) atribuída e linha do tempo de eventos.

As mudanças de status (reservas.atualizar_status) geram eventos sozinhas; o painel acrescenta os demais
("separado", "chegou_porto", "saiu_entrega"…). As mensagens aparecem na página pública do pedido: nunca devem levar
dados pessoais do cliente (só a cidade de destino, que a página já mostra).

Cada evento gera exatamente um e-mail ao cliente (notificacoes.evento_pedido), sempre depois do COMMIT:
reservas.atualizar_status chama `notificar` para o evento automático; adicionar_evento faz o mesmo para os manuais.
"""

import re

from . import config, horario, viagens
from .validacao import ErroValidacao, NaoEncontrado

TIPOS_EVENTO = {
    "pago": "Pagamento confirmado",
    "separado": "Pedido separado",
    "embarcado": "Embarcado",
    "chegou_porto": "Chegou ao porto",
    "saiu_entrega": "Saiu para entrega",
    "entregue": "Entregue",
    "outro": "Atualização",
}

_CORREIOS = re.compile(r"[A-Z]{2}\d{9}[A-Z]{2}")
_CODIGO_RASTREIO = re.compile(r"[A-Z0-9-]{4,40}")
URL_CORREIOS = "https://rastreamento.correios.com.br/app/index.php?objeto={}"
MENSAGEM_MAX = 300


def url_rastreio(codigo):
    """Link dos Correios para códigos no formato AA123456789BR; None para outros (transportadora, barco…)."""
    return URL_CORREIOS.format(codigo) if codigo and _CORREIOS.fullmatch(codigo) else None


def mensagem_padrao(tipo, cidade, embarcacao=None):
    if tipo == "pago":
        return "Pagamento confirmado. Já estamos separando o seu pedido."
    if tipo == "separado":
        return "Pedido separado e embalado."
    if tipo == "embarcado":
        return f"Embarcou no {embarcacao} rumo a {cidade}." if embarcacao else f"Embarcou rumo a {cidade}."
    if tipo == "chegou_porto":
        return f"Chegou ao porto de {cidade}."
    if tipo == "saiu_entrega":
        return "Saiu para entrega."
    if tipo == "entregue":
        return "Pedido entregue. Obrigado por comprar na Tipiti!"
    return None


def registrar_evento(conn, pedido_id, tipo, mensagem):
    conn.execute("INSERT INTO eventos_pedido (pedido_id, tipo, mensagem, criado_em) VALUES (?, ?, ?, ?)",
                 (pedido_id, tipo, mensagem, horario.texto_db(horario.agora())))


def _pedido_e_viagem(conn, pedido_id):
    return conn.execute(
        """SELECT p.cidade, p.codigo_rastreio, v.embarcacao
           FROM pedidos p LEFT JOIN viagens v ON v.id = p.viagem_id WHERE p.id = ?""",
        (pedido_id,),
    ).fetchone()


def notificar(conn, codigo, tipo, mensagem, status=None):
    """E-mail ao cliente sobre um evento já gravado (chamar só depois do COMMIT). Nunca levanta erro."""
    from . import notificacoes  # notificacoes -> emails; import tardio evita ciclo com reservas

    notificacoes.evento_pedido(conn, codigo, tipo, mensagem, status=status)


def evento_de_status(conn, pedido_id, novo_status):
    """Evento automático de uma mudança de status (chamado dentro da transação de reservas.atualizar_status).

    Devolve (tipo, mensagem) para o e-mail que reservas manda depois do COMMIT, ou None.
    """
    p = _pedido_e_viagem(conn, pedido_id)
    if novo_status == "pago":
        tipo, mensagem = "pago", mensagem_padrao("pago", p["cidade"])
    elif novo_status == "enviado":
        if p["embarcacao"]:
            tipo, mensagem = "embarcado", mensagem_padrao("embarcado", p["cidade"], p["embarcacao"])
        else:
            tipo, mensagem = "outro", "Pedido enviado."
            if p["codigo_rastreio"]:
                mensagem += f" Código de rastreio: {p['codigo_rastreio']}."
    elif novo_status == "entregue":
        tipo, mensagem = "entregue", mensagem_padrao("entregue", p["cidade"])
    elif novo_status == "cancelado":
        tipo, mensagem = "outro", "Pedido cancelado."
    elif novo_status == "aguardando_pagamento":
        tipo, mensagem = "outro", "Pedido voltou a aguardar a confirmação do pagamento."
    else:
        return None
    registrar_evento(conn, pedido_id, tipo, mensagem)
    return tipo, mensagem


def _pedido(conn, codigo):
    row = conn.execute("SELECT * FROM pedidos WHERE codigo = ?", (str(codigo).upper(),)).fetchone()
    if not row:
        raise NaoEncontrado("Pedido não encontrado.")
    return row


def adicionar_evento(conn, codigo, dados, junto=None):
    """Evento lançado pelo painel: {tipo, mensagem?}. Não muda o status do pedido.

    `junto(row)` (opcional) roda na mesma transação do evento (ex.: separação grava `separado_em`).
    Depois do COMMIT o cliente recebe o e-mail do evento. Devolve (tipo, mensagem).
    """
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    row = _pedido(conn, codigo)
    tipo = dados.get("tipo")
    mensagem = dados.get("mensagem")
    erros = {}
    if not isinstance(tipo, str) or tipo not in TIPOS_EVENTO:
        erros["tipo"] = "Tipo de evento inválido."
    if mensagem is not None and not isinstance(mensagem, str):
        erros["mensagem"] = "Mensagem inválida."
        mensagem = None
    mensagem = (mensagem or "").strip()
    if len(mensagem) > MENSAGEM_MAX:
        erros["mensagem"] = f"A mensagem deve ter no máximo {MENSAGEM_MAX} caracteres."
    if row["status"] == "cancelado":
        erros["status"] = "O pedido está cancelado."
    if not erros and not mensagem:
        embarcacao = None
        if row["viagem_id"]:
            v = conn.execute("SELECT embarcacao FROM viagens WHERE id = ?", (row["viagem_id"],)).fetchone()
            embarcacao = v["embarcacao"] if v else None
        mensagem = mensagem_padrao(tipo, row["cidade"], embarcacao)
        if not mensagem:
            erros["mensagem"] = "Escreva a mensagem do evento."
    if erros:
        raise ErroValidacao(erros, "Revise o evento.")
    conn.execute("BEGIN IMMEDIATE")
    try:
        registrar_evento(conn, row["id"], tipo, mensagem)
        if junto is not None:
            junto(row)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    notificar(conn, row["codigo"], tipo, mensagem)
    return tipo, mensagem


def _validar_alteracoes(conn, dados):
    """codigo_rastreio / viagem_id enviados ao PATCH do pedido -> {coluna: valor}."""
    mudancas, erros = {}, {}
    if "codigo_rastreio" in dados:
        valor = dados["codigo_rastreio"]
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            mudancas["codigo_rastreio"] = None
        elif isinstance(valor, str) and _CODIGO_RASTREIO.fullmatch(cod := re.sub(r"\s+", "", valor).upper()):
            mudancas["codigo_rastreio"] = cod
        else:
            erros["codigo_rastreio"] = "Use de 4 a 40 letras, números ou hífens (ex.: AA123456789BR)."
    if "viagem_id" in dados:
        valor = dados["viagem_id"]
        if valor is None:
            mudancas["viagem_id"] = None
        elif (isinstance(valor, int) and not isinstance(valor, bool) and 0 < valor <= 2 ** 62
              and conn.execute("SELECT 1 FROM viagens WHERE id = ?", (valor,)).fetchone()):
            mudancas["viagem_id"] = valor
        else:
            erros["viagem_id"] = "Viagem não encontrada."
    return mudancas, erros


def atualizar_pedido_admin(conn, codigo, dados):
    """PATCH do painel: {status?, codigo_rastreio?, viagem_id?}. Tudo é validado antes de gravar; o código e a
    viagem são gravados antes do status, para o evento de "enviado" já sair com o barco."""
    from . import reservas  # reservas importa este módulo

    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    row = _pedido(conn, codigo)
    mudancas, erros = _validar_alteracoes(conn, dados)
    tem_status = "status" in dados or not mudancas
    novo = dados.get("status")
    if tem_status:
        if not isinstance(novo, str) or novo not in reservas.STATUS_PEDIDO:
            erros["status"] = "Status inválido."
        elif novo != row["status"] and novo not in reservas.TRANSICOES[row["status"]]:
            erros["status"] = (f"Um pedido “{reservas.STATUS_PEDIDO[row['status']]}” não pode passar para "
                               f"“{reservas.STATUS_PEDIDO[novo]}”.")
    if erros:
        raise ErroValidacao(erros)
    if mudancas:
        conn.execute(f"UPDATE pedidos SET {', '.join(f'{c} = ?' for c in mudancas)} WHERE id = ?",
                     [*mudancas.values(), row["id"]])
    if tem_status:
        reservas.atualizar_status(conn, row["codigo"], novo)


def _texto_aviso(row, ultimo):
    primeiro = (row["cliente_nome"] or "").split()[0] if row["cliente_nome"] else ""
    linhas = [f"Olá, {primeiro}! Novidade do seu pedido {row['codigo']} na Tipiti:", ultimo["mensagem"]]
    if row["codigo_rastreio"]:
        url = url_rastreio(row["codigo_rastreio"])
        linhas.append(f"Código de rastreio: {row['codigo_rastreio']}" + (f" — {url}" if url else ""))
    linhas.append(f"Acompanhe: {config.SITE_URL}/pedido/{row['codigo']}")
    return "\n".join(linhas)


def anexar(conn, pares, admin=False):
    """Completa os resumos de pedido [(row do pedido, resumo)] com rastreio, viagem e eventos (consultas em lote).

    No painel (admin=True) também `whatsapp_aviso`: o texto do último evento, pronto para mandar ao cliente.
    """
    if not pares:
        return
    ids = [row["id"] for row, _ in pares]
    eventos = {pid: [] for pid in ids}
    for i in range(0, len(ids), 500):
        lote = ids[i:i + 500]
        for e in conn.execute(
            f"""SELECT pedido_id, tipo, mensagem, criado_em FROM eventos_pedido
                WHERE pedido_id IN ({','.join('?' * len(lote))}) ORDER BY id DESC""",
            lote,
        ):
            eventos[e["pedido_id"]].append({"tipo": e["tipo"], "mensagem": e["mensagem"],
                                            "data": horario.iso_z(e["criado_em"])})
    ids_viagem = sorted({row["viagem_id"] for row, _ in pares if row["viagem_id"]})
    viagens_por_id = {}
    if ids_viagem:
        viagens_por_id = {
            v["id"]: viagens.viagem_dict(v) for v in conn.execute(
                f"SELECT * FROM viagens WHERE id IN ({','.join('?' * len(ids_viagem))})", ids_viagem)
        }
    for row, resumo in pares:
        resumo["codigo_rastreio"] = row["codigo_rastreio"]
        resumo["url_rastreio"] = url_rastreio(row["codigo_rastreio"])
        resumo["viagem"] = viagens_por_id.get(row["viagem_id"])
        resumo["eventos"] = eventos[row["id"]]
        if admin:
            resumo["whatsapp_aviso"] = _texto_aviso(row, eventos[row["id"]][0]) if eventos[row["id"]] else None


def aviso_whatsapp(conn, codigo):
    row = _pedido(conn, codigo)
    ultimo = conn.execute("SELECT mensagem FROM eventos_pedido WHERE pedido_id = ? ORDER BY id DESC LIMIT 1",
                          (row["id"],)).fetchone()
    return _texto_aviso(row, ultimo) if ultimo else None
