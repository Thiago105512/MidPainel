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
        self.addCleanup(self.conn.close)

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
        self.addCleanup(self.conn.close)

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



class TestVariacoes(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)
        self.produto = regras.obter_produto(self.conn, "fone-bluetooth-tws", admin=True)
        self.preto = self.produto["variacoes"][0]

    def test_exige_escolher_opcao(self):
        c = regras.cotar_carrinho(self.conn, [{"slug": "fone-bluetooth-tws", "quantidade": 1}])
        self.assertFalse(c["valido"])
        with self.assertRaises(regras.ErroValidacao):
            regras.criar_pedido(self.conn, {**CLIENTE, "itens": [{"slug": "fone-bluetooth-tws", "quantidade": 1}]})

    def test_variacao_de_outro_produto(self):
        c = regras.cotar_carrinho(self.conn, [{"slug": "power-bank-20000mah", "variacao": self.preto["id"], "quantidade": 1}])
        self.assertFalse(c["valido"])

    def test_pedido_baixa_estoque_da_variacao_e_cancelamento_devolve(self):
        total = self.produto["estoque"]
        codigo = regras.criar_pedido(self.conn, {**CLIENTE, "itens": [
            {"slug": "fone-bluetooth-tws", "variacao": self.preto["id"], "quantidade": 2}]})
        depois = regras.obter_produto(self.conn, "fone-bluetooth-tws", admin=True)
        self.assertEqual(depois["variacoes"][0]["estoque"], self.preto["estoque"] - 2)
        self.assertEqual(depois["estoque"], total - 2)
        pub = regras.obter_pedido_publico(self.conn, codigo)
        self.assertEqual(pub["itens"][0]["variacao_nome"], "Preto")
        regras.atualizar_status(self.conn, codigo, "cancelado")
        self.assertEqual(regras.obter_produto(self.conn, "fone-bluetooth-tws")["estoque"], total)

    def test_preco_proprio_da_variacao(self):
        relogio = regras.obter_produto(self.conn, "smartwatch-tela-amoled")
        prata = next(v for v in relogio["variacoes"] if v["preco_centavos"])
        c = regras.cotar_carrinho(self.conn, [{"slug": "smartwatch-tela-amoled", "variacao": prata["id"], "quantidade": 1}])
        self.assertEqual(c["subtotal_centavos"], 22990)

    def test_salvar_variacoes(self):
        lista = [dict(v) for v in self.produto["variacoes"]]
        lista[0]["estoque"] = 50
        lista = lista[:2] + [{"nome": "Verde", "estoque": 7}]
        p = regras.salvar_variacoes(self.conn, "fone-bluetooth-tws", lista)
        ativas = [v for v in p["variacoes"] if v["ativo"]]
        self.assertEqual([v["nome"] for v in ativas], ["Preto", "Branco", "Verde"])
        self.assertEqual(p["estoque"], 50 + 15 + 7)  # "Rosa" saiu da lista e foi desativada
        with self.assertRaises(regras.ErroValidacao):
            regras.salvar_variacoes(self.conn, "fone-bluetooth-tws", [{"nome": "A"}, {"nome": "a"}])

    def test_estoque_do_produto_com_variacoes_nao_e_editavel_direto(self):
        p = regras.atualizar_produto(self.conn, "fone-bluetooth-tws", {"estoque": 999, "custo_centavos": 3000})
        self.assertNotEqual(p["estoque"], 999)
        self.assertEqual(p["custo_centavos"], 3000)


class TestLucro(unittest.TestCase):
    def test_lucro_do_pedido(self):
        conn = nova_conexao()
        self.addCleanup(conn.close)
        regras.atualizar_produto(conn, "cabo-usb-c-reforcado-2m", {"custo_centavos": 1000})
        regras.criar_pedido(conn, {**CLIENTE, "itens": [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 2}]})
        pedido = regras.listar_pedidos(conn)[0]
        # 2 × 24,90 = 49,80; Pix -5% = 2,49; custo 2 × 10,00
        self.assertEqual(pedido["lucro_centavos"], 4980 - 249 - 2000)

    def test_sem_custo(self):
        conn = nova_conexao()
        self.addCleanup(conn.close)
        regras.atualizar_produto(conn, "cabo-usb-c-reforcado-2m", {"custo_centavos": None})
        regras.criar_pedido(conn, {**CLIENTE, "itens": [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}]})
        self.assertIsNone(regras.listar_pedidos(conn)[0]["lucro_centavos"])
        self.assertEqual(regras.resumo_vendas(conn)["pedidos_sem_custo"], 1)


class TestCalculadora(unittest.TestCase):
    def test_arredondamento(self):
        from loja.precificacao import arredondar_preco
        self.assertEqual(arredondar_preco(7077), 7090)
        self.assertEqual(arredondar_preco(7090), 7090)
        self.assertEqual(arredondar_preco(7091), 7190)
        self.assertEqual(arredondar_preco(10), 90)

    def test_margem_impossivel(self):
        from loja import precificacao
        with self.assertRaises(regras.ErroValidacao):
            precificacao.calcular({"custo_unitario": 10, "taxa_pagamento_pct": 10, "margem_pct": 90})
        with self.assertRaises(regras.ErroValidacao):
            precificacao.calcular({"custo_unitario": "abc"})


def envelhecer(conn, codigo, horas):
    conn.execute("UPDATE pedidos SET criado_em = datetime('now', ?) WHERE codigo = ?", (f"-{horas} hours", codigo))


def status_de(conn, codigo):
    return conn.execute("SELECT status FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()[0]


class TestReservaDeEstoque(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def pedido(self, slug="fita-led-rgb-5m", quantidade=2):
        return regras.criar_pedido(self.conn, {**CLIENTE, "itens": [{"slug": slug, "quantidade": quantidade}]})

    def test_pedido_nao_pago_expira_e_devolve_estoque(self):
        antes = estoque(self.conn, "fita-led-rgb-5m")
        vencido, recente, pago = self.pedido(), self.pedido(), self.pedido()
        regras.atualizar_status(self.conn, pago, "pago")
        for codigo in (vencido, pago):
            envelhecer(self.conn, codigo, config.PRAZO_RESERVA_HORAS + 1)
        envelhecer(self.conn, recente, config.PRAZO_RESERVA_HORAS - 1)
        regras.cotar_carrinho(self.conn, [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}])
        self.assertEqual(status_de(self.conn, vencido), "cancelado")
        self.assertEqual(status_de(self.conn, recente), "aguardando_pagamento")
        self.assertEqual(status_de(self.conn, pago), "pago")
        self.assertEqual(estoque(self.conn, "fita-led-rgb-5m"), antes - 4)

    def test_expiracao_roda_ao_criar_pedido_e_listar(self):
        disponivel = estoque(self.conn, "mini-projetor-portatil")
        restante = disponivel
        codigos = []
        while restante:  # esgota o produto com pedidos de até 10 unidades
            q = min(restante, config.QTD_MAX_POR_ITEM)
            codigos.append(self.pedido("mini-projetor-portatil", q))
            restante -= q
        with self.assertRaises(regras.ErroValidacao):
            self.pedido("mini-projetor-portatil", 1)
        for codigo in codigos:
            envelhecer(self.conn, codigo, config.PRAZO_RESERVA_HORAS * 2)
        self.pedido("mini-projetor-portatil", 1)
        self.assertEqual(estoque(self.conn, "mini-projetor-portatil"), disponivel - 1)
        novo = self.pedido()
        envelhecer(self.conn, novo, config.PRAZO_RESERVA_HORAS + 1)
        pedido = next(p for p in regras.listar_pedidos(self.conn) if p["codigo"] == novo)
        self.assertEqual(pedido["status"], "cancelado")

    def test_limite_por_item(self):
        self.assertEqual(config.QTD_MAX_POR_ITEM, 10)
        with self.assertRaises(regras.ErroValidacao):
            regras.cotar_carrinho(self.conn, [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 11}])

    def test_quantidade_e_variacao_absurdas_sao_erro_de_validacao(self):
        for item in ({"slug": "cabo-usb-c-reforcado-2m", "quantidade": float("inf")},
                     {"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1e400},
                     {"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1, "variacao": 10 ** 30},
                     {"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1, "variacao": -1}):
            with self.assertRaises(regras.ErroValidacao):
                regras.cotar_carrinho(self.conn, [item])

    def test_codigo_novo_tem_12_caracteres_e_antigo_continua_valendo(self):
        codigo = self.pedido()
        self.assertRegex(codigo, r"^TPT-[A-Z2-9]{12}$")
        self.conn.execute("UPDATE pedidos SET codigo = 'TPT-ABCD2345' WHERE codigo = ?", (codigo,))
        self.assertEqual(regras.obter_pedido_publico(self.conn, "tpt-abcd2345")["codigo"], "TPT-ABCD2345")


class TestStatusDoPedido(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)
        self.antes = estoque(self.conn, "fita-led-rgb-5m")
        self.codigo = regras.criar_pedido(self.conn, {**CLIENTE, "itens": [{"slug": "fita-led-rgb-5m", "quantidade": 3}]})

    def test_caminho_normal(self):
        for status in ("pago", "enviado", "entregue"):
            regras.atualizar_status(self.conn, self.codigo, status)
        self.assertEqual(status_de(self.conn, self.codigo), "entregue")
        self.assertEqual(estoque(self.conn, "fita-led-rgb-5m"), self.antes - 3)
        for status in ("cancelado", "pago", "aguardando_pagamento"):
            with self.assertRaises(regras.ErroValidacao):
                regras.atualizar_status(self.conn, self.codigo, status)

    def test_transicoes_proibidas(self):
        with self.assertRaises(regras.ErroValidacao):
            regras.atualizar_status(self.conn, self.codigo, "enviado")
        regras.atualizar_status(self.conn, self.codigo, "pago")
        regras.atualizar_status(self.conn, self.codigo, "enviado")
        with self.assertRaises(regras.ErroValidacao):
            regras.atualizar_status(self.conn, self.codigo, "cancelado")  # já saiu: estoque não volta sozinho
        self.assertEqual(estoque(self.conn, "fita-led-rgb-5m"), self.antes - 3)

    def test_mesmo_status_nao_faz_nada(self):
        regras.atualizar_status(self.conn, self.codigo, "aguardando_pagamento")
        self.assertEqual(status_de(self.conn, self.codigo), "aguardando_pagamento")

    def test_pago_pode_voltar_ou_ser_cancelado_devolvendo_estoque(self):
        regras.atualizar_status(self.conn, self.codigo, "pago")
        regras.atualizar_status(self.conn, self.codigo, "aguardando_pagamento")
        regras.atualizar_status(self.conn, self.codigo, "pago")
        regras.atualizar_status(self.conn, self.codigo, "cancelado")
        self.assertEqual(estoque(self.conn, "fita-led-rgb-5m"), self.antes)

    def test_status_invalido(self):
        for status in (["pago"], None, "voando"):
            with self.assertRaises(regras.ErroValidacao):
                regras.atualizar_status(self.conn, self.codigo, status)

    def test_listagem_traz_proximos_status(self):
        pedido = regras.listar_pedidos(self.conn)[0]
        self.assertEqual(pedido["proximos_status"], ["pago", "cancelado"])
        regras.atualizar_status(self.conn, self.codigo, "cancelado")
        self.assertEqual(regras.listar_pedidos(self.conn)[0]["proximos_status"], [])


class TestEstoqueComVariacoes(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def test_desativar_todas_as_variacoes_zera_o_estoque(self):
        p = regras.salvar_variacoes(self.conn, "fone-bluetooth-tws", [])
        self.assertEqual(p["estoque"], 0)
        self.assertFalse(p["tem_variacoes"])
        c = regras.cotar_carrinho(self.conn, [{"slug": "fone-bluetooth-tws", "quantidade": 1}])
        self.assertFalse(c["valido"])
        # o estoque continua controlado pelas variações (reative uma para voltar a vender)
        p = regras.atualizar_produto(self.conn, "fone-bluetooth-tws", {"estoque": 50, "destaque": True})
        self.assertEqual(p["estoque"], 0)

    def test_cancelar_pedido_antigo_de_produto_que_ganhou_variacoes(self):
        codigo = regras.criar_pedido(self.conn, {**CLIENTE, "itens": [{"slug": "power-bank-20000mah", "quantidade": 2}]})
        regras.salvar_variacoes(self.conn, "power-bank-20000mah", [{"nome": "Preto", "estoque": 5}])
        regras.atualizar_status(self.conn, codigo, "cancelado")
        self.assertEqual(estoque(self.conn, "power-bank-20000mah"), 5)

    def test_preco_da_variacao_nao_pode_ser_zero(self):
        with self.assertRaises(regras.ErroValidacao):
            regras.salvar_variacoes(self.conn, "fone-bluetooth-tws", [{"nome": "Preto", "preco_centavos": 0}])
        with self.assertRaises(regras.ErroValidacao):
            regras.salvar_variacoes(self.conn, "fone-bluetooth-tws", [{"nome": "Preto", "id": [1]}])
        p = regras.salvar_variacoes(self.conn, "fone-bluetooth-tws", [{"nome": "Preto", "preco_centavos": None}])
        self.assertIsNone(p["variacoes"][-1]["preco_centavos"])


class TestValidacaoDeProduto(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def test_preco_zero_e_numeros_gigantes(self):
        for dados in ({"preco_centavos": 0}, {"estoque": 10 ** 9 + 1}, {"custo_centavos": 10 ** 20}):
            with self.assertRaises(regras.ErroValidacao):
                regras.atualizar_produto(self.conn, "cabo-usb-c-reforcado-2m", dados)
        self.assertEqual(regras.atualizar_produto(self.conn, "cabo-usb-c-reforcado-2m", {"estoque": 10 ** 9})["estoque"],
                         10 ** 9)

    def test_calculadora_recusa_valores_absurdos(self):
        from loja import precificacao
        with self.assertRaises(regras.ErroValidacao):
            precificacao.calcular({"custo_unitario": "1e30"})
        with self.assertRaises(regras.ErroValidacao):
            precificacao.calcular({"custo_unitario": "1", "quantidade": "1e999999"})


class TestBuscaEListagens(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def slugs(self, **kwargs):
        return [p["slug"] for p in regras.listar_produtos(self.conn, **kwargs)]

    def test_busca_usa_coluna_normalizada(self):
        busca = self.conn.execute("SELECT busca FROM produtos WHERE slug = 'power-bank-20000mah'").fetchone()[0]
        self.assertIn("carregador portatil", busca)
        self.assertIn("celular", busca)  # nome da categoria
        p = regras.criar_produto(self.conn, {"nome": "Câmera de ré", "categoria": "ferramentas-e-automotivo",
                                             "preco_centavos": 9990, "estoque": 3, "descricao": "Visão noturna"})
        self.assertIn(p["slug"], self.slugs(busca="camera noturna"))
        regras.atualizar_produto(self.conn, p["slug"], {"descricao": "Encaixe universal"})
        self.assertNotIn(p["slug"], self.slugs(busca="noturna"))
        self.assertIn(p["slug"], self.slugs(busca="UNIVERSAL"))
        self.assertEqual(self.slugs(busca="_"), [])

    def test_migracao_preenche_busca(self):
        self.conn.execute("UPDATE produtos SET busca = ''")
        db.inicializar(self.conn)
        self.assertIn("power-bank-20000mah", self.slugs(busca="portatil"))

    def test_indices(self):
        indices = {r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
        self.assertTrue({"idx_pedidos_status", "idx_produtos_vitrine"} <= indices)

    def test_listagem_publica_sem_descricao_e_com_cor(self):
        lista = regras.listar_produtos(self.conn)
        self.assertNotIn("descricao", lista[0])
        self.assertRegex(lista[0]["cor"], r"^#[0-9a-fA-F]{6}$")
        self.assertIsNone(lista[0]["imagem_miniatura"])
        produto = regras.obter_produto(self.conn, lista[0]["slug"])
        self.assertIn("descricao", produto)
        self.assertIn("cor", produto)
        self.assertTrue(all("descricao" not in r for r in produto["relacionados"]))
        self.assertIn("descricao", regras.listar_produtos(self.conn, admin=True)[0])

    def test_limite_e_offset(self):
        todos = self.slugs(ordem="nome")
        self.assertEqual(self.slugs(ordem="nome", limite=3, offset=2), todos[2:5])
        self.assertEqual(self.slugs(ordem="nome", offset=len(todos) - 1), todos[-1:])

    def test_miniatura_da_capa(self):
        regras.adicionar_foto(self.conn, "power-bank-20000mah", "power-bank-20000mah-aaaa0001.jpg")
        p = regras.adicionar_foto(self.conn, "power-bank-20000mah", "power-bank-20000mah-aaaa0002.jpg",
                                  "power-bank-20000mah-aaaa0003.webp")
        self.assertEqual([f["miniatura"] for f in p["fotos"]],
                         ["/fotos/power-bank-20000mah-aaaa0001.jpg", "/fotos/power-bank-20000mah-aaaa0003.webp"])
        self.assertEqual(p["imagem_miniatura"], "/fotos/power-bank-20000mah-aaaa0001.jpg")
        p = regras.definir_capa(self.conn, "power-bank-20000mah", p["fotos"][1]["id"])
        listado = next(x for x in regras.listar_produtos(self.conn) if x["slug"] == "power-bank-20000mah")
        self.assertEqual(listado["imagem_miniatura"], "/fotos/power-bank-20000mah-aaaa0003.webp")
        arquivos, _ = regras.remover_foto(self.conn, "power-bank-20000mah", p["fotos"][0]["id"])
        self.assertEqual(arquivos, ["power-bank-20000mah-aaaa0002.jpg", "power-bank-20000mah-aaaa0003.webp"])

    def test_limite_de_fotos(self):
        for i in range(config.FOTOS_POR_PRODUTO):
            regras.adicionar_foto(self.conn, "power-bank-20000mah", f"power-bank-20000mah-{i:08x}.jpg")
        with self.assertRaises(regras.ErroValidacao):
            regras.adicionar_foto(self.conn, "power-bank-20000mah", "power-bank-20000mah-ffffffff.jpg")
        self.assertFalse(self.conn.in_transaction)

    def test_imagem_de_produto_inativo(self):
        regras.atualizar_produto(self.conn, "power-bank-20000mah", {"ativo": False})
        with self.assertRaises(regras.NaoEncontrado):
            regras.cor_e_icone(self.conn, "power-bank-20000mah")


class TestResumoDeVendas(unittest.TestCase):
    def test_soma_todos_os_pedidos_em_sql(self):
        conn = nova_conexao()
        self.addCleanup(conn.close)
        regras.atualizar_produto(conn, "cabo-usb-c-reforcado-2m", {"custo_centavos": 1000})
        com_custo = regras.criar_pedido(conn, {**CLIENTE, "itens": [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 2}]})
        regras.atualizar_produto(conn, "power-bank-20000mah", {"custo_centavos": None})
        sem_custo = regras.criar_pedido(conn, {**CLIENTE, "itens": [
            {"slug": "power-bank-20000mah", "quantidade": 1}, {"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}]})
        cancelado = regras.criar_pedido(conn, {**CLIENTE, "itens": [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}]})
        regras.atualizar_status(conn, cancelado, "cancelado")
        lista = {p["codigo"]: p for p in regras.listar_pedidos(conn)}
        self.assertEqual(len(lista[sem_custo]["itens"]), 2)
        self.assertEqual(len(lista[com_custo]["itens"]), 1)

        # cópias do pedido com custo, além do antigo limite de 500 pedidos
        pid = conn.execute("SELECT id FROM pedidos WHERE codigo = ?", (com_custo,)).fetchone()[0]
        colunas = [r["name"] for r in conn.execute("PRAGMA table_info(pedidos)") if r["name"] not in ("id", "codigo")]
        conn.execute("BEGIN")
        for i in range(600):
            novo = conn.execute(f"INSERT INTO pedidos (codigo, {', '.join(colunas)}) "
                                f"SELECT ?, {', '.join(colunas)} FROM pedidos WHERE id = ?", (f"TPT-COPIA{i}", pid)).lastrowid
            conn.execute("""INSERT INTO itens_pedido (pedido_id, produto_id, variacao_id, nome, variacao_nome,
                                preco_unit_centavos, custo_unit_centavos, quantidade)
                            SELECT ?, produto_id, variacao_id, nome, variacao_nome, preco_unit_centavos,
                                   custo_unit_centavos, quantidade FROM itens_pedido WHERE pedido_id = ?""", (novo, pid))
        conn.execute("COMMIT")

        resumo = regras.resumo_vendas(conn)
        validos = [lista[com_custo]] * 601 + [lista[sem_custo]]
        faturamento = sum(p["total_centavos"] for p in validos)
        self.assertEqual(resumo["pedidos"], 602)
        self.assertEqual(resumo["faturamento_centavos"], faturamento)
        self.assertEqual(resumo["ticket_medio_centavos"], faturamento // 602)
        self.assertEqual(resumo["lucro_centavos"], 601 * lista[com_custo]["lucro_centavos"])
        self.assertEqual(resumo["pedidos_sem_custo"], 1)
        self.assertIn("estoque_baixo", resumo)

    def test_sem_pedidos(self):
        conn = nova_conexao()
        self.addCleanup(conn.close)
        resumo = regras.resumo_vendas(conn)
        self.assertEqual((resumo["pedidos"], resumo["faturamento_centavos"], resumo["ticket_medio_centavos"],
                          resumo["lucro_centavos"], resumo["pedidos_sem_custo"]), (0, 0, 0, 0, 0))


class TestAjustes(unittest.TestCase):
    def test_chave_pix(self):
        from loja import ajustes
        conn = nova_conexao()
        self.addCleanup(conn.close)
        self.assertEqual(ajustes.obter(conn)["chave_pix"], "")
        self.assertEqual(ajustes.salvar(conn, {"chave_pix": "  pix@tipiti.com.br "})["chave_pix"], "pix@tipiti.com.br")
        with self.assertRaises(regras.ErroValidacao):
            ajustes.salvar(conn, {"chave_pix": "x" * 121})


if __name__ == "__main__":
    unittest.main()
