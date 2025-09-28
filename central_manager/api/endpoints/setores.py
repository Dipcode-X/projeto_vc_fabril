from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from central_manager.database.connection import DatabaseManager
 
router = APIRouter(
     prefix="/setores",
     tags=["Setores"],
 )
 
db = DatabaseManager()
 
@router.get("", summary="Lista todos os setores de produção")
async def get_setores():
    """Lista setores com totais de câmeras e câmeras online (SQLite)."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
              s.id,
              s.nome AS name,
              COALESCE(SUM(CASE WHEN c.id IS NOT NULL THEN 1 ELSE 0 END), 0) AS total_cameras,
              COALESCE(SUM(CASE WHEN c.status = 'online' THEN 1 ELSE 0 END), 0) AS active_cameras
            FROM setores s
            LEFT JOIN linhas  l ON l.setor_id = s.id AND l.ativo = 1
            LEFT JOIN cameras c ON c.linha_id = l.id AND c.ativo = 1
            WHERE s.ativo = 1
            GROUP BY s.id, s.nome
            ORDER BY s.nome;
            """
        )
        rows = cursor.fetchall()
        setores = [
            {
                "id": r[0],
                "name": r[1],
                "total_cameras": r[2],
                "active_cameras": r[3],
            }
            for r in rows
        ]
        return setores
