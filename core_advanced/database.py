# core_advanced/database.py

from .utils.simple_logger import SimpleLogger

# Mock de uma tabela de câmeras no banco de dados.
# No futuro, isso será substituído por chamadas a um banco de dados real (ex: SQLite, PostgreSQL).
_MOCK_IP_CAMERAS = [
    {
        "id": 101,
        "description": "Câmera IP do Pátio",
        "url": "rtsp://user:pass@192.168.1.101:554/stream1",
        "type": "IP"
    },
    {
        "id": 102,
        "description": "Câmera IP do Estoque",
        "url": "rtsp://user:pass@192.168.1.102:554/stream1",
        "type": "IP"
    }
]

logger = SimpleLogger("Database").get_logger()


def get_ip_cameras_from_db():
    """Simula a busca de câmeras IP cadastradas no banco de dados."""
    logger.info(f"Buscando câmeras IP no banco de dados (mock)... Encontradas: {len(_MOCK_IP_CAMERAS)}")
    # Em uma implementação real, aqui ocorreria a conexão e a query ao banco.
    return _MOCK_IP_CAMERAS

def get_all_cameras_from_db():
    """
    Retorna todas as câmeras configuradas no banco de dados.
    Por enquanto, apenas retorna as câmeras IP mockadas.
    """
    return get_ip_cameras_from_db()
