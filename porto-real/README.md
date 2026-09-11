# Projeto Porto Real — caderno de arquitetura gerado por código

Residência unifamiliar, Manaus/AM (setor urbano SU16 Tarumã/Tarumã-Açu — **H**),
lote de 20,00 × 40,00 m. Estrutura híbrida: vedação em Light Steel Frame,
grandes vãos em perfis metálicos, fundação em radier.

Todo o caderno é **gerado por código a partir de um único modelo geométrico**.
Não há desenho manual: plantas, cortes, fachadas, cobertura e croqui leem a
mesma estrutura de dados, então é impossível uma prancha divergir da outra.

## Como executar

```bash
cd src
python3 build.py                 # SVG + PNG + PDF de todas as pranchas
python3 build.py --no-png        # pula a rasterização
python3 projeto.py               # confere áreas e verificação urbanística
```

Dependências: `cairosvg` (rasterização) e `pymupdf` (união do PDF).
Saída em `out/`, incluindo `PORTO_REAL_CADERNO_ARQUITETURA.pdf`.

## Caderno

| Prancha | Conteúdo | Escala |
|---|---|---|
| PR-01 | Implantação e situação, recuos, faixa técnica, verificação urbanística | 1:200 |
| PR-02 | Planta baixa — pavimento térreo, cotada, com quadros | 1:50 |
| PR-03 | Planta baixa — pavimento superior | 1:50 |
| PR-04 | Planta de layout — mobiliário solto | 1:50 |
| PR-05 | Planta de cobertura, caimentos, calhas e cálculo pluvial | 1:100 |
| PR-06 | Cortes AA (transversal) e BB (longitudinal) | 1:60 |
| PR-07 | Quatro fachadas | 1:80 |
| PR-08 | Croqui axonométrico e zoneamento funcional | s/ escala |
| PR-09 | Quadros gerais, sistemas prediais e pendências | s/ escala |
| PR-10 | Detalhes: parede LSF, escada, piscina, faixa técnica | 1:5 a 1:25 |

## Arquitetura do código

```
src/
  core.py        geometria, canvas SVG em mm, formatos ABNT, larguras de linha
  projeto.py     ÚNICA FONTE DE DADOS — ambientes, vãos, piscina, parâmetros
  elementos.py   derivação automática de paredes a partir da malha + esquadrias
  mobiliario.py  mobiliário fixo (louças, bancadas) e solto
  anotacao.py    cotagem, níveis, eixos, norte, marcas de corte, carimbo
  pranchas.py    implantação, plantas baixas, cobertura
  pranchas2.py   cortes, fachadas, croqui axonométrico
  pranchas3.py   detalhes e quadros gerais
  build.py       pipeline
```

**As paredes não são desenhadas.** São deduzidas: a malha de 600 mm é
preenchida pelos ambientes, e cada face entre dois ambientes vira divisória
de 100 mm, cada face entre ambiente e exterior vira parede externa de 150 mm.
Mudar um ambiente em `projeto.py` reconstrói paredes, cortes e fachadas.

## Para alterar o projeto

Edite apenas `src/projeto.py`:

- `TERREO` / `SUPERIOR` — retângulos modulares dos ambientes (múltiplos de 600 mm)
- `VAOS` — posição de portas e janelas; `ESQUADRIAS` — famílias de vão
- `PISCINA`, `DECK`, `FAIXA_TECNICA`, `CAIXA_DAGUA`, `ESCADA`, `COBERTURA`
- `RECUO_*`, `TAXA_OCUP_MAX`, `CAMT_MAX` — parâmetros urbanísticos

Rode `python3 projeto.py` para conferir áreas e enquadramento antes de gerar.

## Convenções de representação

NBR 10068 (formatos), 10582 (carimbo), 8403 (larguras de linha), 8402 (texto),
6492 (representação). Corte horizontal a 1,50 m. Cotas externas em duas
linhas — parciais e totais —, conforme exigido para planta baixa.

## Status

**Estudo preliminar.** Não liberado para obra, fabricação ou aprovação legal.
Sem ART/RRT. Itens marcados **(H)** no briefing são hipóteses técnicas
reproduzidas, não validadas. Ver `docs/DIVERGENCIAS.md`.
