"""
Database Models - SIAC Industrial
Modelos Pydantic para validação e serialização de dados
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

# =====================================================
# ENUMS
# =====================================================

class StatusEnum(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERRO = "erro"
    MANUTENCAO = "manutencao"

class EstadoProducaoEnum(str, Enum):
    AGUARDANDO = "aguardando"
    PROCESSANDO = "processando"
    CAIXA_COMPLETA = "caixa_completa"
    ERRO = "erro"

class SeveridadeEnum(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class TipoDispositivoEnum(str, Enum):
    CAMERA = "camera"
    SENSOR = "sensor"
    ATUADOR = "atuador"

# =====================================================
# SETOR MODELS
# =====================================================

class SetorBase(BaseModel):
    nome: str = Field(..., max_length=100)
    descricao: Optional[str] = Field(None, max_length=500)
    ativo: bool = Field(default=True)

class SetorCreate(SetorBase):
    pass

class Setor(SetorBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# =====================================================
# LINHA MODELS
# =====================================================

class LinhaBase(BaseModel):
    setor_id: int
    nome: str = Field(..., max_length=100)
    descricao: Optional[str] = Field(None, max_length=500)
    ativo: bool = Field(default=True)

class LinhaCreate(LinhaBase):
    pass

class Linha(LinhaBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    setor: Optional[Setor] = None

    class Config:
        from_attributes = True

# =====================================================
# PRODUTO MODELS
# =====================================================

class ProdutoBase(BaseModel):
    nome: str = Field(..., max_length=100)
    descricao: Optional[str] = Field(None, max_length=500)
    config_json: Optional[Dict[str, Any]] = Field(default_factory=dict)
    ativo: bool = Field(default=True)

class ProdutoCreate(ProdutoBase):
    pass

class Produto(ProdutoBase):
    id: int
    itens_por_camada: Optional[int] = None
    max_camadas: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# =====================================================
# CAMERA MODELS
# =====================================================

class CameraBase(BaseModel):
    linha_id: int
    produto_id: int
    nome: str = Field(..., max_length=100)
    device_index: Optional[int] = None  # Para câmeras USB
    ip_address: Optional[str] = Field(None, max_length=1024)  # IP ou URL completa (RTSP/HTTP)
    porta: Optional[int] = None
    bancada: Optional[str] = Field(None, max_length=10)
    # Configurações de vídeo (opcionais, usam defaults do DB se não fornecidos)
    resolucao_width: Optional[int] = Field(default=1920)
    resolucao_height: Optional[int] = Field(default=1080)
    fps: Optional[int] = Field(default=30)
    usuario: Optional[str] = Field(None, max_length=50)
    senha: Optional[str] = Field(None, max_length=100)
    config_json: Optional[Dict[str, Any]] = Field(default_factory=dict)
    ativo: bool = Field(default=True)

class CameraCreate(CameraBase):
    pass

class Camera(CameraBase):
    id: int
    status: StatusEnum = Field(default=StatusEnum.OFFLINE)
    created_at: datetime
    updated_at: Optional[datetime] = None
    linha: Optional[Linha] = None
    produto: Optional[Produto] = None

    class Config:
        from_attributes = True

# =====================================================
# DISPOSITIVO ALERTA MODELS
# =====================================================

class DispositivoAlertaBase(BaseModel):
    linha_id: int
    nome: str = Field(..., max_length=100)
    tipo: TipoDispositivoEnum
    endereco: Optional[str] = Field(None, max_length=200)
    config_json: Optional[Dict[str, Any]] = Field(default_factory=dict)
    ativo: bool = Field(default=True)

class DispositivoAlertaCreate(DispositivoAlertaBase):
    pass

class DispositivoAlerta(DispositivoAlertaBase):
    id: int
    status: StatusEnum = Field(default=StatusEnum.OFFLINE)
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# =====================================================
# PRODUÇÃO DADOS MODELS
# =====================================================

class ProducaoDadosBase(BaseModel):
    camera_id: int
    estado: EstadoProducaoEnum
    contagem_atual: int = Field(default=0)
    camada_atual: int = Field(default=1)
    caixas_completas: int = Field(default=0)
    roi_detectada: bool = Field(default=False)
    itens_detectados: int = Field(default=0)
    confianca_media: float = Field(default=0.0)
    tempo_processamento: float = Field(default=0.0)
    alertas_json: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    eventos_json: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    cpu_uso: Optional[float] = Field(default=0.0)
    memoria_uso: Optional[float] = Field(default=0.0)
    dados_json: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ProducaoDadosCreate(ProducaoDadosBase):
    pass

class ProducaoDados(ProducaoDadosBase):
    id: int
    timestamp: datetime
    camera: Optional[Camera] = None

    class Config:
        from_attributes = True

# =====================================================
# ALERTA HISTÓRICO MODELS
# =====================================================

class AlertaHistoricoBase(BaseModel):
    camera_id: Optional[int] = None
    dispositivo_id: Optional[int] = None
    severidade: SeveridadeEnum
    titulo: str = Field(..., max_length=200)
    mensagem: str = Field(..., max_length=1000)
    dados_json: Optional[Dict[str, Any]] = Field(default_factory=dict)
    resolvido: bool = Field(default=False)

class AlertaHistoricoCreate(AlertaHistoricoBase):
    pass

class AlertaHistorico(AlertaHistoricoBase):
    id: int
    timestamp: datetime
    resolvido_em: Optional[datetime] = None
    camera: Optional[Camera] = None
    dispositivo: Optional[DispositivoAlerta] = None

    class Config:
        from_attributes = True
