"""Histórico do painel: quem fez o quê, em quê, de onde e quando. Toda escrita no admin passa por aqui."""

import json

from . import horario
from .validacao import ErroValidacao

# Campos que nunca vão para o histórico (senhas, códigos, tokens, fotos em base64)
_OCULTOS = ("senha", "nova", "atual", "codigo_2fa", "token", "sessao", "segredo", "dados", "miniatura")
DETALHES_MAX = 2000
POR_PAGINA_MAX = 200


def _limpar(valor, chave=""):
    if any(o in str(chave).lower() for o in _OCULTOS) and chave != "codigos":
        return "***"
    if isinstance(valor, dict):
        return {k: _limpar(v, k) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_limpar(v) for v in valor[:50]]
    return valor


def registrar(conn, ator, acao, alvo="", detalhes=None, ip=""):
    if isinstance(detalhes, (dict, list)):
        texto = json.dumps(_limpar(detalhes), ensure_ascii=False)
    else:
        texto = str(detalhes or "")
    conn.execute(
        "INSERT INTO historico (usuario_id, usuario_nome, acao, alvo, detalhes, ip, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ((ator or {}).get("id"), (ator or {}).get("nome") or "—", str(acao)[:80], str(alvo)[:200],
         texto[:DETALHES_MAX], str(ip)[:64], horario.agora_db()),
    )


def listar(conn, usuario=None, alvo=None, pagina=1, por_pagina=50):
    where, params = [], []
    if usuario not in (None, ""):
        if str(usuario) == "token":
            where.append("usuario_id IS NULL")
        elif str(usuario).isdigit():
            where.append("usuario_id = ?")
            params.append(int(usuario))
        else:
            raise ErroValidacao({"usuario": "Use o id do usuário ou \"token\"."})
    if alvo:
        termo = str(alvo)[:200].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("alvo LIKE ? ESCAPE '\\'")
        params.append(f"%{termo}%")
    filtro = (" WHERE " + " AND ".join(where)) if where else ""
    try:
        pagina = max(1, int(pagina or 1))
        por_pagina = min(POR_PAGINA_MAX, max(1, int(por_pagina or 50)))
    except (TypeError, ValueError):
        raise ErroValidacao({"pagina": "Página inválida."})
    total = conn.execute(f"SELECT COUNT(*) FROM historico{filtro}", params).fetchone()[0]
    rows = conn.execute(f"SELECT * FROM historico{filtro} ORDER BY id DESC LIMIT ? OFFSET ?",
                        (*params, por_pagina, (pagina - 1) * por_pagina)).fetchall()
    itens = []
    for r in rows:
        try:
            detalhes = json.loads(r["detalhes"]) if r["detalhes"] else None
        except ValueError:
            detalhes = r["detalhes"]
        itens.append({"id": r["id"], "usuario": {"id": r["usuario_id"], "nome": r["usuario_nome"]},
                      "acao": r["acao"], "alvo": r["alvo"], "detalhes": detalhes, "ip": r["ip"],
                      "data": horario.iso_z(r["criado_em"])})
    return {"itens": itens, "pagina": pagina, "por_pagina": por_pagina, "total": total}
