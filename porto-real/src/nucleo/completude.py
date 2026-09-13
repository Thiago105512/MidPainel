"""COMPLETUDE — o que precisa EXISTIR, verificado contra o modelo.

A auditoria verifica o que esta la. Nao sente falta do que nunca foi escrito, e
essa cegueira tem historico neste projeto: o modelo passou trinta e uma
revisoes com 805 pecas de estrutura, todas de PAREDE. Nao havia vigamento de
entrepiso, nem cobertura, nem contraventamento. O piso do pavimento superior
nao se apoiava em nada, e as 447 condicoes de verificacao continuaram verdes,
porque todas verificavam coisas que existiam.

A diferenca entre este arquivo e o resto da auditoria e de direcao. O resto
pergunta "isto esta certo?". Aqui a pergunta e "isto esta aqui?" — e ela so
pode ser feita a partir de uma lista escrita ANTES de olhar o modelo, senao a
lista vira o inventario do que ja existe e confirma tudo por construcao.

COMO CADA ITEM E DETECTADO. Nunca por sinalizador. Todo item traz uma consulta
ao modelo que devolve a contagem do que encontrou: se o vigamento existe, ha
pecas de familia "viga"; se ha contraventamento, ha pecas de familia
"diagonal". Um item marcavel a mao seria marcado.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Exigencia:
    cod: str
    nome: str
    porque: str              # por que um edificio deste tipo precisa disto
    ausencia: str            # o que a falta significa, em termos fisicos
    obrigatorio: bool = True
    tipologias: tuple = ()   # vazio = vale para toda tipologia


# A lista e do SISTEMA CONSTRUTIVO, nao deste projeto. Escrita a partir do que
# um edificio em LSF tem de ter para ficar de pe e ser usado — e por isso ela
# pode acusar falta num projeto que ninguem tinha achado incompleto.
EXIGENCIAS = (
    Exigencia("parede", "Paredes estruturais",
              "sao o sistema portante vertical: o LSF nao tem pilares",
              "sem elas nao ha por onde a carga descer"),
    Exigencia("guia", "Guias superior e inferior",
              "amarram os montantes e transferem o cisalhamento ao diafragma",
              "montante sem guia e peca solta: nao ha painel, ha pecas"),
    Exigencia("entrepiso", "Vigamento de entrepiso",
              "sustenta o piso do pavimento superior",
              "o piso do superior nao se apoia em nada — foi exatamente esta "
              "a falta que passou 31 revisoes despercebida",
              tipologias=("SOBRADO", "MULTIFAMILIAR", "COMERCIAL")),
    Exigencia("cobertura", "Estrutura de cobertura",
              "sustenta o fechamento superior e transfere vento e sobrecarga",
              "a cobertura flutua sobre as paredes"),
    Exigencia("contraventamento", "Contraventamento",
              "resiste a forca horizontal de vento e de desaprumo",
              "a estrutura e um mecanismo no plano horizontal: as paredes "
              "giram nas ligacoes e a casa se deforma como um paralelogramo"),
    Exigencia("verga", "Vergas sobre as aberturas",
              "recebem a carga interrompida pela abertura e a levam as jambas",
              "a carga sobre o vao nao tem caminho: a guia superior flete e a "
              "esquadria trabalha como viga, que e como ela quebra"),
    Exigencia("jamba", "Jambas (king e jack stud)",
              "apoiam a verga e levam a reacao ate a fundacao",
              "a verga apoia em nada: a carga da abertura desce pela guia "
              "inferior, que nao foi feita para isso"),
    Exigencia("travamento", "Blocking ou bridging",
              "corta o comprimento de flambagem do montante",
              "o montante flamba no comprimento inteiro: a carga resistente "
              "cai para um quarto"),
    Exigencia("ancoragem", "Ancoragem a fundacao",
              "resiste ao arrancamento por vento e transfere o cisalhamento",
              "a casa apoia por peso proprio apenas — e vento de sucçao "
              "levanta uma estrutura leve com facilidade"),
    Exigencia("ligacao", "Programa de ligacoes",
              "sem parafuso definido as pecas nao formam estrutura",
              "cada peca e um objeto solto ao lado de outro"),
    Exigencia("corte", "Plano de corte",
              "a barra comprada e de 6 m e a peca nao",
              "nao ha como comprar nem cortar: o projeto nao chega a fabrica"),
    Exigencia("sequencia", "Sequencia de montagem",
              "define a ordem em que a estrutura fica estavel",
              "a obra improvisa a ordem, e ha ordens que deixam a estrutura "
              "instavel no meio do caminho"),
    Exigencia("escada", "Estrutura da escada",
              "liga os pavimentos e e carga concentrada no entrepiso",
              "nao ha acesso ao pavimento superior",
              tipologias=("SOBRADO", "MULTIFAMILIAR")),
)

POR_COD = {e.cod: e for e in EXIGENCIAS}


def _conta(pecas, familias) -> int:
    return sum(1 for p in pecas if getattr(p, "familia", "") in familias)


def conferir(r: dict, tipologia: str = "SOBRADO") -> dict:
    """Cada exigencia, consultada no resultado real da cadeia.

    Recebe o dicionario que `liberacao.rodar()` devolve — o mesmo que gera o
    BOM e o caderno. Conferir contra outro objeto seria conferir outra coisa.
    """
    pecas = r.get("pecas", [])
    fam = {}
    for p in pecas:
        f = getattr(p, "familia", "")
        fam[f] = fam.get(f, 0) + 1

    achados = {
        "parede": sum(fam.get(k, 0) for k in
                      ("stud", "king stud", "jack stud", "cripple superior",
                       "cripple inferior")),
        "guia": fam.get("track", 0),
        "entrepiso": sum(fam.get(k, 0) for k in ("viga", "viga de borda")),
        "cobertura": sum(1 for p in pecas
                         if getattr(p, "pav", "") == "C"),
        "contraventamento": fam.get("diagonal", 0),
        "verga": fam.get("header", 0),
        "jamba": fam.get("king stud", 0) + fam.get("jack stud", 0),
        "travamento": fam.get("blocking", 0) + fam.get("travamento", 0),
        # os tres abaixo nao sao pecas: sao resultados da cadeia
        "ancoragem": len(r.get("ancoragem", {}) or {}),
        "ligacao": r.get("n_parafusos", 0),
        "corte": r.get("plano", {}).get("n_barras", 0),
        "sequencia": len(r.get("passos", []) or []),
        "escada": fam.get("escada", 0),
    }

    itens, faltando = [], []
    for e in EXIGENCIAS:
        if e.tipologias and tipologia not in e.tipologias:
            itens.append(dict(cod=e.cod, nome=e.nome, n=0,
                              situacao="NAO SE APLICA",
                              nota=f"exigencia de {', '.join(e.tipologias)}"))
            continue
        n = achados.get(e.cod, 0)
        ok = n > 0
        itens.append(dict(cod=e.cod, nome=e.nome, n=n,
                          situacao="PRESENTE" if ok else "AUSENTE",
                          nota=e.porque if ok else e.ausencia))
        if not ok:
            faltando.append(dict(cod=e.cod, nome=e.nome, porque=e.porque,
                                 ausencia=e.ausencia))
    aplicaveis = [i for i in itens if i["situacao"] != "NAO SE APLICA"]
    return dict(itens=itens, faltando=faltando,
                n=len(aplicaveis), presentes=len(aplicaveis) - len(faltando),
                completo=not faltando,
                situacao=("COMPLETO" if not faltando else
                          f"INCOMPLETO: {len(faltando)} sistema(s) ausente(s) — "
                          + ", ".join(f["nome"] for f in faltando)))
