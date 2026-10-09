"""Rodada 2 pela API: Pix copia e cola + QR, app instalável (manifesto, sw.js, ícones), dados estruturados e
feeds de produtos, "Encomenda pra mim" e pré-venda."""

import base64
import csv
import io
import json
import re
import shutil
import struct
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

from loja import config, encomendas, horario, pix, prevenda, regras
from tests.test_regras import CLIENTE
from tests.test_servidor import Base

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
G = "{http://base.google.com/ns/1.0}"


def dimensoes_png(caminho):
    dados = Path(caminho).read_bytes()
    assert dados[:8] == b"\x89PNG\r\n\x1a\n" and dados[12:16] == b"IHDR"
    return struct.unpack(">II", dados[16:24])


def json_ld(html):
    blocos = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return [item for bloco in blocos for item in json.loads(bloco)]


def futuro(dias):
    return (horario.agora().astimezone(horario.FUSO_LOJA).date() + timedelta(days=dias)).isoformat()


class TestPixApi(Base):
    def pedido(self, pagamento="pix", ip="10.1.0.1"):
        status, p = self.json("/api/pedidos", "POST", {**CLIENTE, "pagamento": pagamento,
                                                       "itens": [{"slug": "power-bank-20000mah", "quantidade": 1}]},
                              ip=ip)
        self.assertEqual(status, 201)
        return p

    def configurar(self, **valores):
        status, a = self.admin("/api/admin/ajustes", "PUT", valores)
        self.assertEqual(status, 200, a)
        return a

    def test_ajustes_e_pix_ativo(self):
        self.assertFalse(self.json("/api/loja")[1]["pix_ativo"])
        a = self.configurar(chave_pix="", pix_nome="Tipiti Importações Ltda", pix_cidade="")
        self.assertEqual((a["pix_nome"], a["pix_cidade"]), ("TIPITI IMPORTACOES LTDA", "MANAUS"))
        self.assertFalse(self.json("/api/loja")[1]["pix_ativo"])  # falta a chave
        self.configurar(chave_pix="(92) 99123-4567")
        self.assertTrue(self.json("/api/loja")[1]["pix_ativo"])
        status, erro = self.admin("/api/admin/ajustes", "PUT", {"pix_nome": "N" * 26, "pix_cidade": "C" * 16})
        self.assertEqual(status, 422)
        self.assertEqual(set(erro["campos"]), {"pix_nome", "pix_cidade"})
        status, erro = self.admin("/api/admin/ajustes", "PUT", {"chave_pix": "52998224725"})  # CPF ou celular?
        self.assertEqual((status, list(erro["campos"])), (422, ["chave_pix"]))
        self.configurar(chave_pix="", pix_nome="")

    def test_copia_e_cola_e_qr_code(self):
        p = self.pedido()
        url = f"/api/pedidos/{p['codigo']}/pix"
        status, erro = self.json(url)
        self.assertEqual(status, 409)  # Pix da loja ainda não configurado
        self.assertIn("erro", erro)
        self.configurar(chave_pix="loja@tipiti.com.br", pix_nome="Tipiti", pix_cidade="Santarém")
        self.addCleanup(self.configurar, chave_pix="", pix_nome="")
        status, dados = self.json(url.lower())  # o código vale em minúsculas também
        self.assertEqual(status, 200)
        self.assertEqual(set(dados), {"copia_e_cola", "valor_centavos", "qr_svg"})
        self.assertEqual(dados["valor_centavos"], p["total_centavos"])
        self.assertEqual(dados["qr_svg"], f"/api/pedidos/{p['codigo']}/pix.svg")
        cc = dados["copia_e_cola"]
        valor = f"{p['total_centavos'] // 100}.{p['total_centavos'] % 100:02d}"
        self.assertIn(f"54{len(valor):02d}{valor}", cc)
        self.assertIn("0118loja@tipiti.com.br", cc)
        self.assertIn("5906TIPITI6008SANTAREM", cc)
        txid = p["codigo"].replace("-", "")
        self.assertIn(f"62{len(txid) + 4:02d}05{len(txid):02d}{txid}", cc)
        self.assertEqual(cc[-4:], f"{pix.crc16(cc[:-4]):04X}")

        status, corpo, h = self.chamar(dados["qr_svg"])
        self.assertEqual(status, 200)
        self.assertTrue(h["Content-Type"].startswith("image/svg+xml"))
        self.assertEqual(h["Cache-Control"], "no-store")
        self.assertTrue(corpo.startswith(b"<svg") and b'fill="#fff"' in corpo)

        # pago: não oferece mais o Pix
        self.admin(f"/api/admin/pedidos/{p['codigo']}", "PATCH", {"status": "pago"})
        self.assertEqual(self.json(url)[0], 409)
        self.assertEqual(self.chamar(dados["qr_svg"])[0], 409)

    def test_pedido_no_cartao_e_inexistente(self):
        self.configurar(chave_pix="loja@tipiti.com.br", pix_nome="Tipiti")
        self.addCleanup(self.configurar, chave_pix="", pix_nome="")
        p = self.pedido("cartao")
        self.assertEqual(self.json(f"/api/pedidos/{p['codigo']}/pix")[0], 409)
        for _ in range(30):
            self.assertEqual(self.chamar("/api/pedidos/TPT-NAOEXISTE22/pix", ip="10.1.0.9")[0], 404)
        self.assertEqual(self.chamar("/api/pedidos/TPT-NAOEXISTE22/pix.svg", ip="10.1.0.9")[0], 429)
        self.assertEqual(self.chamar(f"/api/pedidos/{p['codigo']}", ip="10.1.0.9")[0], 429)  # mesmo limite
        self.assertEqual(self.chamar(f"/api/pedidos/{p['codigo']}/pix", "POST", {})[0], 405)


class TestPwa(Base):
    def test_manifesto(self):
        status, corpo, h = self.chamar("/manifest.webmanifest")
        self.assertEqual(status, 200)
        self.assertTrue(h["Content-Type"].startswith("application/manifest+json"))
        m = json.loads(corpo)
        for chave, valor in {"name": "Tipiti", "short_name": "Tipiti", "start_url": "/?origem=app", "scope": "/",
                             "display": "standalone", "theme_color": "#1f5c45", "background_color": "#f6f5f0",
                             "lang": "pt-BR"}.items():
            self.assertEqual(m[chave], valor)
        tamanhos = {(i["sizes"], i["purpose"]): i["src"] for i in m["icons"]}
        self.assertEqual(set(tamanhos), {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")})
        for (tamanho, _), src in tamanhos.items():
            status, png, hp = self.chamar(src)
            self.assertEqual((status, hp["Content-Type"]), (200, "image/png"))
            lado = int(tamanho.split("x")[0])
            self.assertEqual(dimensoes_png(config.STATIC_DIR / src[len("/static/"):]), (lado, lado))

    def test_imagem_de_compartilhamento(self):
        self.assertEqual(self.chamar("/static/pwa/compartilhar.png")[0], 200)
        self.assertEqual(dimensoes_png(config.STATIC_DIR / "pwa" / "compartilhar.png"), (1200, 630))

    def test_service_worker(self):
        status, corpo, h = self.chamar("/sw.js", headers={"Accept-Encoding": "identity"})
        self.assertEqual(status, 200)
        self.assertTrue(h["Content-Type"].startswith("application/javascript"))
        self.assertEqual(h["Cache-Control"], "no-cache")
        self.assertEqual(h["Service-Worker-Allowed"], "/")
        sw = corpo.decode()
        html = self.chamar("/")[1].decode()
        app = re.search(r'src="(/static/js/app\.js\?v=[0-9a-f]{10})"', html).group(1)
        css = re.search(r'href="(/static/css/estilo\.css\?v=[0-9a-f]{10})"', html).group(1)
        self.assertIn(f'const APP_JS = "{app}";', sw)
        self.assertIn(f'const ESTILO_CSS = "{css}";', sw)
        self.assertRegex(sw, r'const VERSAO = "[0-9a-f]{12}";')
        self.assertNotRegex(sw, r"\b__[A-Z_]+__\b")
        for prefixo in ("/api/admin", "/api/pedidos", "/api/revenda", "/api/encomendas", "/api/conta", "/api/carrinhos",
                        "/api/privacidade", "/api/avise-me"):
            self.assertIn(f'"{prefixo}"', sw)
        self.assertIn('event.data.tipo === "SKIP_WAITING"', sw)
        self.assertEqual(sw.count("skipWaiting()"), 1)  # só na mensagem
        self.assertEqual(self.chamar("/sw.js", headers={"If-None-Match": h["ETag"],
                                                        "Accept-Encoding": "identity"})[0], 304)
        node = shutil.which("node")
        if node is None:
            self.skipTest("node não instalado: sem checagem de sintaxe")
        with tempfile.TemporaryDirectory() as tmp:
            arquivo = Path(tmp) / "sw.js"
            arquivo.write_text(sw, encoding="utf-8")
            resultado = subprocess.run([node, "--check", str(arquivo)], capture_output=True, text=True, timeout=30)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)

    def test_versao_do_sw_muda_com_os_assets(self):
        from loja import pwa
        a = pwa.service_worker("/static/js/app.js?v=1", "/static/css/estilo.css?v=1")
        b = pwa.service_worker("/static/js/app.js?v=2", "/static/css/estilo.css?v=1")
        versao = re.compile(r'const VERSAO = "([0-9a-f]+)";')
        self.assertNotEqual(versao.search(a).group(1), versao.search(b).group(1))
        self.assertIn('"/static/js/app.js?v=2"', b)

    def test_rotas_da_spa_de_encomenda(self):
        for caminho in ("/encomenda", "/encomenda/", "/encomenda/ENC-ABCD2345"):
            self.assertEqual(self.chamar(caminho)[0], 200, caminho)


class TestDadosEstruturados(Base):
    def test_pagina_de_produto(self):
        status, pedido = self.json("/api/pedidos", "POST",
                                   {**CLIENTE, "itens": [{"slug": "power-bank-20000mah", "quantidade": 1}]})
        self.assertEqual(status, 201)
        self.sql("INSERT INTO avaliacoes (produto_id, pedido_id, nota, nome_exibicao, status) "
                 "SELECT p.id, pe.id, 4, 'Ana de Manaus', 'aprovada' FROM produtos p, pedidos pe "
                 "WHERE p.slug = 'power-bank-20000mah' AND pe.codigo = ?", (pedido["codigo"],))
        html = self.chamar("/produto/power-bank-20000mah")[1].decode()
        self.assertIn('<meta property="og:type" content="product">', html)
        self.assertIn(f'<meta property="og:image" content="{config.SITE_URL}/static/pwa/compartilhar.png">', html)
        produto, migalhas = json_ld(html)
        self.assertEqual(produto["@type"], "Product")
        self.assertEqual(produto["sku"], "power-bank-20000mah")
        self.assertEqual(produto["url"], f"{config.SITE_URL}/produto/power-bank-20000mah")
        self.assertEqual(produto["offers"]["price"], "119.90")
        self.assertEqual(produto["offers"]["priceCurrency"], "BRL")
        self.assertEqual(produto["offers"]["availability"], "https://schema.org/InStock")
        self.assertNotIn("priceValidUntil", produto["offers"])
        self.assertEqual(produto["aggregateRating"]["ratingValue"], 4.0)
        self.assertEqual(produto["aggregateRating"]["reviewCount"], 1)
        self.assertTrue(all(u.startswith("https://") for u in produto["image"]))
        self.assertEqual(migalhas["@type"], "BreadcrumbList")
        self.assertEqual([i["position"] for i in migalhas["itemListElement"]], [1, 2, 3])
        self.assertEqual(migalhas["itemListElement"][1]["item"], f"{config.SITE_URL}/categoria/celular-e-acessorios")

    def test_foto_vira_og_image_e_oferta_tem_validade(self):
        status, p = self.admin("/api/admin/produtos/luminaria-lua-3d/foto", "POST",
                               {"dados": base64.b64encode(PNG).decode()})
        self.assertEqual(status, 200)
        fim = (horario.agora() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.admin("/api/admin/produtos/luminaria-lua-3d", "PATCH", {"promo_pct": 10, "promo_fim": fim})
        html = self.chamar("/produto/luminaria-lua-3d")[1].decode()
        self.assertIn(f'<meta property="og:image" content="{config.SITE_URL}{p["imagem"]}">', html)
        produto = json_ld(html)[0]
        self.assertEqual(produto["image"], [f"{config.SITE_URL}{p['imagem']}"])
        self.assertEqual(produto["offers"]["price"], "44.91")  # 49,90 − 10%
        self.assertRegex(produto["offers"]["priceValidUntil"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertNotIn("aggregateRating", produto)

    def test_json_ld_nao_fecha_o_script(self):
        self.sql("UPDATE produtos SET nome = 'Lua </script><script>alert(1)</script> & cia' "
                 "WHERE slug = 'fita-led-rgb-5m'")
        html = self.chamar("/produto/fita-led-rgb-5m")[1].decode()
        bloco = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
        self.assertNotIn("<", bloco)
        self.assertNotIn("&", bloco)
        self.assertEqual(json.loads(bloco)[0]["name"], "Lua </script><script>alert(1)</script> & cia")
        self.assertNotIn("<script>alert(1)", html)

    def test_inicio_categoria_e_404(self):
        html = self.chamar("/")[1].decode()
        tipos = {d["@type"]: d for d in json_ld(html)}
        self.assertEqual(set(tipos), {"Organization", "WebSite"})
        acao = tipos["WebSite"]["potentialAction"]
        self.assertEqual(acao["target"]["urlTemplate"], f"{config.SITE_URL}/busca?q={{search_term_string}}")
        self.assertIn('<meta property="og:type" content="website">', html)
        self.assertEqual([d["@type"] for d in json_ld(self.chamar("/categoria/eletronicos")[1].decode())],
                         ["BreadcrumbList"])
        status, corpo, _ = self.chamar("/produto/nao-existe")
        self.assertEqual(status, 404)
        self.assertEqual(json_ld(corpo.decode()), [])
        self.assertEqual(json_ld(self.chamar("/carrinho")[1].decode()), [])


class TestFeeds(Base):
    def enviar_foto(self, slug):
        status, p = self.admin(f"/api/admin/produtos/{slug}/foto", "POST", {"dados": base64.b64encode(PNG).decode()})
        self.assertEqual(status, 200)
        return p

    def test_feeds(self):
        status, resumo = self.admin("/api/admin/feeds")
        self.assertEqual(status, 200)
        self.assertEqual(resumo["google"], f"{config.SITE_URL}/feeds/google.xml")
        self.assertEqual(resumo["meta"], f"{config.SITE_URL}/feeds/meta.csv")
        self.assertEqual(resumo["produtos_no_feed"], 0)  # catálogo de demonstração: nenhuma foto real
        self.assertIn({"nome": "Carregador portátil 20.000 mAh", "slug": "power-bank-20000mah"}, resumo["sem_foto"])
        self.assertEqual(self.chamar("/api/admin/feeds")[0], 401)

        self.sql("UPDATE produtos SET nome = 'Caixa & Som <IPX7>' WHERE slug = 'caixa-de-som-bluetooth-ipx7'")
        caixa = self.enviar_foto("caixa-de-som-bluetooth-ipx7")
        self.enviar_foto("caixa-de-som-bluetooth-ipx7")
        self.enviar_foto("cabo-usb-c-reforcado-2m")
        fim = (horario.agora() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.admin("/api/admin/produtos/cabo-usb-c-reforcado-2m", "PATCH",
                   {"promo_pct": 20, "promo_fim": fim, "prevenda_chegada": futuro(20)})
        self.enviar_foto("luminaria-lua-3d")
        self.admin("/api/admin/produtos/luminaria-lua-3d", "PATCH", {"ativo": False})

        status, corpo, h = self.chamar("/feeds/google.xml")
        self.assertEqual(status, 200)
        self.assertTrue(h["Content-Type"].startswith("application/xml"))
        canal = ET.fromstring(corpo).find("channel")
        itens = {i.find(f"{G}id").text: i for i in canal.findall("item")}
        self.assertEqual(set(itens), {"caixa-de-som-bluetooth-ipx7", "cabo-usb-c-reforcado-2m"})
        cx = itens["caixa-de-som-bluetooth-ipx7"]
        self.assertEqual(cx.find("title").text, "Caixa & Som <IPX7>")
        self.assertEqual(cx.find("link").text, f"{config.SITE_URL}/produto/caixa-de-som-bluetooth-ipx7")
        self.assertEqual(cx.find(f"{G}image_link").text, f"{config.SITE_URL}{caixa['imagem']}")
        self.assertEqual(len(cx.findall(f"{G}additional_image_link")), 1)
        self.assertEqual(cx.find(f"{G}price").text, "179.90 BRL")  # preço "de"
        self.assertEqual(cx.find(f"{G}sale_price").text, "149.90 BRL")
        self.assertIsNone(cx.find(f"{G}sale_price_effective_date"))
        self.assertEqual((cx.find(f"{G}availability").text, cx.find(f"{G}condition").text,
                          cx.find(f"{G}brand").text), ("in_stock", "new", "Tipiti"))
        cabo = itens["cabo-usb-c-reforcado-2m"]
        self.assertEqual(cabo.find(f"{G}price").text, "24.90 BRL")
        self.assertEqual(cabo.find(f"{G}sale_price").text, "19.92 BRL")
        self.assertRegex(cabo.find(f"{G}sale_price_effective_date").text,
                         r"^\d{4}-\d\d-\d\dT\d\d:\d\dZ/\d{4}-\d\d-\d\dT\d\d:\d\dZ$")
        self.assertEqual(cabo.find(f"{G}availability").text, "preorder")
        self.assertEqual(cabo.find(f"{G}availability_date").text, f"{futuro(20)}T00:00-04:00")

        status, corpo, h = self.chamar("/feeds/meta.csv")
        self.assertTrue(h["Content-Type"].startswith("text/csv"))
        linhas = list(csv.DictReader(io.StringIO(corpo.decode())))
        self.assertEqual(len(linhas), 2)
        cx = next(r for r in linhas if r["id"] == "caixa-de-som-bluetooth-ipx7")
        self.assertEqual((cx["availability"], cx["condition"], cx["price"]), ("in stock", "new", "179.90 BRL"))
        self.assertEqual(cx["title"], "Caixa & Som <IPX7>")
        self.assertTrue(cx["additional_image_link"].startswith(f"{config.SITE_URL}/fotos/"))
        self.assertEqual(next(r for r in linhas if r["id"] == "cabo-usb-c-reforcado-2m")["availability"], "preorder")

        self.assertEqual(self.admin("/api/admin/feeds")[1]["produtos_no_feed"], 2)


class TestEncomendas(Base):
    PEDIDO = {"nome": "Joana Lima", "whatsapp": "(92) 98888-7777", "cidade": "Parintins", "uf": "am",
              "link": "https://pt.aliexpress.com/item/1005.html?x=1&y=2", "descricao": "Cor azul", "quantidade": 2}

    def criar(self, ip="10.2.0.1", **extra):
        return self.json("/api/encomendas", "POST", {**self.PEDIDO, **extra}, ip=ip)

    def test_validacao(self):
        casos = [
            ({"link": "", "descricao": ""}, "descricao"),
            ({"link": "javascript:alert(1)"}, "link"),
            ({"link": "JAVASCRIPT://x.com/%0aalert(1)"}, "link"),
            ({"link": "ftp://x.com/a"}, "link"),
            ({"link": "https://"}, "link"),
            ({"link": "https://x.com/a b"}, "link"),
            ({"link": "https://x.com/" + "a" * 500}, "link"),
            ({"link": ["https://x.com"]}, "link"),
            ({"quantidade": 0}, "quantidade"),
            ({"quantidade": 51}, "quantidade"),
            ({"quantidade": True}, "quantidade"),
            ({"quantidade": 2.5}, "quantidade"),
            ({"whatsapp": "123"}, "whatsapp"),
            ({"whatsapp": ""}, "whatsapp"),
            ({"uf": "XX"}, "uf"),
            ({"nome": "Jo"}, "nome"),
            ({"descricao": "x" * 1001}, "descricao"),
        ]
        for extra, campo in casos:
            with self.subTest(extra=extra):
                status, erro = self.criar(ip="10.2.0.50", **extra)
                self.assertEqual(status, 422)
                self.assertIn(campo, erro["campos"])
        status, ok = self.criar(ip="10.2.0.50", link=None, descricao="Fone igual ao da foto")
        self.assertEqual(status, 201)  # erros de validação não gastam o limite de 5 por hora

    def test_fluxo_completo(self):
        status, criada = self.criar()
        self.assertEqual(status, 201)
        self.assertEqual(set(criada), {"codigo"})
        codigo = criada["codigo"]
        self.assertRegex(codigo, r"^ENC-[A-Z2-9]{8}$")

        url = f"/api/encomendas/{codigo}?whatsapp=5592988887777"
        status, e = self.json(url)
        self.assertEqual(status, 200)
        self.assertEqual(set(e), {"codigo", "status", "status_nome", "descricao", "link", "quantidade",
                                  "cotacao_centavos", "prazo_dias", "observacao", "criado_em"})
        self.assertEqual((e["status"], e["quantidade"], e["link"]), ("nova", 2, self.PEDIDO["link"]))
        self.assertRegex(e["criado_em"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertNotIn("nome", e)
        self.assertEqual(self.json(f"/api/encomendas/{codigo.lower()}?whatsapp=92988887777")[0], 200)
        self.assertEqual(self.json(f"/api/encomendas/{codigo}?whatsapp=92988887770")[0], 404)
        self.assertEqual(self.json(f"/api/encomendas/{codigo}")[0], 404)

        resposta = f"/api/encomendas/{codigo}/resposta"
        status, erro = self.json(resposta, "POST", {"whatsapp": "92988887777", "aceitar": True})
        self.assertEqual(status, 409)  # ainda não foi cotada
        self.assertEqual(self.admin("/api/admin/resumo")[1]["encomendas_novas"], 1)

        status, lista = self.admin("/api/admin/encomendas?status=nova")
        self.assertEqual([x["codigo"] for x in lista], [codigo])
        self.assertEqual((lista[0]["nome"], lista[0]["whatsapp"], lista[0]["cidade"], lista[0]["uf"]),
                         ("Joana Lima", "5592988887777", "Parintins", "AM"))
        self.assertEqual(self.admin("/api/admin/encomendas?status=cotada")[1], [])
        self.assertEqual(self.chamar("/api/admin/encomendas")[0], 401)

        admin = f"/api/admin/encomendas/{codigo}"
        self.assertEqual(self.admin(admin, "PATCH", {"status": "cotada"})[0], 422)  # sem valor e prazo
        self.assertEqual(self.admin(admin, "PATCH", {"status": "entregue"})[0], 422)
        self.assertEqual(self.admin(admin, "PATCH", {"cotacao_centavos": -1})[0], 422)
        status, e = self.admin(admin, "PATCH", {"cotacao_centavos": 25990})
        self.assertEqual((status, e["status"]), (200, "nova"))  # falta o prazo
        status, e = self.admin(admin, "PATCH", {"prazo_dias": 30, "observacao": "Frete incluso."})
        self.assertEqual((e["status"], e["cotacao_centavos"], e["prazo_dias"]), ("cotada", 25990, 30))
        self.assertEqual(self.admin("/api/admin/resumo")[1]["encomendas_novas"], 0)

        self.assertEqual(self.json(resposta, "POST", {"whatsapp": "92988887777", "aceitar": "sim"})[0], 422)
        self.assertEqual(self.json(resposta, "POST", {"whatsapp": "92900000000", "aceitar": True})[0], 404)
        status, e = self.json(resposta, "POST", {"whatsapp": "(92) 98888-7777", "aceitar": True})
        self.assertEqual((status, e["status"], e["observacao"]), (200, "aceita", "Frete incluso."))
        self.assertEqual(self.json(resposta, "POST", {"whatsapp": "92988887777", "aceitar": False})[0], 409)
        self.assertEqual(self.admin(admin, "PATCH", {"cotacao_centavos": 100})[0], 422)  # já aceita
        status, e = self.admin(admin, "PATCH", {"status": "comprada"})
        self.assertEqual((e["status"], e["proximos_status"]), ("comprada", ["entregue", "cancelada"]))
        self.assertEqual(self.admin("/api/admin/encomendas/ENC-NAOEXISTE", "PATCH", {"status": "nova"})[0], 404)

    def test_recusar_e_cotar_de_novo(self):
        codigo = self.criar(ip="10.2.0.7", link="")[1]["codigo"]
        self.admin(f"/api/admin/encomendas/{codigo}", "PATCH", {"cotacao_centavos": 5000, "prazo_dias": 20})
        status, e = self.json(f"/api/encomendas/{codigo}/resposta", "POST",
                              {"whatsapp": "92988887777", "aceitar": False})
        self.assertEqual(e["status"], "recusada")
        self.assertIsNone(e["link"])
        status, e = self.admin(f"/api/admin/encomendas/{codigo}", "PATCH", {"cotacao_centavos": 4500})
        self.assertEqual(e["status"], "cotada")

    def test_limite_de_criacao_e_de_consulta(self):
        for _ in range(5):
            self.assertEqual(self.criar(ip="10.2.0.99")[0], 201)
        status, erro = self.criar(ip="10.2.0.99")
        self.assertEqual((status, erro["erro"]), (429, "Muitas tentativas. Aguarde alguns minutos."))
        self.assertEqual(self.criar(ip="10.2.0.98")[0], 201)  # outro IP
        for _ in range(30):
            self.assertEqual(self.json("/api/encomendas/ENC-AAAAAAAA?whatsapp=92988887777", ip="10.2.0.97")[0], 404)
        self.assertEqual(self.json("/api/encomendas/ENC-AAAAAAAA?whatsapp=92988887777", ip="10.2.0.97")[0], 429)


class TestPrevendaApi(Base):
    def test_prevenda_no_produto_carrinho_e_pedido(self):
        slug = "garrafa-termica-display-led"
        url = f"/api/admin/produtos/{slug}"
        self.assertEqual(self.admin(url, "PATCH", {"prevenda_chegada": "2020-01-01"})[0], 422)
        self.assertEqual(self.admin(url, "PATCH", {"prevenda_chegada": "15/12/2030"})[0], 422)
        chegada = futuro(30)
        status, p = self.admin(url, "PATCH", {"prevenda_chegada": chegada, "estoque": 3})
        self.assertEqual(status, 200)
        self.assertEqual((p["prevenda"], p["prevenda_chegada"]), ({"chegada": chegada}, chegada))
        publico = self.json(f"/api/produtos/{slug}")[1]
        self.assertEqual(publico["prevenda"], {"chegada": chegada})
        self.assertEqual(publico["selos"][0], "prevenda")
        self.assertNotIn("prevenda_chegada", publico)
        self.assertIsNone(self.json("/api/produtos/luminaria-lua-3d")[1]["prevenda"])

        html = self.chamar(f"/produto/{slug}")[1].decode()
        oferta = json_ld(html)[0]["offers"]
        self.assertEqual((oferta["availability"], oferta["availabilityStarts"]),
                         ("https://schema.org/PreOrder", chegada))

        itens = [{"slug": slug, "quantidade": 2}, {"slug": "luminaria-lua-3d", "quantidade": 1}]
        status, cot = self.json("/api/carrinho/cotacao", "POST", {"itens": itens, "cep": "69005-000"})
        self.assertEqual(status, 200)
        linhas = {l["slug"]: l for l in cot["itens"]}
        self.assertEqual(linhas[slug]["prevenda_chegada"], chegada)
        self.assertIsNone(linhas["luminaria-lua-3d"]["prevenda_chegada"])
        envio = futuro(30 + config.PRAZO_MANUSEIO_DIAS)
        self.assertEqual(cot["previsao_envio"], envio)
        self.assertEqual(cot["frete"]["prazo_dias"], 2)  # Manaus: só o transporte, contado a partir do envio
        sem = self.json("/api/carrinho/cotacao", "POST", {"itens": itens[1:], "cep": "69005-000"})[1]
        self.assertIsNone(sem["previsao_envio"])
        self.assertEqual(sem["frete"]["prazo_dias"], 2 + config.PRAZO_MANUSEIO_DIAS)

        muitos = self.json("/api/carrinho/cotacao", "POST", {"itens": [{"slug": slug, "quantidade": 4}]})[1]
        self.assertEqual(muitos["itens"][0]["erro"], "Restam apenas 3 vaga(s).")

        status, pedido = self.json("/api/pedidos", "POST", {**CLIENTE, "itens": itens}, ip="10.3.0.1")
        self.assertEqual(status, 201)
        self.assertEqual((pedido["previsao_envio"], pedido["prazo_dias"]), (envio, 2))
        self.assertEqual(self.json(f"/api/produtos/{slug}")[1]["estoque"], 1)  # uma vaga sobrando
        admin = next(x for x in self.admin("/api/admin/pedidos")[1] if x["codigo"] == pedido["codigo"])
        self.assertEqual(admin["previsao_envio"], envio)
        self.admin(f"/api/admin/pedidos/{pedido['codigo']}", "PATCH", {"status": "cancelado"})
        self.assertEqual(self.json(f"/api/produtos/{slug}")[1]["estoque"], 3)  # vagas devolvidas

        # chegada que já passou: volta a ser produto normal; reenviar a mesma data não dá erro
        ontem = futuro(-1)
        self.sql(f"UPDATE produtos SET prevenda_chegada = '{ontem}' WHERE slug = '{slug}'")
        p = self.json(f"/api/produtos/{slug}")[1]
        self.assertIsNone(p["prevenda"])
        self.assertNotIn("prevenda", p["selos"])
        self.assertEqual(self.admin(url, "PATCH", {"prevenda_chegada": ontem, "nome": "Garrafa térmica"})[0], 200)
        status, p = self.admin(url, "PATCH", {"prevenda_chegada": None})
        self.assertEqual((status, p["prevenda_chegada"]), (200, None))


class TestRegrasR2(unittest.TestCase):
    def test_previsao_de_envio(self):
        self.assertIsNone(prevenda.previsao_envio([None, None]))
        self.assertEqual(prevenda.previsao_envio(["2030-01-10", None, "2030-02-01"]),
                         (date(2030, 2, 1) + timedelta(days=config.PRAZO_MANUSEIO_DIAS)).isoformat())

    def test_validar_chegada(self):
        self.assertIsNone(prevenda.validar({}, None))
        self.assertIsNone(prevenda.validar({"prevenda_chegada": None}, None))
        self.assertEqual(prevenda.validar({"prevenda_chegada": ""}, "2030-01-01"), (None,))
        self.assertEqual(prevenda.validar({"prevenda_chegada": futuro(1)}, None), (futuro(1),))
        for ruim in (futuro(0), futuro(800), "2030-02-30", "2030-1-5", 20300105, "2030-01-05T00:00:00Z"):
            with self.subTest(valor=ruim), self.assertRaises(regras.ErroValidacao):
                prevenda.validar({"prevenda_chegada": ruim}, None)

    def test_links_de_encomenda(self):
        bons = ["https://pt.aliexpress.com/item/1.html", "http://shopee.com.br/p?i=1&j=2", "HTTPS://Exemplo.com"]
        ruins = ["javascript:alert(1)", "data:text/html,<b>", "//x.com", "https://", "https://x.com/<script>",
                 "https://x.com/\n", "mailto:a@b.co", "https://x.com/" + "a" * 500, None, 5]
        for link in bons:
            self.assertTrue(encomendas.link_valido(link), link)
        for link in ruins:
            self.assertFalse(encomendas.link_valido(link), link)


if __name__ == "__main__":
    unittest.main()
