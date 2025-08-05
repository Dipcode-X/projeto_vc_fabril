"""
Database Connection Manager - SIAC Industrial
Gerencia conexões SQLite e operações CRUD
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from datetime import datetime

from ..models.database_models import (
    # Create Models
    SetorCreate, LinhaCreate, ProdutoCreate, CameraCreate, 
    DispositivoAlertaCreate, ProducaoDadosCreate, AlertaHistoricoCreate,
    
    # Response Models
    Setor, Linha, Produto, Camera, DispositivoAlerta,
    ProducaoDados, AlertaHistorico,
    
    # Enums
    StatusEnum, EstadoProducaoEnum, SeveridadeEnum, TipoDispositivoEnum
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gerenciador de conexões e operações do banco de dados"""
    
    def __init__(self, db_path: str = None):
        """
        Inicializa o gerenciador de banco
        
        Args:
            db_path: Caminho para o arquivo SQLite
        """
        if db_path is None:
            db_path = Path(__file__).parent / "siac_industrial.db"
        
        self.db_path = str(db_path)
        self.logger = logging.getLogger(f"{__name__}.DatabaseManager")
        
        # Inicializar banco se não existir
        self._initialize_database()
    
    def _initialize_database(self):
        """Inicializa o banco de dados com o schema"""
        try:
            schema_path = Path(__file__).parent / "schema.sql"
            
            if not Path(self.db_path).exists() and schema_path.exists():
                self.logger.info(f"Criando banco de dados: {self.db_path}")
                
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                with self.get_connection() as conn:
                    conn.executescript(schema_sql)
                    conn.commit()
                
                self.logger.info("Banco de dados inicializado com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar banco: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexões SQLite"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Erro na conexão com banco: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    # =====================================================
    # SETORES CRUD
    # =====================================================
    
    def create_setor(self, setor: SetorCreate) -> Setor:
        """Cria um novo setor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO setores (nome, descricao, ativo)
                VALUES (?, ?, ?)
            """, (setor.nome, setor.descricao, setor.ativo))
            
            setor_id = cursor.lastrowid
            conn.commit()
            
            return self.get_setor(setor_id)
    
    def get_setor(self, setor_id: int) -> Optional[Setor]:
        """Busca setor por ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM setores WHERE id = ?
            """, (setor_id,))
            
            row = cursor.fetchone()
            if row:
                return Setor(**dict(row))
            return None
    
    def get_setores(self, ativo_only: bool = True) -> List[Setor]:
        """Lista todos os setores"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM setores"
            if ativo_only:
                query += " WHERE ativo = 1"
            query += " ORDER BY nome"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            return [Setor(**dict(row)) for row in rows]
    
    # =====================================================
    # LINHAS CRUD
    # =====================================================
    
    def create_linha(self, linha: LinhaCreate) -> Linha:
        """Cria uma nova linha"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO linhas (setor_id, nome, descricao, ativo)
                VALUES (?, ?, ?, ?)
            """, (linha.setor_id, linha.nome, linha.descricao, linha.ativo))
            
            linha_id = cursor.lastrowid
            conn.commit()
            
            return self.get_linha(linha_id)
    
    def get_linha(self, linha_id: int) -> Optional[Linha]:
        """Busca linha por ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT l.*, s.nome as setor_nome
                FROM linhas l
                LEFT JOIN setores s ON l.setor_id = s.id
                WHERE l.id = ?
            """, (linha_id,))
            
            row = cursor.fetchone()
            if row:
                linha_data = dict(row)
                # Criar objeto Setor se existir
                if linha_data.get('setor_nome'):
                    setor = self.get_setor(linha_data['setor_id'])
                    linha_data['setor'] = setor
                
                return Linha(**linha_data)
            return None
    
    def get_linhas_by_setor(self, setor_id: int) -> List[Linha]:
        """Lista linhas de um setor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM linhas 
                WHERE setor_id = ? AND ativo = 1
                ORDER BY nome
            """, (setor_id,))
            
            rows = cursor.fetchall()
            return [Linha(**dict(row)) for row in rows]
    
    # =====================================================
    # PRODUTOS CRUD
    # =====================================================
    
    def create_produto(self, produto: ProdutoCreate) -> Produto:
        """Cria um novo produto"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO produtos (
                    nome, descricao, itens_por_camada, max_camadas,
                    confidence_threshold, divisor_confidence, divisor_low_confidence,
                    buffer_size_roi, buffer_size_divisor, frames_estabilizacao,
                    distancia_minima_item, percentual_itens_novos_minimo,
                    carencia_caixa_ausente, carencia_divisor_ausente, timeout_alerta_minimo,
                    tolerancia_oclusao_camada2, limiar_salto_contagem, tempo_validacao_salto,
                    config_json, ativo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                produto.nome, produto.descricao, produto.itens_por_camada, produto.max_camadas,
                produto.confidence_threshold, produto.divisor_confidence, produto.divisor_low_confidence,
                produto.buffer_size_roi, produto.buffer_size_divisor, produto.frames_estabilizacao,
                produto.distancia_minima_item, produto.percentual_itens_novos_minimo,
                produto.carencia_caixa_ausente, produto.carencia_divisor_ausente, produto.timeout_alerta_minimo,
                produto.tolerancia_oclusao_camada2, produto.limiar_salto_contagem, produto.tempo_validacao_salto,
                str(produto.config_json), produto.ativo
            ))
            
            produto_id = cursor.lastrowid
            conn.commit()
            
            return self.get_produto(produto_id)
    
    def get_produto(self, produto_id: int) -> Optional[Produto]:
        """Busca produto por ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM produtos WHERE id = ?
            """, (produto_id,))
            
            row = cursor.fetchone()
            if row:
                produto_data = dict(row)
                # Parse JSON config
                import json
                try:
                    produto_data['config_json'] = json.loads(produto_data['config_json'])
                except:
                    produto_data['config_json'] = {}
                
                return Produto(**produto_data)
            return None
    
    def get_produtos(self, ativo_only: bool = True) -> List[Produto]:
        """Lista todos os produtos"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM produtos"
            if ativo_only:
                query += " WHERE ativo = 1"
            query += " ORDER BY nome"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            produtos = []
            for row in rows:
                produto_data = dict(row)
                # Parse JSON config
                import json
                try:
                    produto_data['config_json'] = json.loads(produto_data['config_json'])
                except:
                    produto_data['config_json'] = {}
                
                produtos.append(Produto(**produto_data))
            
            return produtos
    
    # =====================================================
    # CAMERAS CRUD
    # =====================================================
    
    def create_camera(self, camera: CameraCreate) -> Camera:
        """Cria uma nova câmera"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO cameras (
                    linha_id, produto_id, nome, device_index, ip_address, porta,
                    resolucao_width, resolucao_height, fps, config_json, ativo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                camera.linha_id, camera.produto_id, camera.nome, 
                camera.device_index, camera.ip_address, camera.porta,
                camera.resolucao_width, camera.resolucao_height, camera.fps,
                str(camera.config_json), camera.ativo
            ))
            
            camera_id = cursor.lastrowid
            conn.commit()
            
            return self.get_camera(camera_id)
    
    def get_camera(self, camera_id: int) -> Optional[Camera]:
        """Busca câmera por ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM cameras WHERE id = ?
            """, (camera_id,))
            
            row = cursor.fetchone()
            if row:
                camera_data = dict(row)
                # Parse JSON config
                import json
                try:
                    camera_data['config_json'] = json.loads(camera_data['config_json'])
                except:
                    camera_data['config_json'] = {}
                
                return Camera(**camera_data)
            return None
    
    def get_cameras_by_linha(self, linha_id: int) -> List[Camera]:
        """Lista câmeras de uma linha"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM cameras 
                WHERE linha_id = ? AND ativo = 1
                ORDER BY nome
            """, (linha_id,))
            
            rows = cursor.fetchall()
            cameras = []
            
            for row in rows:
                camera_data = dict(row)
                # Parse JSON config
                import json
                try:
                    camera_data['config_json'] = json.loads(camera_data['config_json'])
                except:
                    camera_data['config_json'] = {}
                
                cameras.append(Camera(**camera_data))
            
            return cameras
    
    def update_camera_status(self, camera_id: int, status: StatusEnum):
        """Atualiza status de uma câmera"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE cameras 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status.value, camera_id))
            
            conn.commit()
    
    # =====================================================
    # PRODUCAO DADOS CRUD
    # =====================================================
    
    def create_producao_dados(self, dados: ProducaoDadosCreate) -> ProducaoDados:
        """Cria registro de dados de produção"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO producao_dados (
                    camera_id, estado, contagem_atual, camada_atual, caixas_completas,
                    roi_detectada, itens_detectados, divisores_detectados,
                    alertas_json, eventos_json, fps_atual, tempo_processamento, 
                    memoria_uso, dados_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dados.camera_id, dados.estado.value, dados.contagem_atual, dados.camada_atual,
                dados.caixas_completas, dados.roi_detectada, dados.itens_detectados,
                dados.divisores_detectados, str(dados.alertas_json), str(dados.eventos_json),
                dados.fps_atual, dados.tempo_processamento, dados.memoria_uso, str(dados.dados_json)
            ))
            
            dados_id = cursor.lastrowid
            conn.commit()
            
            return self.get_producao_dados(dados_id)
    
    def get_producao_dados(self, dados_id: int) -> Optional[ProducaoDados]:
        """Busca dados de produção por ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM producao_dados WHERE id = ?
            """, (dados_id,))
            
            row = cursor.fetchone()
            if row:
                dados_data = dict(row)
                # Parse JSON fields
                import json
                for field in ['alertas_json', 'eventos_json', 'dados_json']:
                    try:
                        dados_data[field] = json.loads(dados_data[field])
                    except:
                        dados_data[field] = [] if field.endswith('_json') else {}
                
                return ProducaoDados(**dados_data)
            return None
    
    def get_latest_producao_by_camera(self, camera_id: int) -> Optional[ProducaoDados]:
        """Busca dados mais recentes de uma câmera"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM producao_dados 
                WHERE camera_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (camera_id,))
            
            row = cursor.fetchone()
            if row:
                dados_data = dict(row)
                # Parse JSON fields
                import json
                for field in ['alertas_json', 'eventos_json', 'dados_json']:
                    try:
                        dados_data[field] = json.loads(dados_data[field])
                    except:
                        dados_data[field] = [] if field.endswith('_json') else {}
                
                return ProducaoDados(**dados_data)
            return None
    
    # =====================================================
    # ALERTAS CRUD
    # =====================================================
    
    def create_alerta(self, alerta: AlertaHistoricoCreate) -> AlertaHistorico:
        """Cria um novo alerta"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO alertas_historico (
                    camera_id, tipo, severidade, mensagem, estado_anterior,
                    estado_atual, contagem_atual, camada_atual, acao_tomada,
                    dispositivo_alerta_id, dados_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alerta.camera_id, alerta.tipo, alerta.severidade.value, alerta.mensagem,
                alerta.estado_anterior, alerta.estado_atual, alerta.contagem_atual,
                alerta.camada_atual, alerta.acao_tomada, alerta.dispositivo_alerta_id,
                str(alerta.dados_json)
            ))
            
            alerta_id = cursor.lastrowid
            conn.commit()
            
            return self.get_alerta(alerta_id)
    
    def get_alerta(self, alerta_id: int) -> Optional[AlertaHistorico]:
        """Busca alerta por ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM alertas_historico WHERE id = ?
            """, (alerta_id,))
            
            row = cursor.fetchone()
            if row:
                alerta_data = dict(row)
                # Parse JSON
                import json
                try:
                    alerta_data['dados_json'] = json.loads(alerta_data['dados_json'])
                except:
                    alerta_data['dados_json'] = {}
                
                return AlertaHistorico(**alerta_data)
            return None
    
    def get_alertas_recentes(self, limit: int = 50) -> List[AlertaHistorico]:
        """Lista alertas mais recentes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM alertas_historico 
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            alertas = []
            
            for row in rows:
                alerta_data = dict(row)
                # Parse JSON
                import json
                try:
                    alerta_data['dados_json'] = json.loads(alerta_data['dados_json'])
                except:
                    alerta_data['dados_json'] = {}
                
                alertas.append(AlertaHistorico(**alerta_data))
            
            return alertas
