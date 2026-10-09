"""Integração da rodada 3 com a rodada 2: eventos de rastreio → e-mail (um por evento), separação pelo rastreio,
Pix no e-mail do pedido, QR do 2FA, papéis nas rotas da rodada 2 e LGPD de encomendas, revendedoras e eventos."""

import json
import unittest

from loja import ajustes, encomendas, pix, privacidade, rastreio, regras, revendedoras, separacao, usuarios, viagens
from loja.validacao import ErroValidacao
from tests.test_regras import CLIENTE, nova_conexao
from tests.test_revendedoras import cadastro, criar_revendedora, gerar_cpf
from tests.test_rodada3_api import SENHA, Rodada3, ip

VIAGEM = {"zona": "manaus", "embarcacao": "B/M Amazonas Star", "saida": "2030-10-12T22:00:00Z",
          "chegada_prevista": "2030-10-14T12:00:00Z"}


def pedido(conn, **extra):
    return regras.criar_pedido(conn, {**CLIENTE, "itens": [{"slug": "power-bank-20000mah", "quantidade": 1}],
                                      **extra})


def emails_evento(conn, codigo):
    return [r["assunto"] for r in conn.execute(
        "SELECT assunto FROM emails_saida WHERE tipo = 'evento' AND assunto LIKE ? ORDER BY id", (f"%{codigo}%",))]


class TestEventosEEmails(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def test_um_email_por_evento(self):
        codigo = pedido(self.conn)
        regras.atualizar_status(self.conn, codigo, "pago")
        separacao.marcar_separados(self.conn, {"codigos": [codigo]})
        v = viagens.criar(self.conn, VIAGEM)
        rastreio.atualizar_pedido_admin(self.conn, codigo, {"viagem_id": v["id"], "status": "enviado"})
        rastreio.adicionar_evento(self.conn, codigo, {"tipo": "chegou_porto"})
        eventos = regras.obter_pedido_publico(self.conn, codigo)["eventos"]
        self.assertEqual([e["tipo"] for e in eventos], ["chegou_porto", "embarcado", "separado", "pago"])
        assuntos = emails_evento(self.conn, codigo)
        self.assertEqual(len(assuntos), 4)
        for trecho, assunto in zip(("Pagamento confirmado", "separado", "embarcado", "porto"), assuntos):
            self.assertIn(trecho, assunto)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM emails_saida WHERE tipo = 'status'").fetchone()[0], 0)
        texto = self.conn.execute("SELECT texto FROM emails_saida WHERE assunto LIKE '%embarcado%'").fetchone()[0]
        self.assertIn("Embarcou no B/M Amazonas Star rumo a Manaus.", texto)

    def test_evento_generico_de_status_usa_o_nome_do_status(self):
        codigo = pedido(self.conn)
        regras.atualizar_status(self.conn, codigo, "cancelado")
        assunto, texto = self.conn.execute("SELECT assunto, texto FROM emails_saida WHERE tipo = 'evento'").fetchone()
        self.assertIn("Cancelado", assunto)
        self.assertIn("engano", texto)

    def test_evento_invalido_nao_grava_nem_manda_email(self):
        codigo = pedido(self.conn)
        with self.assertRaises(ErroValidacao):
            rastreio.adicionar_evento(self.conn, codigo, {"tipo": "teletransportado"})
        self.assertEqual(emails_evento(self.conn, codigo), [])
        self.assertFalse(self.conn.in_transaction)

    def test_pedido_anonimizado_nao_recebe_email(self):
        codigo = pedido(self.conn)
        self.conn.execute("UPDATE pedidos SET anonimizado_em = datetime('now') WHERE codigo = ?", (codigo,))
        rastreio.adicionar_evento(self.conn, codigo, {"tipo": "outro", "mensagem": "Teste"})
        self.assertEqual(emails_evento(self.conn, codigo), [])

    def test_qr_do_2fa_usa_o_modulo_de_qr(self):
        svg = usuarios.qr_svg("otpauth://totp/Tipiti:a%40b.com?secret=JBSWY3DPEHPK3PXP&issuer=Tipiti")
        self.assertTrue(svg.startswith("<svg") and "<path" in svg)


class TestLgpdRodada2(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def solicitacao(self, cpf=CLIENTE["cpf"], email=CLIENTE["email"]):
        return privacidade.criar_solicitacao(self.conn, {"tipo": "exclusao", "email": email, "cpf": cpf})["protocolo"]

    def encomenda(self, whatsapp=CLIENTE["telefone"]):
        return encomendas.criar(self.conn, {"nome": "Maria da Silva", "whatsapp": whatsapp, "cidade": "Manaus",
                                            "uf": "AM", "descricao": "Uma panela de pressão", "quantidade": 1})

    def test_exporta_e_anonimiza_encomendas_e_eventos(self):
        codigo = pedido(self.conn)
        regras.atualizar_status(self.conn, codigo, "pago")
        rastreio.adicionar_evento(self.conn, codigo, {"tipo": "outro", "mensagem": "Entregue ao porteiro João."})
        regras.atualizar_status(self.conn, codigo, "enviado")
        regras.atualizar_status(self.conn, codigo, "entregue")
        enc = self.encomenda()
        protocolo = self.solicitacao()
        dados = privacidade.exportar(self.conn, protocolo)
        self.assertEqual([e["codigo"] for e in dados["encomendas"]], [enc])
        self.assertIn("Entregue ao porteiro João.", [e["mensagem"] for e in dados["pedidos"][0]["eventos"]])
        self.assertNotIn("comissao_centavos", dados["pedidos"][0])
        self.assertIsNone(dados["revendedora"])
        # encomenda em andamento impede a anonimização
        with self.assertRaises(ErroValidacao) as ctx:
            privacidade.anonimizar(self.conn, protocolo)
        self.assertIn("encomendas", ctx.exception.campos)
        encomendas.atualizar_admin(self.conn, enc, {"status": "cancelada"})
        r = privacidade.anonimizar(self.conn, protocolo)
        self.assertEqual(r["encomendas_anonimizadas"], 1)
        row = self.conn.execute("SELECT nome, whatsapp, cidade FROM encomendas WHERE codigo = ?", (enc,)).fetchone()
        self.assertEqual(tuple(row), ("Titular anonimizado", "", ""))
        mensagens = [e["mensagem"] for e in regras.obter_pedido_publico(self.conn, codigo)["eventos"]]
        self.assertNotIn("Entregue ao porteiro João.", mensagens)
        self.assertNotIn("João", json.dumps(mensagens, ensure_ascii=False))

    def test_revendedora_ativa_ou_com_comissao_a_receber_recusa(self):
        cpf = gerar_cpf(987654321)
        r = criar_revendedora(self.conn, 987654321, comissao_pct=10, desconto_cliente_pct=5)
        venda = pedido(self.conn, cpf="529.982.247-25", revendedora=r["codigo"])
        regras.atualizar_status(self.conn, venda, "pago")
        protocolo = self.solicitacao(cpf=cpf, email="maria.revenda@example.com")
        dados = privacidade.exportar(self.conn, protocolo)
        self.assertEqual(dados["revendedora"]["instagram"], "maria.achadinhos")
        self.assertNotIn("token_acesso", dados["revendedora"])
        self.assertEqual(dados["revendedora"]["comissoes"][0]["pedido"], venda)
        self.assertNotIn("cliente_nome", dados["revendedora"]["comissoes"][0])
        with self.assertRaises(ErroValidacao) as ctx:
            privacidade.anonimizar(self.conn, protocolo)
        self.assertIn("ativa", ctx.exception.mensagem)
        revendedoras.atualizar(self.conn, r["id"], {"status": "inativa"})
        with self.assertRaises(ErroValidacao) as ctx:
            privacidade.anonimizar(self.conn, protocolo)
        self.assertIn("comissões a receber", ctx.exception.mensagem)
        revendedoras.registrar_pagamento(self.conn, r["id"], {"ate": "2099-12-31"})
        resultado = privacidade.anonimizar(self.conn, protocolo)
        self.assertTrue(resultado["revendedora_anonimizada"])
        row = self.conn.execute("SELECT * FROM revendedoras WHERE id = ?", (r["id"],)).fetchone()
        self.assertEqual((row["nome"], row["whatsapp"], row["instagram"], row["codigo"], row["token_acesso"]),
                         ("Revendedora anonimizada", "", "", None, None))
        self.assertNotEqual(row["cpf"], cpf)
        self.assertEqual(self.conn.execute("SELECT ativo FROM cupons WHERE revendedora_id = ?", (r["id"],)).fetchone()[0],
                         0)
        # a comissão paga continua no pedido (registro financeiro); o cadastro não pode mais ser reativado
        self.assertTrue(self.conn.execute("SELECT comissao_paga_em FROM pedidos WHERE codigo = ?", (venda,)).fetchone()[0])
        with self.assertRaises(ErroValidacao):
            revendedoras.atualizar(self.conn, r["id"], {"status": "ativa"})
        self.assertEqual(revendedoras.cadastrar(self.conn, cadastro(987654321)), {"status": "pendente"})

    def test_revendedora_pendente_sem_vendas_e_anonimizada(self):
        cpf = gerar_cpf(111222333)
        revendedoras.cadastrar(self.conn, cadastro(111222333))
        protocolo = self.solicitacao(cpf=cpf, email="outra@example.com")
        self.assertTrue(privacidade.anonimizar(self.conn, protocolo)["revendedora_anonimizada"])
        self.assertIsNone(self.conn.execute("SELECT 1 FROM revendedoras WHERE cpf = ?", (cpf,)).fetchone())


class TestPapeisRodada2(Rodada3):
    def operador(self):
        login = f"op{ip().replace('.', '')}@tipiti.com.br"
        self.criar_usuario(login, "operador")
        return self.entrar(login)[1]["sessao"]

    def test_operador_usa_viagens_eventos_e_encomendas(self):
        sessao = self.operador()
        status, v = self.com_sessao(sessao, "/api/admin/viagens", "POST", VIAGEM)
        self.assertEqual(status, 201, v)
        self.assertEqual(self.com_sessao(sessao, "/api/admin/viagens")[0], 200)
        status, v2 = self.com_sessao(sessao, f"/api/admin/viagens/{v['id']}", "PATCH", {"observacao": "Porão 2"})
        self.assertEqual((status, v2["observacao"]), (200, "Porão 2"))
        codigo = self.pedido()
        status, r = self.com_sessao(sessao, f"/api/admin/pedidos/{codigo}/eventos", "POST", {"tipo": "separado"})
        self.assertEqual(status, 201, r)
        self.assertEqual(r["eventos"][0]["tipo"], "separado")
        self.assertEqual(len(self.sql("SELECT 1 FROM emails_saida e JOIN pedidos p ON e.assunto LIKE '%' || p.codigo || '%' "
                                      "WHERE p.codigo = ? AND e.tipo = 'evento'", (codigo,))), 1)
        self.assertEqual(self.com_sessao(sessao, "/api/admin/encomendas")[0], 200)

    def test_operador_sem_revendedoras_feeds_cupons(self):
        sessao = self.operador()
        for metodo, caminho, corpo in (("GET", "/api/admin/revendedoras", None),
                                       ("PATCH", "/api/admin/revendedoras/1", {"status": "ativa"}),
                                       ("POST", "/api/admin/revendedoras/1/pagamentos", {"ate": "2030-01-01"}),
                                       ("GET", "/api/admin/feeds", None), ("GET", "/api/admin/cupons", None),
                                       ("POST", "/api/admin/cupons", {"codigo": "X"}),
                                       ("GET", "/api/admin/historico", None)):
            status, r = self.com_sessao(sessao, caminho, metodo, corpo)
            self.assertEqual((status, r), (403, {"erro": "Sem permissão."}), caminho)

    def test_operador_nunca_recebe_comissao(self):
        conn = nova_conexao_servidor(self)
        r = criar_revendedora(conn, 555666777, comissao_pct=10)
        codigo = regras.criar_pedido(conn, {**CLIENTE, "revendedora": r["codigo"],
                                            "itens": [{"slug": "power-bank-20000mah", "quantidade": 1}]})
        self.assertGreater(conn.execute("SELECT comissao_centavos FROM pedidos WHERE codigo = ?",
                                        (codigo,)).fetchone()[0], 0)
        dono = json.dumps(self.admin("/api/admin/pedidos")[1])
        self.assertIn("comissao_centavos", dono)
        sessao = self.operador()
        status, pedidos = self.com_sessao(sessao, "/api/admin/pedidos")
        self.assertEqual(status, 200)
        texto = json.dumps(pedidos)
        for campo in ("comissao", "token_acesso", "link_painel", "custo", "lucro"):
            self.assertNotIn(campo, texto)
        self.assertIn(codigo, texto)
        self.assertIn("revendedora", json.loads(dono)[0])  # o dono vê quem vendeu
        self.assertTrue(all("revendedora" not in p for p in pedidos))  # o operador não
        status, p = self.com_sessao(sessao, f"/api/admin/pedidos/{codigo}", "PATCH", {"status": "pago"})
        self.assertEqual(status, 200, p)
        self.assertNotIn("comissao", json.dumps(p))

    def test_operador_nao_grava_oferta_relampago(self):
        sessao = self.operador()
        status, p = self.com_sessao(sessao, "/api/admin/produtos/fita-led-rgb-5m", "PATCH",
                                    {"promo_pct": 30, "promo_fim": "2030-01-01T00:00:00Z", "estoque": 7})
        self.assertEqual(status, 200, p)
        self.assertEqual(tuple(self.sql("SELECT promo_pct, estoque FROM produtos WHERE slug = 'fita-led-rgb-5m'")[0]),
                         (None, 7))

    def test_2fa_devolve_qr(self):
        login = f"qr{ip().replace('.', '')}@tipiti.com.br"
        self.criar_usuario(login, "operador")
        sessao = self.entrar(login, SENHA)[1]["sessao"]
        status, r = self.com_sessao(sessao, "/api/admin/eu/2fa/iniciar", "POST", {})
        self.assertEqual(status, 200)
        self.assertTrue(r["qr_svg"].startswith("<svg"))


def nova_conexao_servidor(teste):
    from loja import db
    conn = db.conectar(teste.servidor.db_path)
    teste.addCleanup(conn.close)
    return conn


class TestPixNoEmail(unittest.TestCase):
    def test_copia_e_cola_do_pedido(self):
        a = {"chave_pix": "pix@tipiti.com.br", "pix_nome": "Tipiti", "pix_cidade": "Manaus"}
        payload = pix.copia_e_cola_do_pedido(a, "TPT-ABC123", 3356)
        self.assertEqual(payload[-4:], f"{pix.crc16(payload[:-4]):04X}")
        self.assertIn("5405" + "33.56", payload)
        self.assertIn("TPTABC123", payload)
        self.assertIsNone(pix.copia_e_cola_do_pedido({"chave_pix": "pix@tipiti.com.br"}, "TPT-ABC123", 3356))
        self.assertEqual(ajustes.PADROES["pix_cidade"], "MANAUS")


if __name__ == "__main__":
    unittest.main()
