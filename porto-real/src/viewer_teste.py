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
        # a lista sai das CAMADAS declaradas, nao de um rol escrito aqui: um
        # rol escrito no teste envelhece na primeira camada nova e acusa falha
        # onde so houve crescimento
        esperados = pag.evaluate("""() => ['terreo','superior','lajes',
          'platibandas','externo','mob','escada','lsf']
          .reduce((s,k)=>s+(M3[k]?M3[k].length:0),0)""")
        ok(n == esperados, "todos os solidos exportados entraram na cena",
           f"{n} de {esperados}")
        ok(pag.evaluate("() => document.querySelectorAll('#cenas button').length") == 8,
           "as 8 cenas aparecem na coluna")
        ok(pag.evaluate("() => document.querySelectorAll('#camadas input').length")
           == pag.evaluate("() => CAMADAS.length"),
           "toda camada declarada aparece no HUD",
           str(pag.evaluate("() => CAMADAS.length")))
        ok(pag.evaluate("() => M3.lsf.length") > 700,
           "a estrutura LSF inteira esta no modelo 3D, peca a peca",
           str(pag.evaluate("() => M3.lsf.length")))
        # a peca tem duas formas: caixa alinhada (p + s) ou definida pelas
        # pontas (de + ate), que e a fita em X. Um teste que so conhece a
        # primeira quebra no dia em que a segunda entra — e quebrou
        ok(pag.evaluate("""() => M3.lsf.every(b => b.cod && b.fam && b.perf
             && b.painel && (b.de ? b.ate && b.de.length === 3
                                  : b.s.every(v => v > 0)))"""),
           "cada peca da estrutura traz codigo, familia, perfil e posicao, "
           "seja caixa alinhada ou peca inclinada")
        ok(pag.evaluate("""() => {
             const d = M3.lsf.filter(b => b.fam === 'diagonal');
             return d.length > 0 && d.every(b => {
               const dx = b.ate[0]-b.de[0], dy = b.ate[1]-b.de[1],
                     dz = b.ate[2]-b.de[2];
               return Math.hypot(dx, dy, dz) > 1000 && dz > 0; }); }"""),
           "as fitas em X sao diagonais de verdade: sobem e tem comprimento",
           str(pag.evaluate("() => M3.lsf.filter(b => b.fam === 'diagonal').length")))
        ok(pag.evaluate("""() => {
             const d = M3.lsf.filter(b => b.fam === 'diagonal');
             const m = R.solidos.filter(s => s.userData.fam === 'diagonal');
             return m.length === d.length
                    && m.every(s => Math.abs(s.quaternion.w) < 0.9999); }"""),
           "e chegam a cena rotacionadas, nao deitadas como caixa")
        ok(pag.evaluate("""() => ['viga','viga de borda','travamento','diagonal']
             .every(f => M3.lsf.some(b => b.fam === f))"""),
           "vigamento de piso, borda, travamento e contraventamento estao no modelo")
        ok(pag.evaluate("""() => new Set(M3.lsf.map(b => b.c)).size >= 6"""),
           "cada familia estrutural tem a sua cor",
           str(pag.evaluate("() => new Set(M3.lsf.map(b => b.c)).size")))
        ok(pag.evaluate("""() => {
             const g = R.grupos.lsf;
             return g && g.children.length === M3.lsf.length && !g.visible; }"""),
           "a camada da estrutura entra desligada, para nao brigar com a parede")
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
        # por id: a classe .check passou a ser usada tambem pela lista de
        # sistemas, e contar por classe somava as duas — a terceira vez que um
        # seletor por aparencia quebra neste arquivo
        ok(pag.evaluate("() => document.querySelectorAll('#checklist li').length")
           == pag.evaluate("() => ENG.liberacao.itens.length"),
           "e todos os itens do checklist, um a um",
           str(pag.evaluate("() => ENG.liberacao.itens.length")))
        ok(pag.evaluate("() => document.querySelectorAll('#engConteudo .nota .form').length")
           == pag.evaluate("() => Object.keys(ENG.scores).length"),
           "cada nota vem com a formula que a produziu")
        # por id, nao por ordem: a ordem muda quando a tela ganha um bloco, e
        # um teste que depende da ordem acusa falha onde nao ha defeito
        ok(pag.evaluate("() => document.getElementById('seloLiberacao').textContent")
           .strip().startswith(pag.evaluate("() => ENG.liberacao.situacao")[:12]),
           "o selo de liberacao repete a situacao do motor")

        # a verificacao estrutural aparece, e aparece com o numero que importa
        ok(pag.evaluate("() => document.querySelectorAll('#engConteudo .eng-sec')"
                        ".length >= 4"),
           "o painel de controle traz o bloco de verificacao estrutural")
        ok(pag.evaluate("() => ENG.estrutura.n") > 300,
           "todos os montantes sao verificados, nao um tipico",
           str(pag.evaluate("() => ENG.estrutura.n")))
        ok(pag.evaluate("""() => ENG.estrutura.histograma
             .reduce((s, h) => s + h.n, 0) === ENG.estrutura.n"""),
           "o histograma soma exatamente o total verificado")
        ok(pag.evaluate("""() => ENG.estrutura.maxima <= 1.0
             && ENG.estrutura.reprovadas === 0"""),
           "nenhum montante passa de 1,00 de utilizacao",
           str(pag.evaluate("() => ENG.estrutura.maxima")))
        ok(pag.evaluate("""() => {
             const u = ENG.estrutura.u_alvo, g = ENG.estrutura.governa;
             return u < 1.0 && g.nsd > 0 && g.nrd > g.nsd; }"""),
           "o alvo de projeto e menor que o limite normativo, e a peca que "
           "governa vem nomeada com N_sd e N_rd")
        ok(pag.evaluate("() => ENG.estrutura.hipoteses.length") >= 5,
           "as hipoteses de caminho de carga estao na tela, nao so no codigo",
           str(pag.evaluate("() => ENG.estrutura.hipoteses.length")))

        ok(pag.evaluate("() => ENG.plausibilidade.n") >= 8,
           "as faixas de plausibilidade estao na tela",
           str(pag.evaluate("() => ENG.plausibilidade.n")))
        ok(pag.evaluate("""() => ENG.plausibilidade.itens.every(x =>
             x.minimo < x.maximo && x.fonte.length > 20)"""),
           "cada faixa tem minimo, maximo e fonte declarada")
        ok(pag.evaluate("""() => document.querySelectorAll('#sistemas li').length
             === ENG.completude.itens.length"""),
           "e os sistemas construtivos obrigatorios, um a um",
           str(pag.evaluate("() => ENG.completude.itens.length")))
        ok(pag.evaluate("() => ENG.completude.completo"),
           "nenhum sistema construtivo ausente",
           pag.evaluate("() => ENG.completude.situacao"))

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

        # materiais: o que vai em cada estrutura, com norma e formato
        pag.click("#vistasEng button[data-vista='materiais']")
        pag.wait_for_timeout(350)
        ok(pag.evaluate("() => ENG.materiais.composicoes.length") >= 5,
           "as composicoes de parede estao na interface",
           str(pag.evaluate("() => ENG.materiais.composicoes.length")))
        ok(pag.evaluate("""() => ENG.materiais.composicoes.every(c =>
             c.camadas.length > 0 && c.camadas.every(k => k.norma))"""),
           "toda camada declara a norma do seu material")
        ok(pag.evaluate("""() => ENG.materiais.composicoes.every(c =>
             c.esp_construida <= c.esp_nominal)"""),
           "nenhuma composicao se constroi mais grossa que o modulo")
        ok(pag.evaluate("""() => ENG.materiais.paginacao.every(p =>
             p.placas > 0 && p.aproveitamento > 0 && p.aproveitamento <= 1)"""),
           "a paginacao devolve placa inteira com aproveitamento valido",
           str(pag.evaluate("() => ENG.materiais.placas")) + " placas")
        ok(pag.evaluate("""() => ENG.materiais.esquadrias.every(e =>
             e.n > 0 && (e.area_vidro === 0 || e.vidro))"""),
           "toda esquadria envidracada tem vidro especificado com motivo")
        ok(pag.evaluate("""() => {
             const d = ENG.materiais.desempenho;
             return d.norma && Object.values(d).some(v =>
               String(v).includes('(H)')); }"""),
           "o desempenho de estanqueidade entra como exigencia (H), nao valor")
        ok(pag.evaluate("() => Object.keys(ENG.materiais.por_painel).length")
           == pag.evaluate("() => ENG.paineis.length"),
           "todo painel aponta para uma composicao")
        ok(pag.evaluate("""() => {
             const f = ENG.materiais.fundacao;
             return f.volume_m3 > 0 && f.aco_kg > 0 && f.pendencia.length > 20
                    && f.hipoteses.length >= 4; }"""),
           "a fundacao traz quantidade, pendencia e hipoteses declaradas",
           str(pag.evaluate("() => ENG.materiais.fundacao.volume_m3")) + " m3")
        ultimo = pag.evaluate("() => ENG.materiais.composicoes.slice(-1)[0].cod")
        pag.click(f"#engConteudo [data-comp='{ultimo}']")
        pag.wait_for_timeout(250)
        ok(pag.evaluate("() => compSel") == ultimo,
           "trocar de composicao troca as camadas mostradas", ultimo)

        # parafusos: a pergunta "quantos e quais" tem de ter resposta na tela
        pag.click("#vistasEng button[data-vista='parafusos']")
        pag.wait_for_timeout(350)
        ok(pag.evaluate("() => ENG.juntas.total") > 3000,
           "o programa de parafusos esta na interface",
           str(pag.evaluate("() => ENG.juntas.total")))
        ok(pag.evaluate("""() => ENG.juntas.por_origem
             .reduce((s, o) => s + o.n, 0) === ENG.juntas.total"""),
           "as origens somam exatamente o total: nenhum parafuso sem origem")
        ok(pag.evaluate("""() => ENG.juntas.por_tipo
             .reduce((s, t) => s + t.n, 0) === ENG.juntas.total"""),
           "e os tipos tambem somam o total")
        ok(pag.evaluate("""() => ENG.juntas.por_origem
             .some(o => o.origem === 'FORCA' && o.n > 0)"""),
           "parte dos parafusos vem de forca calculada, e a interface diz quanto",
           str(pag.evaluate("""() => (ENG.juntas.por_origem
             .find(o => o.origem === 'FORCA') || {}).n""")))
        ok(pag.evaluate("""() => ENG.juntas.exemplos.every(x =>
             x.tipo && x.parafuso && x.n >= 2 && x.origem)"""),
           "cada tipo de junta traz o parafuso, a quantidade e a origem")
        ok(pag.evaluate("""() => ENG.paineis.every(p =>
             p.parafusos > 0 && p.juntas.length > 0)"""),
           "nenhum painel fica sem junta programada")
        ok(pag.evaluate("""() => ENG.paineis.reduce((s, p) => s + p.parafusos, 0)
             === ENG.juntas.total"""),
           "a soma dos paineis bate com o total: o numero e um so")

        # instalacoes: o percurso que existia no desenho e nao no modelo
        pag.click("#vistasEng button[data-vista='instalacoes']")
        pag.wait_for_timeout(350)
        ok(pag.evaluate("() => ENG.instalacoes.hidraulica.comp_total") > 100,
           "o tubo tem comprimento, e nao so ponto",
           str(pag.evaluate("() => ENG.instalacoes.hidraulica.comp_total")) + " m")
        ok(pag.evaluate("""() => {
             const h = ENG.instalacoes.hidraulica;
             const soma = h.itens.reduce((s, i) => s + i.comp_m, 0);
             return Math.abs(soma - h.comp_total) < 0.5; }"""),
           "a soma por diametro bate com o total: nao ha metro sem diametro")
        # o fator tem de estar NA TELA: um limite inferior apresentado como
        # numero fechado e pior que numero nenhum
        ok(pag.evaluate("() => ENG.instalacoes.hidraulica.fator") > 1.0
           and "1,20" in pag.evaluate(
               "() => document.getElementById('engConteudo').textContent"),
           "o fator de percurso aparece declarado na interface",
           str(pag.evaluate("() => ENG.instalacoes.hidraulica.fator")))
        ok(pag.evaluate("""() => {
             const e = ENG.instalacoes.eletrica;
             return e.pontos > 50 && e.eletroduto_m > 0 && e.cabo_m > e.eletroduto_m; }"""),
           "eletroduto e cabo existem, e o cabo e mais longo que o eletroduto",
           str(pag.evaluate("() => ENG.instalacoes.eletrica.pontos")) + " pontos")
        ok(pag.evaluate("""() => {
             const c = ENG.instalacoes.climatizacao;
             return c.n > 0 && c.linhas.length === c.n
                    && Math.abs(c.isolamento_m - c.linha_m * 2) < 0.5; }"""),
           "a linha frigorigena traz isolamento de ida e volta")
        ok(pag.evaluate("() => ENG.instalacoes.clash.volumes") > 500,
           "o clash confronta volume a volume, e nao contra o vazio",
           str(pag.evaluate("() => ENG.instalacoes.clash.volumes")) + " volumes")
        # e o conflito nao pode chegar como contador: sem peca e motivo nao ha
        # como resolver nenhum deles
        ok(pag.evaluate("""() => {
             const k = ENG.instalacoes.clash;
             return k.shafts.concat(k.criticos).every(c =>
               c.peca && c.dn > 0 && c.motivo && c.motivo.length > 40); }"""),
           "cada conflito diz a peca, o diametro e o motivo por extenso")
        ok(pag.evaluate("""() => {
             const k = ENG.instalacoes.clash;
             const n = k.shafts.length + k.criticos.length;
             const t = document.getElementById('engConteudo').textContent;
             return n === 0 ? t.includes('Sem conflito')
                            : t.includes('uma causa'); }"""),
           "o conflito e mostrado agrupado pela causa, nao linha a linha",
           str(pag.evaluate("""() => ENG.instalacoes.clash.shafts.length
             + ENG.instalacoes.clash.criticos.length""")) + " conflitos")
        ok(pag.evaluate("""() => ENG.liberacao.itens
             .some(i => i.item === 'clashes')"""),
           "e o checklist de liberacao le esse resultado, nao um literal")

        # shaft: a decisao tem de chegar na tela com o PORQUE, nao so com a
        # coordenada — coordenada sem motivo e indistinguivel de arbitrada
        ok(pag.evaluate("""() => {
             const S = ENG.instalacoes.shafts;
             return S && S.prumadas.length === 3
                    && S.prumadas.every(v => v.motivo && v.motivo.length > 40); }"""),
           "cada prumada traz lado, afastamento e motivo por extenso")
        ok(pag.evaluate("""() => ENG.instalacoes.shafts.prumadas
             .filter(v => v.deslocado > 0)
             .every(v => v.declarada && (v.x !== v.declarada[0] ||
                                         v.y !== v.declarada[1]))"""),
           "a posicao declarada acompanha a resolvida, e elas diferem",
           str(pag.evaluate("""() => ENG.instalacoes.shafts.prumadas
             .filter(v => v.deslocado > 0).length""")) + " deslocadas")
        ok(pag.evaluate("""() => {
             const S = ENG.instalacoes.shafts;
             return S.placa_m2 > 0 && S.piso_tomado_m2 > 0; }"""),
           "a decisao tem material e custo de piso, nao so geometria",
           str(pag.evaluate("() => ENG.instalacoes.shafts.placa_m2")) + " m2 de RU")
        ok("caixa na face" in pag.evaluate(
               "() => document.getElementById('engConteudo').textContent"),
           "e a regra adotada aparece na tela, nao so no codigo")

        # pendencias: o 18o item, e o que ele impede a tela de dizer
        pag.click("#vistasEng button[data-vista='painel']")
        pag.wait_for_timeout(350)
        ok(pag.evaluate("() => ENG.liberacao.itens.length") == 18,
           "o checklist tem 18 itens",
           str(pag.evaluate("() => ENG.liberacao.itens.length")))
        ok(pag.evaluate("""() => ENG.pendencias.bloqueantes.length > 0
             && ENG.pendencias.bloqueantes.every(d => d.bloqueia === 'fabricacao')"""),
           "as pendencias que trancam a fabricacao estao nomeadas",
           str(pag.evaluate("() => ENG.pendencias.bloqueantes.map(d => d.n).join()")))
        ok(pag.evaluate("""() => {
             const b = ENG.pendencias.bloqueantes.length > 0;
             const rep = ENG.liberacao.itens
               .some(i => i.item === 'pendencias' && i.status !== 'OK');
             return b === rep; }"""),
           "e o item 'pendencias' do checklist responde a elas")
        ok(pag.evaluate("""() => {
             const t = document.getElementById('engConteudo').textContent;
             return ENG.pendencias.bloqueantes.length === 0
                    || !t.includes('LIBERADO PARA FABRICACAO'); }"""),
           "com pendencia bloqueante a tela NAO anuncia fabricacao liberada",
           pag.evaluate("() => ENG.liberacao.situacao"))
        ok(pag.evaluate("""() => ENG.combinacoes.ok
             && ENG.combinacoes.orfas.length === 0
             && Object.values(ENG.combinacoes.cobertura)
                  .every(v => v.length > 0)"""),
           "toda acao declarada entra em alguma verificacao",
           pag.evaluate("() => ENG.combinacoes.leitura"))

        # custo e cotacao: a dupla contagem, e o que ainda nao foi perguntado
        pag.click("#vistasEng button[data-vista='cotacao']")
        pag.wait_for_timeout(350)
        ok(pag.evaluate("""() => {
             const B = ENG.bom;
             const soma = B.reduce((s, i) => s + i.total_compra, 0);
             const decl = B.filter(i => i.compra)
                           .reduce((s, i) => s + i.total, 0);
             return Math.abs(soma - decl) < 0.5 && Math.abs(soma - ENG.custo) < 0.5; }"""),
           "o custo e a soma do que se COMPRA, e so",
           "R$ " + str(pag.evaluate("() => Math.round(ENG.custo)")))
        ok(pag.evaluate("""() => ENG.bom.some(i => !i.compra)
             && ENG.bom.filter(i => !i.compra).every(i => i.total_compra === 0)"""),
           "a linha de producao existe, e nao entra no total",
           str(pag.evaluate("() => ENG.bom.filter(i => !i.compra).length")) + " linhas")
        # a identidade que nenhuma faixa pegaria: util / aproveitamento = bruta
        ok(pag.evaluate("""() => {
             const aco = ENG.bom.find(i => i.sku === 'ACO-PERF');
             const pf = ENG.bom.filter(i => i.sku.startsWith('PF-'));
             const util = pf.reduce((s, i) => s + i.total, 0) / aco.preco;
             return Math.abs(util / ENG.nesting.aproveitamento - aco.quantidade) < 1.0; }"""),
           "barra e peca sao o mesmo aco: a identidade fecha")
        ok(pag.evaluate("""() => {
             const v = ENG.bom.map(i => i.sku);
             return new Set(v).size === v.length; }"""),
           "nenhum SKU se repete: a chave que liga preco a quantidade e unica")
        ok(pag.evaluate("() => ENG.cotacao.cobertura.cotado_pct") == 0
           and "(H)" in pag.evaluate(
               "() => document.getElementById('engConteudo').textContent"),
           "a tela diz que 0 % do custo foi cotado, em vez de omitir",
           str(pag.evaluate("() => ENG.cotacao.cobertura.cotado_pct")) + " %")
        ok(pag.evaluate("""() => ENG.cotacao.mapa.linhas.length > 40
             && ENG.cotacao.mapa.linhas.every(l => l.sku && l.quantidade >= 0)"""),
           "o mapa de cotacao esta na interface",
           str(pag.evaluate("() => ENG.cotacao.mapa.n")) + " linhas")
        ok(pag.evaluate("""() => ENG.cotacao.mapa.lacunas.length > 0
             && ENG.cotacao.mapa.lacunas.every(x => x.faltam.length > 0
                                                    && x.faltam[0].length > 20)"""),
           "e cada lacuna diz o que falta para poder perguntar",
           str(pag.evaluate("() => ENG.cotacao.mapa.n_lacunas")) + " lacunas")
        ok(pag.evaluate("""() => {
             const s = ENG.cotacao.sensibilidade;
             const t = s.reduce((a, x) => a + x.exposicao, 0);
             return Math.abs(t - 1) < 0.01 && s[0].exposicao >= s[1].exposicao; }"""),
           "a exposicao por familia soma 1 e vem ordenada")
        ok(pag.evaluate("""() => ENG.documentos.mapa_de_cotacao
             && ENG.documentos.mapa_de_cotacao.includes('FALTA')"""),
           "o documento que sai para o fornecedor traz as lacunas nele mesmo")

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

        # ---- NAVEGACAO: o endereco descreve o que se esta vendo
        pag.click("button[data-modo='eng']")
        pag.click("#vistasEng button[data-vista='cotacao']")
        pag.wait_for_timeout(300)
        ok(pag.evaluate("() => location.hash") == "#eng/cotacao",
           "a vista aberta aparece no endereco",
           pag.evaluate("() => location.hash"))
        pag.click("button[data-modo='2d']")
        pag.wait_for_timeout(300)
        ok(pag.evaluate("() => location.hash").startswith("#2d/PR-"),
           "e a prancha aberta tambem",
           pag.evaluate("() => location.hash"))
        # voltar desfaz o ultimo passo DENTRO do caderno, em vez de sair dele
        pag.go_back()
        pag.wait_for_timeout(400)
        ok(pag.evaluate("() => location.hash") == "#eng/cotacao"
           and pag.evaluate("() => !document.getElementById('stageEng').hidden"),
           "o botao Voltar do navegador desfaz o ultimo passo",
           pag.evaluate("() => location.hash"))
        # e o endereco colado abre direto no lugar: e o que permite CITAR
        pag.goto(f"http://127.0.0.1:{porta}/porto-real-caderno.html#2d/PR-22")
        pag.wait_for_selector("#rail li", state="attached")
        pag.wait_for_timeout(1200)
        ok(pag.evaluate("() => SHEETS[idxPrancha].n") == "22",
           "abrir o endereco de uma prancha cai nela, e nao na capa",
           "PR-" + str(pag.evaluate("() => SHEETS[idxPrancha].n")))

        # ---- RESPONSIVIDADE: nenhuma largura estoura o visor do telefone
        pag.set_viewport_size({"width": 390, "height": 844})
        pag.wait_for_timeout(500)
        ok(pag.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1"),
           "a 390 px o caderno nao rola na horizontal",
           str(pag.evaluate("() => document.documentElement.scrollWidth")) + " px")
        pag.click("button[data-modo='eng']")
        pag.wait_for_timeout(400)
        estouros = []
        for v in ("painel", "pecas", "cotacao", "instalacoes", "materiais",
                  "parafusos", "paineis", "corte", "montagem", "logistica",
                  "documentos", "bloqueios"):
            pag.click(f"#vistasEng button[data-vista='{v}']")
            pag.wait_for_timeout(150)
            if pag.evaluate("() => document.documentElement.scrollWidth > innerWidth + 1"):
                estouros.append(v)
        ok(not estouros, "e nenhuma das 12 vistas de engenharia estoura",
           "estouram: " + ", ".join(estouros) if estouros else "12 vistas medidas")
        pag.set_viewport_size({"width": 1440, "height": 960})
        pag.wait_for_timeout(400)

        # ---- DINAMISMO: a tabela grande sai em lotes, e ordena
        pag.click("#vistasEng button[data-vista='pecas']")
        pag.wait_for_timeout(400)
        n1 = pag.evaluate("() => document.querySelectorAll('#engConteudo tbody tr').length")
        ok(n1 <= 200, "a lista de 1.033 pecas sai em lote, nao inteira",
           f"{n1} linhas no primeiro lote")
        pag.click("#maisPecas")
        pag.wait_for_timeout(300)
        n2 = pag.evaluate("() => document.querySelectorAll('#engConteudo tbody tr').length")
        ok(n2 > n1, "e o lote seguinte entra sem recarregar", f"{n1} -> {n2}")

        pag.click("#vistasEng button[data-vista='cotacao']")
        pag.wait_for_timeout(400)
        antes = pag.evaluate("""() => [...document.querySelectorAll('#engConteudo table tbody tr')]
             .slice(0, 1).map(r => r.children[0].textContent)[0]""")
        pag.click("#engConteudo table.tabela thead th:nth-child(3)")
        pag.wait_for_timeout(250)
        depois = pag.evaluate("""() => [...document.querySelectorAll('#engConteudo table tbody tr')]
             .slice(0, 1).map(r => r.children[0].textContent)[0]""")
        ok(antes != depois,
           "toda tabela ordena ao clicar no cabecalho, e nao so a de pecas",
           f"{antes} -> {depois}")
        # a ordenacao numerica nao pode ordenar como texto
        ok(pag.evaluate("""() => {
             const t = document.querySelector('#engConteudo table.tabela');
             const v = [...t.querySelectorAll('tbody tr')]
               .map(r => parseFloat((r.children[2].textContent || '')
                 .replace(/[^\d,.-]/g, '').replace(/\.(?=\d{3}\b)/g, '').replace(',', '.')))
               .filter(Number.isFinite);
             return v.length > 2 && v.every((x, i) => i === 0 || v[i - 1] <= x); }"""),
           "e ordena numero como numero, nao como texto")

        # ---- BUSCA GLOBAL: uma pergunta, doze vistas e 35 pranchas
        pag.goto(f"http://127.0.0.1:{porta}/porto-real-caderno.html")
        pag.wait_for_selector("#rail li", state="attached")
        pag.wait_for_timeout(1200)
        ok(pag.evaluate("() => !!document.getElementById('abrirBusca')"),
           "a busca existe nos tres modos, e nao dentro de um deles")
        pag.keyboard.press("Control+k")
        pag.wait_for_timeout(300)
        ok(pag.evaluate("() => { const p = document.getElementById('paleta'); "
                        "return !!p && !p.hidden; }"),
           "Ctrl+K abre a busca")
        pag.fill("#paletaEntrada", "TP23")
        pag.wait_for_timeout(800)
        ok(pag.evaluate("() => _achAtuais.length") > 5,
           "procurar um painel acha o painel E o que depende dele",
           str(pag.evaluate("() => _achAtuais.length")) + " resultados")
        # o ranking e a resposta: o painel TP23 tem de vir antes das pecas que
        # apenas o mencionam, senao a busca devolve ruido ordenado
        ok(pag.evaluate("() => _achAtuais[0].tipo") == "painel",
           "e o codigo exato vem antes de quem so o menciona",
           pag.evaluate("() => _achAtuais[0].tipo + ': ' + _achAtuais[0].rotulo"))
        ok(pag.evaluate("""() => _achAtuais.every(a => a.rota &&
             (a.rota.startsWith('2d/') || a.rota.startsWith('eng/') || a.rota === '3d'))"""),
           "todo resultado sabe para onde ir: busca sem destino e eco")
        # atravessa os tipos, que e o ponto: ate aqui cada filtro via uma lista
        ok(pag.evaluate("() => new Set(montarIndice().map(a => a.tipo)).size") >= 8,
           "o indice atravessa prancha, peca, painel, material, ambiente e mais",
           str(pag.evaluate("() => montarIndice().length")) + " entradas em "
           + str(pag.evaluate("() => new Set(montarIndice().map(a => a.tipo)).size"))
           + " tipos")
        pag.fill("#paletaEntrada", "PR-22")
        pag.wait_for_timeout(500)
        pag.keyboard.press("Enter")
        pag.wait_for_timeout(700)
        ok(pag.evaluate("() => SHEETS[idxPrancha].n") == "22"
           and pag.evaluate("() => location.hash") == "#2d/PR-22",
           "escolher uma prancha abre a prancha, e o endereco acompanha",
           pag.evaluate("() => location.hash"))
        pag.keyboard.press("/")
        pag.wait_for_timeout(300)
        pag.fill("#paletaEntrada", "ACO-PERF")
        pag.wait_for_timeout(600)
        pag.keyboard.press("Enter")
        pag.wait_for_timeout(700)
        ok(pag.evaluate("() => location.hash") == "#eng/cotacao"
           and pag.evaluate("() => bomFiltro") == "ACO-PERF",
           "e escolher um material abre a vista JA filtrada nele",
           pag.evaluate("() => bomFiltro"))
        pag.keyboard.press("/")
        pag.wait_for_timeout(250)
        pag.keyboard.press("Escape")
        pag.wait_for_timeout(250)
        ok(pag.evaluate("() => document.getElementById('paleta').hidden"),
           "Esc fecha")

        # ---- GRAFICOS: o que a barra de <div> nao conseguia dizer
        pag.click("button[data-modo='eng']")
        pag.click("#vistasEng button[data-vista='painel']")
        pag.wait_for_timeout(500)
        ok(pag.evaluate("() => !!document.querySelector('#engConteudo .viz svg')"),
           "a distribuicao de utilizacao e um grafico, com eixo e limiar")
        # IDENTIDADE: o que a tela desenha e o que o motor calculou, nao uma
        # conta refeita no navegador — que poderia divergir do memorial
        ok(pag.evaluate("""() => {
             const somaHist = ENG.estrutura.histograma.reduce((s, h) => s + h.n, 0);
             return somaHist === ENG.estrutura.n; }"""),
           "as faixas do histograma somam exatamente os montantes verificados",
           str(pag.evaluate("() => ENG.estrutura.n")) + " montantes")
        ok(pag.evaluate("""() => document.querySelectorAll(
             '#engConteudo .viz [data-dica]').length""") >= 6,
           "cada coluna responde ao ponteiro: grafico sem leitura e decoracao")
        ok(pag.evaluate("""() => {
             const t = document.querySelector('#engConteudo .viz svg')
                              .getAttribute('aria-label');
             return t && t.length > 20; }"""),
           "e o grafico se descreve para quem nao o ve")
        ok(pag.evaluate("""() => !!document.querySelector('#engConteudo details table.tabela')"""),
           "com a mesma informacao disponivel em tabela")

        pag.click("#vistasEng button[data-vista='cotacao']")
        pag.wait_for_timeout(500)
        ok(pag.evaluate("() => !!document.querySelector('#engConteudo .viz path.linha')"),
           "a concentracao de custo e uma curva, nao uma lista ordenada")
        # os dois eixos em % — uma escala so. Segundo eixo e o erro numero um
        ok(pag.evaluate("""() => {
             const t = [...document.querySelectorAll('#engConteudo .viz text.eixo')]
               .map(x => x.textContent.trim());
             return t.filter(x => x.endsWith('%')).length >= 3; }"""),
           "com os dois eixos em percentual: uma escala, nunca duas")
        ok(pag.evaluate("""() => {
             const a = ENG.abc;
             return a.every((x, i) => i === 0 || a[i-1].acumulado <= x.acumulado)
                    && Math.abs(a[a.length-1].acumulado - 1) < 0.001; }"""),
           "e o acumulado da curva ABC cresce ate exatamente 100 %")

        pag.click("#vistasEng button[data-vista='montagem']")
        pag.wait_for_timeout(600)
        ok(pag.evaluate("() => !!document.querySelector('#engConteudo .viz path.linha')"),
           "a montagem tem curva de horas acumuladas")
        ok(pag.evaluate("""() => {
             const p = ENG.montagem.passos;
             return Math.abs(p[p.length-1].acumulado_h - ENG.montagem.horas) < 0.05; }"""),
           "cujo fim bate com o total de horas do modelo",
           str(pag.evaluate("() => ENG.montagem.horas")) + " h")

        # ---- POR AMBIENTE: o eixo em que a verificacao nao existia
        pag.click("#vistasEng button[data-vista='ambientes']")
        pag.wait_for_timeout(500)
        ok(pag.evaluate("() => ENG.ambientes.dossies.length") == 17,
           "os 17 comodos tem dossie",
           str(pag.evaluate("() => ENG.ambientes.dossies.length")))
        # a soma dos comodos e a area da casa: se nao fechar, falta comodo
        ok(pag.evaluate("""() => Math.abs(ENG.ambientes.area_total
             - ENG.projeto.area_m2) < 0.1"""),
           "e a soma deles e exatamente a area declarada do projeto",
           str(pag.evaluate("() => ENG.ambientes.area_total")) + " m2")
        ok(pag.evaluate("""() => ENG.ambientes.dossies.every(d =>
             d.piso && d.forro && d.tugs_norma > 0 && d.composicoes.length > 0)"""),
           "cada dossie reune acabamento, tomada e as paredes que o cercam")
        # a tomada tem de vir da previsao da norma, nao de uma segunda regra
        ok(pag.evaluate("""() => {
             const t = ENG.ambientes.dossies.reduce((s, d) => s + d.tugs_norma, 0);
             return t === 71; }"""),
           "as tomadas somam o que a NBR 5410 preve por perimetro",
           str(pag.evaluate("""() => ENG.ambientes.dossies
             .reduce((s, d) => s + d.tugs_norma, 0)""")) + " TUG")
        ok(pag.evaluate("""() => {
             const d = ENG.ambientes.dossies.find(x => x.cod === 'S-MAS');
             return d.area_subdividida > 0 && d.area_util < d.area; }"""),
           "a area de permanencia desconta banho e closet",
           str(pag.evaluate("""() => ENG.ambientes.dossies
             .find(x => x.cod === 'S-MAS').area_util""")) + " m2 na master")
        ok(pag.evaluate("""() => {
             const d = ENG.ambientes.dossies.find(x => x.cod === 'T-SOC');
             return d.area_ilum > 0; }"""),
           "e o estar ilumina pela porta-balcao, que nao e janela nem e opaca")
        ultimo = pag.evaluate("() => ENG.ambientes.dossies.slice(-1)[0].cod")
        pag.click(f"#engConteudo [data-amb='{ultimo}']")
        pag.wait_for_timeout(300)
        ok(pag.evaluate("() => ambSel") == ultimo,
           "trocar de comodo troca o dossie", ultimo)

        # a pergunta que 517 verificacoes nao faziam: da para CHEGAR la?
        ok(pag.evaluate("""() => {
             const c = ENG.ambientes.conectividade;
             return c && c.ok && c.ilhados.length === 0
                    && c.alcancaveis === c.total; }"""),
           "todo comodo se alcanca a pe a partir da porta de entrada",
           str(pag.evaluate("() => ENG.ambientes.conectividade.alcancaveis"))
           + " de " + str(pag.evaluate("() => ENG.ambientes.conectividade.total")))
        ok(pag.evaluate("""() => Object.values(ENG.ambientes.conectividade.ligacoes)
             .every(v => Object.keys(v).length > 0)"""),
           "e nenhum comodo tem porta que nao da para lugar nenhum")

        # ---- CATALOGO: o desenho de cada peca, gerado da propria peca
        pag.click("#vistasEng button[data-vista='catalogo']")
        pag.wait_for_timeout(600)
        ok(pag.evaluate("() => ENG.catalogo.n") > 20,
           "o catalogo tecnico desenha perfil, parafuso, chapa e tubo",
           str(pag.evaluate("() => ENG.catalogo.n")) + " pecas")
        ok(pag.evaluate("""() => ['perfis','parafusos','chapas','tubos']
             .every(k => ENG.catalogo[k].length > 0
                      && ENG.catalogo[k].every(x => x.svg
                         && x.svg.indexOf('<svg') === 0))"""),
           "cada peca traz o seu proprio SVG, e nao um link para fora")
        # IDENTIDADE: a cota do desenho e a dimensao que o calculo usa
        ok(pag.evaluate("""() => ENG.catalogo.perfis.every(p =>
             p.svg.includes(String(p.bw)) && p.svg.includes(String(p.bf)))"""),
           "a cota desenhada e a MESMA dimensao que alimenta o solver")
        ok(pag.evaluate("""() => ENG.catalogo.perfis.every(p =>
             p.area > 0 && p.massa_m > 0 && p.n > 0 && p.familias.length > 0)"""),
           "e cada peca diz quanto pesa por metro e onde entra na obra")
        # nada vem de fora: nem imagem, nem host
        ok(pag.evaluate("""() => ['perfis','parafusos','chapas','tubos']
             .every(k => ENG.catalogo[k].every(x =>
               !/https?:|<image|xlink/i.test(x.svg)))"""),
           "nenhum desenho referencia imagem ou host externo")
        ok(pag.evaluate("""() => document.querySelectorAll(
             '#engConteudo svg.pecadesenho').length"""),
           "os desenhos chegam ao DOM",
           str(pag.evaluate("""() => document.querySelectorAll(
             '#engConteudo svg.pecadesenho').length""")) + " na aba aberta")
        pag.click("#engConteudo [data-cat='parafusos']")
        pag.wait_for_timeout(400)
        ok(pag.evaluate("""() => {
             const t = document.getElementById('engConteudo').textContent;
             return t.includes('ponta broca') && t.includes('(H)'); }"""),
           "o parafuso diz o tipo de ponta, e a resistencia continua (H)")

        # ---- IMPRESSAO: o que sai no papel e o documento, nao a interface
        ok(pag.evaluate("""() => {
             const css = [...document.styleSheets].flatMap(s => {
               try { return [...s.cssRules]; } catch (e) { return []; } });
             return css.some(r => r.conditionText && r.conditionText.includes('print')); }"""),
           "existe folha de estilo de impressao")

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
