"""LGPD: solicitações do titular (cópia, exclusão, correção), exportação e anonimização dos dados.

A anonimização troca os dados pessoais dos pedidos e apaga os dados acessórios (endereços salvos, avise-me,
carrinhos, sessões, corpo dos e-mails), mas mantém valores, itens, datas, cidade e UF, que a legislação fiscal
manda guardar. A própria solicitação (com e-mail e CPF) fica guardada como prova do atendimento.

Também cobre: as mensagens dos eventos de rastreio dos pedidos (podem ter sido escritas à mão no painel; viram o
rótulo genérico do tipo), as encomendas ("Encomenda pra mim", pelo WhatsApp: nome, WhatsApp e cidade) e o cadastro
de revendedora com o mesmo CPF (nome, WhatsApp, CPF, Instagram, mensagem, código do link e token do painel) — este
só se ela não estiver ativa e não tiver comissão a receber; senão a anonimização inteira é recusada.
"""

import secrets
from datetime import timedelta

from . import horario, notificacoes, rastreio, revendedoras
from .ajustes import normalizar_whatsapp
from .validacao import ErroValidacao, NaoEncontrado, cpf_valido, email_valido, so_digitos

TIPOS = {"copia": "Cópia dos dados", "exclusao": "Exclusão dos dados", "correcao": "Correção dos dados"}
STATUS = {"aberta": "Aberta", "em_andamento": "Em andamento", "concluida": "Concluída"}
PRAZO_RESPOSTA_DIAS = 15
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
# pedidos nesses status ainda dependem do endereço e do contato do cliente
STATUS_EM_ANDAMENTO = ("aguardando_pagamento", "pago", "enviado")
# encomendas nesses status ainda dependem do contato do cliente
ENCOMENDAS_EM_ANDAMENTO = ("nova", "cotada", "aceita", "comprada")
# campos que nunca saem numa exportação (segredos de outras funcionalidades)
_CAMPOS_SECRETOS = ("token", "senha", "segredo", "hash")
# CPF de revendedora anonimizada (a coluna é única e obrigatória)
PREFIXO_CPF_ANONIMO = "anonimizada-"


def criar_solicitacao(conn, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    erros = {}
    tipo = dados.get("tipo")
    if tipo not in TIPOS:
        erros["tipo"] = "Escolha o tipo de solicitação."
    email = str(dados.get("email") or "").strip().lower()
    if not email_valido(email) or any(c in email for c in "\r\n"):
        erros["email"] = "Informe um e-mail válido."
    cpf = so_digitos(dados.get("cpf"))
    if not cpf_valido(cpf):
        erros["cpf"] = "Informe um CPF válido."
    mensagem = str(dados.get("mensagem") or "").strip()
    if len(mensagem) > 2000:
        erros["mensagem"] = "Use no máximo 2.000 caracteres."
    if erros:
        raise ErroValidacao(erros)
    agora = horario.agora_db()
    while True:
        protocolo = "LGPD-" + "".join(secrets.choice(_ALFABETO) for _ in range(8))
        if not conn.execute("SELECT 1 FROM solicitacoes_lgpd WHERE protocolo = ?", (protocolo,)).fetchone():
            break
    conn.execute("""INSERT INTO solicitacoes_lgpd (protocolo, tipo, email, cpf, mensagem, criado_em, atualizado_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""", (protocolo, tipo, email, cpf, mensagem, agora, agora))
    return {"protocolo": protocolo}


def _solicitacao_dict(r):
    prazo = (horario.de_db(r["criado_em"]) + timedelta(days=PRAZO_RESPOSTA_DIAS)).date().isoformat()
    return {
        "protocolo": r["protocolo"], "tipo": r["tipo"], "tipo_nome": TIPOS[r["tipo"]], "email": r["email"],
        "cpf": r["cpf"], "mensagem": r["mensagem"], "status": r["status"], "status_nome": STATUS[r["status"]],
        "resposta": r["resposta"], "prazo_resposta": prazo, "anonimizado_em": horario.iso_z(r["anonimizado_em"]),
        "criado_em": horario.iso_z(r["criado_em"]), "atualizado_em": horario.iso_z(r["atualizado_em"]),
    }


def _obter(conn, protocolo):
    row = conn.execute("SELECT * FROM solicitacoes_lgpd WHERE protocolo = ?", (str(protocolo).upper(),)).fetchone()
    if not row:
        raise NaoEncontrado("Solicitação não encontrada.")
    return row


def listar(conn, status=None):
    sql, params = "SELECT * FROM solicitacoes_lgpd", []
    if status:
        if status not in STATUS:
            raise ErroValidacao({"status": "Status inválido."})
        sql += " WHERE status = ?"
        params.append(status)
    return [_solicitacao_dict(r) for r in conn.execute(sql + " ORDER BY id DESC LIMIT 500", params).fetchall()]


def atualizar(conn, protocolo, dados):
    """Muda o status e/ou registra a resposta; com resposta nova, o titular recebe um e-mail."""
    row = _obter(conn, protocolo)
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    status = dados.get("status", row["status"])
    if status not in STATUS:
        raise ErroValidacao({"status": "Status inválido."})
    resposta = dados.get("resposta")
    if resposta is not None:
        resposta = str(resposta).strip()
        if len(resposta) > 5000:
            raise ErroValidacao({"resposta": "Use no máximo 5.000 caracteres."})
    conn.execute("UPDATE solicitacoes_lgpd SET status = ?, resposta = COALESCE(?, resposta), atualizado_em = ? "
                 "WHERE id = ?", (status, resposta, horario.agora_db(), row["id"]))
    if resposta and resposta != row["resposta"]:
        try:
            notificacoes.resposta_lgpd(conn, row["email"], row["protocolo"], STATUS[status], resposta)
        except ErroValidacao:
            pass
    return _solicitacao_dict(_obter(conn, protocolo))


# ---------------------------------------------------------------- exportação

def _limpo(row):
    return {k: row[k] for k in row.keys() if not any(s in k.lower() for s in _CAMPOS_SECRETOS)}


def _whatsapps(telefones):
    numeros = set()
    for t in telefones:
        try:
            n = normalizar_whatsapp(t)
        except ErroValidacao:
            continue
        if n:
            numeros.add(n)
    return sorted(numeros)


def _pedidos_do_titular(conn, email, cpf):
    return conn.execute("SELECT * FROM pedidos WHERE (cliente_email = ? OR cliente_cpf = ?) ORDER BY id",
                        (email, cpf)).fetchall()


def _em(lista):
    return ",".join("?" * len(lista)) or "NULL"


def _revendedora_do_titular(conn, cpf):
    return conn.execute("SELECT * FROM revendedoras WHERE cpf = ?", (cpf,)).fetchone()


def _contatos(conn, email, cpf):
    """(pedidos, ids, e-mails, WhatsApps, revendedora) do titular. O WhatsApp da revendedora com o mesmo CPF
    também identifica o titular (encomendas, avise-me, carrinhos)."""
    pedidos = _pedidos_do_titular(conn, email, cpf)
    revendedora = _revendedora_do_titular(conn, cpf)
    telefones = [p["cliente_telefone"] for p in pedidos] + ([revendedora["whatsapp"]] if revendedora else [])
    return (pedidos, [p["id"] for p in pedidos], sorted({email} | {p["cliente_email"] for p in pedidos}),
            _whatsapps(telefones), revendedora)


def exportar(conn, protocolo):
    """Tudo o que a loja guarda ligado ao e-mail/CPF da solicitação (JSON)."""
    s = _obter(conn, protocolo)
    email, cpf = s["email"], s["cpf"]
    pedidos, ids, emails_titular, whatsapps, revendedora = _contatos(conn, email, cpf)
    itens, eventos = {}, {}
    for i in conn.execute(f"SELECT * FROM itens_pedido WHERE pedido_id IN ({_em(ids)})", ids).fetchall():
        item = _limpo(i)
        item.pop("custo_unit_centavos", None)  # informação interna da loja, não dado pessoal
        itens.setdefault(i["pedido_id"], []).append(item)
    for e in conn.execute(f"SELECT pedido_id, tipo, mensagem, criado_em FROM eventos_pedido "
                          f"WHERE pedido_id IN ({_em(ids)}) ORDER BY id", ids).fetchall():
        eventos.setdefault(e["pedido_id"], []).append(
            {"tipo": e["tipo"], "mensagem": e["mensagem"], "data": horario.iso_z(e["criado_em"])})
    dados = {
        "protocolo": s["protocolo"],
        "gerado_em": horario.iso_z(horario.agora_db()),
        "titular": {"email": email, "cpf": cpf},
        # comissão de revendedora e dados internos do pedido não são dados pessoais do cliente
        "pedidos": [dict({k: v for k, v in _limpo(p).items() if not k.startswith("comissao")},
                         itens=itens.get(p["id"], []), eventos=eventos.get(p["id"], [])) for p in pedidos],
        "avaliacoes": [_limpo(r) for r in conn.execute(
            f"SELECT * FROM avaliacoes WHERE pedido_id IN ({_em(ids)})", ids).fetchall()],
        "enderecos_salvos": [_limpo(r) for r in conn.execute(
            f"SELECT * FROM enderecos_conta WHERE email IN ({_em(emails_titular)})", emails_titular).fetchall()],
        "avise_me": [_limpo(r) for r in conn.execute(
            f"""SELECT a.*, p.nome AS produto_nome FROM avise_me a JOIN produtos p ON p.id = a.produto_id
                WHERE a.email IN ({_em(emails_titular)}) OR a.whatsapp IN ({_em(whatsapps)})""",
            emails_titular + whatsapps).fetchall()],
        "carrinhos": [_limpo(r) for r in conn.execute(
            f"SELECT * FROM carrinhos WHERE whatsapp IN ({_em(whatsapps)}) OR pedido_id IN ({_em(ids)})",
            whatsapps + ids).fetchall()],
        "solicitacoes_lgpd": [_solicitacao_dict(r) for r in conn.execute(
            f"SELECT * FROM solicitacoes_lgpd WHERE email IN ({_em(emails_titular)}) OR cpf = ?",
            emails_titular + [cpf]).fetchall()],
        "emails_enviados": [dict(r, criado_em=horario.iso_z(r["criado_em"])) for r in conn.execute(
            f"SELECT id, tipo, para, assunto, status, criado_em FROM emails_saida WHERE para IN ({_em(emails_titular)})",
            emails_titular).fetchall()],
        "sessoes_minha_conta": conn.execute(
            f"SELECT COUNT(*) FROM sessoes_conta WHERE email IN ({_em(emails_titular)})", emails_titular).fetchone()[0],
    }
    dados["encomendas"] = [_limpo(r) for r in conn.execute(
        f"SELECT * FROM encomendas WHERE whatsapp IN ({_em(whatsapps)}) ORDER BY id", whatsapps)]
    dados["revendedora"] = None
    if revendedora:
        # sem o token do painel (_limpo); com as comissões dela, sem dados dos clientes que compraram com ela
        dados["revendedora"] = dict(_limpo(revendedora), comissoes=[
            {"pedido": r["codigo"], "data": horario.iso_z(r["criado_em"]), "status": r["status"],
             "comissao_centavos": r["comissao_centavos"], "paga_em": horario.iso_z(r["comissao_paga_em"])}
            for r in conn.execute("SELECT codigo, criado_em, status, comissao_centavos, comissao_paga_em "
                                  "FROM pedidos WHERE revendedora_id = ? ORDER BY id", (revendedora["id"],))])
    return dados


def _bloqueio_revendedora(conn, revendedora):
    """Motivo para não anonimizar a revendedora agora (ou None)."""
    if revendedora is None or revendedora["cpf"].startswith(PREFIXO_CPF_ANONIMO):
        return None
    if revendedora["status"] == "ativa":
        return ("O titular é revendedora ativa. Desative a revendedora no painel (e pague as comissões pendentes) "
                "antes de anonimizar.")
    a_receber = revendedoras._totais(conn, revendedora["id"])["a_receber_centavos"]
    aguardando = conn.execute("SELECT COUNT(*) FROM pedidos WHERE revendedora_id = ? AND comissao_centavos > 0 "
                              "AND status = 'aguardando_pagamento'", (revendedora["id"],)).fetchone()[0]
    if a_receber or aguardando:
        return ("O titular é revendedora com comissões a receber ou pedidos aguardando pagamento. Pague as "
                "comissões (Revendedoras → Pagar até) antes de anonimizar.")
    return None


# ---------------------------------------------------------------- anonimização

def anonimizar(conn, protocolo):
    s = _obter(conn, protocolo)
    email, cpf = s["email"], s["cpf"]
    conn.execute("BEGIN IMMEDIATE")
    try:
        pedidos, ids, emails_titular, whatsapps, revendedora = _contatos(conn, email, cpf)
        andamento = [p["codigo"] for p in pedidos if p["status"] in STATUS_EM_ANDAMENTO]
        if andamento:
            raise ErroValidacao({"pedidos": andamento}, "Há pedidos em andamento (" + ", ".join(andamento)
                                + "). Conclua a entrega ou cancele antes de anonimizar.")
        encomendas_abertas = [r["codigo"] for r in conn.execute(
            f"SELECT codigo FROM encomendas WHERE whatsapp IN ({_em(whatsapps)}) AND status IN "
            f"({_em(ENCOMENDAS_EM_ANDAMENTO)}) ORDER BY id", whatsapps + list(ENCOMENDAS_EM_ANDAMENTO))]
        if encomendas_abertas:
            raise ErroValidacao({"encomendas": encomendas_abertas},
                                "Há encomendas em andamento (" + ", ".join(encomendas_abertas)
                                + "). Conclua ou cancele antes de anonimizar.")
        motivo = _bloqueio_revendedora(conn, revendedora)
        if motivo:
            raise ErroValidacao({"revendedora": motivo}, motivo)
        agora = horario.agora_db()
        for p in pedidos:
            conn.execute(
                """UPDATE pedidos SET cliente_nome = 'Titular anonimizado', cliente_email = ?, cliente_cpf = '',
                       cliente_telefone = '', endereco = '', numero = '', complemento = '', bairro = '',
                       cep = substr(cep, 1, 5) || '000', anonimizado_em = ? WHERE id = ?""",
                (f"anonimizado-{p['id']}@anonimizado.invalid", agora, p["id"]))
        conn.execute(f"UPDATE avaliacoes SET nome_exibicao = 'Cliente' WHERE pedido_id IN ({_em(ids)})", ids)
        # mensagens de rastreio podem ter sido escritas à mão (ex.: "entregue para João"): viram o rótulo do tipo
        for tipo, rotulo in rastreio.TIPOS_EVENTO.items():
            conn.execute(f"UPDATE eventos_pedido SET mensagem = ? WHERE tipo = ? AND pedido_id IN ({_em(ids)})",
                         [rotulo + ".", tipo] + ids)
        encomendas_anonimizadas = conn.execute(
            f"""UPDATE encomendas SET nome = 'Titular anonimizado', whatsapp = '', cidade = '',
                   atualizado_em = datetime('now') WHERE whatsapp IN ({_em(whatsapps)})""", whatsapps).rowcount
        revendedora_anonimizada = False
        if revendedora is not None and not revendedora["cpf"].startswith(PREFIXO_CPF_ANONIMO):
            conn.execute(
                """UPDATE revendedoras SET nome = 'Revendedora anonimizada', whatsapp = '', cpf = ?, instagram = '',
                       mensagem = '', codigo = NULL, token_acesso = NULL, status = 'inativa' WHERE id = ?""",
                (f"{PREFIXO_CPF_ANONIMO}{revendedora['id']}", revendedora["id"]))
            # o cupom com o código dela (nome + cidade) deixa de valer
            conn.execute("UPDATE cupons SET ativo = 0 WHERE revendedora_id = ?", (revendedora["id"],))
            revendedora_anonimizada = True
        apagados = {
            "enderecos_salvos": conn.execute(
                f"DELETE FROM enderecos_conta WHERE email IN ({_em(emails_titular)})", emails_titular).rowcount,
            "avise_me": conn.execute(
                f"DELETE FROM avise_me WHERE email IN ({_em(emails_titular)}) OR whatsapp IN ({_em(whatsapps)})",
                emails_titular + whatsapps).rowcount,
            "carrinhos": conn.execute(
                f"DELETE FROM carrinhos WHERE whatsapp IN ({_em(whatsapps)}) OR pedido_id IN ({_em(ids)})",
                whatsapps + ids).rowcount,
            "sessoes": conn.execute(
                f"DELETE FROM sessoes_conta WHERE email IN ({_em(emails_titular)})", emails_titular).rowcount,
            "links": conn.execute(
                f"DELETE FROM links_conta WHERE email IN ({_em(emails_titular)})", emails_titular).rowcount,
            # o registro do envio fica; o destinatário e o conteúdo, não
            "emails": conn.execute(
                f"""UPDATE emails_saida SET para = 'anonimizado@anonimizado.invalid', texto = '', html = '',
                       status = CASE WHEN status IN ('pendente', 'enviando') THEN 'falhou' ELSE status END
                    WHERE para IN ({_em(emails_titular)})""", emails_titular).rowcount,
        }
        conn.execute("UPDATE solicitacoes_lgpd SET anonimizado_em = ?, atualizado_em = ? WHERE id = ?",
                     (agora, agora, s["id"]))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {"protocolo": s["protocolo"], "pedidos_anonimizados": len(pedidos),
            "encomendas_anonimizadas": encomendas_anonimizadas, "revendedora_anonimizada": revendedora_anonimizada,
            "apagados": apagados}
