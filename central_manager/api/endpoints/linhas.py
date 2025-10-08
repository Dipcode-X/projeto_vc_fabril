"""
Endpoints para gerenciamento de linhas de produção
"""

from fastapi import APIRouter, HTTPException
from central_manager.database.connection import DatabaseManager
from datetime import datetime
import logging

router = APIRouter(prefix="/linhas", tags=["linhas"])

@router.get("", summary="Lista todas as linhas de produção")
async def get_linhas():
    """
    Retorna uma lista de todas as linhas de produção cadastradas no sistema.
    """
    try:
        db_manager = DatabaseManager()
        
        # Busca todas as linhas com info do setor de forma eficiente
        linhas_data = db_manager.get_all_linhas_with_setor_info(ativo_only=True)
        
        linhas = []
        for linha in linhas_data:
            created_at_iso = None
            if linha.get('created_at') and isinstance(linha['created_at'], str):
                created_at_iso = datetime.strptime(linha['created_at'], '%Y-%m-%d %H:%M:%S').isoformat()
            
            updated_at_iso = None
            if linha.get('updated_at') and isinstance(linha['updated_at'], str):
                updated_at_iso = datetime.strptime(linha['updated_at'], '%Y-%m-%d %H:%M:%S').isoformat()

            linhas.append({
                "id": linha['id'],
                "nome": linha['nome'],
                "setor_id": linha['setor_id'],
                "setor_nome": linha['setor_nome'],
                "ativo": linha['ativo'],
                "created_at": created_at_iso,
                "updated_at": updated_at_iso
            })
        
        return linhas
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar linhas: {str(e)}")

@router.get("/{linha_id}", summary="Obtém detalhes de uma linha específica")
async def get_linha(linha_id: int):
    """
    Retorna os detalhes de uma linha de produção específica.
    """
    try:
        db_manager = DatabaseManager()
        linha = db_manager.get_linha(linha_id)
        
        if not linha:
            raise HTTPException(status_code=404, detail=f"Linha com ID {linha_id} não encontrada")
        
        # Buscar setor da linha
        setor = db_manager.get_setor(linha.setor_id)
        
        return {
            "id": linha.id,
            "nome": linha.nome,
            "setor_id": linha.setor_id,
            "setor_nome": setor.nome if setor else "Setor Desconhecido",
            "ativo": linha.ativo,
            "created_at": linha.created_at.isoformat() if linha.created_at else None,
            "updated_at": linha.updated_at.isoformat() if linha.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar linha: {str(e)}")
