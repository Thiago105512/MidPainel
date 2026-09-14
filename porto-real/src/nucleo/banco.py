"""BANCO — esquema de 28 entidades em SQLite (secao 137).

O modelo do projeto vive em Python e se reconstroi inteiro a cada execucao. O
banco existe para o que NAO se reconstroi: o que aconteceu no mundo. Uma bobina
recebida, uma peca cortada, uma inspecao feita, um painel instalado — nada disso
e funcao do modelo, e nada disso pode ser perdido.

Por isso o esquema separa as duas naturezas: as tabelas de PROJETO sao um espelho
do modelo, regeneravel; as de EVENTO sao registro historico, e so crescem.
"""
from __future__ import annotations

import sqlite3

ENTIDADES_PROJETO = (
    "project", "building", "level", "grid", "room", "wall", "panel", "member",
    "profile", "material", "connection", "fastener", "opening", "load",
    "result", "revision", "bom")
ENTIDADES_EVENTO = (
    "supplier", "product", "price", "coil", "batch", "heat", "machine",
    "pack", "shipment", "installation", "inspection")
ENTIDADES = ENTIDADES_PROJETO + ENTIDADES_EVENTO

ESQUEMA = """
CREATE TABLE IF NOT EXISTS project(
  id TEXT PRIMARY KEY, nome TEXT, cliente TEXT, local TEXT, lat REAL, lon REAL,
  tipologia TEXT, pavimentos INT, area REAL, sistema TEXT, moeda TEXT,
  status TEXT, revisao TEXT, criado TEXT);
CREATE TABLE IF NOT EXISTS building(
  id TEXT PRIMARY KEY, project_id TEXT REFERENCES project(id), nome TEXT);
CREATE TABLE IF NOT EXISTS level(
  id TEXT PRIMARY KEY, building_id TEXT REFERENCES building(id),
  nome TEXT, cota REAL, pe_direito REAL);
CREATE TABLE IF NOT EXISTS grid(
  id TEXT PRIMARY KEY, building_id TEXT, eixo TEXT, direcao TEXT, pos REAL);
CREATE TABLE IF NOT EXISTS room(
  id TEXT PRIMARY KEY, level_id TEXT REFERENCES level(id), cod TEXT, nome TEXT,
  x REAL, y REAL, w REAL, h REAL, area REAL, molhado INT);
CREATE TABLE IF NOT EXISTS wall(
  id TEXT PRIMARY KEY, level_id TEXT, x1 REAL, y1 REAL, x2 REAL, y2 REAL,
  esp REAL, externa INT);
CREATE TABLE IF NOT EXISTS panel(
  id TEXT PRIMARY KEY, wall_id TEXT REFERENCES wall(id), cod TEXT,
  comp REAL, altura REAL, massa REAL, obs TEXT);
CREATE TABLE IF NOT EXISTS member(
  id TEXT PRIMARY KEY, panel_id TEXT REFERENCES panel(id), cod TEXT,
  familia TEXT, profile_id TEXT REFERENCES profile(id), comp REAL, massa REAL,
  x REAL, z REAL, vertical INT, revisao TEXT);
CREATE TABLE IF NOT EXISTS profile(
  id TEXT PRIMARY KEY, forma TEXT, bw REAL, bf REAL, d REAL, t REAL,
  area REAL, ix REAL, iy REAL, j REAL, cw REAL, massa_m REAL);
CREATE TABLE IF NOT EXISTS material(
  id TEXT PRIMARY KEY, tipo TEXT, fy REAL, fu REAL, e REAL, densidade REAL,
  revestimento TEXT);
CREATE TABLE IF NOT EXISTS connection(
  id TEXT PRIMARY KEY, member_a TEXT, member_b TEXT, tipo TEXT, n INT,
  fastener_id TEXT REFERENCES fastener(id), nrd REAL, modo TEXT);
CREATE TABLE IF NOT EXISTS fastener(
  id TEXT PRIMARY KEY, tipo TEXT, d REAL, dw REAL, rv REAL, rt REAL);
CREATE TABLE IF NOT EXISTS opening(
  id TEXT PRIMARY KEY, panel_id TEXT, tipo TEXT, larg REAL, alt REAL,
  peitoril REAL, centro REAL);
CREATE TABLE IF NOT EXISTS load(
  id TEXT PRIMARY KEY, project_id TEXT, natureza TEXT, tipo TEXT, valor REAL,
  direcao TEXT, onde TEXT, origem TEXT);
CREATE TABLE IF NOT EXISTS result(
  id TEXT PRIMARY KEY, member_id TEXT REFERENCES member(id), combinacao TEXT,
  n REAL, vx REAL, vy REAL, mx REAL, my REAL, flecha REAL, uso REAL, modo TEXT);
CREATE TABLE IF NOT EXISTS revision(
  id TEXT PRIMARY KEY, project_id TEXT, cod TEXT, descricao TEXT, autor TEXT,
  data TEXT, congelada INT);
CREATE TABLE IF NOT EXISTS bom(
  id TEXT PRIMARY KEY, project_id TEXT, sku TEXT, descricao TEXT, unidade TEXT,
  quantidade REAL, preco REAL, fonte TEXT);
CREATE TABLE IF NOT EXISTS supplier(
  id TEXT PRIMARY KEY, nome TEXT, pais TEXT, contato TEXT, lead_time INT,
  moq REAL, certificacoes TEXT);
CREATE TABLE IF NOT EXISTS product(
  id TEXT PRIMARY KEY, supplier_id TEXT REFERENCES supplier(id), sku TEXT,
  descricao TEXT, unidade TEXT);
CREATE TABLE IF NOT EXISTS price(
  id TEXT PRIMARY KEY, product_id TEXT REFERENCES product(id), valor REAL,
  moeda TEXT, data TEXT, incoterm TEXT);
CREATE TABLE IF NOT EXISTS coil(
  id TEXT PRIMARY KEY, heat_id TEXT REFERENCES heat(id), largura REAL,
  espessura REAL, massa REAL, revestimento TEXT, recebida TEXT);
CREATE TABLE IF NOT EXISTS heat(
  id TEXT PRIMARY KEY, usina TEXT, corrida TEXT, fy REAL, fu REAL,
  certificado TEXT, composicao TEXT);
CREATE TABLE IF NOT EXISTS batch(
  id TEXT PRIMARY KEY, coil_id TEXT REFERENCES coil(id),
  machine_id TEXT REFERENCES machine(id), inicio TEXT, fim TEXT, n_pecas INT);
CREATE TABLE IF NOT EXISTS machine(
  id TEXT PRIMARY KEY, tipo TEXT, fabricante TEXT, perfis TEXT,
  esp_min REAL, esp_max REAL, comp_max REAL);
CREATE TABLE IF NOT EXISTS pack(
  id TEXT PRIMARY KEY, project_id TEXT, destino TEXT, massa REAL, volume REAL,
  cg_x REAL, cg_y REAL, cg_z REAL);
CREATE TABLE IF NOT EXISTS shipment(
  id TEXT PRIMARY KEY, pack_id TEXT REFERENCES pack(id), modal TEXT,
  saida TEXT, chegada TEXT, container TEXT);
CREATE TABLE IF NOT EXISTS installation(
  id TEXT PRIMARY KEY, member_id TEXT, data TEXT, equipe TEXT, passo INT);
CREATE TABLE IF NOT EXISTS inspection(
  id TEXT PRIMARY KEY, member_id TEXT, data TEXT, inspetor TEXT,
  item TEXT, nominal REAL, medido REAL, status TEXT);
CREATE INDEX IF NOT EXISTS ix_member_panel ON member(panel_id);
CREATE INDEX IF NOT EXISTS ix_result_member ON result(member_id);
CREATE INDEX IF NOT EXISTS ix_coil_heat ON coil(heat_id);
"""


def criar(caminho: str = ":memory:") -> sqlite3.Connection:
    con = sqlite3.connect(caminho)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ESQUEMA)
    return con


def tabelas(con) -> list:
    return sorted(r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall())


def gravar_projeto(con, cadastro, pecas: list, paineis: list,
                   perfis_props: dict) -> dict:
    """Espelha o modelo no banco. As tabelas de PROJETO sao regeneraveis."""
    cur = con.cursor()
    cur.execute("DELETE FROM member")
    cur.execute("DELETE FROM panel")
    cur.execute("DELETE FROM profile")
    cur.execute("INSERT OR REPLACE INTO project VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cadastro.project_id, cadastro.nome, cadastro.cliente,
                 cadastro.localizacao, cadastro.coordenadas[0],
                 cadastro.coordenadas[1], cadastro.tipologia,
                 cadastro.pavimentos, cadastro.area_m2, cadastro.sistema,
                 cadastro.moeda, cadastro.status, cadastro.revisao,
                 cadastro.data_emissao))
    for cod, d in perfis_props.items():
        cur.execute("INSERT OR REPLACE INTO profile VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (cod, d.get("forma", ""), d.get("bw", 0), d.get("bf", 0),
                     d.get("D", 0), d.get("t", 0), d["A"], d["Ix"], d["Iy"],
                     d["J"], d["Cw"], d["massa_m"]))
    for p in paineis:
        cur.execute("INSERT OR REPLACE INTO panel VALUES (?,?,?,?,?,?,?)",
                    (p.cod, None, p.cod, p.comp, p.altura, 0.0, p.obs))
    for m in pecas:
        cur.execute("INSERT OR REPLACE INTO member VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (m.cod, m.painel, m.cod, m.familia, m.perfil, m.comp,
                     m.massa, m.x, m.z, int(m.vertical), m.revisao))
    con.commit()
    return dict(pecas=len(pecas), paineis=len(paineis), perfis=len(perfis_props))
