#!/usr/bin/env python3
"""ENGENHARIA no visualizador — a terceira aba.

A aba 2D mostra as pranchas; a 3D mostra o volume; esta mostra o que nenhuma
das duas cabe: 801 pecas, 62 paineis, um plano de corte de 328 barras, 100
passos de montagem e seis notas com a formula aberta.

Nada e desenhado a mao aqui. O painel de parede e montado no navegador a
partir da posicao (x, z) e do comprimento de cada peca, que sao os mesmos
numeros que a maquina de perfilagem vai receber. Se o desenho sair errado, a
peca sai errada — e esse e exatamente o ponto de desenhar assim.

Sete vistas: painel de controle, paineis, pecas, corte, montagem, logistica e
documentos. Tres modos de leitura (executivo, educacional, especialista) que
mudam a explicacao e nunca o numero.
"""
from __future__ import annotations

CSS_ENG = r'''
  /* ----------------------------------------------------- aba engenharia */
  #stageEng{background:var(--stage); max-height:min(78vh,760px); overflow-y:auto;
            padding:16px}
  .eng-sec{margin:0 0 26px}
  .eng-sec > h3{font-family:var(--mono); font-size:10.5px; letter-spacing:.13em;
    text-transform:uppercase; color:var(--ink-faint); margin:0 0 10px; font-weight:500}
  .cartoes{display:grid; grid-template-columns:repeat(auto-fit,minmax(148px,1fr));
           gap:1px; background:var(--rule-soft); border:1px solid var(--rule-soft)}
  .cartao{background:var(--surface); padding:11px 13px}
  .cartao .rot{font-family:var(--mono); font-size:10px; letter-spacing:.1em;
    text-transform:uppercase; color:var(--ink-faint); display:block; margin-bottom:3px}
  .cartao .val{font-family:var(--mono); font-size:20px; font-weight:500;
    font-variant-numeric:tabular-nums; letter-spacing:-.01em}
  .cartao .uni{font-family:var(--mono); font-size:11px; color:var(--ink-soft)}

  .notas{display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:10px}
  .nota{background:var(--surface); border:1px solid var(--rule-soft); padding:12px 13px}
  .nota h4{margin:0 0 8px; font-family:var(--mono); font-size:11px; letter-spacing:.08em;
           text-transform:uppercase; color:var(--ink-soft); font-weight:500}
  .nota .n{font-family:var(--mono); font-size:26px; font-weight:600;
           font-variant-numeric:tabular-nums; line-height:1}
  .nota .n small{font-size:12px; color:var(--ink-faint); font-weight:400}
  .barra-nota{height:5px; background:var(--rule-soft); margin:8px 0 7px; overflow:hidden}
  .barra-nota i{display:block; height:100%; background:var(--accent)}
  .nota.ruim .barra-nota i{background:var(--alert)}
  .nota .form{font-family:var(--mono); font-size:10.5px; color:var(--ink-faint);
              line-height:1.45; margin:0}

  .selo{border:1px solid var(--ok); color:var(--ok); background:var(--ok-soft);
        font-family:var(--mono); font-size:12px; letter-spacing:.06em;
        padding:9px 13px; display:flex; gap:12px; align-items:center; flex-wrap:wrap}
  .selo.nao{border-color:var(--alert); color:var(--alert); background:var(--alert-soft)}
  .selo b{letter-spacing:.12em; text-transform:uppercase}

  .check{list-style:none; margin:10px 0 0; padding:0;
         display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:0 22px}
  .check li{display:grid; grid-template-columns:16px 1fr auto; gap:9px; align-items:baseline;
            padding:6px 0; border-top:1px solid var(--rule-soft); font-size:13px}
  .check .m{font-family:var(--mono); font-size:12px; color:var(--ok)}
  .check li.mau .m{color:var(--alert)}
  .check .st{font-family:var(--mono); font-size:9.5px; letter-spacing:.09em;
             color:var(--ink-faint)}

  .filtros{display:flex; flex-wrap:wrap; gap:7px; align-items:center; margin-bottom:11px}
  .filtros input, .filtros select{font-family:var(--mono); font-size:11.5px;
    border:1px solid var(--rule); background:var(--surface); color:var(--ink);
    padding:5px 8px; border-radius:2px}
  .filtros input[type="search"]{min-width:190px}
  .conta{font-family:var(--mono); font-size:11px; color:var(--ink-faint)}

  .eng-grid{display:grid; grid-template-columns:220px 1fr; gap:14px; align-items:start}
  @media (max-width:820px){ .eng-grid{grid-template-columns:1fr} }
  .lista{list-style:none; margin:0; padding:0; max-height:520px; overflow-y:auto;
         border:1px solid var(--rule-soft); background:var(--surface)}
  .lista li + li{border-top:1px solid var(--rule-soft)}
  .lista button{width:100%; text-align:left; background:none; border:none; color:inherit;
    font-family:inherit; font-size:12.5px; padding:7px 10px; cursor:pointer; line-height:1.3}
  .lista button:hover{background:var(--rule-soft)}
  .lista button[aria-current="true"]{background:var(--accent-soft);
    box-shadow:inset 2px 0 0 var(--accent)}
  .lista .sub{display:block; font-family:var(--mono); font-size:10px; color:var(--ink-faint)}

  .desenho{border:1px solid var(--rule-soft); background:var(--surface); padding:12px}
  .desenho svg{display:block; width:100%; height:auto; max-width:100%}
  .desenho .cap{font-family:var(--mono); font-size:11px; color:var(--ink-soft);
                margin:9px 0 0; line-height:1.5}
  .legenda{display:flex; flex-wrap:wrap; gap:5px 13px; margin:10px 0 0;
           font-family:var(--mono); font-size:10.5px; color:var(--ink-soft)}
  .legenda span{display:inline-flex; align-items:center; gap:5px}
  .legenda i{width:11px; height:11px; display:inline-block; border:1px solid rgba(0,0,0,.25)}

  .tabela{width:100%; border-collapse:collapse; font-family:var(--mono); font-size:11.5px;
          font-variant-numeric:tabular-nums}
  .tabela th{text-align:left; font-weight:500; font-size:10px; letter-spacing:.09em;
    text-transform:uppercase; color:var(--ink-faint); padding:6px 8px;
    border-bottom:1px solid var(--rule); position:sticky; top:0; background:var(--surface);
    cursor:pointer; white-space:nowrap}
  .tabela th:hover{color:var(--accent)}
  .tabela td{padding:5px 8px; border-bottom:1px solid var(--rule-soft)}
  .tabela tbody tr:hover{background:var(--rule-soft)}
  .rolagem{max-height:480px; overflow:auto; border:1px solid var(--rule-soft);
           background:var(--surface)}
  .chip{display:inline-block; width:9px; height:9px; margin-right:6px;
        border:1px solid rgba(0,0,0,.25)}

  .docs{display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px}
  .doc-txt{background:var(--surface); border:1px solid var(--rule-soft); padding:12px;
           font-family:var(--mono); font-size:11.5px; line-height:1.6; white-space:pre-wrap;
           max-height:520px; overflow:auto; margin:0}
  .modos-leitura{display:flex; gap:4px; margin-left:auto}
  .modos-leitura button{font-family:var(--mono); font-size:10.5px; letter-spacing:.05em;
    border:1px solid var(--rule); background:var(--surface); color:var(--ink-soft);
    padding:4px 9px; cursor:pointer; border-radius:2px}
  .modos-leitura button[aria-pressed="true"]{border-color:var(--accent);
    color:var(--accent); background:var(--accent-soft)}
'''

HTML_ENG = r'''
      <div id="stageEng" hidden>
        <div id="engConteudo"></div>
      </div>
'''


JS_ENG = r'''
// =====================================================================
// ENGENHARIA — o motor inteiro em sete vistas
// =====================================================================
let ENG = null, engVista = "painel", engModo = "educacional";
let painelSel = null, docSel = "memorial", animar = null;

const VISTAS = [
  ["painel",     "Painel de controle", "16 itens e 6 notas"],
  ["paineis",    "Painéis",            "elevação montada da peça"],
  ["pecas",      "Peças",              "801 linhas filtráveis"],
  ["corte",      "Plano de corte",     "barra a barra"],
  ["montagem",   "Montagem",           "sequência animada"],
  ["logistica",  "Logística",          "container e içamento"],
  ["documentos", "Documentos",         "gerados do modelo"],
  ["materiais",  "Materiais",          "camada a camada, com norma"],
  ["parafusos",  "Parafusos",          "5.266, e de onde vem cada um"],
  ["instalacoes","Instalações",        "percurso medido, e onde ele bate"],
  ["cotacao",    "Custo e cotação",    "o que se compra, e o que falta perguntar"],
  ["ambientes",  "Por ambiente",       "cômodo a cômodo, tudo num lugar só"],
  ["catalogo",   "Catálogo técnico",   "cada peça desenhada do modelo"],
  ["fachada",    "Fachada",            "o combinado, o desenhado e o estrutural"],
  ["viabilidade","Viabilidade",        "o que falta, e quanto depende disso"],
  ["geotecnia", "Sondagem e solo",     "três furos, e o que eles mandaram mudar"],
  ["pluvial",   "Água de chuva",       "o lote inteiro, e o que fica retido"],
  ["acustica",  "Acústica",            "quem ouve quem, e através de quê"],
  ["eletrica",  "Cargas e mercado",    "220/127, fases equilibradas e fornecedores"],
  ["marcenaria", "Marcenaria",         "cada móvel em módulos, peças e ferragens"],
  ["bloqueios",  "O que não faço",     "10 contratos, 20 seções"],
];

const LEITURA = {
  executivo: {
    painel: "O projeto está liberado ou não, e quanto custa. As seis notas " +
            "resumem seis riscos distintos; a menor delas é a que decide. " +
            "A verificação estrutural diz quantos montantes reprovam — e o " +
            "número que importa ali é zero.",
    paineis: "Cada painel é uma unidade de compra, de transporte e de " +
             "montagem. O que não couber no caminhão vira custo.",
    pecas: "Cada linha é uma peça que alguém vai cortar, furar e parafusar.",
    corte: "O aproveitamento é dinheiro: o que sobra da barra foi comprado.",
    montagem: "O prazo da obra é esta lista multiplicada pelo tamanho da equipe.",
    logistica: "Um container mal ocupado é frete pago por ar.",
    documentos: "O que vai para a fábrica e para o canteiro.",
    materiais: "O que vai em cada estrutura: material, espessura, norma e " +
               "quantas placas inteiras. Não metro quadrado — placa.",
    parafusos: "Quantos parafusos, quais, e onde. O número que interessa " +
               "não é o total: é quantos vêm de força calculada.",
    viabilidade: "O que ainda falta, quem fecha cada item e — o que uma " +
                 "lista de pendências nunca diz — quanto do projeto depende " +
                 "de cada um deles.",
    fachada: "As quatro faces, o que foi combinado para elas e se o que " +
             "está pendurado ali tem como ficar pendurado.",
    catalogo: "O desenho de cada peça que vai ser comprada: perfil, " +
              "parafuso, chapa e tubo, com dimensão, norma e quanto entra na " +
              "obra. Nenhuma imagem foi buscada fora.",
    ambientes: "O que tem em cada cômodo: acabamento, vão, tomada, peça " +
               "hidráulica, ralo, clima e as paredes que o cercam — e onde " +
               "essas decisões, tomadas em lugares diferentes, discordam.",
    cotacao: "Quanto custa, e — o que quase nenhum orçamento diz — quanto " +
             "do que custa foi perguntado a alguém. Hoje: zero. Todo preço " +
             "aqui é hipótese declarada, e o mapa de cotação já está pronto " +
             "para sair.",
    instalacoes: "Metro de tubo, de eletroduto e de linha frigorígena — o " +
                 "que até aqui aparecia só como traçado no desenho e como " +
                 "zero no orçamento. E os conflitos com a estrutura, que " +
                 "alguém resolve no projeto ou o pedreiro resolve na marreta.",
    geotecnia: "Três sondagens, e o veredito que elas deram: o solo não " +
               "reprova por resistência — sobra fator 9 — e sim por " +
               "uniformidade. Quem muda não é o radier, é o que está " +
               "debaixo dele.",
    pluvial: "Quanto do lote é impermeável, quanto a obra passou a mandar " +
             "para a rua e quanto disso fica retido. O que faz o trabalho é " +
             "o orifício, não o volume.",
    marcenaria: "Cada armário, gabinete, closet, cabeceira e painel da casa, " +
                "derivado do caso: módulos, peças, chapas e ferragens. O " +
                "número que importa é a razão material/serviço — se o " +
                "material pelo plano passa do preço sob medida, o preço " +
                "está errado.",
    acustica: "Quem ouve quem, e através de quê. Uma parede de 44 dB com " +
              "uma porta de correr no meio entrega 20: em acústica o elo " +
              "fraco domina.",
    eletrica: "As três fases, o que cada uma carrega, e de quem se compra " +
              "cada família de material. O preço segue hipótese; o " +
              "fornecedor, não.",
    bloqueios: "O que este sistema não entrega, e o que seria preciso para " +
               "entregar. Nenhum destes itens está pela metade: estão fora, " +
               "com o preço declarado.",
  },
  educacional: {
    painel: "Os 415 montantes são verificados um a um contra a carga que de " +
            "fato desce até cada um: área de influência, o que há acima, " +
            "combinação da NBR 8681. A utilização não tem teto — até R28 ela " +
            "era relatada com min(0,99), e um montante 47 % sobrecarregado " +
            "saía como aprovado. O checklist não é opinião: cada item é uma " +
            "consulta ao resultado " +
            "de uma função do motor. Nenhum é marcável à mão — se fosse, " +
            "seria marcado. As notas trazem a fórmula que as produziu, para " +
            "que se possa discordar do critério, e não do número.",
    paineis: "O painel é desenhado aqui a partir de (x, z) e comprimento de " +
             "cada peça — os mesmos números que vão para a perfiladeira. " +
             "Montante a cada 600 mm; onde há vão, entram king, jack, verga e " +
             "cripples, e a modulação é interrompida só o necessário.",
    pecas: "A família diz a função estrutural, não a forma: dois perfis " +
           "idênticos são peças diferentes se um é montante e o outro é jack. " +
           "O código vem da posição, não da ordem de geração — por isso " +
           "sobrevive a uma revisão.",
    corte: "Cada barra de 6 m recebe peças até não caber mais a próxima. O " +
           "resto é perda, e a perda entra no BOM porque foi comprada.",
    montagem: "A ordem sai de uma ordenação topológica das dependências, e " +
              "cada passo é conferido: em nenhum instante a estrutura fica " +
              "instável. Desmontar é a mesma lista ao contrário.",
    logistica: "O centro de gravidade sai de soma de momentos das peças, e é " +
               "ele que decide onde ficam os pontos de içamento.",
    documentos: "Os seis documentos saem do mesmo dado das telas anteriores. " +
                "Trocar o modo de leitura muda a explicação; o valor de " +
                "cálculo é idêntico nos três.",
    parafusos: "Cada junta entre duas peças é enumerada, e cada uma declara " +
               "DE ONDE veio a quantidade. FORÇA é esforço calculado — o " +
               "único caso com defesa técnica. MÍNIMO é o mínimo construtivo, " +
               "onde a junta só posiciona. DECLARADO é junta que transfere " +
               "esforço que o modelo ainda não calcula, e a quantidade " +
               "desenvolve uma fração escrita da capacidade da peça. Somar as " +
               "três num número só esconderia justamente o que importa saber.",
    bloqueios: "Há três respostas possíveis para o que depende do mundo " +
               "externo: simular, não entregar, ou entregar o contrato. " +
               "Simular é a pior — uma funcionalidade falsa é pior que a " +
               "ausência, porque a ausência se vê. Cada contrato traz o " +
               "esquema de dados, o adaptador que recusa inventar número e o " +
               "critério que o valida no dia em que o dado existir.",
  },
  especialista: {
    painel: "Notas normalizadas em [0,100] por funções monotônicas declaradas; " +
            "score geral é média aritmética simples — deliberadamente sem " +
            "pesos, porque peso embutido esconde juízo. Para ponderar, use " +
            "nucleo/otimizacao.ranquear().",
    paineis: "Painelização por trechos admissíveis: o corte só ocorre onde " +
             "não há abertura e onde a modulação permite; quando nenhuma " +
             "posição satisfaz comp ≤ 3600, o painel é emitido inteiro com a " +
             "razão declarada, em vez de cortado sobre o vão.",
    pecas: "Furo de serviço limitado a d ≤ 0,5·bw na alma, afastado das " +
           "extremidades; a verificação de furação é independente da geração.",
    corte: "First-fit decreasing sobre barras de 6 m, consultando sobras " +
           "antes de abrir barra nova. Identidade conferida: bruto = usado + perda.",
    montagem: "Kahn com detecção de ciclo; estabilidade avaliada no prefixo " +
              "de cada passo, não só no estado final.",
    logistica: "Empacotamento por pilhas com limite de massa e altura; o " +
               "limitante (peso ou volume) é declarado, não inferido.",
    documentos: "memorial_compressao() chama a mesma verificacao.compressao() " +
                "nos três modos; a divergência entre modos seria um defeito.",
    materiais: "Espessura NOMINAL é modular; CONSTRUÍDA é a soma das " +
               "camadas, e a isolante não soma porque vive dentro da cavidade " +
               "do montante. A norma vem do material, não da camada: duas " +
               "fontes para o mesmo fato divergem na primeira correção.",
    viabilidade: "Exposição é a fatia do custo que muda quando o dado " +
                 "chegar, não a probabilidade de ele chegar errado — " +
                 "probabilidade aqui seria palpite com aparência de número. E " +
                 "o projeto não está viável em bloco: está liberado para uma " +
                 "coisa e não para outra, e confundir as duas é como se atrasa " +
                 "obra esperando o que não precisava esperar.",
    fachada: "Regra de fachada declarada que ninguém confere é preferência, " +
             "não regra. A conferência achou duas: o acabamento externo " +
             "especificado era PINTURA num volume de 6,15 m, contra a própria " +
             "regra de não haver superfície que exija pintura em altura; e os " +
             "cinco brises existiam no desenho e no 3D sem material, sem massa " +
             "e sem carga.",
    catalogo: "Cada desenho sai da MESMA poligonal de linha média que o " +
              "solver da NBR 14762 integra para achar A, Ix e Wx. A imagem de " +
              "catálogo do fabricante é de um perfil genérico, carrega marca " +
              "de terceiro e continuaria igual depois de a auditoria mudar " +
              "uma espessura — passaria a mentir em silêncio. A designação já " +
              "É a dimensão: Ue 90x40x12x0,95 diz alma 90, aba 40, lábio 12, " +
              "espessura 0,95.",
    ambientes: "Defeito não se distribui por sistema: concentra-se onde dois " +
               "sistemas se encontram, e os dois se encontram DENTRO de um " +
               "cômodo. Na primeira execução este eixo achou 24 divergências " +
               "— 14 de um defeito real (duas regras para contar tomada, e a " +
               "segunda contava por área onde a NBR 5410 conta perímetro) e " +
               "10 de grossura da própria conferência, que somava a área do " +
               "banho na conta da janela do quarto.",
    cotacao: "Compra-se BARRA (kg, com a perda do plano de corte) e " +
             "produz-se PEÇA cortada: são o mesmo aço descrito de dois jeitos, " +
             "e somar os dois é pagar duas vezes. Era o que acontecia — " +
             "R$ 62.664 em 402.196 — e nenhuma faixa de plausibilidade pegava, " +
             "porque 1.571 e 1.359 R$/m² cabem ambos em 600 a 1.800. O que " +
             "pega é identidade: a massa útil dividida pelo aproveitamento dá " +
             "exatamente a massa bruta comprada.",
    instalacoes: "O comprimento é percurso MANHATTAN de cada ponto até a " +
                 "prumada mais próxima, vezes um fator declarado — limite " +
                 "INFERIOR, nunca o percurso do instalador. O clash confronta " +
                 "volume a volume e classifica: interseção não é defeito, em " +
                 "LSF o ramal cruza o montante e se resolve com furo; defeito " +
                 "é o furo que o perfil não comporta. O ramal de esgoto corre " +
                 "SOB o piso, não no plano da parede — roteá-lo na parede " +
                 "produziu 85 falsos críticos que eram erro de traçado.",
    parafusos: "Cisalhamento por NBR 14762 item 8.4: esmagamento das duas " +
               "chapas e basculamento do parafuso, com o modo governante " +
               "nomeado. A razão t2/t1 decide quais modos competem — chapas " +
               "parecidas basculam o parafuso, chapas muito diferentes não.",
    geotecnia: "σadm por N/50, Teixeira-96 e Mello-75, adotada a menor: " +
               "nenhuma nasceu deste solo, e Mello nem é válida fora de " +
               "4 ≤ N ≤ 16. Recalque por somatório de camadas com E = α·K·N " +
               "(Teixeira & Godoy) e Δσ por espraiamento 2:1. A " +
               "profundidade investigada é conferida pelo critério dos 10 % " +
               "da tensão vertical efetiva — pergunta que a NBR 6122 exige e " +
               "quase ninguém faz.",
    marcenaria: "O inventário une ARMARIOS, BANCADAS, LOUCAS (lavatórios), " +
                "LAYOUT (rack, painel, mesa, camas) e o CLOSET. Cada frente é " +
                "dividida em módulos iguais de até 600 mm — a folha de porta " +
                "máxima —, cada módulo vira laterais, base, topo, fundo de " +
                "6 mm, prateleiras, porta e gavetas; as laterais recebem o " +
                "sistema 32 e a porta os canecos de 35. As peças de 15 mm " +
                "passam pelo mesmo nesting das placas de fechamento.",
    pluvial: "Método racional com C ponderado pelas superfícies declaradas, e " +
             "a mesma intensidade que dimensiona calha e descida — fonte " +
             "única. O volume é o excedente (C_pós − C_pré) acumulado no " +
             "tempo de concentração; o orifício sai de Q = Cd·A·√(2gh) " +
             "calibrado na vazão de pré-ocupação, e o esvaziamento é " +
             "integrado com carga variável.",
    acustica: "R composto = −10·log₁₀(Σ Sᵢ·10^(−Rᵢ/10) / ΣS). Adota-se D ≈ R " +
              "(simplificação declarada: a rigor D = R − 10·log(S/A), e em " +
              "ambiente pequeno e mobiliado os termos ficam da mesma ordem). " +
              "Exigência = nível da fonte − limite do receptor pela NBR " +
              "10152. Isto é pré-verificação de projeto, não ensaio de campo " +
              "da NBR 15575-3.",
    eletrica: "Distribuição das fases pela heurística do maior primeiro: " +
              "carga F-N ocupa uma fase, F-F ocupa duas com metade em cada. " +
              "O condutor de proteção sai da Tabela 58 da NBR 5410 em " +
              "degraus — para 35 mm² o PE é 16, e não 17,5, que não existe. " +
              "O cabo é escolhido pelo disjuntor, não pela demanda: quem " +
              "protege o cabo é o disjuntor.",
    bloqueios: "Adaptador vazio levanta SemFonteDeDados com código, motivo e " +
               "remédio; receber() já valida tipo, unidade, domínio e campo " +
               "desconhecido hoje, antes de o dado existir. A auditoria chama " +
               "consultar() nos dez e reprova qualquer retorno, None inclusive.",
  },
};

function num(v, casas) {
  return Number(v).toLocaleString("pt-BR",
    {minimumFractionDigits: casas || 0, maximumFractionDigits: casas || 0});
}
function corFam(f) { return (ENG.cores && ENG.cores[f]) || "#8a94a6"; }
function esc2(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function leitura(v) {
  const t = LEITURA[engModo][v];
  return t ? `<p class="desenho cap" style="border:none;padding:0;margin:0 0 12px">${esc2(t)}</p>` : "";
}
function barraModos() {
  return '<div class="modos-leitura" role="group" aria-label="Modo de leitura">' +
    ["executivo", "educacional", "especialista"].map(m =>
      `<button type="button" data-leitura="${m}" aria-pressed="${m === engModo}">${m}</button>`
    ).join("") + "</div>";
}
'''
JS_ENG += r'''
// --------------------------------------------------------- painel de controle
function vistaPainel() {
  const L = ENG.liberacao, S = ENG.scores;
  const cartoes = ENG.resumo.map(r =>
    `<div class="cartao"><span class="rot">${esc2(r.rotulo)}</span>
       <span class="val">${num(r.valor, Number.isInteger(r.valor) ? 0 : 1)}</span>
       <span class="uni">${esc2(r.unidade)}</span></div>`).join("");
  const notas = Object.keys(S).map(k => {
    const s = S[k], ruim = s.nota < 70;
    return `<div class="nota${ruim ? " ruim" : ""}">
      <h4>${esc2(k)}</h4>
      <div class="n">${s.nota}<small> / 100</small></div>
      <div class="barra-nota"><i style="width:${s.nota}%"></i></div>
      <p class="form">${esc2(s.formula || s.motivo || "")}</p></div>`;
  }).join("");
  const itens = L.itens.map(i =>
    `<li class="${i.status === "OK" ? "" : "mau"}">
       <span class="m">${i.status === "OK" ? "✓" : "✕"}</span>
       <span>${esc2(i.descricao)}</span>
       <span class="st">${esc2(i.item)}</span></li>`).join("");
  return `${barraModos()}${leitura("painel")}
    <div class="eng-sec"><h3>Números do modelo</h3><div class="cartoes">${cartoes}</div></div>
    ${blocoEstrutura()}
    ${blocoVerificacao()}
    <div class="eng-sec"><h3>Liberação</h3>
      <div class="selo${L.liberado ? "" : " nao"}" id="seloLiberacao">
        <b>${esc2(L.situacao)}</b>
        <span>score geral ${ENG.score_geral}/100 · revisão ${esc2(ENG.revisao)}</span></div>
      <ul class="check" id="checklist">${itens}</ul>${blocoPendencias()}</div>
    <div class="eng-sec"><h3>Seis notas, seis fórmulas</h3>
      <div class="notas">${notas}</div></div>`;
}

function blocoPendencias() {
  // O 18o item do checklist. Os 16 primeiros perguntam se o que esta no modelo
  // esta certo; o 17o, se o que precisa estar la esta; este, se o que o projeto
  // DECLARA que falta permite fabricar. Sem ele a tela dizia "LIBERADO PARA
  // FABRICACAO" com a ART e o nesting abertos no proprio caderno.
  const P = ENG.pendencias;
  if (!P || !P.abertas.length) return "";
  const linha = d =>
    `<li><span class="m" style="color:${d.bloqueia ? "var(--alert)" : "var(--ink-faint)"}">${d.bloqueia ? "✕" : "○"}</span>
       <span>#${esc2(d.n)} ${esc2(d.titulo)}<br>
         <span style="color:var(--ink-faint);font-size:12px">${esc2(d.impacto)}</span></span>
       <span class="st">${d.bloqueia ? esc2(d.bloqueia) : "não bloqueia"}</span></li>`;
  return `<p class="conta" style="display:block;margin:14px 0 4px;line-height:1.55">
      <b>${P.abertas.length} pendências declaradas em aberto</b>, das quais
      <b style="color:var(--alert)">${P.bloqueantes.length}</b> trancam a
      ${esc2(P.portao)}. Consistência interna não é autorização: até aqui o
      checklist media só o modelo, e anunciava fabricação liberada com a ART do
      cálculo estrutural e o nesting codificado abertos.</p>
    <ul class="check">${P.abertas.map(linha).join("")}</ul>`;
}

function blocoVerificacao() {
  const P = ENG.plausibilidade, C = ENG.completude;
  if (!P || !C) return "";
  const faixas = P.itens.map(x => {
    const pos = Math.max(0, Math.min(100,
      (x.valor - x.minimo) / (x.maximo - x.minimo) * 100));
    return `<div style="margin:0 0 9px" title="${esc2(x.fonte)}">
      <div style="font-family:var(--mono);font-size:11px;display:flex;gap:8px">
        <span>${esc2(x.cod)}</span>
        <span style="margin-left:auto;color:${x.dentro ? "var(--ink-faint)" : "var(--alert)"}">
          ${num(x.valor, 2)} ${esc2(x.unidade)}</span></div>
      <div style="position:relative;height:8px;background:var(--rule-soft)">
        <i style="position:absolute;left:0;right:0;top:0;bottom:0;
          background:${x.dentro ? "var(--accent-soft)" : "var(--alert-soft)"}"></i>
        <i style="position:absolute;left:${pos}%;top:-2px;width:3px;height:12px;
          background:${x.dentro ? "var(--accent)" : "var(--alert)"}"></i></div>
      <div style="font-family:var(--mono);font-size:9.5px;color:var(--ink-faint);
        display:flex"><span>${num(x.minimo, 0)}</span>
        <span style="margin-left:auto">${num(x.maximo, 0)}</span></div></div>`;
  }).join("");
  const sistemas = C.itens.map(i =>
    `<li class="${i.situacao === "AUSENTE" ? "mau" : ""}">
      <span class="m">${i.situacao === "AUSENTE" ? "✕" :
        (i.situacao === "NAO SE APLICA" ? "–" : "✓")}</span>
      <span>${esc2(i.nome)}</span>
      <span class="st">${i.n || ""}</span></li>`).join("");
  return `<div class="eng-sec"><h3>As duas perguntas que faltavam</h3>
    <div class="eng-grid" style="grid-template-columns:1fr 1fr">
      <div>
        <h3 style="margin-bottom:8px">Isto é possível? · ${P.n - P.fora} de ${P.n} na faixa</h3>
        ${faixas}
        <p class="conta" style="display:block;margin-top:4px;line-height:1.5">
          Fora da faixa não reprova: obriga a justificar. Passe o mouse para
          ver a fonte de cada faixa.</p></div>
      <div>
        <h3 style="margin-bottom:8px">Isto está aqui? · ${C.presentes} de ${C.n}</h3>
        <ul class="check" id="sistemas" style="grid-template-columns:1fr">${sistemas}</ul>
        <p class="conta" style="display:block;margin-top:10px;line-height:1.5">
          A lista é do <b>sistema construtivo</b>, escrita antes de olhar o
          modelo. Foi ela que acusou, na primeira execução, que a escada não
          tinha estrutura.</p></div>
    </div></div>`;
}

function blocoEstrutura() {
  const E = ENG.estrutura;
  if (!E) return "";
  const maior = Math.max(...E.histograma.map(h => h.n)) || 1;
  const barras = E.histograma.map(h => {
    const rot = h.ate > 1 ? "acima de 1,00" :
      `${h.de.toFixed(2).replace(".", ",")} – ${h.ate.toFixed(2).replace(".", ",")}`;
    const cor = h.ate > 1 ? "var(--alert)" : (h.de >= 0.9 ? "#d98324" : "#3f6fb5");
    return `<div style="display:grid;grid-template-columns:104px 1fr 44px;gap:8px;
      align-items:center;font-family:var(--mono);font-size:11px;padding:2px 0">
      <span>${rot}</span>
      <span style="height:10px;background:var(--rule-soft)"><i style="display:block;
        height:100%;width:${(h.n / maior * 100).toFixed(1)}%;background:${cor}"></i></span>
      <span style="text-align:right">${h.n}</span></div>`;
  }).join("");
  const tabelaHist = `<details style="margin-top:8px"><summary class="conta"
      style="cursor:pointer">ver como tabela</summary>
      <table class="tabela" style="margin-top:6px"><thead><tr><th>faixa</th>
        <th>montantes</th></tr></thead><tbody>${E.histograma.map(h =>
        `<tr><td>${h.ate > 1 ? "acima de 1,00" :
          h.de.toFixed(2).replace(".", ",") + " – " + h.ate.toFixed(2).replace(".", ",")}</td>
          <td>${h.n}</td></tr>`).join("")}</tbody></table></details>`;
  const g = E.governa;
  const jb = E.jambas.map(j =>
    `<li><b>${esc2(j.painel)}</b> — ${esc2(j.solucao)} ·
      N<sub>sd</sub> ${num(j.nsd, 1)} kN · u ${j.u.toFixed(2).replace(".", ",")}
      ${j.sku_nova ? "· SKU nova" : ""}
      <span class="sub">${esc2(j.motivo)}</span></li>`).join("");
  const hip = E.hipoteses.map(h => `<li>${esc2(h)}</li>`).join("");
  return `<div class="eng-sec"><h3>Verificação estrutural — ${E.n} montantes, um a um</h3>
    <div class="selo${E.aprovado ? "" : " nao"}" style="margin-bottom:12px">
      <b>${E.reprovadas} reprovam de ${E.n}</b>
      <span>mediana ${E.mediana.toFixed(2).replace(".", ",")} ·
        máxima ${E.maxima.toFixed(2).replace(".", ",")} ·
        alvo de projeto ${E.u_alvo.toFixed(2).replace(".", ",")} ·
        aprovação pela norma 1,00</span></div>
    <div class="eng-grid" style="grid-template-columns:1fr 1fr">
      <div><h3 style="margin-bottom:8px">Distribuição de utilização</h3>
        ${vizUtilizacao(E)}${tabelaHist}
        <p class="conta" style="display:block;margin-top:10px;line-height:1.5">
          Governa <b>${esc2(g.peca)}</b> (${esc2(g.familia)}, ${esc2(g.perfil)}):
          N<sub>sd</sub> ${num(g.nsd, 1)} kN de ${num(g.nrd, 1)} kN resistentes,
          modo <b>${esc2(g.modo)}</b>, k = ${g.k.toFixed(2).replace(".", ",")},
          combinação ${esc2(g.combinacao)}.</p></div>
      <div><h3 style="margin-bottom:8px">Jambas dimensionadas pela carga</h3>
        <ul class="lista" style="max-height:none">${jb || "<li><button type='button' disabled>nenhuma precisou de reforço</button></li>"}</ul>
        <h3 style="margin:14px 0 8px">Hipóteses de caminho de carga</h3>
        <ul style="margin:0;padding-left:18px;font-size:12.5px;color:var(--ink-soft);
          line-height:1.55">${hip}</ul></div>
    </div></div>`;
}

// --------------------------------------------------------------- painéis
function svgPainel(p) {
  const M = 60;
  const W = p.comp, H = p.altura;
  const pecas = p.pecas.map(q => {
    const bw = q.vertical ? 90 : 92;
    const x = q.x, y = H - q.z - (q.vertical ? q.comp : bw);
    const w = q.vertical ? bw : q.comp, h = q.vertical ? q.comp : bw;
    return `<rect x="${x}" y="${Math.max(0, y)}" width="${w}" height="${h}"
      fill="${corFam(q.familia)}" stroke="#0d1114" stroke-width="4"
      opacity=".92"><title>${esc2(q.cod)} · ${esc2(q.familia)} · ${esc2(q.perfil)} · ${q.comp} mm</title></rect>`;
  }).join("");
  const furos = p.pecas.flatMap(q => (q.furos || []).map(f => {
    const cx = q.vertical ? q.x + 45 : q.x + f.x;
    const cy = q.vertical ? H - q.z - f.x : H - q.z - 46;
    return `<circle cx="${cx}" cy="${cy}" r="${Math.max(14, f.d / 2)}"
      fill="none" stroke="#c4491f" stroke-width="5"/>`;
  })).join("");
  const abs = p.aberturas.map(a => {
    const x = a.centro - a.larg / 2;
    return `<g><rect x="${x}" y="${H - a.peitoril - a.alt}" width="${a.larg}"
      height="${a.alt}" fill="none" stroke="#c4491f" stroke-width="9"
      stroke-dasharray="40 24"/>
      <text x="${a.centro}" y="${H - a.peitoril - a.alt / 2}" fill="#c4491f"
        font-size="96" text-anchor="middle" font-family="monospace"
        dominant-baseline="middle">${esc2(a.tipo)}</text></g>`;
  }).join("");
  const cotas = `<g stroke="currentColor" stroke-width="4" opacity=".55"
      font-family="monospace" font-size="86" fill="currentColor">
      <line x1="0" y1="${H + 150}" x2="${W}" y2="${H + 150}"/>
      <text x="${W / 2}" y="${H + 250}" text-anchor="middle">${W} mm</text>
      <line x1="${-150}" y1="0" x2="${-150}" y2="${H}"/>
      <text x="${-190}" y="${H / 2}" text-anchor="end">${H} mm</text></g>`;
  return `<svg viewBox="${-M - 300} ${-M} ${W + 2 * M + 400} ${H + 2 * M + 300}"
    role="img" aria-label="Elevação do painel ${esc2(p.cod)}">
    <rect x="0" y="0" width="${W}" height="${H}" fill="none"
      stroke="currentColor" stroke-width="6" opacity=".35"/>
    ${pecas}${furos}${abs}${cotas}</svg>`;
}

function vistaPaineis() {
  const lista = ENG.paineis.map(p =>
    `<li><button type="button" data-painel="${esc2(p.cod)}"
       aria-current="${p.cod === painelSel}">${esc2(p.cod)}
       <span class="sub">${p.comp} mm · ${p.n_pecas} peças · ${num(p.massa, 1)} kg${
         p.aberturas.length ? " · vão" : ""}</span></button></li>`).join("");
  const p = ENG.paineis.find(q => q.cod === painelSel) || ENG.paineis[0];
  const fams = Object.keys(p.familias).map(f =>
    `<span><i style="background:${corFam(f)}"></i>${esc2(f)} ${p.familias[f]}</span>`).join("");
  const linhas = p.pecas.map(q =>
    `<tr><td><span class="chip" style="background:${corFam(q.familia)}"></span>${esc2(q.cod)}</td>
      <td>${esc2(q.familia)}</td><td>${esc2(q.perfil)}</td><td>${q.comp}</td>
      <td>${q.x}</td><td>${q.z}</td><td>${q.massa === undefined ? "—" : num(q.massa, 2)}</td>
      <td>${(q.furos || []).length}</td></tr>`).join("");
  return `${barraModos()}${leitura("paineis")}
    <div class="eng-grid">
      <ul class="lista">${lista}</ul>
      <div>
        <div class="desenho">${svgPainel(p)}
          <p class="cap"><b>${esc2(p.cod)}</b> · parede ${esc2(p.parede)} ·
            ${p.externa ? "externa" : "interna"} · ${p.comp} × ${p.altura} mm ·
            espessura ${p.esp} mm · ${num(p.massa, 1)} kg ·
            <b>${num(p.parafusos || 0)} parafusos</b> em ${(p.juntas || []).length} juntas ·
            ${p.horizontal ? "horizontal" : "vertical"} em planta
            ${p.obs ? "<br>" + esc2(p.obs) : ""}</p>
          <div class="legenda">${fams}</div></div>
        <div class="rolagem" style="margin-top:12px">
          <table class="tabela"><thead><tr><th>junta</th><th>peças</th>
            <th>n</th><th>origem</th><th>parafuso</th></tr></thead><tbody>${
              (p.juntas || []).map(j => `<tr><td>${esc2(j.tipo)}</td>
                <td>${j.pecas.map(esc2).join(" + ")}</td><td>${j.n}</td>
                <td>${esc2(j.origem)}</td><td>${esc2(j.parafuso)}</td></tr>`).join("")
            }</tbody></table></div>
        <div class="rolagem" style="margin-top:12px">
          <table class="tabela"><thead><tr><th>peça</th><th>família</th>
            <th>perfil</th><th>comp</th><th>x</th><th>z</th><th>kg</th><th>furos</th>
            </tr></thead><tbody>${linhas}</tbody></table></div>
      </div></div>`;
}
'''
JS_ENG += r'''
// ------------------------------------------------------------------ peças
let pecaOrd = {campo: "cod", asc: true}, pecaBusca = "", pecaFam = "", pecaPav = "";
function todasPecas() {
  // as pecas de parede MAIS as que nao pertencem a painel nenhum — vigamento
  // de entrepiso, cobertura e contraventamento. Percorrer so os paineis
  // mostrava 805 de 1.011 e nao fechava com a contagem por familia
  return ENG.paineis.flatMap(p => p.pecas.map(q =>
    Object.assign({painel: p.cod, pav: p.pav}, q)))
    .concat((ENG.extras || []).map(q =>
      Object.assign({}, q, {painel: q.plano})));
}
function vistaPecas() {
  const todas = todasPecas();
  const fams = [...new Set(todas.map(q => q.familia))].sort();
  let alvo = todas.filter(q =>
    (!pecaFam || q.familia === pecaFam) &&
    (!pecaPav || q.pav === pecaPav) &&
    (!pecaBusca || (q.cod + " " + q.perfil + " " + q.familia + " " + q.painel)
        .toLowerCase().includes(pecaBusca.toLowerCase())));
  alvo.sort((a, b) => {
    const x = a[pecaOrd.campo], y = b[pecaOrd.campo];
    const c = (typeof x === "number" && typeof y === "number")
      ? x - y : String(x).localeCompare(String(y));
    return pecaOrd.asc ? c : -c;
  });
  const massa = alvo.reduce((s, q) => s + (q.massa || 0), 0);
  const cols = [["cod", "peça"], ["painel", "painel"], ["familia", "família"],
                ["perfil", "perfil"], ["comp", "comp mm"], ["massa", "kg"],
                ["marcacao", "marcação"]];
  const cab = cols.map(([c, t]) =>
    `<th data-ord="${c}">${t}${pecaOrd.campo === c ? (pecaOrd.asc ? " ▲" : " ▼") : ""}</th>`).join("");
  const corpo = alvo.slice(0, pecaLimite).map(q =>
    `<tr><td><span class="chip" style="background:${corFam(q.familia)}"></span>${esc2(q.cod)}</td>
      <td>${esc2(q.painel)}</td><td>${esc2(q.familia)}</td><td>${esc2(q.perfil)}</td>
      <td>${q.comp}</td><td>${q.massa === undefined ? "—" : num(q.massa, 2)}</td>
      <td>${esc2(q.marcacao || "")}</td></tr>`).join("");
  const porFam = Object.keys(ENG.familias).sort((a, b) => ENG.familias[b] - ENG.familias[a]);
  const maior = Math.max(...porFam.map(f => ENG.familias[f]));
  const hist = porFam.map(f =>
    `<div style="display:grid;grid-template-columns:118px 1fr 46px;gap:8px;align-items:center;
       font-family:var(--mono);font-size:11px;padding:2px 0">
      <span>${esc2(f)}</span>
      <span style="height:9px;background:var(--rule-soft)"><i style="display:block;height:100%;
        width:${(ENG.familias[f] / maior * 100).toFixed(1)}%;background:${corFam(f)}"></i></span>
      <span style="text-align:right">${ENG.familias[f]}</span></div>`).join("");
  return `${barraModos()}${leitura("pecas")}
    <div class="filtros">
      <input type="search" id="buscaPeca" placeholder="peça, perfil, painel" value="${esc2(pecaBusca)}">
      <select id="filFam"><option value="">todas as famílias</option>${
        fams.map(f => `<option${f === pecaFam ? " selected" : ""}>${esc2(f)}</option>`).join("")}</select>
      <select id="filPav"><option value="">os dois pavimentos</option>
        <option value="T"${pecaPav === "T" ? " selected" : ""}>térreo</option>
        <option value="S"${pecaPav === "S" ? " selected" : ""}>superior</option></select>
      <span class="conta">${alvo.length} de ${todas.length} peças · ${num(massa, 1)} kg${
        alvo.length > pecaLimite ? ` · mostrando ${pecaLimite}` : ""}</span></div>
    <div class="rolagem"><table class="tabela" data-ordena="propria">
      <thead><tr>${cab}</tr></thead>
      <tbody>${corpo}</tbody></table></div>
    ${alvo.length > pecaLimite ? `<div style="margin-top:10px">
      <button class="btn" id="maisPecas">mostrar mais ${
        Math.min(300, alvo.length - pecaLimite)} de ${alvo.length - pecaLimite}
        restantes</button></div>` : ""}
    <div class="eng-sec" style="margin-top:22px"><h3>Distribuição por família</h3>${hist}</div>`;
}

// ------------------------------------------------------------- plano de corte
let corteLim = 60;
function vistaCorte() {
  const N = ENG.nesting;
  const barras = N.barras.slice(0, corteLim).map(b => {
    let acum = 0;
    const segs = b.pecas.map((q, i) => {
      const x = acum / b.bruto * 100; acum += q.comp;
      return `<span title="${esc2(q.cod)} · ${q.comp} mm" style="position:absolute;left:${x}%;
        width:${(q.comp / b.bruto * 100).toFixed(3)}%;top:0;bottom:0;
        background:${i % 2 ? "#3f6fb5" : "#4d8fd6"};border-right:1px solid var(--surface)"></span>`;
    }).join("");
    const perda = b.bruto - b.usado;
    return `<div style="margin:0 0 6px">
      <div style="font-family:var(--mono);font-size:10.5px;color:var(--ink-faint);
        display:flex;gap:10px"><span>${esc2(b.cod)}</span><span>${esc2(b.perfil)}</span>
        <span style="margin-left:auto">sobra ${num(perda)} mm${
          b.origem !== "nova" ? " · de sobra" : ""}</span></div>
      <div style="position:relative;height:15px;background:var(--alert-soft);
        border:1px solid var(--rule-soft)">${segs}</div></div>`;
  }).join("");
  return `${barraModos()}${leitura("corte")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Aproveitamento</span>
        <span class="val">${(N.aproveitamento * 100).toFixed(1)}</span><span class="uni">%</span></div>
      <div class="cartao"><span class="rot">Barras</span>
        <span class="val">${N.n_barras}</span><span class="uni">de 6 m</span></div>
      <div class="cartao"><span class="rot">Comprado</span>
        <span class="val">${num(N.bruto / 1000)}</span><span class="uni">m lineares</span></div>
      <div class="cartao"><span class="rot">Usado</span>
        <span class="val">${num(N.usado / 1000)}</span><span class="uni">m lineares</span></div>
      <div class="cartao"><span class="rot">Perda</span>
        <span class="val">${num(N.perda / 1000)}</span><span class="uni">m lineares</span></div>
    </div>
    <div class="eng-sec"><h3>Barras — azul é peça, vermelho é o que sobra</h3>${barras}
      ${N.n_barras > corteLim ? `<button class="btn" id="maisBarras">mostrar mais
        (${N.n_barras - corteLim} restantes)</button>` : ""}</div>`;
}
'''
JS_ENG += r'''
// -------------------------------------------------------------- montagem
let passoAtual = 0;
function svgPlanta(ate) {
  const ps = ENG.paineis;
  const xs = ps.flatMap(p => [p.x, p.x + (p.horizontal ? p.comp : 0)]);
  const ys = ps.flatMap(p => [p.y, p.y + (p.horizontal ? 0 : p.comp)]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const y0 = Math.min(...ys), y1 = Math.max(...ys);
  const feitos = new Set(ENG.montagem.passos.slice(0, ate)
    .map(s => s.painel).filter(Boolean));
  const linhas = ps.map(p => {
    const X2 = p.x + (p.horizontal ? p.comp : 0);
    const Y2 = p.y + (p.horizontal ? 0 : p.comp);
    const pronto = feitos.has(p.cod);
    return `<line x1="${p.x}" y1="${p.y}" x2="${X2}" y2="${Y2}"
      stroke="${pronto ? (p.pav === "S" ? "#c4491f" : "#3f6fb5") : "currentColor"}"
      stroke-opacity="${pronto ? 1 : 0.16}" stroke-width="${pronto ? 190 : 120}"
      stroke-linecap="butt"><title>${esc2(p.cod)} · ${p.comp} mm</title></line>`;
  }).join("");
  const M = 800;
  return `<svg viewBox="${x0 - M} ${y0 - M} ${x1 - x0 + 2 * M} ${y1 - y0 + 2 * M}"
    role="img" aria-label="Planta dos painéis, passo ${ate}">${linhas}</svg>`;
}
function vistaMontagem() {
  const M = ENG.montagem;
  const p = M.passos[Math.min(passoAtual, M.passos.length - 1)] || null;
  const linhas = M.passos.map((s, i) =>
    `<li><button type="button" data-passo="${i}" aria-current="${i === passoAtual}">
      ${String(s.passo).padStart(3, "0")} · ${esc2(s.descricao)}
      <span class="sub">${esc2(s.tipo)} · ${num(s.massa, 1)} kg ·
        ${s.duracao_h.toFixed(2)} h · acum ${s.acumulado_h.toFixed(1)} h</span></button></li>`).join("");
  return `${barraModos()}${leitura("montagem")}
    <div class="filtros">
      <button class="btn" id="playMont">${animar ? "⏸ pausar" : "▶ animar"}</button>
      <button class="btn" id="passoMenos">◀</button>
      <button class="btn" id="passoMais">▶</button>
      <button class="btn" id="passoZero">reiniciar</button>
      <span class="conta">passo ${passoAtual} de ${M.n_passos} ·
        ${p ? p.acumulado_h.toFixed(1) : "0,0"} h de ${M.horas} h ·
        ${p ? (p.progresso * 100).toFixed(0) : 0} %</span></div>
    <div class="eng-sec"><h3>Curva de montagem — ${M.n_passos} passos,
      ${num(M.horas, 1)} h acumuladas</h3>
      ${vizMontagem(M.passos, M.horas)}</div>
    <div class="eng-grid">
      <ul class="lista" id="listaPassos">${linhas}</ul>
      <div class="desenho">${svgPlanta(passoAtual)}
        <p class="cap">${p ? `<b>${esc2(p.cod)}</b> · ${esc2(p.descricao)} ·
          ferramenta: ${esc2(p.ferramenta)} · ${num(p.massa, 1)} kg`
          : "nenhum painel montado ainda"}<br>
          azul é térreo, vermelho é superior; o que ainda não subiu fica apagado.</p></div>
    </div>`;
}

// -------------------------------------------------------------- logística
function vistaLogistica() {
  const L = ENG.logistica, E = ENG.emissao, D = ENG.desmontabilidade;
  const b = (rot, v, extra) =>
    `<div style="margin:0 0 11px"><div style="font-family:var(--mono);font-size:11px;
      display:flex"><span>${rot}</span><span style="margin-left:auto;color:var(--ink-faint)">
      ${(v * 100).toFixed(1)} %${extra || ""}</span></div>
      <div style="height:11px;background:var(--rule-soft)"><i style="display:block;height:100%;
        width:${Math.min(100, v * 100).toFixed(1)}%;background:${v > 1 ? "var(--alert)" : "var(--accent)"}"></i></div></div>`;
  const co2 = Object.keys(E).filter(k => k !== "total" && typeof E[k] === "number");
  const maiorC = Math.max(...co2.map(k => E[k]));
  const linhas = co2.map(k =>
    `<div style="display:grid;grid-template-columns:120px 1fr 78px;gap:8px;align-items:center;
      font-family:var(--mono);font-size:11px;padding:2px 0"><span>${esc2(k)}</span>
      <span style="height:9px;background:var(--rule-soft)"><i style="display:block;height:100%;
        width:${(E[k] / maiorC * 100).toFixed(1)}%;background:#6fae7c"></i></span>
      <span style="text-align:right">${num(E[k])} kg</span></div>`).join("");
  return `${barraModos()}${leitura("logistica")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">${L.modo === "carreta" ? "Carreta" : "Container"}</span>
        <span class="val" style="font-size:15px">${esc2(L.veiculo || L.container)}</span>
        <span class="uni">${L.volumes} painéis · ${L.viagens} ${L.modo === "carreta" ? "viagens" : "pilhas"}</span></div>
      <div class="cartao"><span class="rot">Massa embarcada</span>
        <span class="val">${num(L.massa)}</span><span class="uni">kg</span></div>
      <div class="cartao"><span class="rot">Limitante</span>
        <span class="val" style="font-size:15px">${esc2(L.limitante)}</span>
        <span class="uni">é o que enche primeiro</span></div>
      <div class="cartao"><span class="rot">Rejeitados</span>
        <span class="val">${L.rejeitados}</span><span class="uni">não couberam</span></div>
      <div class="cartao"><span class="rot">Desmontabilidade</span>
        <span class="val">${D.indice.toFixed(2)}</span><span class="uni">${esc2(D.classe)}</span></div>
    </div>
    ${L.motivo ? `<p style="font-size:12px;color:var(--ink-faint);margin:0 0 12px">${esc2(L.motivo)}</p>` : ""}
    <div class="eng-sec"><h3>Ocupação do ${L.modo === "carreta" ? "veículo" : "container"}</h3>
      ${b("peso", L.uso_peso)}${b("volume", L.uso_volume)}</div>
    <div class="eng-sec"><h3>CO₂e incorporado — ${num(E.total)} kg no total (fatores H)</h3>
      ${linhas}</div>`;
}

// ------------------------------------------------------------- documentos
const DOCS = [["memorial", "memorial descritivo"], ["lista_de_pecas", "lista de peças"],
  ["plano_de_corte", "plano de corte"], ["packing_list", "packing list"],
  ["manual", "manual de montagem"], ["inspecao", "relatório de inspeção"],
  ["mapa_de_cotacao", "mapa de cotação"]];
function vistaDocumentos() {
  const botoes = DOCS.map(([k, t]) =>
    `<button class="btn" data-doc="${k}" ${k === docSel ? 'style="border-color:var(--accent);color:var(--accent)"' : ""}>${t}</button>`).join("");
  const texto = docSel === "memorial_compressao"
    ? ENG.memoriais[engModo] : ENG.documentos[docSel];
  return `${barraModos()}${leitura("documentos")}
    <div class="docs">${botoes}
      <button class="btn" data-doc="memorial_compressao"
        ${docSel === "memorial_compressao" ? 'style="border-color:var(--accent);color:var(--accent)"' : ""}>memorial de cálculo (${engModo})</button></div>
    <pre class="doc-txt">${esc2(texto || "")}</pre>`;
}
'''
JS_ENG += r'''
// --------------------------------------------------------------- materiais
let compSel = null;
function vistaMateriais() {
  const M = ENG.materiais;
  if (!M) return barraModos() + "<p class='conta'>sem especificacao de material</p>";
  const c = M.composicoes.find(x => x.cod === compSel) || M.composicoes[0];
  const lista = M.composicoes.map(x =>
    `<li><button type="button" data-comp="${esc2(x.cod)}"
       aria-current="${x.cod === c.cod}">${esc2(x.cod)} — ${esc2(x.nome)}
       <span class="sub">${num(x.area, 1)} m² · ${x.esp_nominal} mm ·
         Rw ${x.rw}</span></button></li>`).join("");
  const cam = c.camadas.map(k =>
    `<tr><td>${esc2(k.nome)}</td><td>${num(k.espessura, 1)} mm</td>
      <td>${k.n > 1 ? k.n + "×" : "—"}</td><td>${esc2(k.funcao)}</td>
      <td>${esc2(k.face)}</td><td>${esc2(k.norma)}</td>
      <td>${k.formato.length ? k.formato.join(" × ") : "—"}</td></tr>`).join("");
  const pg = M.paginacao.map(p =>
    `<tr><td>${esc2(p.nome)} ${num(p.espessura, 1)} mm</td>
      <td>${esc2(p.formato)}</td><td>${num(p.placas)}</td>
      <td>${num(p.inteiras)} + ${num(p.de_retalho)}</td>
      <td>${num(p.area_util, 1)}</td><td>${num(p.area_bruta, 1)}</td>
      <td>${(p.aproveitamento * 100).toFixed(1)} %</td></tr>`).join("");
  const esq = M.esquadrias.map(e =>
    `<tr><td>${esc2(e.tipo)}</td><td>${e.n}</td>
      <td>${e.larg} × ${e.alt}</td><td>${esc2(e.tipologia)}</td>
      <td>${num(e.area_vidro * e.n, 2)}</td>
      <td style="white-space:normal">${esc2(e.vidro || "—")}</td>
      <td style="white-space:normal;max-width:26ch">${esc2(e.motivo || "")}</td></tr>`).join("");
  const cob = M.cobertura, imp = M.impermeabilizacao;
  return `${barraModos()}${leitura("materiais")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Placas</span>
        <span class="val">${num(M.placas)}</span><span class="uni">inteiras</span></div>
      <div class="cartao"><span class="rot">Junta</span>
        <span class="val">${num(M.junta_m)}</span><span class="uni">m de fita</span></div>
      <div class="cartao"><span class="rot">Caixilho</span>
        <span class="val">${num(M.esq_caixilho_m)}</span><span class="uni">m</span></div>
      <div class="cartao"><span class="rot">Vidro</span>
        <span class="val">${num(M.esq_vidro_m2, 1)}</span><span class="uni">m²</span></div>
      <div class="cartao"><span class="rot">Calha e rufo</span>
        <span class="val">${num(cob.calha_m + cob.rufo_m, 1)}</span><span class="uni">m</span></div>
      <div class="cartao"><span class="rot">Impermeabilização</span>
        <span class="val">${num(imp.area, 1)}</span><span class="uni">m²</span></div>
      <div class="cartao"><span class="rot">Concreto</span>
        <span class="val">${num(M.fundacao.volume_m3, 1)}</span>
        <span class="uni">m³ de radier</span></div>
    </div>
    <div class="eng-sec"><h3>Fundação — quantidade de uma espessura que é (H)</h3>
      <p class="conta" style="display:block;line-height:1.6">
        Radier de <b>${M.fundacao.espessura} mm</b>, fck ${M.fundacao.fck} MPa,
        aço ${esc2(M.fundacao.aco)} · ${num(M.fundacao.area, 1)} m² ·
        <b>${num(M.fundacao.volume_m3, 1)} m³</b> de concreto ·
        ${num(M.fundacao.aco_kg)} kg de aço · ${num(M.fundacao.tela_m2)} m² de
        tela ${esc2(M.fundacao.tela)} · ${num(M.fundacao.lastro_m3, 1)} m³ de
        lastro.<br>
        ${M.fundacao.hipoteses.map(h => "— " + esc2(h)).join("<br>")}<br>
        <b>Pendência:</b> ${esc2(M.fundacao.pendencia)}.</p></div>
    <div class="eng-grid"><ul class="lista">${lista}</ul>
      <div>
        <div class="desenho"><p class="cap" style="font-size:13px">
          <b>${esc2(c.cod)} — ${esc2(c.nome)}</b><br>
          ${num(c.area, 1)} m² · nominal <b>${c.esp_nominal} mm</b>,
          construída <b>${num(c.esp_construida, 1)} mm</b>
          (folga ${num(c.esp_nominal - c.esp_construida, 1)}) · Rw ${c.rw} dB<br>
          <i>${esc2(c.onde)}</i></p></div>
        <div class="rolagem" style="margin-top:12px">
          <table class="tabela"><thead><tr><th>material</th><th>esp</th>
            <th>chapas</th><th>função</th><th>face</th><th>norma</th>
            <th>formato</th></tr></thead><tbody>${cam}</tbody></table></div>
      </div></div>
    <div class="eng-sec" style="margin-top:22px"><h3>Paginação — placa inteira, não metro quadrado</h3>
      <div class="rolagem"><table class="tabela"><thead><tr><th>material</th>
        <th>formato</th><th>placas</th><th>inteiras + retalho</th>
        <th>útil m²</th><th>comprada m²</th><th>aproveitamento</th>
        </tr></thead><tbody>${pg}</tbody></table></div></div>
    <div class="eng-sec"><h3>Esquadrias — ${M.esquadrias.reduce((s, e) => s + e.n, 0)} unidades</h3>
      <div class="rolagem"><table class="tabela"><thead><tr><th>tipo</th>
        <th>n</th><th>vão mm</th><th>tipologia</th><th>vidro m²</th>
        <th>especificação</th><th>por quê</th></tr></thead>
        <tbody>${esq}</tbody></table></div>
      <p class="conta" style="display:block;margin-top:10px;line-height:1.5">
        Desempenho pela ${esc2(M.desempenho.norma)}: estanqueidade à água, ao ar
        e resistência à carga de vento <b>exigem ensaio do sistema</b> e entram
        como exigência declarada, nunca como valor. Uma classificação inventada
        seria indistinguível de uma ensaiada.</p></div>
    ${imp.aviso ? `<div class="selo nao"><b>Impermeabilização incompleta</b>
      <span>${esc2(imp.aviso)}</span></div>` : ""}`;
}

// --------------------------------------------------------------- parafusos
const COR_ORIGEM = {FORCA: "#0a6a4a", MINIMO: "#8a94a6", DECLARADO: "#d98324"};
function vistaParafusos() {
  const J = ENG.juntas;
  if (!J) return barraModos() + "<p class='conta'>sem programa de juntas</p>";
  const totalO = J.por_origem.reduce((s, o) => s + o.n, 0) || 1;
  const origem = J.por_origem.map(o =>
    `<div style="display:grid;grid-template-columns:104px 1fr 64px;gap:8px;
      align-items:center;font-family:var(--mono);font-size:11.5px;padding:3px 0">
      <span style="color:${COR_ORIGEM[o.origem] || "inherit"}">${esc2(o.origem)}</span>
      <span style="height:12px;background:var(--rule-soft)"><i style="display:block;
        height:100%;width:${(o.n / totalO * 100).toFixed(1)}%;
        background:${COR_ORIGEM[o.origem] || "#8a94a6"}"></i></span>
      <span style="text-align:right">${num(o.n)}</span></div>`).join("");
  const maiorT = Math.max(...J.por_tipo.map(t => t.n)) || 1;
  const tipos = J.por_tipo.map(t =>
    `<div style="display:grid;grid-template-columns:148px 1fr 56px;gap:8px;
      align-items:center;font-family:var(--mono);font-size:11px;padding:2px 0">
      <span>${esc2(t.tipo)}</span>
      <span style="height:9px;background:var(--rule-soft)"><i style="display:block;
        height:100%;width:${(t.n / maiorT * 100).toFixed(1)}%;background:#3f6fb5"></i></span>
      <span style="text-align:right">${num(t.n)}</span></div>`).join("");
  const ex = J.exemplos.map(x =>
    `<tr><td>${esc2(x.tipo)}</td>
      <td><span class="chip" style="background:${COR_ORIGEM[x.origem]}"></span>${esc2(x.origem)}</td>
      <td>${x.n}</td><td>${esc2(x.parafuso)}</td>
      <td>${x.forca_kn ? num(x.forca_kn, 2) + " kN" : "—"}</td>
      <td style="white-space:normal;max-width:38ch">${esc2(x.nota || "")}</td></tr>`).join("");
  const pf_ = J.por_parafuso.map(p =>
    `<div class="cartao"><span class="rot">${esc2(p.parafuso)}</span>
      <span class="val">${num(p.n)}</span><span class="uni">unidades</span></div>`).join("");
  return `${barraModos()}${leitura("parafusos")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Parafusos</span>
        <span class="val">${num(J.total)}</span><span class="uni">no total</span></div>
      <div class="cartao"><span class="rot">Por área</span>
        <span class="val">${J.por_m2.toFixed(1).replace(".", ",")}</span>
        <span class="uni">por m² de projeto</span></div>
      <div class="cartao"><span class="rot">Juntas</span>
        <span class="val">${num(J.n_juntas)}</span><span class="uni">peça com peça</span></div>
      ${pf_}
    </div>
    <div class="eng-grid" style="grid-template-columns:1fr 1fr">
      <div class="eng-sec"><h3>De onde vem a quantidade</h3>${origem}
        <p class="conta" style="display:block;margin-top:10px;line-height:1.5">
          Só <b>${num(J.por_origem.find(o => o.origem === "FORCA")?.n || 0)}</b>
          parafusos saem de um esforço calculado. O resto é mínimo construtivo
          ou regra declarada — e saber a diferença é o que permite discutir o
          projeto em vez de aceitá-lo.</p></div>
      <div class="eng-sec"><h3>Por tipo de junta</h3>${tipos}</div>
    </div>
    <div class="eng-sec"><h3>Uma junta de cada tipo, por extenso</h3>
      <div class="rolagem"><table class="tabela"><thead><tr><th>junta</th>
        <th>origem</th><th>n</th><th>parafuso</th><th>força</th><th>por quê</th>
        </tr></thead><tbody>${ex}</tbody></table></div></div>`;
}

// ------------------------------------------------------------ instalacoes
function vistaInstalacoes() {
  const I = ENG.instalacoes;
  if (!I) return barraModos() + "<p class='conta'>sem levantamento de instalações</p>";
  const H = I.hidraulica, E = I.eletrica, C = I.climatizacao, K = I.clash;
  const S = I.shafts;
  const maiorH = Math.max(...H.itens.map(i => i.comp_m)) || 1;
  const hid = H.itens.map(i =>
    `<div style="display:grid;grid-template-columns:150px 1fr 92px;gap:8px;
      align-items:center;font-family:var(--mono);font-size:11px;padding:2px 0">
      <span>${esc2(i.sistema)} DN${i.dn}</span>
      <span style="height:9px;background:var(--rule-soft)"><i style="display:block;
        height:100%;width:${(i.comp_m / maiorH * 100).toFixed(1)}%;
        background:${i.sistema.indexOf("esgoto") >= 0 ? "#6b4f8a" : (i.sistema.indexOf("quente") >= 0 ? "#c0392b" : "#3f6fb5")}"></i></span>
      <span style="text-align:right">${num(i.comp_m, 1)} m</span></div>`).join("");
  const conex = H.itens.map(i =>
    `<tr><td>${esc2(i.sistema)}</td><td>DN${i.dn}</td>
      <td>${num(i.comp_m, 1)}</td><td>${num(i.conexoes)}</td></tr>`).join("");
  const clim = C.linhas.map(l =>
    `<tr><td>${esc2(l.equip)}</td><td>${esc2(l.nicho)}</td>
      <td>${num(l.capacidade)}</td><td>${num(l.comp_m, 1)}</td></tr>`).join("");
  const conf = K.shafts.concat(K.criticos);
  // um conflito por peça não interessa: 26 linhas da mesma causa são uma
  // causa. Agrupar por motivo é o que transforma lista em decisão.
  const porMotivo = {};
  conf.forEach(c => {
    (porMotivo[c.motivo] = porMotivo[c.motivo] || []).push(c);
  });
  const grupos = Object.keys(porMotivo).map(m => {
    const g = porMotivo[m];
    const pecas = g.map(c => esc2(c.peca)).join(", ");
    const prum = [...new Set(g.map(c => c.a.indexOf("-V-") >= 0 ? c.a : c.b))]
      .map(x => esc2(x)).join(", ");
    return `<div class="selo nao" style="align-items:flex-start">
      <b>${g.length} conflito${g.length > 1 ? "s" : ""} — uma causa</b>
      <span style="line-height:1.55">${esc2(m)}<br><br>
        <b>Prumadas.</b> ${prum}<br><b>Peças atingidas.</b> ${pecas}</span></div>`;
  }).join("");
  return `${barraModos()}${leitura("instalacoes")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Tubo</span>
        <span class="val">${num(H.comp_total, 1)}</span>
        <span class="uni">m em ${H.itens.length} diâmetros</span></div>
      <div class="cartao"><span class="rot">Conexões</span>
        <span class="val">${num(H.conexoes)}</span><span class="uni">joelho, tê, luva</span></div>
      <div class="cartao"><span class="rot">Eletroduto</span>
        <span class="val">${num(E.eletroduto_m, 1)}</span>
        <span class="uni">m para ${E.pontos} pontos</span></div>
      <div class="cartao"><span class="rot">Cabo</span>
        <span class="val">${num(E.cabo_m, 1)}</span><span class="uni">m</span></div>
      <div class="cartao"><span class="rot">Linha frigorígena</span>
        <span class="val">${num(C.linha_m, 1)}</span>
        <span class="uni">m em ${C.n} equipamentos</span></div>
      <div class="cartao"><span class="rot">Volumes no clash</span>
        <span class="val">${num(K.volumes)}</span>
        <span class="uni">MEP contra estrutura</span></div>
      <div class="cartao"><span class="rot">Conflitos</span>
        <span class="val" style="color:${conf.length ? "var(--alert)" : "var(--ok)"}">${num(conf.length)}</span>
        <span class="uni">${conf.length ? "a resolver no projeto" : "nenhum"}</span></div>
    </div>
    <div class="eng-sec"><h3>O fator de percurso é declarado, não embutido</h3>
      <p class="conta" style="display:block;line-height:1.6">
        Percurso Manhattan de cada ponto até a prumada mais próxima, vezes
        <b>${H.fator.toFixed(2).replace(".", ",")}</b>. Um tubo real serpenteia
        — desvia de viga, contorna shaft, sobe e desce — e por isso este número
        é <b>limite inferior</b>. Quem discordar do fator muda um número e vê o
        efeito, em vez de descobrir que havia um acréscimo escondido dentro do
        comprimento. ${H.pecas} peças hidráulicas, ${H.ralos} ralos e
        ${H.prumadas} prumadas. Quadro elétrico em
        (${E.quadro[0]}, ${E.quadro[1]}) mm: ${esc2(E.obs)}.</p></div>
    <div class="eng-grid" style="grid-template-columns:1fr 1fr">
      <div class="eng-sec"><h3>Hidrossanitária por diâmetro</h3>${hid}
        <div class="rolagem" style="margin-top:10px">
          <table class="tabela"><thead><tr><th>sistema</th><th>DN</th>
            <th>metros</th><th>conexões</th></tr></thead>
            <tbody>${conex}</tbody></table></div></div>
      <div class="eng-sec"><h3>Climatização — ${C.n} equipamentos</h3>
        <div class="rolagem"><table class="tabela"><thead><tr><th>ambiente</th>
          <th>nicho</th><th>BTU/h</th><th>linha m</th></tr></thead>
          <tbody>${clim}</tbody></table></div>
        <p class="conta" style="display:block;margin-top:10px;line-height:1.5">
          ${esc2(C.obs)} — ${num(C.isolamento_m, 1)} m de isolamento e
          ${num(C.dreno_m, 1)} m de dreno.</p></div>
    </div>
    ${S ? `<div class="eng-sec" style="margin-top:22px">
      <h3>Shaft — a decisão, e por que ela é derivada e não escrita</h3>
      <p class="conta" style="display:block;line-height:1.6">${esc2(S.regra)}.
        Custo da regra: <b>${num(S.piso_tomado_m2, 3)} m²</b> de piso tomados do
        ambiente molhado e <b>${num(S.placa_m2, 2)} m²</b> de placa RU de
        enclausuramento — que agora existem no orçamento, porque uma decisão
        sem material é uma decisão que a obra descobre sozinha.</p>
      <div class="rolagem"><table class="tabela"><thead><tr><th>prumada</th>
        <th>DN</th><th>declarada</th><th>resolvida</th><th>lado</th>
        <th>afastou</th><th>ambiente</th><th>por quê</th></tr></thead>
        <tbody>${S.prumadas.map(v => `<tr>
          <td>${esc2(v.cod)}</td><td>DN${v.dn}</td>
          <td>${v.declarada ? v.declarada.join(", ") : "—"}</td>
          <td>${num(v.x)}, ${num(v.y)}</td>
          <td>${esc2(v.lado)}</td>
          <td>${v.deslocado ? num(v.deslocado) + " mm" : "—"}</td>
          <td>${esc2(v.ambiente || "—")}${v.molhado ? " 💧" : ""}</td>
          <td style="white-space:normal;max-width:44ch">${esc2(v.motivo)}</td>
          </tr>`).join("")}</tbody></table></div></div>` : ""}
    <div class="eng-sec" style="margin-top:22px">
      <h3>Interferência com a estrutura — o critério antes do número</h3>
      <p class="conta" style="display:block;line-height:1.6">
        ${esc2(K.criterio)}. Dos ${num(K.total)} cruzamentos brutos,
        <b>${num(K.resolviveis)}</b> se resolvem com furo verificado e
        <b>${num(conf.length)}</b> não.</p>
      ${grupos || `<div class="selo"><b>Sem conflito</b>
        <span>nenhuma prumada cai dentro de linha de parede e nenhum ramal
        exige furo que o perfil não comporte</span></div>`}</div>`;
}

// ------------------------------------------------------------ custo/cotacao
let bomFiltro = "";
// 900 linhas de uma vez sao 8.218 nos no DOM e ~360 ms por render — e o render
// acontece a cada tecla do filtro. Pagina-se: o custo passa a ser do lote.
let pecaLimite = 150;
function vistaCotacao() {
  const C = ENG.cotacao, B = ENG.bom || [];
  if (!C) return barraModos() + "<p class='conta'>sem levantamento de custo</p>";
  const cob = C.cobertura, M = C.mapa;
  const area = ENG.projeto.area_m2 || 1;
  const compra = B.filter(i => i.compra), prod = B.filter(i => !i.compra);
  const totalC = compra.reduce((s, i) => s + i.total, 0);
  const totalP = prod.reduce((s, i) => s + i.total, 0);
  const porFam = {};
  compra.forEach(i => { porFam[i.familia] = (porFam[i.familia] || 0) + i.total; });
  const fams = Object.keys(porFam).sort((a, b) => porFam[b] - porFam[a]);
  const maiorF = porFam[fams[0]] || 1;
  const barras = fams.map(f =>
    `<div style="display:grid;grid-template-columns:96px 1fr 128px;gap:8px;
      align-items:center;font-family:var(--mono);font-size:11px;padding:2px 0">
      <span>${esc2(f)}</span>
      <span style="height:9px;background:var(--rule-soft)"><i style="display:block;
        height:100%;width:${(porFam[f] / maiorF * 100).toFixed(1)}%;
        background:#3f6fb5"></i></span>
      <span style="text-align:right">R$ ${num(porFam[f], 0)} ·
        ${(porFam[f] / totalC * 100).toFixed(1)} %</span></div>`).join("");
  const sens = C.sensibilidade.slice(0, 6).map(x =>
    `<tr><td>${esc2(x.familia)}</td>
      <td>${(x.exposicao * 100).toFixed(1)} %</td>
      <td>R$ ${num(x.delta, 0)}</td>
      <td>${x.elasticidade.toFixed(2).replace(".", ",")}</td></tr>`).join("");
  const f = bomFiltro.toLowerCase();
  const linhas = B.filter(i => !f || (i.sku + " " + i.descricao).toLowerCase().includes(f))
    .map(i =>
    `<tr${i.compra ? "" : ' style="opacity:.55"'}>
      <td>${esc2(i.sku)}</td>
      <td style="white-space:normal;max-width:30ch">${esc2(i.descricao)}</td>
      <td>${num(i.quantidade, 2)}</td><td>${esc2(i.unidade)}</td>
      <td>${num(i.preco, 2)}</td>
      <td>${i.compra ? "R$ " + num(i.total, 2) : "—"}</td>
      <td style="white-space:normal;max-width:26ch">${esc2(i.fonte)}</td></tr>`).join("");
  const lac = M.lacunas.map(x =>
    `<tr><td>${esc2(x.sku)}</td>
      <td style="white-space:normal">${x.faltam.map(esc2).join("<br>")}</td></tr>`).join("");
  return `${barraModos()}${leitura("cotacao")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Custo</span>
        <span class="val">${num(totalC / 1000, 1)}</span>
        <span class="uni">mil reais · o que se compra</span></div>
      <div class="cartao"><span class="rot">Por área</span>
        <span class="val">${num(totalC / area, 0)}</span>
        <span class="uni">R$/m² de projeto</span></div>
      <div class="cartao"><span class="rot">Cotado</span>
        <span class="val" style="color:${cob.cotado_pct > 0 ? "var(--ok)" : "var(--alert)"}">${cob.cotado_pct.toFixed(0)} %</span>
        <span class="uni">do custo perguntado a alguém</span></div>
      <div class="cartao"><span class="rot">Mapa de cotação</span>
        <span class="val">${M.n}</span>
        <span class="uni">linhas, ${M.cotaveis} prontas</span></div>
      <div class="cartao"><span class="rot">Lacunas</span>
        <span class="val" style="color:var(--alert)">${M.n_lacunas}</span>
        <span class="uni">sem especificação bastante</span></div>
      <div class="cartao"><span class="rot">Não somado</span>
        <span class="val">${num(totalP / 1000, 1)}</span>
        <span class="uni">mil de rota alternativa</span></div>
    </div>
    <div class="selo nao" style="align-items:flex-start">
      <b>Todo preço aqui é (H)</b>
      <span style="line-height:1.55">${esc2(cob.leitura)}. Os números servem
        para auditar QUANTIDADE — que é derivada do modelo e fecha com a massa
        — e não para fechar contrato. O mapa de cotação está pronto para sair:
        ${M.n} linhas, com norma e especificação em cada uma, e
        ${M.min_propostas} propostas mínimas por item.</span></div>
    <div class="eng-grid" style="grid-template-columns:1fr 1fr;margin-top:18px">
      <div class="eng-sec"><h3>Onde está o dinheiro</h3>${barras}</div>
      <div class="eng-sec"><h3>Exposição — a derivada, não o valor</h3>
        <div class="rolagem"><table class="tabela"><thead><tr><th>família</th>
          <th>do total</th><th>+20 % custa</th><th>elasticidade</th>
          </tr></thead><tbody>${sens}</tbody></table></div>
        <p class="conta" style="display:block;margin-top:10px;line-height:1.5">
          Com 100 % dos preços hipotéticos, a informação honesta não é quanto
          custa: é quanto do orçamento depende de um preço que ninguém
          confirmou.</p></div>
    </div>
    <div class="eng-sec"><h3>Concentração do custo — onde vale cotar primeiro</h3>
      ${vizConcentracao(ENG.abc || [])}</div>
    <div class="eng-sec"><h3>O que falta para poder perguntar</h3>
      <div class="rolagem"><table class="tabela"><thead><tr><th>item</th>
        <th>o que falta</th></tr></thead><tbody>${lac}</tbody></table></div>
      <p class="conta" style="display:block;margin-top:10px;line-height:1.5">
        Preço recebido para linha mal especificada é pior que preço nenhum:
        parece comparável e não é.</p></div>
    <div class="eng-sec"><h3>BOM — ${compra.length} linhas de compra e
      ${prod.length} de produção</h3>
      <div class="filtros">
        <input type="search" id="bomBusca" placeholder="filtrar SKU ou descrição"
               value="${esc2(bomFiltro)}" aria-label="Filtrar o BOM">
        <span class="conta">as linhas esmaecidas são rota alternativa: a mesma
          matéria em outra unidade, e por isso não entram no total</span></div>
      <div class="rolagem"><table class="tabela"><thead><tr><th>SKU</th>
        <th>descrição</th><th>qtd</th><th>un</th><th>preço</th><th>total</th>
        <th>origem</th></tr></thead><tbody>${linhas}</tbody></table></div></div>`;
}

// --------------------------------------------------------------- bloqueios
let contratoSel = null;
function vistaBloqueios() {
  const cs = ENG.contratos || [];
  if (!cs.length) return barraModos() + "<p class='conta'>sem contratos</p>";
  const c = cs.find(x => x.cod === contratoSel) || cs[0];
  const lista = cs.map(x =>
    `<li><button type="button" data-contrato="${esc2(x.cod)}"
       aria-current="${x.cod === c.cod}">${esc2(x.cod)}
       <span class="sub">${x.secoes.length} seç${x.secoes.length > 1 ? "ões" : "ão"} ·
         ${x.esquema.length} campos</span></button></li>`).join("");
  const campos = c.esquema.map(k =>
    `<tr><td>${esc2(k.nome)}</td><td>${esc2(k.tipo)}</td>
      <td>${esc2(k.unidade || "—")}</td>
      <td>${k.obrigatorio ? "obrigatório" : "opcional"}</td>
      <td>${esc2(k.dominio.length ? k.dominio.join(" · ") : (k.descricao || ""))}</td></tr>`).join("");
  const nSec = cs.reduce((s, x) => s + x.secoes.length, 0);
  const nCam = cs.reduce((s, x) => s + x.esquema.length, 0);
  return `${barraModos()}${leitura("bloqueios")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Contratos</span>
        <span class="val">${cs.length}</span><span class="uni">bloqueios declarados</span></div>
      <div class="cartao"><span class="rot">Seções cobertas</span>
        <span class="val">${nSec}</span><span class="uni">das 155 da especificação</span></div>
      <div class="cartao"><span class="rot">Campos</span>
        <span class="val">${nCam}</span><span class="uni">com tipo e unidade</span></div>
      <div class="cartao"><span class="rot">Números inventados</span>
        <span class="val">0</span><span class="uni">e a auditoria confere</span></div>
    </div>
    <div class="eng-grid"><ul class="lista">${lista}</ul>
      <div>
        <div class="desenho">
          <p class="cap" style="font-size:13px"><b>${esc2(c.cod)} — ${esc2(c.titulo)}</b><br><br>
            <b>Bloqueio.</b> ${esc2(c.bloqueio)}.<br><br>
            <b>Fonte.</b> ${esc2(c.fonte)}.<br><br>
            <b>Aceite.</b> ${esc2(c.aceite)}.
            ${c.esforco ? "<br><br><b>Falta escrever.</b> " + esc2(c.esforco) + "." : ""}<br><br>
            <b>Seções da especificação.</b> ${c.secoes.join(", ")}.</p></div>
        <div class="rolagem" style="margin-top:12px">
          <table class="tabela"><thead><tr><th>campo</th><th>tipo</th>
            <th>unidade</th><th>exigência</th><th>domínio ou descrição</th></tr></thead>
            <tbody>${campos}</tbody></table></div>
      </div></div>`;
}

// ------------------------------------------------------- ordenar tabelas
// O CSS ja prometia: `.tabela th{cursor:pointer}` em TODA tabela. So a de
// pecas cumpria — as outras nove mudavam o cursor e nao faziam nada, que e
// pior que nao prometer. Esta funcao ordena no DOM, sem passar pelo render:
// serve qualquer tabela, inclusive as que nem sabem o que estao mostrando.
function ordenaveis() {
  document.querySelectorAll("#engConteudo table.tabela").forEach(t => {
    if (t.dataset.ordena === "propria") return;
    const cab = t.querySelectorAll("thead th");
    cab.forEach((th, i) => {
      if (th.dataset.ord !== undefined) { t.dataset.ordena = "propria"; return; }
      th.addEventListener("click", () => {
        const asc = th.dataset.dir !== "asc";
        cab.forEach(x => { delete x.dataset.dir; x.textContent = x.textContent.replace(/ [▲▼]$/, ""); });
        th.dataset.dir = asc ? "asc" : "desc";
        th.textContent = th.textContent.replace(/ [▲▼]$/, "") + (asc ? " ▲" : " ▼");
        const corpo = t.querySelector("tbody");
        const linhas = [...corpo.querySelectorAll("tr")];
        // numero com separador de milhar e virgula decimal tem de ordenar como
        // NUMERO: "1.234,5" antes de "9" e o erro classico da ordenacao por texto
        const val = tr => {
          const txt = (tr.children[i] ? tr.children[i].textContent : "").trim();
          const n = parseFloat(txt.replace(/[^\d,.-]/g, "")
                                  .replace(/\.(?=\d{3}\b)/g, "").replace(",", "."));
          return Number.isFinite(n) && /\d/.test(txt) ? n : txt.toLowerCase();
        };
        linhas.sort((x, y) => {
          const a1 = val(x), b1 = val(y);
          const c = (typeof a1 === "number" && typeof b1 === "number")
            ? a1 - b1 : String(a1).localeCompare(String(b1), "pt");
          return asc ? c : -c;
        });
        linhas.forEach(r => corpo.appendChild(r));
      });
    });
  });
}

// ---------------------------------------------------------------- roteador
function renderEng() {
  const alvo = document.getElementById("engConteudo");
  if (!ENG) { alvo.innerHTML = "<p class='conta'>carregando engenharia.json…</p>"; return; }
  const f = {painel: vistaPainel, paineis: vistaPaineis, pecas: vistaPecas,
             corte: vistaCorte, montagem: vistaMontagem,
             logistica: vistaLogistica, documentos: vistaDocumentos,
             materiais: vistaMateriais, parafusos: vistaParafusos,
             instalacoes: vistaInstalacoes, cotacao: vistaCotacao,
             ambientes: vistaAmbientes, catalogo: vistaCatalogo,
             fachada: vistaFachada, viabilidade: vistaViabilidade,
             geotecnia: vistaGeotecnia, pluvial: vistaPluvial,
             acustica: vistaAcustica, eletrica: vistaEletrica,
             marcenaria: vistaMarcenaria, bloqueios: vistaBloqueios}[engVista];
  // a rolagem e do LEITOR, nao do render. Trocar de filtro ou de ordenacao
  // jogava a pagina de volta ao topo da vista, e numa tabela de 900 linhas
  // isso e perder o lugar a cada tecla.
  const caixa = document.getElementById("stageEng");
  const rolagem = caixa ? caixa.scrollTop : 0;
  alvo.innerHTML = f();
  if (caixa && rolagem) caixa.scrollTop = rolagem;
  const v = VISTAS.find(x => x[0] === engVista);
  document.getElementById("sheetTitle").firstChild.nodeValue =
    "Engenharia · " + v[1];
  document.getElementById("sheetMeta").textContent = v[2];
  document.querySelectorAll("#vistasEng button").forEach(b =>
    b.setAttribute("aria-current", (b.dataset.vista === engVista) + ""));
  ligarEng();
  ordenaveis();
  ligarViz();
  if (typeof gravarRota === "function") gravarRota();
}

function ligarEng() {
  const em = (sel, ev, fn) => document.querySelectorAll(sel).forEach(
    n => n.addEventListener(ev, fn));
  em("[data-leitura]", "click", e => {
    engModo = e.currentTarget.dataset.leitura; renderEng();
  });
  em("[data-painel]", "click", e => {
    painelSel = e.currentTarget.dataset.painel; renderEng();
  });
  em("[data-ord]", "click", e => {
    const c = e.currentTarget.dataset.ord;
    pecaOrd = {campo: c, asc: pecaOrd.campo === c ? !pecaOrd.asc : true};
    renderEng();
  });
  const busca = document.getElementById("buscaPeca");
  if (busca) {
    busca.addEventListener("input", e => {
      // filtrar e comecar outra leitura: o lote volta ao inicio, senao o
      // "mostrar mais" de uma busca anterior contamina a proxima
      pecaBusca = e.target.value; pecaLimite = 150; renderEng();
      const n = document.getElementById("buscaPeca");
      n.focus(); n.setSelectionRange(n.value.length, n.value.length);
    });
    document.getElementById("filFam").addEventListener("change",
      e => { pecaFam = e.target.value; pecaLimite = 150; renderEng(); });
    document.getElementById("filPav").addEventListener("change",
      e => { pecaPav = e.target.value; pecaLimite = 150; renderEng(); });
  }
  const mais = document.getElementById("maisBarras");
  if (mais) mais.addEventListener("click", () => { corteLim += 60; renderEng(); });
  em("[data-passo]", "click", e => {
    passoAtual = Number(e.currentTarget.dataset.passo); pararAnim(); renderEng();
  });
  em("[data-doc]", "click", e => { docSel = e.currentTarget.dataset.doc; renderEng(); });
  // filtro do BOM: preserva o foco e o cursor, senao digitar fica impossivel
  const mp = document.getElementById("maisPecas");
  if (mp) mp.addEventListener("click", () => { pecaLimite += 300; renderEng(); });
  const bb = document.getElementById("bomBusca");
  if (bb) bb.addEventListener("input", e => {
    bomFiltro = e.target.value;
    const pos = e.target.selectionStart;
    renderEng();
    const novo = document.getElementById("bomBusca");
    if (novo) { novo.focus(); novo.setSelectionRange(pos, pos); }
  });
  em("[data-cat]", "click", e => { catAba = e.currentTarget.dataset.cat; renderEng(); });
  em("[data-amb]", "click", e => { ambSel = e.currentTarget.dataset.amb; renderEng(); });
  em("[data-comp]", "click", e => {
    compSel = e.currentTarget.dataset.comp; renderEng();
  });
  em("[data-contrato]", "click", e => {
    contratoSel = e.currentTarget.dataset.contrato; renderEng();
  });
  const play = document.getElementById("playMont");
  if (play) {
    play.addEventListener("click", () => animar ? pararAnim(true) : tocarAnim());
    document.getElementById("passoMenos").addEventListener("click",
      () => { passoAtual = Math.max(0, passoAtual - 1); pararAnim(); renderEng(); });
    document.getElementById("passoMais").addEventListener("click",
      () => { passoAtual = Math.min(ENG.montagem.n_passos, passoAtual + 1);
              pararAnim(); renderEng(); });
    document.getElementById("passoZero").addEventListener("click",
      () => { passoAtual = 0; pararAnim(); renderEng(); });
  }
}

function pararAnim(redesenhar) {
  if (animar) { clearInterval(animar); animar = null; if (redesenhar) renderEng(); }
}
function tocarAnim() {
  if (passoAtual >= ENG.montagem.n_passos) passoAtual = 0;
  animar = setInterval(() => {
    passoAtual += 1;
    if (passoAtual >= ENG.montagem.n_passos) { passoAtual = ENG.montagem.n_passos; pararAnim(); }
    const d = document.querySelector("#engConteudo .desenho");
    const c = document.querySelector("#engConteudo .conta");
    if (!d) { pararAnim(); return; }
    d.innerHTML = svgPlanta(passoAtual) + d.innerHTML.slice(d.innerHTML.indexOf("<p class="));
    const s = ENG.montagem.passos[passoAtual - 1];
    if (c) c.textContent = `passo ${passoAtual} de ${ENG.montagem.n_passos} · ` +
      `${s ? s.acumulado_h.toFixed(1) : "0,0"} h de ${ENG.montagem.horas} h · ` +
      `${s ? (s.progresso * 100).toFixed(0) : 0} %`;
  }, 140);
  renderEng();
}

let carregouEng = false;
// =====================================================================
// ROTA — o endereco descreve o que se esta vendo
//
// Ate R40 o caderno inteiro vivia numa URL so. Nao havia como mandar "olha a
// PR-22" nem "olha a vista de cotacao": o destinatario abria na capa e
// procurava. Recarregar a pagina no meio de uma analise voltava ao inicio, e o
// botao Voltar do navegador saia do caderno em vez de desfazer o ultimo passo.
//
// Isso nao e detalhe de conforto. Um caderno de projeto existe para ser
// CITADO — em e-mail, em ata de reuniao, em RFI de obra. Endereco que nao
// aponta para um lugar especifico transforma citacao em instrucao de busca.
// =====================================================================
let _rotaAplicando = false, _rotaPrimeira = true;

function rotaDaTela() {
  const m = document.querySelector(".modos button[aria-selected='true']");
  const qual = m ? m.dataset.modo : "2d";
  if (qual === "eng") return "eng/" + engVista;
  if (qual === "3d") return "3d";
  const s = (typeof SHEETS !== "undefined" && SHEETS[idxPrancha]) || null;
  return s ? "2d/PR-" + s.n : "2d";
}

function gravarRota() {
  if (_rotaAplicando) return;
  const nova = "#" + rotaDaTela();
  if (location.hash === nova) return;
  // pushState, nao replaceState: o botao Voltar passa a desfazer o ultimo
  // passo dentro do caderno, que e o que qualquer um espera dele.
  // A PRIMEIRA gravacao e a excecao: ela apenas carimba o endereco do estado
  // inicial, e empilha-la faria o primeiro Voltar cair num endereco vazio —
  // um beco, que e exatamente o que esta mudanca existe para eliminar.
  if (_rotaPrimeira) { _rotaPrimeira = false; history.replaceState(null, "", nova); return; }
  history.pushState(null, "", nova);
}

function aplicarRota(h) {
  const partes = (h || "").replace(/^#/, "").split("/").filter(Boolean);
  if (!partes.length) return false;
  _rotaAplicando = true;
  try {
    const qual = partes[0];
    if (qual === "eng") {
      if (partes[1] && VISTAS.some(v => v[0] === partes[1])) engVista = partes[1];
      modo("eng");
    } else if (qual === "3d") {
      modo("3d");
    } else if (qual === "2d") {
      modo("2d");
      if (partes[1] && typeof SHEETS !== "undefined") {
        const n = partes[1].replace(/^PR-/i, "");
        const i = SHEETS.findIndex(x => x.n === n);
        if (i >= 0) mostrar(i);
      }
    } else {
      return false;
    }
    return true;
  } finally {
    _rotaAplicando = false;
  }
}

addEventListener("popstate", () => aplicarRota(location.hash));
addEventListener("DOMContentLoaded", () => aplicarRota(location.hash));
if (document.readyState !== "loading") aplicarRota(location.hash);

function abrirEng() {
  if (carregouEng) { renderEng(); return; }
  carregouEng = true;
  const ul = document.getElementById("vistasEng");
  VISTAS.forEach(([id, nome, sub]) => {
    const li = document.createElement("li");
    const b = document.createElement("button");
    b.type = "button"; b.dataset.vista = id;
    b.innerHTML = `${nome}<span class="sub">${sub}</span>`;
    b.addEventListener("click", () => { engVista = id; pararAnim(); renderEng(); });
    li.appendChild(b); ul.appendChild(li);
  });
  garantirENG().then(renderEng).catch(() => {
    document.getElementById("engConteudo").innerHTML =
      "<div class='selo nao'><b>engenharia.json não carregou</b>" +
      "<span>a aba mostra o motor; sem o arquivo não há o que mostrar</span></div>";
  });
}

// O motor era carregado so quando a aba de engenharia abria. A busca global
// precisa dele antes disso — quem procura "TP23" nao quer primeiro descobrir
// em que aba TP23 mora. Uma promessa so, memorizada: duas chamadas simultaneas
// nao viram dois downloads de 930 KB.
let _promessaENG = null;
function garantirENG() {
  if (ENG) return Promise.resolve(ENG);
  if (!_promessaENG) {
    _promessaENG = fetch("engenharia.json").then(r => r.json()).then(d => {
      ENG = d;
      if (!painelSel && d.paineis && d.paineis.length) painelSel = d.paineis[0].cod;
      return d;
    });
  }
  return _promessaENG;
}
'''

CSS_ENG += r'''
  /* ---------------------------------------------------- busca global */
  .lupa{font-family:var(--mono); font-size:11.5px; letter-spacing:.03em;
        border:1px solid var(--rule); background:var(--surface); color:var(--ink-soft);
        padding:5px 10px; cursor:pointer; border-radius:2px; display:flex;
        align-items:center; gap:7px}
  .lupa:hover{border-color:var(--accent); color:var(--accent)}
  .lupa kbd{font-family:var(--mono); font-size:9.5px; border:1px solid var(--rule);
            border-radius:2px; padding:1px 4px; color:var(--ink-faint)}
  @media (max-width:560px){ .lupa kbd{display:none} }

  .paleta{position:fixed; inset:0; z-index:50; background:rgba(10,14,18,.45);
          display:flex; align-items:flex-start; justify-content:center;
          padding:8vh 16px 16px}
  .paleta-caixa{width:min(720px,100%); background:var(--surface);
                border:1px solid var(--rule); box-shadow:var(--shadow);
                border-radius:3px; display:flex; flex-direction:column;
                max-height:76vh; overflow:hidden}
  .paleta input{font-family:var(--body); font-size:16px; border:none;
                border-bottom:1px solid var(--rule-soft); background:none;
                color:var(--ink); padding:14px 16px; width:100%}
  .paleta input:focus{outline:none}
  .paleta .achados{overflow-y:auto; padding:6px 0}
  .paleta .grupo{font-family:var(--mono); font-size:9.5px; letter-spacing:.13em;
                 text-transform:uppercase; color:var(--ink-faint);
                 padding:9px 16px 4px}
  .paleta button.ach{display:grid; grid-template-columns:1fr auto; gap:12px;
    width:100%; text-align:left; background:none; border:none; color:inherit;
    font-family:inherit; font-size:13.5px; padding:7px 16px; cursor:pointer;
    align-items:baseline}
  .paleta button.ach:hover, .paleta button.ach[aria-current="true"]{
    background:var(--accent-soft); box-shadow:inset 2px 0 0 var(--accent)}
  .paleta .ach .sub{display:block; font-family:var(--mono); font-size:10.5px;
                    color:var(--ink-faint); margin-top:1px}
  .paleta .ach .onde{font-family:var(--mono); font-size:10px; color:var(--ink-faint);
                     white-space:nowrap}
  .paleta .rodape{border-top:1px solid var(--rule-soft); padding:8px 16px;
    font-family:var(--mono); font-size:10.5px; color:var(--ink-faint);
    display:flex; gap:14px; flex-wrap:wrap}
'''

JS_ENG += r'''
// =====================================================================
// BUSCA GLOBAL — uma pergunta, doze vistas e 35 pranchas
//
// Ate R41 cada vista tinha o seu filtro, e cada filtro so enxergava a propria
// lista. Quem procurava "TP23" precisava saber ANTES em que aba TP23 mora —
// e essa e exatamente a informacao que quem procura nao tem. Um sistema que
// exige saber onde esta a resposta para poder procura-la nao tem busca: tem
// filtros.
//
// O indice se monta do que ja existe (nada de estrutura paralela para
// divergir) e cada achado sabe PARA ONDE IR. E por isso que isto vem depois da
// rota de R41: sem endereco nao ha destino, e um resultado de busca que nao
// leva a lugar nenhum e so um eco.
// =====================================================================
let _indice = null, _achSel = 0, _achAtuais = [];

function _ir(rota, antes) {
  if (typeof antes === "function") antes();
  aplicarRota(rota);
  if (rota.startsWith("eng/")) renderEng();
  gravarRota();
}

function montarIndice() {
  if (_indice) return _indice;
  const ix = [];
  const add = (tipo, chave, rotulo, sub, rota, antes) =>
    ix.push({tipo, chave: (chave || "").toLowerCase(),
             texto: ((rotulo || "") + " " + (sub || "")).toLowerCase(),
             rotulo, sub, rota, antes});

  if (typeof SHEETS !== "undefined") SHEETS.forEach(s => add(
    "prancha", "pr-" + s.n, `PR-${s.n} · ${s.t}`,
    `${s.etapa} · escala ${s.esc} · ${s.d.slice(0, 90)}`, `2d/PR-${s.n}`));

  VISTAS.forEach(([id, nome, sub]) => add(
    "vista", id, nome, sub, "eng/" + id));

  if (!ENG) return (_indice = ix);

  ENG.paineis.forEach(p => add(
    "painel", p.cod, p.cod,
    `${p.pecas.length} peças · ${p.comp} mm · ${p.parafusos} parafusos`,
    "eng/paineis", () => { painelSel = p.cod; }));

  todasPecas().forEach(q => add(
    "peça", q.cod, q.cod,
    `${q.familia} · ${q.perfil} · ${q.painel}`,
    "eng/pecas", () => { pecaBusca = q.cod; pecaFam = ""; pecaPav = ""; pecaLimite = 150; }));

  (ENG.bom || []).forEach(i => add(
    "material", i.sku, `${i.sku} — ${i.descricao}`,
    `${num(i.quantidade, 2)} ${i.unidade}${i.compra ? " · R$ " + num(i.total, 2) : " · rota alternativa"}`,
    "eng/cotacao", () => { bomFiltro = i.sku; }));

  ((ENG.materiais || {}).composicoes || []).forEach(c => add(
    "composição", c.cod, `${c.cod} — ${c.nome}`,
    `${num(c.area, 1)} m² · ${c.esp_nominal} mm · Rw ${c.rw}`,
    "eng/materiais", () => { compSel = c.cod; }));

  (((ENG.instalacoes || {}).shafts || {}).prumadas || []).forEach(v => add(
    "prumada", v.cod, `${v.cod} — DN${v.dn}`,
    `${esc2(v.onde)} · caixa ${v.lado} ${v.deslocado} mm em ${v.ambiente}`,
    "eng/instalacoes"));

  ((ENG.pendencias || {}).abertas || []).forEach(d => add(
    "pendência", "pendencia-" + d.n, `#${d.n} ${d.titulo}`,
    `${d.impacto.slice(0, 80)}${d.bloqueia ? " · tranca " + d.bloqueia : ""}`,
    "eng/painel"));

  (ENG.contratos || []).forEach(c => add(
    "bloqueio", c.cod, `${c.cod} — ${c.titulo}`, c.bloqueio.slice(0, 90),
    "eng/bloqueios", () => { contratoSel = c.cod; }));

  if (typeof FICHAS !== "undefined") Object.keys(FICHAS).forEach(cod => {
    const f = FICHAS[cod] || {};
    add("ambiente", cod, `${cod} — ${f.nome || ""}`,
        Object.keys(f).map(k => `${k}: ${f[k]}`).join(" · ").slice(0, 90),
        cod.startsWith("S-") ? "2d/PR-03" : "2d/PR-02");
  });
  return (_indice = ix);
}

function procurar(q) {
  const t = (q || "").trim().toLowerCase();
  if (!t) return [];
  const ix = montarIndice();
  const out = [];
  for (const e of ix) {
    // a pontuacao e a ordem da resposta: codigo exato ganha de codigo que
    // comeca com, que ganha de texto que contem. Sem isso, procurar "TP23"
    // devolve primeiro as 14 pecas QUE MENCIONAM TP23 e so depois o painel
    let p = -1;
    if (e.chave === t) p = 0;
    else if (e.chave.startsWith(t)) p = 1;
    else if (e.chave.includes(t)) p = 2;
    else if (e.texto.includes(t)) p = 3;
    if (p >= 0) out.push({e, p});
    if (out.length > 400) break;
  }
  out.sort((a, b) => a.p - b.p || a.e.rotulo.localeCompare(b.e.rotulo, "pt"));
  return out.slice(0, 40).map(x => x.e);
}

function _pintarAchados(lista) {
  const cx = document.getElementById("paletaAchados");
  if (!lista.length) {
    cx.innerHTML = `<p class="grupo">nada encontrado</p>`;
    return;
  }
  let html = "", grupo = "";
  lista.forEach((e, i) => {
    if (e.tipo !== grupo) { grupo = e.tipo; html += `<p class="grupo">${esc2(grupo)}</p>`; }
    html += `<button type="button" class="ach" data-i="${i}"
       aria-current="${i === _achSel}">
       <span>${esc2(e.rotulo)}<span class="sub">${esc2(e.sub || "")}</span></span>
       <span class="onde">${esc2(e.rota)}</span></button>`;
  });
  cx.innerHTML = html;
  const alvo = cx.querySelector(`[data-i="${_achSel}"]`);
  if (alvo) alvo.scrollIntoView({block: "nearest"});
}

function abrirPaleta() {
  let pal = document.getElementById("paleta");
  if (!pal) {
    pal = document.createElement("div");
    pal.id = "paleta"; pal.className = "paleta";
    pal.innerHTML = `<div class="paleta-caixa" role="dialog" aria-modal="true"
        aria-label="Busca no caderno">
        <input id="paletaEntrada" type="search" autocomplete="off"
               placeholder="prancha, peça, painel, material, ambiente, pendência…">
        <div class="achados" id="paletaAchados"></div>
        <div class="rodape"><span><kbd>↑</kbd><kbd>↓</kbd> percorre</span>
          <span><kbd>Enter</kbd> abre</span><span><kbd>Esc</kbd> fecha</span>
          <span id="paletaConta"></span></div></div>`;
    document.body.appendChild(pal);
    pal.addEventListener("click", e => { if (e.target === pal) fecharPaleta(); });
    const ent = pal.querySelector("#paletaEntrada");
    ent.addEventListener("input", () => {
      _achSel = 0;
      _achAtuais = procurar(ent.value);
      _pintarAchados(_achAtuais);
      document.getElementById("paletaConta").textContent =
        _achAtuais.length ? `${_achAtuais.length} resultado(s)` : "";
    });
    ent.addEventListener("keydown", e => {
      if (e.key === "Escape") { fecharPaleta(); return; }
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (!_achAtuais.length) return;
        _achSel = (_achSel + (e.key === "ArrowDown" ? 1 : -1) + _achAtuais.length)
                  % _achAtuais.length;
        _pintarAchados(_achAtuais);
      }
      if (e.key === "Enter" && _achAtuais[_achSel]) {
        const a = _achAtuais[_achSel];
        fecharPaleta();
        _ir(a.rota, a.antes);
      }
    });
    pal.querySelector("#paletaAchados").addEventListener("click", e => {
      const b = e.target.closest("button.ach");
      if (!b) return;
      const a = _achAtuais[+b.dataset.i];
      fecharPaleta();
      if (a) _ir(a.rota, a.antes);
    });
  }
  pal.hidden = false;
  const ent = pal.querySelector("#paletaEntrada");
  ent.value = ""; _achAtuais = []; _achSel = 0;
  _pintarAchados([]);
  document.getElementById("paletaConta").textContent = "";
  ent.focus();
  // o indice completo depende do motor; enquanto ele nao chega a busca ja
  // funciona sobre as pranchas, e se completa sozinha quando chegar
  garantirENG().then(() => { _indice = null; if (ent.value) ent.dispatchEvent(new Event("input")); })
               .catch(() => {});
}

function fecharPaleta() {
  const pal = document.getElementById("paleta");
  if (pal) pal.hidden = true;
}

// o botao entra na barra por JS: a busca vale para os tres modos, e pendura-la
// no HTML de um deles a faria sumir nos outros
(function ligarBusca() {
  const barra = document.querySelector(".toolbar .modos");
  if (barra) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "lupa"; b.id = "abrirBusca";
    b.innerHTML = `<span aria-hidden="true">⌕</span> buscar <kbd>Ctrl K</kbd>`;
    b.addEventListener("click", abrirPaleta);
    barra.parentElement.insertBefore(b, barra.nextSibling);
  }
  addEventListener("keydown", e => {
    const dentro = /^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName);
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault(); abrirPaleta(); return;
    }
    if (e.key === "/" && !dentro) { e.preventDefault(); abrirPaleta(); }
  });
})();
'''

CSS_ENG += r'''
  /* ------------------------------------------------ impressao (secao 4)
     Ctrl+P dava um resultado ruim: trilho, barra de ferramentas, minimapa e
     cartoes de navegacao iam para o papel, e o desenho saia cortado dentro de
     um palco de altura fixa em vh — unidade que nao existe em papel.

     O que se imprime nao e a interface: e o DOCUMENTO. Cabecalho, a prancha ou
     a vista aberta, e as notas. O resto e ferramenta de tela. */
  @media print {
    @page { size: A4 landscape; margin: 10mm; }
    body{background:#fff; color:#000}
    .rail, .modos, .barra, .barra2, .lupa, .paleta, .minimapa, .rodape2d,
    .hint, .hud, .ficha, .filtros, .docs, .modos-leitura,
    .toolbar .btn, .escalag{display:none !important}
    .work{display:block; padding-block:0}
    .stage-box{border:none; box-shadow:none}
    /* altura em vh nao existe em papel: o palco precisa caber na folha */
    .stage, .stage3d, #stageEng{height:auto !important; max-height:none !important;
      overflow:visible !important}
    .folha{position:static !important; transform:none !important;
           box-shadow:none !important; width:100% !important}
    .folha svg{width:100% !important; height:auto !important}
    .rolagem{max-height:none !important; overflow:visible !important}
    /* uma linha de tabela partida entre duas folhas e ilegivel */
    .tabela tr{break-inside:avoid}
    .eng-sec, .cartao, .nota, .selo{break-inside:avoid}
    .cartoes{border-color:#bbb}
    a[href^="http"]::after{content:" (" attr(href) ")"; font-size:9px}
    /* a procedencia do que esta no papel: revisao e endereco da vista */
    .stage-box::after{content:"Porto Real · impresso da vista " attr(data-rota);
      display:block; font-family:var(--mono); font-size:9px; color:#555;
      padding-top:6px; border-top:1px solid #ccc; margin-top:8px}
  }
'''

JS_ENG += r'''
// o rodape impresso carrega o endereco da vista: uma folha solta em cima da
// mesa da obra nao diz de onde veio, e a rota e exatamente o que diz
addEventListener("beforeprint", () => {
  const cx = document.querySelector(".stage-box");
  if (cx) cx.dataset.rota = "#" + (typeof rotaDaTela === "function" ? rotaDaTela() : "");
});
'''

CSS_ENG += r'''
  /* ------------------------------------------------------- graficos
     Ate R42 todo "grafico" aqui era uma <div> com largura percentual: serve
     para comparar magnitude e nao serve para mais nada — nao tem eixo, nao
     tem escala, nao tem limiar e nao responde "onde isto passa de aceitavel".

     UMA cor de serie, sequencial. Nada aqui e categorico: sao series unicas,
     e serie unica dispensa legenda — o titulo ja diz o que esta plotado. */
  .viz{--viz-serie:#3f6fb5; --viz-critico:#d03b3b; --viz-ref:var(--ink-faint);
       position:relative}
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]) .viz{--viz-serie:#3987e5; --viz-critico:#e66767}
  }
  :root[data-theme="dark"] .viz{--viz-serie:#3987e5; --viz-critico:#e66767}
  /* O SVG escala tudo, inclusive o texto: um viewBox de 460 renderizado em
     930 px dobra cada rotulo. Limitar a largura mantem a tipografia proxima do
     tamanho desenhado, em vez de virar cartaz no monitor e sumir no telefone. */
  .viz svg{display:block; width:100%; max-width:640px; height:auto; overflow:visible}
  .viz .grade{stroke:var(--rule-soft); stroke-width:1; fill:none}
  .viz .eixo{fill:var(--ink-faint); font-family:var(--mono); font-size:9px}
  .viz .rot{fill:var(--ink-soft); font-family:var(--mono); font-size:9.5px}
  .viz .val{fill:var(--ink); font-family:var(--mono); font-size:10px; font-weight:500}
  .viz .marca{fill:var(--viz-serie)}
  .viz .marca.critica{fill:var(--viz-critico)}
  .viz .linha{stroke:var(--viz-serie); stroke-width:2; fill:none;
              stroke-linejoin:round; stroke-linecap:round}
  .viz .area{fill:var(--viz-serie); opacity:.10}
  .viz .ref{stroke:var(--ink-faint); stroke-width:1; fill:none; opacity:.55}
  .viz .ponto{fill:var(--viz-serie); stroke:var(--surface); stroke-width:2}
  .viz .alvo{stroke:var(--viz-critico); stroke-width:1; fill:none}
  .viz .sombra{fill:transparent; cursor:crosshair}
  .viz .sombra:hover{fill:var(--rule-soft); opacity:.5}
  .dica-viz{position:absolute; pointer-events:none; z-index:6;
    background:var(--surface); border:1px solid var(--rule); box-shadow:var(--shadow);
    padding:6px 9px; border-radius:2px; font-family:var(--mono); font-size:10.5px;
    color:var(--ink); white-space:nowrap; transform:translate(-50%,-115%)}
  .viz-legenda{font-family:var(--mono); font-size:10px; color:var(--ink-faint);
               margin:6px 0 0; line-height:1.5}
'''

JS_ENG += r'''
// =====================================================================
// GRAFICOS — o que a barra de <div> nao conseguia dizer
//
// Tres perguntas que as tabelas respondem mal:
//   1. os 415 montantes estao FOLGADOS ou raspando o limite?
//   2. o custo esta concentrado em poucos itens ou espalhado?
//   3. a obra comeca devagar e acelera, ou o contrario?
//
// Todas sao de SERIE UNICA — e por isso nenhuma tem legenda: o titulo ja diz
// o que esta plotado, e uma caixa com um quadradinho so repete o titulo. Cor
// sequencial de uma hue; vermelho aparece uma vez so, para limite normativo, e
// sempre acompanhado de texto: vermelho contra verde tem separacao 4,1 sob
// deuteranopia, ou seja, cor sozinha ali nao informa ninguem.
// =====================================================================
function _dicaViz(cx, txt, x, y) {
  let d = cx.querySelector(".dica-viz");
  if (!d) { d = document.createElement("div"); d.className = "dica-viz"; cx.appendChild(d); }
  d.textContent = txt; d.style.left = x + "px"; d.style.top = y + "px"; d.hidden = false;
}
function _semDica(cx) { const d = cx.querySelector(".dica-viz"); if (d) d.hidden = true; }

function ligarViz() {
  document.querySelectorAll("#engConteudo .viz").forEach(cx => {
    cx.querySelectorAll("[data-dica]").forEach(el => {
      el.addEventListener("mousemove", e => {
        const r = cx.getBoundingClientRect();
        _dicaViz(cx, el.dataset.dica, e.clientX - r.left, e.clientY - r.top);
      });
      el.addEventListener("mouseleave", () => _semDica(cx));
    });
    cx.addEventListener("mouseleave", () => _semDica(cx));
  });
}

// ---- 1. distribuicao de utilizacao: colunas, com o limite desenhado
function vizUtilizacao(E) {
  const W = 460, H = 190, ML = 8, MR = 8, MT = 22, MB = 30;
  const dados = E.histograma;
  const maior = Math.max(...dados.map(h => h.n)) || 1;
  const faixa = (W - ML - MR) / dados.length;
  const alt = H - MT - MB;
  const colunas = dados.map((h, i) => {
    const larg = Math.min(24, faixa - 10);          // <= 24 px, nunca a faixa toda
    const x = ML + i * faixa + (faixa - larg) / 2;
    const a = Math.max(h.n ? 3 : 0, h.n / maior * alt);
    const y = MT + alt - a;
    const crit = h.ate > 1;
    const rot = crit ? "acima de 1,00"
      : `${h.de.toFixed(2).replace(".", ",")}–${h.ate.toFixed(2).replace(".", ",")}`;
    const dica = `${h.n} montante(s) · utilização ${rot}`;
    // topo arredondado em 4 px, pe quadrado na linha de base
    const r = Math.min(4, a / 2);
    const caminho = a <= 0 ? "" :
      `M${x} ${MT + alt} V${y + r} a${r} ${r} 0 0 1 ${r} -${r} h${larg - 2 * r}` +
      ` a${r} ${r} 0 0 1 ${r} ${r} V${MT + alt} Z`;
    return `${a > 0 ? `<path class="marca${crit ? " critica" : ""}" d="${caminho}"
        data-dica="${esc2(dica)}"></path>` : ""}
      <rect class="sombra" x="${ML + i * faixa}" y="${MT}" width="${faixa}"
            height="${alt}" data-dica="${esc2(dica)}"></rect>
      <text class="val" x="${x + larg / 2}" y="${(h.n ? y : MT + alt) - 5}"
            text-anchor="middle">${h.n}</text>
      <text class="rot" x="${ML + i * faixa + faixa / 2}" y="${H - 14}"
            text-anchor="middle">${rot.replace("acima de ", "> ")}</text>`;
  }).join("");
  // O limite so pode ser desenhado ONDE ELE E FRONTEIRA DE CATEGORIA: entre a
  // faixa 0,90–1,00 e a faixa "acima de 1,00". Posicionar 0,95 dentro de uma
  // coluna seria fingir que o eixo e continuo — ele e categorico, e a primeira
  // versao deste grafico fazia exatamente isso. O alvo de projeto vive no
  // texto, que e onde um numero sem lugar no eixo pertence.
  const xLim = ML + (dados.length - 1) * faixa;
  return `<div class="viz"><svg viewBox="0 0 ${W} ${H}" role="img"
      aria-label="Distribuição de utilização dos ${E.n} montantes">
      <line class="grade" x1="${ML}" y1="${MT + H - MT - MB}" x2="${W - MR}"
            y2="${MT + H - MT - MB}"></line>
      ${colunas}
      <line class="alvo" x1="${xLim}" y1="${MT - 2}" x2="${xLim}" y2="${H - MB}"></line>
      <text class="rot" x="${xLim - 4}" y="${MT + 4}" text-anchor="end"
            style="fill:var(--viz-critico)">limite 1,00</text>
      </svg>
    <p class="viz-legenda">Cada coluna é um número de montantes; a última faixa é
      a que <b>reprova</b> pela norma, e traz ${dados[dados.length - 1].n}.
      O alvo de projeto é ${E.u_alvo.toFixed(2).replace(".", ",")} e não aparece
      no eixo de propósito: o eixo é categórico, e valor contínuo marcado dentro
      de uma faixa finge uma escala que não existe.
      A utilização não tem teto: até R28 ela era relatada com min(0,99), e um
      montante 47&nbsp;% sobrecarregado saía como aprovado.</p></div>`;
}

// ---- 2. concentracao de custo: os dois eixos em %, uma escala so
function vizConcentracao(abc) {
  const W = 460, H = 210, ML = 34, MR = 12, MT = 14, MB = 30;
  const n = abc.length;
  if (!n) return "";
  const px = (W - ML - MR), py = (H - MT - MB);
  const pts = abc.map((a, i) => [(i + 1) / n, a.acumulado]);
  const X = f => ML + f * px, Y = f => MT + py - f * py;
  const d = "M" + X(0) + " " + Y(0) + pts.map(([a, b]) => ` L${X(a).toFixed(1)} ${Y(b).toFixed(1)}`).join("");
  const area = d + ` L${X(1)} ${Y(0)} Z`;
  // onde o acumulado cruza 80 %: e a fronteira da classe A, e o unico rotulo
  // direto que este grafico precisa
  const iA = pts.findIndex(([, b]) => b >= 0.8);
  const fA = iA >= 0 ? pts[iA][0] : 1;
  const sombras = abc.map((a, i) => {
    const x0 = X(i / n), larg = px / n;
    return `<rect class="sombra" x="${x0.toFixed(1)}" y="${MT}" width="${Math.max(larg, 2).toFixed(1)}"
      height="${py}" data-dica="${esc2(`${a.sku} · ${(a.participacao * 100).toFixed(1)} % do custo · acumulado ${(a.acumulado * 100).toFixed(1)} %`)}"></rect>`;
  }).join("");
  const marcas = [0, 0.25, 0.5, 0.75, 1].map(f =>
    `<line class="grade" x1="${ML}" y1="${Y(f)}" x2="${W - MR}" y2="${Y(f)}"></line>
     <text class="eixo" x="${ML - 6}" y="${Y(f) + 3}" text-anchor="end">${(f * 100).toFixed(0)} %</text>`).join("");
  return `<div class="viz"><svg viewBox="0 0 ${W} ${H}" role="img"
      aria-label="Concentração do custo: participação acumulada por item">
      ${marcas}
      <line class="ref" x1="${X(0)}" y1="${Y(0)}" x2="${X(1)}" y2="${Y(1)}"></line>
      <text class="rot" x="${X(0.52)}" y="${Y(0.48)}"
            transform="rotate(${(-Math.atan2(py, px) * 180 / Math.PI).toFixed(1)} ${X(0.52)} ${Y(0.48)})">custo espalhado por igual</text>
      <path class="area" d="${area}"></path>
      <path class="linha" d="${d}"></path>
      ${sombras}
      <line class="alvo" x1="${X(fA)}" y1="${Y(0)}" x2="${X(fA)}" y2="${Y(0.8)}"></line>
      <circle class="ponto" cx="${X(fA)}" cy="${Y(0.8)}" r="4"></circle>
      <text class="val" x="${X(fA) + 7}" y="${Y(0.8) - 6}">${iA + 1} itens = 80 % do custo</text>
      <text class="eixo" x="${ML}" y="${H - 10}">itens, do maior para o menor</text>
      <text class="eixo" x="${W - MR}" y="${H - 10}" text-anchor="end">${n} itens</text>
      </svg>
    <p class="viz-legenda">Os dois eixos são percentuais — uma escala só, sem
      segundo eixo. Quanto mais a curva se afasta da reta, mais o orçamento
      depende de poucos itens: são esses que valem cotar primeiro.</p></div>`;
}

// ---- 3. curva S da montagem
function vizMontagem(passos, horas) {
  const W = 460, H = 190, ML = 36, MR = 14, MT = 14, MB = 28;
  const n = passos.length;
  if (!n || !horas) return "";
  const px = (W - ML - MR), py = (H - MT - MB);
  const X = f => ML + f * px, Y = f => MT + py - f * py;
  const pts = passos.map((p, i) => [i / (n - 1 || 1), p.acumulado_h / horas]);
  const d = "M" + pts.map(([a, b], i) => `${i ? "L" : ""}${X(a).toFixed(1)} ${Y(b).toFixed(1)}`).join(" ");
  const marcas = [0, 0.5, 1].map(f =>
    `<line class="grade" x1="${ML}" y1="${Y(f)}" x2="${W - MR}" y2="${Y(f)}"></line>
     <text class="eixo" x="${ML - 6}" y="${Y(f) + 3}" text-anchor="end">${num(horas * f, 0)} h</text>`).join("");
  const sombras = passos.map((p, i) =>
    `<rect class="sombra" x="${(X(i / (n - 1 || 1)) - px / n / 2).toFixed(1)}" y="${MT}"
      width="${Math.max(px / n, 2).toFixed(1)}" height="${py}"
      data-dica="${esc2(`${p.cod} · ${num(p.acumulado_h, 1)} h acumuladas · ${num(p.duracao_h, 2)} h neste passo`)}"></rect>`).join("");
  return `<div class="viz"><svg viewBox="0 0 ${W} ${H}" role="img"
      aria-label="Horas acumuladas de montagem ao longo dos ${n} passos">
      ${marcas}
      <path class="linha" d="${d}"></path>
      ${sombras}
      <circle class="ponto" cx="${X(1)}" cy="${Y(1)}" r="4"></circle>
      <text class="val" x="${X(1) - 8}" y="${Y(1) + 12}" text-anchor="end">${num(horas, 1)} h no total</text>
      <text class="eixo" x="${ML}" y="${H - 8}">passo 1</text>
      <text class="eixo" x="${W - MR}" y="${H - 8}" text-anchor="end">passo ${n}</text>
      </svg>
    <p class="viz-legenda">A inclinação é a velocidade: trecho plano é passo
      rápido, trecho íngreme é onde a equipe fica. O prazo da obra é esta curva
      dividida pelo tamanho da equipe.</p></div>`;
}
'''

JS_ENG += r'''
// ---------------------------------------------------------- por ambiente
// A vista que faltava. As outras doze olham o projeto por SISTEMA; esta olha
// pelo comodo, que e onde se mora e onde se trabalha. Quem pergunta "o que tem
// na lavanderia?" nao quer doze abas: quer uma.
let ambSel = null;
function vistaAmbientes() {
  const A = ENG.ambientes;
  if (!A) return barraModos() + "<p class='conta'>sem dossiê por ambiente</p>";
  const d = A.dossies.find(x => x.cod === ambSel) || A.dossies[0];
  const achados = A.achados.filter(x => x.amb === d.cod);
  const lista = A.dossies.map(x => {
    const n = A.por_ambiente[x.cod] || 0;
    return `<li><button type="button" data-amb="${esc2(x.cod)}"
       aria-current="${x.cod === d.cod}">${esc2(x.nome)}
       <span class="sub">${esc2(x.cod)} · ${num(x.area, 1)} m²${
         n ? " · " + n + " achado(s)" : ""}</span></button></li>`;
  }).join("");
  const linha = (r, v) => v === "" || v === null || v === undefined ? "" :
    `<tr><td style="color:var(--ink-faint)">${esc2(r)}</td>
      <td style="white-space:normal">${v}</td></tr>`;
  const vaos = d.vaos.map(v =>
    `<tr><td>${esc2(v.tipo)}</td><td>${v.larg} × ${v.alt}</td>
      <td>${v.peitoril || "—"}</td><td>${num(v.area, 2)}</td>
      <td>${v.externo ? (v.translucido ? "externo, ilumina" : "externo, opaco")
                      : "interno"}</td>
      <td style="white-space:normal;max-width:26ch">${esc2(v.familia)}</td></tr>`).join("");
  const frac = f => f ? "1/" + (1 / f).toFixed(1) : "—";
  const sel = achados.length
    ? achados.map(x => `<div class="selo ${x.nivel === "ERRO" ? "nao" : ""}"
        style="align-items:flex-start;margin-bottom:8px">
        <b>${esc2(x.item)}</b><span style="line-height:1.55">${esc2(x.texto)}</span></div>`).join("")
    : `<div class="selo"><b>sem divergência</b><span>acabamento, vão, tomada,
        peça hidráulica, ralo, clima e composição de parede conferem entre si</span></div>`;
  return `${barraModos()}${leitura("ambientes")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Cômodos</span>
        <span class="val">${A.n}</span><span class="uni">somando ${num(A.area_total, 1)} m²</span></div>
      <div class="cartao"><span class="rot">Divergências</span>
        <span class="val" style="color:${A.achados.length ? "var(--alert)" : "var(--ok)"}">${A.achados.length}</span>
        <span class="uni">entre sistemas, dentro de cômodos</span></div>
      <div class="cartao"><span class="rot">Este cômodo</span>
        <span class="val">${num(d.area, 1)}</span>
        <span class="uni">m² · ${num(d.perimetro, 1)} m de perímetro</span></div>
      <div class="cartao"><span class="rot">Iluminação</span>
        <span class="val">${frac(d.frac_ilum)}</span>
        <span class="uni">mínimo (H) ${frac(d.exige_ilum)}</span></div>
    </div>
    <div class="eng-grid"><ul class="lista">${lista}</ul>
      <div>
        <div class="desenho"><p class="cap" style="font-size:13px">
          <b>${esc2(d.nome)}</b> · ${esc2(d.cod)} · ${d.pav === "T" ? "térreo" : "superior"}<br>
          ${d.largura} × ${d.profundidade} mm · ${num(d.area, 2)} m²${
            d.area_subdividida ? ` (${num(d.area_util, 2)} m² de permanência, descontando ${esc2(d.subdivisoes.join(", "))})` : ""}<br>
          <i>${esc2(d.categoria)} · ${esc2(d.classe)}${d.molhado ? " · área molhada" : ""}</i></p></div>
        ${sel}
        ${(A.conectividade && A.conectividade.ligacoes[d.cod]) ? `
        <p class="conta" style="display:block;margin:10px 0;line-height:1.55">
          <b>Liga a:</b> ${Object.keys(A.conectividade.ligacoes[d.cod]).map(k =>
            esc2(k) + " (" + A.conectividade.ligacoes[d.cod][k].map(esc2).join(", ") + ")"
          ).join(" · ") || "<span style='color:var(--alert)'>nenhum ambiente — este cômodo está ilhado</span>"}
        </p>` : ""}
        <div class="rolagem" style="margin-top:12px">
          <table class="tabela"><tbody>
            ${linha("piso", esc2(d.piso))}
            ${linha("parede", esc2(d.parede))}
            ${linha("forro", esc2(d.forro) + " · h " + d.forro_h + " mm")}
            ${linha("rodapé", esc2(d.rodape))}
            ${linha("revestimento", d.revest_h ? "até " + d.revest_h + " mm" : "")}
            ${linha("composições que o cercam", d.composicoes.join(" · ") + " · " + d.paineis + " painéis")}
            ${linha("iluminação natural", num(d.area_ilum, 2) + " m² = " + frac(d.frac_ilum) + " (mínimo " + frac(d.exige_ilum) + ")")}
            ${linha("ventilação natural", num(d.area_vent, 2) + " m² = " + frac(d.frac_vent) + " (mínimo " + frac(d.exige_vent) + ")")}
            ${linha("tomadas (NBR 5410)", d.tugs_norma + " TUG · " + num(d.tug_va) + " VA" + (d.molhada_eletrica ? " · área molhada, uma a cada 3,5 m" : " · uma a cada 5,0 m"))}
            ${linha("iluminação (carga)", num(d.ilum_va) + " VA")}
            ${linha("cargas especiais", d.tue.length ? d.tue.map(t => esc2(t.desc) + " (" + num(t.va) + " VA)").join(" · ") : "")}
            ${linha("peças hidráulicas", d.hidraulicas.length ? d.hidraulicas.map(h => esc2(h.cod) + (h.quente ? " (quente)" : "")).join(" · ") : "")}
            ${linha("ralos", d.ralos || "")}
            ${linha("climatização", d.clima.length ? d.clima.map(c => num(c.capacidade) + " BTU/h em " + esc2(c.nicho)).join(" · ") : "")}
          </tbody></table></div>
        <div class="eng-sec" style="margin-top:16px"><h3>Vãos deste cômodo — ${d.n_vaos}</h3>
          <div class="rolagem"><table class="tabela"><thead><tr><th>tipo</th>
            <th>vão mm</th><th>peitoril</th><th>m²</th><th>abre para</th>
            <th>família</th></tr></thead><tbody>${vaos}</tbody></table></div></div>
      </div></div>
    <p class="conta" style="display:block;margin-top:14px;line-height:1.6">
      ${esc2(A.criterio)}</p>`;
}
'''

CSS_ENG += r'''
  /* ------------------------------------------------ catalogo tecnico */
  .pecadesenho{display:block; width:100%; max-width:320px; height:auto;
               margin:0 auto; overflow:visible}
  .pecadesenho .secao{fill:none; stroke:var(--ink); stroke-width:1.4;
                      stroke-linejoin:round; stroke-linecap:round}
  .pecadesenho .secao-cheia{fill:var(--ink); stroke:none}
  .pecadesenho .rosca{fill:none; stroke:var(--ink); stroke-width:.7}
  .pecadesenho .cota-l{fill:none; stroke:var(--alert); stroke-width:.6}
  .pecadesenho text{font-family:var(--mono); font-size:9px; fill:var(--ink-soft)}
  .pecadesenho .titulo{font-size:11px; font-weight:600; fill:var(--ink)}
  .pecadesenho .cota{fill:var(--alert); font-size:8.5px}
  .pecas-grade{display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
               gap:14px}
  .peca-cartao{border:1px solid var(--rule-soft); background:var(--surface);
               padding:12px; display:flex; flex-direction:column; gap:8px}
  .peca-cartao .ficha{font-family:var(--mono); font-size:10.5px;
                      color:var(--ink-soft); line-height:1.55}
  .peca-cartao .ficha b{color:var(--ink)}
  .peca-cartao .uso{font-family:var(--mono); font-size:10px;
                    color:var(--accent); letter-spacing:.04em;
                    border-top:1px solid var(--rule-soft); padding-top:7px}
'''

JS_ENG += r'''
// ------------------------------------------------------ catalogo tecnico
// Cada peca desenhada A PARTIR DAS SUAS PROPRIAS DIMENSOES — a mesma poligonal
// de linha media que o solver da NBR 14762 integra para achar A, Ix e Wx.
// Buscar a imagem do fabricante daria um desenho generico, com marca de
// terceiro, que continuaria igual depois de a auditoria mudar uma espessura:
// passaria a mentir em silencio, que e a unica coisa que este projeto nao
// tolera. A designacao ja E a dimensao.
let catAba = "perfis";
const CAT_ABAS = [["perfis", "Perfis"], ["parafusos", "Parafusos"],
                  ["chapas", "Chapas"], ["tubos", "Tubos"]];
function vistaCatalogo() {
  const C = ENG.catalogo;
  if (!C) return barraModos() + "<p class='conta'>sem catálogo técnico</p>";
  const abas = CAT_ABAS.map(([k, t]) =>
    `<button class="btn" data-cat="${k}" ${k === catAba
      ? 'style="border-color:var(--accent);color:var(--accent)"' : ""}>${t}
      (${(C[k] || []).length})</button>`).join("");
  const itens = (C[catAba] || []).map(x => {
    let ficha = "", uso = "";
    if (catAba === "perfis") {
      ficha = `<b>${x.forma}</b> · alma ${x.bw} · aba ${x.bf}${x.D ? " · lábio " + x.D : ""}
        · esp ${num(x.t, 2)} mm<br>A ${num(x.area, 1)} mm² · Ix ${num(x.ix, 2)} cm⁴
        · Wx ${num(x.wx, 2)} cm³ · <b>${num(x.massa_m, 3)} kg/m</b><br>${esc2(x.norma)}`;
      uso = `${num(x.n)} peças · ${num(x.massa, 1)} kg · ${x.familias.map(esc2).join(", ")}`;
    } else if (catAba === "parafusos") {
      ficha = `⌀ rosca <b>${num(x.d, 1)} mm</b> · cabeça ${num(x.dw, 1)} mm ·
        comprimento ${num(x.comp)} mm<br>${esc2(x.tipo)} ·
        Rv ${num(x.rv, 1)} kN · Rt ${num(x.rt, 1)} kN <span class="conta">(H)</span><br>${esc2(x.norma)}`;
      uso = `${num(x.n)} unidades no projeto`;
    } else if (catAba === "chapas") {
      ficha = `<b>${esc2(x.nome)}</b> · espessura ${num(x.espessura, 1)} mm<br>
        formato ${x.formato[0]} × ${x.formato[1]} mm<br>${esc2(x.norma)}`;
      uso = `${num(x.area, 1)} m² no projeto`;
    } else {
      ficha = `DN ${x.dn} · diâmetro externo <b>${num(x.de, 1)} mm</b><br>
        ${esc2(x.sistema)}<br>${esc2(x.norma)}`;
      uso = `${num(x.comp, 1)} m · ${num(x.conexoes)} conexões`;
    }
    return `<div class="peca-cartao">${x.svg}
      <div class="ficha">${ficha}</div>
      <div class="uso">${uso}</div></div>`;
  }).join("");
  return `${barraModos()}${leitura("catalogo")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Peças no catálogo</span>
        <span class="val">${C.n}</span><span class="uni">desenhadas do modelo</span></div>
      <div class="cartao"><span class="rot">Perfis</span>
        <span class="val">${C.perfis.length}</span>
        <span class="uni">de 81 do catálogo, em uso</span></div>
      <div class="cartao"><span class="rot">Parafusos</span>
        <span class="val">${C.parafusos.length}</span>
        <span class="uni">tipos, ${num(C.parafusos.reduce((s, x) => s + x.n, 0))} unidades</span></div>
      <div class="cartao"><span class="rot">Imagens de catálogo</span>
        <span class="val">0</span><span class="uni">nenhuma buscada fora</span></div>
    </div>
    <div class="selo" style="align-items:flex-start;margin-bottom:14px">
      <b>Desenho é vista do modelo</b>
      <span style="line-height:1.55">${esc2(C.metodo)}. <br><br>
        <b>Limite declarado:</b> ${esc2(C.limite)}.</span></div>
    <div class="filtros">${abas}</div>
    <div class="pecas-grade">${itens}</div>`;
}
'''

JS_ENG += r'''
// ------------------------------------------------------------- fachada
// Tres perguntas diferentes, e o projeto so respondia a segunda: o que foi
// COMBINADO, o que foi DESENHADO e o que tem ESTRUTURA. Regra de fachada
// declarada que ninguem confere e preferencia, nao regra.
function vistaFachada() {
  const F = ENG.fachada;
  if (!F) return barraModos() + "<p class='conta'>sem levantamento de fachada</p>";
  const maior = Math.max(...F.faces.map(f => f.area_bruta)) || 1;
  const barras = F.faces.map(f =>
    `<div style="display:grid;grid-template-columns:118px 1fr 160px;gap:8px;
      align-items:center;font-family:var(--mono);font-size:11px;padding:3px 0">
      <span>${esc2(f.nome)}</span>
      <span style="height:12px;background:var(--rule-soft);position:relative">
        <i style="display:block;height:100%;width:${(f.area_bruta / maior * 100).toFixed(1)}%;
          background:#3f6fb5"></i>
        <i style="position:absolute;left:0;top:0;height:100%;
          width:${(f.area_vidro / maior * 100).toFixed(1)}%;background:#86b6ef"></i></span>
      <span style="text-align:right">${num(f.area_bruta, 1)} m² ·
        <b>${(f.frac_vidro * 100).toFixed(1)} %</b> vidro</span></div>`).join("");
  const mat = F.materiais.map(m =>
    `<tr><td><b>${esc2(m.familia)}</b></td>
      <td style="white-space:normal">${esc2(m.onde)}</td></tr>`).join("");
  const br = F.brises.itens.map(b =>
    `<tr><td>${esc2(b.cod)}</td><td>${esc2(b.face)}</td>
      <td>${num(b.comp)} × ${num(b.altura)}</td><td>${b.passo}</td>
      <td>${b.n_ripas}</td><td>${num(b.ripa_m, 1)}</td>
      <td>${num(b.massa, 1)}</td>
      <td>${b.movel ? "móvel" : "fixo"}</td>
      <td style="white-space:normal;max-width:30ch">${esc2(b.desc)}</td></tr>`).join("");
  const ach = F.achados.map(a =>
    `<div class="selo ${a.nivel === "ERRO" ? "nao" : ""}"
       style="align-items:flex-start;margin-bottom:8px">
      <b>${esc2(a.item)}</b>
      <span style="line-height:1.55">${esc2(a.texto)}</span></div>`).join("");
  const B = F.brises;
  return `${barraModos()}${leitura("fachada")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Fachada</span>
        <span class="val">${num(F.faces.reduce((s, f) => s + f.area_bruta, 0), 1)}</span>
        <span class="uni">m² nas quatro faces</span></div>
      <div class="cartao"><span class="rot">Famílias</span>
        <span class="val">${F.materiais.length}</span>
        <span class="uni">de ${F.regras.familias_max} permitidas</span></div>
      <div class="cartao"><span class="rot">Brises</span>
        <span class="val">${B.n}</span>
        <span class="uni">${num(B.comp_total, 1)} m · ${B.moveis} móveis</span></div>
      <div class="cartao"><span class="rot">Ripa</span>
        <span class="val">${num(B.ripa_m, 1)}</span>
        <span class="uni">m · ${num(B.massa, 1)} kg na parede</span></div>
    </div>
    <div class="eng-sec"><h3>As quatro faces — área e vidro</h3>${barras}
      <p class="conta" style="display:block;margin-top:10px;line-height:1.5">
        A face é derivada do envelope construído: quando o hall cresceu em R46,
        a fachada cresceu junto, sem que ninguém a redesenhasse.</p></div>
    <div class="eng-sec"><h3>O que foi combinado</h3>
      <div class="rolagem"><table class="tabela"><tbody>${mat}</tbody></table></div>
      <p class="conta" style="display:block;margin-top:8px;line-height:1.5">
        <b>Regras declaradas:</b> vidro ${esc2(F.regras.vidro)} ·
        ornamento: ${esc2(F.regras.ornamento)} ·
        manutenção: ${esc2(F.regras.manutencao)}.</p></div>
    <div class="eng-sec"><h3>Conferência das regras</h3>${ach}</div>
    ${F.platibanda && F.platibanda.altura ? `
    <div class="eng-sec"><h3>Platibanda — ${F.platibanda.altura} mm coroando
      ${num(F.platibanda.comprimento_m, 1)} m de perímetro</h3>
      <p class="conta" style="display:block;line-height:1.6">
        ${F.platibanda.n_montantes} montantes a cada ${F.platibanda.espac} mm
        (${num(F.platibanda.montante_m, 1)} m), ${num(F.platibanda.guia_m, 1)} m
        de guia, <b>${num(F.platibanda.placa_m2, 1)} m²</b> de placa em duas
        faces e ${num(F.platibanda.massa_aco, 1)} kg de aço.
        ${esc2(F.platibanda.obs)}.</p></div>` : ""}
    ${F.externo ? `
    <div class="eng-sec"><h3>Área externa — ${num(F.externo.area_externa, 1)} m²</h3>
      <div class="rolagem"><table class="tabela"><thead><tr><th>zona</th>
        <th>m²</th><th>material</th><th>por quê</th></tr></thead><tbody>
        ${F.externo.pisos.itens.map(z => `<tr><td>${esc2(z.zona)}</td>
          <td>${num(z.area, 2)}</td>
          <td style="white-space:normal">${esc2(z.material)}</td>
          <td style="white-space:normal;max-width:30ch">${esc2(z.razao)}</td></tr>`).join("")}
        <tr><td>jardim e canteiro</td><td>${num(F.externo.pisos.jardim, 2)}</td>
          <td>grama e vegetação</td><td>—</td></tr>
        </tbody></table></div>
      <p class="conta" style="display:block;margin-top:10px;line-height:1.55">
        <b>Muro:</b> ${num(F.externo.muro.comprimento_m, 1)} m a
        ${F.externo.muro.altura / 1000} m = ${num(F.externo.muro.area, 1)} m²,
        ${num(F.externo.muro.blocos)} blocos · ${esc2(F.externo.muro.material)}.<br>
        <b>Piscina:</b> ${F.externo.piscina.lamina} m² de lâmina,
        ${F.externo.piscina.volume} m³, ${num(F.externo.piscina.revestimento_m2, 1)} m²
        de revestimento e ${num(F.externo.piscina.concreto_m3, 2)} m³ de casca.<br>
        <b>Paisagismo:</b> ${F.externo.paisagismo.arvores} árvores e
        ${F.externo.paisagismo.vasos} vasos.</p></div>` : ""}
    <div class="eng-sec"><h3>Brises — ${B.n} elementos, ${num(B.massa, 1)} kg</h3>
      <div class="rolagem"><table class="tabela"><thead><tr><th>cód</th>
        <th>face</th><th>comp × alt</th><th>passo</th><th>ripas</th>
        <th>m de ripa</th><th>kg</th><th>tipo</th><th>onde</th></tr></thead>
        <tbody>${br}</tbody></table></div>
      <p class="conta" style="display:block;margin-top:10px;line-height:1.5">
        ${esc2(B.nota)}. Ripa: ${esc2(B.ripa.desc)}, ${num(B.ripa.massa_m, 2)} kg/m.</p></div>`;
}
'''

JS_ENG += r'''
// --------------------------------------------------------- viabilidade
// Uma lista de pendencias diz o que falta. Ela nao diz a unica coisa que
// decide se um projeto pode andar: QUANTO DELE DEPENDE DE CADA UMA. Um item
// que move 2 % do orcamento e nota de rodape; um que move 100 % e risco de
// contrato — e os dois aparecem iguais numa lista com bolinha.
function vistaViabilidade() {
  const V = ENG.viabilidade;
  if (!V) return barraModos() + "<p class='conta'>sem avaliação de viabilidade</p>";
  const abertas = V.itens.filter(i => i.status === "ABERTA")
                         .sort((a, b) => b.fracao - a.fracao);
  const maior = Math.max(...abertas.map(i => i.fracao)) || 1;
  const portoes = V.portoes.map(p =>
    `<div class="cartao"><span class="rot">${esc2(p.portao)}</span>
      <span class="val" style="color:${p.travado ? "var(--alert)" : "var(--ok)"}">${p.travado ? "travado" : "livre"}</span>
      <span class="uni">${p.travado ? "por #" + p.itens.join(", #") : "nada pendente"}<br>
        ${esc2(p.o_que_libera)}</span></div>`).join("");
  const linhas = abertas.map(i =>
    `<div class="eng-sec" style="margin-bottom:14px">
      <div style="display:grid;grid-template-columns:40px 1fr 150px;gap:10px;
        align-items:baseline">
        <span style="font-family:var(--mono);font-size:15px;color:var(--alert)">#${esc2(i.n)}</span>
        <div><b>${esc2(i.titulo)}</b>
          <span class="sub" style="display:block;font-family:var(--mono);
            font-size:10px;color:var(--ink-faint)">${esc2(i.norma)}${
            i.bloqueia ? " · tranca " + esc2(i.bloqueia) : " · não tranca portão"}</span></div>
        <span style="text-align:right;font-family:var(--mono);font-size:11px">
          <b>${(i.fracao * 100).toFixed(1)} %</b><br>R$ ${num(i.exposicao, 0)}</span>
      </div>
      <div style="height:8px;background:var(--rule-soft);margin:8px 0">
        <i style="display:block;height:100%;width:${(i.fracao / maior * 100).toFixed(1)}%;
          background:${i.fracao > 0.5 ? "#d03b3b" : "#3f6fb5"}"></i></div>
      <p class="conta" style="display:block;line-height:1.6;margin:0">
        ${i.grandeza ? "<b>" + esc2(i.grandeza) + "</b> · " : ""}${esc2(i.simulacao)}</p>
    </div>`).join("");
  const feitas = V.itens.filter(i => i.status !== "ABERTA").map(i =>
    `<li><span class="m">✓</span><span>#${esc2(i.n)} ${esc2(i.titulo)}
      <span class="sub" style="display:block;color:var(--ink-faint);font-size:12px">${esc2(i.impacto)}</span></span>
      <span class="st">resolvida</span></li>`).join("");
  return `${barraModos()}${leitura("viabilidade")}
    <div class="cartoes" style="margin-bottom:16px">${portoes}
      <div class="cartao"><span class="rot">Pendências</span>
        <span class="val">${V.abertas}</span>
        <span class="uni">abertas · ${V.resolvidas} resolvidas</span></div>
    </div>
    <div class="selo nao" style="align-items:flex-start;margin-bottom:16px">
      <b>Um projeto não está viável em bloco</b>
      <span style="line-height:1.55">${esc2(V.leitura)}. <br><br>
        <b>Exposição:</b> ${esc2(V.criterio)}.</span></div>
    ${linhas}
    ${feitas ? `<div class="eng-sec"><h3>Resolvidas</h3>
      <ul class="check">${feitas}</ul></div>` : ""}`;
}
'''


# ---------------------------------------------------------------------------
# R52 — quatro vistas novas. Cada uma corresponde a um sistema que saiu da
# hipotese nesta revisao, e existe pela mesma razao que as pranchas 37 a 40:
# o que esta no modelo tem de chegar ao papel E a tela.
# ---------------------------------------------------------------------------
JS_ENG += r'''
function _conf(lista) {
  return (lista || []).map(c =>
    `<div class="selo ${c.ok ? "" : "nao"}" style="align-items:flex-start;margin-bottom:6px">
      <b>${esc2(c.titulo)}</b>
      <span style="line-height:1.55">${esc2(c.detalhe)}</span></div>`).join("");
}

function vistaGeotecnia() {
  const G = ENG.geotecnia;
  if (!G) return barraModos() + "<p class='conta'>sem dados de sondagem</p>";
  const D = G.dimensionamento, R = D.recalque, I = D.investigacao;
  const nmax = 34;
  const perfil = G.perfil.map(f =>
    `<div style="display:grid;grid-template-columns:70px 1fr 210px;gap:8px;
      align-items:center;font-family:var(--mono);font-size:11px;padding:2px 0">
      <span>${f.z0}–${f.z1} m</span>
      <span style="height:13px;background:var(--rule-soft);position:relative">
        <i style="display:block;height:100%;width:${(f.medio / nmax * 100).toFixed(1)}%;
          background:#3f6fb5"></i>
        <i style="position:absolute;top:5px;height:3px;background:#1d3f6d;
          left:${(f.minimo / nmax * 100).toFixed(1)}%;
          width:${((f.maximo - f.minimo) / nmax * 100).toFixed(1)}%"></i></span>
      <span><b>N ${f.medio.toFixed(1)}</b> (${f.n.join("/")}) · ${esc2(f.solo)}</span>
    </div>`).join("");
  const cam = R.camadas.map(c =>
    `<tr><td>${c.z0}–${c.z1} m</td><td>${num(c.dsigma, 2)}</td>
      <td>${num(c.e_mpa, 1)}</td><td>${num(c.recalque_mm, 2)}</td>
      <td style="white-space:normal">${esc2(c.fonte)}</td></tr>`).join("");
  const cor = Object.entries(D.admissivel.candidatas).map(([k, v]) =>
    `<tr><td>${esc2(k)}</td><td>${num(v, 1)} kPa</td>
      <td>${k === D.admissivel.governa ? "<b>adotada</b>" : "—"}</td></tr>`).join("");
  const T = G.terraplenagem;
  return `${barraModos()}${leitura("geotecnia")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Pressão de contato</span>
        <span class="val">${num(D.pressao_kpa, 2)}</span>
        <span class="uni">kPa contra ${num(D.admissivel.adotada_kpa, 1)} admissíveis</span></div>
      <div class="cartao"><span class="rot">Fator</span>
        <span class="val">${num(D.fator, 2)}</span>
        <span class="uni">mínimo ${num(D.fator_minimo, 0)}</span></div>
      <div class="cartao"><span class="rot">Recalque</span>
        <span class="val">${num(R.total_mm, 2)}</span>
        <span class="uni">mm de ${num(R.limite_total_mm, 0)} admitidos</span></div>
      <div class="cartao"><span class="rot">Sondagem</span>
        <span class="val">${num(I.investigada, 0)}</span>
        <span class="uni">m; crítica em ${num(I.z_critico, 1)} m</span></div>
    </div>
    <h4 class="sub">Perfil das três sondagens</h4>
    <p class="desenho cap">A barra é o N médio; o traço escuro é a faixa entre
      o furo mais fraco e o mais forte. É a DISPERSÃO, e não a média, que
      estima recalque diferencial — e recalque diferencial é o que trinca
      radier.</p>
    ${perfil}
    <h4 class="sub">Tensão admissível: três correlações, adota-se a menor</h4>
    <p class="desenho cap">Nenhuma das três nasceu deste solo. N/50 veio de
      sapata quadrada em areia pura; Teixeira-96 de solo arenoso, com a largura
      explícita; Mello-75 sem distinção, válida só entre N 4 e 16. Usar
      correlação fora do universo que a gerou só é honesto pelo lado
      conservador.</p>
    <table class="tab"><thead><tr><th>Correlação</th><th>Valor</th>
      <th>Situação</th></tr></thead><tbody>${cor}</tbody></table>
    <h4 class="sub">Recalque por camadas</h4>
    <table class="tab"><thead><tr><th>Camada</th><th>Δσ (kPa)</th>
      <th>E (MPa)</th><th>Recalque (mm)</th><th>De onde vem o E</th>
      </tr></thead><tbody>${cam}</tbody></table>
    <h4 class="sub">O que o solo mandou mudar</h4>
    <p class="desenho cap">${esc2(G.tratamento.razao)}</p>
    <div class="cartoes" style="margin:12px 0">
      <div class="cartao"><span class="rot">Troca</span>
        <span class="val">${num(T.profundidade * 1000, 0)}</span>
        <span class="uni">mm em ${num(T.area_tratada, 1)} m²</span></div>
      <div class="cartao"><span class="rot">Bota-fora</span>
        <span class="val">${num(T.bota_fora_m3, 1)}</span>
        <span class="uni">m³ (empolamento de 25 %)</span></div>
      <div class="cartao"><span class="rot">Substituição</span>
        <span class="val">${num(T.substituicao_m3, 1)}</span>
        <span class="uni">m³ em ${T.camadas} camadas, ${T.ensaios} ensaios</span></div>
      <div class="cartao"><span class="rot">Armadura</span>
        <span class="val">${num(G.armadura.total_kg, 0)}</span>
        <span class="uni">kg = ${num(G.armadura.taxa_kg_m3, 1)} kg/m³, e a taxa é resultado</span></div>
    </div>
    ${_conf(G.conferencia)}`;
}

function vistaPluvial() {
  const P = ENG.pluvial;
  if (!P) return barraModos() + "<p class='conta'>sem levantamento pluvial</p>";
  const B = P.balanco, G = P.gatilho, V = P.vazoes, R = P.retencao;
  const maior = Math.max(...B.superficies.map(s => s.area)) || 1;
  const sup = B.superficies.map(s =>
    `<div style="display:grid;grid-template-columns:200px 1fr 150px;gap:8px;
      align-items:center;font-family:var(--mono);font-size:11px;padding:2px 0">
      <span>${esc2(s.nome)}</span>
      <span style="height:12px;background:var(--rule-soft)">
        <i style="display:block;height:100%;width:${(s.area / maior * 100).toFixed(1)}%;
          background:${s.c >= 0.8 ? "#3f6fb5" : "#9dbfe4"}"></i></span>
      <span style="text-align:right">${num(s.area, 2)} m² · C ${s.c.toFixed(2)}</span>
    </div>`).join("");
  return `${barraModos()}${leitura("pluvial")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Superfícies</span>
        <span class="val">${num(B.total, 2)}</span>
        <span class="uni">m² declarados de ${num(B.lote, 0)} m² de lote</span></div>
      <div class="cartao"><span class="rot">Impermeável</span>
        <span class="val">${num(B.impermeavel, 2)}</span>
        <span class="uni">m² — gatilho da lei: ${num(G.limite_m2, 0)} m²</span></div>
      <div class="cartao"><span class="rot">Vazão</span>
        <span class="val">${num(V.q_pos_ls, 2)}</span>
        <span class="uni">L/s contra ${num(V.q_pre_ls, 2)} do terreno natural</span></div>
      <div class="cartao"><span class="rot">Retenção</span>
        <span class="val">${num(R.volume_m3, 2)}</span>
        <span class="uni">m³, orifício de ${num(R.orificio_mm, 0)} mm</span></div>
    </div>
    <h4 class="sub">A decisão</h4>
    <p class="desenho cap">${esc2(P.decisao.porque_a_retencao)}</p>
    <p class="desenho cap">${esc2(P.decisao.porque_nao_o_reuso)}</p>
    <h4 class="sub">Superfícies do lote — a soma tem de dar o lote</h4>
    <p class="desenho cap">Azul cheio é superfície impermeável (C ≥ 0,80).
      Não há classe "outros": sobra seria superfície não declarada, e
      superfície não declarada não escoa no cálculo e escoa na chuva.</p>
    ${sup}
    <h4 class="sub">A lei</h4>
    <p class="desenho cap"><b>${esc2(G.lei)}</b> — ${G.obriga ? "OBRIGA" :
      `não obriga: ${num(G.impermeavel, 2)} m² contra ${num(G.limite_m2, 0)} m²,
       folga de ${num(G.folga, 2)} m²`}. ${esc2(G.decisao)}</p>
    <ul class="lista">${G.exigencias.map(e => `<li>${esc2(e)}</li>`).join("")}</ul>
    <h4 class="sub">Do excedente ao orifício</h4>
    <p class="desenho cap">${esc2(R.obs)} Esvaziamento em
      ${num(R.esvaziamento_min, 1)} min: o reservatório volta a estar vazio
      antes da próxima chuva, que é a condição de ele servir para alguma
      coisa.</p>
    ${_conf(P.conferencia)}`;
}

function vistaMarcenaria() {
  const M = ENG.marcenaria;
  if (!M) return barraModos() + "<p class='conta'>sem marcenaria derivada</p>";
  const R = M.resumo, C = M.custo, F = M.ferragens;
  const linhas = M.moveis.map(m =>
    `<tr><td>${esc2(m.cod)}</td><td>${esc2(m.amb)}</td><td>${esc2(m.familia)}</td>
      <td class="num">${num(m.frente, 0)}</td><td class="num">${num(m.prof, 0)}</td>
      <td class="num">${num(m.alt, 0)}</td><td class="num">${m.n_modulos}</td>
      <td class="num">${m.n_portas}</td><td class="num">${m.n_gavetas}</td>
      <td class="num">${m.n_pecas}</td><td class="num">${num(m.area_frente_m2, 2)}</td>
      <td>${esc2(m.puxador)}</td></tr>`).join("");
  const ferr = [["Dobradiças", F.dobradicas, "un"], ["Corrediças", F.corredicas_par, "par"],
                ["Perfil gola", F.gola_m, "m"], ["Puxadores", F.puxadores, "un"],
                ["Suportes", F.suportes, "un"], ["Sapatas", F.sapatas, "un"],
                ["Cabideiro", F.cabideiro_m, "m"], ["Ripas", F.ripas_m, "m"]]
    .map(([n, q, u]) => `<tr><td>${n}</td><td class="num">${num(q, 1)}</td><td>${u}</td></tr>`).join("");
  const custo = C.linhas.map(l =>
    `<tr><td>${esc2(l.item)}</td><td class="num">${num(l.qtd, 1)}</td>
      <td class="num">${num(l.unit, 2)}</td><td class="num">${num(l.total, 2)}</td></tr>`).join("");
  const conf = M.conferencia.filter(c => !c.ok).map(c =>
    `<li><b>${esc2(c.titulo)}</b> — ${esc2(c.detalhe)}</li>`).join("");
  return `${barraModos()}${leitura("marcenaria")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Móveis</span><span class="val">${R.moveis}</span>
        <span class="uni">${R.modulos} módulos · ${R.pecas} peças</span></div>
      <div class="cartao"><span class="rot">Frente</span><span class="val">${num(R.frente_m2, 1)}</span>
        <span class="uni">m² · ${R.portas} portas · ${R.gavetas} gavetas</span></div>
      <div class="cartao"><span class="rot">Chapas 15 / 6 mm</span>
        <span class="val">${R.chapas["15"].n} / ${R.chapas["6"].n}</span>
        <span class="uni">${(R.chapas["15"].aproveitamento * 100).toFixed(0)} % de aproveitamento</span></div>
      <div class="cartao"><span class="rot">Material / serviço</span>
        <span class="val">${(C.razao * 100).toFixed(0)} %</span>
        <span class="uni">R$ ${num(C.material, 0)} de R$ ${num(C.servico_bom, 0)}</span></div>
    </div>
    <h4 class="sub">Quadro de móveis — tudo o que é marcenaria na casa</h4>
    <table class="tab"><thead><tr><th>cód</th><th>amb</th><th>família</th><th>frente</th><th>prof</th>
      <th>alt</th><th>mód</th><th>portas</th><th>gav</th><th>peças</th><th>m² fr</th><th>puxador</th></tr></thead>
      <tbody>${linhas}</tbody></table>
    <h4 class="sub">Ferragens derivadas</h4>
    <table class="tab"><thead><tr><th>item</th><th>qtd</th><th>un</th></tr></thead><tbody>${ferr}</tbody></table>
    <h4 class="sub">Material pelo plano x serviço sob medida do BOM</h4>
    <table class="tab"><thead><tr><th>item</th><th>qtd</th><th>unit R$</th><th>total R$</th></tr></thead>
      <tbody>${custo}</tbody></table>
    ${conf ? `<h4 class="sub">Conferências que não passam</h4><ul>${conf}</ul>` : "<p class='conta'>todas as conferências de marcenaria passam</p>"}`;
}

function vistaAcustica() {
  const A = ENG.acustica;
  if (!A) return barraModos() + "<p class='conta'>sem levantamento acústico</p>";
  const ps = A.entre_zonas.slice().sort((a, b) => a.folga - b.folga);
  const esc_ = 1.6;
  const barras = ps.map(p =>
    `<div style="display:grid;grid-template-columns:190px 1fr 210px;gap:8px;
      align-items:center;font-family:var(--mono);font-size:11px;padding:3px 0">
      <span>${esc2(p.fonte)} → ${esc2(p.receptor)}</span>
      <span style="height:13px;background:var(--rule-soft);position:relative">
        <i style="display:block;height:100%;width:${Math.min(p.obtido * esc_, 100)}%;
          background:${p.passa ? "#3f6fb5" : "#d03b3b"}"></i>
        <i style="position:absolute;top:-2px;height:17px;width:2px;background:#20242a;
          left:${Math.min(p.exigido * esc_, 100)}%"></i></span>
      <span style="text-align:right">${num(p.obtido, 1)} dB · exige
        ${num(p.exigido, 0)} · <b>${p.folga >= 0 ? "+" : ""}${num(p.folga, 1)}</b></span>
    </div>`).join("");
  const det = ps.map(p =>
    `<tr><td>${esc2(p.fonte)} → ${esc2(p.receptor)}</td>
      <td style="white-space:normal">${esc2(p.ruido)}</td>
      <td>${p.nivel} dB(A)</td><td>${esc2(p.uso_receptor)} · ${p.limite}</td>
      <td>${esc2(p.parede)} Rw ${p.rw_parede}</td>
      <td>${p.vaos.length ? p.vaos.join(", ") : "—"}</td>
      <td>${num(p.area_parede, 2)} / ${num(p.area_vao, 2)}</td>
      <td><b>${num(p.obtido, 1)}</b></td>
      <td>${num(p.estimado, 1)} dB(A)</td></tr>`).join("");
  const pior = ps[0];
  return `${barraModos()}${leitura("acustica")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Pares entre zonas</span>
        <span class="val">${ps.length}</span>
        <span class="uni">de ${A.pares.length} vizinhanças com fonte</span></div>
      <div class="cartao"><span class="rot">Reprovados</span>
        <span class="val">${ps.filter(p => !p.passa).length}</span>
        <span class="uni">depois das correções de R52</span></div>
      <div class="cartao"><span class="rot">Pior folga</span>
        <span class="val">${pior ? num(pior.folga, 1) : "—"}</span>
        <span class="uni">dB em ${pior ? esc2(pior.fonte + " → " + pior.receptor) : ""}</span></div>
    </div>
    <h4 class="sub">Isolamento obtido contra exigido</h4>
    <p class="desenho cap">A barra é o isolamento do fechamento inteiro —
      parede e porta somadas por ENERGIA, não por média. O traço vertical é o
      exigido: nível da fonte menos o limite do receptor (NBR 10152). Pares
      dentro da mesma zona acústica não aparecem: ali o ruído não é defeito,
      é o programa.</p>
    ${barras}
    <h4 class="sub">Como cada número foi obtido</h4>
    <table class="tab"><thead><tr><th>Par</th><th>Fonte</th><th>Nível</th>
      <th>Receptor · limite</th><th>Parede</th><th>Vãos</th>
      <th>m² parede/vão</th><th>Rw composto</th><th>Chega</th>
      </tr></thead><tbody>${det}</tbody></table>
    ${_conf(A.conferencia)}`;
}

function vistaEletrica() {
  const E = ENG.eletrica, M = ENG.mercado;
  if (!E) return barraModos() + "<p class='conta'>sem quadro de cargas</p>";
  const Q = E.equilibrio, N = E.entrada;
  const maxf = Math.max(...Object.values(Q.por_fase)) || 1;
  const fases = Object.entries(Q.por_fase).map(([f, va]) =>
    `<div style="display:grid;grid-template-columns:70px 1fr 190px;gap:8px;
      align-items:center;font-family:var(--mono);font-size:11px;padding:3px 0">
      <span>Fase ${f}</span>
      <span style="height:14px;background:var(--rule-soft)">
        <i style="display:block;height:100%;width:${(va / maxf * 100).toFixed(1)}%;
          background:#3f6fb5"></i></span>
      <span style="text-align:right">${num(va, 0)} VA ·
        ${num(Q.corrente_por_fase[f], 1)} A</span></div>`).join("");
  const circ = Q.circuitos.slice().sort((a, b) => b.va - a.va).map(c =>
    `<tr><td>${esc2(c.cod)}</td><td>${esc2(c.tipo)}</td><td>${c.v} V</td>
      <td>${num(c.va, 0)}</td><td>${c.fases.join("-")}</td>
      <td style="white-space:normal">${esc2(c.desc || c.amb || "")}</td></tr>`).join("");
  const forn = M ? M.cobertura.linhas.map(l =>
    `<tr><td>${esc2(l.familia)}</td><td>${(l.fracao * 100).toFixed(1)} %</td>
      <td>${l.fornecedores}</td><td>${l.manaus}</td>
      <td style="white-space:normal">${esc2(l.lista.map(f => f[0]).join(", "))}</td>
      </tr>`).join("") : "";
  const fora = M ? M.fora_do_orcamento.map(([k, v]) =>
    `<tr><td><b>${esc2(k)}</b></td>
      <td style="white-space:normal">${esc2(v)}</td></tr>`).join("") : "";
  const idx = M ? M.indices.map(i =>
    `<tr><td>${esc2(i.nome)}</td><td>${num(i.valor, 2)} ${esc2(i.unidade)}</td>
      <td>${esc2(i.data)}</td><td>${esc2(i.praca)}</td>
      <td style="white-space:normal">${esc2(i.escopo)}</td></tr>`).join("") : "";
  return `${barraModos()}${leitura("eletrica")}
    <div class="cartoes" style="margin-bottom:16px">
      <div class="cartao"><span class="rot">Esquema</span>
        <span class="val">220/127</span>
        <span class="uni">trifásico, estrela com neutro</span></div>
      <div class="cartao"><span class="rot">Desequilíbrio</span>
        <span class="val">${(Q.desequilibrio * 100).toFixed(2)} %</span>
        <span class="uni">contra ${(Q.limite * 100).toFixed(0)} % admitidos</span></div>
      <div class="cartao"><span class="rot">Entrada</span>
        <span class="val">${N.disjuntor_a} A</span>
        <span class="uni">${N.secao_mm2} mm² para ${num(N.corrente_a, 1)} A</span></div>
      <div class="cartao"><span class="rot">Circuitos</span>
        <span class="val">${Q.circuitos.length}</span>
        <span class="uni">com fase atribuída no projeto</span></div>
    </div>
    <h4 class="sub">Carga por fase</h4>
    <p class="desenho cap">Num 220/127 a carga de 127 V fica entre fase e
      neutro e a de 220 V entre duas fases. Se as de 127 se acumulam numa
      fase, ela aquece e a tensão cai nela — e ninguém percebe até a lâmpada
      piscar quando a secadora liga.</p>
    ${fases}
    <h4 class="sub">Circuitos e a fase de cada um</h4>
    <table class="tab"><thead><tr><th>Circuito</th><th>Tipo</th><th>Tensão</th>
      <th>VA</th><th>Fase</th><th>Onde</th></tr></thead>
      <tbody>${circ}</tbody></table>
    ${M ? `<h4 class="sub">De quem se compra</h4>
    <p class="desenho cap">A pesquisa devolveu a identidade dos fornecedores e
      os índices públicos; não devolveu preço unitário. Todo preço do
      orçamento segue (H).</p>
    <table class="tab"><thead><tr><th>Família</th><th>% custo</th>
      <th>Fornec.</th><th>Manaus</th><th>Nomes</th></tr></thead>
      <tbody>${forn}</tbody></table>
    <h4 class="sub">Índices públicos, com data e escopo</h4>
    <table class="tab"><thead><tr><th>Índice</th><th>Valor</th><th>Data</th>
      <th>Praça</th><th>Escopo</th></tr></thead><tbody>${idx}</tbody></table>
    <h4 class="sub">O que NÃO está neste orçamento</h4>
    <p class="desenho cap">Foi a conferência de cima para baixo que obrigou a
      escrever esta lista: comparar o total com um índice de obra entregue só
      faz sentido sabendo o que falta entre um e outro.</p>
    <table class="tab"><thead><tr><th>Escopo</th>
      <th>Situação no modelo</th></tr></thead><tbody>${fora}</tbody></table>` : ""}
    ${_conf(E.conferencia)}
    ${M ? _conf(M.conferencia) : ""}`;
}
'''
