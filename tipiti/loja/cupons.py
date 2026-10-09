"""Cupons de desconto: percentual, valor fixo ou frete grátis, com mínimo, validade, limite de usos e
opção "só na primeira compra". O uso é contado dentro da transação do pedido."""

import re
import sqlite3

from . import horario
from .validacao import ErroValidacao, NaoEncontrado, so_digitos

TIPOS = ("pct", "valor", "frete")
PCT_MAX = 90
INTEIRO_MAX = 10 ** 9
_CODIGO = re.compile(r"[A-Z0-9-]{3,20}")

# Cupom ativo, dentro da validade e com usos sobrando — agora.
SQL_VIGENTE = """ativo = 1 AND (inicio IS NULL OR inicio <= datetime('now')) AND (fim IS NULL OR fim > datetime('now'))
                 AND (limite_usos IS NULL OR usos < limite_usos)"""

_SELECT = f"""SELECT *, inicio > datetime('now') AS futuro, fim <= datetime('now') AS expirado,
                     ({SQL_VIGENTE}) AS vigente FROM cupons"""


def formatar_reais(centavos):
    """12345 -> 'R$ 123,45'; 123456789 -> 'R$ 1.234.567,89'."""
    reais, resto = divmod(int(centavos), 100)
    return f"R$ {reais:,}".replace(",", ".") + f",{resto:02d}"


def normalizar_codigo(codigo):
    return str(codigo or "").strip().upper()


def descricao(c):
    """Texto para o cliente: "10% de desconto", "R$ 15,00 de desconto", "Frete grátis" (+ mínimo, primeira compra)."""
    if c["tipo"] == "pct":
        texto = f"{c['valor']}% de desconto"
    elif c["tipo"] == "valor":
        texto = f"{formatar_reais(c['valor'])} de desconto"
    else:
        texto = "Frete grátis"
    if c["minimo_centavos"] > 0:
        texto += f" acima de {formatar_reais(c['minimo_centavos'])}"
    if c["so_primeira_compra"]:
        texto += " na primeira compra"
    return texto


def desconto(cupom, subtotal):
    if cupom["tipo"] == "pct":
        return subtotal * cupom["valor"] // 100
    if cupom["tipo"] == "valor":
        return min(cupom["valor"], subtotal)
    return 0


def ja_comprou(conn, cpf):
    return conn.execute("SELECT 1 FROM pedidos WHERE cliente_cpf = ? AND status != 'cancelado' LIMIT 1",
                        (so_digitos(cpf),)).fetchone() is not None


def avaliar(conn, codigo, subtotal, cpf=None):
    """Confere o cupom para este carrinho. Devolve (cupom, None) ou (None, mensagem de erro).

    Sem CPF (ou com CPF incompleto) a regra de primeira compra só é conferida ao fechar o pedido.
    """
    codigo = normalizar_codigo(codigo)
    if not codigo:
        return None, None
    c = conn.execute(_SELECT + " WHERE codigo = ?", (codigo,)).fetchone() if _CODIGO.fullmatch(codigo) else None
    if not c or not c["ativo"]:
        return None, "Cupom inválido. Confira o código."
    if c["futuro"]:
        return None, "Este cupom ainda não está valendo."
    if c["expirado"]:
        return None, "Este cupom expirou."
    if c["limite_usos"] is not None and c["usos"] >= c["limite_usos"]:
        return None, "Este cupom já atingiu o limite de usos."
    if subtotal < c["minimo_centavos"]:
        return None, (f"Faltam {formatar_reais(c['minimo_centavos'] - subtotal)} para usar este cupom "
                      f"(compras a partir de {formatar_reais(c['minimo_centavos'])}).")
    if c["so_primeira_compra"] and len(so_digitos(cpf)) == 11 and ja_comprou(conn, cpf):
        return None, "Este cupom é válido só na primeira compra."
    return c, None


def registrar_uso(conn, codigo):
    """Conta um uso, respeitando o limite (chamar dentro da transação do pedido). False se o limite acabou."""
    return conn.execute(
        "UPDATE cupons SET usos = usos + 1 WHERE codigo = ? AND (limite_usos IS NULL OR usos < limite_usos)",
        (codigo,),
    ).rowcount == 1


def devolver_uso(conn, codigo):
    """Pedido cancelado: o uso do cupom volta."""
    if codigo:
        conn.execute("UPDATE cupons SET usos = usos - 1 WHERE codigo = ? AND usos > 0", (codigo,))


def cupom_destaque(conn):
    c = conn.execute(f"SELECT * FROM cupons WHERE destaque = 1 AND {SQL_VIGENTE} LIMIT 1").fetchone()
    return {"codigo": c["codigo"], "descricao": descricao(c)} if c else None


# ---------------------------------------------------------------- painel

def _cupom(c):
    return {
        "codigo": c["codigo"],
        "tipo": c["tipo"],
        "valor": c["valor"],
        "minimo_centavos": c["minimo_centavos"],
        "inicio": horario.iso_z(c["inicio"]),
        "fim": horario.iso_z(c["fim"]),
        "limite_usos": c["limite_usos"],
        "usos": c["usos"],
        "so_primeira_compra": bool(c["so_primeira_compra"]),
        "ativo": bool(c["ativo"]),
        "destaque": bool(c["destaque"]),
        "descricao": descricao(c),
        "vigente": bool(c["vigente"]),
        "criado_em": horario.iso_z(c["criado_em"]),
    }


def listar(conn):
    return [_cupom(c) for c in conn.execute(_SELECT + " ORDER BY ativo DESC, id DESC").fetchall()]


def obter(conn, codigo):
    c = conn.execute(_SELECT + " WHERE codigo = ?", (normalizar_codigo(codigo),)).fetchone()
    if not c:
        raise NaoEncontrado("Cupom não encontrado.")
    return _cupom(c)


def _inteiro(valor, minimo):
    return not isinstance(valor, bool) and isinstance(valor, int) and minimo <= valor <= INTEIRO_MAX


def _validar(c):
    """Valida o cupom completo (já com os campos enviados aplicados). Devolve os valores a gravar."""
    erros = {}
    if c["tipo"] not in TIPOS:
        erros["tipo"] = "Escolha o tipo: porcentagem, valor fixo ou frete grátis."
    elif c["tipo"] == "frete":
        c["valor"] = 0
    elif c["tipo"] == "pct" and not (_inteiro(c["valor"], 1) and c["valor"] <= PCT_MAX):
        erros["valor"] = f"Use uma porcentagem inteira de 1 a {PCT_MAX}."
    elif c["tipo"] == "valor" and not _inteiro(c["valor"], 1):
        erros["valor"] = "Informe o valor do desconto em centavos (maior que zero)."
    if c["minimo_centavos"] in (None, ""):
        c["minimo_centavos"] = 0
    if not _inteiro(c["minimo_centavos"], 0):
        erros["minimo_centavos"] = "Use um valor inteiro em centavos, zero ou mais."
    if c["limite_usos"] == "":
        c["limite_usos"] = None
    if c["limite_usos"] is not None and not _inteiro(c["limite_usos"], 1):
        erros["limite_usos"] = "Use um número inteiro de usos (1 ou mais), ou deixe vazio para ilimitado."
    for campo in ("inicio", "fim"):
        if c[campo] in (None, ""):
            c[campo] = None
            continue
        try:
            c[campo] = horario.ler_data(c[campo])
        except (TypeError, ValueError):
            erros[campo] = "Data inválida."
    if "inicio" not in erros and "fim" not in erros and c["inicio"] and c["fim"] and c["fim"] <= c["inicio"]:
        erros["fim"] = "O fim precisa ser depois do início."
    for campo in ("so_primeira_compra", "ativo", "destaque"):
        c[campo] = 1 if c[campo] else 0
    if erros:
        raise ErroValidacao(erros, "Revise o cupom.")
    return c


_CAMPOS = ("tipo", "valor", "minimo_centavos", "inicio", "fim", "limite_usos", "so_primeira_compra", "ativo",
           "destaque")


def _gravar(conn, c, novo):
    conn.execute("BEGIN IMMEDIATE")
    try:
        if c["destaque"]:  # só um cupom em destaque por vez
            conn.execute("UPDATE cupons SET destaque = 0 WHERE codigo != ?", (c["codigo"],))
        valores = [c[campo] for campo in _CAMPOS]
        if novo:
            conn.execute(f"INSERT INTO cupons (codigo, {', '.join(_CAMPOS)}) VALUES (?{', ?' * len(_CAMPOS)})",
                         (c["codigo"], *valores))
        else:
            conn.execute(f"UPDATE cupons SET {', '.join(f'{campo} = ?' for campo in _CAMPOS)} WHERE codigo = ?",
                         (*valores, c["codigo"]))
        conn.execute("COMMIT")
    except sqlite3.IntegrityError:
        conn.execute("ROLLBACK")
        raise ErroValidacao({"codigo": "Já existe um cupom com esse código."})
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return obter(conn, c["codigo"])


def criar(conn, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    codigo = normalizar_codigo(dados.get("codigo"))
    if not _CODIGO.fullmatch(codigo):
        raise ErroValidacao({"codigo": "Use de 3 a 20 letras, números ou hífens (ex.: BEMVINDO10)."})
    if conn.execute("SELECT 1 FROM cupons WHERE codigo = ?", (codigo,)).fetchone():
        raise ErroValidacao({"codigo": "Já existe um cupom com esse código."})
    padrao = {"tipo": None, "valor": None, "minimo_centavos": 0, "inicio": None, "fim": None, "limite_usos": None,
              "so_primeira_compra": False, "ativo": True, "destaque": False}
    c = {campo: dados.get(campo, padrao[campo]) for campo in _CAMPOS}
    return _gravar(conn, _validar({**c, "codigo": codigo}), novo=True)


def atualizar(conn, codigo, dados):
    """Altera qualquer campo, menos o código e o número de usos."""
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    atual = conn.execute("SELECT * FROM cupons WHERE codigo = ?", (normalizar_codigo(codigo),)).fetchone()
    if not atual:
        raise NaoEncontrado("Cupom não encontrado.")
    if "codigo" in dados and normalizar_codigo(dados["codigo"]) != atual["codigo"]:
        raise ErroValidacao({"codigo": "O código do cupom não pode ser alterado."})
    if "usos" in dados and dados["usos"] != atual["usos"]:
        raise ErroValidacao({"usos": "O número de usos é contado pelos pedidos."})
    c = {campo: dados.get(campo, atual[campo]) for campo in _CAMPOS}
    return _gravar(conn, _validar({**c, "codigo": atual["codigo"]}), novo=False)
