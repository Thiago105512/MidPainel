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
   descrição e foto (JPG/PNG/WEBP até 3 MB). O produto aparece na loja na hora.
3. Você cai no editor do produto, onde pode adicionar mais fotos, criar opções (ex.: Preto, Branco,
   127 V, 220 V — cada uma com estoque) e usar a calculadora para aplicar preço e custo.
4. Na aba **Produtos** você volta ao editor de qualquer item, tira do ar (desmarcando "Produto no ar")
   ou desativa os produtos de demonstração.
5. Em **Configurações**, informe o WhatsApp da loja para ativar os botões de WhatsApp no site.

O lucro mostrado no painel é: valor dos produtos (já com desconto do Pix) − custo cadastrado.
O frete cobrado do cliente fica fora da conta. Pedidos de produtos sem custo cadastrado aparecem como "sem custo".
O token do painel `/admin` é impresso no terminal (ou defina `TIPITI_ADMIN_TOKEN`).

| Variável | Padrão | Para quê |
|---|---|---|
| `TIPITI_HOST` / `TIPITI_PORT` | `127.0.0.1` / `8000` | Endereço do servidor |
| `TIPITI_DB` | `data/tipiti.db` | Arquivo do banco |
| `TIPITI_ADMIN_TOKEN` | gerado a cada execução | Acesso ao painel `/admin` |
| `TIPITI_SITE_URL` | `https://tipiti.com.br` | Links canônicos, sitemap |
| `TIPITI_EMAIL` | `contato@tipiti.com.br` | E-mail exibido na loja |
| `TIPITI_WHATSAPP` | vazio | WhatsApp inicial (o do painel tem prioridade) |

## O que já tem

- **Vitrine**: categorias, destaques, novidades, busca sem acento ("oculos" acha "Óculos"), ordenação.
- **Produto**: preço "de/por", preço no Pix, parcelamento, estoque, simulador de frete por CEP.
- **Carrinho e checkout**: recalculado no servidor (o navegador nunca define preço), máscaras de
  CPF/CEP/telefone, validação de CPF, endereço preenchido pelo ViaCEP, Pix/cartão/boleto.
- **Pedidos**: baixa de estoque em transação (não vende o que não tem), código `TPT-XXXXXXXX`,
  página de confirmação sem expor dados pessoais; cancelamento devolve o estoque.
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
  - *Configurações*: número do WhatsApp e padrões da calculadora (câmbio, impostos, taxa, margem).
- **SEO**: título/descrição por página de produto e categoria, `sitemap.xml`, `robots.txt`.

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
  regras.py            catálogo, opções, fotos, carrinho, pedidos, validações
  precificacao.py      calculadora de preço do importado
  ajustes.py           configurações editáveis no painel (WhatsApp, padrões da calculadora)
  fotos.py             gravação e validação das fotos enviadas
  db.py                esquema SQLite e carga inicial
  catalogo_inicial.py  produtos de demonstração
  imagens.py           imagens provisórias (SVG) até as fotos reais
  servidor.py          servidor HTTP, API e páginas
static/                index.html, css/, js/, img/
tests/                 testes de regras e da API
```

## Próximos passos

1. **Gateway de pagamento** (Mercado Pago, Pagar.me, Asaas…): hoje o pedido fica "Aguardando
   pagamento" e não há cobrança real.
2. Cadastro do catálogo definitivo (já é possível pelo painel).
3. **Cotação de frete real** (Correios/transportadoras) e cálculo por peso/volume.
4. E-mails transacionais (confirmação, envio, rastreio) e conta de cliente.
5. Hospedagem com HTTPS para `tipiti.com.br` (proxy reverso na frente do servidor) e backup do banco.
