"""Calendário de barcos: viagens por zona de frete, próximas saídas e o "próximo barco" da cotação de frete.

Cada viagem pertence a uma zona de `frete.py` (ex.: "parintins", "santarem", "interior-am"). Os horários ficam em
UTC no banco e saem em ISO com Z; uma data pura ("2026-10-20") enviada pelo painel vale como 00:00 de Manaus.
"""

import re
from datetime import date, datetime, timedelta

from . import config, frete, horario
from .validacao import ErroValidacao, NaoEncontrado

# id da zona -> nome (a primeira faixa de cada id dá o nome)
ZONAS = {}
for _z in frete.ZONAS:
    ZONAS.setdefault(_z[2], _z[3])

PROXIMAS_PUBLICAS = 5
_DATA_PURA = re.compile(r"\d{4}-\d{2}-\d{2}")
_CAMPOS = ("zona", "embarcacao", "saida", "chegada_prevista", "observacao", "ativo")


def _momento(valor):
    """Texto do banco (UTC) para uma data/hora enviada; ValueError se inválida."""
    if isinstance(valor, str) and _DATA_PURA.fullmatch(valor.strip()):
        d = date.fromisoformat(valor.strip())
        texto = horario.texto_db(datetime(d.year, d.month, d.day, tzinfo=horario.FUSO_LOJA))
    else:
        try:
            texto = horario.ler_data(valor)
        except OverflowError:
            raise ValueError("data fora do intervalo")
    if not "2000" <= texto[:4] <= "2100":
        raise ValueError("data fora do intervalo")
    return texto


def data_manaus(texto_db):
    """'2026-10-21 03:00:00' (UTC) -> '2026-10-20' (data em Manaus)."""
    return horario.de_db(texto_db).astimezone(horario.FUSO_LOJA).date().isoformat()


def viagem_dict(row):
    return {
        "id": row["id"],
        "zona": row["zona"],
        "zona_nome": ZONAS.get(row["zona"], row["zona"]),
        "embarcacao": row["embarcacao"],
        "saida": horario.iso_z(row["saida"]),
        "chegada_prevista": horario.iso_z(row["chegada_prevista"]),
        "observacao": row["observacao"],
        "ativo": bool(row["ativo"]),
    }


def _validar(v):
    erros = {}
    if v["zona"] not in ZONAS:
        erros["zona"] = "Escolha uma zona de entrega válida."
    v["embarcacao"] = str(v["embarcacao"] or "").strip()
    if not 2 <= len(v["embarcacao"]) <= 80:
        erros["embarcacao"] = "Informe o nome da embarcação (2 a 80 caracteres)."
    for campo in ("saida", "chegada_prevista"):
        try:
            v[campo] = _momento(v[campo])
        except (TypeError, ValueError):
            erros[campo] = "Data inválida."
    if "saida" not in erros and "chegada_prevista" not in erros and v["chegada_prevista"] <= v["saida"]:
        erros["chegada_prevista"] = "A chegada precisa ser depois da saída."
    v["observacao"] = str(v["observacao"] or "").strip()
    if len(v["observacao"]) > 300:
        erros["observacao"] = "A observação deve ter no máximo 300 caracteres."
    if not isinstance(v["ativo"], bool) and v["ativo"] not in (0, 1):
        erros["ativo"] = "Use verdadeiro ou falso."
    v["ativo"] = 1 if v["ativo"] else 0
    if erros:
        raise ErroValidacao(erros, "Revise a viagem.")
    return v


def obter(conn, viagem_id):
    row = conn.execute("SELECT * FROM viagens WHERE id = ?", (viagem_id,)).fetchone()
    if not row:
        raise NaoEncontrado("Viagem não encontrada.")
    return viagem_dict(row)


def criar(conn, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    padrao = {"zona": None, "embarcacao": "", "saida": None, "chegada_prevista": None, "observacao": "",
              "ativo": True}
    v = _validar({c: dados.get(c, padrao[c]) for c in _CAMPOS})
    cur = conn.execute(f"INSERT INTO viagens ({', '.join(_CAMPOS)}) VALUES ({', '.join('?' * len(_CAMPOS))})",
                       [v[c] for c in _CAMPOS])
    return obter(conn, cur.lastrowid)


def atualizar(conn, viagem_id, dados):
    """Altera qualquer campo. Para tirar uma viagem do calendário, use ativo = false (o histórico dos pedidos fica)."""
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    atual = conn.execute("SELECT * FROM viagens WHERE id = ?", (viagem_id,)).fetchone()
    if not atual:
        raise NaoEncontrado("Viagem não encontrada.")
    base = {c: atual[c] for c in _CAMPOS}
    base["saida"], base["chegada_prevista"] = horario.iso_z(atual["saida"]), horario.iso_z(atual["chegada_prevista"])
    v = _validar({c: dados.get(c, base[c]) for c in _CAMPOS})
    conn.execute(f"UPDATE viagens SET {', '.join(f'{c} = ?' for c in _CAMPOS)} WHERE id = ?",
                 [v[c] for c in _CAMPOS] + [viagem_id])
    return obter(conn, viagem_id)


def listar_admin(conn):
    """Todas as viagens (próximas primeiro, depois as passadas), com quantos pedidos cada uma leva."""
    agora = horario.texto_db(horario.agora())
    rows = conn.execute(
        """SELECT v.*, (SELECT COUNT(*) FROM pedidos p WHERE p.viagem_id = v.id AND p.status != 'cancelado') AS n
           FROM viagens v
           ORDER BY v.saida < ?, CASE WHEN v.saida >= ? THEN v.saida END, v.saida DESC, v.id
           LIMIT 500""",
        (agora, agora),
    ).fetchall()
    return [{**viagem_dict(r), "pedidos": r["n"]} for r in rows]


def proximas(conn, zona=None, limite=PROXIMAS_PUBLICAS):
    """Próximas saídas ativas e futuras. Sem zona: as próximas de todas as zonas (até 10 por zona)."""
    agora = horario.texto_db(horario.agora())
    if zona is not None:
        if zona not in ZONAS:
            raise ErroValidacao({"zona": "Zona de entrega inválida."})
        rows = conn.execute(
            "SELECT * FROM viagens WHERE zona = ? AND ativo = 1 AND saida > ? ORDER BY saida, id LIMIT ?",
            (zona, agora, limite),
        ).fetchall()
        return [viagem_dict(r) for r in rows]
    rows = conn.execute(
        """SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY zona ORDER BY saida, id) AS n
                          FROM viagens WHERE ativo = 1 AND saida > ?)
           WHERE n <= 10 ORDER BY saida, id""",
        (agora,),
    ).fetchall()
    return [viagem_dict(r) for r in rows]


def inicio_do_envio(previsao_envio=None, agora=None):
    """Primeiro momento em que o pedido pode embarcar: agora + manuseio, ou o dia de `previsao_envio`
    (pré-venda, 00:00 de Manaus) se for depois. `previsao_envio` é opcional e pode vir inválido (é ignorado)."""
    inicio = (agora or horario.agora()) + timedelta(days=config.PRAZO_MANUSEIO_DIAS)
    if previsao_envio:
        try:
            d = date.fromisoformat(str(previsao_envio)[:10])
        except ValueError:
            return inicio
        inicio = max(inicio, datetime(d.year, d.month, d.day, tzinfo=horario.FUSO_LOJA))
    return inicio


def proximo_barco(conn, zona, previsao_envio=None, agora=None):
    """A primeira viagem ativa da zona que sai depois do manuseio (e da previsão de envio, se houver), ou None."""
    if zona not in ZONAS:
        return None
    a_partir = horario.texto_db(inicio_do_envio(previsao_envio, agora))
    return conn.execute(
        "SELECT * FROM viagens WHERE zona = ? AND ativo = 1 AND saida >= ? ORDER BY saida, id LIMIT 1",
        (zona, a_partir),
    ).fetchone()


def anexar_ao_frete(conn, cotacao_frete, previsao_envio=None, agora=None):
    """Acrescenta `proximo_barco` e `chegada_estimada` (data em Manaus) à cotação de frete; None sem barco."""
    if not cotacao_frete:
        return cotacao_frete
    row = proximo_barco(conn, cotacao_frete.get("zona"), previsao_envio, agora)
    cotacao_frete["proximo_barco"] = {
        "embarcacao": row["embarcacao"],
        "saida": horario.iso_z(row["saida"]),
        "chegada_prevista": horario.iso_z(row["chegada_prevista"]),
    } if row else None
    cotacao_frete["chegada_estimada"] = data_manaus(row["chegada_prevista"]) if row else None
    return cotacao_frete
