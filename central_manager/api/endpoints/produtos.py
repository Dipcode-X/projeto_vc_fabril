from fastapi import APIRouter

router = APIRouter(
    prefix="/produtos",
    tags=["Produtos"],
)

# Dados de exemplo (mock)
# No futuro, isso virá de um banco de dados
DADOS_PRODUTOS = [
    {
        "id": 1,
        "nome": "Caixa Padrão (3x4)",
        "descricao": "Caixa de papelão para 12 itens.",
        "itens_por_camada": 12,
        "camadas_por_caixa": 1,
        "imagem_url": "/assets/images/product_default.png"
    },
    {
        "id": 2,
        "nome": "Caixa Grande (5x5)",
        "descricao": "Caixa de papelão para 25 itens.",
        "itens_por_camada": 25,
        "camadas_por_caixa": 1,
        "imagem_url": "/assets/images/product_default.png"
    }
]

@router.get("", summary="Lista todos os produtos configurados")
async def get_produtos():
    """
    Retorna uma lista de todos os produtos que o sistema pode monitorar.
    """
    return DADOS_PRODUTOS
