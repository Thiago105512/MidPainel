"""Identificação da loja (Decreto 7.962/2013) e textos legais: política de privacidade e termos de uso.

Os textos são modelos em português simples, preenchidos com os dados da empresa cadastrados em Configurações.
Onde faltar um dado aparece "[a preencher]". Recomenda-se a revisão por um advogado antes de publicar.
"""

from . import config
from .validacao import UFS, cnpj_valido, cpf_valido, email_valido, so_digitos

A_PREENCHER = "[a preencher]"
ATUALIZADO_EM = "2026-10-09"

# Ajustes novos (texto; vazio = não preenchido)
PADROES_EMPRESA = {
    "empresa_razao_social": "",
    "empresa_nome_fantasia": "Tipiti",
    "empresa_documento": "",      # CNPJ ou CPF, só dígitos
    "empresa_endereco": "",       # logradouro, número, complemento, bairro
    "empresa_cidade": "",
    "empresa_uf": "",
    "empresa_cep": "",
    "empresa_email": "",
    "empresa_telefone": "",
    "encarregado_dados": "",      # nome/e-mail do encarregado (LGPD); vazio = e-mail da empresa
}

# Prazos de guarda citados na política (e aplicados em retencao.py)
RETENCAO_CARRINHO_DIAS = 30
RETENCAO_AVISE_ME_DIAS = 180
RETENCAO_FISCAL_ANOS = 5


def validar_campo(chave, valor, erros):
    """Normaliza um ajuste da empresa; problemas vão para `erros[chave]`. Devolve o texto a gravar."""
    texto = " ".join(str(valor if valor is not None else "").split())
    if chave == "empresa_documento":
        d = so_digitos(texto)
        if d and not ((len(d) == 14 and cnpj_valido(d)) or (len(d) == 11 and cpf_valido(d))):
            erros[chave] = "Informe um CNPJ ou CPF válido."
        return d
    if chave == "empresa_uf":
        texto = texto.upper()
        if texto and texto not in UFS:
            erros[chave] = "Selecione o estado."
        return texto
    if chave == "empresa_cep":
        d = so_digitos(texto)
        if d and len(d) != 8:
            erros[chave] = "Informe um CEP com 8 dígitos."
        return d
    if chave == "empresa_email":
        texto = texto.lower()
        if texto and not email_valido(texto):
            erros[chave] = "Informe um e-mail válido."
        return texto
    if chave == "empresa_telefone":
        d = so_digitos(texto)
        if d and not 10 <= len(d) <= 13:
            erros[chave] = "Informe o telefone com DDD."
        return d
    if len(texto) > 200:
        erros[chave] = "Use no máximo 200 caracteres."
    return texto


def formatar_documento(d):
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return d or None


def formatar_cep(d):
    return f"{d[:5]}-{d[5:]}" if len(d) == 8 else d


def formatar_telefone(d):
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return d


def endereco_completo(a):
    """'Rua X, 10, Centro, Manaus - AM, CEP 69005-000' — só quando todas as partes estão preenchidas."""
    partes = [a.get(c, "") for c in ("empresa_endereco", "empresa_cidade", "empresa_uf", "empresa_cep")]
    if not all(partes):
        return None
    return f"{partes[0]}, {partes[1]} - {partes[2]}, CEP {formatar_cep(partes[3])}"


def empresa(a):
    """Bloco `empresa` do /api/loja (campos vazios viram null)."""
    return {
        "razao_social": a.get("empresa_razao_social") or None,
        "nome_fantasia": a.get("empresa_nome_fantasia") or config.NOME_LOJA,
        "documento_formatado": formatar_documento(a.get("empresa_documento") or ""),
        "endereco_completo": endereco_completo(a),
        "email": a.get("empresa_email") or None,
        "telefone": formatar_telefone(a.get("empresa_telefone") or "") or None,
    }


def encarregado(a):
    return a.get("encarregado_dados") or a.get("empresa_email") or ""


def pendencias(a):
    """Rótulos dos dados obrigatórios (Decreto 7.962/2013, art. 2º) que ainda faltam."""
    faltam = []
    if not a.get("empresa_razao_social"):
        faltam.append("razão social")
    if not a.get("empresa_documento"):
        faltam.append("documento (CNPJ ou CPF)")
    if not endereco_completo(a):
        faltam.append("endereço completo")
    if not a.get("empresa_email"):
        faltam.append("e-mail")
    return faltam


# ---------------------------------------------------------------- textos

def _dados(a):
    e = empresa(a)
    return {
        "nome": e["nome_fantasia"],
        "razao": e["razao_social"] or A_PREENCHER,
        "doc": e["documento_formatado"] or A_PREENCHER,
        "tipo_doc": "CPF" if len(a.get("empresa_documento") or "") == 11 else "CNPJ",
        "endereco": e["endereco_completo"] or A_PREENCHER,
        "email": e["email"] or A_PREENCHER,
        "telefone": e["telefone"] or A_PREENCHER,
        "encarregado": encarregado(a) or A_PREENCHER,
        "cidade_foro": (f"{a['empresa_cidade']} - {a['empresa_uf']}"
                        if a.get("empresa_cidade") and a.get("empresa_uf") else A_PREENCHER),
        "site": config.SITE_URL,
    }


def _documento(titulo, secoes):
    return {"titulo": titulo, "atualizado_em": ATUALIZADO_EM,
            "secoes": [{"titulo": t, "paragrafos": list(p)} for t, p in secoes]}


def politica_privacidade(a):
    d = _dados(a)
    return _documento("Política de Privacidade", [
        ("Quem somos", [
            f"Esta política explica como a {d['nome']} ({d['razao']}, {d['tipo_doc']} {d['doc']}), com endereço em "
            f"{d['endereco']}, trata os seus dados pessoais quando você usa o site {d['site']}, faz um pedido ou fala "
            "com a gente, de acordo com a Lei Geral de Proteção de Dados (Lei 13.709/2018 — LGPD).",
            f"Somos a controladora dos seus dados. Dúvidas: {d['email']}.",
        ]),
        ("Quais dados coletamos", [
            "Para fazer e entregar o seu pedido: nome completo, e-mail, CPF, telefone/WhatsApp e endereço de entrega "
            "(CEP, rua, número, complemento, bairro, cidade e estado).",
            "Do pedido: produtos, valores, forma de pagamento, cupom usado, data e situação da entrega.",
            "Quando você usa outros recursos: contato informado no \"Avise-me quando chegar\", WhatsApp e itens do "
            "carrinho (se você autorizar o contato), endereços salvos na \"Minha conta\" e avaliações que você escrever.",
            "Dados técnicos: endereço IP e data/hora de acesso, usados para segurança e para limitar abusos.",
            "Não pedimos dados sensíveis (saúde, religião, biometria etc.) e não vendemos produtos para menores de 18 "
            "anos sem a participação dos responsáveis.",
        ]),
        ("Para que usamos e com qual base legal", [
            "Executar o contrato de compra (art. 7º, V): registrar o pedido, receber o pagamento, separar, enviar, "
            "avisar sobre a entrega e atender trocas e devoluções.",
            "Cumprir obrigações legais e fiscais (art. 7º, II): emitir nota fiscal e guardar os registros exigidos "
            "pela legislação tributária e pelo Código de Defesa do Consumidor.",
            "Legítimo interesse (art. 7º, IX): prevenir fraudes e abusos (por exemplo, limitar tentativas repetidas "
            "e conferir CPF em cupons de primeira compra) e melhorar a loja, sempre respeitando os seus direitos.",
            "Consentimento (art. 7º, I): mandar mensagens pelo WhatsApp sobre o pedido, o carrinho que ficou "
            "aberto e ofertas, e avisar quando um produto chegar. Você pode retirar o consentimento a qualquer "
            "momento, respondendo \"parar\" ou escrevendo para o e-mail abaixo.",
        ]),
        ("Com quem compartilhamos", [
            "Transportadoras, Correios e empresas de transporte fluvial: nome, telefone e endereço, só para a entrega.",
            "Meio de pagamento (banco, Pix ou intermediador de cartão/boleto): dados necessários para a cobrança.",
            "Contabilidade: dados do pedido para a escrituração fiscal.",
            "Provedores de hospedagem e de envio de e-mail, que tratam os dados em nosso nome e sob as nossas instruções.",
            "Autoridades públicas, quando a lei ou uma ordem judicial exigir. Não vendemos nem alugamos os seus dados.",
        ]),
        ("Por quanto tempo guardamos", [
            f"Pedidos e notas: pelo prazo da legislação fiscal (em regra, {RETENCAO_FISCAL_ANOS} anos) e pelo prazo "
            "para eventuais reclamações de consumo.",
            f"Carrinhos não finalizados: até {RETENCAO_CARRINHO_DIAS} dias. Links de acesso à \"Minha conta\": até "
            "30 minutos (e são de uso único). Sessões da \"Minha conta\": até 30 dias.",
            f"Pedidos de \"Avise-me\": até o aviso e, depois dele, por até {RETENCAO_AVISE_ME_DIAS} dias.",
            "Terminado o prazo, os dados são apagados ou anonimizados.",
        ]),
        ("Seus direitos (art. 18 da LGPD)", [
            "Você pode pedir: confirmação de que tratamos seus dados; acesso e cópia; correção de dados incompletos ou "
            "errados; anonimização, bloqueio ou eliminação de dados desnecessários ou tratados em desacordo com a lei; "
            "portabilidade; eliminação dos dados tratados com consentimento; informação sobre com quem compartilhamos; "
            "informação sobre a possibilidade de não consentir; e revogação do consentimento.",
            f"Faça o pedido na página {d['site']}/meus-dados ou pelo e-mail {d['email']}. Você recebe um protocolo e a "
            "resposta em até 15 dias. Para a sua segurança, podemos confirmar a sua identidade antes de responder.",
            "Dados que a lei manda guardar (como os de notas fiscais) são mantidos pelo prazo legal, mesmo após um "
            "pedido de exclusão; nesse caso apagamos ou anonimizamos tudo o que não for obrigatório.",
            "Você também pode reclamar à Autoridade Nacional de Proteção de Dados (ANPD).",
        ]),
        ("Segurança", [
            "Usamos conexão segura (HTTPS), acesso ao painel com senha forte e verificação em duas etapas, registro "
            "das ações feitas no painel e acesso aos dados só por quem precisa deles para trabalhar.",
            "Nenhum sistema é 100% seguro. Se acontecer um incidente que possa causar risco ou dano relevante, "
            "avisaremos você e a ANPD, como manda a lei.",
        ]),
        ("Encarregado pelo tratamento de dados", [
            f"Encarregado (DPO): {d['encarregado']}. Telefone da loja: {d['telefone']}.",
        ]),
        ("Cookies e armazenamento local", [
            "O site não usa cookies de publicidade nem ferramentas de rastreamento de terceiros.",
            "Usamos apenas o armazenamento local do seu navegador, que é essencial para o funcionamento: guardar o "
            "carrinho, o acesso à \"Minha conta\" e preferências da página. Você pode apagar esses dados nas "
            "configurações do navegador a qualquer momento.",
        ]),
        ("Mudanças nesta política", [
            "Podemos atualizar esta política. A data da última atualização fica no topo da página; mudanças "
            "importantes serão avisadas no site.",
        ]),
    ])


def termos_uso(a):
    d = _dados(a)
    return _documento("Termos de Uso e Condições de Compra", [
        ("Identificação da loja", [
            f"{d['nome']} — {d['razao']}, {d['tipo_doc']} {d['doc']}, {d['endereco']}. "
            f"Atendimento: {d['email']} e {d['telefone']}.",
            "Ao comprar no site, você declara que leu e aceita estes termos e a Política de Privacidade.",
        ]),
        ("Preços e ofertas", [
            "Os preços estão em reais e podem mudar sem aviso, mas o valor que vale é o que aparece no resumo do "
            "pedido no momento da compra. Ofertas relâmpago valem até a data e hora mostradas ou enquanto durar o "
            "estoque.",
            f"Pagamento no Pix tem {config.DESCONTO_PIX_PCT}% de desconto sobre o valor dos produtos (já com cupom). "
            "Fotos são ilustrativas; as características que valem são as da descrição.",
            "Em caso de erro evidente de preço (por exemplo, um valor muito abaixo do normal por falha do sistema), "
            "avisaremos você e poderemos cancelar o pedido, devolvendo integralmente o que foi pago.",
        ]),
        ("Pagamento", [
            "Aceitamos Pix, cartão de crédito (em até "
            f"{config.PARCELAS_MAX}x sem juros, parcela mínima de R$ {config.PARCELA_MINIMA // 100}) e boleto.",
            f"Os produtos ficam reservados por {config.PRAZO_RESERVA_HORAS} horas aguardando o pagamento. Sem "
            "pagamento nesse prazo, o pedido é cancelado automaticamente e os produtos voltam à venda.",
        ]),
        ("Entrega e prazos", [
            "Enviamos a partir de Manaus para toda a Região Norte e para o restante do Brasil. O prazo informado no "
            "carrinho começa a contar depois da confirmação do pagamento e do tempo de separação.",
            "Para cidades atendidas por barco (como Parintins, Santarém e o interior do Amazonas e do Pará), o prazo "
            "depende do calendário das embarcações, da cheia e da vazante dos rios e de condições de navegação. "
            "Atrasos por esses motivos serão comunicados, e você pode desistir da compra com reembolso integral se "
            "o novo prazo não servir.",
            "Confira o endereço antes de finalizar. Se a entrega voltar por endereço errado ou ausência repetida, "
            "combinaremos um novo envio (o frete adicional pode ser cobrado).",
        ]),
        ("Direito de arrependimento (7 dias)", [
            "Você pode desistir da compra em até 7 dias corridos a partir do recebimento, sem precisar justificar "
            "(art. 49 do Código de Defesa do Consumidor).",
            "Fale com a gente pelo WhatsApp ou e-mail. Devolvemos todo o valor pago, inclusive o frete, pelo mesmo "
            "meio de pagamento ou por Pix, assim que recebermos o produto de volta. O custo da devolução é nosso.",
        ]),
        ("Trocas e garantia", [
            "Produtos com defeito podem ser reclamados em até 90 dias do recebimento (garantia legal, art. 26 do CDC). "
            "Consertamos, trocamos ou devolvemos o dinheiro em até 30 dias, como manda a lei.",
            f"Os detalhes estão na página de trocas: {d['site']}/trocas.",
        ]),
        ("Pré-venda", [
            "Produtos em pré-venda ainda estão sendo importados. A data prevista de chegada aparece na página do "
            "produto, e o prazo de entrega passa a contar a partir dela.",
            "Se o lote atrasar, avisaremos você. Você pode esperar ou cancelar com reembolso integral.",
        ]),
        ("Encomendas", [
            "No serviço \"Encomenda pra mim\" você nos diz o que procura e enviamos uma cotação com valor e prazo. "
            "A compra só acontece se você aceitar a cotação. Os produtos encomendados seguem as mesmas regras de "
            "arrependimento, troca e garantia.",
        ]),
        ("Cupons", [
            "Cada cupom tem regras próprias (valor mínimo, validade, limite de usos ou só na primeira compra), que "
            "aparecem ao aplicá-lo. Cupons não são trocados por dinheiro e não se somam, salvo quando indicado. "
            "Se o pedido for cancelado, o uso do cupom é devolvido.",
        ]),
        ("Revendedoras", [
            "Revendedoras cadastradas divulgam a loja com um link ou cupom próprio e recebem comissão pelas vendas "
            "pagas. Elas não são funcionárias nem representantes legais da loja; a venda, a entrega e o atendimento "
            "pós-venda são de responsabilidade da loja.",
        ]),
        ("Conta, avaliações e uso do site", [
            "A \"Minha conta\" é acessada por um link enviado ao e-mail usado na compra; não compartilhe esse link.",
            "Avaliações devem ser verdadeiras e respeitosas; podemos não publicar textos ofensivos ou que não tratem "
            "do produto. É proibido usar o site para fraudes, pedidos falsos ou tentativas de invasão.",
        ]),
        ("Foro", [
            "Estes termos seguem as leis brasileiras. Fica eleito o foro do domicílio do consumidor; se preferir, "
            f"você também pode buscar o foro de {d['cidade_foro']}. Antes, fale com a gente: a maioria dos "
            "problemas se resolve rápido pelo WhatsApp ou pelo consumidor.gov.br.",
        ]),
    ])
