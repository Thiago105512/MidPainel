"""RENDER APROXIMADO — a mesma geometria, num renderizador de verdade (R66).

Le out/porto-real.obj (as caixas da cena, exportadas por modelo3d.exportar_obj),
atribui materiais por TIPO (o nome do material do OBJ e "<tipo>_<cor>"), poe o
sol de Manaus na hora da vista, e fotografa das mesmas cameras que
perspectivas.py derivou (out/perspectivas.json). Cycles, CPU, com denoise.

E aproximado por construcao: caixas nao tem textura de verdade, nao ha
vegetacao, nem vizinhos. O que e verdadeiro: proporcao, vao, sombra, vidro,
materiais declarados em FACHADA_MATERIAIS. O que e ilustracao: o resto.

    python3 render_blender.py ext-270 ext-090 aer-225 T-SOC   [--amostras=96]
"""
from __future__ import annotations

import json
import math
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(AQUI, "..", "out"))
LAT = -3.1                      # Manaus
EXPOSICAO = float(os.environ.get("RENDER_EXPOSICAO", "-5.0"))   # ceu fisico e brilhante


def sol(hora: float) -> tuple[float, tuple]:
    """(elevacao rad, vetor unitario casa->sol em coordenadas do MODELO) no equinocio.

    Modelo: +x = norte, +y = oeste, +z = cima. Azimute pela formula classica
    tan A = sin H / (cos H sin lat - tan decl cos lat), A medido do sul."""
    H = math.radians(15 * (hora - 12))
    lat = math.radians(LAT)
    alt = math.asin(math.cos(lat) * math.cos(H))
    A = math.atan2(math.sin(H), math.cos(H) * math.sin(lat))      # do sul, oeste +
    az = A + math.pi                                               # do norte, leste +
    E, N, U = math.sin(az) * math.cos(alt), math.cos(az) * math.cos(alt), math.sin(alt)
    return alt, (N, -E, U)


def material(bpy, nome: str, cor_hex: str):
    """Material por tipo. Tudo Principled, com uma textura procedural onde a
    superficie real tem juntas ou ripas."""
    tipo = nome.split("_")[0]
    r, g, b = (int(cor_hex[i:i + 2], 16) / 255 for i in (0, 2, 4))
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    out = nt.nodes["Material Output"]
    bsdf.inputs["Base Color"].default_value = (r ** 2.2, g ** 2.2, b ** 2.2, 1)
    bsdf.inputs["Roughness"].default_value = 0.75

    def bump(escala, forca, tipo_tex="NOISE"):
        tex = nt.nodes.new("ShaderNodeTexNoise" if tipo_tex == "NOISE" else "ShaderNodeTexWave")
        if tipo_tex == "NOISE":
            tex.inputs["Scale"].default_value = escala
            tex.inputs["Detail"].default_value = 6
        else:
            tex.inputs["Scale"].default_value = escala
            tex.wave_type = "BANDS"
            tex.bands_direction = "Z"
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = forca
        nt.links.new(tex.outputs["Fac"] if tipo_tex == "NOISE" else tex.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
        return tex

    if tipo in ("parede", "platibanda") and cor_hex.lower() == "ebe7e0":
        # mineral claro de grande formato 1.200 x 2.400 com junta seca de 6 mm:
        # a junta e o que faz a placa ler como placa
        bsdf.inputs["Roughness"].default_value = 0.8
        br = nt.nodes.new("ShaderNodeTexBrick")
        br.inputs["Scale"].default_value = 1.0
        br.inputs["Mortar Size"].default_value = 0.006
        br.inputs["Brick Width"].default_value = 1.2
        br.inputs["Row Height"].default_value = 2.4
        br.inputs["Color1"].default_value = (r ** 2.2, g ** 2.2, b ** 2.2, 1)
        br.inputs["Color2"].default_value = (r ** 2.2, g ** 2.2, b ** 2.2, 1)
        br.inputs["Mortar"].default_value = (0.25, 0.24, 0.23, 1)
        co = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(co.outputs["Object"], br.inputs["Vector"])
        nt.links.new(br.outputs["Color"], bsdf.inputs["Base Color"])
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = 0.5
        nt.links.new(br.outputs["Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    elif tipo in ("parede", "muro", "platibanda", "laje", "cobertura"):
        bsdf.inputs["Roughness"].default_value = 0.85
        bump(40.0, 0.08)                                   # reboco pintado
    elif tipo == "vao" and cor_hex.lower() in ("8fc4dd", "9dd0e8", "8ec4dc"):
        # vidro: para o raio de sombra, transparente (senao o interior fica escuro)
        bsdf.inputs["Base Color"].default_value = (0.85, 0.93, 0.97, 1)
        bsdf.inputs["Roughness"].default_value = 0.02
        bsdf.inputs["Transmission Weight"].default_value = 1.0
        bsdf.inputs["IOR"].default_value = 1.5
        lp = nt.nodes.new("ShaderNodeLightPath")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Shadow Ray"], mix.inputs["Fac"])
        nt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
        nt.links.new(tr.outputs["BSDF"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    elif tipo == "vao" and cor_hex.lower() == "4a4f55":
        bsdf.inputs["Metallic"].default_value = 0.7      # portao ripado de aluminio grafite
        bsdf.inputs["Roughness"].default_value = 0.35
        bump(40.0, 0.7, "WAVE")
    elif tipo == "vao":
        bsdf.inputs["Roughness"].default_value = 0.45     # folha de madeira
        bump(30.0, 0.15, "WAVE")
    elif tipo == "piscina":
        bsdf.inputs["Base Color"].default_value = (0.55, 0.85, 0.95, 1)
        bsdf.inputs["Roughness"].default_value = 0.05
        bsdf.inputs["Transmission Weight"].default_value = 0.9
        bsdf.inputs["IOR"].default_value = 1.33
        bump(6.0, 0.25)
    elif tipo == "deck":
        bsdf.inputs["Roughness"].default_value = 0.6
        bump(12.0, 0.3, "WAVE")                            # tabuas
    elif tipo == "forro":
        bsdf.inputs["Roughness"].default_value = 0.45     # madeira do portico
        bump(20.0, 0.2, "WAVE")
    elif tipo in ("pilar", "brise", "fascia", "caixilho"):
        bsdf.inputs["Metallic"].default_value = 0.7
        bsdf.inputs["Roughness"].default_value = 0.35
        if tipo == "brise":
            bump(28.0, 0.6, "WAVE")                        # ripas
    elif tipo == "copa":
        bsdf.inputs["Roughness"].default_value = 0.9
        bump(25.0, 0.9)
    elif tipo in ("lote", "externo", "radier", "reservatorio"):
        if g > r and g > b:                                # verde: grama
            bsdf.inputs["Base Color"].default_value = (0.13, 0.30, 0.10, 1)
            bsdf.inputs["Roughness"].default_value = 0.95
            bump(120.0, 0.5)
        else:
            bsdf.inputs["Roughness"].default_value = 0.9
            bump(60.0, 0.1)
    elif tipo == "mob":
        bsdf.inputs["Roughness"].default_value = 0.6
    elif tipo == "tecnico":
        bsdf.inputs["Roughness"].default_value = 0.5
        bsdf.inputs["Metallic"].default_value = 0.3
    elif tipo == "escada":
        bsdf.inputs["Roughness"].default_value = 0.5
    return m


def montar(bpy, obj_path: str):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=obj_path)
    # materiais: o importador cria um por "usemtl"; trocamos pelo nosso
    for mat in list(bpy.data.materials):
        nome = mat.name
        if "_" not in nome:
            continue
        cor = nome.split("_")[-1]
        novo = material(bpy, nome + "_pr", cor)
        for ob in bpy.data.objects:
            for slot in ob.material_slots:
                if slot.material == mat:
                    slot.material = novo
    # chao infinito neutro fora do lote
    bpy.ops.mesh.primitive_plane_add(size=400, location=(10, 20, -0.25))
    chao = bpy.context.active_object
    mc = material(bpy, "chao_externo_9aa89a", "9aa89a")
    chao.data.materials.append(mc)
    # arvores do paisagismo (PA-xx com porte): tronco + copa, na posicao declarada
    import projeto as pj
    for p in pj.PAISAGISMO:
        porte = p.get("porte", "")
        try:
            alt = float(porte.split(" a ")[0].replace(",", ".")) if " a " in porte else 0.0
        except ValueError:
            alt = 0.0
        if alt < 3.0:
            continue
        alt = min(alt, 9.0)                                   # na entrega: arvore jovem
        x, y = p["x"] / 1000, p["y"] / 1000
        n = max(1, min(p.get("qtd", 1), 3))
        for k in range(n):
            dx = (k - (n - 1) / 2) * 2.5
            bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=alt * 0.45,
                                                location=(x + dx, y, alt * 0.225))
            tr = bpy.context.active_object
            tr.data.materials.append(material(bpy, "tronco_6b4a2e", "6b4a2e"))
            bpy.ops.mesh.primitive_uv_sphere_add(radius=alt * 0.28, location=(x + dx, y, alt * 0.7))
            cp = bpy.context.active_object
            cp.scale = (1.0, 1.0, 0.75 if "Palmeira" not in p["especie"] else 0.35)
            cp.data.materials.append(material(bpy, "copa_2f6b2a", "2f6b2a"))
            for pl in cp.data.polygons:
                pl.use_smooth = True
    # rua e calcada na testada (y < 0): contexto minimo para a foto ler "rua"
    import bpy as _b
    _b.ops.mesh.primitive_plane_add(size=1, location=(10, -1.5, -0.24))
    calcada = _b.context.active_object; calcada.scale = (60, 3, 1)
    calcada.data.materials.append(material(_b, "calcada_c9c4bb", "c9c4bb"))
    _b.ops.mesh.primitive_plane_add(size=1, location=(10, -8, -0.30))
    rua = _b.context.active_object; rua.scale = (60, 10, 1)
    rua.data.materials.append(material(_b, "rua_3d3f42", "3d3f42"))
    # o OBJ vem em blocos por usemtl; sombras suaves precisam de faces reais — ja sao.
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            for p in ob.data.polygons:
                p.use_smooth = False


def ceu(bpy, hora: float):
    w = bpy.data.worlds.new("Manaus")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    sky = nt.nodes.new("ShaderNodeTexSky")
    tipos = [i.identifier for i in sky.bl_rna.properties["sky_type"].enum_items]
    sky.sky_type = "NISHITA" if "NISHITA" in tipos else ("MULTIPLE_SCATTERING" if "MULTIPLE_SCATTERING" in tipos else tipos[0])
    alt, vet = sol(hora)
    sky.sun_elevation = max(0.05, alt)
    if hasattr(sky, "sun_disc"):
        sky.sun_disc = True                     # o ceu fisico traz o proprio sol
    sky.sun_intensity = 1.0
    # rotacao do sol no ceu: Blender mede a partir de +Y (norte do Blender);
    # no modelo o norte e +X. O vetor calculado da o azimute no modelo.
    if hasattr(sky, "sun_direction"):
        # Blender 5: o vetor manda; os eixos do OBJ importado sao os do modelo
        sinal = float(os.environ.get("RENDER_SOL_SINAL", "1"))
        sky.sun_direction = (vet[0] * sinal, vet[1] * sinal, vet[2])
    else:
        az_modelo = math.atan2(-vet[1], vet[0])     # do +x (norte) para leste (-y)
        sky.sun_rotation = -az_modelo + math.pi / 2
    for attr, val in (("sun_size", math.radians(1.2)), ("altitude", 90),
                      ("air_density", 1.2), ("dust_density", 1.6)):
        if hasattr(sky, attr):
            setattr(sky, attr, val)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    outn = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], outn.inputs["Surface"])


def camera(bpy, v: dict):
    px, py, pz = (c / 1000 for c in v["pos"])
    tx, ty, tz = (c / 1000 for c in v["alvo"])
    cam_data = bpy.data.cameras.new("cam")
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.angle = math.radians(v["fov"])
    cam_data.clip_start = 0.05
    cam_data.clip_end = 500
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (px, py, pz)
    alvo = bpy.data.objects.new("alvo", None)
    alvo.location = (tx, ty, tz)
    bpy.context.scene.collection.objects.link(alvo)
    c = cam.constraints.new("TRACK_TO")
    c.target = alvo
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    bpy.context.scene.camera = cam
    return cam


def renderizar(ids: list[str], amostras: int = 96, larg: int = 1280, alt: int = 800):
    import bpy
    man = json.load(open(os.path.join(OUT, "perspectivas.json"), encoding="utf-8"))
    vistas = {v["id"]: v for v in man["vistas"]}
    feitos = []
    for vid in ids:
        v = vistas[vid]
        montar(bpy, os.path.join(OUT, "porto-real.obj"))
        ceu(bpy, v["hora"])
        camera(bpy, v)
        sc = bpy.context.scene
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = amostras
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 6
        sc.cycles.transparent_max_bounces = 8
        sc.render.resolution_x, sc.render.resolution_y = larg, alt
        sc.render.resolution_percentage = 100
        sc.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
        sc.view_settings.look = "AgX - Medium High Contrast" if sc.view_settings.view_transform == "AgX" else "None"
        # dentro de casa so entra a luz das aberturas: +2,5 EV sobre a calibracao externa
        sc.view_settings.exposure = EXPOSICAO + (2.5 if v["tipo"] == "interna" else 0.0)
        sc.render.image_settings.file_format = "PNG"
        alvo = os.path.join(OUT, f"render-{vid}.png")
        sc.render.filepath = alvo
        bpy.ops.render.render(write_still=True)
        feitos.append(alvo)
        print("render", alvo, flush=True)
    return feitos


if __name__ == "__main__":
    ids = [a for a in sys.argv[1:] if not a.startswith("--")] or ["ext-270", "ext-090"]
    am = next((int(a.split("=")[1]) for a in sys.argv[1:] if a.startswith("--amostras=")), 96)
    renderizar(ids, am)
