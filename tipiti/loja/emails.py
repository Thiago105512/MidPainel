"""E-mail por SMTP genérico: fila no banco + thread de envio em segundo plano.

Nenhuma requisição espera pelo SMTP: as mensagens entram na tabela `emails_saida` e uma thread as envia, com
novas tentativas (espera crescente) até MAX_TENTATIVAS. Sem SMTP configurado, ficam "pendentes".

Configuração só por variáveis de ambiente (lidas a cada envio):
TIPITI_SMTP_HOST, TIPITI_SMTP_PORTA (587), TIPITI_SMTP_USUARIO, TIPITI_SMTP_SENHA,
TIPITI_SMTP_REMETENTE ("Tipiti <contato@tipiti.com.br>"), TIPITI_SMTP_TLS ("starttls" | "ssl" | "nenhum").
"""

import logging
import os
import smtplib
import ssl
import threading
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parseaddr
from html import escape

from . import db, horario
from .validacao import ErroValidacao, NaoEncontrado, email_valido, sem_quebras

log = logging.getLogger("tipiti.emails")

MAX_TENTATIVAS = 5
LOTE = 20
INTERVALO_S = 30
STATUS = ("pendente", "enviando", "enviado", "falhou")
REMETENTE_PADRAO = "Tipiti <contato@tipiti.com.br>"

_acordar = threading.Event()


def configuracao():
    """Dados do SMTP (dict) ou None se não configurado. A senha nunca sai deste módulo."""
    host = os.environ.get("TIPITI_SMTP_HOST", "").strip()
    if not host:
        return None
    try:
        porta = int(os.environ.get("TIPITI_SMTP_PORTA", "587"))
    except ValueError:
        porta = 587
    tls = os.environ.get("TIPITI_SMTP_TLS", "starttls").strip().lower()
    return {
        "host": host,
        "porta": porta,
        "usuario": os.environ.get("TIPITI_SMTP_USUARIO", ""),
        "senha": os.environ.get("TIPITI_SMTP_SENHA", ""),
        "remetente": os.environ.get("TIPITI_SMTP_REMETENTE", "").strip() or REMETENTE_PADRAO,
        "tls": tls if tls in ("starttls", "ssl", "nenhum") else "starttls",
    }


def configurado():
    return configuracao() is not None


def endereco_seguro(email):
    """E-mail de destino válido, de uma linha só. ErroValidacao caso contrário (nunca entra CRLF em cabeçalho)."""
    texto = str(email or "").strip()
    if any(c in texto for c in "\r\n\x00,;<>\"") or not email_valido(texto):
        raise ErroValidacao({"email": "E-mail inválido."})
    return texto.lower()


def enfileirar(conn, para, assunto, texto, html="", tipo="", validade_horas=None):
    """Coloca uma mensagem na fila e acorda a thread de envio. Devolve o id."""
    para = endereco_seguro(para)
    assunto = sem_quebras(assunto, 200) or "Tipiti"
    agora = horario.agora_db()
    expira = horario.agora_db(hours=validade_horas) if validade_horas else None
    cur = conn.execute(
        """INSERT INTO emails_saida (tipo, para, assunto, texto, html, status, proxima_tentativa, expira_em, criado_em)
           VALUES (?, ?, ?, ?, ?, 'pendente', ?, ?, ?)""",
        (sem_quebras(tipo, 40), para, assunto, str(texto)[:100_000], str(html or "")[:200_000], agora, expira, agora),
    )
    acordar()
    return cur.lastrowid


def acordar():
    _acordar.set()


def montar_mensagem(cfg, para, assunto, texto, html=""):
    msg = EmailMessage()  # a política padrão recusa CR/LF em cabeçalhos
    nome, endereco = parseaddr(cfg["remetente"])
    msg["From"] = formataddr((sem_quebras(nome, 80), endereco)) if nome else endereco
    msg["To"] = endereco_seguro(para)
    msg["Subject"] = sem_quebras(assunto, 200)
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain=(endereco.split("@")[-1] or "tipiti.com.br"))
    msg.set_content(texto)
    if html:
        msg.add_alternative(html, subtype="html")
    return msg


def _enviar_smtp(cfg, msg):
    contexto = ssl.create_default_context()
    if cfg["tls"] == "ssl":
        cliente = smtplib.SMTP_SSL(cfg["host"], cfg["porta"], timeout=20, context=contexto)
    else:
        cliente = smtplib.SMTP(cfg["host"], cfg["porta"], timeout=20)
    try:
        if cfg["tls"] == "starttls":
            cliente.starttls(context=contexto)
        if cfg["usuario"]:
            cliente.login(cfg["usuario"], cfg["senha"])
        cliente.send_message(msg)
    finally:
        try:
            cliente.quit()
        except Exception:  # noqa: BLE001 — a mensagem já foi entregue (ou o erro original importa mais)
            pass


def _espera_minutos(tentativas):
    return min(2 ** tentativas, 120)  # 2, 4, 8, 16… minutos


def processar_fila(conn, limite=LOTE):
    """Envia as mensagens vencidas da fila. Devolve quantas foram enviadas. Nunca levanta erro de SMTP."""
    cfg = configuracao()
    agora = horario.agora_db()
    # envios interrompidos (queda do processo) voltam para a fila
    conn.execute("UPDATE emails_saida SET status = 'pendente' WHERE status = 'enviando' AND proxima_tentativa < ?",
                 (horario.agora_db(minutes=-10),))
    conn.execute("""UPDATE emails_saida SET status = 'falhou', erro = 'Expirou antes do envio.'
                    WHERE status = 'pendente' AND expira_em IS NOT NULL AND expira_em < ?""", (agora,))
    if cfg is None:
        return 0
    enviados = 0
    rows = conn.execute(
        """SELECT id, para, assunto, texto, html, tentativas FROM emails_saida
           WHERE status = 'pendente' AND proxima_tentativa <= ? ORDER BY id LIMIT ?""", (agora, limite)
    ).fetchall()
    for r in rows:
        # reserva a mensagem: duas threads (ou processos) não enviam a mesma
        if conn.execute("UPDATE emails_saida SET status = 'enviando', proxima_tentativa = ? "
                        "WHERE id = ? AND status = 'pendente'", (agora, r["id"])).rowcount != 1:
            continue
        try:
            _enviar_smtp(cfg, montar_mensagem(cfg, r["para"], r["assunto"], r["texto"], r["html"]))
        except Exception as e:  # noqa: BLE001 — erro de rede/SMTP: tenta de novo mais tarde
            tentativas = r["tentativas"] + 1
            status = "falhou" if tentativas >= MAX_TENTATIVAS else "pendente"
            erro = sem_quebras(f"{type(e).__name__}: {e}", 300)
            conn.execute("UPDATE emails_saida SET status = ?, tentativas = ?, erro = ?, proxima_tentativa = ? "
                         "WHERE id = ?",
                         (status, tentativas, erro, horario.agora_db(minutes=_espera_minutos(tentativas)), r["id"]))
            log.warning("Falha ao enviar o e-mail %s (tentativa %s): %s", r["id"], tentativas, erro)
        else:
            conn.execute("UPDATE emails_saida SET status = 'enviado', tentativas = tentativas + 1, erro = NULL, "
                         "enviado_em = ? WHERE id = ?", (horario.agora_db(), r["id"]))
            enviados += 1
    return enviados


class Remetente(threading.Thread):
    """Thread em segundo plano: acorda a cada INTERVALO_S ou quando uma mensagem entra na fila."""

    def __init__(self, db_path, tarefas=()):
        super().__init__(name="tipiti-emails", daemon=True)
        self.db_path = db_path
        self.tarefas = tarefas  # funções extras (conn) -> None, ex.: avisos do avise-me, limpeza
        self._parar = threading.Event()

    def run(self):
        while not self._parar.is_set():
            _acordar.wait(INTERVALO_S)
            _acordar.clear()
            if self._parar.is_set():
                break
            self.rodada()

    def rodada(self):
        try:
            conn = db.conectar(self.db_path)
        except Exception:  # noqa: BLE001
            log.exception("Fila de e-mails: banco indisponível")
            return
        try:
            for tarefa in self.tarefas:
                try:
                    tarefa(conn)
                except Exception:  # noqa: BLE001 — uma tarefa com problema não para a fila
                    log.exception("Tarefa de fundo falhou")
            processar_fila(conn)
        except Exception:  # noqa: BLE001 — a thread nunca morre
            log.exception("Fila de e-mails: erro inesperado")
        finally:
            conn.close()

    def parar(self):
        self._parar.set()
        _acordar.set()


# ---------------------------------------------------------------- painel

def listar(conn, status=None):
    sql = "SELECT id, tipo, para, assunto, status, tentativas, erro, criado_em, enviado_em FROM emails_saida"
    params = []
    if status:
        if status not in STATUS:
            raise ErroValidacao({"status": "Status inválido."})
        sql += " WHERE status = ?"
        params.append(status)
    rows = conn.execute(sql + " ORDER BY id DESC LIMIT 300", params).fetchall()
    return [dict(r, criado_em=horario.iso_z(r["criado_em"]), enviado_em=horario.iso_z(r["enviado_em"]))
            for r in rows]


def reenviar(conn, email_id):
    if conn.execute("""UPDATE emails_saida SET status = 'pendente', tentativas = 0, erro = NULL, expira_em = NULL,
                       proxima_tentativa = ? WHERE id = ?""", (horario.agora_db(), email_id)).rowcount != 1:
        raise NaoEncontrado("E-mail não encontrado.")
    acordar()
    row = conn.execute("SELECT id, tipo, para, assunto, status, tentativas, erro, criado_em, enviado_em "
                       "FROM emails_saida WHERE id = ?", (email_id,)).fetchone()
    return dict(row, criado_em=horario.iso_z(row["criado_em"]), enviado_em=horario.iso_z(row["enviado_em"]))


def pendentes(conn):
    return conn.execute("SELECT COUNT(*) FROM emails_saida WHERE status IN ('pendente', 'enviando')").fetchone()[0]


# ---------------------------------------------------------------- modelos simples (texto + HTML)

def html_simples(titulo, paragrafos, botao=None):
    """HTML mínimo e seguro: todo texto passa por escape. botao = (rótulo, url)."""
    corpo = "".join(f"<p style=\"margin:0 0 12px\">{escape(p)}</p>" for p in paragrafos)
    if botao:
        corpo += (f'<p style="margin:20px 0"><a href="{escape(botao[1], quote=True)}" '
                  f'style="background:#1f5c45;color:#fff;padding:10px 18px;border-radius:6px;'
                  f'text-decoration:none">{escape(botao[0])}</a></p>')
    return ("<!doctype html><html lang=\"pt-BR\"><body style=\"font-family:Arial,sans-serif;color:#222;"
            "background:#f6f5f0;padding:16px\"><div style=\"max-width:560px;margin:auto;background:#fff;"
            f"padding:20px;border-radius:8px\"><h1 style=\"font-size:20px;color:#1f5c45\">{escape(titulo)}</h1>"
            f"{corpo}<p style=\"color:#777;font-size:12px\">Tipiti — importados com entrega no Norte</p>"
            "</div></body></html>")
