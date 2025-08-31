# central_manager/database/seed_db.py

import logging
import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path
# para garantir que os imports de módulo funcionem
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from central_manager.database.connection import DatabaseManager
from central_manager.models.database_models import CameraCreate, LinhaCreate

# Configuração básica de logging para ver o que está acontecendo
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def seed_database():
    """Popula o banco de dados com dados de teste, se necessário."""
    db_manager = DatabaseManager()
    logger = logging.getLogger(__name__)

    logger.info("Iniciando o processo de seeding do banco de dados...")

    # Verificar se já existem câmeras para não duplicar
    existing_cameras = db_manager.get_all_cameras(ativo_only=False)
    if existing_cameras:
        logger.info(f"{len(existing_cameras)} câmera(s) já existem no banco. Nenhuma ação necessária.")
        return

    logger.info("Nenhuma câmera encontrada. Inserindo dados de teste...")

    # Como o schema.sql já cria um setor e uma linha com ID 1, podemos usá-los.
    linha_id_padrao = 1
    produto_id_padrao = 1

    # Câmera 1: USB
    camera_usb = CameraCreate(
        linha_id=linha_id_padrao,
        produto_id=produto_id_padrao,
        nome="Câmera da Bancada (USB)",
        device_index=0,  # Índice da câmera USB
        ip_address=None,
        porta=None,
        config_json={},  # Dicionário vazio em vez de string
        ativo=True
    )

    # Câmera 2: IP
    camera_ip = CameraCreate(
        linha_id=linha_id_padrao + 1, # Supondo que exista uma linha 2 ou que precise ser criada
        produto_id=produto_id_padrao,
        nome="Câmera do Pátio (IP)",
        device_index=None,
        ip_address="rtsp://user:pass@192.168.1.101:554/stream1", # URL de exemplo
        porta=554,
        config_json={},  # Dicionário vazio em vez de string
        ativo=True
    )

    try:
        # Criar uma nova linha para a câmera IP para evitar a violação da restrição UNIQUE
        # Verifica se a linha 2 já existe antes de criar
        if not db_manager.get_linha(2):
            db_manager.create_linha(LinhaCreate(setor_id=1, nome="Linha 02", descricao="Linha de produção secundária"))
            logger.info("Linha 02 criada para a câmera IP.")

        # Inserir as câmeras
        created_cam_usb = db_manager.create_camera(camera_usb)
        logger.info(f"Câmera USB criada com sucesso: ID {created_cam_usb.id}")

        created_cam_ip = db_manager.create_camera(camera_ip)
        logger.info(f"Câmera IP criada com sucesso: ID {created_cam_ip.id}")

        logger.info("Banco de dados populado com sucesso!")

    except Exception as e:
        logger.error(f"Ocorreu um erro ao popular o banco de dados: {e}", exc_info=True)

if __name__ == "__main__":
    seed_database()
