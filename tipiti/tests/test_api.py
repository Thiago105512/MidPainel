import base64
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from loja.servidor import criar_servidor
from tests.test_regras import CLIENTE

TOKEN = "token-de-teste"


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.servidor = criar_servidor("127.0.0.1", 0, Path(cls.tmp.name) / "teste.db", TOKEN, silencioso=True)
        cls.base = f"http://127.0.0.1:{cls.servidor.server_address[1]}"
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.tmp.cleanup()

    def chamar(self, caminho, metodo="GET", corpo=None, token=None):
        dados = json.dumps(corpo).encode() if corpo is not None else None
        req = Request(self.base + caminho, data=dados, method=metodo, headers={"Content-Type": "application/json"})
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urlopen(req) as resp:
                return resp.status, resp.read(), resp.headers
        except HTTPError as e:
            return e.code, e.read(), e.headers

    def json(self, *args, **kwargs):
        status, corpo, _ = self.chamar(*args, **kwargs)
        return status, json.loads(corpo)

    def test_catalogo(self):
        status, cats = self.json("/api/categorias")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(cats), 6)
        status, prods = self.json("/api/produtos?categoria=eletronicos")
        self.assertTrue(all(p["categoria"]["slug"] == "eletronicos" for p in prods))

    def test_pagina_de_produto_tem_titulo_proprio(self):
        status, corpo, headers = self.chamar("/produto/power-bank-20000mah")
        self.assertEqual(status, 200)
        self.assertIn("<title>Carregador portátil 20.000 mAh | Tipiti</title>", corpo.decode())
        self.assertIn("https://tipiti.com.br/produto/power-bank-20000mah", corpo.decode())
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])

    def test_404(self):
        self.assertEqual(self.chamar("/produto/nao-existe")[0], 404)
        self.assertEqual(self.chamar("/api/produtos/nao-existe")[0], 404)
        self.assertEqual(self.chamar("/static/../loja/config.py")[0], 404)

    def test_imagem_svg(self):
        status, corpo, headers = self.chamar("/img/produto/power-bank-20000mah.svg")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("image/svg+xml"))

    def test_sitemap_e_robots(self):
        status, corpo, _ = self.chamar("/sitemap.xml")
        self.assertIn(b"https://tipiti.com.br/produto/", corpo)
        self.assertIn(b"Sitemap: https://tipiti.com.br/sitemap.xml", self.chamar("/robots.txt")[1])

    def test_fluxo_de_compra_e_admin(self):
        status, cot = self.json("/api/carrinho/cotacao", "POST",
                                {"itens": [{"slug": "power-bank-20000mah", "quantidade": 2}], "cep": "69151-000"})
        self.assertEqual(status, 200)
        self.assertTrue(cot["frete"]["gratis"])  # 2 × R$ 119,90 > R$ 199 em Parintins
        self.assertNotIn("custo_unit_centavos", cot["itens"][0])

        status, pedido = self.json("/api/pedidos", "POST",
                                   {**CLIENTE, "cep": "69151-000", "cidade": "Parintins",
                                    "itens": [{"slug": "power-bank-20000mah", "quantidade": 2}]})
        self.assertEqual(status, 201)
        self.assertEqual(pedido["frete_centavos"], 0)
        self.assertEqual(pedido["destino"], "Parintins - AM")

        self.assertEqual(self.chamar("/api/admin/pedidos")[0], 401)
        self.assertEqual(self.chamar("/api/admin/pedidos", token="errado")[0], 401)
        status, lista = self.json("/api/admin/pedidos", token=TOKEN)
        self.assertEqual(status, 200)
        self.assertIn(pedido["codigo"], [p["codigo"] for p in lista])
        self.assertIsNotNone(next(p for p in lista if p["codigo"] == pedido["codigo"])["lucro_centavos"])
        self.assertNotIn("lucro_centavos", pedido)
        status, resumo = self.json("/api/admin/resumo", token=TOKEN)
        self.assertGreaterEqual(resumo["pedidos"], 1)

        status, atualizado = self.json(f"/api/admin/pedidos/{pedido['codigo']}", "PATCH", {"status": "pago"}, token=TOKEN)
        self.assertEqual(atualizado["status"], "pago")

    def test_cadastro_de_produto_com_foto(self):
        novo = {"nome": "Luminária de mesa dobrável", "categoria": "achadinhos", "preco_centavos": 5990, "estoque": 5}
        self.assertEqual(self.chamar("/api/admin/produtos", "POST", novo)[0], 401)
        status, produto = self.json("/api/admin/produtos", "POST", novo, token=TOKEN)
        self.assertEqual(status, 201)
        slug = produto["slug"]

        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        status, com_foto = self.json(f"/api/admin/produtos/{slug}/foto", "POST",
                                     {"dados": base64.b64encode(png).decode()}, token=TOKEN)
        self.assertEqual(status, 200)
        self.assertRegex(com_foto["imagem"], r"^/fotos/luminaria-de-mesa-dobravel-[0-9a-f]{8}\.png$")
        status, corpo, headers = self.chamar(com_foto["imagem"])
        self.assertEqual((status, corpo, headers["Content-Type"]), (200, png, "image/png"))

        # galeria: segunda foto vira capa, depois a primeira é removida do disco
        status, duas = self.json(f"/api/admin/produtos/{slug}/foto", "POST",
                                 {"dados": base64.b64encode(png).decode()}, token=TOKEN)
        self.assertEqual(len(duas["fotos"]), 2)
        primeira, segunda = duas["fotos"]
        status, capa = self.json(f"/api/admin/produtos/{slug}/fotos/{segunda['id']}/capa", "POST", {}, token=TOKEN)
        self.assertEqual(capa["imagem"], segunda["url"])
        status, restante = self.json(f"/api/admin/produtos/{slug}/fotos/{primeira['id']}", "DELETE", token=TOKEN)
        self.assertEqual([f["id"] for f in restante["fotos"]], [segunda["id"]])
        self.assertEqual(self.chamar(primeira["url"])[0], 404)
        status, publico = self.json(f"/api/produtos/{slug}")
        self.assertNotIn("custo_centavos", publico)

        falso = base64.b64encode(b"<svg onload=alert(1)>").decode()
        status, erro = self.json(f"/api/admin/produtos/{slug}/foto", "POST", {"dados": falso}, token=TOKEN)
        self.assertEqual(status, 422)
        self.assertEqual(self.chamar("/fotos/../teste.db")[0], 404)

    def test_ajustes_whatsapp_e_calculadora(self):
        status, a = self.json("/api/admin/ajustes", "PUT", {"whatsapp": "(92) 99123-4567"}, token=TOKEN)
        self.assertEqual(a["whatsapp"], "5592991234567")
        self.assertEqual(self.json("/api/loja")[1]["whatsapp"], "5592991234567")
        self.assertEqual(self.json("/api/admin/ajustes", "PUT", {"whatsapp": "123"}, token=TOKEN)[0], 422)
        status, calc = self.json("/api/admin/calculadora", "POST",
                                 {"moeda": "USD", "custo_unitario": "3.20", "cambio": "5.5", "quantidade": 100,
                                  "frete_lote": "800", "impostos_pct": "60", "embalagem_unidade": "1.5",
                                  "taxa_pagamento_pct": "5", "margem_pct": "35"}, token=TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(calc["custo"]["total_centavos"], 4246)
        self.assertEqual(calc["sugerido"]["preco_centavos"], 7090)
        self.assertEqual(self.chamar("/api/admin/calculadora", "POST", {}, token=None)[0], 401)

    def test_erros_de_entrada(self):
        status, corpo = self.json("/api/pedidos", "POST", {"itens": []})
        self.assertEqual(status, 422)
        self.assertIn("campos", corpo)
        status, _, _ = self.chamar("/api/frete?cep=123")
        self.assertEqual(status, 422)
        req = Request(self.base + "/api/pedidos", data=b"nao-e-json", method="POST")
        try:
            urlopen(req)
        except HTTPError as e:
            self.assertEqual(e.code, 400)


if __name__ == "__main__":
    unittest.main()
