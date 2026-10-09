"""Usuários do painel: senhas (PBKDF2-SHA256), sessões, 2FA (TOTP), papéis e filtro de dados para operadores.

- Senha: PBKDF2-HMAC-SHA256 com ITERACOES e sal aleatório de 16 bytes; comparação em tempo constante.
- Sessão: secrets.token_urlsafe(32); no banco fica só o SHA-256. Expira em 12 h, renovada a cada uso.
  Trocar a senha ou desativar o usuário encerra as sessões dele.
- O TIPITI_ADMIN_TOKEN continua valendo como acesso de emergência, com papel de dono.
- Papéis: "dono" acessa tudo; "operador" só as rotas permitidas (OPERADOR_PODE ou papel="operador" na @rota) e
  nunca recebe custo, lucro, margem ou comissão (filtrar_para_operador).
"""

import base64
import hashlib
import hmac
import re
import secrets

from . import horario, qrcode, totp
from .validacao import ErroValidacao, NaoEncontrado, email_valido

ITERACOES = 600_000
SESSAO_HORAS = 12
RENOVAR_APOS_MIN = 5
SENHA_MIN = 10
SENHA_MAX = 200
PAPEIS = ("dono", "operador")

ATOR_TOKEN = {"id": None, "nome": "Acesso de emergência (token)", "login": None, "papel": "dono",
              "totp_ativo": False, "via_token": True}

# Rotas do painel que o operador pode usar (as demais exigem dono). Uma rota pode declarar papel="operador"
# ou papel="dono" na @rota para sair desta regra.
OPERADOR_PODE = re.compile(
    r"^/api/admin/(pedidos|produtos|avaliacoes|avise-me|carrinhos|separacao|encomendas|viagens|resumo|eu|logout)"
    r"(/|$)"
)
# Pedaços de nomes de campo que o operador nunca recebe (custo, lucro, margem, markup, comissão)
CAMPOS_RESTRITOS = ("custo", "lucro", "margem", "markup", "comissao")
# Campos (nome exato) que o operador nunca recebe: acesso ao painel da revendedora e os totais dela
CAMPOS_RESTRITOS_EXATOS = frozenset({"token_acesso", "link_painel", "totais"})
# Campos que o operador não grava (são ignorados no corpo): oferta relâmpago é decisão de preço, do dono
CAMPOS_SO_DONO_NA_ESCRITA = frozenset({"promo_pct", "promo_fim"})


# ---------------------------------------------------------------- senhas

def hash_senha(senha):
    sal = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, ITERACOES)
    return f"pbkdf2_sha256${ITERACOES}${base64.b64encode(sal).decode()}${base64.b64encode(dk).decode()}"


def conferir_senha(senha, armazenado):
    try:
        algoritmo, iteracoes, sal, esperado = armazenado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", str(senha).encode("utf-8"), base64.b64decode(sal), int(iteracoes))
        return hmac.compare_digest(dk, base64.b64decode(esperado))
    except (ValueError, TypeError, AttributeError):
        return False


# usado quando o login não existe, para a resposta levar o mesmo tempo
_HASH_FICTICIO = hash_senha(secrets.token_urlsafe(16))


def _validar_senha(senha, campo="senha"):
    if not isinstance(senha, str) or not SENHA_MIN <= len(senha) <= SENHA_MAX:
        raise ErroValidacao({campo: f"A senha deve ter entre {SENHA_MIN} e {SENHA_MAX} caracteres."})
    return senha


def hash_token(token):
    return hashlib.sha256(str(token).encode()).hexdigest()


# ---------------------------------------------------------------- usuários

def _usuario_dict(r):
    return {"id": r["id"], "nome": r["nome"], "login": r["login"], "papel": r["papel"], "ativo": bool(r["ativo"]),
            "totp_ativo": bool(r["totp_segredo"]), "ultimo_acesso": horario.iso_z(r["ultimo_acesso"]),
            "criado_em": horario.iso_z(r["criado_em"])}


def existe_algum(conn):
    return conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone() is not None


def listar(conn):
    return [_usuario_dict(r) for r in conn.execute("SELECT * FROM usuarios ORDER BY id").fetchall()]


def _obter(conn, usuario_id):
    row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if not row:
        raise NaoEncontrado("Usuário não encontrado.")
    return row


def criar(conn, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    erros = {}
    nome = " ".join(str(dados.get("nome") or "").split())
    if not 2 <= len(nome) <= 80:
        erros["nome"] = "Informe o nome (2 a 80 caracteres)."
    login = str(dados.get("login") or "").strip().lower()
    if not email_valido(login) or any(c in login for c in "\r\n"):
        erros["login"] = "Use um e-mail como login."
    elif conn.execute("SELECT 1 FROM usuarios WHERE login = ?", (login,)).fetchone():
        erros["login"] = "Já existe um usuário com este login."
    papel = dados.get("papel", "operador")
    if papel not in PAPEIS:
        erros["papel"] = "Papel inválido."
    try:
        senha = _validar_senha(dados.get("senha"))
    except ErroValidacao as e:
        erros.update(e.campos)
    if erros:
        raise ErroValidacao(erros)
    cur = conn.execute("INSERT INTO usuarios (nome, login, papel, senha_hash, criado_em) VALUES (?, ?, ?, ?, ?)",
                       (nome, login, papel, hash_senha(senha), horario.agora_db()))
    return _usuario_dict(_obter(conn, cur.lastrowid))


def encerrar_sessoes(conn, usuario_id, exceto_hash=None):
    conn.execute("DELETE FROM sessoes_admin WHERE usuario_id = ? AND token_hash IS NOT ?", (usuario_id, exceto_hash))


def atualizar(conn, usuario_id, dados):
    """Dono edita: nome, papel, ativo, nova_senha e desativar_2fa (celular perdido)."""
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    row = _obter(conn, usuario_id)
    sets, params, erros, encerrar = [], [], {}, False
    if "nome" in dados:
        nome = " ".join(str(dados.get("nome") or "").split())
        if not 2 <= len(nome) <= 80:
            erros["nome"] = "Informe o nome (2 a 80 caracteres)."
        sets.append("nome = ?")
        params.append(nome)
    if "papel" in dados:
        if dados["papel"] not in PAPEIS:
            erros["papel"] = "Papel inválido."
        sets.append("papel = ?")
        params.append(dados["papel"])
    if "ativo" in dados:
        if not isinstance(dados["ativo"], bool):
            erros["ativo"] = "Use verdadeiro ou falso."
        sets.append("ativo = ?")
        params.append(int(bool(dados["ativo"])))
        encerrar = encerrar or not dados["ativo"]
    if dados.get("nova_senha") is not None:
        try:
            sets.append("senha_hash = ?")
            params.append(hash_senha(_validar_senha(dados["nova_senha"], "nova_senha")))
            encerrar = True
        except ErroValidacao as e:
            erros.update(e.campos)
    if dados.get("desativar_2fa") is True:
        sets.append("totp_segredo = NULL, totp_pendente = NULL, totp_ultimo_passo = NULL")
        encerrar = True
    if erros:
        raise ErroValidacao(erros)
    if not sets:
        raise ErroValidacao({"geral": "Nada para atualizar."})
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(f"UPDATE usuarios SET {', '.join(sets)} WHERE id = ?", (*params, row["id"]))
        if not conn.execute("SELECT 1 FROM usuarios WHERE papel = 'dono' AND ativo = 1").fetchone():
            raise ErroValidacao({"papel": "É preciso manter pelo menos um dono ativo."})
        if encerrar:
            encerrar_sessoes(conn, row["id"])
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return _usuario_dict(_obter(conn, row["id"]))


# ---------------------------------------------------------------- login e sessões

class FalhaLogin(Exception):
    def __init__(self, precisa_2fa=False, usuario=None):
        super().__init__("login")
        self.precisa_2fa = precisa_2fa
        self.usuario = usuario


def _consumir_passo(conn, usuario_id, passo):
    """Grava o passo TOTP aceito; falha se ele (ou um posterior) já foi usado — código não vale duas vezes."""
    return conn.execute("UPDATE usuarios SET totp_ultimo_passo = ? WHERE id = ? "
                        "AND (totp_ultimo_passo IS NULL OR totp_ultimo_passo < ?)",
                        (passo, usuario_id, passo)).rowcount == 1


def autenticar(conn, login, senha, codigo_2fa=None, ip=""):
    """Confere login, senha e (se ativo) o código 2FA. Devolve {sessao, usuario, expira_em} ou FalhaLogin."""
    login = str(login or "").strip().lower()[:254]
    if not isinstance(senha, str) or len(senha) > SENHA_MAX:
        senha = ""
    row = conn.execute("SELECT * FROM usuarios WHERE login = ?", (login,)).fetchone()
    senha_ok = conferir_senha(senha, row["senha_hash"] if row else _HASH_FICTICIO)
    if not row or not senha_ok or not row["ativo"]:
        raise FalhaLogin()
    if row["totp_segredo"]:
        if not codigo_2fa:
            raise FalhaLogin(precisa_2fa=True, usuario=row["id"])
        passo = totp.verificar(row["totp_segredo"], str(codigo_2fa), row["totp_ultimo_passo"])
        if passo is None or not _consumir_passo(conn, row["id"], passo):
            raise FalhaLogin(precisa_2fa=True, usuario=row["id"])
    return criar_sessao(conn, row, ip)


def criar_sessao(conn, row, ip=""):
    sessao = secrets.token_urlsafe(32)
    agora = horario.agora_db()
    expira = horario.agora_db(hours=SESSAO_HORAS)
    conn.execute("INSERT INTO sessoes_admin (token_hash, usuario_id, criada_em, expira_em, ip) VALUES (?, ?, ?, ?, ?)",
                 (hash_token(sessao), row["id"], agora, expira, str(ip)[:64]))
    conn.execute("UPDATE usuarios SET ultimo_acesso = ? WHERE id = ?", (agora, row["id"]))
    return {"sessao": sessao, "usuario": {"nome": row["nome"], "papel": row["papel"]},
            "expira_em": horario.iso_z(expira)}


def ator_da_sessao(conn, sessao):
    """Usuário dono da sessão (ativo e não expirada), com renovação deslizante; None se inválida."""
    if not isinstance(sessao, str) or not 20 <= len(sessao) <= 100:
        return None
    th = hash_token(sessao)
    agora = horario.agora_db()
    row = conn.execute(
        """SELECT u.*, s.expira_em AS sessao_expira FROM sessoes_admin s JOIN usuarios u ON u.id = s.usuario_id
           WHERE s.token_hash = ? AND s.expira_em > ? AND u.ativo = 1""", (th, agora)).fetchone()
    if not row:
        return None
    nova = horario.agora_db(hours=SESSAO_HORAS)
    if row["sessao_expira"] < horario.agora_db(hours=SESSAO_HORAS, minutes=-RENOVAR_APOS_MIN):
        conn.execute("UPDATE sessoes_admin SET expira_em = ? WHERE token_hash = ?", (nova, th))
        conn.execute("UPDATE usuarios SET ultimo_acesso = ? WHERE id = ?", (agora, row["id"]))
    return {"id": row["id"], "nome": row["nome"], "login": row["login"], "papel": row["papel"],
            "totp_ativo": bool(row["totp_segredo"]), "via_token": False, "sessao_hash": th}


def encerrar_sessao(conn, sessao):
    conn.execute("DELETE FROM sessoes_admin WHERE token_hash = ?", (hash_token(sessao),))


def eu(conn, ator):
    dados = {"nome": ator["nome"], "papel": ator["papel"], "totp_ativo": ator["totp_ativo"],
             "via_token": ator["via_token"]}
    if ator["via_token"]:
        dados["primeiro_usuario"] = not existe_algum(conn)  # painel mostra "Crie o primeiro usuário (dono)"
    else:
        dados["login"] = ator["login"]
    return dados


# ---------------------------------------------------------------- 2FA e senha do próprio usuário

def _exigir_usuario(ator):
    if ator["via_token"]:
        raise ErroValidacao({"geral": "Entre com um usuário (não com o token de emergência) para usar esta função."})


def iniciar_2fa(conn, ator):
    _exigir_usuario(ator)
    row = _obter(conn, ator["id"])
    if row["totp_segredo"]:
        raise ErroValidacao({"geral": "A verificação em duas etapas já está ativa."})
    segredo = totp.gerar_segredo()
    conn.execute("UPDATE usuarios SET totp_pendente = ? WHERE id = ?", (segredo, row["id"]))
    resposta = {"segredo": segredo, "otpauth_url": totp.otpauth_url(segredo, row["login"])}
    resposta["qr_svg"] = qr_svg(resposta["otpauth_url"])
    return resposta


def qr_svg(texto):
    """QR Code (SVG) do endereço otpauth://, para cadastrar no aplicativo autenticador."""
    return qrcode.svg(qrcode.gerar(texto.encode("utf-8"), "M"), margem=4)


def confirmar_2fa(conn, ator, codigo_2fa):
    _exigir_usuario(ator)
    row = _obter(conn, ator["id"])
    if row["totp_segredo"] or not row["totp_pendente"]:
        raise ErroValidacao({"geral": "Comece a ativação da verificação em duas etapas de novo."})
    passo = totp.verificar(row["totp_pendente"], str(codigo_2fa or ""))
    if passo is None:
        raise ErroValidacao({"codigo": "Código inválido. Confira o horário do celular e tente de novo."})
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("UPDATE usuarios SET totp_segredo = totp_pendente, totp_pendente = NULL, totp_ultimo_passo = ? "
                     "WHERE id = ?", (passo, row["id"]))
        encerrar_sessoes(conn, row["id"], exceto_hash=ator.get("sessao_hash"))  # outras sessões, sem 2FA, caem
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {"totp_ativo": True}


def desativar_2fa(conn, ator, senha, codigo_2fa):
    _exigir_usuario(ator)
    row = _obter(conn, ator["id"])
    if not row["totp_segredo"]:
        raise ErroValidacao({"geral": "A verificação em duas etapas não está ativa."})
    if not conferir_senha(senha if isinstance(senha, str) else "", row["senha_hash"]):
        raise ErroValidacao({"senha": "Senha incorreta."})
    passo = totp.verificar(row["totp_segredo"], str(codigo_2fa or ""), row["totp_ultimo_passo"])
    if passo is None or not _consumir_passo(conn, row["id"], passo):
        raise ErroValidacao({"codigo": "Código inválido."})
    conn.execute("UPDATE usuarios SET totp_segredo = NULL, totp_pendente = NULL WHERE id = ?", (row["id"],))
    return {"totp_ativo": False}


def trocar_senha(conn, ator, atual, nova):
    _exigir_usuario(ator)
    row = _obter(conn, ator["id"])
    if not conferir_senha(atual if isinstance(atual, str) else "", row["senha_hash"]):
        raise ErroValidacao({"atual": "Senha atual incorreta."})
    nova = _validar_senha(nova, "nova")
    if nova == atual:
        raise ErroValidacao({"nova": "Escolha uma senha diferente da atual."})
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (hash_senha(nova), row["id"]))
        encerrar_sessoes(conn, row["id"], exceto_hash=ator.get("sessao_hash"))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {"ok": True}


# ---------------------------------------------------------------- papéis

def pode(ator, caminho, func):
    if ator["papel"] == "dono":
        return True
    papel = getattr(func, "papel", None)
    if papel == "operador":
        return True
    if papel == "dono":
        return False
    return bool(OPERADOR_PODE.match(caminho))


def _restrito(chave):
    chave = str(chave).lower()
    return chave in CAMPOS_RESTRITOS_EXATOS or any(p in chave for p in CAMPOS_RESTRITOS)


def filtrar_para_operador(dados):
    """Cópia dos dados sem campos de custo/lucro/margem/comissão, em qualquer nível."""
    if isinstance(dados, dict):
        return {k: filtrar_para_operador(v) for k, v in dados.items() if not _restrito(k)}
    if isinstance(dados, list):
        return [filtrar_para_operador(v) for v in dados]
    return dados


def remover_campos_restritos(dados):
    """Corpo enviado por operador: custo, comissão e oferta relâmpago (promo_pct/promo_fim) são ignorados."""
    dados = filtrar_para_operador(dados)
    if isinstance(dados, dict):
        dados = {k: v for k, v in dados.items() if k not in CAMPOS_SO_DONO_NA_ESCRITA}
    return dados
