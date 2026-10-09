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
3. Na aba **Produtos** você ajusta preço/estoque, tira do ar (desmarcando "Ativo") e troca fotos.
   Os produtos de demonstração podem ser desativados ali mesmo.
O token do painel `/admin` é impresso no terminal (ou defina `TIPITI_ADMIN_TOKEN`).

| Variável | Padrão | Para quê |
|---|---|---|
| `TIPITI_HOST` / `TIPITI_PORT` | `127.0.0.1` / `8000` | Endereço do servidor |
| `TIPITI_DB` | `data/tipiti.db` | Arquivo do banco |
| `TIPITI_ADMIN_TOKEN` | gerado a cada execução | Acesso ao painel `/admin` |
| `TIPITI_SITE_URL` | `https://tipiti.com.br` | Links canônicos, sitemap |
| `TIPITI_EMAIL` | `contato@tipiti.com.br` | E-mail exibido na loja |

## O que já tem

- **Vitrine**: categorias, destaques, novidades, busca sem acento ("oculos" acha "Óculos"), ordenação.
- **Produto**: preço "de/por", preço no Pix, parcelamento, estoque, simulador de frete por CEP.
- **Carrinho e checkout**: recalculado no servidor (o navegador nunca define preço), máscaras de
  CPF/CEP/telefone, validação de CPF, endereço preenchido pelo ViaCEP, Pix/cartão/boleto.
- **Pedidos**: baixa de estoque em transação (não vende o que não tem), código `TPT-XXXXXXXX`,
  página de confirmação sem expor dados pessoais; cancelamento devolve o estoque.
- **Painel `/admin`**: pedidos com mudança de status; produtos com preço, estoque, ativo e destaque;
  **cadastro de produtos novos com foto** (aba "+ Novo produto") e troca de foto dos existentes.
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
  regras.py            catálogo, carrinho, pedidos, validações
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
