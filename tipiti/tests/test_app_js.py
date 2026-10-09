import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from loja import config, servidor


class TestAppJs(unittest.TestCase):
    """O app.js é montado no servidor a partir de static/js/partes; o resultado tem de ser um script válido."""

    def montar(self):
        nome, _, _, ler = servidor._localizar_estatico("js/app.js")
        self.assertEqual(nome, "app.js")
        return ler()

    def test_partes_em_ordem_e_use_strict_uma_vez(self):
        partes = sorted((config.STATIC_DIR / "js" / "partes").glob("*.js"))
        self.assertGreater(len(partes), 1)
        self.assertEqual(self.montar(), b"\n".join(p.read_bytes() for p in partes))
        self.assertIn(b'"use strict";', partes[0].read_bytes().splitlines()[:3])
        self.assertEqual(self.montar().count(b'"use strict"'), 1)
        self.assertFalse((config.STATIC_DIR / "js" / "app.js").exists())

    def test_nomes_globais_nao_se_repetem(self):
        # as partes dividem o mesmo escopo: uma função com o mesmo nome em duas partes substitui a outra sem aviso
        # (já aconteceu: o "Sair" do painel tomou o lugar do "Sair" da Minha conta)
        definicao = re.compile(r"^(?:async\s+)?function\s+(\w+)|^(?:const|let|var|class)\s+(\w+)")
        vistos = {}
        for parte in sorted((config.STATIC_DIR / "js" / "partes").glob("*.js")):
            for numero, linha in enumerate(parte.read_text(encoding="utf-8").splitlines(), 1):
                m = definicao.match(linha)
                if not m:
                    continue
                nome = m.group(1) or m.group(2)
                self.assertFalse(nome in vistos, f"{nome} definido em {vistos.get(nome)} e em {parte.name}:{numero}")
                vistos[nome] = f"{parte.name}:{numero}"

    @unittest.skipUnless(shutil.which("node"), "node não está instalado")
    def test_node_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            arquivo = Path(tmp) / "app.js"
            arquivo.write_bytes(self.montar())
            r = subprocess.run(["node", "--check", str(arquivo)], capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
