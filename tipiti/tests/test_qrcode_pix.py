"""QR Code (codificador próprio) e Pix copia e cola (BR Code)."""

import hashlib
import random
import re
import unittest

from loja import pix, qrcode

try:  # comparação opcional com uma biblioteca de referência (não é dependência da loja)
    import segno
    from segno import encoder as _segno_encoder
except ImportError:  # pragma: no cover — depende do ambiente
    segno = None


def impressao(matriz):
    return hashlib.sha256("\n".join("".join(map(str, linha)) for linha in matriz).encode()).hexdigest()


def exp(valor):
    """Expoente de α para um elemento de GF(256)."""
    return qrcode._LOG[valor]


class TestReedSolomon(unittest.TestCase):
    def test_polinomios_geradores(self):
        # ISO/IEC 18004, anexo A: expoentes de α nos coeficientes (o líder é α⁰)
        self.assertEqual([exp(c) for c in qrcode.polinomio_gerador(7)], [0, 87, 229, 146, 149, 238, 102, 21])
        self.assertEqual([exp(c) for c in qrcode.polinomio_gerador(10)],
                         [0, 251, 67, 46, 61, 118, 70, 64, 94, 32, 45])

    def test_bytes_de_correcao(self):
        # "HELLO WORLD" alfanumérico, versão 1-M (exemplo clássico): 16 bytes de dados -> 10 de correção
        dados = [32, 91, 11, 120, 209, 114, 220, 77, 67, 64, 236, 17, 236, 17, 236, 17]
        self.assertEqual(qrcode.reed_solomon(dados, 10), [196, 35, 39, 119, 235, 215, 231, 226, 93, 23])


class TestEstrutura(unittest.TestCase):
    def test_capacidades_em_bytes(self):
        # tabela 7 da norma (modo byte = codewords de dados − cabeçalho)
        self.assertEqual(qrcode.capacidade_bytes(1, "M"), 16)
        self.assertEqual(qrcode.capacidade_bytes(10, "M"), 216)
        self.assertEqual(qrcode.capacidade_bytes(40, "L"), 2956)
        self.assertEqual(qrcode.capacidade_bytes(40, "H"), 1276)
        self.assertEqual(qrcode.escolher_versao(14, "M"), 1)
        self.assertEqual(qrcode.escolher_versao(15, "M"), 2)
        self.assertEqual(qrcode.escolher_versao(213, "M"), 10)
        self.assertEqual(qrcode.escolher_versao(2953, "L"), 40)
        with self.assertRaises(ValueError):
            qrcode.escolher_versao(2954, "L")

    def test_alinhamento(self):
        self.assertEqual(qrcode.posicoes_alinhamento(1), [])
        self.assertEqual(qrcode.posicoes_alinhamento(2), [6, 18])
        self.assertEqual(qrcode.posicoes_alinhamento(7), [6, 22, 38])
        self.assertEqual(qrcode.posicoes_alinhamento(32), [6, 34, 60, 86, 112, 138])
        self.assertEqual(qrcode.posicoes_alinhamento(40), [6, 30, 58, 86, 114, 142, 170])

    def test_formato_e_versao(self):
        self.assertEqual(f"{qrcode._bits_formato('M', 0):015b}", "101010000010010")
        self.assertEqual(f"{qrcode._bits_formato('L', 4):015b}", "110011000101111")
        self.assertEqual(f"{qrcode._bits_formato('H', 7):015b}", "000100000111011")
        self.assertEqual(f"{qrcode._bits_versao(7):018b}", "000111110010010100")
        self.assertEqual(f"{qrcode._bits_versao(40):018b}", "101000110001101001")

    def test_matrizes_de_referencia(self):
        """Impressões das matrizes geradas pelo segno 1.6.6 (com a correção do enchimento descrita abaixo)."""
        payload = pix.copia_e_cola("+5592991234567", "TIPITI IMPORTADOS", "MANAUS", 12345, "TPTABCDEFGH2345")
        casos = [
            (b"HELLO", "M", 21, "1fff7fd781f0f59edd796e0f79b20d68de6ecef41b47571460c4bbfbac1afe97"),
            (b"https://tipiti.com.br/produto/power-bank-20000mah", "M", 33,
             "23b7375b8bc2e48649569e40e3d2acce1a5a9750739baa25290960b222a33803"),
            (payload.encode(), "M", 49, "83d95456d1063303e731b782cbbf778a7e027298a8a21877addf09841be7892b"),
            (bytes(range(256)) * 3, "Q", 125, "35a520e5896c7f80ae824930eefc780eebac4f0a9eb9128584c10bcce4ab3b6e"),
        ]
        for dados, nivel, lado, esperado in casos:
            with self.subTest(tamanho=len(dados)):
                matriz = qrcode.gerar(dados, nivel)
                self.assertEqual(len(matriz), lado)
                self.assertEqual(impressao(matriz), esperado)

    def test_padroes_fixos(self):
        m = qrcode.gerar("teste", "M")
        localizador = [[1, 1, 1, 1, 1, 1, 1], [1, 0, 0, 0, 0, 0, 1], [1, 0, 1, 1, 1, 0, 1], [1, 0, 1, 1, 1, 0, 1],
                       [1, 0, 1, 1, 1, 0, 1], [1, 0, 0, 0, 0, 0, 1], [1, 1, 1, 1, 1, 1, 1]]
        n = len(m)
        self.assertEqual([linha[:7] for linha in m[:7]], localizador)
        self.assertEqual([linha[n - 7:] for linha in m[:7]], localizador)
        self.assertEqual([linha[:7] for linha in m[n - 7:]], localizador)
        self.assertEqual(m[6][8:n - 8], [1, 0] * ((n - 16) // 2) + [1])  # sincronismo
        self.assertEqual(m[n - 8][8], 1)  # módulo escuro

    def test_svg(self):
        svg = qrcode.svg(qrcode.gerar("abc"), margem=4)
        self.assertIn('viewBox="0 0 29 29"', svg)  # 21 + 2 × 4
        self.assertIn('<rect width="29" height="29" fill="#fff"/>', svg)
        self.assertTrue(svg.startswith("<svg") and svg.endswith("</svg>"))
        self.assertIn("M4,4h7v1h-7z", svg)  # primeira linha do localizador, já deslocada pela margem

    @unittest.skipIf(segno is None, "segno não instalado (comparação opcional)")
    def test_igual_ao_segno(self):  # pragma: no cover — só roda onde o segno existe
        # segno 1.6.6 acrescenta 8 bits zero quando o fluxo já termina num limite de byte; a norma pede nenhum
        original = _segno_encoder.write_padding_bits
        _segno_encoder.write_padding_bits = lambda buff, version, length: buff.extend([0] * (-length % 8))
        self.addCleanup(setattr, _segno_encoder, "write_padding_bits", original)
        sorteio = random.Random(18004)
        for versao in range(1, 41):
            for nivel in "LMQH":
                cap = qrcode.capacidade_bytes(versao, nivel) - (3 if versao >= 10 else 2)
                dados = bytes(sorteio.randrange(256) for _ in range(sorteio.randint(max(1, cap // 2), cap)))
                ref = segno.make_qr(dados, error=nivel.lower(), version=versao, mode="byte", boost_error=False)
                self.assertEqual(qrcode.gerar(dados, nivel, versao), [list(r) for r in ref.matrix],
                                 f"versão {versao}-{nivel}")


class TestPix(unittest.TestCase):
    def test_crc16_ccitt_false(self):
        self.assertEqual(pix.crc16("123456789"), 0x29B1)

    def test_exemplo_do_manual_do_banco_central(self):
        esperado = ("00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-4266554400005204000053039865802BR"
                    "5913Fulano de Tal6008BRASILIA62070503***63041D3D")
        self.assertEqual(pix.copia_e_cola("123e4567-e12b-12d1-a456-426655440000", "Fulano de Tal", "BRASILIA"),
                         esperado)

    def test_payload_com_valor_e_txid(self):
        p = pix.copia_e_cola("+5592991234567", "TIPITI IMPORTADOS", "MANAUS", 12345, "TPTABCDEFGH2345")
        self.assertEqual(
            p, "00020126360014br.gov.bcb.pix0114+55929912345675204000053039865406123.455802BR"
               "5917TIPITI IMPORTADOS6006MANAUS62190515TPTABCDEFGH23456304" + f"{pix.crc16(p[:-4]):04X}")
        self.assertIn("5404" + "0.05", pix.copia_e_cola("a@b.co", "X", "Y", 5))
        self.assertIn("54071000.00", pix.copia_e_cola("a@b.co", "X", "Y", 100000))
        self.assertRegex(p[-4:], r"^[0-9A-F]{4}$")
        with self.assertRaises(ValueError):
            pix.copia_e_cola("a@b.co", "X", "Y", 0)

    def test_campos_tem_tamanho_correto(self):
        p = pix.copia_e_cola("maria.silva@exemplo.com.br", "MARIA", "SANTAREM", 999, "TPT2345")
        i, campos = 0, {}
        while i < len(p):
            id_, tam = p[i:i + 2], int(p[i + 2:i + 4])
            campos[id_] = p[i + 4:i + 4 + tam]
            i += 4 + tam
        self.assertEqual(list(campos), ["00", "26", "52", "53", "54", "58", "59", "60", "62", "63"])
        self.assertEqual(campos["26"], "0014br.gov.bcb.pix0126maria.silva@exemplo.com.br")
        self.assertEqual(campos["62"], "0507TPT2345")

    def test_normalizacao_de_nome_e_cidade(self):
        self.assertEqual(pix.normalizar_texto("  João Açaí & Cia. Ltda  ", 25), "JOAO ACAI CIA. LTDA")
        self.assertEqual(pix.normalizar_texto("Santarém", 15), "SANTAREM")
        self.assertEqual(len(pix.normalizar_texto("A" * 40, 25)), 25)
        self.assertEqual(pix.normalizar_texto("São Gabriel da Cachoeira", 15), "SAO GABRIEL DA")

    def test_chaves(self):
        casos = {
            "529.982.247-25": "52998224725",
            "(92) 99123-4567": "+5592991234567",
            "+55 92 99123-4567": "+5592991234567",
            "5592991234567": "+5592991234567",
            "559233334444": "+559233334444",
            "9233334444": "+559233334444",
            "+1 415 555 0100": "",
            "(92) 9912-345": "",
            "529.982.247-24": "",  # dígito verificador errado
            "52998224725": "",  # CPF válido que também tem cara de celular: não adivinha
            "11144477735": "11144477735",  # CPF válido, não é celular
            "92991234560": "+5592991234560",  # celular, não é CPF válido
            "12345678000195": "12345678000195",
            "12.345.678/0001-95": "12345678000195",
            "Loja@Tipiti.com.BR": "loja@tipiti.com.br",
            "123E4567-E12B-12D1-A456-426655440000": "123e4567-e12b-12d1-a456-426655440000",
            "": "", "abc": "", "123": "", "a" * 80 + "@x.com": "",
        }
        for entrada, esperado in casos.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(pix.normalizar_chave(entrada), esperado)

    def test_configurado_e_txid(self):
        self.assertIsNone(pix.configurado({"chave_pix": "a@b.co", "pix_nome": ""}))
        self.assertIsNone(pix.configurado({"chave_pix": "", "pix_nome": "LOJA"}))
        self.assertEqual(pix.configurado({"chave_pix": "a@b.co", "pix_nome": "Lojá", "pix_cidade": ""}),
                         {"chave": "a@b.co", "nome": "LOJA", "cidade": "MANAUS"})
        self.assertEqual(pix.txid_do_pedido("TPT-ABCD2345EFGH"), "TPTABCD2345EFGH")
        self.assertTrue(re.fullmatch(r"[A-Z0-9]{1,25}", pix.txid_do_pedido("x" * 40)))

    def test_qr_svg_do_pix(self):
        svg = pix.qr_svg(pix.copia_e_cola("a@b.co", "LOJA", "MANAUS", 1990, "TPT1"))
        self.assertIn('fill="#fff"', svg)
        self.assertIn("<path", svg)


if __name__ == "__main__":
    unittest.main()
