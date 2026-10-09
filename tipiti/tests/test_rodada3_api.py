"""Rodada 3 pela API HTTP: LGPD, e-mails, Minha conta, avise-me, carrinhos, separação, usuários, papéis e 2FA."""

import itertools
import json

from loja import horario, totp
from tests.test_regras import CLIENTE
from tests.test_servidor import TOKEN, Base

_ips = (f"10.30.{i // 250}.{i % 250 + 1}" for i in itertools.count())
SENHA = "senha-forte-123"
CAMPOS_PROIBIDOS = ("custo_centavos", "lucro_centavos", "custo_unit_centavos", "margem", "markup", "pedidos_sem_custo")


def ip():
    return next(_ips)


class Rodada3(Base):
    def pedido(self, itens=None, **extra):
        itens = itens or [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}]
        status, corpo = self.json("/api/pedidos", "POST", {**CLIENTE, **extra, "itens": itens}, ip=ip())
        self.assertEqual(status, 201, corpo)
        return corpo["codigo"]

    def com_sessao(self, sessao, caminho, metodo="GET", corpo=None, endereco=None):
        return self.json(caminho, metodo, corpo, headers={"Authorization": f"Bearer {sessao}"}, ip=endereco or ip())

    def criar_usuario(self, login, papel="operador", senha=SENHA):
        status, u = self.admin("/api/admin/usuarios", "POST", {"nome": login.split("@")[0].title(), "login": login,
                                                               "papel": papel, "senha": senha})
        self.assertEqual(status, 201, u)
        return u

    def entrar(self, login, senha=SENHA, codigo=None, endereco=None):
        corpo = {"login": login, "senha": senha}
        if codigo:
            corpo["codigo_2fa"] = codigo
        return self.json("/api/admin/login", "POST", corpo, ip=endereco or ip())


class TestLojaLegalELgpd(Rodada3):
    def test_loja_tem_empresa_e_pendencias(self):
        loja = self.json("/api/loja")[1]
        self.assertEqual(loja["empresa"]["nome_fantasia"], "Tipiti")
        self.assertIsNone(loja["empresa"]["documento_formatado"])
        self.assertIn("razão social", loja["pendencias_legais"])
        status, a = self.admin("/api/admin/ajustes", "PUT", {"empresa_razao_social": "Tipiti Ltda",
                                                             "empresa_documento": "11222333000181"})
        self.assertEqual(status, 200)
        self.addCleanup(self.admin, "/api/admin/ajustes", "PUT", {"empresa_razao_social": "", "empresa_documento": ""})
        loja = self.json("/api/loja")[1]
        self.assertEqual(loja["empresa"]["documento_formatado"], "11.222.333/0001-81")
        self.assertNotIn("razão social", loja["pendencias_legais"])
        resumo = self.admin("/api/admin/resumo")[1]
        self.assertEqual(resumo["pendencias_legais"], loja["pendencias_legais"])
        self.assertIs(resumo["email_configurado"], False)
        self.assertIsInstance(resumo["emails_pendentes"], int)
        self.assertEqual(self.admin("/api/admin/ajustes", "PUT", {"empresa_documento": "123"})[0], 422)

    def test_textos_legais_e_paginas(self):
        for caminho in ("/api/legal/privacidade", "/api/legal/termos"):
            status, doc = self.json(caminho)
            self.assertEqual(status, 200)
            self.assertTrue(doc["secoes"] and doc["titulo"] and doc["atualizado_em"])
        for caminho in ("/conta", "/minha-conta", "/privacidade", "/termos", "/meus-dados"):
            self.assertEqual(self.chamar(caminho)[0], 200, caminho)
        self.assertIn(b"/privacidade", self.chamar("/sitemap.xml")[1])

    def test_checkout_exige_aceite(self):
        corpo = {**CLIENTE, "itens": [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}]}
        del corpo["aceite_termos"]
        status, r = self.json("/api/pedidos", "POST", corpo, ip=ip())
        self.assertEqual(status, 422)
        self.assertIn("aceite_termos", r["campos"])

    def test_solicitacao_lgpd_e_painel(self):
        codigo = self.pedido(aceite_whatsapp=True)
        endereco = ip()
        status, r = self.json("/api/privacidade/solicitacoes", "POST",
                              {"tipo": "copia", "email": CLIENTE["email"], "cpf": CLIENTE["cpf"]}, ip=endereco)
        self.assertEqual(status, 201)
        protocolo = r["protocolo"]
        self.assertRegex(protocolo, r"^LGPD-[A-Z0-9]{8}$")
        self.assertEqual(self.json("/api/privacidade/solicitacoes", "POST", {"tipo": "x"}, ip=endereco)[0], 422)
        for _ in range(2):
            self.assertEqual(self.json("/api/privacidade/solicitacoes", "POST",
                                       {"tipo": "correcao", "email": "a@b.com", "cpf": CLIENTE["cpf"]},
                                       ip=endereco)[0], 201)
        self.assertEqual(self.json("/api/privacidade/solicitacoes", "POST",
                                   {"tipo": "correcao", "email": "a@b.com", "cpf": CLIENTE["cpf"]}, ip=endereco)[0], 429)

        lista = self.admin("/api/admin/privacidade")[1]
        self.assertIn(protocolo, [s["protocolo"] for s in lista])
        status, dados = self.admin(f"/api/admin/privacidade/{protocolo}/dados")
        self.assertEqual(status, 200)
        self.assertIn(codigo, [p["codigo"] for p in dados["pedidos"]])
        for campo in ("pedidos", "enderecos_salvos", "avise_me", "carrinhos", "solicitacoes_lgpd", "emails_enviados"):
            self.assertIn(campo, dados)
        status, s = self.admin(f"/api/admin/privacidade/{protocolo}", "PATCH",
                               {"status": "em_andamento", "resposta": "Estamos preparando."})
        self.assertEqual((status, s["status"]), (200, "em_andamento"))
        self.assertEqual(self.admin("/api/admin/privacidade/LGPD-ZZZZZZZZ", "PATCH", {"status": "aberta"})[0], 404)
        # anonimizar: recusa enquanto há pedido em andamento
        status, erro = self.admin(f"/api/admin/privacidade/{protocolo}/anonimizar", "POST", {})
        self.assertEqual(status, 422)
        self.assertIn("pedidos", erro["campos"])
        hist = self.admin("/api/admin/historico?alvo=privacidade")[1]
        self.assertIn("lgpd_exportar", [h["acao"] for h in hist["itens"]])


class TestMinhaConta(Rodada3):
    def token_do_link(self, email):
        texto = self.sql("SELECT texto FROM emails_saida WHERE tipo = 'conta' AND para = ? ORDER BY id DESC",
                         (email,))[0][0]
        return texto.split("/conta#")[1].split()[0]

    def test_fluxo_completo(self):
        email = "conta.cliente@example.com"
        self.pedido(email=email)
        respostas = [self.json("/api/conta/acesso", "POST", {"email": e}, ip=ip())
                     for e in (email, "nao-existe@example.com")]
        self.assertEqual(respostas[0], respostas[1])  # não revela se o e-mail existe
        self.assertEqual(respostas[0], (200, {"ok": True}))
        self.assertEqual(self.json("/api/conta/acesso", "POST", {"email": "x"}, ip=ip())[0], 422)
        token = self.token_do_link(email)
        self.assertEqual(self.json("/api/conta/sessao", "POST", {"token": "x" * 43}, ip=ip())[0], 401)
        status, s = self.json("/api/conta/sessao", "POST", {"token": token}, ip=ip())
        self.assertEqual(status, 200)
        self.assertRegex(s["expira_em"], r"Z$")
        self.assertEqual(self.json("/api/conta/sessao", "POST", {"token": token}, ip=ip())[0], 401)  # uso único
        conta = {"Authorization": f"Conta {s['sessao']}"}
        status, dados = self.json("/api/conta", headers=conta, ip=ip())
        self.assertEqual(status, 200)
        self.assertEqual((dados["email"], len(dados["pedidos"])), (email, 1))
        self.assertNotIn("cliente", dados["pedidos"][0])
        self.assertEqual(self.json("/api/conta", headers={"Authorization": "Conta " + "y" * 43}, ip=ip())[0], 401)
        self.assertEqual(self.json("/api/conta", ip=ip())[0], 401)
        self.assertEqual(self.json("/api/conta", headers={"Authorization": f"Bearer {TOKEN}"}, ip=ip())[0], 401)
        status, e = self.json("/api/conta/enderecos", "POST", {"cep": "69005000", "endereco": "Rua A", "numero": "1",
                                                               "bairro": "Centro", "cidade": "Manaus", "uf": "AM"},
                              headers=conta, ip=ip())
        self.assertEqual(status, 201)
        self.assertEqual(len(self.json("/api/conta", headers=conta, ip=ip())[1]["enderecos"]), 1)
        self.assertEqual(self.json(f"/api/conta/enderecos/{e['id']}", "DELETE", headers=conta, ip=ip())[0], 200)
        self.assertEqual(self.json(f"/api/conta/enderecos/{e['id']}", "DELETE", headers=conta, ip=ip())[0], 404)
        self.assertEqual(self.json("/api/conta/sessao", "DELETE", headers=conta, ip=ip())[0], 200)
        self.assertEqual(self.json("/api/conta", headers=conta, ip=ip())[0], 401)
        # só hashes no banco
        self.assertEqual(self.sql("SELECT COUNT(*) FROM sessoes_conta WHERE token_hash = ?", (s["sessao"],))[0][0], 0)

    def test_limites(self):
        endereco = ip()
        for i in range(5):
            self.assertEqual(self.json("/api/conta/acesso", "POST", {"email": f"l{i}@example.com"}, ip=endereco)[0], 200)
        self.assertEqual(self.json("/api/conta/acesso", "POST", {"email": "l9@example.com"}, ip=endereco)[0], 429)
        for _ in range(5):  # por e-mail, mesmo trocando de IP
            self.assertEqual(self.json("/api/conta/acesso", "POST", {"email": "alvo@example.com"}, ip=ip())[0], 200)
        self.assertEqual(self.json("/api/conta/acesso", "POST", {"email": "alvo@example.com"}, ip=ip())[0], 429)
        endereco = ip()
        for _ in range(20):
            self.json("/api/conta/sessao", "POST", {"token": "z" * 43}, ip=endereco)
        self.assertEqual(self.json("/api/conta/sessao", "POST", {"token": "z" * 43}, ip=endereco)[0], 429)


class TestAviseMeECarrinhos(Rodada3):
    def test_avise_me(self):
        self.sql("UPDATE produtos SET estoque = 0 WHERE slug = 'mini-projetor-portatil'")
        corpo = {"slug": "mini-projetor-portatil", "email": "avise@example.com", "nome": "Bia", "aceite": True}
        self.assertEqual(self.json("/api/avise-me", "POST", corpo, ip=ip())[0], 201)
        self.assertEqual(self.json("/api/avise-me", "POST", corpo, ip=ip())[0], 201)  # duplicado ignorado
        self.assertEqual(self.json("/api/avise-me", "POST", {**corpo, "aceite": False}, ip=ip())[0], 422)
        self.assertEqual(self.json("/api/avise-me", "POST", {**corpo, "slug": "nao-existe"}, ip=ip())[0], 404)
        produto = self.admin("/api/admin/produtos/mini-projetor-portatil")[1]
        self.assertEqual(produto["avise_me_total"], 1)
        self.assertNotIn("avise_me_total", self.json("/api/produtos/mini-projetor-portatil")[1])
        self.admin("/api/admin/produtos/mini-projetor-portatil", "PATCH", {"estoque": 4})
        avisos = [a for a in self.admin("/api/admin/avise-me?status=pronto")[1] if a["email"] == "avise@example.com"]
        self.assertEqual(len(avisos), 1)
        self.assertEqual(avisos[0]["produto"]["slug"], "mini-projetor-portatil")
        status, a = self.admin(f"/api/admin/avise-me/{avisos[0]['id']}", "PATCH", {"status": "avisado"})
        self.assertEqual((status, a["status"]), (200, "avisado"))
        endereco = ip()
        for _ in range(10):
            self.json("/api/avise-me", "POST", corpo, ip=endereco)
        self.assertEqual(self.json("/api/avise-me", "POST", corpo, ip=endereco)[0], 429)

    def test_carrinho_abandonado(self):
        itens = [{"slug": "fita-led-rgb-5m", "quantidade": 1}]
        self.assertEqual(self.json("/api/carrinhos", "POST", {"whatsapp": "92988887777", "itens": itens}, ip=ip())[0], 422)
        status, c = self.json("/api/carrinhos", "POST", {"whatsapp": "(92) 98888-7777", "nome": "Caio", "itens": itens,
                                                         "aceite_whatsapp": True}, ip=ip())
        self.assertEqual(status, 201)
        token = c["id"]
        status, publico = self.json(f"/api/carrinhos/{token}")
        self.assertEqual(publico, {"itens": [{"slug": "fita-led-rgb-5m", "variacao": None, "quantidade": 1}]})
        self.assertNotIn("whatsapp", json.dumps(publico))
        self.assertEqual(self.json(f"/api/carrinhos/{token}", "PUT",
                                   {"itens": [{"slug": "fita-led-rgb-5m", "quantidade": 2}]})[0], 200)
        self.assertEqual(self.json("/api/carrinhos/" + "a" * 22)[0], 404)
        self.sql("UPDATE carrinhos SET atualizado_em = ? WHERE token = ?", (horario.agora_db(hours=-3), token))
        lista = self.admin("/api/admin/carrinhos?status=abandonado")[1]
        c = next(x for x in lista if x["id"] == token)
        self.assertEqual(c["itens"][0]["quantidade"], 2)
        self.assertIn("wa.me/5592988887777", c["whatsapp_link"])
        self.assertEqual(self.admin(f"/api/admin/carrinhos/{token}", "PATCH", {"lembrete_enviado": True})[1]
                         ["lembrete_enviado"], True)
        self.pedido(carrinho=token, telefone="(92) 98888-7777")
        self.assertNotIn(token, [x["id"] for x in self.admin("/api/admin/carrinhos")[1]])
        self.assertIn(token, [x["id"] for x in self.admin("/api/admin/carrinhos?status=convertido")[1]])


class TestSeparacao(Rodada3):
    def test_separacao_e_separados(self):
        codigo = self.pedido([{"slug": "luminaria-lua-3d", "quantidade": 2}])
        self.admin(f"/api/admin/pedidos/{codigo}", "PATCH", {"status": "pago"})
        status, r = self.admin("/api/admin/separacao?status=pago")
        self.assertEqual(status, 200)
        p = next(x for x in r["pedidos"] if x["codigo"] == codigo)
        self.assertEqual((p["destinatario"], p["cidade"], p["uf"]), (CLIENTE["nome"], "Manaus", "AM"))
        self.assertTrue(any(c["sku"] == "luminaria-lua-3d" and c["quantidade"] >= 2 for c in r["consolidado"]))
        self.assertIn("remetente", r)
        status, s = self.admin("/api/admin/pedidos/separados", "POST", {"codigos": [codigo]})
        self.assertEqual((status, s["separados"]), (200, [codigo]))
        self.assertEqual(self.admin("/api/admin/separacao?status=x")[0], 422)


class TestUsuariosPapeisE2fa(Rodada3):
    def test_token_continua_e_primeiro_usuario(self):
        status, eu = self.admin("/api/admin/eu")
        self.assertEqual(status, 200)
        self.assertEqual((eu["papel"], eu["via_token"]), ("dono", True))
        self.assertIn("primeiro_usuario", eu)
        self.assertEqual(self.admin("/api/admin/eu/2fa/iniciar", "POST", {})[0], 422)  # token não tem 2FA própria

    def test_login_logout_e_limites(self):
        self.criar_usuario("dona@tipiti.com.br", "dono")
        self.assertEqual(self.criar_usuario("op1@tipiti.com.br")["papel"], "operador")
        status, r = self.entrar("dona@tipiti.com.br", "errada-errada")
        self.assertEqual((status, r), (401, {"erro": "Login ou senha incorretos."}))
        self.assertEqual(self.entrar("ninguem@tipiti.com.br")[1], r)  # mesma resposta para login inexistente
        status, r = self.entrar("dona@tipiti.com.br")
        self.assertEqual(status, 200)
        self.assertEqual(r["usuario"], {"nome": "Dona", "papel": "dono"})
        sessao = r["sessao"]
        status, eu = self.com_sessao(sessao, "/api/admin/eu")
        self.assertEqual((eu["papel"], eu["via_token"], eu["totp_ativo"]), ("dono", False, False))
        self.assertEqual(self.com_sessao(sessao, "/api/admin/resumo")[0], 200)
        self.assertNotIn("senha_hash", json.dumps(self.admin("/api/admin/usuarios")[1]))
        self.assertEqual(self.com_sessao(sessao, "/api/admin/logout", "POST", {})[0], 200)
        self.assertEqual(self.com_sessao(sessao, "/api/admin/eu")[0], 401)
        # limite por login, mesmo trocando de IP
        for _ in range(10):
            self.entrar("op1@tipiti.com.br", "errada-errada")
        self.assertEqual(self.entrar("op1@tipiti.com.br")[0], 429)
        # e por IP
        endereco = ip()
        for i in range(10):
            self.entrar(f"x{i}@tipiti.com.br", endereco=endereco)
        self.assertEqual(self.entrar("dona@tipiti.com.br", endereco=endereco)[0], 429)
        historico = self.admin("/api/admin/historico")[1]["itens"]
        self.assertIn("login_falhou", [h["acao"] for h in historico])
        self.assertNotIn(SENHA, json.dumps(historico))

    def test_operador_sem_custo_nem_lucro(self):
        self.criar_usuario("op2@tipiti.com.br")
        self.pedido([{"slug": "power-bank-20000mah", "quantidade": 1}])
        sessao = self.entrar("op2@tipiti.com.br")[1]["sessao"]
        proibidas = [("POST", "/api/admin/calculadora"), ("GET", "/api/admin/cupons"), ("GET", "/api/admin/ajustes"),
                     ("PUT", "/api/admin/ajustes"), ("GET", "/api/admin/usuarios"), ("POST", "/api/admin/usuarios"),
                     ("GET", "/api/admin/privacidade"), ("GET", "/api/admin/emails"), ("GET", "/api/admin/historico"),
                     ("GET", "/api/admin/feeds"), ("GET", "/api/admin/revendedoras"), ("PATCH", "/api/admin/usuarios/1")]
        for metodo, caminho in proibidas:
            status, r = self.com_sessao(sessao, caminho, metodo, {} if metodo != "GET" else None)
            if caminho in ("/api/admin/feeds", "/api/admin/revendedoras"):
                self.assertIn(status, (403, 404), caminho)  # rotas da rodada 2 (podem não existir nesta base)
                continue
            self.assertEqual((status, r), (403, {"erro": "Sem permissão."}), caminho)
        permitidas = ["/api/admin/pedidos", "/api/admin/produtos", "/api/admin/produtos/power-bank-20000mah",
                      "/api/admin/resumo", "/api/admin/avise-me", "/api/admin/carrinhos", "/api/admin/separacao",
                      "/api/admin/avaliacoes", "/api/admin/eu"]
        for caminho in permitidas:
            status, r = self.com_sessao(sessao, caminho)
            self.assertEqual(status, 200, caminho)
            texto = json.dumps(r)
            for campo in CAMPOS_PROIBIDOS:
                self.assertNotIn(f'"{campo}', texto, (caminho, campo))
        # o dono continua vendo
        self.assertIn("lucro_centavos", self.admin("/api/admin/resumo")[1])
        self.assertIn("custo_centavos", self.admin("/api/admin/produtos/power-bank-20000mah")[1])
        # operador edita estoque, mas não o custo
        custo = self.admin("/api/admin/produtos/power-bank-20000mah")[1]["custo_centavos"]
        status, p = self.com_sessao(sessao, "/api/admin/produtos/power-bank-20000mah", "PATCH",
                                    {"estoque": 33, "custo_centavos": 1})
        self.assertEqual(status, 200)
        self.assertNotIn("custo_centavos", p)
        depois = self.admin("/api/admin/produtos/power-bank-20000mah")[1]
        self.assertEqual((depois["estoque"], depois["custo_centavos"]), (33, custo))
        # histórico registra quem fez
        itens = self.admin("/api/admin/historico?alvo=power-bank")[1]["itens"]
        self.assertEqual(itens[0]["usuario"]["nome"], "Op2")
        self.assertEqual(itens[0]["acao"], "produto")
        self.assertEqual(itens[0]["detalhes"], {"estoque": 33})

    def test_desativar_e_trocar_senha_derruba_sessoes(self):
        u = self.criar_usuario("op3@tipiti.com.br")
        s1 = self.entrar("op3@tipiti.com.br")[1]["sessao"]
        s2 = self.entrar("op3@tipiti.com.br")[1]["sessao"]
        self.assertEqual(self.com_sessao(s1, "/api/admin/eu/senha", "POST", {"atual": "errada-errada",
                                                                             "nova": "outra-senha-forte"})[0], 422)
        self.assertEqual(self.com_sessao(s1, "/api/admin/eu/senha", "POST", {"atual": SENHA, "nova": "curta"})[0], 422)
        self.assertEqual(self.com_sessao(s1, "/api/admin/eu/senha", "POST", {"atual": SENHA,
                                                                             "nova": "outra-senha-forte"})[0], 200)
        self.assertEqual(self.com_sessao(s1, "/api/admin/eu")[0], 200)
        self.assertEqual(self.com_sessao(s2, "/api/admin/eu")[0], 401)
        self.assertEqual(self.entrar("op3@tipiti.com.br")[0], 401)
        self.assertEqual(self.entrar("op3@tipiti.com.br", "outra-senha-forte")[0], 200)
        self.assertEqual(self.admin(f"/api/admin/usuarios/{u['id']}", "PATCH", {"ativo": False})[0], 200)
        self.assertEqual(self.com_sessao(s1, "/api/admin/eu")[0], 401)
        self.assertEqual(self.entrar("op3@tipiti.com.br", "outra-senha-forte")[0], 401)
        hist = self.admin("/api/admin/historico")[1]["itens"]
        self.assertNotIn("outra-senha-forte", json.dumps(hist))

    def test_2fa(self):
        self.criar_usuario("dois@tipiti.com.br", "dono")
        sessao = self.entrar("dois@tipiti.com.br")[1]["sessao"]
        outra = self.entrar("dois@tipiti.com.br")[1]["sessao"]
        status, r = self.com_sessao(sessao, "/api/admin/eu/2fa/iniciar", "POST", {})
        self.assertEqual(status, 200)
        segredo = r["segredo"]
        self.assertTrue(r["otpauth_url"].startswith("otpauth://totp/"))
        p0 = totp.passo_atual()
        self.assertEqual(self.com_sessao(sessao, "/api/admin/eu/2fa/confirmar", "POST", {"codigo": "000000"})[0]
                         if totp.codigo(segredo, p0) != "000000" else 422, 422)
        status, r = self.com_sessao(sessao, "/api/admin/eu/2fa/confirmar", "POST",
                                    {"codigo": totp.codigo(segredo, p0 - 1)})
        self.assertEqual((status, r), (200, {"totp_ativo": True}))
        self.assertEqual(self.com_sessao(outra, "/api/admin/eu")[0], 401)  # outras sessões caem
        self.assertNotIn(segredo, json.dumps(self.com_sessao(sessao, "/api/admin/eu")[1]))
        self.assertNotIn(segredo, json.dumps(self.admin("/api/admin/usuarios")[1]))
        self.assertEqual(self.com_sessao(sessao, "/api/admin/eu/2fa/iniciar", "POST", {})[0], 422)
        # login passa a pedir o código
        status, r = self.entrar("dois@tipiti.com.br")
        self.assertEqual(status, 401)
        self.assertIs(r["precisa_2fa"], True)
        self.assertEqual(self.entrar("dois@tipiti.com.br", "errada-errada", totp.codigo(segredo, p0))[1],
                         {"erro": "Login ou senha incorretos."})
        codigo = totp.codigo(segredo, p0)
        status, r = self.entrar("dois@tipiti.com.br", codigo=codigo)
        self.assertEqual(status, 200)
        status, r = self.entrar("dois@tipiti.com.br", codigo=codigo)  # o mesmo código não vale duas vezes
        self.assertEqual((status, r["precisa_2fa"]), (401, True))
        # desativar exige senha e um código ainda não usado
        self.assertEqual(self.com_sessao(sessao, "/api/admin/eu/2fa/desativar", "POST",
                                         {"senha": "errada-errada", "codigo": totp.codigo(segredo, p0 + 1)})[0], 422)
        self.assertEqual(self.com_sessao(sessao, "/api/admin/eu/2fa/desativar", "POST",
                                         {"senha": SENHA, "codigo": codigo})[0], 422)  # reuso
        self.assertEqual(self.sql("SELECT totp_segredo FROM usuarios WHERE login = 'dois@tipiti.com.br'")[0][0], segredo)
        status, r = self.com_sessao(sessao, "/api/admin/eu/2fa/desativar", "POST",
                                    {"senha": SENHA, "codigo": totp.codigo(segredo, p0 + 1)})
        self.assertEqual((status, r), (200, {"totp_ativo": False}))
        self.assertEqual(self.entrar("dois@tipiti.com.br")[0], 200)

    def test_token_errado_e_sessao_invalida_contam_no_limite(self):
        endereco = ip()
        for _ in range(10):
            self.assertEqual(self.com_sessao("s" * 43, "/api/admin/resumo", endereco=endereco)[0], 401)
        self.assertEqual(self.admin("/api/admin/resumo", ip=endereco)[0], 429)


class TestEmailsNoPainel(Rodada3):
    def test_lista_e_reenvio(self):
        self.pedido(email="fila@example.com")
        lista = self.admin("/api/admin/emails?status=pendente")[1]
        e = next(x for x in lista if x["para"] == "fila@example.com")
        self.assertEqual(set(e) >= {"id", "para", "assunto", "status", "tentativas", "erro", "criado_em",
                                    "enviado_em"}, True)
        self.assertEqual(self.admin(f"/api/admin/emails/{e['id']}/reenviar", "POST", {})[1]["status"], "pendente")
        self.assertEqual(self.admin("/api/admin/emails/999999/reenviar", "POST", {})[0], 404)
        self.assertEqual(self.admin("/api/admin/emails?status=x")[0], 422)
        self.assertGreaterEqual(self.admin("/api/admin/resumo")[1]["emails_pendentes"], 1)
