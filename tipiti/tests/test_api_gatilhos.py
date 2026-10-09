"""Gatilhos de venda pela API HTTP: rotas novas, campos novos e limites."""

import itertools
from datetime import datetime, timezone
from unittest import mock

from loja import horario
from tests.test_regras import CLIENTE
from tests.test_servidor import Base

_ips = (f"10.9.{i // 250}.{i % 250 + 1}" for i in itertools.count())


class TestGatilhosApi(Base):
    def pedido(self, itens, **extra):
        status, corpo = self.json("/api/pedidos", "POST", {**CLIENTE, **extra, "itens": itens}, ip=next(_ips))
        self.assertEqual(status, 201, corpo)
        return corpo

    def entregar(self, codigo):
        for status in ("pago", "enviado", "entregue"):
            self.assertEqual(self.admin(f"/api/admin/pedidos/{codigo}", "PATCH", {"status": status})[0], 200)

    def test_loja_tem_os_campos_novos(self):
        loja = self.json("/api/loja")[1]
        self.assertIs(loja["prova_social"], True)
        self.assertIsNone(loja["envio_hoje"])
        self.assertIsNone(loja["cupom_destaque"])
        self.admin("/api/admin/ajustes", "PUT", {"horario_corte": "14:00"})
        self.addCleanup(self.admin, "/api/admin/ajustes", "PUT", {"horario_corte": ""})
        sexta_9h = datetime(2026, 10, 9, 13, tzinfo=timezone.utc)
        with mock.patch.object(horario, "agora", return_value=sexta_9h):
            self.assertEqual(self.json("/api/loja")[1]["envio_hoje"], {"ate": "2026-10-09T18:00:00Z"})
        self.assertEqual(self.admin("/api/admin/ajustes", "PUT", {"horario_corte": "2pm"})[0], 422)

    def test_oferta_relampago(self):
        status, corpo = self.admin("/api/admin/produtos/fita-led-rgb-5m", "PATCH", {"promo_pct": 20})
        self.assertEqual(status, 422)
        self.assertIn("promo", corpo["campos"])
        status, corpo = self.admin("/api/admin/produtos/fita-led-rgb-5m", "PATCH",
                                   {"promo_pct": 20, "promo_fim": "2020-01-01T00:00:00Z"})
        self.assertEqual((status, list(corpo["campos"])), (422, ["promo_fim"]))
        status, p = self.admin("/api/admin/produtos/fita-led-rgb-5m", "PATCH",
                               {"promo_pct": 20, "promo_fim": "2099-01-01T00:00:00Z"})
        self.assertEqual(status, 200)
        self.addCleanup(self.admin, "/api/admin/produtos/fita-led-rgb-5m", "PATCH", {"promo_pct": None, "promo_fim": None})
        self.assertEqual((p["promo_pct"], p["promo_fim"]), (20, "2099-01-01T00:00:00Z"))
        ofertas = self.json("/api/produtos?promo=1")[1]
        self.assertEqual([o["slug"] for o in ofertas], ["fita-led-rgb-5m"])
        self.assertEqual(ofertas[0]["promo"], {"pct": 20, "fim": "2099-01-01T00:00:00Z"})
        self.assertEqual(ofertas[0]["preco_final_centavos"], (ofertas[0]["preco_centavos"] * 80 + 50) // 100)
        self.assertNotIn("promo_pct", ofertas[0])
        admin = next(p for p in self.admin("/api/admin/produtos")[1] if p["slug"] == "fita-led-rgb-5m")
        self.assertEqual(admin["promo_pct"], 20)
        detalhe = self.json("/api/produtos/fita-led-rgb-5m")[1]
        for campo in ("preco_final_centavos", "preco_ancora_centavos", "promo", "vendidos_30d", "selos", "nota_media",
                      "avaliacoes_total", "comprados_juntos"):
            self.assertIn(campo, detalhe)
        self.assertTrue(all("preco_final_centavos" in r for r in detalhe["relacionados"]))

    def test_listagem_mais_vendidos(self):
        self.assertEqual(self.chamar("/api/produtos?ordem=mais_vendidos")[0], 200)

    def test_cupons_no_painel_e_no_carrinho(self):
        status, corpo = self.admin("/api/admin/cupons", "POST", {"codigo": "x", "tipo": "pct", "valor": 200})
        self.assertEqual(status, 422)
        self.assertEqual(set(corpo["campos"]), {"codigo"})
        status, corpo = self.admin("/api/admin/cupons", "POST", {"codigo": "API10", "tipo": "pct", "valor": 200})
        self.assertEqual((status, set(corpo["campos"])), (422, {"valor"}))
        status, cupom = self.admin("/api/admin/cupons", "POST",
                                   {"codigo": "api10", "tipo": "pct", "valor": 10, "destaque": True})
        self.assertEqual((status, cupom["codigo"], cupom["descricao"]), (201, "API10", "10% de desconto"))
        self.assertEqual(self.admin("/api/admin/cupons", "POST", {"codigo": "API10", "tipo": "frete"})[0], 422)
        self.assertEqual(self.json("/api/loja")[1]["cupom_destaque"], {"codigo": "API10", "descricao": "10% de desconto"})
        self.assertEqual([c["codigo"] for c in self.admin("/api/admin/cupons")[1]], ["API10"])
        self.assertEqual(self.chamar("/api/admin/cupons")[0], 401)

        cotacao = self.json("/api/carrinho/cotacao", "POST", {
            "itens": [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 2}], "cep": "69005000", "cupom": "api10",
            "cpf": CLIENTE["cpf"]})[1]
        self.assertEqual(cotacao["desconto_cupom_centavos"], 498)
        self.assertEqual(cotacao["cupom"]["codigo"], "API10")
        self.assertIsNone(cotacao["cupom_erro"])
        self.assertEqual(cotacao["total_centavos"], 4980 - 498 - (4980 - 498) * 5 // 100 + 990)
        self.assertEqual(cotacao["economia_centavos"], 498 + (4980 - 498) * 5 // 100)
        self.assertIn("preco_ancora_unit_centavos", cotacao["itens"][0])

        status, cupom = self.admin("/api/admin/cupons/api10", "PATCH", {"minimo_centavos": 10000, "destaque": False})
        self.assertEqual((status, cupom["descricao"]), (200, "10% de desconto acima de R$ 100,00"))
        self.assertIsNone(self.json("/api/loja")[1]["cupom_destaque"])
        self.assertEqual(self.admin("/api/admin/cupons/API10", "PATCH", {"codigo": "OUTRO"})[0], 422)
        self.assertEqual(self.admin("/api/admin/cupons/NAOEXISTE", "PATCH", {"ativo": False})[0], 404)
        status, corpo = self.json("/api/pedidos", "POST", {
            **CLIENTE, "cupom": "API10", "itens": [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}]}, ip=next(_ips))
        self.assertEqual(status, 422)
        self.assertIn("Faltam", corpo["campos"]["cupom"])

        self.admin("/api/admin/cupons/API10", "PATCH", {"minimo_centavos": 0})
        pedido = self.pedido([{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}], cupom="api10")
        self.assertEqual((pedido["cupom_codigo"], pedido["desconto_cupom_centavos"]), ("API10", 249))
        lista = self.admin("/api/admin/pedidos")[1]
        self.assertEqual(next(p for p in lista if p["codigo"] == pedido["codigo"])["cupom_codigo"], "API10")
        self.assertEqual(self.admin("/api/admin/cupons")[1][0]["usos"], 1)
        self.admin(f"/api/admin/pedidos/{pedido['codigo']}", "PATCH", {"status": "cancelado"})
        self.assertEqual(self.admin("/api/admin/cupons")[1][0]["usos"], 0)

    def test_avaliacoes(self):
        self.assertEqual(self.json("/api/produtos/power-bank-20000mah/avaliacoes"), (200, []))
        self.assertEqual(self.chamar("/api/produtos/nao-existe/avaliacoes")[0], 404)
        pedido = self.pedido([{"slug": "power-bank-20000mah", "quantidade": 1}], cidade="Santarém", uf="PA",
                             cep="68005-000")
        self.assertEqual([i["pode_avaliar"] for i in pedido["itens"]], [False])
        self.assertEqual(pedido["itens"][0]["slug"], "power-bank-20000mah")
        avaliacao = {"codigo": pedido["codigo"], "email": CLIENTE["email"], "slug": "power-bank-20000mah", "nota": 4,
                     "comentario": "Bom"}
        status, corpo = self.json("/api/avaliacoes", "POST", avaliacao, ip="10.8.0.1")
        self.assertEqual(status, 422)
        self.assertIn("entregue", corpo["campos"]["codigo"])
        self.entregar(pedido["codigo"])
        self.assertTrue(self.json(f"/api/pedidos/{pedido['codigo']}")[1]["itens"][0]["pode_avaliar"])
        self.assertEqual(self.json("/api/avaliacoes", "POST", avaliacao, ip="10.8.0.1"), (201, {"status": "pendente"}))
        self.assertFalse(self.json(f"/api/pedidos/{pedido['codigo']}")[1]["itens"][0]["pode_avaliar"])
        self.assertEqual(self.json("/api/avaliacoes", "POST", avaliacao, ip="10.8.0.1")[0], 422)

        pendentes = self.admin("/api/admin/avaliacoes?status=pendente")[1]
        self.assertEqual(len(pendentes), 1)
        self.assertEqual(pendentes[0]["nome"], "Maria de Santarém")
        self.assertEqual(pendentes[0]["pedido"], pedido["codigo"])
        self.assertEqual(self.admin("/api/admin/avaliacoes?status=talvez")[0], 422)
        status, moderada = self.admin(f"/api/admin/avaliacoes/{pendentes[0]['id']}", "PATCH", {"status": "aprovada"})
        self.assertEqual((status, moderada["status"]), (200, "aprovada"))
        self.assertEqual(self.admin(f"/api/admin/avaliacoes/{pendentes[0]['id']}", "PATCH", {"status": "x"})[0], 422)
        self.assertEqual(self.admin("/api/admin/avaliacoes/999999", "PATCH", {"status": "oculta"})[0], 404)
        publicas = self.json("/api/produtos/power-bank-20000mah/avaliacoes")[1]
        self.assertEqual([(a["nome"], a["nota"], a["comentario"]) for a in publicas], [("Maria de Santarém", 4, "Bom")])
        produto = self.json("/api/produtos/power-bank-20000mah")[1]
        self.assertEqual((produto["nota_media"], produto["avaliacoes_total"]), (4.0, 1))
        self.assertEqual(len(self.admin("/api/admin/avaliacoes")[1]), 1)

    def test_limite_de_avaliacoes_por_ip(self):
        tentativa = {"codigo": "TPT-NAOEXISTE00", "email": "a@b.com", "slug": "power-bank-20000mah", "nota": 5}
        for _ in range(20):
            self.assertEqual(self.chamar("/api/avaliacoes", "POST", tentativa, ip="10.8.1.1")[0], 422)
        self.assertEqual(self.json("/api/avaliacoes", "POST", tentativa, ip="10.8.1.1"),
                         (429, {"erro": "Muitas tentativas. Aguarde alguns minutos."}))
        self.assertEqual(self.chamar("/api/avaliacoes", "POST", tentativa, ip="10.8.1.2")[0], 422)

    def test_vendas_recentes_com_cache_e_desligavel(self):
        self.servidor.cache_vendas_recentes = None
        self.pedido([{"slug": "mini-projetor-portatil", "quantidade": 1}], cidade="Macapá", uf="AP", cep="68900-000")
        status, vendas = self.json("/api/vendas-recentes")
        self.assertEqual(status, 200)
        projetor = next(v for v in vendas if v["slug"] == "mini-projetor-portatil")
        self.assertEqual((projetor["cidade"], projetor["uf"]), ("Macapá", "AP"))
        self.assertNotIn(CLIENTE["nome"].split()[0], str(vendas))
        self.pedido([{"slug": "caixa-de-som-bluetooth-ipx7", "quantidade": 1}])
        self.assertEqual(self.json("/api/vendas-recentes")[1], vendas)  # guardado por 60 s
        self.servidor.cache_vendas_recentes = None
        self.assertIn("caixa-de-som-bluetooth-ipx7", [v["slug"] for v in self.json("/api/vendas-recentes")[1]])
        self.admin("/api/admin/ajustes", "PUT", {"prova_social": "0"})
        self.addCleanup(self.admin, "/api/admin/ajustes", "PUT", {"prova_social": "1"})
        self.assertEqual(self.json("/api/vendas-recentes"), (200, []))
        self.assertIs(self.json("/api/loja")[1]["prova_social"], False)
