"""Gatilhos de venda: ofertas relâmpago, prova social, avaliações, cupons, envio no dia e compras recentes.

Tudo deve sair de dados reais do banco — os testes conferem também o que NÃO pode aparecer.
"""

import re
import sqlite3
import unittest
from datetime import datetime, timezone
from unittest import mock

from loja import ajustes, config, cupons, db, horario, promocoes, regras
from tests.test_regras import CLIENTE, estoque, nova_conexao

CPF_2 = "111.444.777-35"


def pedido(conn, itens, **extra):
    return regras.criar_pedido(conn, {**CLIENTE, **extra, "itens": itens})


def entregar(conn, codigo):
    for status in ("pago", "enviado", "entregue"):
        regras.atualizar_status(conn, codigo, status)


def envelhecer(conn, codigo, dias=0, horas=0):
    conn.execute("UPDATE pedidos SET criado_em = datetime('now', ?, ?) WHERE codigo = ?",
                 (f"-{dias} days", f"-{horas} hours", codigo))


def produto(conn, slug, admin=False):
    return regras.obter_produto(conn, slug, incluir_inativos=admin, admin=admin)


def listado(conn, slug, **kwargs):
    return next(p for p in regras.listar_produtos(conn, **kwargs) if p["slug"] == slug)


def promo(conn, slug, pct, fim="2099-01-01T00:00:00Z"):
    return regras.atualizar_produto(conn, slug, {"promo_pct": pct, "promo_fim": fim})


class TestPromocoes(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def test_preco_com_desconto_arredonda_meio_para_cima(self):
        self.assertEqual(promocoes.preco_com_desconto(1990, 15), 1692)  # 1691,5
        self.assertEqual(promocoes.preco_com_desconto(1000, 33), 670)
        self.assertEqual(promocoes.preco_com_desconto(999, 10), 899)    # 899,1
        self.assertEqual(promocoes.preco_com_desconto(1990, None), 1990)

    def test_preco_ancora(self):
        self.assertEqual(promocoes.preco_ancora(1000, 1500, None), 1500)
        self.assertIsNone(promocoes.preco_ancora(1000, 1000, None))
        self.assertIsNone(promocoes.preco_ancora(1000, None, None))
        self.assertEqual(promocoes.preco_ancora(1000, 1500, 10), 1500)
        self.assertEqual(promocoes.preco_ancora(1000, 800, 10), 1000)
        self.assertEqual(promocoes.preco_ancora(1000, None, 10), 1000)

    def test_produto_em_oferta(self):
        p = promo(self.conn, "power-bank-20000mah", 15, "2099-01-01 12:00:00")
        self.assertEqual(p["preco_centavos"], 11990)  # o preço cadastrado não muda de sentido
        self.assertEqual(p["preco_final_centavos"], 10192)
        self.assertEqual(p["preco_ancora_centavos"], 11990)
        self.assertEqual(p["promo"], {"pct": 15, "fim": "2099-01-01T12:00:00Z"})
        self.assertEqual((p["promo_pct"], p["promo_fim"]), (15, "2099-01-01T12:00:00Z"))
        self.assertEqual(p["selos"][0], "oferta")
        publico = produto(self.conn, "power-bank-20000mah")
        self.assertNotIn("promo_pct", publico)
        self.assertEqual(listado(self.conn, "power-bank-20000mah")["preco_final_centavos"], 10192)

    def test_produto_sem_oferta(self):
        p = produto(self.conn, "power-bank-20000mah")
        self.assertEqual(p["preco_final_centavos"], p["preco_centavos"])
        self.assertIsNone(p["promo"])
        regras.atualizar_produto(self.conn, "power-bank-20000mah", {"preco_de_centavos": 15990})
        p = produto(self.conn, "power-bank-20000mah")
        self.assertEqual(p["preco_ancora_centavos"], 15990)
        self.assertIn("oferta", p["selos"])

    def test_oferta_vencida_some_sem_reiniciar(self):
        promo(self.conn, "power-bank-20000mah", 20)
        self.conn.execute("UPDATE produtos SET promo_fim = datetime('now', '-1 minute') WHERE slug = 'power-bank-20000mah'")
        p = produto(self.conn, "power-bank-20000mah", admin=True)
        self.assertIsNone(p["promo"])
        self.assertEqual(p["preco_final_centavos"], 11990)
        self.assertIsNone(p["preco_ancora_centavos"])
        self.assertNotIn("oferta", p["selos"])
        self.assertEqual(p["promo_pct"], 20)  # o painel ainda vê o que estava gravado
        # salvar o formulário inteiro de novo, com a oferta vencida sem mudança, não é bloqueado
        p = regras.atualizar_produto(self.conn, "power-bank-20000mah", {"nome": "Carregador novo", "promo_pct": 20,
                                                                         "promo_fim": p["promo_fim"]})
        self.assertEqual(p["nome"], "Carregador novo")
        with self.assertRaises(regras.ErroValidacao):  # mas mudar o desconto exige um término futuro
            regras.atualizar_produto(self.conn, "power-bank-20000mah", {"promo_pct": 25})
        c = regras.cotar_carrinho(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}])
        self.assertEqual(c["subtotal_centavos"], 11990)
        self.assertEqual(regras.listar_produtos(self.conn, promo=True), [])

    def test_validacao_no_painel(self):
        invalidos = [
            {"promo_pct": 10},                                          # sem término
            {"promo_fim": "2099-01-01T00:00:00Z"},                      # sem desconto
            {"promo_pct": 0, "promo_fim": "2099-01-01T00:00:00Z"},
            {"promo_pct": 91, "promo_fim": "2099-01-01T00:00:00Z"},
            {"promo_pct": True, "promo_fim": "2099-01-01T00:00:00Z"},
            {"promo_pct": "10", "promo_fim": "2099-01-01T00:00:00Z"},
            {"promo_pct": 10, "promo_fim": "2020-01-01T00:00:00Z"},     # no passado
            {"promo_pct": 10, "promo_fim": "amanhã"},
            {"promo_pct": 10, "promo_fim": 123},
            {"promo_pct": None, "promo_fim": "2099-01-01T00:00:00Z"},
        ]
        for dados in invalidos:
            with self.assertRaises(regras.ErroValidacao, msg=dados):
                regras.atualizar_produto(self.conn, "power-bank-20000mah", dados)
        self.assertIsNone(produto(self.conn, "power-bank-20000mah", admin=True)["promo_pct"])
        p = promo(self.conn, "power-bank-20000mah", 90, "2099-06-30T23:59:00-04:00")
        self.assertEqual(p["promo_fim"], "2099-07-01T03:59:00Z")  # gravado em UTC
        p = regras.atualizar_produto(self.conn, "power-bank-20000mah", {"promo_pct": 30})  # término mantido
        self.assertEqual(p["promo"]["pct"], 30)
        p = regras.atualizar_produto(self.conn, "power-bank-20000mah", {"promo_pct": None, "promo_fim": None})
        self.assertEqual((p["promo_pct"], p["promo_fim"], p["promo"]), (None, None, None))

    def test_variacoes_e_carrinho_com_oferta(self):
        promo(self.conn, "smartwatch-tela-amoled", 10)
        p = produto(self.conn, "smartwatch-tela-amoled")
        propria = next(v for v in p["variacoes"] if v["preco_centavos"])
        comum = next(v for v in p["variacoes"] if v["preco_centavos"] is None)
        self.assertEqual(propria["preco_final_centavos"], promocoes.preco_com_desconto(propria["preco_centavos"], 10))
        self.assertEqual(comum["preco_final_centavos"], promocoes.preco_com_desconto(p["preco_centavos"], 10))
        c = regras.cotar_carrinho(self.conn, [{"slug": "smartwatch-tela-amoled", "variacao": propria["id"], "quantidade": 2}])
        linha = c["itens"][0]
        self.assertEqual(linha["preco_unit_centavos"], propria["preco_final_centavos"])
        self.assertEqual(linha["preco_ancora_unit_centavos"], propria["preco_centavos"])
        self.assertEqual(c["subtotal_centavos"], 2 * propria["preco_final_centavos"])

    def test_pedido_grava_preco_com_oferta(self):
        promo(self.conn, "cabo-usb-c-reforcado-2m", 50)
        codigo = pedido(self.conn, [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 2}])
        pub = regras.obter_pedido_publico(self.conn, codigo)
        self.assertEqual(pub["itens"][0]["preco_unit_centavos"], 1245)
        self.assertEqual(pub["itens"][0]["preco_ancora_unit_centavos"], 2490)
        self.assertEqual(pub["subtotal_centavos"], 2490)
        # sem oferta, a linha não tem preço riscado
        c = regras.cotar_carrinho(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}])
        self.assertIsNone(c["itens"][0]["preco_ancora_unit_centavos"])

    def test_listagem_so_ofertas_e_ordem_por_preco_final(self):
        promo(self.conn, "power-bank-20000mah", 50, "2099-03-01T00:00:00Z")
        promo(self.conn, "cabo-usb-c-reforcado-2m", 10, "2099-01-01T00:00:00Z")
        self.assertEqual([p["slug"] for p in regras.listar_produtos(self.conn, promo=True)],
                         ["cabo-usb-c-reforcado-2m", "power-bank-20000mah"])
        precos = [p["preco_final_centavos"] for p in regras.listar_produtos(self.conn, ordem="menor_preco")]
        self.assertEqual(precos, sorted(precos))
        precos = [p["preco_final_centavos"] for p in regras.listar_produtos(self.conn, ordem="maior_preco")]
        self.assertEqual(precos, sorted(precos, reverse=True))


class TestProvaSocial(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)
        # catálogo de demonstração "antigo", para o selo de novidade não aparecer em tudo
        self.conn.execute("UPDATE produtos SET criado_em = datetime('now', '-60 days')")

    def test_vendidos_30d_so_conta_pedidos_validos_e_recentes(self):
        pedido(self.conn, [{"slug": "fita-led-rgb-5m", "quantidade": 2}])
        cancelado = pedido(self.conn, [{"slug": "fita-led-rgb-5m", "quantidade": 5}])
        regras.atualizar_status(self.conn, cancelado, "cancelado")
        antigo = pedido(self.conn, [{"slug": "fita-led-rgb-5m", "quantidade": 4}])
        regras.atualizar_status(self.conn, antigo, "pago")
        envelhecer(self.conn, antigo, dias=31)
        self.assertEqual(listado(self.conn, "fita-led-rgb-5m")["vendidos_30d"], 2)
        self.assertEqual(produto(self.conn, "fita-led-rgb-5m")["vendidos_30d"], 2)
        self.assertEqual(listado(self.conn, "power-bank-20000mah")["vendidos_30d"], 0)

    def test_selo_mais_vendido_top3_da_categoria_com_minimo_de_3(self):
        cat = "eletronicos"
        mesmos = [regras.criar_produto(self.conn, {"nome": f"Produto de teste {i}", "categoria": cat,
                                                   "preco_centavos": 1000, "estoque": 20})["slug"] for i in range(5)]
        for slug, qtd in zip(mesmos, (9, 7, 5, 4, 2)):
            pedido(self.conn, [{"slug": slug, "quantidade": qtd}])
        selos = {slug: listado(self.conn, slug)["selos"] for slug in mesmos}
        self.assertEqual([("mais_vendido" in selos[s]) for s in mesmos], [True, True, True, False, False])
        ordem = [p["slug"] for p in regras.listar_produtos(self.conn, categoria=cat, ordem="mais_vendidos")]
        self.assertEqual(ordem[:5], mesmos)
        pagina = regras.listar_produtos(self.conn, categoria=cat, ordem="mais_vendidos", limite=2, offset=1)
        self.assertEqual([p["slug"] for p in pagina], mesmos[1:3])
        # menos de 3 vendidos nunca é "mais vendido", mesmo sendo o único da categoria a vender
        conn = nova_conexao()
        self.addCleanup(conn.close)
        pedido(conn, [{"slug": "power-bank-20000mah", "quantidade": 2}])
        self.assertNotIn("mais_vendido", listado(conn, "power-bank-20000mah")["selos"])

    def test_novidade_e_ultimas_unidades_na_ordem_certa(self):
        self.conn.execute("UPDATE produtos SET criado_em = datetime('now', '-3 days'), preco_de_centavos = 99999, "
                          "estoque = 4 WHERE slug = 'power-bank-20000mah'")
        self.assertEqual(listado(self.conn, "power-bank-20000mah")["selos"], ["oferta", "novidade", "ultimas_unidades"])
        self.conn.execute("UPDATE produtos SET estoque = 0 WHERE slug = 'power-bank-20000mah'")
        self.assertNotIn("ultimas_unidades", listado(self.conn, "power-bank-20000mah")["selos"])
        self.conn.execute("UPDATE produtos SET estoque = 6, criado_em = datetime('now', '-15 days'), "
                          "preco_de_centavos = NULL WHERE slug = 'power-bank-20000mah'")
        self.assertEqual(listado(self.conn, "power-bank-20000mah")["selos"], [])

    def test_listagem_usa_consultas_agregadas(self):
        """O número de consultas não cresce com o número de produtos listados."""
        for slug in ("power-bank-20000mah", "fita-led-rgb-5m", "cabo-usb-c-reforcado-2m"):
            pedido(self.conn, [{"slug": slug, "quantidade": 1}])
        consultas = []
        self.conn.set_trace_callback(consultas.append)
        self.addCleanup(self.conn.set_trace_callback, None)
        lista = regras.listar_produtos(self.conn, ordem="mais_vendidos")
        self.assertGreater(len(lista), 10)
        self.assertEqual(len(consultas), 2)  # o agregado de vendas e a listagem
        consultas.clear()
        regras.listar_produtos(self.conn, limite=3)
        self.assertEqual(len(consultas), 2)

    def test_comprados_juntos(self):
        self.assertEqual(produto(self.conn, "power-bank-20000mah")["comprados_juntos"], [])
        for _ in range(2):
            pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1},
                               {"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}])
        pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}, {"slug": "fita-led-rgb-5m", "quantidade": 1}])
        cancelado = pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1},
                                       {"slug": "mini-projetor-portatil", "quantidade": 1}])
        regras.atualizar_status(self.conn, cancelado, "cancelado")
        juntos = produto(self.conn, "power-bank-20000mah")["comprados_juntos"]
        self.assertEqual([p["slug"] for p in juntos], ["cabo-usb-c-reforcado-2m", "fita-led-rgb-5m"])
        self.assertNotIn("descricao", juntos[0])
        self.assertIn("preco_final_centavos", juntos[0])
        # sem estoque ou fora do ar não é sugerido
        regras.atualizar_produto(self.conn, "cabo-usb-c-reforcado-2m", {"estoque": 0})
        regras.atualizar_produto(self.conn, "fita-led-rgb-5m", {"ativo": False})
        self.assertEqual(produto(self.conn, "power-bank-20000mah")["comprados_juntos"], [])

    def test_vendas_recentes(self):
        self.assertEqual(regras.vendas_recentes(self.conn), [])
        pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}], cidade="Parintins", cep="69151-000")
        velho = pedido(self.conn, [{"slug": "fita-led-rgb-5m", "quantidade": 1}])
        envelhecer(self.conn, velho, horas=73)
        cancelado = pedido(self.conn, [{"slug": "mini-projetor-portatil", "quantidade": 1}])
        regras.atualizar_status(self.conn, cancelado, "cancelado")
        mais_novo = pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1},
                                       {"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}], cidade="Boa Vista", uf="RR")
        envelhecer(self.conn, mais_novo, horas=0)
        vendas = regras.vendas_recentes(self.conn)
        self.assertEqual(sorted(v["slug"] for v in vendas), ["cabo-usb-c-reforcado-2m", "power-bank-20000mah"])
        power = next(v for v in vendas if v["slug"] == "power-bank-20000mah")
        self.assertEqual(set(power), {"produto", "slug", "imagem", "cor", "icone", "cidade", "uf", "minutos_atras"})
        self.assertEqual((power["cidade"], power["uf"]), ("Boa Vista", "RR"))  # a compra mais nova do produto
        self.assertEqual(power["minutos_atras"], 0)
        self.assertNotIn("Maria", str(vendas))
        # no máximo 8, um por produto, a mais nova primeiro
        slugs = [p["slug"] for p in regras.listar_produtos(self.conn) if not p["tem_variacoes"] and p["estoque"] > 2][:10]
        for i, slug in enumerate(slugs):
            codigo = pedido(self.conn, [{"slug": slug, "quantidade": 1}])
            self.conn.execute("UPDATE pedidos SET criado_em = datetime('now', ?) WHERE codigo = ?", (f"-{100 - i} minutes", codigo))
        vendas = regras.vendas_recentes(self.conn)
        self.assertEqual(len(vendas), 8)
        self.assertEqual(len({v["slug"] for v in vendas}), 8)
        minutos = [v["minutos_atras"] for v in vendas]
        self.assertEqual(minutos, sorted(minutos))


class TestAvaliacoes(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)
        self.codigo = pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1},
                                         {"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}], cidade="Parintins",
                             cep="69151-000", nome="maria da silva")

    def avaliar(self, **dados):
        return regras.criar_avaliacao(self.conn, {"codigo": self.codigo, "email": CLIENTE["email"],
                                                  "slug": "power-bank-20000mah", "nota": 5, "comentario": "Chegou rápido",
                                                  **dados})

    def erro(self, **dados):
        with self.assertRaises(regras.ErroValidacao) as ctx:
            self.avaliar(**dados)
        return ctx.exception.campos

    def test_so_depois_de_entregue(self):
        self.assertIn("entregue", self.erro()["codigo"])
        self.assertFalse(any(i["pode_avaliar"] for i in regras.obter_pedido_publico(self.conn, self.codigo)["itens"]))
        entregar(self.conn, self.codigo)
        itens = regras.obter_pedido_publico(self.conn, self.codigo)["itens"]
        self.assertEqual([(i["slug"], i["pode_avaliar"]) for i in itens],
                         [("power-bank-20000mah", True), ("cabo-usb-c-reforcado-2m", True)])
        self.assertEqual(self.avaliar(email="  MARIA@Example.com "), {"status": "pendente"})
        itens = regras.obter_pedido_publico(self.conn, self.codigo)["itens"]
        self.assertEqual([i["pode_avaliar"] for i in itens], [False, True])
        self.assertIn("já avaliou", self.erro()["slug"])
        self.assertNotIn("pode_avaliar", regras.listar_pedidos(self.conn)[0]["itens"][0])

    def test_erros_claros(self):
        entregar(self.conn, self.codigo)
        self.assertIn("não encontrado", self.erro(codigo="TPT-NAOEXISTE00")["codigo"])
        self.assertIn("e-mail", self.erro(email="outra@example.com")["email"])
        self.assertIn("não faz parte", self.erro(slug="fita-led-rgb-5m")["slug"])
        self.assertIn("não faz parte", self.erro(slug="nao-existe")["slug"])
        for nota in (0, 6, "5", True, None, 4.5):
            self.assertIn("nota", self.erro(nota=nota))
        self.assertIn("comentario", self.erro(comentario="x" * 1001))
        self.assertIn("comentario", self.erro(comentario=["x"]))
        self.assertEqual(self.avaliar(comentario=None, nota=1), {"status": "pendente"})
        with self.assertRaises(regras.ErroValidacao):
            regras.criar_avaliacao(self.conn, ["x"])

    def test_moderacao_media_e_lista_publica(self):
        entregar(self.conn, self.codigo)
        self.avaliar(nota=4)
        outros = []
        for nota, nome in ((5, "João Souza"), (5, "Ana Lima")):
            codigo = pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}], nome=nome, cidade="Manaus")
            entregar(self.conn, codigo)
            regras.criar_avaliacao(self.conn, {"codigo": codigo, "email": CLIENTE["email"], "slug": "power-bank-20000mah",
                                               "nota": nota, "comentario": ""})
            outros.append(codigo)
        p = produto(self.conn, "power-bank-20000mah")
        self.assertEqual((p["nota_media"], p["avaliacoes_total"]), (None, 0))  # pendentes não contam
        self.assertEqual(regras.listar_avaliacoes(self.conn, "power-bank-20000mah"), [])

        admin = regras.listar_avaliacoes_admin(self.conn)
        self.assertEqual(len(admin), 3)
        self.assertEqual(set(admin[0]), {"id", "produto", "pedido", "nome", "nota", "comentario", "status", "data"})
        self.assertEqual(admin[-1]["nome"], "Maria de Parintins")
        self.assertEqual(admin[-1]["pedido"], self.codigo)
        self.assertEqual(admin[-1]["produto"], {"nome": p["nome"], "slug": "power-bank-20000mah"})
        for a in admin:
            regras.moderar_avaliacao(self.conn, a["id"], "aprovada")
        p = produto(self.conn, "power-bank-20000mah")
        self.assertEqual((p["nota_media"], p["avaliacoes_total"]), (4.7, 3))
        self.assertEqual(listado(self.conn, "power-bank-20000mah")["nota_media"], 4.7)
        publicas = regras.listar_avaliacoes(self.conn, "power-bank-20000mah")
        self.assertEqual([a["nome"] for a in publicas], ["Ana de Manaus", "João de Manaus", "Maria de Parintins"])
        self.assertEqual(set(publicas[0]), {"nome", "nota", "comentario", "data"})
        self.assertRegex(publicas[0]["data"], r"^\d{4}-\d{2}-\d{2}$")

        oculta = regras.moderar_avaliacao(self.conn, admin[0]["id"], "oculta")
        self.assertEqual(oculta["status"], "oculta")
        self.assertEqual(produto(self.conn, "power-bank-20000mah")["avaliacoes_total"], 2)
        self.assertEqual([a["status"] for a in regras.listar_avaliacoes_admin(self.conn, "oculta")], ["oculta"])
        regras.moderar_avaliacao(self.conn, admin[1]["id"], "pendente")
        self.assertEqual(regras.listar_avaliacoes_admin(self.conn)[0]["status"], "pendente")  # pendentes primeiro
        for status in ("apagada", None, ["aprovada"]):
            with self.assertRaises(regras.ErroValidacao):
                regras.moderar_avaliacao(self.conn, admin[0]["id"], status)
        with self.assertRaises(regras.ErroValidacao):
            regras.listar_avaliacoes_admin(self.conn, "x")
        with self.assertRaises(regras.NaoEncontrado):
            regras.moderar_avaliacao(self.conn, 999, "aprovada")
        with self.assertRaises(regras.NaoEncontrado):
            regras.listar_avaliacoes(self.conn, "nao-existe")

    def test_media_com_uma_casa(self):
        self.assertEqual(regras.nota_media(9, 2), 4.5)
        self.assertEqual(regras.nota_media(13, 3), 4.3)
        self.assertEqual(regras.nota_media(29, 6), 4.8)  # 4,833…
        self.assertIsNone(regras.nota_media(None, 0))

    def test_unica_por_pedido_e_produto_no_banco(self):
        entregar(self.conn, self.codigo)
        self.avaliar()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO avaliacoes (produto_id, pedido_id, nota, nome_exibicao) "
                              "SELECT produto_id, pedido_id, 3, 'x' FROM avaliacoes")


class TestCupons(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def cupom(self, **dados):
        return regras.criar_cupom(self.conn, {"codigo": "TESTE10", "tipo": "pct", "valor": 10, **dados})

    def cotar(self, cupom, itens=None, **kwargs):
        itens = itens or [{"slug": "power-bank-20000mah", "quantidade": 1}]  # R$ 119,90
        return regras.cotar_carrinho(self.conn, itens, cupom=cupom, **kwargs)

    def test_descricao_e_formato(self):
        self.assertEqual(regras.formatar_reais(123456789), "R$ 1.234.567,89")
        self.assertEqual(regras.formatar_reais(5), "R$ 0,05")
        self.assertEqual(self.cupom()["descricao"], "10% de desconto")
        c = regras.criar_cupom(self.conn, {"codigo": "menos15", "tipo": "valor", "valor": 1500, "minimo_centavos": 9900})
        self.assertEqual((c["codigo"], c["descricao"]), ("MENOS15", "R$ 15,00 de desconto acima de R$ 99,00"))
        c = regras.criar_cupom(self.conn, {"codigo": "FRETE", "tipo": "frete", "valor": 500, "so_primeira_compra": True})
        self.assertEqual((c["valor"], c["descricao"]), (0, "Frete grátis na primeira compra"))
        self.assertEqual(c["usos"], 0)
        self.assertTrue(c["ativo"])
        self.assertFalse(c["destaque"])

    def test_validacao_do_cadastro(self):
        invalidos = [
            ({"codigo": "AB"}, "codigo"), ({"codigo": "COM ESPACO"}, "codigo"), ({"codigo": "Ç123"}, "codigo"),
            ({"codigo": "X" * 21}, "codigo"), ({"tipo": "brinde"}, "tipo"), ({"valor": 0}, "valor"),
            ({"valor": 91}, "valor"), ({"valor": "10"}, "valor"), ({"tipo": "valor", "valor": 0}, "valor"),
            ({"minimo_centavos": -1}, "minimo_centavos"), ({"limite_usos": 0}, "limite_usos"),
            ({"inicio": "ontem"}, "inicio"),
            ({"inicio": "2099-01-02T00:00:00Z", "fim": "2099-01-01T00:00:00Z"}, "fim"),
        ]
        for dados, campo in invalidos:
            with self.assertRaises(regras.ErroValidacao, msg=dados) as ctx:
                self.cupom(**dados)
            self.assertIn(campo, ctx.exception.campos, dados)
        self.cupom()
        with self.assertRaises(regras.ErroValidacao) as ctx:
            self.cupom(codigo="teste10")
        self.assertIn("Já existe", ctx.exception.campos["codigo"])
        with self.assertRaises(regras.ErroValidacao):
            regras.criar_cupom(self.conn, "x")

    def test_editar(self):
        self.cupom(limite_usos=5)
        c = regras.atualizar_cupom(self.conn, "teste10", {"tipo": "valor", "valor": 2000, "fim": "2099-01-01 00:00:00",
                                                          "codigo": "TESTE10", "usos": 0})
        self.assertEqual((c["tipo"], c["valor"], c["fim"], c["limite_usos"]), ("valor", 2000, "2099-01-01T00:00:00Z", 5))
        c = regras.atualizar_cupom(self.conn, "TESTE10", {"limite_usos": None, "ativo": False})
        self.assertEqual((c["limite_usos"], c["ativo"], c["vigente"]), (None, False, False))
        for dados in ({"codigo": "OUTRO"}, {"usos": 3}, {"tipo": "pct"}, {"tipo": "pct", "valor": 95}):
            with self.assertRaises(regras.ErroValidacao, msg=dados):
                regras.atualizar_cupom(self.conn, "TESTE10", dados)
        with self.assertRaises(regras.NaoEncontrado):
            regras.atualizar_cupom(self.conn, "NAOEXISTE", {"ativo": True})

    def test_so_um_em_destaque(self):
        self.cupom(destaque=True)
        regras.criar_cupom(self.conn, {"codigo": "OUTRO", "tipo": "frete", "destaque": True})
        self.assertEqual({c["codigo"]: c["destaque"] for c in regras.listar_cupons(self.conn)},
                         {"TESTE10": False, "OUTRO": True})
        self.assertEqual(regras.cupom_destaque(self.conn), {"codigo": "OUTRO", "descricao": "Frete grátis"})
        regras.atualizar_cupom(self.conn, "TESTE10", {"destaque": True})
        self.assertEqual(regras.cupom_destaque(self.conn)["codigo"], "TESTE10")
        regras.atualizar_cupom(self.conn, "TESTE10", {"fim": "2020-01-01T00:00:00Z"})  # vencido não aparece
        self.assertIsNone(regras.cupom_destaque(self.conn))

    def test_ordem_do_calculo_cupom_pix_frete(self):
        promo(self.conn, "power-bank-20000mah", 10)  # 11990 -> 10791
        self.cupom()
        c = self.cotar("teste10", cep="69005000")
        self.assertEqual(c["subtotal_centavos"], 10791)
        self.assertEqual(c["desconto_cupom_centavos"], 1079)            # 10% de 10791
        self.assertEqual(c["desconto_centavos"], (10791 - 1079) * 5 // 100)  # Pix sobre o que sobrou
        self.assertEqual(c["frete"]["valor_centavos"], 990)
        self.assertEqual(c["total_centavos"], 10791 - 1079 - 485 + 990)
        self.assertEqual(c["cupom"], {"codigo": "TESTE10", "descricao": "10% de desconto", "desconto_centavos": 1079,
                                      "frete_gratis": False})
        self.assertIsNone(c["cupom_erro"])
        self.assertEqual(c["economia_centavos"], (11990 - 10791) + 1079 + 485)
        cartao = self.cotar("TESTE10", pagamento="cartao", cep="69005000")
        self.assertEqual(cartao["desconto_centavos"], 0)
        self.assertEqual(cartao["total_centavos"], 10791 - 1079 + 990)
        self.assertEqual(cartao["parcelas_max"], regras.parcelas_maximas(10791 - 1079 + 990))
        sem = self.cotar(None)
        self.assertEqual((sem["cupom"], sem["cupom_erro"], sem["desconto_cupom_centavos"]), (None, None, 0))
        self.assertEqual(sem["economia_centavos"], (11990 - 10791) + sem["desconto_centavos"])

    def test_valor_fixo_limitado_ao_subtotal_e_frete_gratis(self):
        regras.criar_cupom(self.conn, {"codigo": "GRANDE", "tipo": "valor", "valor": 10 ** 6})
        c = self.cotar("grande", cep="69005000")
        self.assertEqual(c["desconto_cupom_centavos"], 11990)
        self.assertEqual((c["desconto_centavos"], c["total_centavos"]), (0, 990))
        regras.criar_cupom(self.conn, {"codigo": "FRETE", "tipo": "frete"})
        c = self.cotar("frete", cep="01310100")  # fora do Norte também
        self.assertEqual(c["frete"]["valor_centavos"], 0)
        self.assertTrue(c["frete"]["gratis"])
        self.assertTrue(c["cupom"]["frete_gratis"])
        self.assertEqual(c["desconto_cupom_centavos"], 0)
        self.assertEqual(c["falta_para_frete_gratis"], 0)
        self.assertEqual(c["total_centavos"], 11990 - 11990 * 5 // 100)

    def test_mensagens_de_erro(self):
        self.cupom(minimo_centavos=15000)
        c = self.cotar("teste10")
        self.assertIsNone(c["cupom"])
        self.assertEqual(c["desconto_cupom_centavos"], 0)
        self.assertEqual(c["cupom_erro"], "Faltam R$ 30,10 para usar este cupom (compras a partir de R$ 150,00).")
        self.assertEqual(self.cotar("NAOEXISTE")["cupom_erro"], "Cupom inválido. Confira o código.")
        self.assertEqual(self.cotar("x")["cupom_erro"], "Cupom inválido. Confira o código.")
        self.assertEqual(self.cotar(123)["cupom_erro"], "Cupom inválido. Confira o código.")
        regras.atualizar_cupom(self.conn, "TESTE10", {"minimo_centavos": 0, "ativo": False})
        self.assertIn("inválido", self.cotar("teste10")["cupom_erro"])
        regras.atualizar_cupom(self.conn, "TESTE10", {"ativo": True, "fim": "2020-01-01T00:00:00Z"})
        self.assertEqual(self.cotar("teste10")["cupom_erro"], "Este cupom expirou.")
        regras.atualizar_cupom(self.conn, "TESTE10", {"fim": None, "inicio": "2099-01-01T00:00:00Z"})
        self.assertIn("ainda não", self.cotar("teste10")["cupom_erro"])
        regras.atualizar_cupom(self.conn, "TESTE10", {"inicio": None, "limite_usos": 1})
        self.conn.execute("UPDATE cupons SET usos = 1")
        self.assertIn("limite de usos", self.cotar("teste10")["cupom_erro"])

    def test_primeira_compra(self):
        self.cupom(so_primeira_compra=True)
        self.assertIsNone(self.cotar("teste10", cpf=CLIENTE["cpf"])["cupom_erro"])
        codigo = pedido(self.conn, [{"slug": "fita-led-rgb-5m", "quantidade": 1}])
        self.assertIn("primeira compra", self.cotar("teste10", cpf=CLIENTE["cpf"])["cupom_erro"])
        self.assertIsNone(self.cotar("teste10", cpf=CPF_2)["cupom_erro"])
        self.assertIsNone(self.cotar("teste10")["cupom_erro"])  # sem CPF, a regra é conferida no pedido
        with self.assertRaises(regras.ErroValidacao) as ctx:
            pedido(self.conn, [{"slug": "fita-led-rgb-5m", "quantidade": 1}], cupom="teste10")
        self.assertIn("primeira compra", ctx.exception.campos["cupom"])
        regras.atualizar_status(self.conn, codigo, "cancelado")  # pedido cancelado não conta como compra
        pedido(self.conn, [{"slug": "fita-led-rgb-5m", "quantidade": 1}], cupom="teste10")

    def test_pedido_com_cupom_conta_uso_e_cancelamento_devolve(self):
        regras.atualizar_produto(self.conn, "power-bank-20000mah", {"custo_centavos": 5000})
        self.cupom(limite_usos=2)
        antes = estoque(self.conn, "power-bank-20000mah")
        codigo = pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}], cupom=" teste10 ")
        pub = regras.obter_pedido_publico(self.conn, codigo)
        self.assertEqual((pub["cupom_codigo"], pub["desconto_cupom_centavos"]), ("TESTE10", 1199))
        self.assertEqual(pub["desconto_centavos"], (11990 - 1199) * 5 // 100)
        self.assertEqual(pub["total_centavos"], 11990 - 1199 - pub["desconto_centavos"] + 990)
        admin = regras.listar_pedidos(self.conn)[0]
        self.assertEqual(admin["cupom_codigo"], "TESTE10")
        self.assertEqual(admin["lucro_centavos"], 11990 - 1199 - pub["desconto_centavos"] - 5000)
        self.assertEqual(regras.resumo_vendas(self.conn)["lucro_centavos"], admin["lucro_centavos"])
        self.assertEqual(regras.listar_cupons(self.conn)[0]["usos"], 1)

        pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}], cupom="TESTE10")
        with self.assertRaises(regras.ErroValidacao) as ctx:  # limite de 2 usos
            pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}], cupom="TESTE10")
        self.assertIn("cupom", ctx.exception.campos)
        self.assertEqual(estoque(self.conn, "power-bank-20000mah"), antes - 2)  # o pedido recusado não baixou nada
        self.assertFalse(self.conn.in_transaction)

        regras.atualizar_status(self.conn, codigo, "cancelado")
        regras.atualizar_status(self.conn, codigo, "cancelado")  # cancelar de novo não devolve outra vez
        self.assertEqual(regras.listar_cupons(self.conn)[0]["usos"], 1)
        pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}], cupom="TESTE10")
        self.assertEqual(regras.listar_cupons(self.conn)[0]["usos"], 2)

    def test_pedido_expirado_devolve_uso(self):
        self.cupom(limite_usos=1)
        codigo = pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}], cupom="TESTE10")
        self.assertEqual(regras.listar_cupons(self.conn)[0]["usos"], 1)
        envelhecer(self.conn, codigo, horas=config.PRAZO_RESERVA_HORAS + 1)
        regras.expirar_pendentes(self.conn)
        self.assertEqual(regras.listar_cupons(self.conn)[0]["usos"], 0)

    def test_cupom_invalido_no_pedido(self):
        for valor in ("NAOEXISTE", 10, ["X"]):
            with self.assertRaises(regras.ErroValidacao) as ctx:
                pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}], cupom=valor)
            self.assertIn("cupom", ctx.exception.campos)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0], 0)
        codigo = pedido(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}], cupom="")
        pub = regras.obter_pedido_publico(self.conn, codigo)
        self.assertEqual((pub["cupom_codigo"], pub["desconto_cupom_centavos"]), (None, 0))

    def test_uso_e_atomico(self):
        """O limite é conferido e consumido no mesmo UPDATE (dentro da transação do pedido)."""
        self.cupom(limite_usos=1)
        self.conn.execute("BEGIN IMMEDIATE")
        self.assertTrue(cupons.registrar_uso(self.conn, "TESTE10"))
        self.assertFalse(cupons.registrar_uso(self.conn, "TESTE10"))
        self.conn.execute("ROLLBACK")


class TestEnvioHojeEAjustes(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def envio(self, corte, ano, mes, dia, hora, minuto=0):
        return ajustes.envio_hoje({"horario_corte": corte}, datetime(ano, mes, dia, hora, minuto, tzinfo=timezone.utc))

    def test_envio_hoje_no_horario_de_manaus(self):
        # 09/10/2026 é sexta-feira; 13:00 UTC = 09:00 em Manaus
        self.assertEqual(self.envio("14:00", 2026, 10, 9, 13), {"ate": "2026-10-09T18:00:00Z"})
        self.assertIsNone(self.envio("14:00", 2026, 10, 9, 18))       # 14:00 em Manaus: já passou
        self.assertIsNone(self.envio("14:00", 2026, 10, 10, 13))      # sábado
        self.assertIsNone(self.envio("14:00", 2026, 10, 11, 13))      # domingo
        self.assertEqual(self.envio("14:00", 2026, 10, 12, 13), {"ate": "2026-10-12T18:00:00Z"})  # segunda
        # sábado 02:00 UTC ainda é sexta 22:00 em Manaus
        self.assertEqual(self.envio("23:00", 2026, 10, 10, 2), {"ate": "2026-10-10T03:00:00Z"})
        # segunda 02:00 UTC ainda é domingo em Manaus
        self.assertIsNone(self.envio("23:00", 2026, 10, 12, 2))
        self.assertIsNone(self.envio("", 2026, 10, 9, 13))
        self.assertIsNone(self.envio("25:00", 2026, 10, 9, 13))

    def test_ajustes_novos(self):
        valores = ajustes.obter(self.conn)
        self.assertEqual((valores["horario_corte"], valores["prova_social"]), ("", "1"))
        valores = ajustes.salvar(self.conn, {"horario_corte": " 14:30 ", "prova_social": False})
        self.assertEqual((valores["horario_corte"], valores["prova_social"]), ("14:30", "0"))
        self.assertEqual(ajustes.salvar(self.conn, {"prova_social": "1"})["prova_social"], "1")
        self.assertEqual(ajustes.salvar(self.conn, {"horario_corte": ""})["horario_corte"], "")
        for dados in ({"horario_corte": "24:00"}, {"horario_corte": "9:00"}, {"horario_corte": "14h"},
                      {"prova_social": "talvez"}):
            with self.assertRaises(regras.ErroValidacao, msg=dados):
                ajustes.salvar(self.conn, dados)

    def test_horario_relogio_e_datas(self):
        self.assertEqual(horario.ler_data("2026-10-09T15:00:00Z"), "2026-10-09 15:00:00")
        self.assertEqual(horario.ler_data("2026-10-09 15:00:00"), "2026-10-09 15:00:00")
        self.assertEqual(horario.ler_data("2026-10-09T11:00:00-04:00"), "2026-10-09 15:00:00")
        self.assertEqual(horario.iso_z("2026-10-09 15:00:00"), "2026-10-09T15:00:00Z")
        self.assertIsNone(horario.iso_z(None))
        for invalido in ("", "ontem", "2026-13-01T00:00:00Z", None, 5):
            with self.assertRaises((ValueError, TypeError)):
                horario.ler_data(invalido)
        with mock.patch.object(horario, "agora", return_value=datetime(2026, 10, 9, 13, tzinfo=timezone.utc)):
            ajustes.salvar(self.conn, {"horario_corte": "14:00"})
            self.assertEqual(ajustes.envio_hoje(ajustes.obter(self.conn)), {"ate": "2026-10-09T18:00:00Z"})


class TestMigracaoDeBancoAntigo(unittest.TestCase):
    def test_banco_sem_as_tabelas_e_colunas_novas(self):
        conn = db.conectar(":memory:")
        self.addCleanup(conn.close)
        antigo = re.sub(r"CREATE TABLE IF NOT EXISTS (cupons|avaliacoes) \(.*?\n\);\n", "", db.ESQUEMA, flags=re.S)
        antigo = "\n".join(linha for linha in antigo.splitlines()
                           if "avaliacoes" not in linha and "idx_pedidos_criado" not in linha)
        conn.executescript(antigo)
        self.assertNotIn("promo_pct", {r["name"] for r in conn.execute("PRAGMA table_info(produtos)")})
        conn.execute("INSERT INTO categorias (id, slug, nome) VALUES (1, 'casa', 'Casa')")
        conn.execute("INSERT INTO produtos (id, slug, nome, categoria_id, preco_centavos, estoque, criado_em) "
                     "VALUES (1, 'balde', 'Balde', 1, 1000, 3, '2020-01-01 00:00:00')")
        conn.execute("""INSERT INTO pedidos (id, codigo, status, cliente_nome, cliente_email, cliente_cpf, cliente_telefone,
                            cep, endereco, numero, bairro, cidade, uf, zona_frete, prazo_dias, pagamento,
                            subtotal_centavos, desconto_centavos, frete_centavos, total_centavos, criado_em)
                        VALUES (1, 'TPT-ANTIGO2345', 'entregue', 'Rita Alves', 'rita@example.com', '52998224725',
                                '92991234567', '69005000', 'Rua A', '1', 'Centro', 'Manaus', 'AM', 'Manaus (AM)', 3,
                                'pix', 2000, 100, 990, 2890, '2020-01-01 10:00:00')""")
        conn.execute("INSERT INTO itens_pedido (pedido_id, produto_id, nome, preco_unit_centavos, quantidade) "
                     "VALUES (1, 1, 'Balde', 1000, 2)")

        db.inicializar(conn)
        colunas = {r["name"] for r in conn.execute("PRAGMA table_info(produtos)")}
        self.assertTrue({"promo_pct", "promo_fim"} <= colunas)
        colunas = {r["name"] for r in conn.execute("PRAGMA table_info(pedidos)")}
        self.assertTrue({"cupom_codigo", "desconto_cupom_centavos"} <= colunas)
        p = regras.obter_produto(conn, "balde")
        self.assertEqual((p["preco_final_centavos"], p["promo"], p["vendidos_30d"]), (1000, None, 0))  # pedido antigo
        self.assertEqual(p["selos"], ["ultimas_unidades"])
        pub = regras.obter_pedido_publico(conn, "TPT-ANTIGO2345")
        self.assertEqual((pub["cupom_codigo"], pub["desconto_cupom_centavos"]), (None, 0))
        self.assertTrue(pub["itens"][0]["pode_avaliar"])
        self.assertEqual(regras.criar_avaliacao(conn, {"codigo": "TPT-ANTIGO2345", "email": "rita@example.com",
                                                       "slug": "balde", "nota": 5}), {"status": "pendente"})
        self.assertEqual(regras.resumo_vendas(conn)["pedidos"], 1)
        regras.criar_cupom(conn, {"codigo": "NOVO", "tipo": "frete"})
        db.inicializar(conn)  # rodar de novo não muda nada
        self.assertEqual(len(regras.listar_cupons(conn)), 1)


if __name__ == "__main__":
    unittest.main()
