"""
Configuração centralizada de logging para o sistema SIAC
"""

import logging
import sys
from typing import Optional

def get_siac_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Cria e configura um logger para o sistema SIAC.
    
    Args:
        name: Nome do logger (ex: "STATE_MANAGER", "VISUAL_TESTER")
        level: Nível de logging (default: INFO)
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(f"SIAC.{name}")
    
    # Evitar duplicação de handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Criar handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Formato das mensagens
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Adicionar handler ao logger
    logger.addHandler(console_handler)
    
    # Evitar propagação para o logger raiz
    logger.propagate = False
    
    return logger
