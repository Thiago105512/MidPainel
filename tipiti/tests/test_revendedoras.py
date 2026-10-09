"""Programa de revendedoras: cadastro, ativação, cupom, atribuição, comissão (com cupom, Pix, cancelamento e
expiração), pagamento das comissões e painel dela — sem dados pessoais dos clientes."""

import itertools
import json
import unittest
from datetime import datetime, timedelta

from loja import config, cupons, horario, regras, revendedoras
from tests.test_regras import CLIENTE, nova_conexao
from tests.test_servidor import Base

CPF_CLIENTE = "52998224725"
POWER_BANK = 11990  # preço do power-bank-20000mah no catálogo inicial


def gerar_cpf(semente):
    base = [int(c) for c in f"{semente:09d}"[-9:]]
    for n in (9, 10):
        soma = sum(d * (n + 1 - i) for i, d in enumerate(base))
        base.append(soma * 10 % 11 % 10)
    return "".join(map(str, base))


def cadastro(semente=123456789, **extra):
    return {"nome": "Maria Lúcia Souza", "whatsapp": "(93) 99123-4567", "cpf": gerar_cpf(semente),
            "cidade": "Parintins", "uf": "AM", "instagram": "@maria.achadinhos", "mensagem": "Vendo na minha rua.",
            **extra}


def criar_revendedora(conn, semente=123456789, ativar=True, **extra):
    dados = cadastro(semente, **{k: v for k, v in extra.items() if k in ("nome", "cidade", "uf")})
    revendedoras.cadastrar(conn, dados)
    rid = conn.execute("SELECT id FROM revendedoras WHERE cpf = ?", (dados["cpf"],)).fetchone()[0]
    if not ativar:
        return revendedoras.obter_admin(conn, rid)
    patch = {"status": "ativa", **{k: v for k, v in extra.items() if k.endswith("_pct")}}
    return revendedoras.atualizar(conn, rid, patch)


def pedido(conn, itens=None, **extra):
    return regras.criar_pedido(conn, {**CLIENTE, "itens": itens or [{"slug": "power-bank-20000mah", "quantidade": 1}],
                                      **extra})


def linha(conn, codigo):
    return conn.execute("SELECT revendedora_id, comissao_centavos, comissao_paga_em FROM pedidos WHERE codigo = ?",
                        (codigo,)).fetchone()


class TestCadastro(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def test_cadastro_valido_fica_pendente(self):
        self.assertEqual(revendedoras.cadastrar(self.conn, cadastro()), {"status": "pendente"})
        self.assertEqual(revendedoras.pendentes(self.conn), 1)
        r = revendedoras.listar_admin(self.conn)[0]
        self.assertEqual((r["status"], r["whatsapp"], r["instagram"], r["codigo"], r["token_acesso"]),
                         ("pendente", "5593991234567", "maria.achadinhos", None, None))
        self.assertIsNone(r["link_divulgacao"])
        self.assertIsNone(r["whatsapp_boas_vindas"])

    def test_cpf_repetido_responde_igual_sem_duplicar(self):
        revendedoras.cadastrar(self.conn, cadastro())
        self.assertEqual(revendedoras.cadastrar(self.conn, cadastro(nome="Outra Pessoa")), {"status": "pendente"})
        self.assertEqual(self.conn.execute("SELECT COUNT(*), MIN(nome) FROM revendedoras").fetchone()[:],
                         (1, "Maria Lúcia Souza"))

    def test_validacao(self):
        with self.assertRaises(regras.ErroValidacao) as e:
            revendedoras.cadastrar(self.conn, {"nome": "M", "whatsapp": "123", "cpf": "11111111111", "cidade": "",
                                               "uf": "XX", "instagram": "a b", "mensagem": "x" * 501})
        self.assertEqual(set(e.exception.campos), {"nome", "whatsapp", "cpf", "cidade", "uf", "instagram", "mensagem"})
        with self.assertRaises(regras.ErroValidacao) as e:
            revendedoras.cadastrar(self.conn, {**cadastro(), "whatsapp": None, "nome": ["x"], "mensagem": 3})
        self.assertEqual(set(e.exception.campos), {"whatsapp", "nome", "mensagem"})
        revendedoras.cadastrar(self.conn, cadastro(instagram="https://www.instagram.com/maria_vendas/"))
        self.assertEqual(revendedoras.listar_admin(self.conn)[0]["instagram"], "maria_vendas")


class TestAtivacao(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)

    def test_ativar_gera_codigo_token_links_e_cupom(self):
        r = criar_revendedora(self.conn, comissao_pct=12, desconto_cliente_pct=5)
        self.assertEqual(r["codigo"], "maria-parintins")
        self.assertGreaterEqual(len(r["token_acesso"]), 32)
        self.assertEqual(r["link_divulgacao"], f"{config.SITE_URL}/?r=maria-parintins")
        self.assertEqual(r["link_painel"], f"{config.SITE_URL}/revenda#{r['token_acesso']}")
        self.assertEqual(r["cupom"], {"codigo": "MARIA-PARINTINS", "descricao": "5% de desconto"})
        self.assertEqual((r["comissao_pct"], r["desconto_cliente_pct"]), (12, 5))
        for trecho in ("Oi, Maria!", r["link_divulgacao"], r["link_painel"], "MARIA-PARINTINS", "12%"):
            self.assertIn(trecho, r["whatsapp_boas_vindas"])
        self.assertEqual(revendedoras.pendentes(self.conn), 0)
        self.assertIsNotNone(r["ativada_em"])

        # mudar o desconto atualiza o cupom; zerar desativa; inativar desativa
        r = revendedoras.atualizar(self.conn, r["id"], {"desconto_cliente_pct": 8})
        self.assertEqual(r["cupom"]["descricao"], "8% de desconto")
        r = revendedoras.atualizar(self.conn, r["id"], {"desconto_cliente_pct": 0})
        self.assertIsNone(r["cupom"])
        r = revendedoras.atualizar(self.conn, r["id"], {"desconto_cliente_pct": 5})
        token = r["token_acesso"]
        r = revendedoras.atualizar(self.conn, r["id"], {"status": "inativa"})
        self.assertIsNone(r["cupom"])
        self.assertIsNone(r["whatsapp_boas_vindas"])
        _, erro = cupons.avaliar(self.conn, "MARIA-PARINTINS", 10000)
        self.assertEqual(erro, "Cupom inválido. Confira o código.")
        # reativar mantém código e token; novo_token troca o token
        r = revendedoras.atualizar(self.conn, r["id"], {"status": "ativa"})
        self.assertEqual((r["codigo"], r["token_acesso"], r["cupom"]["codigo"]), ("maria-parintins", token,
                                                                                  "MARIA-PARINTINS"))
        r = revendedoras.atualizar(self.conn, r["id"], {"novo_token": True})
        self.assertNotEqual(r["token_acesso"], token)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM cupons").fetchone()[0], 1)

    def test_validacao_do_patch(self):
        r = criar_revendedora(self.conn, ativar=False)
        for dados, campo in (({"status": "chefe"}, "status"), ({"comissao_pct": 51}, "comissao_pct"),
                             ({"comissao_pct": True}, "comissao_pct"), ({"desconto_cliente_pct": -1},
                                                                         "desconto_cliente_pct"),
                             ({"comissao_pct": 7.5}, "comissao_pct")):
            with self.assertRaises(regras.ErroValidacao) as e:
                revendedoras.atualizar(self.conn, r["id"], dados)
            self.assertIn(campo, e.exception.campos)
        with self.assertRaises(regras.NaoEncontrado):
            revendedoras.atualizar(self.conn, 999, {"status": "ativa"})

    def test_codigos_unicos_e_sem_colidir_com_cupons(self):
        cupons.criar(self.conn, {"codigo": "MARIA-PARINTINS", "tipo": "pct", "valor": 10})
        a = criar_revendedora(self.conn, 111222333, desconto_cliente_pct=5)
        b = criar_revendedora(self.conn, 222333444, desconto_cliente_pct=5)
        self.assertEqual((a["codigo"], b["codigo"]), ("maria-parintins-2", "maria-parintins-3"))
        self.assertEqual((a["cupom"]["codigo"], b["cupom"]["codigo"]), ("MARIA-PARINTINS-2", "MARIA-PARINTINS-3"))
        c = criar_revendedora(self.conn, 333444555, nome="Antônia Conceição", cidade="São Gabriel da Cachoeira")
        self.assertEqual(c["codigo"], "antonia-sao-gabriel")
        self.assertLessEqual(len(c["codigo"]), 20)
        d = criar_revendedora(self.conn, 444555666, nome="Antônia Conceição", cidade="São Gabriel da Cachoeira")
        self.assertEqual(d["codigo"], "antonia-sao-gabrie-2")
        # pendente ainda não tem código
        e = criar_revendedora(self.conn, 555666777, ativar=False)
        self.assertIsNone(e["codigo"])

    def test_cupom_de_mesmo_codigo_criado_depois_bloqueia_o_desconto(self):
        r = criar_revendedora(self.conn)  # ativa, sem desconto: ainda sem cupom
        cupons.criar(self.conn, {"codigo": "MARIA-PARINTINS", "tipo": "valor", "valor": 500})
        with self.assertRaises(regras.ErroValidacao) as e:
            revendedoras.atualizar(self.conn, r["id"], {"desconto_cliente_pct": 5})
        self.assertIn("desconto_cliente_pct", e.exception.campos)
        self.assertEqual(revendedoras.obter_admin(self.conn, r["id"])["desconto_cliente_pct"], 0)  # nada gravado


class TestComissao(unittest.TestCase):
    def setUp(self):
        self.conn = nova_conexao()
        self.addCleanup(self.conn.close)
        self.maria = criar_revendedora(self.conn, 123456789, comissao_pct=10, desconto_cliente_pct=10)
        self.joana = criar_revendedora(self.conn, 987654321, nome="Joana Dark", cidade="Santarém", uf="PA",
                                       comissao_pct=7, desconto_cliente_pct=5)

    def test_link_no_pix_sem_cupom_e_sem_frete(self):
        # Parintins, 1 unidade: frete de R$ 19,90 cobrado, mas fora da comissão
        codigo = pedido(self.conn, revendedora="maria-parintins", cep="69151-000", cidade="Parintins")
        p = regras.obter_pedido_publico(self.conn, codigo)
        self.assertEqual(p["frete_centavos"], 1990)
        desconto_pix = POWER_BANK * 5 // 100  # 599
        self.assertEqual(p["desconto_centavos"], desconto_pix)
        self.assertEqual(tuple(linha(self.conn, codigo))[:2], (self.maria["id"], (POWER_BANK - 599) * 10 // 100))
        self.assertEqual(linha(self.conn, codigo)["comissao_centavos"], 1139)  # 11391 × 10% arredondado para baixo
        self.assertNotIn("revendedora", p)
        self.assertNotIn("comissao_centavos", p)

    def test_cupom_dela_mais_pix(self):
        itens = [{"slug": "power-bank-20000mah", "quantidade": 2}]
        cot = regras.cotar_carrinho(self.conn, itens, cep="69151-000", cupom="maria-parintins")
        self.assertEqual(cot["revendedora"], {"nome": "Maria", "cidade": "Parintins"})
        codigo = pedido(self.conn, itens, cupom="MARIA-PARINTINS")
        # subtotal 23980 → cupom 10% = 2398 → Pix 5% de 21582 = 1079 → base 20503 → 10% = 2050
        self.assertEqual(cot["desconto_cupom_centavos"], 2398)
        self.assertEqual(cot["desconto_centavos"], 1079)
        self.assertEqual(tuple(linha(self.conn, codigo))[:2], (self.maria["id"], 2050))

    def test_cupom_de_uma_vence_o_link_da_outra(self):
        cot = regras.cotar_carrinho(self.conn, [{"slug": "power-bank-20000mah", "quantidade": 1}],
                                    cupom="JOANA-SANTAREM", revendedora="maria-parintins", pagamento="cartao")
        self.assertEqual(cot["revendedora"], {"nome": "Joana", "cidade": "Santarém"})
        codigo = pedido(self.conn, cupom="JOANA-SANTAREM", revendedora="maria-parintins", pagamento="cartao")
        # cartão: sem Pix. 11990 − 5% (599) = 11391 → 7% = 797
        self.assertEqual(tuple(linha(self.conn, codigo))[:2], (self.joana["id"], 797))

    def test_cupom_comum_com_link_conta_para_o_link(self):
        cupons.criar(self.conn, {"codigo": "BEMVINDO", "tipo": "valor", "valor": 1000})
        codigo = pedido(self.conn, cupom="BEMVINDO", revendedora="MARIA-PARINTINS ")
        # 11990 − 1000 = 10990 → Pix 549 → 10441 → 10% = 1044
        self.assertEqual(tuple(linha(self.conn, codigo))[:2], (self.maria["id"], 1044))

    def test_cupom_de_frete_gratis_nao_mexe_na_base(self):
        cupons.criar(self.conn, {"codigo": "FRETE0", "tipo": "frete"})
        codigo = pedido(self.conn, cupom="FRETE0", revendedora="maria-parintins", cep="69151-000",
                        cidade="Parintins")
        self.assertEqual(regras.obter_pedido_publico(self.conn, codigo)["frete_centavos"], 0)
        self.assertEqual(linha(self.conn, codigo)["comissao_centavos"], 1139)

    def test_sem_revendedora_codigo_desconhecido_ou_inativa(self):
        self.assertIsNone(linha(self.conn, pedido(self.conn))["revendedora_id"])
        self.assertIsNone(linha(self.conn, pedido(self.conn, revendedora="ninguem"))["revendedora_id"])
        self.assertIsNone(linha(self.conn, pedido(self.conn, revendedora={"x": 1}))["revendedora_id"])
        revendedoras.atualizar(self.conn, self.maria["id"], {"status": "inativa"})
        self.assertIsNone(linha(self.conn, pedido(self.conn, revendedora="maria-parintins"))["revendedora_id"])
        self.assertIsNone(regras.cotar_carrinho(self.conn, [{"slug": "power-bank-20000mah"}],
                                                revendedora="maria-parintins")["revendedora"])

    def test_compra_com_o_proprio_cpf_nao_gera_comissao(self):
        cpf_maria = self.conn.execute("SELECT cpf FROM revendedoras WHERE id = ?", (self.maria["id"],)).fetchone()[0]
        codigo = pedido(self.conn, cpf=cpf_maria, cupom="MARIA-PARINTINS", revendedora="maria-parintins")
        self.assertEqual(tuple(linha(self.conn, codigo))[:2], (None, 0))
        # o desconto do cupom vale normalmente
        self.assertGreater(regras.obter_pedido_publico(self.conn, codigo)["desconto_cupom_centavos"], 0)

    def test_status_cancelamento_expiracao_e_totais(self):
        pago = pedido(self.conn, revendedora="maria-parintins")
        enviado = pedido(self.conn, revendedora="maria-parintins")
        aguardando = pedido(self.conn, revendedora="maria-parintins")
        cancelado = pedido(self.conn, revendedora="maria-parintins")
        expirado = pedido(self.conn, revendedora="maria-parintins")
        regras.atualizar_status(self.conn, pago, "pago")
        for s in ("pago", "enviado"):
            regras.atualizar_status(self.conn, enviado, s)
        regras.atualizar_status(self.conn, cancelado, "pago")
        regras.atualizar_status(self.conn, cancelado, "cancelado")
        self.conn.execute("UPDATE pedidos SET criado_em = datetime('now', '-25 hours') WHERE codigo = ?", (expirado,))
        regras.expirar_pendentes(self.conn)
        self.assertEqual(linha(self.conn, cancelado)["comissao_centavos"], 0)
        self.assertEqual(linha(self.conn, expirado)["comissao_centavos"], 0)
        self.assertEqual(linha(self.conn, aguardando)["comissao_centavos"], 1139)  # guardada, mas ainda não conta
        totais = revendedoras.obter_admin(self.conn, self.maria["id"])["totais"]
        self.assertEqual(totais, {"vendas": 2, "a_receber_centavos": 2 * 1139, "pago_centavos": 0})
        # pago → aguardando pagamento: sai da conta até voltar a ser pago
        regras.atualizar_status(self.conn, pago, "aguardando_pagamento")
        self.assertEqual(revendedoras.obter_admin(self.conn, self.maria["id"])["totais"]["a_receber_centavos"], 1139)
        regras.atualizar_status(self.conn, pago, "pago")

        # lista do painel da loja
        lista = {p["codigo"]: p for p in regras.listar_pedidos(self.conn)}
        self.assertEqual(lista[pago]["revendedora"], {"id": self.maria["id"], "nome": "Maria Lúcia Souza",
                                                      "codigo": "maria-parintins"})
        self.assertEqual((lista[pago]["comissao_centavos"], lista[pago]["comissao_paga"]), (1139, False))

    def test_pagamento_das_comissoes(self):
        hoje = datetime.now(horario.FUSO_LOJA).date()
        antigo = pedido(self.conn, revendedora="maria-parintins")
        novo = pedido(self.conn, revendedora="maria-parintins")
        aguardando = pedido(self.conn, revendedora="maria-parintins")
        for codigo in (antigo, novo):
            regras.atualizar_status(self.conn, codigo, "pago")
        # "antigo" foi feito há 3 dias
        self.conn.execute("UPDATE pedidos SET criado_em = datetime('now', '-3 days') WHERE codigo = ?", (antigo,))
        ontem = (hoje - timedelta(days=1)).isoformat()
        r = revendedoras.registrar_pagamento(self.conn, self.maria["id"], {"ate": ontem})
        self.assertEqual(r, {"pago_centavos": 1139, "pedidos": 1, "ate": ontem})
        self.assertEqual(revendedoras.registrar_pagamento(self.conn, self.maria["id"], {"ate": ontem})["pago_centavos"], 0)
        r = revendedoras.registrar_pagamento(self.conn, self.maria["id"], {"ate": hoje.isoformat()})
        self.assertEqual((r["pago_centavos"], r["pedidos"]), (1139, 1))  # o aguardando não entra
        self.assertIsNone(linha(self.conn, aguardando)["comissao_paga_em"])
        totais = revendedoras.obter_admin(self.conn, self.maria["id"])["totais"]
        self.assertEqual(totais, {"vendas": 2, "a_receber_centavos": 0, "pago_centavos": 2278})
        # cancelar um pedido com comissão já paga mantém o registro do que foi pago
        regras.atualizar_status(self.conn, novo, "cancelado")
        self.assertEqual(linha(self.conn, novo)["comissao_centavos"], 1139)
        self.assertEqual(revendedoras.obter_admin(self.conn, self.maria["id"])["totais"]["pago_centavos"], 2278)
        for ate in ("2026-13-01", "ontem", None, 20261009):
            with self.assertRaises(regras.ErroValidacao):
                revendedoras.registrar_pagamento(self.conn, self.maria["id"], {"ate": ate})
        with self.assertRaises(regras.NaoEncontrado):
            revendedoras.registrar_pagamento(self.conn, 999, {"ate": ontem})

    def test_painel_sem_dados_dos_clientes(self):
        codigo = pedido(self.conn, cupom="MARIA-PARINTINS", cep="69151-000", cidade="Parintins")
        regras.atualizar_status(self.conn, codigo, "pago")
        token = self.maria["token_acesso"]
        row = revendedoras.autenticar(self.conn, token)
        self.assertEqual(row["id"], self.maria["id"])
        self.assertIsNone(revendedoras.autenticar(self.conn, token[:-1] + ("A" if token[-1] != "A" else "B")))
        self.assertIsNone(revendedoras.autenticar(self.conn, ""))
        self.assertIsNone(revendedoras.autenticar(self.conn, None))
        p = revendedoras.painel(self.conn, row)
        self.assertEqual(set(p), {"nome", "codigo", "cidade", "comissao_pct", "link_divulgacao", "cupom", "totais",
                                  "pedidos"})
        self.assertEqual(p["pedidos"], [{
            "codigo": codigo, "data": p["pedidos"][0]["data"], "cidade": "Parintins", "uf": "AM",
            "total_centavos": regras.obter_pedido_publico(self.conn, codigo)["total_centavos"],
            "comissao_centavos": linha(self.conn, codigo)["comissao_centavos"], "status": "pago",
            "comissao_paga": False,
        }])
        self.assertEqual(p["totais"]["vendas"], 1)
        texto = json.dumps(p, ensure_ascii=False)
        for dado in (CLIENTE["nome"], "Maria da", CPF_CLIENTE, "529.982", CLIENTE["email"], "99123-4567",
                     "92991234567", CLIENTE["endereco"], CLIENTE["bairro"], "69151"):
            self.assertNotIn(dado, texto)


_ips = (f"10.8.{i // 250}.{i % 250 + 1}" for i in itertools.count())


class TestRevendedorasApi(Base):
    def test_fluxo_completo(self):
        status, corpo = self.json("/api/revendedoras", "POST", cadastro(246813579, nome="Rosa Maria",
                                                                         cidade="Macapá", uf="AP"), ip=next(_ips))
        self.assertEqual((status, corpo), (201, {"status": "pendente"}))
        self.assertGreaterEqual(self.admin("/api/admin/resumo")[1]["revendedoras_pendentes"], 1)
        self.assertEqual(self.json("/api/admin/revendedoras")[0], 401)
        lista = self.admin("/api/admin/revendedoras?status=pendente")[1]
        rosa = next(r for r in lista if r["nome"] == "Rosa Maria")
        self.assertEqual(self.admin("/api/admin/revendedoras?status=xx")[0], 422)

        status, rosa = self.admin(f"/api/admin/revendedoras/{rosa['id']}", "PATCH",
                                  {"status": "ativa", "comissao_pct": 10, "desconto_cliente_pct": 5})
        self.assertEqual((status, rosa["codigo"]), (200, "rosa-macapa"))
        self.assertEqual(self.admin("/api/admin/revendedoras/99999", "PATCH", {"status": "ativa"})[0], 404)

        cot = self.json("/api/carrinho/cotacao", "POST", {"itens": ITENS, "revendedora": "rosa-macapa"})[1]
        self.assertEqual(cot["revendedora"], {"nome": "Rosa", "cidade": "Macapá"})
        status, pedido_criado = self.json("/api/pedidos", "POST",
                                          {**CLIENTE, "itens": ITENS, "revendedora": "rosa-macapa"}, ip=next(_ips))
        self.assertEqual(status, 201)
        codigo = pedido_criado["codigo"]
        self.admin(f"/api/admin/pedidos/{codigo}", "PATCH", {"status": "pago"})

        headers = {"Authorization": f"Bearer {rosa['token_acesso']}"}
        status, painel = self.json("/api/revenda/painel", headers=headers, ip=next(_ips))
        self.assertEqual(status, 200)
        self.assertEqual(painel["pedidos"][0]["codigo"], codigo)
        self.assertEqual(painel["totais"], {"vendas": 1, "a_receber_centavos": 1139, "pago_centavos": 0})
        self.assertNotIn(CLIENTE["email"], json.dumps(painel))

        hoje = datetime.now(horario.FUSO_LOJA).date().isoformat()
        status, pago = self.admin(f"/api/admin/revendedoras/{rosa['id']}/pagamentos", "POST", {"ate": hoje})
        self.assertEqual((status, pago["pago_centavos"]), (200, 1139))
        painel = self.json("/api/revenda/painel", headers=headers, ip=next(_ips))[1]
        self.assertTrue(painel["pedidos"][0]["comissao_paga"])

        self.admin(f"/api/admin/revendedoras/{rosa['id']}", "PATCH", {"status": "inativa"})
        status, corpo = self.json("/api/revenda/painel", headers=headers, ip=next(_ips))
        self.assertEqual(status, 403)

    def test_token_errado_e_limitado(self):
        ip = next(_ips)
        self.assertEqual(self.json("/api/revenda/painel", ip=ip)[0], 401)  # sem token não conta
        for _ in range(10):
            self.assertEqual(self.json("/api/revenda/painel", headers={"Authorization": "Bearer " + "x" * 43},
                                       ip=ip)[0], 401)
        status, corpo = self.json("/api/revenda/painel", headers={"Authorization": "Bearer " + "x" * 43}, ip=ip)
        self.assertEqual((status, corpo["erro"]), (429, "Muitas tentativas. Aguarde alguns minutos."))
        # o limite da revenda não bloqueia o painel admin do mesmo IP
        self.assertEqual(self.admin("/api/admin/resumo", ip=ip)[0], 200)

    def test_limite_de_cadastros(self):
        ip = next(_ips)
        self.assertEqual(self.json("/api/revendedoras", "POST", {"nome": "x"}, ip=ip)[0], 422)  # erro não conta
        for i in range(3):
            self.assertEqual(self.json("/api/revendedoras", "POST", cadastro(300000000 + i), ip=ip)[0], 201)
        self.assertEqual(self.json("/api/revendedoras", "POST", cadastro(300000010), ip=ip)[0], 429)


ITENS = [{"slug": "power-bank-20000mah", "quantidade": 1}]
