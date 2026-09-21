# Dados de campo — medição por GPS/celular, 21/09/2026

**Fonte:** app de mapas no celular do proprietário (ferramenta "Medir" +
alfinete), sobre o Condomínio Porto Real. **Não é levantamento topográfico
certificado** — é GPS de celular + modelo digital de elevação do provedor de
mapas. Entra como (H) de campo, mais forte que a hipótese "lote plano" que
estava no modelo, mas ainda não substitui uma poligonal com estação total ou
RTK. Capturas em `2026-09-21-pin-lote.png` e `2026-09-21-medicao-testada.png`.

## 1. Localização

- Coordenadas do alfinete: **3°00'09.04"S 60°04'43.73"W**
- Elevação no ponto: **23,49 m**
- Local: dentro do lote do Condomínio Porto Real (rótulo "Cond. Porto Real"
  visível na busca do mapa).

## 2. Medição da testada (linha de 20 m)

- Comprimento: **20 m** — bate com `LOTE_L = 20_000` do caso.
- Direção (azimute) da linha: **341,53°**
- Elevação ao longo da linha: mín. **22,56 m** · mediana **22,89 m** ·
  máx. **23,49 m** → diferença de **0,93 m em 20 m**
- Inclinação estimada: mín. **1,7°** · mediana **2,1°** · máx. **4,7°**

## O que isso contradiz no modelo

1. **"Lote plano" era hipótese (H)**, citada em `DIVERGENCIAS.md` como
   premissa não verificada (seção B, contenções/arrimo) e usada
   implicitamente em `nucleo/vento.py:s1_talude` (S1 = 1,0 só vale para
   terreno plano). A medição mostra até 4,7° de declividade e quase 1 m de
   diferença de cota **só na faixa da testada** — o resto do lote (40 m de
   profundidade) pode variar mais.
2. **Norte da planta x norte real.** `NORTE_EM_PLANTA = -90` (símbolo do
   norte apontando para +x) e a convenção do caso é `+x = NORTE`. Se a linha
   de 20 m medida for de fato a testada, o azimute de 341,53° (≈18,5° a
   oeste do norte verdadeiro) sugere que o **+x do modelo não é exatamente o
   norte geográfico** — a orientação solar (insolação, SPDA, fator solar por
   face) foi calculada no norte da planta, não no norte real. Isto ainda não
   foi conferido — é candidato a pendência, não conclusão.
3. **RN (referência de nível) do projeto** hoje é `+0,00` arbitrário na
   platibanda/implantação (PR-01). Com cota real disponível (23,49 m no
   ponto do alfinete), dá para amarrar o RN do projeto a uma cota real, se o
   proprietário confirmar o datum.

## O que isto NÃO é

Não é uma sondagem nem uma poligonal. Não deve entrar como dado definitivo
de `RADIER`, `geotecnia` ou `terraplenagem` sem uma medição em mais pontos do
lote (a medida cobre só a faixa da testada, 20 m de 40 m de profundidade) ou
uma confirmação por levantamento planialtimétrico contratado (item A.2/A.3 da
lista de entregáveis, hoje "não tem").

## Próximo passo, se o proprietário confirmar

- Registrar como pendência nova em `PENDENCIAS` (projeto): declividade real
  do lote, hoje tratada como plana.
- Se houver mais pontos medidos (idealmente os 4 cantos + 2-3 pontos
  internos), dá para estimar corte/aterro real em vez de assumir zero.
- Conferir se a orientação solar do caso usa `NORTE_EM_PLANTA` como rotação
  geográfica ou só como símbolo de desenho.

Este arquivo é só o registro do dado bruto — nenhuma alteração foi aplicada
ao modelo, ao orçamento ou às pranchas a partir dele.
