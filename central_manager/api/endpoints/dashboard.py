"""
Endpoints para dashboard e monitoramento
"""

from fastapi import APIRouter, Request
from central_manager.database.connection import DatabaseManager

router = APIRouter(tags=["Dashboard"])
db = DatabaseManager()

@router.get("/dashboard")
async def get_dashboard_overview(request: Request):
    """Retorna visão geral do sistema a partir do banco (SQLite)."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM setores WHERE ativo = 1) AS total_setores,
              (SELECT COUNT(DISTINCT s.id)
                 FROM setores s
                 JOIN linhas  l ON l.setor_id = s.id AND l.ativo = 1
                 JOIN cameras c ON c.linha_id = l.id AND c.ativo = 1
                 WHERE s.ativo = 1 AND c.status = 'online'
              ) AS setores_ativos,
              (SELECT COUNT(*) FROM cameras WHERE ativo = 1) AS total_cameras,
              (SELECT COUNT(*) FROM cameras WHERE ativo = 1 AND status = 'online') AS cameras_ativas;
            """
        )
        row = cursor.fetchone()
        return {
            "total_setores": row[0] if row else 0,
            "setores_ativos": row[1] if row else 0,
            "total_cameras": row[2] if row else 0,
            "cameras_ativas": row[3] if row else 0,
        }
