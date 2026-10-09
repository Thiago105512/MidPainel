import base64
import gzip
import http.client
import json
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from loja import config, db, fotos
from loja.servidor import criar_servidor, resolver_token_admin
from tests.test_regras import CLIENTE

TOKEN = "token-de-teste-com-mais-de-24-caracteres"


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.servidor = criar_servidor("127.0.0.1", 0, Path(cls.tmp.name) / "teste.db", TOKEN, silencioso=True)
        cls.servidor.confiar_proxy = True  # cada teste usa um IP próprio em X-Forwarded-For
        cls.porta = cls.servidor.server_address[1]
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.tmp.cleanup()

    def chamar(self, caminho, metodo="GET", corpo=None, headers=None, ip="10.0.0.1"):
        conexao = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
        self.addCleanup(conexao.close)
        if isinstance(corpo, (dict, list)):
            corpo = json.dumps(corpo).encode()
        conexao.request(metodo, caminho, body=corpo, headers={"X-Forwarded-For": f"203.0.113.9, {ip}", **(headers or {})})
        resp = conexao.getresponse()
        return resp.status, resp.read(), resp.headers

    def json(self, *args, **kwargs):
        status, corpo, _ = self.chamar(*args, **kwargs)
        return status, json.loads(corpo)

    def admin(self, caminho, metodo="GET", corpo=None, ip="10.0.0.1"):
        return self.json(caminho, metodo, corpo, headers={"Authorization": f"Bearer {TOKEN}"}, ip=ip)

    def sql(self, comando, params=()):
        conn = db.conectar(self.servidor.db_path)
        try:
            return conn.execute(comando, params).fetchall()
        finally:
            conn.close()


class TestCabecalhosECache(Base):
    def test_cabecalhos_de_seguranca(self):
        for caminho in ("/", "/api/loja", "/static/css/estilo.css", "/nao-existe", "/api/nao-existe"):
            _, _, h = self.chamar(caminho)
            self.assertEqual(h["X-Frame-Options"], "DENY", caminho)
            self.assertEqual(h["Cross-Origin-Opener-Policy"], "same-origin")
            self.assertEqual(h["Permissions-Policy"], "camera=(), microphone=(), geolocation=(), payment=()")
            self.assertEqual(h["Strict-Transport-Security"], "max-age=31536000; includeSubDomains")
            self.assertIsNotNone(h["Content-Length"])

    def test_sem_hsts_fora_de_https(self):
        with mock.patch.object(config, "SITE_URL", "http://localhost:8000"):
            self.assertIsNone(self.chamar("/api/loja")[2]["Strict-Transport-Security"])

    def test_gzip(self):
        original = (config.STATIC_DIR / "js" / "app.js").read_bytes()
        status, corpo, h = self.chamar("/static/js/app.js", headers={"Accept-Encoding": "gzip, deflate"})
        self.assertEqual((status, h["Content-Encoding"], h["Vary"]), (200, "gzip", "Accept-Encoding"))
        self.assertEqual(gzip.decompress(corpo), original)
        self.assertEqual(int(h["Content-Length"]), len(corpo))
        self.assertEqual(self.chamar("/static/js/app.js", headers={"Accept-Encoding": "gzip"})[1], corpo)
        status, corpo, h = self.chamar("/static/js/app.js")
        self.assertIsNone(h["Content-Encoding"])
        self.assertEqual(corpo, original)
        self.assertIsNone(self.chamar("/static/js/app.js", headers={"Accept-Encoding": "gzip;q=0"})[2]["Content-Encoding"])
        _, corpo, h = self.chamar("/api/produtos", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(h["Content-Encoding"], "gzip")
        self.assertIsInstance(json.loads(gzip.decompress(corpo)), list)
        _, corpo, h = self.chamar("/sitemap.xml", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(h["Content-Encoding"], "gzip")
        self.assertIn(b"<urlset", gzip.decompress(corpo))
        _, corpo, h = self.chamar("/img/produto/power-bank-20000mah.svg", headers={"Accept-Encoding": "gzip"})
        self.assertLess(len(corpo), 1024)  # pequeno demais para valer a compressão
        self.assertIsNone(h["Content-Encoding"])
        self.assertIsNone(self.chamar("/api/loja/x", headers={"Accept-Encoding": "gzip"})[2]["Content-Encoding"])

    def test_etag_e_304(self):
        for caminho in ("/static/css/estilo.css", "/img/produto/power-bank-20000mah.svg"):
            for encoding in ("gzip", "identity"):
                status, _, h = self.chamar(caminho, headers={"Accept-Encoding": encoding})
                self.assertEqual(status, 200)
                etag = h["ETag"]
                status, corpo, h2 = self.chamar(caminho, headers={"Accept-Encoding": encoding, "If-None-Match": etag})
                self.assertEqual((status, corpo, h2["ETag"]), (304, b"", etag), caminho)
        self.assertEqual(self.chamar("/static/css/estilo.css", headers={"If-None-Match": '"outra"'})[0], 200)

    def test_cache_dos_assets_versionados(self):
        _, _, h = self.chamar("/static/js/app.js?v=abc")
        self.assertEqual(h["Cache-Control"], "public, max-age=31536000, immutable")
        _, _, h = self.chamar("/static/js/app.js")
        self.assertEqual(h["Cache-Control"], "public, max-age=300")

    def test_pagina_com_dados_iniciais_e_assets_versionados(self):
        self.sql("UPDATE categorias SET nome = 'Achados </script><b>&' WHERE slug = 'achadinhos'")
        self.addCleanup(self.sql, "UPDATE categorias SET nome = 'Achadinhos' WHERE slug = 'achadinhos'")
        status, corpo, _ = self.chamar("/")
        html = corpo.decode()
        self.assertEqual(status, 200)
        self.assertRegex(html, r'src="/static/js/app\.js\?v=[0-9a-f]{10}"')
        self.assertRegex(html, r'href="/static/css/estilo\.css\?v=[0-9a-f]{10}"')
        bruto = re.search(r'<script type="application/json" id="dados-iniciais">(.*?)</script>', html).group(1)
        self.assertNotIn("<", bruto)
        dados = json.loads(bruto)
        self.assertEqual(dados["loja"], self.json("/api/loja")[1])
        self.assertEqual(dados["categorias"], self.json("/api/categorias")[1])
        self.assertIn("Achados </script><b>&", [c["nome"] for c in dados["categorias"]])
        self.assertNotIn("__DADOS_INICIAIS__", html)

    def test_pagina_sem_marcador(self):
        original = (config.STATIC_DIR / "index.html").read_text(encoding="utf-8")
        sem = original.replace('  <script type="application/json" id="dados-iniciais">__DADOS_INICIAIS__</script>\n', "")
        with mock.patch("pathlib.Path.read_text", return_value=sem):
            self.assertEqual(self.chamar("/")[0], 200)

    def test_head_e_keep_alive(self):
        conexao = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
        self.addCleanup(conexao.close)
        for caminho in ("/", "/api/loja", "/static/css/estilo.css", "/api/nao-existe"):
            conexao.request("HEAD", caminho)
            resp = conexao.getresponse()
            self.assertEqual(resp.read(), b"")
            self.assertGreater(int(resp.headers["Content-Length"]), 0)
            self.assertEqual(resp.version, 11)
        conexao.request("GET", "/api/loja")  # mesma conexão
        self.assertEqual(json.loads(conexao.getresponse().read())["nome"], "Tipiti")

    def test_metodo_desconhecido_responde_json(self):
        status, corpo, h = self.chamar("/", metodo="BREW")
        self.assertEqual(status, 501)
        self.assertEqual(int(h["Content-Length"]), len(corpo))
        self.assertIn("erro", json.loads(corpo))

    def test_configuracao_do_servidor(self):
        from loja.servidor import TipitiHandler
        self.assertEqual((TipitiHandler.timeout, TipitiHandler.protocol_version), (15, "HTTP/1.1"))
        self.assertEqual((self.servidor.request_queue_size, self.servidor.daemon_threads), (128, True))
        # cada conexão encerrada devolve a vaga do semáforo
        for _ in range(3):
            conexao = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
            conexao.request("GET", "/api/loja")
            conexao.getresponse().read()
            conexao.close()
        obtidas = 0
        try:
            while obtidas < 64 and self.servidor._vagas.acquire(timeout=5):
                obtidas += 1
        finally:
            for _ in range(obtidas):
                self.servidor._vagas.release()
        self.assertEqual(obtidas, 64)

    def test_loja_tem_pix_e_prazo(self):
        loja = self.json("/api/loja")[1]
        self.assertEqual(loja["chave_pix"], "")
        self.assertEqual(loja["prazo_reserva_horas"], config.PRAZO_RESERVA_HORAS)


class TestEntradasInvalidas(Base):
    def corpo_bruto(self, conteudo_tamanho, corpo=b""):
        conexao = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
        self.addCleanup(conexao.close)
        conexao.putrequest("POST", "/api/carrinho/cotacao")
        conexao.putheader("Content-Length", conteudo_tamanho)
        conexao.endheaders(corpo)
        resp = conexao.getresponse()
        return resp.status, resp.read(), resp.headers

    def test_content_length_invalido(self):
        for tamanho, esperado in (("-1", 400), ("abc", 400), ("99999999", 413)):
            status, corpo, h = self.corpo_bruto(tamanho)
            self.assertEqual(status, esperado, tamanho)
            self.assertEqual(h["Connection"], "close")
            self.assertIn("erro", json.loads(corpo))

    def test_corpo_em_partes_e_recusado(self):
        conexao = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
        self.addCleanup(conexao.close)
        conexao.request("POST", "/api/carrinho/cotacao", body=iter([b'{"itens": []}']),
                        headers={"Transfer-Encoding": "chunked"})
        resp = conexao.getresponse()
        self.assertEqual((resp.status, resp.headers["Connection"]), (411, "close"))
        resp.read()

    def test_json_com_nan_ou_inteiro_gigante(self):
        for bruto in (b'{"itens": NaN}', b'{"x": Infinity}', b'{"x": ' + b"9" * 5000 + b"}", b"[" * 20000):
            status, _, _ = self.chamar("/api/carrinho/cotacao", "POST", bruto)
            self.assertEqual(status, 400, bruto[:20])

    def test_quantidade_infinita(self):
        status, _, _ = self.chamar("/api/carrinho/cotacao", "POST", b'{"itens": [{"slug": "a", "quantidade": 1e400}]}')
        self.assertEqual(status, 422)

    def test_limite_e_offset(self):
        self.assertEqual(self.chamar("/api/produtos?limite=abc")[0], 400)
        self.assertEqual(self.chamar("/api/produtos?offset=-1")[0], 400)
        self.assertEqual(self.chamar("/api/produtos?offset=99999999999999999999")[0], 400)
        self.assertEqual(len(self.json("/api/produtos?limite=100000")[1]), min(100, len(self.json("/api/produtos")[1])))
        todos = self.json("/api/produtos?ordem=nome")[1]
        pagina = self.json("/api/produtos?ordem=nome&limite=3&offset=3")[1]
        self.assertEqual([p["slug"] for p in pagina], [p["slug"] for p in todos[3:6]])
        self.assertNotIn("descricao", todos[0])
        self.assertIn("cor", todos[0])
        self.assertIn("descricao", self.json(f"/api/produtos/{todos[0]['slug']}")[1])

    def test_id_de_foto_gigante(self):
        status, _ = self.admin("/api/admin/produtos/power-bank-20000mah/fotos/" + "9" * 30, "DELETE")
        self.assertEqual(status, 404)

    def test_svg_de_produto_inativo(self):
        self.admin("/api/admin/produtos/fita-led-rgb-5m", "PATCH", {"ativo": False})
        self.addCleanup(self.admin, "/api/admin/produtos/fita-led-rgb-5m", "PATCH", {"ativo": True})
        self.assertEqual(self.chamar("/img/produto/fita-led-rgb-5m.svg")[0], 404)


class TestLimitesDeTaxa(Base):
    def test_criacao_de_pedidos(self):
        pedido = {**CLIENTE, "itens": [{"slug": "cabo-usb-c-reforcado-2m", "quantidade": 1}]}
        for _ in range(10):
            self.assertEqual(self.chamar("/api/pedidos", "POST", pedido, ip="10.1.0.1")[0], 201)
        status, corpo = self.json("/api/pedidos", "POST", pedido, ip="10.1.0.1")
        self.assertEqual((status, corpo), (429, {"erro": "Muitas tentativas. Aguarde alguns minutos."}))
        self.assertEqual(self.chamar("/api/pedidos", "POST", pedido, ip="10.1.0.2")[0], 201)

    def test_token_errado(self):
        errado = {"Authorization": "Bearer errado"}
        for _ in range(10):
            self.assertEqual(self.chamar("/api/admin/resumo", headers=errado, ip="10.2.0.1")[0], 401)
        self.assertEqual(self.admin("/api/admin/resumo", ip="10.2.0.1")[0], 429)  # nem o token certo passa
        self.assertEqual(self.admin("/api/admin/resumo", ip="10.2.0.2")[0], 200)
        # sem token nenhum não conta como tentativa
        for _ in range(15):
            self.assertEqual(self.chamar("/api/admin/resumo", ip="10.2.0.3")[0], 401)
        self.assertEqual(self.admin("/api/admin/resumo", ip="10.2.0.3")[0], 200)

    def test_consulta_de_pedido_inexistente(self):
        for _ in range(30):
            self.assertEqual(self.chamar("/api/pedidos/TPT-NAOEXISTE", ip="10.3.0.1")[0], 404)
        self.assertEqual(self.chamar("/api/pedidos/TPT-NAOEXISTE", ip="10.3.0.1")[0], 429)
        self.assertEqual(self.chamar("/api/pedidos/TPT-NAOEXISTE", ip="10.3.0.2")[0], 404)

    def test_ip_do_proxy_so_quando_configurado(self):
        self.servidor.confiar_proxy = False
        self.addCleanup(setattr, self.servidor, "confiar_proxy", True)
        for i in range(30):  # cada pedido "vem" de um IP diferente, mas o proxy não é confiável
            self.chamar("/api/pedidos/TPT-NAOEXISTE", ip=f"10.4.0.{i}")
        self.assertEqual(self.chamar("/api/pedidos/TPT-NAOEXISTE", ip="10.4.1.1")[0], 429)
        self.servidor.limites["consulta"]._eventos.clear()


class TestFotos(Base):
    PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    JPG = b"\xff\xd8\xff" + b"\x00" * 64

    def enviar(self, slug, **campos):
        corpo = {k: base64.b64encode(v).decode() for k, v in campos.items()}
        return self.admin(f"/api/admin/produtos/{slug}/foto", "POST", corpo)

    def test_foto_com_miniatura(self):
        status, p = self.enviar("luminaria-lua-3d", dados=self.PNG, miniatura=self.JPG)
        self.assertEqual(status, 200)
        foto = p["fotos"][0]
        self.assertRegex(foto["miniatura"], r"^/fotos/luminaria-lua-3d-[0-9a-f]{8}\.jpg$")
        self.assertNotEqual(foto["miniatura"], foto["url"])
        self.assertEqual(p["imagem_miniatura"], foto["miniatura"])
        listado = next(x for x in self.json("/api/produtos")[1] if x["slug"] == "luminaria-lua-3d")
        self.assertEqual(listado["imagem_miniatura"], foto["miniatura"])

        status, corpo, h = self.chamar(foto["miniatura"])
        self.assertEqual((status, corpo), (200, self.JPG))
        self.assertEqual(h["Cache-Control"], "public, max-age=31536000, immutable")
        self.assertEqual(self.chamar(foto["miniatura"], headers={"If-None-Match": h["ETag"]})[0], 304)

        status, _ = self.admin(f"/api/admin/produtos/luminaria-lua-3d/fotos/{foto['id']}", "DELETE")
        self.assertEqual(status, 200)
        self.assertEqual(self.chamar(foto["url"])[0], 404)
        self.assertEqual(self.chamar(foto["miniatura"])[0], 404)

    def test_miniatura_invalida_ou_grande(self):
        self.assertEqual(self.enviar("projetor-galaxia-estrelas", dados=self.PNG, miniatura=b"<svg>")[0], 422)
        grande = self.JPG + b"\x00" * fotos.TAMANHO_MAX_MINIATURA
        self.assertEqual(self.enviar("projetor-galaxia-estrelas", dados=self.PNG, miniatura=grande)[0], 422)
        self.assertEqual(list(Path(self.servidor.fotos_dir).glob("projetor-galaxia-estrelas-*")), [])

    def test_sem_espaco_em_disco(self):
        with mock.patch.object(fotos, "ESPACO_LIVRE_MINIMO", 10 ** 30):
            status, corpo = self.enviar("projetor-galaxia-estrelas", dados=self.PNG)
        self.assertEqual(status, 422)
        self.assertIn("espaço", corpo["campos"]["foto"])

    def test_foto_antiga_sem_miniatura_usa_a_principal(self):
        self.sql("INSERT INTO fotos_produto (produto_id, arquivo, ordem) "
                 "SELECT id, 'mini-ventilador-portatil-de-mao-0000abcd.png', 0 FROM produtos "
                 "WHERE slug = 'mini-ventilador-portatil-de-mao'")
        self.sql("UPDATE produtos SET foto = 'mini-ventilador-portatil-de-mao-0000abcd.png' "
                 "WHERE slug = 'mini-ventilador-portatil-de-mao'")
        p = self.json("/api/produtos/mini-ventilador-portatil-de-mao")[1]
        self.assertEqual(p["fotos"][0]["miniatura"], p["fotos"][0]["url"])
        self.assertEqual(p["imagem_miniatura"], p["fotos"][0]["url"])


class TestTokenDoPainel(unittest.TestCase):
    def test_token_curto_impede_subir(self):
        with mock.patch.object(config, "ADMIN_TOKEN", "curto"):
            with self.assertRaises(SystemExit) as ctx:
                resolver_token_admin("127.0.0.1")
        self.assertIn("24", str(ctx.exception))

    def test_token_gerado_so_no_localhost(self):
        with mock.patch.object(config, "ADMIN_TOKEN", ""):
            token, gerado = resolver_token_admin("127.0.0.1")
            self.assertTrue(gerado)
            self.assertGreaterEqual(len(token), 24)
            with self.assertRaises(SystemExit):
                resolver_token_admin("0.0.0.0")

    def test_token_configurado(self):
        with mock.patch.object(config, "ADMIN_TOKEN", "x" * 24):
            self.assertEqual(resolver_token_admin("0.0.0.0"), ("x" * 24, False))


if __name__ == "__main__":
    unittest.main()
