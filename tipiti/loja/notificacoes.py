"""E-mails ao cliente (pedido, status/rastreio, Minha conta, avise-me, LGPD) e ganchos chamados pelos pedidos.

Os ganchos nunca derrubam a operação principal: um problema aqui é registrado no log e o pedido segue.
"""

import logging

from . import ajustes, config, emails
from .cupons import formatar_reais

log = logging.getLogger("tipiti.notificacoes")

NOMES_EVENTO = {
    "pago": "Pagamento confirmado",
    "separado": "Pedido separado",
    "embarcado": "Pedido embarcado",
    "chegou_porto": "Chegou ao porto",
    "saiu_entrega": "Saiu para entrega",
    "entregue": "Pedido entregue",
    "outro": "Atualização do pedido",
}


def _seguro(func):
    def envolvida(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:  # noqa: BLE001 — e-mail é acessório: nunca desfaz o pedido
            log.exception("Falha ao preparar e-mail (%s)", func.__name__)
            return None
    envolvida.__name__ = func.__name__
    return envolvida


def _primeiro_nome(nome):
    return (str(nome or "").split() or ["cliente"])[0]


def _pix_copia_e_cola(conn, codigo):
    """Pix copia e cola do pedido, se o módulo de Pix (rodada 2) existir. Senão, None.

    Ponto de integração: na fusão com a rodada 2, apontar para a função do módulo `pix`.
    """
    try:
        from . import pix  # type: ignore[attr-defined]
    except ImportError:
        return None
    for nome in ("copia_e_cola_do_pedido", "pix_do_pedido", "obter_pix_pedido", "dados_pix"):
        funcao = getattr(pix, nome, None)
        if callable(funcao):
            try:
                r = funcao(conn, codigo)
            except Exception:  # noqa: BLE001 — Pix não configurado, pedido não é Pix…
                return None
            return r.get("copia_e_cola") if isinstance(r, dict) else r
    return None


@_seguro
def pedido_criado(conn, codigo):
    p = conn.execute("SELECT * FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()
    if not p:
        return
    itens = conn.execute("SELECT nome, variacao_nome, quantidade, preco_unit_centavos FROM itens_pedido "
                         "WHERE pedido_id = ? ORDER BY id", (p["id"],)).fetchall()
    link = f"{config.SITE_URL}/pedido/{codigo}"
    linhas = [f"- {i['quantidade']}x {i['nome']}{' (' + i['variacao_nome'] + ')' if i['variacao_nome'] else ''}"
              f" — {formatar_reais(i['preco_unit_centavos'] * i['quantidade'])}" for i in itens]
    pagamento = {"pix": "Pix", "cartao": "Cartão de crédito", "boleto": "Boleto"}.get(p["pagamento"], p["pagamento"])
    if p["parcelas"] and p["parcelas"] > 1:
        pagamento += f" em {p['parcelas']}x"
    valores = [f"Subtotal: {formatar_reais(p['subtotal_centavos'])}"]
    if p["desconto_cupom_centavos"]:
        valores.append(f"Cupom {p['cupom_codigo']}: −{formatar_reais(p['desconto_cupom_centavos'])}")
    if p["desconto_centavos"]:
        valores.append(f"Desconto no Pix: −{formatar_reais(p['desconto_centavos'])}")
    valores.append("Frete: " + (formatar_reais(p["frete_centavos"]) if p["frete_centavos"] else "grátis"))
    valores.append(f"Total: {formatar_reais(p['total_centavos'])}")
    pix = []
    if p["pagamento"] == "pix":
        copia = _pix_copia_e_cola(conn, codigo)
        chave = ajustes.obter(conn)["chave_pix"]
        if copia:
            pix = ["Pix copia e cola (cole no app do banco):", copia]
        elif chave:
            pix = [f"Chave Pix: {chave} (valor: {formatar_reais(p['total_centavos'])})"]
        pix.append(f"Os produtos ficam reservados por {config.PRAZO_RESERVA_HORAS} horas aguardando o pagamento.")
    paragrafos = [
        f"Oi, {_primeiro_nome(p['cliente_nome'])}! Recebemos o seu pedido {codigo}.",
        "Itens:", *linhas, *valores,
        f"Pagamento: {pagamento}.", *pix,
        f"Prazo de entrega: até {p['prazo_dias']} dias úteis após a confirmação do pagamento "
        f"({p['cidade']} - {p['uf']}).",
        f"Acompanhe o pedido: {link}",
        f"Trocas e devoluções: {config.SITE_URL}/trocas — você pode desistir em até 7 dias do recebimento.",
    ]
    emails.enfileirar(conn, p["cliente_email"], f"Pedido {codigo} recebido — Tipiti", "\n".join(paragrafos),
                      emails.html_simples(f"Pedido {codigo} recebido", paragrafos, ("Ver meu pedido", link)),
                      tipo="pedido", validade_horas=72)


@_seguro
def status_mudou(conn, codigo, novo_status):
    from .reservas import STATUS_PEDIDO
    p = conn.execute("SELECT cliente_nome, cliente_email FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()
    if not p or novo_status not in STATUS_PEDIDO:
        return
    link = f"{config.SITE_URL}/pedido/{codigo}"
    nome = STATUS_PEDIDO[novo_status]
    paragrafos = [f"Oi, {_primeiro_nome(p['cliente_nome'])}! O seu pedido {codigo} agora está: {nome}.",
                  f"Acompanhe: {link}"]
    if novo_status == "cancelado":
        paragrafos.insert(1, "Se você já pagou ou acha que foi um engano, responda este e-mail ou fale com a gente "
                             "pelo WhatsApp.")
    emails.enfileirar(conn, p["cliente_email"], f"Pedido {codigo}: {nome} — Tipiti", "\n".join(paragrafos),
                      emails.html_simples(f"Pedido {codigo}: {nome}", paragrafos, ("Ver meu pedido", link)),
                      tipo="status", validade_horas=72)


@_seguro
def evento_pedido(conn, codigo, tipo, mensagem=None):
    """Evento de rastreio (ex.: "separado", "embarcado"). A rodada 2 pode chamar este gancho ao criar eventos."""
    p = conn.execute("SELECT cliente_nome, cliente_email FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()
    if not p:
        return
    titulo = NOMES_EVENTO.get(tipo, NOMES_EVENTO["outro"])
    link = f"{config.SITE_URL}/pedido/{codigo}"
    paragrafos = [f"Oi, {_primeiro_nome(p['cliente_nome'])}! Novidade no pedido {codigo}: {titulo}."]
    if mensagem:
        paragrafos.append(str(mensagem)[:500])
    paragrafos.append(f"Acompanhe: {link}")
    emails.enfileirar(conn, p["cliente_email"], f"Pedido {codigo}: {titulo} — Tipiti", "\n".join(paragrafos),
                      emails.html_simples(f"Pedido {codigo}: {titulo}", paragrafos, ("Ver meu pedido", link)),
                      tipo="evento", validade_horas=72)


def link_conta(conn, email, token):
    link = f"{config.SITE_URL}/conta#{token}"
    paragrafos = ["Use o link abaixo para entrar na sua conta da Tipiti e ver os seus pedidos.",
                  link, "O link vale por 30 minutos e só pode ser usado uma vez.",
                  "Se não foi você que pediu, é só ignorar este e-mail."]
    emails.enfileirar(conn, email, "Seu link de acesso — Tipiti", "\n".join(paragrafos),
                      emails.html_simples("Seu link de acesso", paragrafos[:1] + paragrafos[2:], ("Entrar", link)),
                      tipo="conta", validade_horas=0.5)


def avise_me(conn, email, nome, produto_nome, variacao_nome, slug):
    link = f"{config.SITE_URL}/produto/{slug}"
    item = produto_nome + (f" ({variacao_nome})" if variacao_nome else "")
    paragrafos = [f"Oi, {_primeiro_nome(nome) if nome else 'tudo bem'}! Chegou: {item} está disponível de novo.",
                  f"Garanta o seu: {link}", "As unidades são limitadas."]
    emails.enfileirar(conn, email, f"Chegou: {item[:120]} — Tipiti", "\n".join(paragrafos),
                      emails.html_simples("Chegou o que você esperava", paragrafos, ("Ver produto", link)),
                      tipo="avise_me", validade_horas=72)


def resposta_lgpd(conn, email, protocolo, status_nome, resposta):
    paragrafos = [f"Sobre a sua solicitação {protocolo} (LGPD): {status_nome}.", str(resposta)[:5000],
                  f"Política de privacidade: {config.SITE_URL}/privacidade"]
    emails.enfileirar(conn, email, f"Solicitação {protocolo} — Tipiti", "\n\n".join(paragrafos),
                      emails.html_simples(f"Solicitação {protocolo}", paragrafos), tipo="lgpd")
