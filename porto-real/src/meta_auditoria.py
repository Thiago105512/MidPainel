"""META-AUDITORIA — procura o FORMATO dos defeitos, nao um defeito por vez.

Depois de 96 defeitos documentados, eles cabem em cinco moldes:
  1. duas fontes para o mesmo fato (39, 62, 69, 88, 90, 96, 97, 98)
  2. literal que envelhece (71 tomadas, 6.150 de platibanda, "8 cenas", 7.200)
  3. existe no modelo, nao chega ao desenho / cena / orcamento (79, 87, 89, 99, 100)
  4. funcao duplicada com semantica "quase" igual (_brl x3, _geom x2, _face_do_vao x2)
  5. premissa errada — so olho humano acha; este modulo nao promete isso

As auditorias do programa verificam FATOS. Esta verifica MOLDES:
  - MUTACAO: muda um valor do caso NUM SUBPROCESSO (as constantes derivadas
    sao calculadas na importacao; mudar em memoria nao propaga — foi assim que
    a primeira versao deste teste acusou a si mesma) e mede quem se mexe.
    Consumidor que deveria mexer e ficou parado tem uma segunda fonte.
  - LITERAIS: numero escrito fora do caso igual a um valor distintivo do caso.
  - ALCANCE: cada entidade com codigo chega a uma prancha? a cena 3D?
  - DUPLICADAS: funcao privada com o mesmo nome em mais de um modulo produtor.

Roda-se depois de cada revisao (auditoria 138 no programa e `--mutacao` na CI).
O que ela nao acha, a folha de contato e o proprietario acham — e e por isso
que o metodo tem os tres.
"""
from __future__ import annotations

import ast, glob, json, os, re, sys, collections, subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "..", "out")
CASO = os.path.join(AQUI, "projetos", "porto_real.py")

# modulos que RECOMPUTAM de proposito (auditoria nao confere desenho com desenho)
# ou que sao o proprio instrumento; neles um nome repetido nao e defeito.
EXCLUIR = ("auditoria.py", "auditoria2.py", "auditoria3.py", "viewer_teste.py",
           "meta_auditoria.py", "projeto.py", "programa.py")


# ---------------------------------------------------------------- 1. mutacao
# (nome, trecho exato no caso, substituto, consumidores que DEVEM mexer)
MUTACOES = [
    # (nome, trecho exato no caso, substituto, DEVEM mexer, PODEM mexer)
    ("PE_DIREITO", "PE_DIREITO = 2_900", "PE_DIREITO = 3_100",
     {"gesso", "placa", "tinta", "massa", "pecas", "custo", "solidos3d"}, {"luminarias"}),
    ("MONTANTE_ESPACAMENTO", "MONTANTE_ESPACAMENTO = 600", "MONTANTE_ESPACAMENTO = 400",
     {"pecas", "massa", "u_parede", "custo"}, {"gesso", "placa"}),   # chapa arredonda por painel
    ("RADIER.espessura", "espessura=180,            # mm, conferida em geotecnia.py",
     "espessura=230,            # mm, conferida em geotecnia.py", {"custo"}, set()),
    ("PISCINA.lamina_m2", "lamina_m2=17.82", "lamina_m2=22.82", {"retencao", "custo"}, set()),
    ("ABSORTANCIA", "ABSORTANCIA = 0.30", "ABSORTANCIA = 0.60", {"carga_termica"}, set()),
    ("LOTE_P", "LOTE_P = 40_000", "LOTE_P = 44_000", {"retencao", "custo"}, set()),
]

_MEDIR = r'''
import sys, json, types
patches = json.loads(sys.argv[1]); caminho = sys.argv[2]
src = open(caminho, encoding="utf-8").read()
for velho, novo in patches:
    assert src.count(velho) == 1, ("trecho nao unico no caso", velho)
    src = src.replace(velho, novo)
import projetos
mod = types.ModuleType("projetos.porto_real"); mod.__file__ = caminho
sys.modules["projetos.porto_real"] = mod; projetos.porto_real = mod
exec(compile(src, caminho, "exec"), mod.__dict__)
import projeto as pj, fixture, modelo3d
import nucleo.luminotecnica as lu, nucleo.termica as tm, nucleo.pluvial as pl
r = fixture.liberacao()
d = modelo3d.exportar()
bom = {i.sku: i.quantidade for i in r["bom"]}
def _w(c):
    r = pj.carga_termica(c["amb"], c.get("pessoas", 2), c.get("equip", 0))
    return r.get("w") or r.get("total_w") or r.get("btu") or 0 if isinstance(r, dict) else float(r)
carga = round(sum(_w(c) for c in pj.CLIMATIZACAO))
print(json.dumps(dict(
    custo=round(sum(i.total for i in r["bom"] if i.compra)),
    pecas=len(r["pecas"]), massa=round(r["massa_comprada"]),
    gesso=bom.get("GESSO-12,5"), placa=bom.get("PLCIM-10"),
    tinta=bom.get("PIN-TINTA"), piso=bom.get("REV-PISO"),
    luminarias=lu.levantar(pj)["n_geral"],
    u_parede=tm.levantar(pj)[0]["u"],
    retencao=pl.retencao(pj)["volume_m3"],
    solidos3d=sum(len(d[k]) for k in ("terreo", "superior", "mob", "luz")),
    vidro=bom.get("ESQ-VIDRO"), tug=bom.get("ELE-TUG"),
    forro=r["camadas"]["planos"]["forro"]["area"],
    carga_termica=carga,
)))
'''


def _medir(patches: list) -> dict:
    p = subprocess.run([sys.executable, "-c", _MEDIR, json.dumps(patches), CASO],
                       cwd=AQUI, capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip().splitlines()[-1] if p.stderr.strip() else "falhou")
    return json.loads(p.stdout.strip().splitlines()[-1])


def teste_de_mutacao() -> list[dict]:
    """Muda um valor do caso (em subprocesso) e mede quem se mexe."""
    base = _medir([])
    out = []
    for nome, velho, novo, esperados, tolerados in MUTACOES:
        try:
            m = _medir([[velho, novo]])
        except Exception as e:
            out.append(dict(mutacao=nome, erro=str(e)[:120])); continue
        moveu = {k for k in base if base[k] != m[k]}
        out.append(dict(mutacao=nome, moveu=sorted(moveu),
                        parados_suspeitos=sorted(esperados - moveu),
                        inesperados=sorted(moveu - esperados - tolerados)))
    return out


# ------------------------------------------------------- 2. literais magicos
# So valores DISTINTIVOS: 600 (modulacao) e 2.400 (recuo = modulo) coincidem com
# meio mundo; 17 e 41 sao contagens. O que sobra e o que envelhece sem aviso.
LITERAIS_DO_CASO = ("PE_DIREITO", "RECUO_FRENTE", "TOPO_PLATIBANDA", "LOTE_P")


def literais_magicos() -> list[dict]:
    """Numero escrito em codigo (fora do caso e das auditorias) igual a um valor do caso."""
    import projetos.porto_real as pj
    valores = {}
    for nome in LITERAIS_DO_CASO:
        v = getattr(pj, nome, None)
        if isinstance(v, (int, float)):
            valores[int(v)] = nome
    achados = []
    for f in sorted(glob.glob(os.path.join(AQUI, "*.py")) + glob.glob(os.path.join(AQUI, "nucleo", "*.py"))):
        if os.path.basename(f) in EXCLUIR:
            continue
        try:
            arv = ast.parse(open(f, encoding="utf-8").read())
        except SyntaxError:
            continue
        for n in ast.walk(arv):
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
                v = int(n.value) if float(n.value).is_integer() else None
                if v in valores:
                    achados.append(dict(arquivo=os.path.relpath(f, AQUI), linha=n.lineno,
                                        valor=v, igual_a=valores[v]))
    return achados


# --------------------------------------------- 3. entidade -> onde ela chega
# listas cujo item a cena 3D desenha; as outras chegam so a prancha
NA_CENA = {"LOUCAS", "ARMARIOS", "LAYOUT", "BANCADAS", "BRISES", "PILARES",
           "VENTILADORES", "EQUIPAMENTOS", "TECNICOS"}


def alcance_das_entidades() -> list[dict]:
    """Cada codigo declarado no caso: esta na cena 3D? numa prancha?"""
    import projetos.porto_real as pj, modelo3d
    listas = {
        "LOUCAS": [l["cod"] for l in pj.LOUCAS], "ARMARIOS": [a["cod"] for a in pj.ARMARIOS],
        "LAYOUT": [l["cod"] for l in pj.LAYOUT], "BANCADAS": [b["cod"] for b in pj.BANCADAS],
        "RALOS": [r["cod"] for r in pj.RALOS], "TECNICOS": [t["cod"] for t in pj.TECNICOS],
        "EXAUSTAO": [e["cod"] for e in pj.EXAUSTAO], "BRISES": [b["cod"] for b in pj.BRISES],
        "PILARES": [p["cod"] for p in pj.PILARES],
        "EQUIPAMENTOS": [e["cod"] for e in pj.EQUIPAMENTOS],
        "ILUMINACAO_FACHADA": [f["cod"] for f in pj.ILUMINACAO_FACHADA],
        "VENTILADORES": [v["cod"] for v in pj.VENTILADORES],
        "VIGAS": [v["cod"] for v in pj.VIGAS],
    }
    # tecnicos internos e rasantes nao sao volume: declarado, nao esquecido
    sem_volume = {t["cod"] for t in pj.TECNICOS if t.get("zona") == "INT" or t.get("rasante")}
    d = modelo3d.exportar()
    cena = set()
    for k in ("terreo", "superior", "lajes", "platibandas", "externo", "mob", "escada", "luz", "lsf"):
        for b in d.get(k, []):
            for campo in ("amb", "cod"):
                if b.get(campo):
                    cena.add(str(b[campo]))
    svgs = [open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(OUT, "PR-*.svg"))]
    todos_svg = "\n".join(svgs)
    out = []
    for lista, cods in listas.items():
        for c in cods:
            out.append(dict(lista=lista, cod=c, cena=c in cena, prancha=c in todos_svg,
                            esperado_cena=lista in NA_CENA and c not in sem_volume))
    return out, len(svgs)


# ------------------------------------------------ 4. funcoes duplicadas
def funcoes_duplicadas() -> list[dict]:
    por_nome = collections.defaultdict(list)
    for f in glob.glob(os.path.join(AQUI, "nucleo", "*.py")) + glob.glob(os.path.join(AQUI, "*.py")):
        if os.path.basename(f) in EXCLUIR:
            continue
        try:
            arv = ast.parse(open(f, encoding="utf-8").read())
        except SyntaxError:
            continue
        for n in arv.body:
            if isinstance(n, ast.FunctionDef) and n.name.startswith("_") and not n.name.startswith("__"):
                por_nome[n.name].append(os.path.relpath(f, AQUI))
    return [dict(funcao=k, arquivos=v) for k, v in sorted(por_nome.items()) if len(v) > 1]


def moldes(com_mutacao: bool = False) -> dict:
    """Tudo em um dicionario, para a auditoria 138."""
    alc, n_svg = alcance_das_entidades()
    return dict(literais=literais_magicos(), alcance=alc, n_svg=n_svg,
                duplicadas=funcoes_duplicadas(),
                mutacao=teste_de_mutacao() if com_mutacao else None)


def main(com_mutacao: bool):
    print("=" * 72); print("META-AUDITORIA — moldes de defeito"); print("=" * 72)
    if com_mutacao:
        print("\n1. MUTACAO — muda o caso (em subprocesso), quem se mexe?")
        for m in teste_de_mutacao():
            if "erro" in m:
                print(f"   ERRO {m['mutacao']:22s} {m['erro']}"); continue
            flag = "!!" if m["parados_suspeitos"] else "ok"
            print(f"   {flag} {m['mutacao']:22s} moveu {m['moveu']}")
            if m["parados_suspeitos"]: print(f"      PARADOS (suspeitos de segunda fonte): {m['parados_suspeitos']}")
            if m["inesperados"]: print(f"      moveram sem eu esperar: {m['inesperados']}")
    print("\n2. LITERAIS iguais a valores do caso, fora do caso")
    lit = literais_magicos()
    for a in lit:
        print(f"   {a['arquivo']}:{a['linha']}  {a['valor']} = {a['igual_a']}")
    print(f"   total {len(lit)}")
    print("\n3. ALCANCE — entidade do caso que nao chega a cena / prancha")
    al, n_svg = alcance_das_entidades()
    faltas = [a for a in al if not a["prancha"] or (a["esperado_cena"] and not a["cena"])]
    porl = collections.defaultdict(list)
    for a in faltas:
        porl[a["lista"]].append(f"{a['cod']}{'' if a['cena'] or not a['esperado_cena'] else '[-3D]'}{'' if a['prancha'] else '[-PR]'}")
    for l, cs in porl.items(): print(f"   {l:18s} {', '.join(cs)}")
    print(f"   {len(al)} entidades, {len(faltas)} com lacuna ({n_svg} pranchas lidas)")
    print("\n4. FUNCOES privadas com o mesmo nome em mais de um modulo produtor")
    dup = funcoes_duplicadas()
    for d in dup: print(f"   {d['funcao']:22s} {d['arquivos']}")
    print(f"   total {len(dup)}")


if __name__ == "__main__":
    main("--mutacao" in sys.argv)
