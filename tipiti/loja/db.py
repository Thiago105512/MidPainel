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

CREATE TABLE IF NOT EXISTS variacoes (
    id INTEGER PRIMARY KEY,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    nome TEXT NOT NULL,
    sku TEXT NOT NULL DEFAULT '',
    preco_centavos INTEGER CHECK (preco_centavos IS NULL OR preco_centavos >= 0),
    estoque INTEGER NOT NULL DEFAULT 0 CHECK (estoque >= 0),
    ativo INTEGER NOT NULL DEFAULT 1,
    ordem INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fotos_produto (
    id INTEGER PRIMARY KEY,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    arquivo TEXT NOT NULL,
    ordem INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ajustes (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cupons (
    id INTEGER PRIMARY KEY,
    codigo TEXT UNIQUE NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('pct', 'valor', 'frete')),
    valor INTEGER NOT NULL DEFAULT 0 CHECK (valor >= 0),
    minimo_centavos INTEGER NOT NULL DEFAULT 0 CHECK (minimo_centavos >= 0),
    inicio TEXT,
    fim TEXT,
    limite_usos INTEGER CHECK (limite_usos IS NULL OR limite_usos > 0),
    usos INTEGER NOT NULL DEFAULT 0 CHECK (usos >= 0),
    so_primeira_compra INTEGER NOT NULL DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1,
    destaque INTEGER NOT NULL DEFAULT 0,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS avaliacoes (
    id INTEGER PRIMARY KEY,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
    nota INTEGER NOT NULL CHECK (nota BETWEEN 1 AND 5),
    comentario TEXT NOT NULL DEFAULT '' CHECK (length(comentario) <= 1000),
    nome_exibicao TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente', 'aprovada', 'oculta')),
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (pedido_id, produto_id)
);

CREATE INDEX IF NOT EXISTS idx_produtos_categoria ON produtos(categoria_id);
CREATE INDEX IF NOT EXISTS idx_itens_pedido ON itens_pedido(pedido_id);
CREATE INDEX IF NOT EXISTS idx_variacoes_produto ON variacoes(produto_id);
CREATE INDEX IF NOT EXISTS idx_fotos_produto ON fotos_produto(produto_id);
CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status, id);
CREATE INDEX IF NOT EXISTS idx_produtos_vitrine ON produtos(ativo, destaque, nome);
CREATE INDEX IF NOT EXISTS idx_pedidos_criado ON pedidos(criado_em);
CREATE INDEX IF NOT EXISTS idx_pedidos_cpf ON pedidos(cliente_cpf);
CREATE INDEX IF NOT EXISTS idx_itens_produto ON itens_pedido(produto_id);
CREATE INDEX IF NOT EXISTS idx_avaliacoes_produto ON avaliacoes(produto_id, status);

-- calendário de barcos (zona = id de zona de frete.py); horários em UTC
CREATE TABLE IF NOT EXISTS viagens (
    id INTEGER PRIMARY KEY,
    zona TEXT NOT NULL,
    embarcacao TEXT NOT NULL,
    saida TEXT NOT NULL,
    chegada_prevista TEXT NOT NULL,
    observacao TEXT NOT NULL DEFAULT '',
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_viagens_zona ON viagens(zona, ativo, saida);

-- linha do tempo do pedido (rastreio)
CREATE TABLE IF NOT EXISTS eventos_pedido (
    id INTEGER PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
    tipo TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_eventos_pedido ON eventos_pedido(pedido_id, id);

-- programa de revendedoras
CREATE TABLE IF NOT EXISTS revendedoras (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    whatsapp TEXT NOT NULL,
    cpf TEXT UNIQUE NOT NULL,
    cidade TEXT NOT NULL,
    uf TEXT NOT NULL,
    instagram TEXT NOT NULL DEFAULT '',
    mensagem TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente', 'ativa', 'inativa')),
    codigo TEXT UNIQUE,
    token_acesso TEXT UNIQUE,
    comissao_pct INTEGER NOT NULL DEFAULT 10 CHECK (comissao_pct BETWEEN 0 AND 50),
    desconto_cliente_pct INTEGER NOT NULL DEFAULT 0 CHECK (desconto_cliente_pct BETWEEN 0 AND 50),
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    ativada_em TEXT
);
"""

# Colunas acrescentadas depois da primeira versão: (tabela, coluna, definição)
MIGRACOES = [
    ("produtos", "foto", "TEXT NOT NULL DEFAULT ''"),
    ("produtos", "custo_centavos", "INTEGER CHECK (custo_centavos IS NULL OR custo_centavos >= 0)"),
    ("itens_pedido", "variacao_id", "INTEGER REFERENCES variacoes(id)"),
    ("itens_pedido", "variacao_nome", "TEXT NOT NULL DEFAULT ''"),
    ("itens_pedido", "custo_unit_centavos", "INTEGER"),
    ("produtos", "busca", "TEXT NOT NULL DEFAULT ''"),
    ("fotos_produto", "miniatura", "TEXT NOT NULL DEFAULT ''"),
    # oferta relâmpago: desconto (%) e término em UTC
    ("produtos", "promo_pct", "INTEGER CHECK (promo_pct IS NULL OR promo_pct BETWEEN 1 AND 90)"),
    ("produtos", "promo_fim", "TEXT"),
    ("pedidos", "cupom_codigo", "TEXT"),
    ("pedidos", "desconto_cupom_centavos", "INTEGER NOT NULL DEFAULT 0"),
    ("itens_pedido", "preco_ancora_unit_centavos", "INTEGER"),
    # rastreio e calendário de barcos
    ("pedidos", "codigo_rastreio", "TEXT"),
    ("pedidos", "viagem_id", "INTEGER REFERENCES viagens(id)"),
    # revendedoras: comissão guardada no pedido; paga quando comissao_paga_em é preenchido
    ("pedidos", "revendedora_id", "INTEGER REFERENCES revendedoras(id)"),
    ("pedidos", "comissao_centavos", "INTEGER NOT NULL DEFAULT 0"),
    ("pedidos", "comissao_paga_em", "TEXT"),
    ("cupons", "revendedora_id", "INTEGER REFERENCES revendedoras(id)"),
]

# Índices de colunas que vêm das MIGRACOES (só podem ser criados depois delas).
INDICES_POS_MIGRACOES = """
CREATE INDEX IF NOT EXISTS idx_pedidos_revendedora ON pedidos(revendedora_id);
CREATE INDEX IF NOT EXISTS idx_cupons_revendedora ON cupons(revendedora_id);
"""

# Texto pesquisável já normalizado, gravado junto com o produto para a busca não processar linha a linha.
_SQL_BUSCA = """UPDATE produtos SET busca = normaliza(
                    nome || ' ' || descricao || ' ' || (SELECT c.nome FROM categorias c WHERE c.id = categoria_id))"""


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
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.create_function("normaliza", 1, normaliza, deterministic=True)
    return conn


def atualizar_busca(conn, produto_id=None):
    if produto_id is None:
        conn.execute(_SQL_BUSCA)
    else:
        conn.execute(_SQL_BUSCA + " WHERE id = ?", (produto_id,))


def inicializar(conn, carregar_catalogo=True):
    conn.execute("PRAGMA journal_mode = WAL")  # leitores não esperam pela escrita de um pedido
    conn.executescript(ESQUEMA)
    for tabela, coluna, definicao in MIGRACOES:
        colunas = {r["name"] for r in conn.execute(f"PRAGMA table_info({tabela})")}
        if coluna not in colunas:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")
    conn.executescript(INDICES_POS_MIGRACOES)
    # fotos enviadas antes da galeria passam a ser a capa da galeria
    conn.execute(
        """INSERT INTO fotos_produto (produto_id, arquivo, ordem)
           SELECT id, foto, 0 FROM produtos p
           WHERE foto != '' AND NOT EXISTS (SELECT 1 FROM fotos_produto f WHERE f.produto_id = p.id)"""
    )
    conn.execute(_SQL_BUSCA + " WHERE busca = ''")
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
            variacoes = p.get("variacoes") or []
            estoque = sum(v[2] for v in variacoes) if variacoes else p["estoque"]
            cur = conn.execute(
                """INSERT INTO produtos (slug, nome, descricao, categoria_id, preco_centavos,
                       preco_de_centavos, custo_centavos, estoque, icone, destaque, criado_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '-30 days'))""",
                (
                    p["slug"], p["nome"], p["descricao"], ids[p["categoria"]], p["preco"],
                    p.get("preco_de"), p.get("custo"), estoque, p["icone"],
                    1 if p.get("destaque") else 0,
                ),
            )
            for ordem, (nome, preco, est) in enumerate(variacoes):
                conn.execute(
                    "INSERT INTO variacoes (produto_id, nome, preco_centavos, estoque, ordem) VALUES (?, ?, ?, ?, ?)",
                    (cur.lastrowid, nome, preco, est, ordem),
                )
        atualizar_busca(conn)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
