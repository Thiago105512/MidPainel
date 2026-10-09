# Tipiti — tipiti.com.br

Loja virtual de produtos importados da China (achadinhos, eletrônicos, casa, beleza, moda…), com atendimento e logística focados na
**Região Norte**: Manaus, Parintins, Boa Vista, Santarém, Macapá, Belém, Rio Branco, Porto Velho
e interior dos estados do Norte. Também entrega no restante do Brasil.

Projeto independente: não usa nada do restante deste repositório e não tem dependências externas
(Python 3.10+ só com a biblioteca padrão; front-end em HTML/CSS/JS puro).

## Rodando

```bash
cd tipiti
python3 -m loja                # http://127.0.0.1:8000
python3 -m unittest discover -s tests -t .
```

Na primeira execução o banco SQLite é criado em `data/tipiti.db` com um catálogo de demonstração
(as fotos enviadas pelo painel ficam em `data/fotos/`). Para recomeçar do catálogo inicial, apague a pasta `data/`.

## Como cadastrar seus produtos

1. Rode a loja e abra `http://127.0.0.1:8000/admin`; entre com o token mostrado no terminal.
2. Aba **+ Novo produto**: nome, categoria, preço de venda (e opcionalmente o preço "de"), estoque,
   descrição e fotos (JPG/PNG/WEBP; o navegador reduz para 1200 px e gera uma miniatura de 400 px antes de enviar).
   O produto aparece na loja na hora.
3. Você cai no editor do produto, onde pode adicionar mais fotos, criar opções (ex.: Preto, Branco,
   127 V, 220 V — cada uma com estoque) e usar a calculadora para aplicar preço e custo.
4. Na aba **Produtos** você volta ao editor de qualquer item, tira do ar (desmarcando "Produto no ar")
   ou desativa os produtos de demonstração.
5. Em **Configurações**, informe o WhatsApp da loja (ativa os botões de WhatsApp no site) e a chave Pix
   (mostrada ao cliente na confirmação do pedido).

O lucro mostrado no painel é: valor dos produtos (já com os descontos do cupom e do Pix) − custo cadastrado.
O frete cobrado do cliente fica fora da conta. Pedidos de produtos sem custo cadastrado aparecem como "sem custo".
O token do painel `/admin` é gerado e impresso no terminal só quando o servidor escuta no próprio computador
(`127.0.0.1`/`localhost`). Em qualquer outro endereço `TIPITI_ADMIN_TOKEN` é obrigatório, com pelo menos 24 caracteres
(ex.: `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`).

| Variável | Padrão | Para quê |
|---|---|---|
| `TIPITI_HOST` / `TIPITI_PORT` | `127.0.0.1` / `8000` | Endereço do servidor |
| `TIPITI_DB` | `data/tipiti.db` | Arquivo do banco |
| `TIPITI_ADMIN_TOKEN` | gerado a cada execução (só em localhost) | Acesso ao painel `/admin` (mín. 24 caracteres) |
| `TIPITI_TRUST_PROXY` | vazio | `1` atrás de proxy reverso: o IP do cliente vem do último valor de `X-Forwarded-For` |
| `TIPITI_SITE_URL` | `https://tipiti.com.br` | Links canônicos, sitemap |
| `TIPITI_EMAIL` | `contato@tipiti.com.br` | E-mail exibido na loja |
| `TIPITI_WHATSAPP` | vazio | WhatsApp inicial (o do painel tem prioridade) |

## O que já tem

- **Vitrine**: categorias, destaques, novidades, busca sem acento ("oculos" acha "Óculos"), ordenação,
  "Carregar mais" de 24 em 24.
- **Produto**: preço "de/por", preço no Pix, parcelamento, estoque, simulador de frete por CEP;
  no celular, barra fixa de compra (com o WhatsApp) e painel "adicionado ao carrinho".
- **Carrinho e checkout**: recalculado no servidor (o navegador nunca define preço), total no Pix e no cartão,
  máscaras de CPF/CEP/telefone, validação de CPF ao sair do campo, endereço preenchido pelo ViaCEP,
  Pix/cartão/boleto; no máximo 10 unidades por item.
- **Pedidos**: baixa de estoque em transação (não vende o que não tem), código `TPT-` com 12 caracteres,
  página de confirmação sem expor dados pessoais, com a chave Pix para copiar; cancelamento devolve o estoque.
- **Reserva de estoque**: pedido não pago em 24 h (`PRAZO_RESERVA_HORAS`) é cancelado e as unidades voltam à venda.
- **Opções de produto** (cor, voltagem, tamanho): cada opção tem estoque e, se quiser, preço próprio;
  o cliente escolhe na página do produto e o estoque baixa da opção certa.
- **Galeria**: até 8 fotos por produto, com capa e miniaturas na página do produto.
- **WhatsApp**: botão flutuante de atendimento, "Pedir pelo WhatsApp" no produto, "Finalizar pelo WhatsApp"
  no carrinho, "Enviar meu pedido" na confirmação e link para o WhatsApp do cliente no painel.
- **Painel `/admin`**:
  - *Pedidos*: faturamento, lucro estimado, ticket médio, aviso de estoque baixo e lucro de cada pedido.
  - *Produtos*: lista com custo e margem; editor com dados, fotos, opções e calculadora.
  - *+ Novo produto*: cadastro com várias fotos e custo.
  - *Calculadora*: custo real do importado (preço em US$/¥/R$, câmbio, frete e outros custos do lote,
    impostos, embalagem) e preço sugerido para a margem desejada, já descontada a taxa do pagamento.
  - *Configurações*: WhatsApp, chave Pix e padrões da calculadora (câmbio, impostos, taxa, margem).
  - Funciona no celular: abas roláveis e tabelas que viram cartões.
- **Segurança**: limites de tentativas por IP (pedidos, token errado do painel, consulta de pedido inexistente)
  com resposta 429; corpo da requisição limitado e validado; cabeçalhos CSP, HSTS, COOP e X-Frame-Options.
- **Velocidade**: gzip com cache, ETag/304, `app.js` e `estilo.css` versionados (`?v=<hash>`) com cache de um ano,
  dados iniciais embutidos na página, imagens provisórias em SVG geradas no navegador.
- **SEO**: título/descrição por página de produto e categoria, `sitemap.xml`, `robots.txt`.

## Gatilhos de venda

Tudo sai de dados reais do banco: nenhum número, selo, contador ou avaliação é inventado, e nenhum prazo reinicia.

- **Oferta relâmpago**: desconto de 1% a 90% com data de término, aplicado ao produto e às opções dele.
  Terminado o prazo, o preço volta sozinho. `/api/produtos?promo=1` lista só as ofertas ativas.
  O preço riscado é o preço normal (ou o preço "de", se maior).
- **Prova social**: unidades vendidas nos últimos 30 dias (pedidos não cancelados) e selos *oferta*,
  *mais vendido* (top 3 da categoria, com pelo menos 3 vendidos), *novidade* (cadastrado há até 14 dias)
  e *últimas unidades* (até 5 em estoque); ordenação "mais vendidos".
- **Compras recentes**: `/api/vendas-recentes` mostra produto, cidade e UF das compras das últimas 72 h
  (sem nome do cliente); pode ser desligado em Configurações.
- **Comprados juntos**: na página do produto, os itens que mais aparecem nos mesmos pedidos.
- **Avaliações de compra verificada**: só quem recebeu o pedido avalia (código + e-mail do pedido), uma vez por
  produto; a avaliação só aparece depois de aprovada no painel. Nome exibido: "Maria de Parintins".
- **Cupons**: porcentagem, valor fixo ou frete grátis, com valor mínimo, validade, limite de usos e opção
  "só na primeira compra" (pelo CPF). O uso é contado na transação do pedido e volta se ele for cancelado.
  Cálculo: subtotal → cupom → Pix sobre o restante → frete. Um cupom pode ficar em destaque na loja.
- **Envio no mesmo dia**: com o horário de corte (Configurações), a loja mostra até quando o pedido sai hoje,
  em dias úteis, no horário de Manaus.
- No painel: `/api/admin/cupons` e `/api/admin/avaliacoes` (moderação).

## Regras comerciais (em `loja/config.py` e `loja/frete.py`)

- Frete grátis **para a Região Norte** acima de R$ 199 (fora do Norte, frete fixo de referência).
- 5% de desconto no Pix; até 6x sem juros com parcela mínima de R$ 30.
- Tabela de frete por faixa de CEP, expedição a partir de Manaus. **Os valores, prazos e faixas
  de CEP são de referência** — ajuste com a transportadora/Correios antes de abrir a loja.

## Estrutura

```
loja/
  config.py            configurações e regras comerciais
  frete.py             zonas de frete por CEP (Norte primeiro)
  regras.py            reúne e reexporta as regras de negócio abaixo (use `regras.X`)
    validacao.py       erros de validação, CPF, e-mail, CEP, UF
    catalogo.py        categorias, listagem e detalhe de produtos
    carrinho.py        cotação do carrinho, frete, desconto no Pix, parcelas
    reservas.py        status dos pedidos, cancelamento e expiração da reserva de estoque
    pedidos.py         criação, consulta e listagem de pedidos, resumo de vendas
    admin_produtos.py  cadastro e edição de produtos, opções e galeria de fotos
    promocoes.py       oferta relâmpago: preço com desconto e preço riscado
    prova_social.py    vendidos em 30 dias, selos, compras recentes, comprados juntos
    avaliacoes.py      avaliações de compra verificada e moderação
    cupons.py          cupons de desconto
  horario.py           datas em UTC no banco, ISO na API, fuso de Manaus (UTC−4)
  precificacao.py      calculadora de preço do importado
  ajustes.py           configurações editáveis no painel (WhatsApp, chave Pix, calculadora, horário de corte,
                       compras recentes)
  fotos.py             gravação e validação das fotos enviadas
  db.py                esquema SQLite e carga inicial
  catalogo_inicial.py  produtos de demonstração
  imagens.py           imagens provisórias (SVG) até as fotos reais
  rotas.py             rotas da API JSON
  limites.py           limites de tentativas por IP
  servidor.py          servidor HTTP: estáticos (gzip, cache), páginas e inicialização
static/
  index.html, css/, img/
  js/partes/           o JavaScript da loja em partes numeradas (01-utilidades.js … 09-roteador.js);
                       o servidor as junta em ordem de nome e entrega como um arquivo só, /static/js/app.js
tests/                 testes de regras, do servidor, da API e do app.js montado
```

As partes do JavaScript são scripts comuns (não módulos) e dividem o mesmo escopo: `"use strict"` fica só no
início da primeira. Para criar uma parte nova, basta um arquivo `.js` com o número da posição.

## Próximos passos

1. **Gateway de pagamento** (Mercado Pago, Pagar.me, Asaas…): hoje o pedido fica "Aguardando
   pagamento" e não há cobrança real.
2. Cadastro do catálogo definitivo (já é possível pelo painel).
3. **Cotação de frete real** (Correios/transportadoras) e cálculo por peso/volume.
4. E-mails transacionais (confirmação, envio, rastreio) e conta de cliente.
5. Hospedagem com HTTPS para `tipiti.com.br` (proxy reverso na frente do servidor) e backup do banco.

## E-mail (SMTP)

Os e-mails (confirmação do pedido, mudança de status/rastreio, link da "Minha conta", avise-me e resposta LGPD)
entram numa fila no banco e são enviados por uma thread em segundo plano, com até 5 tentativas e espera crescente.
Sem SMTP configurado eles ficam "pendentes" (painel: `GET /api/admin/emails`, reenvio em
`POST /api/admin/emails/<id>/reenviar`). A configuração é só por variáveis de ambiente:

| Variável | Padrão | Para quê |
|---|---|---|
| `TIPITI_SMTP_HOST` | vazio (e-mail desligado) | Servidor SMTP (ex.: do seu provedor de e-mail transacional) |
| `TIPITI_SMTP_PORTA` | `587` | Porta |
| `TIPITI_SMTP_USUARIO` / `TIPITI_SMTP_SENHA` | vazio | Login no SMTP (a senha nunca aparece no painel nem no log) |
| `TIPITI_SMTP_REMETENTE` | `Tipiti <contato@tipiti.com.br>` | Remetente (configure SPF/DKIM do domínio no provedor) |
| `TIPITI_SMTP_TLS` | `starttls` | `starttls`, `ssl` (porta 465) ou `nenhum` |

## Usuários do painel, papéis e verificação em duas etapas

- Entre no `/admin` com o `TIPITI_ADMIN_TOKEN` e crie o primeiro usuário **dono** (`POST /api/admin/usuarios`).
  Depois disso, use login (e-mail) e senha; o token continua valendo como **acesso de emergência** (papel dono) —
  guarde-o fora do dia a dia.
- Papéis: **dono** vê tudo; **operador** cuida de pedidos, separação/etiquetas, produtos (sem custo), avaliações,
  avise-me, carrinhos abandonados, encomendas e viagens. O operador recebe 403 em calculadora, cupons,
  configurações, usuários, revendedoras, privacidade, e-mails, feeds e histórico, e os campos de custo, lucro, margem
  e comissão são retirados de todas as respostas para ele (regra central em `loja/usuarios.py`, `OPERADOR_PODE`;
  rotas novas podem declarar `papel="operador"` ou `papel="dono"` na `@rota`).
- Senhas com PBKDF2-SHA256 (600 000 iterações, sal aleatório); sessões de 12 h renovadas a cada uso, guardadas só
  como hash; trocar a senha ou desativar o usuário encerra as sessões.
- 2FA (TOTP, compatível com Google Authenticator, Authy etc.): `POST /api/admin/eu/2fa/iniciar` → cadastre o segredo
  no aplicativo → `POST /api/admin/eu/2fa/confirmar`. Celular perdido: o dono desativa com
  `PATCH /api/admin/usuarios/<id>` `{"desativar_2fa": true}`.
- Toda escrita no painel (e login, falhas de login e exportação de dados pessoais) fica em `GET /api/admin/historico`.

## LGPD e identificação da loja

- Em Configurações, preencha razão social, CNPJ/CPF, endereço completo, cidade/UF/CEP, e-mail e telefone
  (Decreto 7.962/2013). Enquanto faltar algo, `/api/loja` e o resumo do painel listam as `pendencias_legais`.
- `/privacidade` e `/termos` são gerados com esses dados. **São modelos**: revise com um advogado antes de abrir a loja.
- O checkout exige aceite dos termos (`aceite_termos: true`) e guarda o aceite opcional de contato por WhatsApp,
  com data e hora.
- Pedidos do titular em `/meus-dados` (`POST /api/privacidade/solicitacoes`, protocolo `LGPD-XXXXXXXX`, prazo de
  resposta de 15 dias). No painel (só dono): exportar tudo o que a loja tem do CPF/e-mail e anonimizar — os valores,
  itens, datas, cidade e UF dos pedidos ficam (obrigação fiscal); nome, e-mail, CPF, telefone e endereço são trocados.
  Confirme a identidade do titular antes de enviar a cópia dos dados.
- Prazos de guarda aplicados automaticamente: carrinhos abandonados 30 dias, links de acesso 30 minutos (apagados em
  1 dia), sessões da Minha conta 30 dias, avise-me 180 dias após o aviso, e-mails enviados 180 dias.
