"""
Endpoints para gerenciamento de produtos
"""

from fastapi import APIRouter

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/")
async def list_products():
    """Lista todos os produtos disponíveis"""
    # TODO: Implementar carregamento do banco SQL
    pass

@router.get("/{product_id}")
async def get_product_config(product_id: str):
    """Retorna configuração específica de um produto"""
    # TODO: Implementar
    pass

@router.get("/sectors/{sector_id}/products")
async def list_products_by_sector(sector_id: str):
    """Lista produtos disponíveis para um setor específico"""
    # TODO: Implementar
    pass

@router.post("/")
async def create_product(product_data: dict):
    """Cria novo produto no sistema"""
    # TODO: Implementar
    pass

@router.put("/{product_id}")
async def update_product(product_id: str, product_data: dict):
    """Atualiza configuração de um produto"""
    # TODO: Implementar
    pass
