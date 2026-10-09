"""Regras de negócio da loja, reunidas num lugar só.

O código fica nos módulos de cada assunto — validacao, catalogo, carrinho, reservas, pedidos, admin_produtos,
promocoes, prova_social, avaliacoes e cupons —; este módulo apenas os reexporta, para quem usa `regras.X`
continuar funcionando.
"""

from .admin_produtos import (
    INTEIRO_MAX, adicionar_foto, atualizar_produto, criar_produto, definir_capa, remover_foto, salvar_variacoes,
)
from .avaliacoes import (
    STATUS_AVALIACAO, criar_avaliacao, listar_avaliacoes, listar_avaliacoes_admin, moderar_avaliacao, nota_media,
)
from .carrinho import FORMAS_PAGAMENTO, chave_item, cotar_carrinho, parcelas_maximas
from .catalogo import (
    ORDENACOES, cor_e_icone, gerar_slug, listar_categorias, listar_produtos, obter_categoria, obter_produto,
    url_imagem, url_miniatura,
)
from .cupons import atualizar as atualizar_cupom
from .cupons import criar as criar_cupom
from .cupons import cupom_destaque, formatar_reais
from .cupons import listar as listar_cupons
from .pedidos import criar_pedido, listar_pedidos, lucro_do_pedido, obter_pedido_publico, resumo_vendas
from .promocoes import preco_ancora, preco_com_desconto
from .prova_social import selos, vendas_recentes
from .reservas import STATUS_PEDIDO, TRANSICOES, atualizar_status, expirar_pendentes
from .validacao import UFS, ErroValidacao, NaoEncontrado, cep_digitos, cpf_valido, email_valido, so_digitos

__all__ = [
    "ErroValidacao", "NaoEncontrado", "UFS", "so_digitos", "cpf_valido", "email_valido", "cep_digitos",
    "ORDENACOES", "url_imagem", "url_miniatura", "gerar_slug", "listar_categorias", "obter_categoria",
    "listar_produtos", "obter_produto", "cor_e_icone",
    "FORMAS_PAGAMENTO", "chave_item", "parcelas_maximas", "cotar_carrinho",
    "STATUS_PEDIDO", "TRANSICOES", "atualizar_status", "expirar_pendentes",
    "criar_pedido", "obter_pedido_publico", "listar_pedidos", "lucro_do_pedido", "resumo_vendas",
    "INTEIRO_MAX", "criar_produto", "atualizar_produto", "salvar_variacoes",
    "adicionar_foto", "remover_foto", "definir_capa",
    "preco_com_desconto", "preco_ancora",
    "selos", "vendas_recentes",
    "STATUS_AVALIACAO", "nota_media", "criar_avaliacao", "listar_avaliacoes", "listar_avaliacoes_admin",
    "moderar_avaliacao",
    "formatar_reais", "cupom_destaque", "listar_cupons", "criar_cupom", "atualizar_cupom",
]
