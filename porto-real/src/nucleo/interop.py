"""INTEROP — exportacao e importacao (secoes 137 a 139).

O que sai daqui e formato ABERTO, e a razao e pratica: DWG e RVT sao
proprietarios e nao se escrevem sem licenca. Prometer DWG e entregar um arquivo
que o AutoCAD abre com aviso seria pior que nao prometer — por isso eles tem
ADAPTADOR DECLARADO, que falha dizendo o que falta, em vez de implementacao
aproximada.

A verificacao central de todo formato e a ida e volta: exportar e reimportar tem
de devolver a mesma geometria. Formato que so escreve nao se audita.
"""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass

FORMATOS_ESCRITA = ("DXF", "IFC", "OBJ", "STL", "CSV", "JSON", "XML", "SVG")
FORMATOS_LEITURA = ("DXF", "IFC", "CSV", "JSON", "XML")
PROPRIETARIOS = {
    "DWG": "formato binario proprietario da Autodesk; escrever exige a "
           "biblioteca licenciada RealDWG ou equivalente",
    "RVT": "formato binario proprietario do Revit, sem especificacao publica",
    "SKP": "formato proprietario do SketchUp; a SDK e licenciada",
}


class SemAdaptador(Exception):
    """Formato que este projeto NAO escreve. Falha explicita, nao aproximacao."""


def exportar(formato: str, *a, **k):
    f = formato.upper()
    if f in PROPRIETARIOS:
        raise SemAdaptador(f"{f}: {PROPRIETARIOS[f]}. Use IFC ou DXF, que sao "
                           f"abertos e este projeto escreve de verdade.")
    fn = globals().get(f"_para_{f.lower()}")
    if fn is None:
        raise SemAdaptador(f"formato '{formato}' nao implementado")
    return fn(*a, **k)


# ---------------------------------------------------------------------- DXF
def _para_dxf(entidades: list, layer_padrao: str = "ESTRUTURA") -> str:
    """DXF R12 ASCII: LINE, LWPOLYLINE e TEXT. Formato publicado e legivel."""
    out = ["0", "SECTION", "2", "ENTITIES"]
    for e in entidades:
        t = e.get("tipo", "line")
        lay = e.get("layer", layer_padrao)
        if t == "line":
            out += ["0", "LINE", "8", lay,
                    "10", f"{e['x1']:.4f}", "20", f"{e['y1']:.4f}", "30", "0.0",
                    "11", f"{e['x2']:.4f}", "21", f"{e['y2']:.4f}", "31", "0.0"]
        elif t == "poly":
            p = e["pontos"]
            out += ["0", "LWPOLYLINE", "8", lay, "90", str(len(p)),
                    "70", "1" if e.get("fechado") else "0"]
            for x, y in p:
                out += ["10", f"{x:.4f}", "20", f"{y:.4f}"]
        elif t == "text":
            out += ["0", "TEXT", "8", lay,
                    "10", f"{e['x']:.4f}", "20", f"{e['y']:.4f}", "30", "0.0",
                    "40", f"{e.get('h', 2.5):.4f}", "1", str(e["texto"])]
    out += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(out) + "\n"


def de_dxf(txt: str) -> list:
    """Leitor do proprio dialeto: pares (codigo, valor)."""
    linhas = txt.splitlines()
    pares = [(linhas[i].strip(), linhas[i + 1].strip())
             for i in range(0, len(linhas) - 1, 2)]
    ents, atual = [], None
    for cod, val in pares:
        if cod == "0":
            if atual:
                ents.append(atual)
            atual = dict(tipo=val.lower()) if val in ("LINE", "LWPOLYLINE",
                                                      "TEXT") else None
            continue
        if atual is None:
            continue
        atual.setdefault("cods", []).append((cod, val))
    if atual:
        ents.append(atual)
    saida = []
    for e in ents:
        c = dict(e.get("cods", []))
        if e["tipo"] == "line":
            saida.append(dict(tipo="line", layer=c.get("8", ""),
                              x1=float(c["10"]), y1=float(c["20"]),
                              x2=float(c["11"]), y2=float(c["21"])))
        elif e["tipo"] == "text":
            saida.append(dict(tipo="text", layer=c.get("8", ""),
                              x=float(c["10"]), y=float(c["20"]),
                              texto=c.get("1", "")))
        else:
            xs = [float(v) for k, v in e["cods"] if k == "10"]
            ys = [float(v) for k, v in e["cods"] if k == "20"]
            saida.append(dict(tipo="poly", layer=c.get("8", ""),
                              pontos=list(zip(xs, ys))))
    return saida


# ---------------------------------------------------------------------- IFC
def _para_ifc(projeto: dict, elementos: list) -> str:
    """IFC4 em arquivo STEP — subconjunto suficiente para trocar geometria.

    Entra IfcProject, IfcSite, IfcBuilding, IfcBuildingStorey e um IfcMember por
    peca, com posicao e comprimento. Nao entra material, propriedade nem
    relacao de agregacao completa: o subconjunto e declarado, nao disfarcado.
    """
    L, n = [], [0]

    def add(s):
        n[0] += 1
        L.append(f"#{n[0]}= {s};")
        return n[0]

    unidade = add("IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.)")
    ctx_un = add(f"IFCUNITASSIGNMENT((#{unidade}))")
    org = add(f"IFCORGANIZATION($,'{projeto.get('empresa','—')}',$,$,$)")
    app = add(f"IFCAPPLICATION(#{org},'R23','Porto Real','PORTOREAL')")
    p0 = add("IFCCARTESIANPOINT((0.,0.,0.))")
    eixo = add(f"IFCAXIS2PLACEMENT3D(#{p0},$,$)")
    ctx = add(f"IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#{eixo},$)")
    proj = add(f"IFCPROJECT('{_guid(1)}',$,'{projeto.get('nome','projeto')}',"
               f"$,$,$,$,(#{ctx}),#{ctx_un})")
    plc = add(f"IFCLOCALPLACEMENT($,#{eixo})")
    site = add(f"IFCSITE('{_guid(2)}',$,'Terreno',$,$,#{plc},$,$,.ELEMENT.,"
               f"$,$,$,$,$)")
    bld = add(f"IFCBUILDING('{_guid(3)}',$,'{projeto.get('nome','')}',$,$,"
              f"#{plc},$,$,.ELEMENT.,$,$,$)")
    pisos = {}
    for pav in sorted({e.get("pav", "T") for e in elementos}):
        pisos[pav] = add(f"IFCBUILDINGSTOREY('{_guid(10+len(pisos))}',$,"
                         f"'Pavimento {pav}',$,$,#{plc},$,$,.ELEMENT.,0.)")
    membros = []
    for i, e in enumerate(elementos, 1):
        pt = add(f"IFCCARTESIANPOINT(({e.get('x',0.0):.2f},"
                 f"{e.get('y',0.0):.2f},{e.get('z',0.0):.2f}))")
        ax = add(f"IFCAXIS2PLACEMENT3D(#{pt},$,$)")
        lp = add(f"IFCLOCALPLACEMENT(#{plc},#{ax})")
        membros.append(add(
            f"IFCMEMBER('{_guid(100+i)}',$,'{e['cod']}','{e.get('perfil','')}',"
            f"$,#{lp},$,'{e.get('familia','')}')"))
    cab = ("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('ViewDefinition "
           "[CoordinationView]'),'2;1');\n"
           f"FILE_NAME('{projeto.get('nome','projeto')}.ifc','{projeto.get('data','')}',"
           f"(''),(''),'Porto Real','Porto Real','');\n"
           "FILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n")
    return cab + "\n".join(L) + "\nENDSEC;\nEND-ISO-10303-21;\n"


def _guid(n: int) -> str:
    tab = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"
    s, v = "", n * 2654435761 % (64 ** 22)
    for _ in range(22):
        s = tab[v % 64] + s
        v //= 64
    return s


def de_ifc(txt: str) -> dict:
    """Le o cabecalho e conta as entidades — o suficiente para a ida e volta."""
    if "IFC4" not in txt:
        raise ValueError("nao e IFC4")
    linhas = [l for l in txt.splitlines() if l.startswith("#")]
    tipos = {}
    for l in linhas:
        t = l.split("= ", 1)[1].split("(", 1)[0]
        tipos[t] = tipos.get(t, 0) + 1
    return dict(entidades=len(linhas), tipos=tipos,
                membros=tipos.get("IFCMEMBER", 0))


# ------------------------------------------------------------------ OBJ/STL
def _para_obj(solidos: list) -> str:
    out, base = ["# Porto Real"], 1
    for s in solidos:
        x, y, z = s["p"]
        dx, dy, dz = [v / 2 for v in s["s"]]
        vs = [(x - dx, y - dy, z - dz), (x + dx, y - dy, z - dz),
              (x + dx, y + dy, z - dz), (x - dx, y + dy, z - dz),
              (x - dx, y - dy, z + dz), (x + dx, y - dy, z + dz),
              (x + dx, y + dy, z + dz), (x - dx, y + dy, z + dz)]
        for v in vs:
            out.append(f"v {v[0]:.2f} {v[1]:.2f} {v[2]:.2f}")
        for f in ((1, 2, 3, 4), (5, 6, 7, 8), (1, 2, 6, 5), (2, 3, 7, 6),
                  (3, 4, 8, 7), (4, 1, 5, 8)):
            out.append("f " + " ".join(str(base + i - 1) for i in f))
        base += 8
    return "\n".join(out) + "\n"


def _para_stl(solidos: list, nome: str = "portoreal") -> str:
    out = [f"solid {nome}"]
    for s in solidos:
        x, y, z = s["p"]
        dx, dy, dz = [v / 2 for v in s["s"]]
        v = [(x - dx, y - dy, z - dz), (x + dx, y - dy, z - dz),
             (x + dx, y + dy, z - dz), (x - dx, y + dy, z - dz),
             (x - dx, y - dy, z + dz), (x + dx, y - dy, z + dz),
             (x + dx, y + dy, z + dz), (x - dx, y + dy, z + dz)]
        tris = ((0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5),
                (0, 5, 1), (1, 5, 6), (1, 6, 2), (2, 6, 7), (2, 7, 3),
                (3, 7, 4), (3, 4, 0))
        for t in tris:
            out.append("facet normal 0 0 0\n outer loop")
            for i in t:
                out.append(f"  vertex {v[i][0]:.2f} {v[i][1]:.2f} {v[i][2]:.2f}")
            out.append(" endloop\nendfacet")
    out.append(f"endsolid {nome}")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------- CSV/JSON/XML
def _para_csv(linhas: list, cabec: list) -> str:
    def esc(v):
        s = str(v)
        return f'"{s}"' if ("," in s or '"' in s) else s
    out = [",".join(cabec)]
    for l in linhas:
        out.append(",".join(esc(l.get(c, "")) for c in cabec))
    return "\n".join(out) + "\n"


def de_csv(txt: str) -> list:
    linhas = [l for l in txt.splitlines() if l.strip()]
    cab = linhas[0].split(",")
    out = []
    for l in linhas[1:]:
        vals, atual, dentro = [], "", False
        for ch in l:
            if ch == '"':
                dentro = not dentro
            elif ch == "," and not dentro:
                vals.append(atual)
                atual = ""
            else:
                atual += ch
        vals.append(atual)
        out.append(dict(zip(cab, vals)))
    return out


def _para_json(dados) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=1)


def _para_xml(raiz: str, itens: list, tag: str = "item") -> str:
    r = ET.Element(raiz)
    for i in itens:
        e = ET.SubElement(r, tag)
        for k, v in i.items():
            e.set(str(k), str(v))
    return ET.tostring(r, encoding="unicode")


def de_xml(txt: str) -> list:
    r = ET.fromstring(txt)
    return [dict(e.attrib) for e in r]
