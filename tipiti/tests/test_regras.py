import unittest

from loja import config, db, frete, regras

CLIENTE = {
    "nome": "Maria da Silva", "email": "maria@example.com", "cpf": "529.982.247-25",
    "telefone": "(92) 99123-4567", "cep": "69005-000", "endereco": "Av. Eduardo Ribeiro",
    "numero": "100", "complemento": "", "bairro": "Centro", "cidade": "Manaus", "uf": "AM",
    "pagamento": "pix", "parcelas": 1,
}


def nova_conexao():
    conn = db.conectar(":memory:")
    db.inicializar(conn)
    return conn


def estoque(conn, slug):
    return conn.execute("SELECT estoque FROM produtos WHERE slug = ?", (slug,)).fetchone()[0]


class TestValidacoes(unittest.TestCase):
    def test_cpf(self):
        self.assertTrue(regras.cpf_valido("529.982.247-25"))
        self.assertFalse(regras.cpf_valido("529.982.247-24"))
        self.assertFalse(regras.cpf_valido("111.111.111-11"))
        self.assertFalse(regras.cpf_valido("123"))

    def test_email(self):
        self.assertTrue(regras.email_valido("a@b.com.br"))
        self.assertFalse(regras.email_valido("a@b"))
        self.assertFalse(regras.email_valido(""))


class TestFrete(unittest.TestCase):
    def test_cidades_do_norte(self):
        casos = {
            "69005000": "manaus", "69151000": "parintins", "69301000": "boa-vista",
            "68005000": "santarem", "68900000": "macapa", "66010000": "belem",
            "69400000": "interior-am", "68440000": "interior-pa",
        }
        for cep, zona in casos.items():
            self.assertEqual(frete.zona_do_cep(cep)[0], zona, cep)

    def test_fora_do_norte(self):
        zid, *_, norte = frete.zona_do_cep("01310100")
        self.assertEqual(zid, "demais-regioes")
        self.assertFalse(norte)

    def test_frete_gratis_so_no_norte(self):
        self.assertTrue(frete.cotar("69151000", config.FRETE_GRATIS_A_PARTIR)["gratis"])
        self.assertFalse(frete.cotar("69151000", config.FRETE_GRATIS_A_PARTIR - 1)["gratis"])
        self.assertFalse(frete.cotar("01310100", 10 ** 6)["gratis"])


class TestCatalogo(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()

    def test_busca_ignora_acentos(self):
        nomes = [p["nome"] for p in regras.listar_produtos(self.conn, busca="oculos")]
        self.assertIn("Óculos de sol polarizado UV400", nomes)

    def test_busca_trata_curinga(self):
        self.assertEqual(regras.listar_produtos(self.conn, busca="%"), [])

    def test_ordenacao_por_preco(self):
        precos = [p["preco_centavos"] for p in regras.listar_produtos(self.conn, ordem="menor_preco")]
        self.assertEqual(precos, sorted(precos))

    def test_produto_inexistente(self):
        with self.assertRaises(regras.NaoEncontrado):
            regras.obter_produto(self.conn, "nao-existe")


class TestCarrinhoEPedido(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()

    def test_cotacao_usa_preco_do_banco_e_desconto_pix(self):
        c = regras.cotar_carrinho(self.conn, [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 2, "preco_centavos": 1}],
                                  cep="69005000", pagamento="pix")
        self.assertEqual(c["subtotal_centavos"], 4980)
        self.assertEqual(c["desconto_centavos"], 249)
        self.assertEqual(c["frete"]["valor_centavos"], 990)
        self.assertEqual(c["total_centavos"], 4980 - 249 + 990)

    def test_itens_repetidos_sao_somados(self):
        c = regras.cotar_carrinho(self.conn, [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}] * 3)
        self.assertEqual(c["itens"][0]["quantidade"], 3)

    def test_parcelamento(self):
        self.assertEqual(regras.parcelas_maximas(2000), 1)
        self.assertEqual(regras.parcelas_maximas(9000), 3)
        self.assertEqual(regras.parcelas_maximas(100000), config.PARCELAS_MAX)

    def test_pedido_baixa_estoque(self):
        antes = estoque(self.conn, "power-bank-20000mah")
        codigo = regras.criar_pedido(self.conn, {**CLIENTE, "itens": [{"slug": "power-bank-20000mah", "quantidade": 2}]})
        self.assertTrue(codigo.startswith("TPT-"))
        self.assertEqual(estoque(self.conn, "power-bank-20000mah"), antes - 2)
        pub = regras.obter_pedido_publico(self.conn, codigo)
        self.assertEqual(pub["status"], "aguardando_pagamento")
        self.assertEqual(pub["zona_frete"], "Manaus (AM)")
        self.assertNotIn("cliente_cpf", pub)
        self.assertNotIn("cpf", str(pub))

    def test_pedido_sem_estoque_nao_altera_nada(self):
        disponivel = estoque(self.conn, "mini-projetor-portatil")
        with self.assertRaises(regras.ErroValidacao):
            regras.criar_pedido(self.conn, {**CLIENTE, "itens": [
                {"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1},
                {"slug": "mini-projetor-portatil", "quantidade": disponivel + 1},
            ]})
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0], 0)
        self.assertEqual(estoque(self.conn, "cabo-usb-c-reforcado-2m"), 120)

    def test_dados_invalidos(self):
        with self.assertRaises(regras.ErroValidacao) as ctx:
            regras.criar_pedido(self.conn, {**CLIENTE, "cpf": "123", "email": "x", "uf": "XX",
                                            "itens": [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}]})
        self.assertEqual(set(ctx.exception.campos), {"cpf", "email", "uf"})

    def test_parcelas_acima_do_permitido(self):
        with self.assertRaises(regras.ErroValidacao):
            regras.criar_pedido(self.conn, {**CLIENTE, "pagamento": "cartao", "parcelas": 6,
                                            "itens": [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}]})

    def test_cancelamento_devolve_estoque_uma_vez(self):
        antes = estoque(self.conn, "fita-led-rgb-5m")
        codigo = regras.criar_pedido(self.conn, {**CLIENTE, "itens": [{"slug": "fita-led-rgb-5m", "quantidade": 3}]})
        regras.atualizar_status(self.conn, codigo, "cancelado")
        regras.atualizar_status(self.conn, codigo, "cancelado")
        self.assertEqual(estoque(self.conn, "fita-led-rgb-5m"), antes)
        with self.assertRaises(regras.ErroValidacao):
            regras.atualizar_status(self.conn, codigo, "pago")

    def test_atualizar_produto(self):
        p = regras.atualizar_produto(self.conn, "fita-led-rgb-5m", {"preco_centavos": 3990, "ativo": False})
        self.assertEqual(p["preco_centavos"], 3990)
        self.assertFalse(p["ativo"])
        with self.assertRaises(regras.ErroValidacao):
            regras.atualizar_produto(self.conn, "fita-led-rgb-5m", {"estoque": -1})


    def test_criar_produto(self):
        p = regras.criar_produto(self.conn, {"nome": "Fone Bluetooth TWS com estojo", "categoria": "eletronicos",
                                             "preco_centavos": 4990, "estoque": 10})
        self.assertEqual(p["slug"], "fone-bluetooth-tws-com-estojo")
        repetido = regras.criar_produto(self.conn, {"nome": "Fone Bluetooth TWS com estojo", "categoria": "eletronicos",
                                                    "preco_centavos": 4990, "estoque": 10})
        self.assertEqual(repetido["slug"], "fone-bluetooth-tws-com-estojo-2")
        with self.assertRaises(regras.ErroValidacao) as ctx:
            regras.criar_produto(self.conn, {"nome": "x", "categoria": "nao-existe", "preco_centavos": -1, "estoque": "a"})
        self.assertEqual(set(ctx.exception.campos), {"nome", "categoria", "preco_centavos", "estoque"})


if __name__ == "__main__":
    unittest.main()
