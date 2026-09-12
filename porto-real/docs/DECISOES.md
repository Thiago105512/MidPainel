# Registro de decisões fechadas

## 1. Banheiro térreo — reposicionado, não acrescentado

Eu havia apontado a ausência de lavabo social como lacuna de programa.
**Estava errado.** O briefing (Lista Consolidada, seção 11) já decide:

> "Área social diretamente conectada à piscina; **banheiro térreo atende os
> usuários (sem banheiro exclusivo novo)**."

O banheiro existe e já é destinado a uso compartilhado. O problema real era
outro: ele estava em (13.200, 7.200), no extremo leste, **acessível apenas
atravessando o quarto reversível** — o que obrigava visitantes a entrar na
zona íntima e contradizia a própria função que o briefing lhe atribui.

### Solução: reposicionamento com área zero

| | Antes | Depois |
|---|---|---|
| Banho | (13.200, 7.200) 1.800 × 2.400 | **(10.200, 10.800)** 1.800 × 2.400 |
| Quarto reversível | (10.200, 7.200) 3.000 × 6.000 | **(12.000, 7.200)** 3.000 × 6.000 |
| Área térrea fechada | 174,24 m² | **174,24 m²** |

O banheiro passa a ter **duas portas**: uma para o hall (uso social e da
piscina) e outra para o quarto reversível (uso privativo quando o quarto
está ocupado). Mantém o box — que serve justamente quem sai da piscina.

Ganhos colaterais: o quarto reversível passa a ter **três faces externas**
(leste/frente, norte e oeste) em vez de uma, com ventilação cruzada real; e
surgem dois jardins — leste (6,48 m²) e norte (10,80 m²) — que dão face
externa ao banheiro e ao quarto.

Nenhum metro quadrado fechado foi acrescentado. Nenhuma família de esquadria
foi criada.

---

## 2. Chuveiros elétricos — 4.500 W em 220 V

Definição do cliente: **220 V**. Adotada, e com redução de potência.

### Cálculo

Para vazão de 3 L/min (0,05 kg/s) elevando de 27 °C (temperatura da rede em
Manaus) a 38 °C:

```
P = m · c · ΔT = 0,05 × 4.186 × 11 = 2.302 W ≈ 2,3 kW
```

Os 6.800 W do briefing aquecem água que já está quente. Adotado **4.500 W**,
menor potência comercial corrente, que ainda entrega ΔT de 21 K — margem de
sobra para qualquer condição.

| Parâmetro | Briefing | Adotado |
|---|---|---|
| Potência unitária | 6.800 W | **4.500 W** |
| Tensão | (não definida) | **220 V** |
| Corrente por chuveiro | 53,5 A em 127 V | **20,5 A** |
| Seção do condutor | 6,0 mm² | **4,0 mm²** |
| Disjuntor | 32 A | **25 A** |
| Potência instalada | 27.200 W | **18.000 W** |
| Demanda (fd 0,75) | — | **13,5 kW** |

A mudança de tensão sozinha derruba a corrente pela metade; a redução de
potência derruba de novo. O efeito em cascata alcança condutores, disjuntores,
o quadro de 36 módulos e a demanda contratada junto à concessionária.

---

## 3. Pluvial — reuso, não retenção

O briefing chama o reservatório de "retenção" mas descreve função de **reuso**
(irrigação e lavagem). São coisas diferentes, com dimensionamento oposto.

### Correção de uma crítica minha anterior

Eu havia dito que 2.500 L captam menos de 1 % da chuva anual e que, portanto,
o volume estaria subdimensionado. **O raciocínio estava invertido:** um
reservatório de reuso é dimensionado pela **demanda**, não pela oferta.
Guardar água que não será consumida não tem função.

### Balanço calculado

| Grandeza | Valor |
|---|---|
| Área de captação (cobertura + alpendre + varanda) | 188,64 m² |
| Precipitação em Manaus | 2.300 mm/ano |
| Captação (C = 0,95, descarte inicial 10 %) | **371 m³/ano** |
| Demanda diária | **269 L/dia** |
| Demanda anual | 98 m³/ano |
| **Autonomia com 2.500 L** | **9,3 dias** |
| Aproveitamento da chuva | 26,5 % |

Composição da demanda: lavagem de deck, calçada e veículos (21 L/dia), ducha
externa (90), reposição da piscina por evaporação (58) e irrigação com
paisagismo adaptado (100).

**Decisão: 2.500 L confirmados.** Em Manaus, uma estiagem superior a 9 dias é
rara mesmo na estação seca. Ampliar o reservatório só aumentaria custo e
volume morto.

### Não estender a vasos sanitários

Descarga com água de chuva renderia cerca de 55 m³/ano, mas exige tubulação
dupla permanentemente identificada, tratamento, bomba e controle. Payback de
15 a 30 anos, com risco permanente de conexão cruzada — falha cujo efeito é
sanitário, não econômico. Em uma cidade onde a água é abundante e barata, o
item não se paga nem em dinheiro nem em risco. **Mantida a restrição do
briefing.**

### Retenção: só se a lei exigir

Retenção é função distinta: amortecer o pico de vazão para a drenagem urbana.
Exige o reservatório **vazio** antes da chuva — o oposto do reuso, que o quer
cheio. Se o Código Ambiental de Manaus exigir retenção no lote, ela será
dimensionada como **volume separado**, ou como zona superior do mesmo
reservatório com descarga lenta por orifício calibrado. Mantida como
pendência nº 8 até a consulta.

---

## A fita social não recebe ar condicionado

Estar, core, gourmet e cozinha formam **um volume contínuo de 87,84 m²**, com
portas de vidro para o deck norte e para o pátio. Climatizar isso em Manaus é
resfriar o quintal: a carga do volume inteiro passa de 60.000 BTU/h e, com as
portas na posição em que o morador vai querer usá-las, o equipamento nunca
alcança o setpoint.

A estratégia ali é outra, e foi desenhada desde o início: **ventilação cruzada
sul → norte** (PV02 do estar para a loggia sul, PV01 do core para o deck norte),
ventiladores de teto e o pacote de sombreamento. Em clima quente-úmido, o
conforto vem da velocidade do ar sobre a pele, não da temperatura do ar — 0,8 m/s
de brisa equivalem a cerca de 2,5 °C de redução na temperatura operativa.

Fica **reservada a infraestrutura** — posição no nicho TC-09, furo, dreno e
circuito — para um split duto de 36.000 BTU sobre o jantar, caso o morador
decida depois fechar o vidro e pagar a conta. Decidir isso agora seria comprar
equipamento para uma hipótese; deixar o furo custa quase nada.

A cozinha também não recebe equipamento próprio: tem cooktop e churrasqueira,
que **adicionam** calor. Ali a solução é exaustão e ventilação, não resfriamento.

## A oficina recebe infraestrutura, não equipamento

Oficina de 9,00 m² com carga de 7.000 BTU/h. A terceira posição do nicho sul,
o furo, o dreno e o circuito estão previstos. O equipamento de 9.000 BTU entra
quando e se o uso justificar — é o mesmo método de especificação por demanda
que deixou apenas 7,80 m² de parede acústica PA-2 na casa inteira.

## A casa de máquinas da piscina é semi-enterrada, não enterrada

O modelo dizia "enterrada" com 1.200 mm. Errado por dois motivos técnicos:

1. A **retrolavagem do filtro** precisa drenar por gravidade. Com a bomba abaixo
   do nível de descarte, a lavagem depende de bombeamento e o filtro nunca é
   limpo direito.
2. Um motor de 1/2 cv dissipa cerca de 300 W de calor. Em recinto confinado com
   alçapão cego, a temperatura sobe e o motor perde vida útil.

**Correção:** piso 600 mm abaixo do deck, tampa em grelha 800 × 1.200 mm. A
grelha resolve ventilação e iluminação de manutenção ao mesmo tempo, e o dreno
vai para vala de infiltração. Continua sem volume solto no jardim — que era o
ganho que motivou enterrar.

---

## CORREÇÃO — a fita social passa a ser climatizada, com fronteira aerodinâmica

A decisão anterior (só infraestrutura) estava certa no diagnóstico e curta na
solução. O diagnóstico: climatizar os 87,84 m² inteiros exigiria 71.700 BTU/h
para resfriar justamente os dois ambientes que **produzem** calor —
churrasqueira e cooktop — e cuja exaustão joga o ar tratado fora. Pagar para
resfriar o que se está aquecendo e expulsando é termodinamicamente absurdo.

Mas a alternativa não é desistir do conforto. É **não climatizar o volume, e
sim a zona** — estabelecendo uma fronteira aerodinâmica na linha estar/gourmet,
sem nenhuma parede nova. Quatro medidas que se reforçam:

| medida | por que funciona |
|---|---|
| **Rebaixo de forro de 300 mm** na linha de fronteira | ar frio estratifica embaixo, ar quente retorna pelo teto. O rebaixo corta o caminho de retorno. Altura livre 2.300 mm — não atrapalha a passagem |
| **Insuflamento longe da fronteira, retorno junto a ela** | a circulação induzida puxa o ar para dentro da zona fria, não para fora |
| **Exaustão de 600 + 450 m³/h** na churrasqueira e no cooktop | mantém o gourmet em leve depressão: o fluxo fica estar → gourmet → exaustão, **uma direção só**. A fronteira deixa de ser reversível |
| **Ventiladores de teto no lado quente** | a 0,8 m/s, 27,5 °C tem a mesma temperatura operativa de 25 °C em ar parado (NBR 16401-2) |

Resultado: estar e jantar a 24–25 °C, gourmet a 27–28 °C com brisa. **Gradiente
de 3 °C em 12 m de planta, estável e numa direção.**

### O ventilador pagou um degrau do equipamento

A carga do estar + core era 33.200 BTU/h. Com o ventilador de teto permanente
na zona (VT-05), a NBR 16401-2 autoriza elevar a temperatura operativa de
projeto em ~2,5 °C — cerca de 8 % de carga por grau, fator 0,85. Com a perda de
5 % na rede de dutos: 33.200 × 0,85 × 1,05 = **29.700 BTU/h → equipamento de
30.000 em vez de 36.000.**

Um degrau comercial inteiro economizado por um ventilador de teto. É a melhor
relação custo-benefício do caderno, e não é coincidência: em clima quente-úmido
o conforto vem da velocidade do ar sobre a pele, não da temperatura do ar.

**Onde NÃO descontei:** nos dormitórios. Eles também recebem pá (VT-07 a VT-10),
mas o morador desliga o ventilador para dormir — ali a pá entra como economia de
**operação**, não como redução de **capacidade**. Descontar capacidade contando
com um equipamento que o usuário desliga é a forma mais comum de
subdimensionamento em projeto residencial. A auditoria agora reprova o desconto
quando não há pá declarada no ambiente.

### Carga final

| | BTU/h |
|---|---|
| 4 dormitórios × 18.000 | 72.000 |
| Zona social (duto, 30.000) | 30.000 |
| **Instalado** | **102.000** |
| Reservado (oficina) | 9.000 |

Contra os 144.000 BTU/h que a solução ingênua (climatizar tudo) exigiria —
**29 % menos equipamento**, e o projeto ganhou 10 ventiladores, 4 pontos de
exaustão e um rebaixo de forro, que juntos custam menos que uma única
condensadora de 36.000.
