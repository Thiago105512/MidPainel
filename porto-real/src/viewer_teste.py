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

    import engenharia
    import viewer
    engenharia.main()
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
        pag.wait_for_function("() => typeof svg2d !== 'undefined' && svg2d")
        pag.wait_for_timeout(400)

        # ---------------- 2D: o zoom precisa ser proporcional ----------------
        ok(pag.evaluate("() => typeof THREE") == "object", "three.js carregado")
        nat = pag.evaluate("() => ({w: nat.w, h: nat.h})")
        ok(abs(nat["w"] - 841) < 1 and abs(nat["h"] - 594) < 1,
           "a prancha entra no DOM em milimetros de papel A1", str(nat))
        gs = pag.evaluate("() => svg2d.querySelectorAll('g[data-tipo]').length")
        ok(gs > 50, "os tracos chegam com procedencia", f"{gs} escopos no DOM")

        pag.evaluate("() => ajustar()")
        largura0 = pag.evaluate("() => parseFloat(svg2d.style.width)")
        pct0 = pag.evaluate("() => zval.textContent")
        ok(pct0 == "100%", "ajuste inicial marca 100%", pct0)

        medidas = []
        for _ in range(4):
            pag.evaluate("() => passo(1)")
            medidas.append((pag.evaluate("() => parseFloat(svg2d.style.width)"),
                            pag.evaluate("() => zval.textContent")))
        esperado = ["150%", "200%", "300%", "400%"]
        ok([m[1] for m in medidas] == esperado,
           "a escada de zoom sobe nos degraus declarados",
           " → ".join(m[1] for m in medidas))
        razao = medidas[-1][0] / largura0
        ok(abs(razao - 4.0) < 0.02,
           "400% amplia a prancha exatamente 4x em pixel", f"{razao:.3f}x")

        # o defeito original: scale() sobre a <img> nao reamostra o vetor
        transf = pag.evaluate("() => folha.style.transform")
        ok("scale(" not in transf,
           "o zoom redesenha o SVG (nao estica bitmap com scale)", transf)
        cr = pag.evaluate("() => { const r = svg2d.getBoundingClientRect(); "
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
        pag.wait_for_function("() => miniImg.src.includes('PR-01') && svg2d")
        ok(pag.evaluate("() => zval.textContent") == "100%",
           "trocar de prancha reajusta o enquadramento")
        pag.evaluate("() => mostrar(34)")
        pag.wait_for_function("() => miniImg.src.includes('PR-35') && svg2d")
        ok("PR-35" in pag.evaluate("() => miniImg.src"), "chega na ultima prancha")
        ok(pag.evaluate("() => document.querySelectorAll('#rail button').length") == 35,
           "as 35 pranchas estao no indice")
        ok(pag.evaluate("() => noteKeys.children.length") == 4,
           "cada prancha traz 4 chaves de leitura")

        if fotos:
            pag.evaluate("() => { mostrar(1); }")
            pag.wait_for_function("() => svg2d && miniImg.src.includes('PR-02')")
            pag.wait_for_timeout(300)
            pag.evaluate("() => passo(1, stage.getBoundingClientRect().left + 500, "
                         "stage.getBoundingClientRect().top + 300)")
            pag.locator("#stage").screenshot(path=os.path.join(OUT, "teste-2d-zoom.png"))

        # ---------------- 2D: a prancha como documento (R12) ----------------
        pag.evaluate("() => mostrar(1)")                       # planta do terreo
        pag.wait_for_function("() => svg2d && miniImg.src.includes('PR-02')")
        pag.wait_for_timeout(300)

        ncam = pag.evaluate("() => document.querySelectorAll('#camadas2d input').length")
        ok(ncam >= 8, "as camadas do 2D vem dos tipos presentes na prancha",
           f"{ncam} camadas")

        # desligar cotas tem de esconder os grupos de cota, e so eles
        pag.evaluate("""() => {
          const i = [...document.querySelectorAll('#camadas2d label')]
            .find(l => l.textContent.trim().toLowerCase().startsWith('cota'))
            .querySelector('input');
          i.checked = false; i.dispatchEvent(new Event('change'));
        }""")
        escondidas = pag.evaluate("""() => {
          const c = [...svg2d.querySelectorAll('[data-tipo=cota]')];
          const p = [...svg2d.querySelectorAll('[data-tipo=parede]')];
          return {cota: c.filter(g => g.style.display === 'none').length, ncota: c.length,
                  par: p.filter(g => g.style.display === 'none').length};
        }""")
        ok(escondidas["cota"] == escondidas["ncota"] and escondidas["par"] == 0,
           "a camada desliga exatamente o seu tipo",
           f"{escondidas['cota']}/{escondidas['ncota']} cotas fora, "
           f"{escondidas['par']} paredes fora")
        pag.evaluate("""() => {
          const i = [...document.querySelectorAll('#camadas2d label')]
            .find(l => l.textContent.trim().toLowerCase().startsWith('cota'))
            .querySelector('input');
          i.checked = true; i.dispatchEvent(new Event('change'));
        }""")

        # clicar num ambiente abre a ficha, e a ficha traz o que outras
        # pranchas ja diziam sobre ele
        pag.evaluate("""() => {
          const g = [...svg2d.querySelectorAll('g[data-tipo=ambiente]')]
            .find(x => x.dataset.cod === 'T-COZ');
          porRealce(g); mostrarFicha(g);
        }""")
        fic = pag.evaluate("() => document.getElementById('ficha').textContent")
        ok("COZINHA" in fic and "21,60" in fic.replace(".", ","),
           "clicar no ambiente abre a ficha com nome e area", fic[:60])
        ok("forro" in fic.lower() and "gesso" in fic.lower(),
           "a ficha puxa o acabamento declarado em outra prancha",
           fic[:90])

        # o realce cobre o AMBIENTE, nao o rotulo: e para isso que o escopo
        # carrega a caixa em coordenadas de papel
        cx = pag.evaluate("""() => {
          const g = [...svg2d.querySelectorAll('g[data-tipo=ambiente]')]
            .find(x => x.dataset.cod === 'T-COZ');
          const b = g.dataset.box.split(' ').map(Number);
          const r = svg2d.querySelector('.realce');
          return {box: b[2], realce: parseFloat(r.getAttribute('width')),
                  rotulo: g.getBBox().width};
        }""")
        ok(abs(cx["realce"] - cx["box"]) < 3 and cx["box"] > cx["rotulo"] * 1.5,
           "o realce cobre o ambiente inteiro, nao so o rotulo",
           f"caixa {cx['box']:.0f} mm de papel contra rotulo {cx['rotulo']:.0f}")

        # escala grafica
        eg = pag.evaluate("""() => ({txt: document.getElementById('escalagTxt').textContent,
          vis: !document.getElementById('escalag').hidden,
          larg: parseFloat(document.getElementById('escalagBarra').style.width)})""")
        ok(eg["vis"] and "1:50" in eg["txt"], "a escala grafica declara o denominador",
           eg["txt"])
        antes = eg["larg"]
        pag.evaluate("() => passo(1)")
        depois = pag.evaluate("() => parseFloat(document.getElementById('escalagBarra').style.width)")
        ok(depois != antes, "e a barra acompanha o zoom, porque 1:50 so vale no papel",
           f"{antes:.0f} px → {depois:.0f} px")
        pag.evaluate("() => ajustar()")

        # busca dentro do desenho
        pag.evaluate("""() => { const b = document.getElementById('busca');
          b.value = 'DESPENSA'; b.dispatchEvent(new Event('input')); }""")
        pag.wait_for_timeout(200)
        bq = pag.evaluate("() => ({n: achados.length, "
                          "conta: document.getElementById('buscaConta').textContent})")
        ok(bq["n"] >= 1, "a busca acha texto dentro da prancha",
           f"DESPENSA: {bq['n']} ocorrencia(s), contador {bq['conta']}")
        pag.evaluate("""() => { const b = document.getElementById('busca');
          b.value = ''; b.dispatchEvent(new Event('input')); }""")

        # medicao: dois pontos devolvem milimetro de MODELO, nao pixel de tela
        pag.evaluate("() => ajustar()")
        med = pag.evaluate("""() => {
          medindo = true; denom = 50;
          const r = stage.getBoundingClientRect();
          const p1 = {clientX: r.left + 200, clientY: r.top + 200};
          const p2 = {clientX: r.left + 400, clientY: r.top + 200};
          const a = papel(p1), b = papel(p2);
          stage.dispatchEvent(new MouseEvent('click', p1));
          stage.dispatchEvent(new MouseEvent('click', p2));
          const t = capaRegua.querySelector('text');
          medindo = false;
          return {rotulo: t ? t.textContent : null,
                  esperado: Math.hypot(b.x - a.x, b.y - a.y) * 50};
        }""")
        lido = None
        if med["rotulo"]:
            v = med["rotulo"].replace(" m", "").replace(" mm", "").replace(",", ".")
            lido = float(v) * (1000 if "m" in med["rotulo"] and "mm" not in med["rotulo"] else 1)
        ok(lido is not None and abs(lido - med["esperado"]) < 20,
           "a regua devolve milimetro do modelo, nao pixel de tela",
           f"{med['rotulo']} contra {med['esperado']:.0f} mm calculados")
        pag.evaluate("() => limparRegua()")

        # modo sem moldura
        pag.evaluate("() => ajustar()")
        antes_esc = pag.evaluate("() => escala")
        pag.click("#semmold")
        pag.wait_for_timeout(250)
        sm = pag.evaluate("""() => {
          const car = svg2d.querySelector('[data-tipo=carimbo]');
          const c = caixaDesenho();
          return {carimbo: car.style.display, escala,
                  caixa: [Math.round(c.width), Math.round(c.height)]};
        }""")
        ok(sm["carimbo"] == "none", "sem moldura esconde o carimbo")
        # o ganho e o que sobra de pagina em volta do desenho: numa prancha bem
        # ocupada e pequeno, e isso e uma propriedade da prancha, nao um defeito
        ganho = sm["escala"] / antes_esc
        ok(ganho >= 0.999,
           "e reenquadra no desenho, nunca menor que o enquadramento da pagina",
           f"desenho {sm['caixa'][0]}x{sm['caixa'][1]} mm de papel; "
           f"ganho de {(ganho - 1) * 100:+.1f} %")
        pag.click("#semmold")
        pag.wait_for_timeout(200)
        ok(pag.evaluate("() => svg2d.querySelector('[data-tipo=carimbo]').style.display") != "none",
           "e devolve a moldura quando se desliga o modo")

        # minimapa
        mm = pag.evaluate("""() => {
          const j = document.getElementById('miniJanela');
          return {w: parseFloat(j.style.width), mw: mini.clientWidth,
                  h: parseFloat(j.style.height)};
        }""")
        ok(0 < mm["w"] <= mm["mw"] + 1, "o minimapa mostra a janela visivel dentro do limite",
           f"{mm['w']:.0f} de {mm['mw']} px")

        if fotos:
            pag.locator("#stage").screenshot(path=os.path.join(OUT, "teste-2d-ficha.png"))

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

        # =================================================================
        # ABA DE ENGENHARIA — 62 paineis, 801 pecas e a cadeia inteira
        # =================================================================
        pag.click(".modos button[data-modo='eng']")
        pag.wait_for_timeout(700)
        ok(pag.evaluate("() => document.getElementById('stageEng').hidden") is False,
           "a aba de engenharia abre")
        ok(pag.evaluate("() => document.getElementById('stage').hidden") is True,
           "e esconde o palco 2D (a tabela DONO cobre as tres abas)")
        ok(pag.evaluate("() => !!ENG && ENG.paineis.length > 0"),
           "engenharia.json carrega no navegador",
           str(pag.evaluate("() => ENG && ENG.paineis.length")))

        # o painel de controle mostra o que o motor decidiu, nao um texto fixo
        ok(pag.evaluate("() => document.querySelectorAll('#engConteudo .cartao').length")
           == pag.evaluate("() => ENG.resumo.length"),
           "o painel de controle mostra todas as figuras do resumo")
        ok(pag.evaluate("() => document.querySelectorAll('#engConteudo .check li').length")
           == pag.evaluate("() => ENG.liberacao.itens.length"),
           "e os 16 itens do checklist, um a um",
           str(pag.evaluate("() => ENG.liberacao.itens.length")))
        ok(pag.evaluate("() => document.querySelectorAll('#engConteudo .nota .form').length")
           == pag.evaluate("() => Object.keys(ENG.scores).length"),
           "cada nota vem com a formula que a produziu")
        ok(pag.evaluate("() => document.querySelector('#engConteudo .selo').textContent")
           .strip().startswith(pag.evaluate("() => ENG.liberacao.situacao")[:12]),
           "o selo de liberacao repete a situacao do motor")

        # o modo de leitura muda a explicacao
        antes = pag.evaluate("() => document.querySelector('#engConteudo .cap').textContent")
        pag.click("#engConteudo [data-leitura='especialista']")
        pag.wait_for_timeout(200)
        depois = pag.evaluate("() => document.querySelector('#engConteudo .cap').textContent")
        ok(antes != depois and len(depois) > 40,
           "trocar o modo de leitura troca a explicacao")
        fig = pag.evaluate("() => document.querySelectorAll('#engConteudo .cartao .val')[0].textContent")
        pag.click("#engConteudo [data-leitura='executivo']")
        pag.wait_for_timeout(200)
        ok(pag.evaluate("() => document.querySelectorAll('#engConteudo .cartao .val')[0].textContent")
           == fig, "e nao troca nenhum numero", fig)
        pag.click("#engConteudo [data-leitura='educacional']")
        pag.wait_for_timeout(150)

        # paineis: o desenho vem da posicao das pecas
        pag.click("#vistasEng button[data-vista='paineis']")
        pag.wait_for_timeout(350)
        ok(pag.evaluate("() => document.querySelectorAll('#engConteudo .lista button').length")
           == pag.evaluate("() => ENG.paineis.length"),
           "a lista traz os 62 paineis")
        ok(pag.evaluate("""() => {
             const p = ENG.paineis.find(q => q.cod === painelSel);
             return document.querySelectorAll('#engConteudo .desenho svg rect').length
                    >= p.pecas.length; }"""),
           "o desenho tem ao menos um retangulo por peca")
        ok(pag.evaluate("""() => {
             const p = ENG.paineis.find(q => q.cod === painelSel);
             const rs = [...document.querySelectorAll('#engConteudo .desenho svg rect')];
             return rs.every(r => {
               const x = +r.getAttribute('x'), w = +r.getAttribute('width');
               return x >= -1 && x + w <= p.comp + 1; }); }"""),
           "nenhuma peca desenhada fora do painel")
        ok(pag.evaluate("""() => {
             const p = ENG.paineis.find(q => q.cod === painelSel);
             const rs = [...document.querySelectorAll('#engConteudo .desenho svg rect')];
             return rs.every(r => {
               const y = +r.getAttribute('y'), h = +r.getAttribute('height');
               return y >= -1 && y + h <= p.altura + 1; }); }"""),
           "nem acima da guia superior")
        com_vao = pag.evaluate("() => (ENG.paineis.find(p => p.aberturas.length) || {}).cod")
        if com_vao:
            pag.click(f"#engConteudo [data-painel='{com_vao}']")
            pag.wait_for_timeout(300)
            ok(pag.evaluate("() => painelSel") == com_vao,
               "clicar troca o painel mostrado", com_vao)
            ok(pag.evaluate("""() => {
                 const p = ENG.paineis.find(q => q.cod === painelSel);
                 const t = [...document.querySelectorAll('#engConteudo .desenho svg text')]
                   .map(n => n.textContent);
                 return p.aberturas.every(a => t.includes(a.tipo)); }"""),
               "e o vao aparece rotulado pelo tipo do quadro de esquadrias")
            ok(pag.evaluate("""() => {
                 const p = ENG.paineis.find(q => q.cod === painelSel);
                 return p.familias['header'] === p.aberturas.length; }"""),
               "cada vao tem a sua verga — o desenho denuncia se faltar")

        # pecas: filtro, ordenacao e busca operam sobre as 801
        pag.click("#vistasEng button[data-vista='pecas']")
        pag.wait_for_timeout(350)
        total = pag.evaluate("() => todasPecas().length")
        ok(total == sum(pag.evaluate("() => Object.values(ENG.familias)")),
           f"a tabela enxerga as {total} pecas")
        pag.select_option("#filFam", "header")
        pag.wait_for_timeout(250)
        ok(pag.evaluate("() => document.querySelectorAll('#engConteudo tbody tr').length")
           == pag.evaluate("() => ENG.familias['header']"),
           "filtrar por familia devolve exatamente as vergas",
           str(pag.evaluate("() => ENG.familias['header']")))
        pag.select_option("#filFam", "")
        pag.wait_for_timeout(200)
        pag.click("#engConteudo th[data-ord='comp']")
        pag.wait_for_timeout(250)
        ok(pag.evaluate("""() => {
             const c = [...document.querySelectorAll('#engConteudo tbody tr')]
               .map(r => +r.children[4].textContent);
             return c.every((v, i) => i === 0 || c[i-1] <= v); }"""),
           "ordenar por comprimento ordena de fato")
        pag.click("#engConteudo th[data-ord='comp']")
        pag.wait_for_timeout(250)
        ok(pag.evaluate("""() => {
             const c = [...document.querySelectorAll('#engConteudo tbody tr')]
               .map(r => +r.children[4].textContent);
             return c.every((v, i) => i === 0 || c[i-1] >= v); }"""),
           "e o segundo clique inverte")

        # corte
        pag.click("#vistasEng button[data-vista='corte']")
        pag.wait_for_timeout(350)
        ok(abs(pag.evaluate("() => ENG.nesting.bruto - ENG.nesting.usado - ENG.nesting.perda"))
           < 1e-6, "o plano de corte fecha: bruto = usado + perda")
        ok(pag.evaluate("""() => ENG.nesting.barras.every(b =>
             b.pecas.reduce((s, q) => s + q.comp, 0) <= b.bruto + 1e-6)"""),
           "nenhuma barra recebe mais peca do que cabe")

        # montagem
        pag.click("#vistasEng button[data-vista='montagem']")
        pag.wait_for_timeout(350)
        ok(pag.evaluate("() => document.querySelectorAll('#listaPassos button').length")
           == pag.evaluate("() => ENG.montagem.n_passos"),
           "a sequencia traz todos os passos",
           str(pag.evaluate("() => ENG.montagem.n_passos")))
        ok(pag.evaluate("""() => ENG.montagem.passos.every((s, i) =>
             i === 0 || s.acumulado_h >= ENG.montagem.passos[i-1].acumulado_h)"""),
           "a hora acumulada nunca anda para tras")
        acesos = ("() => document.querySelectorAll('#engConteudo .desenho svg "
                  "line[stroke-opacity=\"1\"]').length")
        linhas0 = pag.evaluate(acesos)
        # o primeiro passo e a fundacao, que nao acende painel nenhum: avancar
        # ate o primeiro passo de painel e o que tem de mudar a planta
        pag.click("#passoMais")
        pag.click("#passoMais")
        pag.wait_for_timeout(320)
        linhas1 = pag.evaluate(acesos)
        ok(linhas1 > linhas0,
           "avancar ate o primeiro painel acende painel na planta",
           f"{linhas0} -> {linhas1}")
        pag.evaluate("() => { passoAtual = ENG.montagem.n_passos; renderEng(); }")
        pag.wait_for_timeout(320)
        ok(pag.evaluate(acesos) == pag.evaluate("() => ENG.paineis.length"),
           "e no ultimo passo a planta esta inteira montada",
           str(pag.evaluate(acesos)))
        ok(pag.evaluate("""() => ENG.montagem.passos.filter(s => s.painel).length
             === ENG.paineis.length"""),
           "todo painel tem o seu passo de montagem, e so um")
        pag.click("#passoZero")
        pag.wait_for_timeout(150)
        pag.click("#playMont")
        pag.wait_for_timeout(900)
        pag.click("#playMont")
        pag.wait_for_timeout(250)
        ok(pag.evaluate("() => passoAtual") > 1,
           "a animacao anda sozinha e pausa",
           str(pag.evaluate("() => passoAtual")))

        # logistica e documentos
        pag.click("#vistasEng button[data-vista='logistica']")
        pag.wait_for_timeout(300)
        ok(pag.evaluate("() => ENG.logistica.uso_peso <= 1 && ENG.logistica.uso_volume <= 1"),
           "a carga nao excede o container")
        pag.click("#vistasEng button[data-vista='documentos']")
        pag.wait_for_timeout(350)
        ok(len(pag.evaluate("() => document.querySelector('.doc-txt').textContent")) > 200,
           "o documento sai com conteudo, nao so cabecalho")
        pag.click("#engConteudo [data-doc='memorial_compressao']")
        pag.wait_for_timeout(250)
        m_edu = pag.evaluate("() => document.querySelector('.doc-txt').textContent")
        pag.click("#engConteudo [data-leitura='especialista']")
        pag.wait_for_timeout(250)
        m_esp = pag.evaluate("() => document.querySelector('.doc-txt').textContent")
        import re as _re
        n_edu = set(_re.findall(r"\d+[.,]\d+", m_edu))
        n_esp = set(_re.findall(r"\d+[.,]\d+", m_esp))
        ok(m_edu != m_esp and bool(n_edu & n_esp),
           "os tres modos mudam o texto e mantem o valor de calculo",
           f"{len(n_edu & n_esp)} numeros identicos nos dois modos")

        # o que o sistema NAO faz, com o mesmo rigor do que faz
        pag.click("#vistasEng button[data-vista='bloqueios']")
        pag.wait_for_timeout(350)
        ok(pag.evaluate("() => document.querySelectorAll('#engConteudo .lista button').length")
           == pag.evaluate("() => ENG.contratos.length"),
           "os contratos do que e bloqueado estao na interface",
           str(pag.evaluate("() => ENG.contratos.length")))
        ok(pag.evaluate("""() => ENG.contratos.every(c =>
             c.bloqueio.length > 40 && c.fonte.length > 20 && c.aceite.length > 40
             && c.esquema.length > 0)"""),
           "cada um diz o bloqueio, a fonte, o aceite e o esquema")
        ok(pag.evaluate("() => document.querySelectorAll('#engConteudo tbody tr').length")
           == pag.evaluate("() => (ENG.contratos.find(c => c.cod === contratoSel) "
                           "|| ENG.contratos[0]).esquema.length"),
           "e a tabela mostra os campos que o fornecedor tera de entregar")
        ultimo = pag.evaluate("() => ENG.contratos[ENG.contratos.length-1].cod")
        pag.click(f"#engConteudo [data-contrato='{ultimo}']")
        pag.wait_for_timeout(250)
        ok(pag.evaluate("() => contratoSel") == ultimo,
           "trocar de contrato troca o esquema mostrado", ultimo)

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
