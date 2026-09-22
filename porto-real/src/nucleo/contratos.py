"""CONTRATOS — o que o sistema NAO faz, escrito com a mesma seriedade do que faz.

Vinte das 155 secoes da especificacao dependem de algo que nao existe dentro
deste repositorio: um arquivo proprietario que so a Autodesk le, uma nuvem de
pontos que so um scanner produz, uma foto de obra que so alguem no canteiro
tira, um ERP que so a empresa tem. Ha duas maneiras honestas de tratar isso e
uma desonesta.

A desonesta e simular. Gerar um as-built plausivel, um desvio de 3 mm que
parece medido, um "digital twin" que na verdade e o proprio modelo redesenhado
com outra cor. Isso nao e uma funcionalidade incompleta: e uma funcionalidade
FALSA, e e pior do que a ausencia, porque a ausencia se ve.

As duas honestas sao: nao entregar, ou entregar o CONTRATO. Este arquivo faz a
segunda. Para cada bloqueio ha:

  1. o motivo do bloqueio — o que, concretamente, falta;
  2. o esquema de dados — os campos, tipos e unidades que o mundo tem de
     fornecer, com precisao suficiente para alguem implementar o fornecedor;
  3. o adaptador vazio — `consultar()`, que levanta SemFonteDeDados com o que
     falta e como suprir, e NUNCA devolve numero;
  4. `receber()` — que ja funciona hoje: valida e normaliza o dado quando ele
     chegar, e recusa o malformado;
  5. o criterio de aceite — o teste que passa no dia em que o dado existir.

O contrato e executavel. Nao e um comentario dizendo "futuramente": e codigo
que ja recusa dado errado e ja sabe dizer o que quer. No dia em que o scanner
entregar o arquivo, o que falta escrever e o leitor do formato — o resto ja
esta aqui, verificado.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class SemFonteDeDados(RuntimeError):
    """Levantada por todo adaptador bloqueado. Carrega o que falta.

    Nao e um erro de programacao: e a resposta correta de uma funcao que nao
    tem como responder. Traz o codigo do contrato, o que falta e como suprir,
    para que a mensagem sirva a quem for resolver, e nao apenas a quem depurar.
    """

    def __init__(self, contrato: "Contrato"):
        self.contrato = contrato
        super().__init__(
            f"{contrato.cod}: sem fonte de dados — {contrato.bloqueio}. "
            f"Para suprir: {contrato.fonte}")


TIPOS = {
    "texto": str, "inteiro": int, "real": float, "booleano": bool,
    "lista": list, "registro": dict,
}


@dataclass(frozen=True)
class Campo:
    nome: str
    tipo: str
    unidade: str = ""
    obrigatorio: bool = True
    descricao: str = ""
    dominio: tuple = ()          # valores admissiveis, quando fechado

    def validar(self, v) -> str:
        """Devolve o erro, ou string vazia. Um campo se valida sozinho."""
        if v is None or v == "":
            return "" if not self.obrigatorio else f"{self.nome}: ausente"
        esperado = TIPOS[self.tipo]
        if esperado is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if not isinstance(v, esperado) or (esperado is not bool
                                           and isinstance(v, bool)):
            return (f"{self.nome}: esperado {self.tipo}, veio "
                    f"{type(v).__name__}")
        if self.dominio and v not in self.dominio:
            return f"{self.nome}: '{v}' fora do dominio {self.dominio}"
        return ""


@dataclass(frozen=True)
class Contrato:
    cod: str
    titulo: str
    secoes: tuple                 # secoes da especificacao que este contrato cobre
    bloqueio: str                 # o que, concretamente, falta
    fonte: str                    # como suprir
    esquema: tuple                # tuple[Campo]
    aceite: str                   # o criterio que valida quando o dado chegar
    esforco: str = ""             # o que ainda seria preciso escrever

    # ---------------------------------------------------------- adaptador
    def consultar(self, *a, **k):
        """O adaptador vazio. Sempre levanta; nunca devolve numero."""
        raise SemFonteDeDados(self)

    def receber(self, registros: list) -> list[dict]:
        """Valida e normaliza o dado externo. Isto ja funciona hoje.

        E o que separa um contrato de uma promessa: o validador existe antes do
        dado, entao o dado chega a um lugar que ja sabe recusa-lo.
        """
        if not isinstance(registros, list):
            raise TypeError(f"{self.cod}: esperava lista de registros")
        limpos, erros = [], []
        conhecidos = {c.nome for c in self.esquema}
        for i, r in enumerate(registros):
            if not isinstance(r, dict):
                erros.append(f"registro {i}: nao e um registro")
                continue
            for extra in sorted(set(r) - conhecidos):
                erros.append(f"registro {i}: campo '{extra}' nao esta no esquema")
            reg = {}
            for c in self.esquema:
                e = c.validar(r.get(c.nome))
                if e:
                    erros.append(f"registro {i}: {e}")
                elif c.nome in r:
                    reg[c.nome] = r[c.nome]
            limpos.append(reg)
        if erros:
            raise ValueError(f"{self.cod}: {len(erros)} problema(s) — "
                             + "; ".join(erros[:5]))
        return limpos

    def obrigatorios(self) -> tuple:
        return tuple(c.nome for c in self.esquema if c.obrigatorio)

    def documentar(self) -> str:
        """O contrato em texto, para quem for implementar o fornecedor."""
        linhas = [f"# {self.cod} — {self.titulo}",
                  f"Secoes da especificacao: "
                  f"{', '.join(str(s) for s in self.secoes)}",
                  "",
                  f"BLOQUEIO: {self.bloqueio}",
                  f"FONTE: {self.fonte}",
                  f"ACEITE: {self.aceite}"]
        if self.esforco:
            linhas.append(f"FALTA ESCREVER: {self.esforco}")
        linhas += ["", "## Esquema", ""]
        for c in self.esquema:
            u = f" [{c.unidade}]" if c.unidade else ""
            o = "obrigatorio" if c.obrigatorio else "opcional"
            d = f" · dominio {c.dominio}" if c.dominio else ""
            linhas.append(f"- {c.nome}: {c.tipo}{u} ({o}){d}"
                          + (f" — {c.descricao}" if c.descricao else ""))
        return "\n".join(linhas) + "\n"


# =========================================================================
# OS CONTRATOS
# =========================================================================
def _c(n, t, u="", ob=True, d="", dom=()):
    return Campo(n, t, u, ob, d, dom)


CONTRATOS = (
    Contrato(
        cod="DWG-RVT",
        titulo="Leitura de formato proprietario (DWG, RVT, SKP, PLN)",
        secoes=(3,),
        bloqueio="DWG e RVT sao formatos proprietarios e sem especificacao "
                 "publica completa; ler um deles exige biblioteca licenciada "
                 "ou engenharia reversa, e a fidelidade nao e verificavel",
        fonte="exportacao do proprio CAD em DXF (que o projeto ja le) ou IFC4; "
              "alternativamente, licenca do RealDWG ou da API do Revit",
        esquema=(
            _c("formato", "texto", dom=("DWG", "RVT", "SKP", "PLN")),
            _c("versao", "texto", d="R2018, 2024, etc — muda o binario"),
            _c("unidade", "texto", dom=("mm", "cm", "m", "pol")),
            _c("camadas", "lista", d="nomes das camadas, para mapear disciplina"),
            _c("origem", "lista", u="mm", ob=False,
               d="ponto de insercao, para casar com a origem do modelo"),
        ),
        aceite="importar o DXF exportado do mesmo arquivo e o proprio arquivo "
               "proprietario tem de produzir a MESMA lista de paredes, com "
               "diferenca de coordenada menor que 1 mm",
        esforco="leitor do formato; o resto do caminho (DXF -> paredes -> "
                "paineis) ja existe e esta auditado"),

    Contrato(
        cod="LIDAR",
        titulo="Nuvem de pontos de scanner ou LiDAR",
        secoes=(77,),
        bloqueio="nao ha scanner; nuvem de pontos nao se deduz de projeto — "
                 "ela mede o que foi construido, e e justamente por diferir do "
                 "projeto que serve para alguma coisa",
        fonte="levantamento com estacao a laser (E57, LAS, PTS) ou fotogrametria "
              "com alvo codificado; precisao declarada pelo equipamento",
        esquema=(
            _c("x", "real", "mm"), _c("y", "real", "mm"), _c("z", "real", "mm"),
            _c("intensidade", "real", ob=False),
            _c("precisao", "real", "mm", d="incerteza declarada do equipamento"),
            _c("estacao", "texto", ob=False, d="de qual posicao o ponto veio"),
            _c("data", "texto", d="ISO 8601 — a nuvem envelhece"),
        ),
        aceite="registrar a nuvem contra o modelo e obter desvio medio menor "
               "que a precisao declarada do equipamento; um desvio menor que a "
               "precisao seria suspeito, nao bom",
        esforco="registro (ICP ou alvos), segmentacao de plano e comparacao "
                "com as faces do modelo"),

    Contrato(
        cod="VISAO",
        titulo="Reconhecimento automatico de planta por visao computacional",
        secoes=(4, 76),
        bloqueio="exige modelo treinado e um conjunto anotado de plantas; sem "
                 "treino, qualquer 'reconhecimento' seria adivinhacao com "
                 "aparencia de resultado",
        fonte="corpus anotado de plantas (parede, vao, cota, texto) com "
              "geometria verdadeira, ou servico de terceiros com acuracia "
              "publicada por classe",
        esquema=(
            _c("classe", "texto",
               dom=("parede", "vao", "cota", "texto", "mobiliario", "eixo")),
            _c("caixa", "lista", "px", d="x0, y0, x1, y1 na imagem"),
            _c("confianca", "real", d="0 a 1, calibrada"),
            _c("escala", "real", "mm/px", d="sem escala a caixa nao vira parede"),
            _c("pagina", "inteiro", ob=False),
        ),
        aceite="rodar sobre as 35 pranchas deste projeto, cuja verdade e "
               "conhecida por construcao, e medir precisao e revocacao por "
               "classe; abaixo de 0,95 em parede o resultado nao entra no modelo",
        esforco="inferencia, calibracao da confianca e a conversao "
                "caixa+escala -> parede"),

    Contrato(
        cod="AS-BUILT",
        titulo="As-designed x as-built e digital twin",
        secoes=(78, 117, 118),
        bloqueio="as-built e medicao do que foi construido; sem obra e sem "
                 "medicao, um 'as-built' gerado do projeto e o proprio projeto "
                 "com outro nome — o unico caso em que os dois coincidem "
                 "perfeitamente e o caso que nunca acontece",
        fonte="medicao em campo (LIDAR, estacao total ou trena a laser) por "
              "peca ou por painel, com data e responsavel",
        esquema=(
            _c("peca", "texto", d="codigo estavel da peca no modelo"),
            _c("x", "real", "mm"), _c("y", "real", "mm"), _c("z", "real", "mm"),
            _c("metodo", "texto",
               dom=("lidar", "estacao total", "trena", "fotogrametria")),
            _c("incerteza", "real", "mm"),
            _c("data", "texto"), _c("responsavel", "texto"),
        ),
        aceite="para cada peca medida, |as-built − as-designed| comparado a "
               "tolerancia de montagem; o que passar da tolerancia vira "
               "pendencia, nao virgula no relatorio",
        esforco="a comparacao em si e trivial — o modelo ja tem a posicao de "
                "cada peca; falta so o dado medido"),

    Contrato(
        cod="AR",
        titulo="Realidade aumentada em canteiro",
        secoes=(111,),
        bloqueio="exige dispositivo com rastreamento espacial e ancoragem no "
                 "mundo real; uma sobreposicao sem ancoragem verificada "
                 "posiciona a peca no lugar errado com aparencia de precisao",
        fonte="ARKit/ARCore com marcador fisico de origem levantado por estacao "
              "total, ou headset com SLAM e erro de deriva publicado",
        esquema=(
            _c("ancora", "texto", d="marcador fisico com coordenada conhecida"),
            _c("origem", "lista", "mm", d="x, y, z do marcador no modelo"),
            _c("rotacao", "lista", "grau", d="alinhamento do eixo do canteiro"),
            _c("deriva", "real", "mm", d="erro acumulado declarado pelo aparelho"),
        ),
        aceite="a peca sobreposta tem de coincidir com a peca fisica dentro da "
               "deriva declarada, verificado por foto com escala",
        esforco="o modelo ja exporta OBJ e glTF-equivalente; falta o app e a "
                "ancoragem"),

    Contrato(
        cod="OBRA",
        titulo="Aplicativo de obra: modo offline, fotos, punch list e diario",
        secoes=(112, 113, 114, 115, 116),
        bloqueio="exige aplicativo movel e armazenamento sincronizavel; nada "
                 "disso e gerado do projeto — e registro do que aconteceu, e o "
                 "que aconteceu so o canteiro sabe",
        fonte="app com banco local e fila de sincronizacao; o esquema abaixo e "
              "o contrato minimo do que ele precisa devolver",
        esquema=(
            _c("tipo", "texto",
               dom=("foto", "pendencia", "diario", "medicao", "ocorrencia")),
            _c("peca", "texto", ob=False, d="peca ou painel a que se refere"),
            _c("etapa", "texto", ob=False, d="passo da sequencia de montagem"),
            _c("autor", "texto"), _c("data", "texto"),
            _c("texto", "texto", ob=False),
            _c("anexo", "texto", ob=False, d="caminho ou hash do arquivo"),
            _c("gps", "lista", ob=False, d="latitude, longitude"),
            _c("sincronizado", "booleano", ob=False,
               d="falso enquanto so existir no aparelho"),
        ),
        aceite="um registro criado offline e sincronizado depois tem de chegar "
               "com a data de CRIACAO, nao a de sincronizacao — o diario de "
               "obra que reordena eventos nao vale como diario",
        esforco="o app inteiro; do lado do projeto, so a chave peca/etapa, que "
                "ja existe e e estavel entre revisoes"),

    Contrato(
        cod="SENSOR",
        titulo="Sensoriamento da edificacao em uso",
        secoes=(120,),
        bloqueio="exige sensores instalados e uma serie temporal; sem eles, "
                 "qualquer curva e simulacao — util para estudo, nunca para "
                 "afirmar como o edificio se comporta",
        fonte="sensores com modelo, faixa e incerteza declarados, amostrando "
              "com carimbo de tempo sincronizado",
        esquema=(
            _c("sensor", "texto"), _c("grandeza", "texto",
               dom=("temperatura", "umidade", "co2", "energia", "vazao",
                    "deformacao", "ruido")),
            _c("valor", "real"), _c("unidade", "texto"),
            _c("instante", "texto", d="ISO 8601 com fuso"),
            _c("ambiente", "texto", ob=False, d="codigo do ambiente no modelo"),
            _c("incerteza", "real", ob=False),
        ),
        aceite="comparar a serie medida com a previsao do calculo termico do "
               "projeto e publicar a diferenca; um sistema que so mostra o "
               "medido nao aprende nada",
        esforco="ingestao, agregacao temporal e o cruzamento com o desempenho "
                "calculado, que ja existe"),

    Contrato(
        cod="ERP",
        titulo="Integracao com ERP, compras e estoque",
        secoes=(136,),
        bloqueio="exige sistema da empresa e credencial; preco, prazo e estoque "
                 "reais nao se deduzem — os precos do BOM sao (H) e estao "
                 "marcados como tal em todo lugar onde aparecem",
        fonte="API do ERP (SKU, preco, lead time, saldo) ou exportacao "
              "periodica em CSV com a mesma chave de SKU",
        esquema=(
            _c("sku", "texto"), _c("descricao", "texto", ob=False),
            _c("preco", "real", "BRL"), _c("moeda", "texto", dom=("BRL", "USD", "EUR")),
            _c("lead_time_dias", "inteiro"),
            _c("saldo", "real", ob=False),
            _c("fornecedor", "texto", ob=False),
            _c("cotado_em", "texto", d="preco sem data nao e preco"),
        ),
        aceite="substituir a tabela (H) pelos precos reais nao pode mudar a "
               "ESTRUTURA do BOM, so os valores; se a lista de itens mudar, a "
               "chave de SKU esta errada",
        esforco="o cliente da API; a montagem do BOM, a curva ABC, o landed "
                "cost e o Monte Carlo ja existem e ja consomem esta forma"),

    Contrato(
        cod="USUARIO",
        titulo="Usuarios, permissoes, aprovacoes e assinatura digital",
        secoes=(131, 132, 133, 134),
        bloqueio="exige servidor, identidade e, no caso da assinatura, "
                 "certificado ICP-Brasil com cadeia verificavel; uma 'aprovacao' "
                 "sem identidade verificada e um campo de texto",
        fonte="provedor de identidade (OIDC) e, para assinatura, certificado "
              "A1/A3 com carimbo de tempo de autoridade credenciada",
        esquema=(
            _c("usuario", "texto"), _c("papel", "texto",
               dom=("leitor", "projetista", "coordenador", "responsavel tecnico",
                    "cliente", "fabrica")),
            _c("acao", "texto",
               dom=("ler", "editar", "aprovar", "congelar", "liberar", "assinar")),
            _c("documento", "texto"), _c("revisao", "texto"),
            _c("instante", "texto"),
            _c("certificado", "texto", ob=False, d="serie do certificado usado"),
            _c("carimbo_tempo", "texto", ob=False,
               d="de autoridade credenciada, nao do relogio local"),
        ),
        aceite="a assinatura tem de continuar verificavel depois de o documento "
               "ser reemitido noutra maquina; e aprovar exige papel com "
               "atribuicao tecnica — o sistema nao substitui ART nem RRT",
        esforco="autenticacao, autorizacao e a cadeia de assinatura; o registro "
                "de quem fez o que ja tem lugar no banco (11 tabelas de evento)"),

    Contrato(
        cod="HISTORICO",
        titulo="Aprendizado com projetos anteriores",
        secoes=(125,),
        bloqueio="exige historico real de obras executadas — com o que foi "
                 "orcado, o que foi gasto, o que atrasou e por que; um projeto "
                 "so nao e amostra, e o proprio Porto Real ainda nao foi "
                 "construido",
        fonte="base de obras concluidas do mesmo sistema construtivo, com "
              "desvio de custo e prazo por etapa",
        esquema=(
            _c("projeto", "texto"), _c("area_m2", "real", "m2"),
            _c("sistema", "texto"), _c("custo_previsto", "real", "BRL"),
            _c("custo_real", "real", "BRL"),
            _c("prazo_previsto_dias", "inteiro"),
            _c("prazo_real_dias", "inteiro"),
            _c("causa_desvio", "texto", ob=False),
            _c("concluido_em", "texto"),
        ),
        aceite="a previsao aprendida tem de ser testada fora da amostra: "
               "treinar sem uma obra e prever justamente ela; sem isso o modelo "
               "so decora",
        esforco="a estatistica; a estrutura de custo por etapa ja existe"),
)

POR_COD = {c.cod: c for c in CONTRATOS}


def bloqueadas_cobertas() -> set:
    """Quais secoes da especificacao os contratos cobrem."""
    return {s for c in CONTRATOS for s in c.secoes}


def documentar_tudo() -> str:
    return ("\n\n".join(c.documentar() for c in CONTRATOS)
            + f"\n\n{len(CONTRATOS)} contratos, "
              f"{len(bloqueadas_cobertas())} secoes bloqueadas cobertas.\n")
