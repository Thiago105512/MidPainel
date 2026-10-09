"""Administração de produtos pelo painel: cadastro, edição, variações e galeria de fotos."""

from . import config, prevenda, promocoes
from .catalogo import _SELECT_PRODUTO, _sincronizar_estoque, _variacoes, gerar_slug, obter_produto
from .db import atualizar_busca, normaliza
from .validacao import ErroValidacao, NaoEncontrado


INTEIRO_MAX = 10 ** 9


def _inteiro_ou_nulo(valor, erros, campo, aceita_nulo):
    if valor in (None, "") and aceita_nulo:
        return None
    if isinstance(valor, bool) or not isinstance(valor, int) or not 0 <= valor <= INTEIRO_MAX:
        erros[campo] = "Use um número inteiro entre 0 e 1.000.000.000."
        return None
    return valor


def atualizar_produto(conn, slug, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    row = conn.execute(_SELECT_PRODUTO + " WHERE p.slug = ?", (slug,)).fetchone()
    if not row:
        raise NaoEncontrado("Produto não encontrado.")
    sets, params, erros = [], [], {}
    for campo, aceita_nulo in (("preco_centavos", False), ("preco_de_centavos", True),
                               ("custo_centavos", True), ("estoque", False)):
        if campo in dados:
            if campo == "estoque" and row["n_variacoes_total"]:
                continue  # controlado pelas variações, mesmo que todas estejam desativadas
            valor = _inteiro_ou_nulo(dados[campo], erros, campo, aceita_nulo)
            if campo == "preco_centavos" and valor == 0:
                erros[campo] = "Informe o preço."
            if campo not in erros:
                sets.append(f"{campo} = ?")
                params.append(valor)
    for campo in ("ativo", "destaque"):
        if campo in dados:
            sets.append(f"{campo} = ?")
            params.append(1 if dados[campo] else 0)
    for campo in ("nome", "descricao", "icone"):
        if campo in dados:
            valor = str(dados[campo] or "").strip()
            if campo == "nome" and not 3 <= len(valor) <= 120:
                erros[campo] = "O nome deve ter entre 3 e 120 caracteres."
                continue
            sets.append(f"{campo} = ?")
            params.append(valor[:8] if campo == "icone" else valor[:2000])
    try:
        promo = promocoes.validar(dados, row["promo_pct"], row["promo_fim"])
    except ErroValidacao as e:
        erros.update(e.campos)
    else:
        if promo is not None:
            sets += ["promo_pct = ?", "promo_fim = ?"]
            params += list(promo)
    try:
        chegada = prevenda.validar(dados, row["prevenda_chegada"])
    except ErroValidacao as e:
        erros.update(e.campos)
    else:
        if chegada is not None:
            sets.append("prevenda_chegada = ?")
            params.append(chegada[0])
    if "categoria" in dados:
        cat = conn.execute("SELECT id FROM categorias WHERE slug = ?", (str(dados["categoria"]),)).fetchone()
        if cat:
            sets.append("categoria_id = ?")
            params.append(cat["id"])
        else:
            erros["categoria"] = "Categoria inválida."
    if erros:
        raise ErroValidacao(erros)
    if not sets:
        raise ErroValidacao({"geral": "Nada para atualizar."})
    conn.execute(f"UPDATE produtos SET {', '.join(sets)} WHERE id = ?", (*params, row["id"]))
    atualizar_busca(conn, row["id"])
    return obter_produto(conn, slug, incluir_inativos=True, admin=True)


def criar_produto(conn, dados):
    """Cadastro pelo painel. O endereço (slug) é gerado a partir do nome."""
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    erros = {}
    nome = str(dados.get("nome") or "").strip()
    if not 3 <= len(nome) <= 120:
        erros["nome"] = "O nome deve ter entre 3 e 120 caracteres."
    cat = conn.execute("SELECT id FROM categorias WHERE slug = ?", (str(dados.get("categoria") or ""),)).fetchone()
    if not cat:
        erros["categoria"] = "Escolha a categoria."
    numeros = {
        campo: _inteiro_ou_nulo(dados.get(campo), erros, campo, aceita_nulo)
        for campo, aceita_nulo in (("preco_centavos", False), ("preco_de_centavos", True),
                                   ("custo_centavos", True), ("estoque", False))
    }
    if numeros["preco_centavos"] == 0:
        erros["preco_centavos"] = "Informe o preço."
    if erros:
        raise ErroValidacao(erros)

    base = gerar_slug(nome)
    slug, n = base, 2
    while conn.execute("SELECT 1 FROM produtos WHERE slug = ?", (slug,)).fetchone():
        slug, n = f"{base}-{n}", n + 1
    cur = conn.execute(
        """INSERT INTO produtos (slug, nome, descricao, categoria_id, preco_centavos, preco_de_centavos,
               custo_centavos, estoque, icone, destaque, ativo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (slug, nome, str(dados.get("descricao") or "").strip()[:2000], cat["id"], numeros["preco_centavos"],
         numeros["preco_de_centavos"], numeros["custo_centavos"], numeros["estoque"],
         str(dados.get("icone") or "📦")[:8], 1 if dados.get("destaque") else 0,
         0 if dados.get("ativo") is False else 1),
    )
    atualizar_busca(conn, cur.lastrowid)
    return obter_produto(conn, slug, incluir_inativos=True, admin=True)


def _id_produto(conn, slug):
    row = conn.execute("SELECT id FROM produtos WHERE slug = ?", (slug,)).fetchone()
    if not row:
        raise NaoEncontrado("Produto não encontrado.")
    return row["id"]


def salvar_variacoes(conn, slug, lista):
    """Substitui as variações do produto pela lista enviada.

    Variações que saem da lista são desativadas (não apagadas), porque pedidos antigos apontam para elas.
    """
    if not isinstance(lista, list) or len(lista) > 60:
        raise ErroValidacao({"variacoes": "Lista de variações inválida."})
    produto_id = _id_produto(conn, slug)
    existentes = {v["id"] for v in _variacoes(conn, produto_id, incluir_inativas=True)}
    erros, limpas, nomes = {}, [], set()
    for i, v in enumerate(lista):
        if not isinstance(v, dict):
            raise ErroValidacao({"variacoes": "Variação inválida."})
        nome = str(v.get("nome") or "").strip()[:80]
        if not nome:
            erros[f"variacao_{i}"] = "Dê um nome à opção (ex.: Preto, 220 V)."
        elif normaliza(nome) in nomes:
            erros[f"variacao_{i}"] = f"A opção “{nome}” está repetida."
        nomes.add(normaliza(nome))
        e = {}
        preco = _inteiro_ou_nulo(v.get("preco_centavos"), e, "preco", True)
        estoque = _inteiro_ou_nulo(v.get("estoque", 0), e, "estoque", False)
        if e:
            erros[f"variacao_{i}"] = "Preço e estoque devem ser números inteiros maiores ou iguais a zero."
        elif preco == 0:
            erros[f"variacao_{i}"] = "Deixe o preço da opção vazio para usar o do produto, ou informe um valor."
        vid = v.get("id")
        if vid is not None and (isinstance(vid, bool) or not isinstance(vid, int) or vid not in existentes):
            erros[f"variacao_{i}"] = "Variação de outro produto."
        limpas.append((vid, nome, str(v.get("sku") or "").strip()[:60], preco, estoque or 0,
                       0 if v.get("ativo") is False else 1, i))
    if erros:
        raise ErroValidacao(erros, "Revise as variações.")

    conn.execute("BEGIN IMMEDIATE")
    try:
        mantidas = set()
        for vid, nome, sku, preco, estoque, ativo, ordem in limpas:
            if vid:
                conn.execute(
                    "UPDATE variacoes SET nome = ?, sku = ?, preco_centavos = ?, estoque = ?, ativo = ?, ordem = ? WHERE id = ?",
                    (nome, sku, preco, estoque, ativo, ordem, vid),
                )
                mantidas.add(vid)
            else:
                conn.execute(
                    "INSERT INTO variacoes (produto_id, nome, sku, preco_centavos, estoque, ativo, ordem) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (produto_id, nome, sku, preco, estoque, ativo, ordem),
                )
        for vid in existentes - mantidas:
            conn.execute("UPDATE variacoes SET ativo = 0 WHERE id = ?", (vid,))
        _sincronizar_estoque(conn, produto_id)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return obter_produto(conn, slug, incluir_inativos=True, admin=True)


# ---------------------------------------------------------------- galeria de fotos

def _atualizar_capa(conn, produto_id):
    primeira = conn.execute(
        "SELECT arquivo FROM fotos_produto WHERE produto_id = ? ORDER BY ordem, id LIMIT 1", (produto_id,)
    ).fetchone()
    conn.execute("UPDATE produtos SET foto = ? WHERE id = ?", (primeira["arquivo"] if primeira else "", produto_id))


def adicionar_foto(conn, slug, arquivo, miniatura=""):
    produto_id = _id_produto(conn, slug)
    # contagem e inserção na mesma transação: dois envios simultâneos não passam do limite
    conn.execute("BEGIN IMMEDIATE")
    try:
        total = conn.execute("SELECT COUNT(*) FROM fotos_produto WHERE produto_id = ?", (produto_id,)).fetchone()[0]
        if total >= config.FOTOS_POR_PRODUTO:
            raise ErroValidacao({"foto": f"Máximo de {config.FOTOS_POR_PRODUTO} fotos por produto."})
        ordem = conn.execute("SELECT COALESCE(MAX(ordem), -1) + 1 FROM fotos_produto WHERE produto_id = ?",
                             (produto_id,)).fetchone()[0]
        conn.execute("INSERT INTO fotos_produto (produto_id, arquivo, miniatura, ordem) VALUES (?, ?, ?, ?)",
                     (produto_id, arquivo, miniatura, ordem))
        _atualizar_capa(conn, produto_id)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return obter_produto(conn, slug, incluir_inativos=True, admin=True)


def remover_foto(conn, slug, foto_id):
    """Remove a foto do produto e devolve os nomes dos arquivos (foto e miniatura) para apagar do disco."""
    produto_id = _id_produto(conn, slug)
    row = conn.execute("SELECT arquivo, miniatura FROM fotos_produto WHERE id = ? AND produto_id = ?",
                       (foto_id, produto_id)).fetchone()
    if not row:
        raise NaoEncontrado("Foto não encontrada.")
    conn.execute("DELETE FROM fotos_produto WHERE id = ?", (foto_id,))
    _atualizar_capa(conn, produto_id)
    arquivos = [a for a in (row["arquivo"], row["miniatura"]) if a]
    return arquivos, obter_produto(conn, slug, incluir_inativos=True, admin=True)


def definir_capa(conn, slug, foto_id):
    produto_id = _id_produto(conn, slug)
    if not conn.execute("SELECT 1 FROM fotos_produto WHERE id = ? AND produto_id = ?", (foto_id, produto_id)).fetchone():
        raise NaoEncontrado("Foto não encontrada.")
    minimo = conn.execute("SELECT MIN(ordem) FROM fotos_produto WHERE produto_id = ?", (produto_id,)).fetchone()[0]
    conn.execute("UPDATE fotos_produto SET ordem = ? WHERE id = ?", (minimo - 1, foto_id))
    _atualizar_capa(conn, produto_id)
    return obter_produto(conn, slug, incluir_inativos=True, admin=True)
