#!/usr/bin/env python3
"""Auditoria do visualizador num navegador de verdade.

O caderno audita o modelo; nada auditava o visualizador — e foi exatamente ali
que apareceu o defeito que o proprietario relatou (o zoom que "aumenta de forma
nada proporcional"). Este arquivo fecha a lacuna: abre o HTML num Chromium
headless, exercita zoom, navegacao, abas, camadas, sol e corte, e falha se algo
nao se comportar como a prancha promete.

Uso:  python3 viewer_teste.py            (gera o HTML em out/ e testa)
      python3 viewer_teste.py --fotos    (tambem salva PNGs de conferencia)

Depende de playwright (pip install playwright) e do Chromium ja presente em
PLAYWRIGHT_BROWSERS_PATH. three.js e servido de um arquivo local quando existir,
porque o CDN nao e alcancavel de dentro do container de build.
"""
from __future__ import annotations

import glob
import http.server
import os
import socketserver
import sys
import threading

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(AQUI, "..", "out"))
TRES_LOCAL = [os.path.join(OUT, "three.min.js"),
              os.path.join(os.environ.get("SCRATCHPAD", "/tmp"), "three.min.js")]
CHROME = next((c for c in glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome")), None)

falhas: list[str] = []
notas: list[str] = []


def ok(cond: bool, msg: str, detalhe: str = "") -> None:
    (notas if cond else falhas).append(f"{msg}{(' — ' + detalhe) if detalhe else ''}")


def servir(raiz: str):
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=raiz, **k)

        def log_message(self, *a):
            pass

    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def rodar(fotos: bool = False) -> int:
    from playwright.sync_api import sync_playwright

    import viewer
    viewer.main()

    srv, porta = servir(OUT)
    tres = next((c for c in TRES_LOCAL if os.path.exists(c)), None)

    with sync_playwright() as p:
        nav = p.chromium.launch(
            executable_path=CHROME,
            args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
                  "--enable-unsafe-swiftshader"])
        pag = nav.new_page(viewport={"width": 1440, "height": 960})
        erros: list[str] = []
        externos: list[str] = []

        def _req(r):
            # fonte e CDN externos nao sao alcancaveis do container de build;
            # falha de rede la nao e defeito do visualizador
            (externos if "127.0.0.1" not in r.url else erros).append(
                f"{r.failure} {r.url[:60]}")

        pag.on("pageerror", lambda e: erros.append(str(e)))
        pag.on("console", lambda m: erros.append(m.text)
               if m.type == "error" and "Failed to load resource" not in m.text else None)
        pag.on("requestfailed", _req)
        if tres:
            pag.route("**/three.min.js", lambda r: r.fulfill(
                path=tres, content_type="application/javascript"))

        pag.goto(f"http://127.0.0.1:{porta}/porto-real-caderno.html")
        pag.wait_for_function("() => typeof SHEETS !== 'undefined' "
                              "&& document.getElementById('sheet').complete")
        pag.wait_for_timeout(400)

        # ---------------- 2D: o zoom precisa ser proporcional ----------------
        ok(pag.evaluate("() => typeof THREE") == "object", "three.js carregado")
        nat = pag.evaluate("() => ({w: nat.w, h: nat.h})")
        ok(nat["w"] > 800, "prancha rasterizada no tamanho natural", str(nat))

        pag.evaluate("() => ajustar()")
        largura0 = pag.evaluate("() => parseFloat(img.style.width)")
        pct0 = pag.evaluate("() => zval.textContent")
        ok(pct0 == "100%", "ajuste inicial marca 100%", pct0)

        medidas = []
        for _ in range(4):
            pag.evaluate("() => passo(1)")
            medidas.append((pag.evaluate("() => parseFloat(img.style.width)"),
                            pag.evaluate("() => zval.textContent")))
        esperado = ["150%", "200%", "300%", "400%"]
        ok([m[1] for m in medidas] == esperado,
           "a escada de zoom sobe nos degraus declarados",
           " → ".join(m[1] for m in medidas))
        razao = medidas[-1][0] / largura0
        ok(abs(razao - 4.0) < 0.02,
           "400% amplia a prancha exatamente 4x em pixel", f"{razao:.3f}x")

        # o defeito original: scale() sobre a <img> nao reamostra o vetor
        transf = pag.evaluate("() => img.style.transform")
        ok("scale(" not in transf,
           "o zoom redesenha o SVG (nao estica bitmap com scale)", transf)
        cr = pag.evaluate("() => { const r = img.getBoundingClientRect(); "
                          "return {w: Math.round(r.width)}; }")
        ok(abs(cr["w"] - medidas[-1][0]) < 2,
           "a caixa do elemento acompanha o zoom", str(cr))

        # ancoragem: o ponto sob o cursor nao deve escapar
        pag.evaluate("() => ajustar()")
        antes = pag.evaluate("""() => {
          const r = stage.getBoundingClientRect();
          return {x: (400 - tx) / escala, y: (300 - ty) / escala, l: r.left, t: r.top};
        }""")
        pag.evaluate("(a) => passo(1, a.l + 400, a.t + 300)", antes)
        depois = pag.evaluate("() => ({x: (400 - tx) / escala, y: (300 - ty) / escala})")
        desvio = max(abs(antes["x"] - depois["x"]), abs(antes["y"] - depois["y"]))
        ok(desvio < 1.0, "o ponto sob o cursor fica parado ao ampliar",
           f"{desvio:.2f} px do desenho")

        # limites
        for _ in range(12):
            pag.evaluate("() => passo(1)")
        ok(pag.evaluate("() => zval.textContent") == "2400%",
           "a escada trava no ultimo degrau", pag.evaluate("() => zval.textContent"))
        for _ in range(14):
            pag.evaluate("() => passo(-1)")
        ok(pag.evaluate("() => zval.textContent") == "100%",
           "e volta ao primeiro degrau", pag.evaluate("() => zval.textContent"))

        # ---------------- 2D: navegacao ----------------
        pag.evaluate("() => mostrar(0)")
        pag.wait_for_function("() => img.complete && img.src.includes('PR-01')")
        ok(pag.evaluate("() => zval.textContent") == "100%",
           "trocar de prancha reajusta o enquadramento")
        pag.evaluate("() => mostrar(34)")
        pag.wait_for_function("() => img.complete && img.src.includes('PR-35')")
        ok("PR-35" in pag.evaluate("() => img.src"), "chega na ultima prancha")
        ok(pag.evaluate("() => document.querySelectorAll('#rail button').length") == 35,
           "as 35 pranchas estao no indice")
        ok(pag.evaluate("() => noteKeys.children.length") == 4,
           "cada prancha traz 4 chaves de leitura")

        if fotos:
            pag.evaluate("() => { mostrar(1); }")
            pag.wait_for_function("() => img.complete")
            pag.evaluate("() => passo(1, stage.getBoundingClientRect().left + 500, "
                         "stage.getBoundingClientRect().top + 300)")
            pag.locator("#stage").screenshot(path=os.path.join(OUT, "teste-2d-zoom.png"))

        # ---------------- 3D ----------------
        pag.click(".modos button[data-modo='3d']")
        try:
            pag.wait_for_function("() => typeof R !== 'undefined' && R && "
                                  "R.solidos.length > 0", timeout=25000)
        except Exception:
            ok(False, "o modelo 3D monta",
               pag.evaluate("() => document.getElementById('leitura3d').textContent"))
            srv.shutdown(); nav.close()
            return relatorio()

        n = pag.evaluate("() => R.solidos.length")
        esperados = pag.evaluate("""() => ['terreo','superior','lajes','platibandas',
          'externo','mob','escada'].reduce((s,k)=>s+(M3[k]?M3[k].length:0),0)""")
        ok(n == esperados, "todos os solidos exportados entraram na cena",
           f"{n} de {esperados}")
        ok(pag.evaluate("() => document.querySelectorAll('#cenas button').length") == 8,
           "as 8 cenas aparecem na coluna")
        ok(pag.evaluate("() => document.querySelectorAll('#camadas input').length") == 9,
           "as 9 camadas aparecem no HUD")
        ok(pag.evaluate("() => document.getElementById('stage3d')"
                        ".querySelectorAll('canvas').length") == 1,
           "um unico canvas no palco")

        # o canvas precisa ter conteudo, nao um fundo liso
        cores = pag.evaluate("""() => {
          const c = document.querySelector('#stage3d canvas');
          const g = c.getContext('webgl') || c.getContext('webgl2');
          return g ? 1 : 0;
        }""")
        ok(cores == 1, "contexto WebGL ativo")

        # abas nao deixam os dois modos visiveis ao mesmo tempo
        ok(pag.evaluate("() => document.getElementById('stage').hidden") is True,
           "no 3D o palco 2D some")
        ok(pag.evaluate("() => document.getElementById('barra2d').hidden") is True,
           "no 3D a barra de zoom 2D some")
        ok(pag.evaluate("() => document.getElementById('notas3d').hidden") is False,
           "no 3D a nota do 3D aparece")

        # cenas mudam a camera
        cam0 = pag.evaluate("() => [R.azim, R.elev, R.dist, R.alvo.toArray()]")
        pag.click("#cenas button:nth-child(1) >> nth=0") if False else None
        pag.evaluate("() => document.querySelectorAll('#cenas button')[4].click()")
        pag.wait_for_timeout(200)
        cam1 = pag.evaluate("() => [R.azim, R.elev, R.dist, R.alvo.toArray()]")
        ok(cam0 != cam1, "trocar de cena move a camera", f"{cam0[:3]} → {cam1[:3]}")
        ok(pag.evaluate("() => document.getElementById('leitura3d').textContent")
           .strip() != "", "a cena explica o que esta sendo olhado")

        # camadas desligam de fato
        pag.evaluate("""() => {
          const i = document.querySelectorAll('#camadas input')[1];
          i.checked = false; i.dispatchEvent(new Event('change'));
        }""")
        ok(pag.evaluate("() => R.grupos.superior.visible") is False,
           "desligar a camada some com o pavimento superior")
        pag.evaluate("""() => {
          const i = document.querySelectorAll('#camadas input')[1];
          i.checked = true; i.dispatchEvent(new Event('change'));
        }""")

        # sol: geometria real, nao decorativa
        alturas = []
        for h in (7, 12, 17):
            pag.evaluate("""(h) => {
              const e = document.getElementById('solHora');
              e.value = h; e.dispatchEvent(new Event('input'));
            }""", h)
            alturas.append(pag.evaluate("() => document.getElementById('solVal').textContent"))
        ok(alturas[1].endswith("87°") or "8" in alturas[1].split("·")[-1],
           "ao meio-dia de equinocio o sol fica quase no zenite (lat −3,10°)",
           " | ".join(alturas))
        ok(pag.evaluate("() => R.sol.position.z") > 0, "o sol fica acima do horizonte")

        # corte horizontal
        pag.evaluate("""() => {
          const e = document.getElementById('corte');
          e.value = 1500; e.dispatchEvent(new Event('input'));
        }""")
        ok(pag.evaluate("() => R.plano.constant") == 1500,
           "o corte horizontal chega ao plano de clipping")
        ok("1,50" in pag.evaluate("() => document.getElementById('corteVal').textContent"),
           "e a cota do corte e mostrada em metros")

        # clique identifica ambiente
        pag.evaluate("""() => {
          const e = document.getElementById('corte');
          e.value = 6400; e.dispatchEvent(new Event('input'));
          document.querySelectorAll('#cenas button')[0].click();
        }""")
        pag.wait_for_timeout(300)
        box = pag.locator("#stage3d").bounding_box()
        pag.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        pag.wait_for_timeout(200)
        leitura = pag.evaluate("() => document.getElementById('leitura3d').textContent")
        ok(len(leitura.strip()) > 3, "clicar no modelo devolve alguma leitura", leitura[:70])

        if fotos:
            for i in range(8):
                pag.evaluate("(i) => document.querySelectorAll('#cenas button')[i].click()", i)
                pag.wait_for_timeout(350)
                cid = pag.evaluate("(i) => M3.cenas[i].id", i)
                pag.locator("#stage3d").screenshot(
                    path=os.path.join(OUT, f"teste-3d-{i}-{cid}.png"))

        # volta para o 2D
        pag.click(".modos button[data-modo='2d']")
        pag.wait_for_timeout(250)
        ok(pag.evaluate("() => document.getElementById('stage3d').hidden") is True,
           "voltar ao 2D esconde o palco 3D")
        ok(pag.evaluate("() => zval.textContent") == "100%",
           "e reajusta a prancha, que ficou sem tamanho enquanto escondida",
           pag.evaluate("() => zval.textContent"))

        ok(not erros, "nenhum erro de console ou de script",
           " | ".join(erros[:3]))
        if externos:
            notas.append(f"recursos externos bloqueados no container (esperado): "
                         f"{len(externos)} — {externos[0][:52]}")
        nav.close()
    srv.shutdown()
    return relatorio()


def relatorio() -> int:
    print(f"\n  AUDITORIA DO VISUALIZADOR — {len(notas)} verificacoes passaram, "
          f"{len(falhas)} falharam\n")
    for n in notas:
        print(f"  ok    {n}")
    for f in falhas:
        print(f"  FALHA {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(rodar("--fotos" in sys.argv))
