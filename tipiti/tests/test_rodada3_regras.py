"""Rodada 3 — regras: dados da empresa e textos legais, LGPD, e-mail, avise-me, carrinhos, separação, usuários e 2FA."""

import json
import os
import smtplib
import unittest
from unittest import mock

from loja import (ajustes, avise_me, carrinhos, conta, emails, historico, horario, legal, privacidade, regras,
                  retencao, separacao, totp, usuarios)
from loja.validacao import ErroValidacao, NaoEncontrado, cnpj_valido
from tests.test_regras import CLIENTE, nova_conexao

SMTP_ENV = {"TIPITI_SMTP_HOST": "smtp.exemplo.com", "TIPITI_SMTP_PORTA": "587", "TIPITI_SMTP_USUARIO": "loja",
            "TIPITI_SMTP_SENHA": "segredo-smtp", "TIPITI_SMTP_REMETENTE": "Tipiti <contato@tipiti.com.br>",
            "TIPITI_SMTP_TLS": "starttls"}


class SMTPFalso:
    """Substitui smtplib.SMTP nos testes: nada sai para a rede."""
    enviados = []
    falhar = 0  # quantas próximas conexões devem falhar
    logins = []

    def __init__(self, host, porta, timeout=None, **kwargs):
        if SMTPFalso.falhar:
            SMTPFalso.falhar -= 1
            raise smtplib.SMTPConnectError(421, "servidor ocupado")
        self.host, self.porta = host, porta

    def starttls(self, context=None):
        self.tls = True

    def login(self, usuario, senha):
        SMTPFalso.logins.append((usuario, senha))

    def send_message(self, msg):
        SMTPFalso.enviados.append(msg)

    def quit(self):
        pass

    @classmethod
    def limpar(cls):
        cls.enviados, cls.falhar, cls.logins = [], 0, []


def conexao(teste):
    conn = nova_conexao()
    teste.addCleanup(conn.close)
    return conn


def pedido(conn, itens=None, **extra):
    itens = itens or [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}]
    return regras.criar_pedido(conn, {**CLIENTE, **extra, "itens": itens})


def empresa_completa(conn):
    ajustes.salvar(conn, {"empresa_razao_social": "Tipiti Comércio Ltda", "empresa_documento": "11.222.333/0001-81",
                          "empresa_endereco": "Av. Eduardo Ribeiro, 100, Centro", "empresa_cidade": "Manaus",
                          "empresa_uf": "am", "empresa_cep": "69005-000", "empresa_email": "contato@tipiti.com.br",
                          "empresa_telefone": "(92) 99123-4567"})


class TestDadosDaEmpresaETextos(unittest.TestCase):
    def setUp(self):
        self.conn = conexao(self)

    def test_cnpj(self):
        self.assertTrue(cnpj_valido("11.222.333/0001-81"))
        self.assertFalse(cnpj_valido("11.222.333/0001-82"))
        self.assertFalse(cnpj_valido("11111111111111"))

    def test_pendencias_e_empresa(self):
        a = ajustes.obter(self.conn)
        self.assertEqual(legal.pendencias(a), ["razão social", "documento (CNPJ ou CPF)", "endereço completo", "e-mail"])
        self.assertEqual(legal.empresa(a)["nome_fantasia"], "Tipiti")
        self.assertIsNone(legal.empresa(a)["razao_social"])
        empresa_completa(self.conn)
        a = ajustes.obter(self.conn)
        self.assertEqual(legal.pendencias(a), [])
        self.assertEqual(a["empresa_documento"], "11222333000181")
        self.assertEqual(a["empresa_uf"], "AM")
        self.assertEqual(legal.empresa(a), {
            "razao_social": "Tipiti Comércio Ltda", "nome_fantasia": "Tipiti",
            "documento_formatado": "11.222.333/0001-81",
            "endereco_completo": "Av. Eduardo Ribeiro, 100, Centro, Manaus - AM, CEP 69005-000",
            "email": "contato@tipiti.com.br", "telefone": "(92) 99123-4567"})
        self.assertEqual(legal.encarregado(a), "contato@tipiti.com.br")
        ajustes.salvar(self.conn, {"empresa_documento": "529.982.247-25"})  # CPF também vale
        self.assertEqual(legal.empresa(ajustes.obter(self.conn))["documento_formatado"], "529.982.247-25")

    def test_validacao_dos_ajustes_da_empresa(self):
        with self.assertRaises(ErroValidacao) as ctx:
            ajustes.salvar(self.conn, {"empresa_documento": "11.222.333/0001-82", "empresa_uf": "XX",
                                       "empresa_cep": "123", "empresa_email": "x@", "empresa_telefone": "12",
                                       "empresa_razao_social": "x" * 201})
        self.assertEqual(set(ctx.exception.campos), {"empresa_documento", "empresa_uf", "empresa_cep",
                                                     "empresa_email", "empresa_telefone", "empresa_razao_social"})
        ajustes.salvar(self.conn, {"empresa_razao_social": "  Tipiti\r\nLtda  "})
        self.assertEqual(ajustes.obter(self.conn)["empresa_razao_social"], "Tipiti Ltda")

    def test_textos_com_placeholder_e_preenchidos(self):
        for gerar in (legal.politica_privacidade, legal.termos_uso):
            doc = gerar(ajustes.obter(self.conn))
            self.assertEqual(set(doc), {"titulo", "atualizado_em", "secoes"})
            texto = json.dumps(doc, ensure_ascii=False)
            self.assertIn("[a preencher]", texto)
            empresa_completa(self.conn)
            texto = json.dumps(gerar(ajustes.obter(self.conn)), ensure_ascii=False)
            self.assertNotIn("[a preencher]", texto)
            self.assertIn("11.222.333/0001-81", texto)
            self.assertIn("Tipiti Comércio Ltda", texto)
            self.conn = conexao(self)
        politica = json.dumps(legal.politica_privacidade(ajustes.obter(self.conn)), ensure_ascii=False)
        for trecho in ("CPF", "IP", "obrigações legais", "Legítimo interesse", "Consentimento", "Transportadoras",
                       "art. 18", "Encarregado", "armazenamento local", "Contabilidade"):
            self.assertIn(trecho, politica)
        termos = json.dumps(legal.termos_uso(ajustes.obter(self.conn)), ensure_ascii=False)
        for trecho in ("7 dias", "art. 49", "90 dias", "Pré-venda", "Encomendas", "Cupons", "Revendedoras", "Foro",
                       "barco"):
            self.assertIn(trecho, termos)


class TestAceiteNoCheckout(unittest.TestCase):
    def setUp(self):
        self.conn = conexao(self)

    def test_aceite_obrigatorio_e_gravado(self):
        sem = {k: v for k, v in CLIENTE.items() if k != "aceite_termos"}
        for valor in (None, False, "true", 1):
            with self.assertRaises(ErroValidacao) as ctx:
                regras.criar_pedido(self.conn, {**sem, "aceite_termos": valor,
                                                "itens": [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}]})
            self.assertIn("aceite_termos", ctx.exception.campos)
        codigo = pedido(self.conn, aceite_whatsapp=True)
        row = self.conn.execute("SELECT * FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()
        self.assertIsNotNone(row["aceite_termos_em"])
        self.assertEqual((row["aceite_whatsapp"], row["aceite_whatsapp_em"] is not None), (1, True))
        codigo = pedido(self.conn)
        row = self.conn.execute("SELECT * FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()
        self.assertEqual((row["aceite_whatsapp"], row["aceite_whatsapp_em"]), (0, None))
        admin = next(p for p in regras.listar_pedidos(self.conn) if p["codigo"] == codigo)
        self.assertEqual(admin["aceites"]["whatsapp"], False)
        self.assertRegex(admin["aceites"]["termos_em"], r"Z$")


class TestEmails(unittest.TestCase):
    def setUp(self):
        self.conn = conexao(self)
        SMTPFalso.limpar()
        p1 = mock.patch.object(smtplib, "SMTP", SMTPFalso)
        p1.start()
        self.addCleanup(p1.stop)

    def com_smtp(self):
        p = mock.patch.dict(os.environ, SMTP_ENV)
        p.start()
        self.addCleanup(p.stop)

    def test_sem_smtp_fica_pendente(self):
        with mock.patch.dict(os.environ, {"TIPITI_SMTP_HOST": ""}):
            self.assertFalse(emails.configurado())
            emails.enfileirar(self.conn, "a@b.com.br", "Oi", "texto")
            self.assertEqual(emails.processar_fila(self.conn), 0)
        self.assertEqual(emails.listar(self.conn)[0]["status"], "pendente")
        self.assertEqual(emails.pendentes(self.conn), 1)
        self.assertEqual(SMTPFalso.enviados, [])

    def test_envio_com_texto_e_html(self):
        self.com_smtp()
        emails.enfileirar(self.conn, "Cliente@Example.com", "Pedido recebido", "Olá", emails.html_simples("T", ["<b>x"]))
        self.assertEqual(emails.processar_fila(self.conn), 1)
        msg = SMTPFalso.enviados[0]
        self.assertEqual((msg["To"], msg["Subject"]), ("cliente@example.com", "Pedido recebido"))
        self.assertEqual(msg["From"], "Tipiti <contato@tipiti.com.br>")
        self.assertEqual(SMTPFalso.logins, [("loja", "segredo-smtp")])
        tipos = [p.get_content_type() for p in msg.walk()]
        self.assertIn("text/plain", tipos)
        self.assertIn("text/html", tipos)
        html = msg.get_body(("html",)).get_content()
        self.assertIn("&lt;b&gt;x", html)  # conteúdo escapado
        e = emails.listar(self.conn)[0]
        self.assertEqual((e["status"], e["tentativas"]), ("enviado", 1))
        self.assertRegex(e["enviado_em"], r"Z$")
        self.assertNotIn("segredo-smtp", json.dumps(emails.listar(self.conn)))

    def test_falha_tenta_de_novo_com_espera_e_desiste(self):
        self.com_smtp()
        emails.enfileirar(self.conn, "a@b.com.br", "Oi", "texto")
        SMTPFalso.falhar = 1
        with self.assertLogs("tipiti.emails", level="WARNING"):
            self.assertEqual(emails.processar_fila(self.conn), 0)
        e = emails.listar(self.conn)[0]
        self.assertEqual((e["status"], e["tentativas"]), ("pendente", 1))
        self.assertIn("SMTPConnectError", e["erro"])
        self.assertEqual(emails.processar_fila(self.conn), 0)  # ainda esperando a próxima tentativa
        for _ in range(emails.MAX_TENTATIVAS - 1):
            self.conn.execute("UPDATE emails_saida SET proxima_tentativa = '2000-01-01 00:00:00'")
            SMTPFalso.falhar = 1
            with self.assertLogs("tipiti.emails", level="WARNING"):
                emails.processar_fila(self.conn)
        e = emails.listar(self.conn)[0]
        self.assertEqual((e["status"], e["tentativas"]), ("falhou", emails.MAX_TENTATIVAS))
        emails.reenviar(self.conn, e["id"])
        self.assertEqual(emails.processar_fila(self.conn), 1)
        self.assertEqual(emails.listar(self.conn, "enviado")[0]["id"], e["id"])
        with self.assertRaises(NaoEncontrado):
            emails.reenviar(self.conn, 999)
        with self.assertRaises(ErroValidacao):
            emails.listar(self.conn, "x")

    def test_sem_injecao_de_cabecalho(self):
        self.com_smtp()
        for ruim in ("a@b.com\r\nBcc: x@y.com", "a@b.com\nBcc:x@y.com", "a@b.com, c@d.com", "<a@b.com>", "x"):
            with self.assertRaises(ErroValidacao):
                emails.enfileirar(self.conn, ruim, "Oi", "t")
        emails.enfileirar(self.conn, "a@b.com.br", "Oi\r\nBcc: x@y.com", "t")
        emails.processar_fila(self.conn)
        msg = SMTPFalso.enviados[0]
        self.assertIsNone(msg["Bcc"])
        self.assertNotIn("\n", msg["Subject"])
        self.assertEqual(msg["Subject"], "Oi Bcc: x@y.com")

    def test_ssl_e_expiracao(self):
        self.com_smtp()
        with mock.patch.dict(os.environ, {"TIPITI_SMTP_TLS": "ssl"}), \
                mock.patch.object(smtplib, "SMTP_SSL", SMTPFalso) as _:
            emails.enfileirar(self.conn, "a@b.com.br", "Oi", "t")
            self.assertEqual(emails.processar_fila(self.conn), 1)
        emails.enfileirar(self.conn, "a@b.com.br", "Link", "t", validade_horas=0.5)
        self.conn.execute("UPDATE emails_saida SET expira_em = '2000-01-01 00:00:00' WHERE assunto = 'Link'")
        emails.processar_fila(self.conn)
        e = emails.listar(self.conn)[0]
        self.assertEqual((e["status"], e["erro"]), ("falhou", "Expirou antes do envio."))

    def test_thread_nao_morre_com_erro_e_envia(self):
        import tempfile
        from pathlib import Path
        from loja import db
        self.com_smtp()
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "t.db"
            conn = db.conectar(caminho)
            db.inicializar(conn)
            emails.enfileirar(conn, "a@b.com.br", "Oi", "t")
            ruim = mock.Mock(side_effect=RuntimeError("boom"))
            remetente = emails.Remetente(caminho, tarefas=(ruim,))
            with self.assertLogs("tipiti.emails", level="ERROR"):
                remetente.rodada()  # a tarefa falha, a fila segue
            self.assertEqual(emails.listar(conn)[0]["status"], "enviado")
            remetente = emails.Remetente(caminho)
            remetente.start()
            emails.enfileirar(conn, "c@d.com.br", "Dois", "t")
            for _ in range(100):
                if emails.listar(conn, "enviado") and len(emails.listar(conn, "enviado")) == 2:
                    break
                import time
                time.sleep(0.05)
            remetente.parar()
            remetente.join(5)
            self.assertEqual(len(emails.listar(conn, "enviado")), 2)
            conn.close()

    def test_emails_do_pedido(self):
        from loja import pix
        ajustes.salvar(self.conn, {"chave_pix": "pix@tipiti.com.br", "pix_nome": "Tipiti Comércio"})
        codigo = pedido(self.conn)
        e = self.conn.execute("SELECT * FROM emails_saida WHERE tipo = 'pedido'").fetchone()
        self.assertEqual(e["para"], CLIENTE["email"])
        self.assertIn(codigo, e["assunto"])
        for trecho in ("Total:", "Pagamento: Pix", "Pix copia e cola", f"/pedido/{codigo}", "/trocas",
                       "Prazo de entrega"):
            self.assertIn(trecho, e["texto"])
        copia = next(linha for linha in e["texto"].splitlines() if linha.startswith("000201"))
        self.assertEqual(copia[-4:], f"{pix.crc16(copia[:-4]):04X}")  # CRC do BR Code confere
        self.assertIn("pix@tipiti.com.br", copia)
        total = self.conn.execute("SELECT total_centavos FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()[0]
        self.assertIn(f"54{len(f'{total / 100:.2f}'):02d}{total / 100:.2f}", copia)
        regras.atualizar_status(self.conn, codigo, "pago")
        status = self.conn.execute("SELECT * FROM emails_saida WHERE tipo = 'evento'").fetchone()
        self.assertIn("Pagamento confirmado", status["assunto"])
        regras.atualizar_status(self.conn, codigo, "pago")  # sem mudança, sem e-mail
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM emails_saida WHERE tipo = 'evento'").fetchone()[0], 1)

    def test_email_do_pedido_sem_pix_configurado_nao_manda_chave_solta(self):
        ajustes.salvar(self.conn, {"chave_pix": "pix@tipiti.com.br"})  # sem o nome do recebedor
        pedido(self.conn)
        e = self.conn.execute("SELECT texto FROM emails_saida WHERE tipo = 'pedido'").fetchone()
        self.assertNotIn("pix@tipiti.com.br", e["texto"])
        self.assertNotIn("copia e cola", e["texto"])


class TestAviseMe(unittest.TestCase):
    def setUp(self):
        self.conn = conexao(self)

    def zerar(self, slug):
        self.conn.execute("UPDATE produtos SET estoque = 0 WHERE slug = ?", (slug,))

    def test_validacao_e_duplicado(self):
        with self.assertRaises(NaoEncontrado):
            avise_me.criar(self.conn, {"slug": "nao-existe", "email": "a@b.com", "aceite": True})
        with self.assertRaises(ErroValidacao) as ctx:
            avise_me.criar(self.conn, {"slug": "fita-led-rgb-5m", "aceite": True})
        self.assertIn("contato", ctx.exception.campos)
        with self.assertRaises(ErroValidacao) as ctx:
            avise_me.criar(self.conn, {"slug": "fita-led-rgb-5m", "email": "a@b.com"})
        self.assertIn("aceite", ctx.exception.campos)
        with self.assertRaises(ErroValidacao) as ctx:
            avise_me.criar(self.conn, {"slug": "fita-led-rgb-5m", "email": "a@b.com", "variacao": 99999, "aceite": True})
        self.assertIn("variacao", ctx.exception.campos)
        for _ in range(2):
            avise_me.criar(self.conn, {"slug": "fita-led-rgb-5m", "email": "A@b.com", "aceite": True})
        avise_me.criar(self.conn, {"slug": "fita-led-rgb-5m", "whatsapp": "(92) 99123-4567", "nome": "Ana",
                                   "aceite": True})
        lista = avise_me.listar_admin(self.conn)
        self.assertEqual(len(lista), 2)
        zap = next(a for a in lista if a["whatsapp"])
        self.assertEqual(zap["whatsapp"], "5592991234567")
        self.assertTrue(zap["whatsapp_link"].startswith("https://wa.me/5592991234567?text="))
        self.assertIn("fita-led-rgb-5m", zap["whatsapp_link"])

    def test_estoque_volta_e_avisos_ficam_prontos(self):
        self.zerar("fita-led-rgb-5m")
        avise_me.criar(self.conn, {"slug": "fita-led-rgb-5m", "email": "a@b.com", "aceite": True})
        avise_me.criar(self.conn, {"slug": "fita-led-rgb-5m", "whatsapp": "92991234567", "email": "c@d.com",
                                   "aceite": True})
        regras.atualizar_produto(self.conn, "fita-led-rgb-5m", {"estoque": 0})
        self.assertEqual({a["status"] for a in avise_me.listar_admin(self.conn)}, {"aguardando"})
        regras.atualizar_produto(self.conn, "fita-led-rgb-5m", {"estoque": 5})
        self.assertEqual({a["status"] for a in avise_me.listar_admin(self.conn)}, {"pronto"})
        id_produto = self.conn.execute("SELECT id FROM produtos WHERE slug = 'fita-led-rgb-5m'").fetchone()[0]
        self.assertEqual(avise_me.total_produto(self.conn, id_produto), 2)
        # e-mails só com SMTP configurado
        with mock.patch.dict(os.environ, {"TIPITI_SMTP_HOST": ""}):
            self.assertEqual(avise_me.enfileirar_avisos(self.conn), 0)
        with mock.patch.dict(os.environ, SMTP_ENV):
            self.assertEqual(avise_me.enfileirar_avisos(self.conn), 2)
            self.assertEqual(avise_me.enfileirar_avisos(self.conn), 0)  # não repete
        status = {a["email"]: a["status"] for a in avise_me.listar_admin(self.conn)}
        self.assertEqual(status, {"a@b.com": "avisado", "c@d.com": "pronto"})  # quem tem WhatsApp segue no painel
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM emails_saida WHERE tipo = 'avise_me'").fetchone()[0], 2)
        aviso = next(a for a in avise_me.listar_admin(self.conn) if a["status"] == "pronto")
        self.assertEqual(avise_me.atualizar_admin(self.conn, aviso["id"], {"status": "avisado"})["status"], "avisado")
        with self.assertRaises(ErroValidacao):
            avise_me.atualizar_admin(self.conn, aviso["id"], {"status": "x"})

    def test_variacao_e_cancelamento(self):
        produto = regras.obter_produto(self.conn, "fone-bluetooth-tws")
        var = produto["variacoes"][0]
        regras.salvar_variacoes(self.conn, "fone-bluetooth-tws",
                                [{**v, "estoque": 0 if v["id"] == var["id"] else v["estoque"]}
                                 for v in regras.obter_produto(self.conn, "fone-bluetooth-tws", admin=True)["variacoes"]])
        avise_me.criar(self.conn, {"slug": "fone-bluetooth-tws", "variacao": var["id"], "email": "a@b.com",
                                   "aceite": True})
        # um pedido de outra opção cancelado não mexe neste aviso
        self.assertEqual(avise_me.listar_admin(self.conn)[0]["status"], "aguardando")
        self.assertEqual(avise_me.listar_admin(self.conn)[0]["variacao"], var["nome"])
        variacoes = regras.obter_produto(self.conn, "fone-bluetooth-tws", admin=True)["variacoes"]
        regras.salvar_variacoes(self.conn, "fone-bluetooth-tws",
                                [{**v, "estoque": 3 if v["id"] == var["id"] else v["estoque"]} for v in variacoes])
        self.assertEqual(avise_me.listar_admin(self.conn)[0]["status"], "pronto")

    def test_cancelamento_devolve_estoque_e_avisa(self):
        self.conn.execute("UPDATE produtos SET estoque = 1 WHERE slug = 'fita-led-rgb-5m'")
        codigo = pedido(self.conn, [{"slug": "fita-led-rgb-5m", "quantidade": 1}])
        avise_me.criar(self.conn, {"slug": "fita-led-rgb-5m", "email": "a@b.com", "aceite": True})
        regras.atualizar_status(self.conn, codigo, "cancelado")
        self.assertEqual(avise_me.listar_admin(self.conn)[0]["status"], "pronto")


class TestCarrinhos(unittest.TestCase):
    def setUp(self):
        self.conn = conexao(self)
        self.itens = [{"slug": "fita-led-rgb-5m", "quantidade": 2}]

    def envelhecer(self, token, horas):
        self.conn.execute("UPDATE carrinhos SET atualizado_em = ? WHERE token = ?",
                          (horario.agora_db(hours=-horas), token))

    def test_criar_validar_restaurar(self):
        with self.assertRaises(ErroValidacao) as ctx:
            carrinhos.criar(self.conn, {"whatsapp": "123", "itens": [], "aceite_whatsapp": False})
        self.assertEqual(set(ctx.exception.campos), {"whatsapp", "itens", "aceite_whatsapp"})
        token = carrinhos.criar(self.conn, {"whatsapp": "(92) 99123-4567", "nome": "Ana", "itens": self.itens,
                                            "aceite_whatsapp": True})["id"]
        self.assertGreaterEqual(len(token), 20)
        self.assertEqual(carrinhos.obter_publico(self.conn, token),
                         {"itens": [{"slug": "fita-led-rgb-5m", "variacao": None, "quantidade": 2}]})
        carrinhos.atualizar(self.conn, token, {"itens": [{"slug": "fita-led-rgb-5m", "quantidade": 3}]})
        self.assertEqual(carrinhos.obter_publico(self.conn, token)["itens"][0]["quantidade"], 3)
        with self.assertRaises(NaoEncontrado):
            carrinhos.obter_publico(self.conn, "x" * 22)
        # novo carrinho do mesmo WhatsApp substitui o anterior
        novo = carrinhos.criar(self.conn, {"whatsapp": "92991234567", "itens": self.itens, "aceite_whatsapp": True})["id"]
        with self.assertRaises(NaoEncontrado):
            carrinhos.obter_publico(self.conn, token)
        self.assertNotEqual(novo, token)

    def test_abandonado_e_convertido(self):
        token = carrinhos.criar(self.conn, {"whatsapp": "92991234567", "nome": "Ana Souza", "itens": self.itens,
                                            "aceite_whatsapp": True})["id"]
        self.assertEqual(carrinhos.listar_admin(self.conn), [])  # menos de 1 h
        self.envelhecer(token, 2)
        lista = carrinhos.listar_admin(self.conn)
        self.assertEqual(len(lista), 1)
        c = lista[0]
        self.assertEqual((c["id"], c["nome"], c["whatsapp"], c["lembrete_enviado"]),
                         (token, "Ana Souza", "5592991234567", False))
        self.assertEqual(c["itens"], [{"nome": "Fita LED RGB 5 m com controle", "quantidade": 2}])
        self.assertGreater(c["total_centavos"], 0)
        self.assertIn(f"%3Fc%3D{token}", c["whatsapp_link"])
        self.assertTrue(carrinhos.marcar_lembrete(self.conn, token, {"lembrete_enviado": True})["lembrete_enviado"])
        self.assertTrue(carrinhos.listar_admin(self.conn)[0]["lembrete_enviado"])
        self.envelhecer(token, 24 * 8)  # fora da janela de 7 dias
        self.assertEqual(carrinhos.listar_admin(self.conn), [])
        self.envelhecer(token, 2)
        pedido(self.conn, telefone="(92) 99123-4567")  # mesmo WhatsApp
        self.assertEqual(carrinhos.listar_admin(self.conn), [])
        self.assertEqual(len(carrinhos.listar_admin(self.conn, "convertido")), 1)

    def test_convertido_pelo_token(self):
        token = carrinhos.criar(self.conn, {"whatsapp": "11987654321", "itens": self.itens,
                                            "aceite_whatsapp": True})["id"]
        pedido(self.conn, carrinho=token)
        row = self.conn.execute("SELECT status, pedido_id FROM carrinhos WHERE token = ?", (token,)).fetchone()
        self.assertEqual(row["status"], "convertido")
        self.assertIsNotNone(row["pedido_id"])
        with self.assertRaises(NaoEncontrado):
            carrinhos.atualizar(self.conn, token, {"itens": self.itens})

    def test_apagado_depois_de_30_dias(self):
        token = carrinhos.criar(self.conn, {"whatsapp": "92991234567", "itens": self.itens,
                                            "aceite_whatsapp": True})["id"]
        self.envelhecer(token, 24 * 31)
        with self.assertRaises(NaoEncontrado):
            carrinhos.obter_publico(self.conn, token)
        self.assertEqual(retencao.purgar(self.conn, forcar=True)["carrinhos"], 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM carrinhos").fetchone()[0], 0)
        self.assertIsNone(retencao.purgar(self.conn))  # só de tempos em tempos


class TestContaSemSenha(unittest.TestCase):
    def setUp(self):
        self.conn = conexao(self)

    def token_do_email(self):
        texto = self.conn.execute("SELECT texto FROM emails_saida WHERE tipo = 'conta' ORDER BY id DESC").fetchone()[0]
        return texto.split("/conta#")[1].split()[0]

    def test_link_unico_e_sessao(self):
        self.assertEqual(conta.solicitar_acesso(self.conn, "ninguem@example.com"), {"ok": True})
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM links_conta").fetchone()[0], 0)
        pedido(self.conn)
        self.assertEqual(conta.solicitar_acesso(self.conn, "MARIA@example.com"), {"ok": True})
        token = self.token_do_email()
        # só o hash fica no banco
        self.assertIsNone(self.conn.execute("SELECT 1 FROM links_conta WHERE token_hash = ?", (token,)).fetchone())
        sessao = conta.criar_sessao(self.conn, token)
        self.assertGreaterEqual(len(sessao["sessao"]), 40)
        with self.assertRaises(conta.SessaoInvalida):
            conta.criar_sessao(self.conn, token)  # uso único
        self.assertEqual(conta.email_da_sessao(self.conn, sessao["sessao"]), "maria@example.com")
        dados = conta.resumo(self.conn, "maria@example.com")
        self.assertEqual(dados["nome"], CLIENTE["nome"])
        self.assertEqual(len(dados["pedidos"]), 1)
        self.assertNotIn("cliente", dados["pedidos"][0])
        conta.encerrar_sessao(self.conn, sessao["sessao"])
        with self.assertRaises(conta.SessaoInvalida):
            conta.email_da_sessao(self.conn, sessao["sessao"])

    def test_link_expira(self):
        pedido(self.conn)
        conta.solicitar_acesso(self.conn, CLIENTE["email"])
        token = self.token_do_email()
        self.conn.execute("UPDATE links_conta SET expira_em = ?", (horario.agora_db(minutes=-1),))
        with self.assertRaises(conta.SessaoInvalida):
            conta.criar_sessao(self.conn, token)
        self.conn.execute("UPDATE links_conta SET expira_em = ?", (horario.agora_db(days=-2),))
        self.assertEqual(retencao.purgar(self.conn, forcar=True)["links_conta"], 1)

    def test_enderecos(self):
        with self.assertRaises(ErroValidacao):
            conta.salvar_endereco(self.conn, "a@b.com", {"cep": "1"})
        e = conta.salvar_endereco(self.conn, "a@b.com", {"apelido": "Casa", "cep": "69005-000", "endereco": "Rua A",
                                                         "numero": "1", "bairro": "Centro", "cidade": "Manaus",
                                                         "uf": "am"})
        self.assertEqual((e["cep"], e["uf"]), ("69005000", "AM"))
        with self.assertRaises(NaoEncontrado):
            conta.remover_endereco(self.conn, "outro@b.com", e["id"])  # de outra conta, não
        conta.remover_endereco(self.conn, "a@b.com", e["id"])
        self.assertEqual(conta.listar_enderecos(self.conn, "a@b.com"), [])


class TestPrivacidade(unittest.TestCase):
    def setUp(self):
        self.conn = conexao(self)

    def test_solicitacao_exportacao_e_anonimizacao(self):
        with self.assertRaises(ErroValidacao) as ctx:
            privacidade.criar_solicitacao(self.conn, {"tipo": "x", "email": "a", "cpf": "1"})
        self.assertEqual(set(ctx.exception.campos), {"tipo", "email", "cpf"})
        codigo = pedido(self.conn, aceite_whatsapp=True)
        avise_me.criar(self.conn, {"slug": "fita-led-rgb-5m", "email": CLIENTE["email"], "aceite": True})
        avise_me.criar(self.conn, {"slug": "fita-led-rgb-5m", "whatsapp": CLIENTE["telefone"], "aceite": True})
        carrinhos.criar(self.conn, {"whatsapp": CLIENTE["telefone"], "itens": [{"slug": "fita-led-rgb-5m"}],
                                    "aceite_whatsapp": True})
        conta.salvar_endereco(self.conn, CLIENTE["email"], {"cep": "69005000", "endereco": "Rua A", "numero": "1",
                                                            "bairro": "B", "cidade": "Manaus", "uf": "AM"})
        protocolo = privacidade.criar_solicitacao(self.conn, {"tipo": "exclusao", "email": CLIENTE["email"],
                                                              "cpf": CLIENTE["cpf"]})["protocolo"]
        self.assertRegex(protocolo, r"^LGPD-[A-Z2-9]{8}$")
        dados = privacidade.exportar(self.conn, protocolo)
        self.assertEqual([p["codigo"] for p in dados["pedidos"]], [codigo])
        self.assertEqual(dados["pedidos"][0]["cliente_cpf"], "52998224725")
        self.assertTrue(dados["pedidos"][0]["itens"])
        self.assertNotIn("custo_unit_centavos", dados["pedidos"][0]["itens"][0])
        self.assertEqual(len(dados["avise_me"]), 2)
        self.assertEqual(len(dados["carrinhos"]), 1)
        self.assertNotIn("token", dados["carrinhos"][0])
        self.assertEqual(len(dados["enderecos_salvos"]), 1)
        self.assertEqual([s["protocolo"] for s in dados["solicitacoes_lgpd"]], [protocolo])
        self.assertTrue(dados["emails_enviados"])

        with self.assertRaises(ErroValidacao):  # pedido aguardando pagamento ainda precisa dos dados
            privacidade.anonimizar(self.conn, protocolo)
        for status in ("pago", "enviado", "entregue"):
            regras.atualizar_status(self.conn, codigo, status)
        antes = self.conn.execute("SELECT * FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()
        r = privacidade.anonimizar(self.conn, protocolo)
        self.assertEqual(r["pedidos_anonimizados"], 1)
        p = self.conn.execute("SELECT * FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()
        self.assertEqual(p["cliente_nome"], "Titular anonimizado")
        self.assertNotIn("maria", p["cliente_email"])
        self.assertEqual((p["cliente_cpf"], p["cliente_telefone"], p["endereco"], p["numero"]), ("", "", "", ""))
        self.assertEqual(p["cep"], "69005000")
        for campo in ("total_centavos", "subtotal_centavos", "frete_centavos", "criado_em", "cidade", "uf", "status"):
            self.assertEqual(p[campo], antes[campo], campo)  # dados fiscais ficam
        self.assertTrue(self.conn.execute("SELECT COUNT(*) FROM itens_pedido WHERE pedido_id = ?", (p["id"],)).fetchone()[0])
        for tabela in ("avise_me", "carrinhos", "enderecos_conta"):
            self.assertEqual(self.conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0], 0, tabela)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM emails_saida WHERE para = ? OR texto LIKE ?",
                                           (CLIENTE["email"], "%Maria%")).fetchone()[0], 0)
        depois = privacidade.exportar(self.conn, protocolo)
        self.assertEqual(depois["pedidos"], [])

    def test_resposta_envia_email(self):
        p = privacidade.criar_solicitacao(self.conn, {"tipo": "copia", "email": "a@b.com", "cpf": CLIENTE["cpf"]})
        r = privacidade.atualizar(self.conn, p["protocolo"], {"status": "concluida", "resposta": "Segue a cópia."})
        self.assertEqual((r["status"], r["resposta"]), ("concluida", "Segue a cópia."))
        self.assertRegex(r["prazo_resposta"], r"^\d{4}-\d{2}-\d{2}$")
        e = self.conn.execute("SELECT * FROM emails_saida WHERE tipo = 'lgpd'").fetchone()
        self.assertEqual(e["para"], "a@b.com")
        self.assertIn("Segue a cópia.", e["texto"])
        with self.assertRaises(ErroValidacao):
            privacidade.atualizar(self.conn, p["protocolo"], {"status": "x"})
        with self.assertRaises(NaoEncontrado):
            privacidade.exportar(self.conn, "LGPD-AAAAAAAA")


class TestSeparacao(unittest.TestCase):
    def setUp(self):
        self.conn = conexao(self)

    def test_lista_consolidado_e_separados(self):
        empresa_completa(self.conn)
        a = pedido(self.conn, [{"slug": "fita-led-rgb-5m", "quantidade": 2}])
        b = pedido(self.conn, [{"slug": "fita-led-rgb-5m", "quantidade": 1},
                               {"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}])
        pedido(self.conn)  # não pago: fica fora
        for codigo in (a, b):
            regras.atualizar_status(self.conn, codigo, "pago")
        lista = separacao.listar(self.conn)
        self.assertEqual([p["codigo"] for p in lista["pedidos"]], [a, b])
        etiqueta = lista["pedidos"][0]
        for campo in ("destinatario", "endereco", "numero", "bairro", "cep", "cidade", "uf", "telefone", "zona", "itens"):
            self.assertIn(campo, etiqueta)
        self.assertEqual(etiqueta["cep"], "69005-000")
        self.assertIsNone(etiqueta["viagem"])
        fita = next(c for c in lista["consolidado"] if c["sku"] == "fita-led-rgb-5m")
        self.assertEqual(fita["quantidade"], 3)
        self.assertEqual(lista["remetente"]["nome"], "Tipiti Comércio Ltda")
        r = separacao.marcar_separados(self.conn, {"codigos": [a, "TPT-NAOEXISTE"]})
        self.assertEqual(r, {"separados": [a], "nao_encontrados": ["TPT-NAOEXISTE"]})
        self.assertIsNotNone(separacao.listar(self.conn)["pedidos"][0]["separado_em"])
        self.assertTrue(self.conn.execute("SELECT 1 FROM emails_saida WHERE tipo = 'evento'").fetchone())
        with self.assertRaises(ErroValidacao):
            separacao.marcar_separados(self.conn, {"codigos": []})
        with self.assertRaises(ErroValidacao):
            separacao.listar(self.conn, "x")

    def test_separado_vira_evento_do_rastreio_com_um_email(self):
        a = pedido(self.conn)
        antes = self.conn.execute("SELECT COUNT(*) FROM emails_saida WHERE tipo = 'evento'").fetchone()[0]
        separacao.marcar_separados(self.conn, {"codigos": [a]})
        eventos = regras.obter_pedido_publico(self.conn, a)["eventos"]
        self.assertEqual((eventos[0]["tipo"], eventos[0]["mensagem"]), ("separado", "Pedido separado e embalado."))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM emails_saida WHERE tipo = 'evento'").fetchone()[0],
                         antes + 1)
        self.assertIsNotNone(self.conn.execute("SELECT separado_em FROM pedidos WHERE codigo = ?", (a,)).fetchone()[0])


class TestUsuariosESenhas(unittest.TestCase):
    def setUp(self):
        self.conn = conexao(self)

    def test_hash_de_senha(self):
        h = usuarios.hash_senha("senha-muito-boa")
        algoritmo, iteracoes, sal, _ = h.split("$")
        self.assertEqual(algoritmo, "pbkdf2_sha256")
        self.assertGreaterEqual(int(iteracoes), 310_000)
        import base64
        self.assertEqual(len(base64.b64decode(sal)), 16)
        self.assertNotEqual(h, usuarios.hash_senha("senha-muito-boa"))  # sal aleatório
        self.assertTrue(usuarios.conferir_senha("senha-muito-boa", h))
        self.assertFalse(usuarios.conferir_senha("senha-muito-boA", h))
        self.assertFalse(usuarios.conferir_senha("x", "lixo"))

    def test_criar_validar_e_nao_devolver_hash(self):
        with self.assertRaises(ErroValidacao) as ctx:
            usuarios.criar(self.conn, {"nome": "A", "login": "x", "papel": "chefe", "senha": "curta"})
        self.assertEqual(set(ctx.exception.campos), {"nome", "login", "papel", "senha"})
        u = usuarios.criar(self.conn, {"nome": "Dona", "login": "Dona@Tipiti.com.br", "papel": "dono",
                                       "senha": "senha-muito-boa"})
        self.assertEqual(u["login"], "dona@tipiti.com.br")
        self.assertNotIn("senha_hash", json.dumps(usuarios.listar(self.conn)))
        with self.assertRaises(ErroValidacao):
            usuarios.criar(self.conn, {"nome": "Outra", "login": "dona@tipiti.com.br", "senha": "senha-muito-boa"})
        with self.assertRaises(ErroValidacao):  # último dono ativo não pode sair
            usuarios.atualizar(self.conn, u["id"], {"ativo": False})
        with self.assertRaises(ErroValidacao):
            usuarios.atualizar(self.conn, u["id"], {"papel": "operador"})

    def test_sessao_expira_e_cai_com_troca_de_senha(self):
        u = usuarios.criar(self.conn, {"nome": "Dona", "login": "dona@t.com", "papel": "dono", "senha": "senha-muito-boa"})
        s = usuarios.autenticar(self.conn, "dona@t.com", "senha-muito-boa")
        self.assertIsNone(self.conn.execute("SELECT 1 FROM sessoes_admin WHERE token_hash = ?", (s["sessao"],)).fetchone())
        self.assertEqual(usuarios.ator_da_sessao(self.conn, s["sessao"])["id"], u["id"])
        with self.assertRaises(usuarios.FalhaLogin):
            usuarios.autenticar(self.conn, "dona@t.com", "errada-errada")
        with self.assertRaises(usuarios.FalhaLogin):
            usuarios.autenticar(self.conn, "ninguem@t.com", "senha-muito-boa")
        # renovação deslizante
        self.conn.execute("UPDATE sessoes_admin SET expira_em = ?", (horario.agora_db(hours=1),))
        usuarios.ator_da_sessao(self.conn, s["sessao"])
        expira = self.conn.execute("SELECT expira_em FROM sessoes_admin").fetchone()[0]
        self.assertGreater(expira, horario.agora_db(hours=11))
        self.conn.execute("UPDATE sessoes_admin SET expira_em = ?", (horario.agora_db(minutes=-1),))
        self.assertIsNone(usuarios.ator_da_sessao(self.conn, s["sessao"]))
        s2 = usuarios.autenticar(self.conn, "dona@t.com", "senha-muito-boa")
        s3 = usuarios.autenticar(self.conn, "dona@t.com", "senha-muito-boa")
        ator = usuarios.ator_da_sessao(self.conn, s2["sessao"])
        usuarios.trocar_senha(self.conn, ator, "senha-muito-boa", "outra-senha-boa")
        self.assertIsNotNone(usuarios.ator_da_sessao(self.conn, s2["sessao"]))  # a sessão que trocou continua
        self.assertIsNone(usuarios.ator_da_sessao(self.conn, s3["sessao"]))
        usuarios.criar(self.conn, {"nome": "Op", "login": "op@t.com", "papel": "dono", "senha": "senha-muito-boa"})
        usuarios.atualizar(self.conn, u["id"], {"ativo": False})
        self.assertIsNone(usuarios.ator_da_sessao(self.conn, s2["sessao"]))

    def test_filtro_do_operador(self):
        dados = {"a": 1, "custo_centavos": 2, "itens": [{"custo_unit_centavos": 3, "nome": "x"}],
                 "lucro_centavos": 4, "pedidos_sem_custo": 1, "margem_pct": 5, "markup": 2, "comissao_centavos": 9,
                 "sub": {"lucro_total": 1, "ok": True}}
        self.assertEqual(usuarios.filtrar_para_operador(dados), {"a": 1, "itens": [{"nome": "x"}], "sub": {"ok": True}})


class TestTotp(unittest.TestCase):
    SEGREDO = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # "12345678901234567890" (vetores da RFC 6238)

    def test_vetores_rfc6238(self):
        for t, esperado in ((59, "287082"), (1111111109, "081804"), (1234567890, "005924"), (2000000000, "279037")):
            self.assertEqual(totp.codigo(self.SEGREDO, t // 30), esperado)

    def test_janela_e_reuso(self):
        agora = 1_700_000_000
        passo = agora // 30
        for delta in (-1, 0, 1):
            self.assertEqual(totp.verificar(self.SEGREDO, totp.codigo(self.SEGREDO, passo + delta), agora=agora),
                             passo + delta)
        for delta in (-2, 2):
            self.assertIsNone(totp.verificar(self.SEGREDO, totp.codigo(self.SEGREDO, passo + delta), agora=agora))
        codigo = totp.codigo(self.SEGREDO, passo)
        self.assertIsNone(totp.verificar(self.SEGREDO, codigo, ultimo_passo=passo, agora=agora))
        self.assertIsNone(totp.verificar(self.SEGREDO, "12345", agora=agora))
        self.assertIsNone(totp.verificar(self.SEGREDO, "abcdef", agora=agora))

    def test_segredo_e_url(self):
        s = totp.gerar_segredo()
        self.assertRegex(s, r"^[A-Z2-7]{32}$")
        url = totp.otpauth_url(s, "dona@tipiti.com.br")
        self.assertTrue(url.startswith("otpauth://totp/Tipiti:dona@tipiti.com.br?"))
        self.assertIn(f"secret={s}", url)
        self.assertIn("issuer=Tipiti", url)


class TestHistorico(unittest.TestCase):
    def test_registro_sem_segredos_e_paginacao(self):
        conn = conexao(self)
        ator = {"id": 7, "nome": "Op"}
        historico.registrar(conn, ator, "usuario", "/api/admin/usuarios/1",
                            {"nova_senha": "segredo123456", "nome": "X", "dados": "base64..."}, "10.0.0.1")
        for i in range(5):
            historico.registrar(conn, None, "status", f"/api/admin/pedidos/TPT-{i}", {"status": "pago"}, "")
        r = historico.listar(conn, usuario="7")
        self.assertEqual(r["total"], 1)
        self.assertEqual(r["itens"][0]["detalhes"], {"nova_senha": "***", "nome": "X", "dados": "***"})
        self.assertEqual(historico.listar(conn, usuario="token")["total"], 5)
        pagina = historico.listar(conn, alvo="pedidos", pagina=2, por_pagina=2)
        self.assertEqual((pagina["total"], len(pagina["itens"])), (5, 2))
        with self.assertRaises(ErroValidacao):
            historico.listar(conn, usuario="x'; drop")


if __name__ == "__main__":
    unittest.main()
