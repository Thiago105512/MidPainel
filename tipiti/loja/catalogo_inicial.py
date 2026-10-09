"""Catálogo de partida da Tipiti: produtos diversos importados.

Preços em centavos. Itens e valores são de demonstração e devem ser substituídos pelo catálogo real.
"""

CATEGORIAS = [
    {"slug": "eletronicos", "nome": "Eletrônicos",
     "descricao": "Fones, caixas de som, relógios inteligentes e gadgets para o dia a dia.",
     "icone": "🎧", "cor": "#1f5c45"},
    {"slug": "celular-e-acessorios", "nome": "Celular & Acessórios",
     "descricao": "Carregadores, cabos, capinhas, suportes e power banks.",
     "icone": "📱", "cor": "#20606e"},
    {"slug": "casa-e-cozinha", "nome": "Casa & Cozinha",
     "descricao": "Utilidades, organização, iluminação e eletroportáteis.",
     "icone": "🍳", "cor": "#8a6a2f"},
    {"slug": "beleza-e-cuidados", "nome": "Beleza & Cuidados",
     "descricao": "Secadores, escovas, kits de maquiagem e cuidados pessoais.",
     "icone": "💄", "cor": "#7a3e5c"},
    {"slug": "moda-e-acessorios", "nome": "Moda & Acessórios",
     "descricao": "Bolsas, mochilas, óculos, relógios e bijuterias.",
     "icone": "👜", "cor": "#a0522d"},
    {"slug": "brinquedos-e-infantil", "nome": "Brinquedos & Infantil",
     "descricao": "Brinquedos educativos, pelúcias e diversão para todas as idades.",
     "icone": "🧸", "cor": "#3f7a4e"},
    {"slug": "ferramentas-e-automotivo", "nome": "Ferramentas & Automotivo",
     "descricao": "Kits de ferramentas, acessórios para carro e moto.",
     "icone": "🔧", "cor": "#4a5560"},
]


def _p(slug, nome, categoria, preco, estoque, icone, descricao, preco_de=None, destaque=False):
    return {"slug": slug, "nome": nome, "categoria": categoria, "preco": preco, "preco_de": preco_de,
            "estoque": estoque, "icone": icone, "descricao": descricao, "destaque": destaque}


PRODUTOS = [
    # Eletrônicos
    _p("fone-bluetooth-tws", "Fone Bluetooth TWS com estojo", "eletronicos", 8990, 40, "🎧",
       "Fone sem fio com cancelamento de ruído passivo, estojo carregador e até 20 h de bateria.", 12990, True),
    _p("caixa-de-som-bluetooth-ipx7", "Caixa de som Bluetooth à prova d'água", "eletronicos", 14990, 20, "🔊",
       "Certificação IPX7, 12 h de bateria e graves reforçados. Conecta duas caixas em estéreo.", 17990, True),
    _p("smartwatch-tela-amoled", "Smartwatch com tela AMOLED", "eletronicos", 19990, 15, "⌚",
       "Monitor de batimentos, sono e passos, notificações do celular e bateria de até 7 dias."),
    _p("mini-projetor-portatil", "Mini projetor portátil Full HD", "eletronicos", 39990, 6, "📽️",
       "Projeta até 100 polegadas, entrada HDMI e USB, alto-falante embutido.", 45990),

    # Celular & Acessórios
    _p("power-bank-20000mah", "Carregador portátil 20.000 mAh", "celular-e-acessorios", 11990, 35, "🔋",
       "Duas saídas USB e uma USB-C com carga rápida. Indicador digital de bateria.", None, True),
    _p("carregador-turbo-usb-c-30w", "Carregador turbo USB-C 30 W", "celular-e-acessorios", 5990, 60, "🔌",
       "Carga rápida PD para celulares e tablets, bivolt."),
    _p("cabo-usb-c-reforcado-2m", "Cabo USB-C reforçado 2 m", "celular-e-acessorios", 2490, 120, "🪢",
       "Revestimento em nylon trançado, suporta até 60 W."),
    _p("suporte-veicular-magnetico", "Suporte veicular magnético", "celular-e-acessorios", 3990, 45, "🧲",
       "Fixa na saída de ar, rotação 360° e ímã forte para celulares de todos os tamanhos."),

    # Casa & Cozinha
    _p("fritadeira-air-fryer-4l", "Fritadeira air fryer 4 L", "casa-e-cozinha", 29990, 10, "🍟",
       "Painel digital, 8 programas pré-definidos e cesto antiaderente. 127 V.", 34990, True),
    _p("ventilador-de-mesa-silencioso", "Ventilador de mesa silencioso 30 cm", "casa-e-cozinha", 16990, 18, "🌀",
       "Três velocidades, oscilação automática e motor de baixo ruído."),
    _p("fita-led-rgb-5m", "Fita LED RGB 5 m com controle", "casa-e-cozinha", 4990, 50, "💡",
       "16 cores, efeitos dinâmicos e controle pelo aplicativo. Adesivo 3M."),
    _p("organizador-de-gaveta-kit-6", "Organizadores de gaveta — kit com 6", "casa-e-cozinha", 3490, 70, "🗂️",
       "Caixas modulares em plástico resistente para cozinha, banheiro e escritório."),

    # Beleza & Cuidados
    _p("secador-de-cabelo-ionico", "Secador de cabelo iônico 2000 W", "beleza-e-cuidados", 13990, 16, "💨",
       "Tecnologia iônica contra o frizz, 3 temperaturas e jato frio."),
    _p("escova-secadora-rotativa", "Escova secadora rotativa", "beleza-e-cuidados", 15990, 12, "🪮",
       "Seca, alisa e modela em uma só etapa. Cerdas mistas.", 19990, True),
    _p("kit-pinceis-maquiagem-12", "Kit 12 pincéis de maquiagem", "beleza-e-cuidados", 4490, 40, "🖌️",
       "Cerdas sintéticas macias com estojo de viagem."),
    _p("massageador-eletrico-pescoco", "Massageador elétrico para pescoço", "beleza-e-cuidados", 9990, 14, "💆",
       "Seis modos de massagem, aquecimento suave e recarga USB."),

    # Moda & Acessórios
    _p("mochila-notebook-antifurto", "Mochila antifurto para notebook", "moda-e-acessorios", 12990, 22, "🎒",
       "Zíper oculto, porta USB externa e compartimento acolchoado para notebook de até 15,6\".", None, True),
    _p("oculos-de-sol-polarizado", "Óculos de sol polarizado UV400", "moda-e-acessorios", 5990, 40, "🕶️",
       "Lentes polarizadas com proteção UV400 e armação leve."),
    _p("relogio-analogico-minimalista", "Relógio analógico minimalista", "moda-e-acessorios", 8990, 25, "⌚",
       "Caixa em aço inox, pulseira de couro sintético e resistência a respingos."),
    _p("bolsa-transversal-feminina", "Bolsa transversal feminina", "moda-e-acessorios", 7990, 30, "👜",
       "Compacta, alça regulável e três compartimentos."),

    # Brinquedos & Infantil
    _p("blocos-de-montar-500-pecas", "Blocos de montar — 500 peças", "brinquedos-e-infantil", 8990, 25, "🧱",
       "Peças compatíveis com as principais marcas, caixa organizadora inclusa. Indicado a partir de 6 anos."),
    _p("carrinho-controle-remoto-4x4", "Carrinho de controle remoto 4x4", "brinquedos-e-infantil", 15990, 12, "🚙",
       "Tração nas quatro rodas, bateria recarregável e controle de 2,4 GHz.", 18990, True),
    _p("pelucia-gigante-urso-80cm", "Urso de pelúcia gigante 80 cm", "brinquedos-e-infantil", 11990, 10, "🧸",
       "Pelúcia antialérgica, macia e lavável."),
    _p("lousa-magica-lcd-10", "Lousa mágica LCD 10\"", "brinquedos-e-infantil", 3990, 50, "✏️",
       "Escreva e apague com um botão. Sem tinta e sem bagunça."),

    # Ferramentas & Automotivo
    _p("parafusadeira-sem-fio-12v", "Parafusadeira sem fio 12 V", "ferramentas-e-automotivo", 18990, 14, "🪛",
       "Duas baterias, maleta e kit com 24 bits.", 21990, True),
    _p("kit-ferramentas-46-pecas", "Kit de ferramentas — 46 peças", "ferramentas-e-automotivo", 8990, 20, "🧰",
       "Catraca, soquetes e bits em maleta compacta."),
    _p("compressor-de-ar-portatil", "Compressor de ar portátil 12 V", "ferramentas-e-automotivo", 13990, 15, "🛞",
       "Calibra pneus de carro, moto e bicicleta pelo acendedor do veículo. Visor digital."),
    _p("camera-veicular-dashcam", "Câmera veicular dashcam Full HD", "ferramentas-e-automotivo", 16990, 10, "📹",
       "Grava em loop, visão noturna e sensor de impacto."),
]
