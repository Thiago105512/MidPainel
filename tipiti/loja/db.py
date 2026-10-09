"""Banco de dados SQLite: esquema, conexão e carga inicial do catálogo."""

import sqlite3
import unicodedata
from pathlib import Path

from .catalogo_inicial import CATEGORIAS, PRODUTOS

ESQUEMA = """
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    descricao TEXT NOT NULL DEFAULT '',
    icone TEXT NOT NULL DEFAULT '',
    cor TEXT NOT NULL DEFAULT '#1f5c45',
    ordem INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    descricao TEXT NOT NULL DEFAULT '',
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    preco_centavos INTEGER NOT NULL CHECK (preco_centavos >= 0),
    preco_de_centavos INTEGER CHECK (preco_de_centavos IS NULL OR preco_de_centavos >= 0),
    estoque INTEGER NOT NULL DEFAULT 0 CHECK (estoque >= 0),
    icone TEXT NOT NULL DEFAULT '',
    foto TEXT NOT NULL DEFAULT '',
    destaque INTEGER NOT NULL DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY,
    codigo TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    cliente_nome TEXT NOT NULL,
    cliente_email TEXT NOT NULL,
    cliente_cpf TEXT NOT NULL,
    cliente_telefone TEXT NOT NULL,
    cep TEXT NOT NULL,
    endereco TEXT NOT NULL,
    numero TEXT NOT NULL,
    complemento TEXT NOT NULL DEFAULT '',
    bairro TEXT NOT NULL,
    cidade TEXT NOT NULL,
    uf TEXT NOT NULL,
    zona_frete TEXT NOT NULL,
    prazo_dias INTEGER NOT NULL,
    pagamento TEXT NOT NULL,
    parcelas INTEGER NOT NULL DEFAULT 1,
    subtotal_centavos INTEGER NOT NULL,
    desconto_centavos INTEGER NOT NULL,
    frete_centavos INTEGER NOT NULL,
    total_centavos INTEGER NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS itens_pedido (
    id INTEGER PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    nome TEXT NOT NULL,
    preco_unit_centavos INTEGER NOT NULL,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0)
);

CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria_id);
CREATE INDEX IF NOT EXISTS idx_itens_pedido ON itens_pedido(pedido_id);
"""


def normaliza(texto):
    """Minúsculas e sem acentos — usado na busca ("acai" encontra "Açaí")."""
    if texto is None:
        return ""
    sem_acento = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).lower()


def conectar(caminho):
    """Abre uma conexão em modo autocommit; transações são abertas explicitamente."""
    if str(caminho) != ":memory:":
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(caminho), isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.create_function("normaliza", 1, normaliza, deterministic=True)
    return conn


def inicializar(conn, carregar_catalogo=True):
    conn.executescript(ESQUEMA)
    colunas = {r["name"] for r in conn.execute("PRAGMA table_info(produtos)")}
    if "foto" not in colunas:  # bancos criados antes do envio de fotos
        conn.execute("ALTER TABLE produtos ADD COLUMN foto TEXT NOT NULL DEFAULT ''")
    vazio = conn.execute("SELECT COUNT(*) FROM categorias").fetchone()[0] == 0
    if carregar_catalogo and vazio:
        _carregar_catalogo(conn)


def _carregar_catalogo(conn):
    conn.execute("BEGIN")
    try:
        ids = {}
        for ordem, cat in enumerate(CATEGORIAS):
            cur = conn.execute(
                "INSERT INTO categorias (slug, nome, descricao, icone, cor, ordem) VALUES (?, ?, ?, ?, ?, ?)",
                (cat["slug"], cat["nome"], cat["descricao"], cat["icone"], cat["cor"], ordem),
            )
            ids[cat["slug"]] = cur.lastrowid
        for p in PRODUTOS:
            conn.execute(
                """INSERT INTO produtos (slug, nome, descricao, categoria_id, preco_centavos,
                       preco_de_centavos, estoque, icone, destaque)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    p["slug"], p["nome"], p["descricao"], ids[p["categoria"]], p["preco"],
                    p.get("preco_de"), p["estoque"], p["icone"],
                    1 if p.get("destaque") else 0,
                ),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
