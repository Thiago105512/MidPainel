"""Calendário de barcos, próximo barco na cotação, rastreio e eventos dos pedidos."""

import itertools
import json
from datetime import datetime, timezone
from unittest import mock
import unittest

from loja import horario, rastreio, regras, viagens
from tests.test_regras import CLIENTE, nova_conexao
from tests.test_servidor import Base

PARINTINS = {"cep": "69151-000", "cidade": "Parintins"}
ITENS = [{"slug": "power-bank-20000mah", "quantidade": 1}]
AGORA = datetime(2026, 10, 9, 13, 0, tzinfo=timezone.utc)  # sexta, 09:00 em Manaus


def relogio(momento=AGORA):
    return mock.patch.object(horario, "agora", return_value=momento)


def viagem(conn, **extra):
    dados = {"zona": "parintins", "embarcacao": "B/M Amazonas Star", "saida": "2026-10-12T22:00:00Z",
             "chegada_prevista": "2026-10-14T12:00:00Z", **extra}
    return viagens.criar(conn, dados)


class TestViagens(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def test_criar_e_validar(self):
        v = viagem(self.conn, observacao="  Saída do porto da Panair  ")
        self.assertEqual(v, {"id": v["id"], "zona": "parintins", "zona_nome": "Parintins (AM)",
                             "embarcacao": "B/M Amazonas Star", "saida": "2026-10-12T22:00:00Z",
                             "chegada_prevista": "2026-10-14T12:00:00Z", "observacao": "Saída do porto da Panair",
                             "ativo": True})
        with self.assertRaises(regras.ErroValidacao) as e:
            viagens.criar(self.conn, {"zona": "marte", "embarcacao": "", "saida": "ontem",
                                      "chegada_prevista": "2026-10-14T12:00:00Z"})
        self.assertEqual(set(e.exception.campos), {"zona", "embarcacao", "saida"})
        with self.assertRaises(regras.ErroValidacao) as e:
            viagem(self.conn, chegada_prevista="2026-10-12T22:00:00Z")
        self.assertIn("chegada_prevista", e.exception.campos)
        with self.assertRaises(regras.ErroValidacao):
            viagem(self.conn, saida="9999-12-31T23:59:59-04:00")
        with self.assertRaises(regras.ErroValidacao):
            viagem(self.conn, ativo="sim")

    def test_data_pura_vale_meia_noite_de_manaus_e_fuso_e_convertido(self):
        v = viagem(self.conn, saida="2026-10-20", chegada_prevista="2026-10-22T08:00:00-04:00")
        self.assertEqual(v["saida"], "2026-10-20T04:00:00Z")
        self.assertEqual(v["chegada_prevista"], "2026-10-22T12:00:00Z")

    def test_atualizar(self):
        v = viagem(self.conn)
        alterada = viagens.atualizar(self.conn, v["id"], {"ativo": False, "embarcacao": "N/M Leão do Norte"})
        self.assertEqual((alterada["ativo"], alterada["embarcacao"], alterada["saida"]),
                         (False, "N/M Leão do Norte", "2026-10-12T22:00:00Z"))
        with self.assertRaises(regras.ErroValidacao):
            viagens.atualizar(self.conn, v["id"], {"saida": "2026-10-15T00:00:00Z"})  # depois da chegada
        with self.assertRaises(regras.NaoEncontrado):
            viagens.atualizar(self.conn, 999, {"ativo": True})

    def test_proximas_saidas(self):
        with relogio():
            viagem(self.conn, saida="2026-10-08T22:00:00Z", chegada_prevista="2026-10-10T12:00:00Z")  # já saiu
            viagem(self.conn, saida="2026-10-10T22:00:00Z", chegada_prevista="2026-10-12T12:00:00Z", ativo=False)
            viagem(self.conn, zona="santarem", saida="2026-10-11T22:00:00Z", chegada_prevista="2026-10-14T12:00:00Z")
            for dia in range(15, 22):
                viagem(self.conn, saida=f"2026-10-{dia}T22:00:00Z", chegada_prevista=f"2026-10-{dia + 2}T12:00:00Z")
            proximas = viagens.proximas(self.conn, "parintins")
            self.assertEqual([v["saida"][:10] for v in proximas],
                             ["2026-10-15", "2026-10-16", "2026-10-17", "2026-10-18", "2026-10-19"])
            self.assertEqual(viagens.proximas(self.conn, "macapa"), [])
            todas = viagens.proximas(self.conn)
            self.assertEqual(todas[0]["zona"], "santarem")
            self.assertEqual(len(todas), 8)
            with self.assertRaises(regras.ErroValidacao):
                viagens.proximas(self.conn, "x")
            admin = viagens.listar_admin(self.conn)
            self.assertEqual(len(admin), 10)
            self.assertEqual(admin[0]["saida"], "2026-10-10T22:00:00Z")  # próximas primeiro (inclusive inativas)
            self.assertEqual(admin[-1]["saida"], "2026-10-08T22:00:00Z")  # passadas no fim
            self.assertEqual(admin[0]["pedidos"], 0)


class TestProximoBarco(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def cotar(self, cep="69151-000"):
        return regras.cotar_carrinho(self.conn, ITENS, cep=cep)

    def test_zona_sem_viagem_fica_como_hoje(self):
        with relogio():
            cot = self.cotar()
        self.assertIsNone(cot["frete"]["proximo_barco"])
        self.assertIsNone(cot["frete"]["chegada_estimada"])
        self.assertEqual(cot["frete"]["prazo_dias"], 6)  # prazo da zona + manuseio, sem mudança

    def test_primeira_saida_depois_do_manuseio(self):
        with relogio():
            # sai hoje à noite: antes de acabar o manuseio (1 dia), não serve
            viagem(self.conn, saida="2026-10-09T23:00:00Z", chegada_prevista="2026-10-11T12:00:00Z")
            viagem(self.conn, saida="2026-10-13T22:00:00Z", chegada_prevista="2026-10-16T02:00:00Z",
                   embarcacao="N/M Leão do Norte")
            viagem(self.conn, saida="2026-10-12T22:00:00Z", chegada_prevista="2026-10-14T12:00:00Z", ativo=False)
            cot = self.cotar()
            self.assertEqual(cot["frete"]["proximo_barco"], {"embarcacao": "N/M Leão do Norte",
                                                             "saida": "2026-10-13T22:00:00Z",
                                                             "chegada_prevista": "2026-10-16T02:00:00Z"})
            self.assertEqual(cot["frete"]["chegada_estimada"], "2026-10-15")  # 22:00 do dia 15 em Manaus
            self.assertIsNone(self.cotar("69005-000")["frete"]["proximo_barco"])  # Manaus: sem barco
            self.assertIsNone(regras.cotar_carrinho(self.conn, ITENS)["frete"])  # sem CEP, sem frete

    def test_previsao_de_envio_da_prevenda_empurra_a_viagem(self):
        with relogio():
            viagem(self.conn, saida="2026-10-12T22:00:00Z", chegada_prevista="2026-10-14T12:00:00Z")
            viagem(self.conn, saida="2026-10-26T22:00:00Z", chegada_prevista="2026-10-28T12:00:00Z")
            frete = {"zona": "parintins"}
            viagens.anexar_ao_frete(self.conn, frete, "2026-10-20")
            self.assertEqual(frete["proximo_barco"]["saida"], "2026-10-26T22:00:00Z")
            viagens.anexar_ao_frete(self.conn, frete, None)
            self.assertEqual(frete["proximo_barco"]["saida"], "2026-10-12T22:00:00Z")
            viagens.anexar_ao_frete(self.conn, frete, "lixo")  # previsão inválida é ignorada
            self.assertEqual(frete["proximo_barco"]["saida"], "2026-10-12T22:00:00Z")
            # previsão no mesmo dia da saída (Manaus) ainda pega o barco
            viagens.anexar_ao_frete(self.conn, frete, "2026-10-26")
            self.assertEqual(frete["proximo_barco"]["saida"], "2026-10-26T22:00:00Z")
            viagens.anexar_ao_frete(self.conn, frete, "2026-10-27")
            self.assertIsNone(frete["proximo_barco"])
            # a cotação usa previsao_envio quando existir (seção V)
            original = regras.cotar_carrinho.__globals__["_cotar"]

            def com_previsao(*args, **kwargs):
                return {**original(*args, **kwargs), "previsao_envio": "2026-10-20"}

            with mock.patch("loja.carrinho._cotar", com_previsao):
                cot = regras.cotar_carrinho(self.conn, ITENS, cep="69151-000")
            self.assertEqual(cot["frete"]["proximo_barco"]["saida"], "2026-10-26T22:00:00Z")


class TestRastreio(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)
        self.codigo = regras.criar_pedido(self.conn, {**CLIENTE, **PARINTINS, "itens": ITENS})

    def publico(self):
        return regras.obter_pedido_publico(self.conn, self.codigo)

    def test_url_dos_correios(self):
        self.assertEqual(rastreio.url_rastreio("AA123456789BR"),
                         "https://rastreamento.correios.com.br/app/index.php?objeto=AA123456789BR")
        for codigo in (None, "", "AA12345678BR", "aa123456789br", "BARCO-123", "AA123456789BRX"):
            self.assertIsNone(rastreio.url_rastreio(codigo), codigo)

    def test_pedido_novo_sem_rastreio(self):
        p = self.publico()
        self.assertEqual((p["codigo_rastreio"], p["url_rastreio"], p["viagem"], p["eventos"]), (None, None, None, []))

    def test_status_geram_eventos_sem_barco(self):
        for status in ("pago", "enviado", "entregue"):
            regras.atualizar_status(self.conn, self.codigo, status)
        eventos = self.publico()["eventos"]
        self.assertEqual([(e["tipo"], e["mensagem"]) for e in eventos], [
            ("entregue", "Pedido entregue. Obrigado por comprar na Tipiti!"),
            ("outro", "Pedido enviado."),
            ("pago", "Pagamento confirmado. Já estamos separando o seu pedido."),
        ])
        self.assertRegex(eventos[0]["data"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_enviado_com_barco_vira_embarcado_e_aviso_no_painel(self):
        v = viagem(self.conn)
        rastreio.atualizar_pedido_admin(self.conn, self.codigo, {"status": "pago"})
        rastreio.atualizar_pedido_admin(self.conn, self.codigo,
                                        {"status": "enviado", "viagem_id": v["id"], "codigo_rastreio": " aa 123456789 br "})
        p = self.publico()
        self.assertEqual(p["eventos"][0], {"tipo": "embarcado", "mensagem": "Embarcou no B/M Amazonas Star rumo a Parintins.",
                                           "data": p["eventos"][0]["data"]})
        self.assertEqual(p["codigo_rastreio"], "AA123456789BR")
        self.assertTrue(p["url_rastreio"].endswith("objeto=AA123456789BR"))
        self.assertEqual(p["viagem"]["embarcacao"], "B/M Amazonas Star")
        texto = json.dumps(p, ensure_ascii=False)
        for dado in ("529.982.247-25", "52998224725", "maria@example.com", "99123", "Eduardo Ribeiro", "Silva"):
            self.assertNotIn(dado, texto)
        admin = next(x for x in regras.listar_pedidos(self.conn) if x["codigo"] == self.codigo)
        self.assertEqual(admin["whatsapp_aviso"], rastreio.aviso_whatsapp(self.conn, self.codigo))
        self.assertIn("Olá, Maria!", admin["whatsapp_aviso"])
        self.assertIn("Embarcou no B/M Amazonas Star rumo a Parintins.", admin["whatsapp_aviso"])
        self.assertIn("https://rastreamento.correios.com.br/app/index.php?objeto=AA123456789BR", admin["whatsapp_aviso"])
        self.assertIn(f"/pedido/{self.codigo}", admin["whatsapp_aviso"])
        self.assertEqual(viagens.listar_admin(self.conn)[0]["pedidos"], 1)

    def test_enviado_sem_barco_cita_o_codigo(self):
        rastreio.atualizar_pedido_admin(self.conn, self.codigo, {"status": "pago", "codigo_rastreio": "JAD-778899"})
        rastreio.atualizar_pedido_admin(self.conn, self.codigo, {"status": "enviado"})
        p = self.publico()
        self.assertEqual(p["eventos"][0]["mensagem"], "Pedido enviado. Código de rastreio: JAD-778899.")
        self.assertIsNone(p["url_rastreio"])

    def test_patch_invalido_nao_grava_nada(self):
        v = viagem(self.conn)
        for dados, campo in (({"viagem_id": 999}, "viagem_id"), ({"viagem_id": True}, "viagem_id"),
                             ({"codigo_rastreio": "<script>"}, "codigo_rastreio"),
                             ({"codigo_rastreio": "AA123456789BR", "status": "entregue"}, "status"),
                             ({"viagem_id": v["id"], "status": "voando"}, "status"), ({}, "status")):
            with self.assertRaises(regras.ErroValidacao) as e:
                rastreio.atualizar_pedido_admin(self.conn, self.codigo, dados)
            self.assertIn(campo, e.exception.campos, dados)
        p = self.publico()
        self.assertEqual((p["status"], p["codigo_rastreio"], p["viagem"], p["eventos"]),
                         ("aguardando_pagamento", None, None, []))
        # só o rastreio, sem status
        rastreio.atualizar_pedido_admin(self.conn, self.codigo, {"viagem_id": v["id"]})
        self.assertEqual(self.publico()["viagem"]["id"], v["id"])
        rastreio.atualizar_pedido_admin(self.conn, self.codigo, {"viagem_id": None, "codigo_rastreio": ""})
        self.assertEqual((self.publico()["viagem"], self.publico()["codigo_rastreio"]), (None, None))
        with self.assertRaises(regras.NaoEncontrado):
            rastreio.atualizar_pedido_admin(self.conn, "TPT-NAOEXISTE", {"status": "pago"})

    def test_eventos_do_painel(self):
        v = viagem(self.conn)
        rastreio.atualizar_pedido_admin(self.conn, self.codigo, {"viagem_id": v["id"]})
        for tipo in ("separado", "embarcado", "chegou_porto", "saiu_entrega"):
            rastreio.adicionar_evento(self.conn, self.codigo, {"tipo": tipo})
        rastreio.adicionar_evento(self.conn, self.codigo, {"tipo": "outro", "mensagem": "  Atraso por cheia do rio. "})
        self.assertEqual([e["mensagem"] for e in self.publico()["eventos"]], [
            "Atraso por cheia do rio.", "Saiu para entrega.", "Chegou ao porto de Parintins.",
            "Embarcou no B/M Amazonas Star rumo a Parintins.", "Pedido separado e embalado.",
        ])
        self.assertEqual(self.publico()["status"], "aguardando_pagamento")  # evento não muda o status
        for dados, campo in (({"tipo": "outro"}, "mensagem"), ({"tipo": "teleporte"}, "tipo"),
                             ({"tipo": "separado", "mensagem": "x" * 301}, "mensagem"),
                             ({"tipo": "separado", "mensagem": 5}, "mensagem")):
            with self.assertRaises(regras.ErroValidacao) as e:
                rastreio.adicionar_evento(self.conn, self.codigo, dados)
            self.assertIn(campo, e.exception.campos)
        regras.atualizar_status(self.conn, self.codigo, "cancelado")
        self.assertEqual(self.publico()["eventos"][0], {**self.publico()["eventos"][0], "tipo": "outro",
                                                        "mensagem": "Pedido cancelado."})
        with self.assertRaises(regras.ErroValidacao):
            rastreio.adicionar_evento(self.conn, self.codigo, {"tipo": "separado"})

    def test_expiracao_gera_evento_de_cancelamento(self):
        self.conn.execute("UPDATE pedidos SET criado_em = datetime('now', '-25 hours') WHERE codigo = ?", (self.codigo,))
        regras.expirar_pendentes(self.conn)
        p = self.publico()
        self.assertEqual(p["status"], "cancelado")
        self.assertEqual([(e["tipo"], e["mensagem"]) for e in p["eventos"]], [("outro", "Pedido cancelado.")])


_ips = (f"10.7.{i // 250}.{i % 250 + 1}" for i in itertools.count())


class TestBarcosApi(Base):
    def test_viagens_e_frete(self):
        corpo = {"zona": "santarem", "embarcacao": "N/M Rondônia", "saida": "2099-01-10T22:00:00Z",
                 "chegada_prevista": "2099-01-13T12:00:00Z"}
        self.assertEqual(self.json("/api/admin/viagens", "POST", corpo)[0], 401)
        status, v = self.admin("/api/admin/viagens", "POST", corpo)
        self.assertEqual(status, 201)
        status, erro = self.admin("/api/admin/viagens", "POST", {**corpo, "zona": "lua"})
        self.assertEqual((status, list(erro["campos"])), (422, ["zona"]))
        self.assertEqual(self.admin(f"/api/admin/viagens/{v['id']}", "PATCH", {"observacao": "Porto da Ceasa"})[1]
                         ["observacao"], "Porto da Ceasa")
        self.assertEqual(self.admin("/api/admin/viagens/9999", "PATCH", {"ativo": False})[0], 404)
        self.assertIn(v["id"], [x["id"] for x in self.admin("/api/admin/viagens")[1]])

        status, publicas = self.json("/api/viagens?zona=santarem")
        self.assertEqual((status, [x["id"] for x in publicas]), (200, [v["id"]]))
        self.assertEqual(self.json("/api/viagens?zona=xyz")[0], 422)
        self.assertIn(v["id"], [x["id"] for x in self.json("/api/viagens")[1]])

        frete = self.json("/api/frete?cep=68005-000&subtotal=1000")[1]
        self.assertEqual(frete["proximo_barco"]["embarcacao"], "N/M Rondônia")
        self.assertEqual(frete["chegada_estimada"], "2099-01-13")
        cot = self.json("/api/carrinho/cotacao", "POST", {"itens": ITENS, "cep": "68005-000"})[1]
        self.assertEqual(cot["frete"]["proximo_barco"]["saida"], "2099-01-10T22:00:00Z")
        self.assertIsNone(self.json("/api/frete?cep=01001-000")[1]["proximo_barco"])

    def test_rastreio_pelo_painel(self):
        status, pedido = self.json("/api/pedidos", "POST", {**CLIENTE, **PARINTINS, "itens": ITENS}, ip=next(_ips))
        self.assertEqual(status, 201)
        codigo = pedido["codigo"]
        self.assertEqual(pedido["eventos"], [])
        v = self.admin("/api/admin/viagens", "POST", {"zona": "parintins", "embarcacao": "B/M Lady Belém",
                                                      "saida": "2099-02-01T22:00:00Z",
                                                      "chegada_prevista": "2099-02-03T12:00:00Z"})[1]
        status, p = self.admin(f"/api/admin/pedidos/{codigo}", "PATCH", {"status": "pago"})
        self.assertEqual((status, p["status"]), (200, "pago"))
        self.assertIn("Pagamento confirmado", p["whatsapp_aviso"])
        status, p = self.admin(f"/api/admin/pedidos/{codigo}", "PATCH",
                               {"status": "enviado", "viagem_id": v["id"], "codigo_rastreio": "AB987654321BR"})
        self.assertEqual(p["eventos"][0]["tipo"], "embarcado")
        self.assertEqual(p["viagem"]["id"], v["id"])
        status, p = self.admin(f"/api/admin/pedidos/{codigo}/eventos", "POST", {"tipo": "chegou_porto"})
        self.assertEqual((status, p["eventos"][0]["mensagem"]), (201, "Chegou ao porto de Parintins."))
        self.assertEqual(self.json(f"/api/admin/pedidos/{codigo}/eventos", "POST", {"tipo": "separado"})[0], 401)
        self.assertEqual(self.admin("/api/admin/pedidos/TPT-NAOEXISTE1/eventos", "POST", {"tipo": "separado"})[0], 404)
        self.assertEqual(self.admin(f"/api/admin/pedidos/{codigo}", "PATCH", {"viagem_id": 99999})[0], 422)

        publico = self.json(f"/api/pedidos/{codigo}", ip=next(_ips))[1]
        self.assertEqual([e["tipo"] for e in publico["eventos"]], ["chegou_porto", "embarcado", "pago"])
        self.assertTrue(publico["url_rastreio"].endswith("AB987654321BR"))
        self.assertNotIn("whatsapp_aviso", publico)
        lista = self.admin("/api/admin/pedidos")[1]
        item = next(x for x in lista if x["codigo"] == codigo)
        self.assertIn("Chegou ao porto de Parintins.", item["whatsapp_aviso"])

    def test_paginas_novas(self):
        for caminho in ("/barcos", "/seja-revendedora", "/revenda", "/revenda/"):
            self.assertEqual(self.chamar(caminho)[0], 200, caminho)
        robots = self.chamar("/robots.txt")[1].decode()
        self.assertIn("Disallow: /revenda", robots)
        self.assertIn(b"/barcos</loc>", self.chamar("/sitemap.xml")[1])
