class SimpleLogger:
    """Logger simples para o teste - COM CONTROLE DE SPAM RIGOROSO"""
    def __init__(self, name):
        self.name = name
        self.last_messages = {}  # Armazena últimas mensagens por tipo
        self.message_counts = {}  # Conta repetições
        self.last_log_time = {}  # Timestamp da última mensagem
    
    def _should_log(self, msg, msg_type, min_interval=1.0):
        """Controla se deve fazer log baseado em debounce temporal"""
        import time
        current_time = time.time()
        key = f"{msg_type}:{msg}"
        
        if key not in self.last_log_time:
            self.last_log_time[key] = current_time
            return True
        
        # Só permite log se passou tempo suficiente
        if current_time - self.last_log_time[key] >= min_interval:
            self.last_log_time[key] = current_time
            return True
        
        return False
    
    def info(self, msg):
        if self._should_log(msg, "INFO", 2.0):  # Mínimo 2s entre logs iguais
            print(f"[{self.name}] INFO: {msg}")
    
    def warning(self, msg):
        if self._should_log(msg, "WARNING", 3.0):  # Mínimo 3s entre warnings iguais
            print(f"[{self.name}] WARNING: {msg}")
    
    def error(self, msg):
        if self._should_log(msg, "ERROR", 1.0):  # Sempre mostrar erros
            print(f"[{self.name}] ERROR: {msg}")
    
    def debug(self, msg):
        pass  # Silenciar debug completamente