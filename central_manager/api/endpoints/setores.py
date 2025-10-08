from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from central_manager.database.connection import DatabaseManager

router = APIRouter(
    prefix="/setores",
    tags=["Setores"],
)

@router.get("", summary="Lista todos os setores de produção")
async def get_setores():
    """
    Retorna uma lista de todos os setores monitorados com base no banco de dados.
    Substitui os dados mockados para alinhar com câmeras e linhas reais.
    """
    db = DatabaseManager()
    setores_db = db.get_setores(ativo_only=True)

    # Serializa apenas os campos necessários para o frontend
    return [
        {
            "id": s.id,
            "nome": s.nome,
            "cameras_ativas": 0,      # Opcional: pode ser atualizado pelo WS/dash
            "total_cameras": 0        # Opcional: pode ser atualizado pelo WS/dash
        }
        for s in setores_db
    ]
