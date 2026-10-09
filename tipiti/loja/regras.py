"""Regras de negócio da loja, reunidas num lugar só.

O código fica nos módulos de cada assunto — validacao, catalogo, carrinho, reservas, pedidos e
admin_produtos —; este módulo apenas os reexporta, para quem usa `regras.X` continuar funcionando.
"""

from .admin_produtos import (
    INTEIRO_MAX, adicionar_foto, atualizar_produto, criar_produto, definir_capa, remover_foto, salvar_variacoes,
)
from .carrinho import FORMAS_PAGAMENTO, chave_item, cotar_carrinho, parcelas_maximas
from .catalogo import (
    ORDENACOES, cor_e_icone, gerar_slug, listar_categorias, listar_produtos, obter_categoria, obter_produto,
    url_imagem, url_miniatura,
)
from .pedidos import criar_pedido, listar_pedidos, lucro_do_pedido, obter_pedido_publico, resumo_vendas
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
]
