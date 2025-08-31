import paho.mqtt.client as mqtt
import threading
import time
import logging

# Configuração do Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AlertManager:
    """
    Gerencia a conexão com o broker MQTT e o envio de alertas.
    A conexão é mantida em uma thread separada para não bloquear a aplicação principal.
    """
    def __init__(self, broker_ip, broker_port=1883, client_id="siac_central_manager"):
        self.broker_ip = broker_ip
        self.broker_port = broker_port
        self.client_id = f"{client_id}-{int(time.time())}" # ID de cliente único
        self._is_connected = False
        self._client = mqtt.Client(client_id=self.client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        # Inicia a thread de gerenciamento da conexão
        self._connection_thread = threading.Thread(target=self._manage_connection, daemon=True)
        self._connection_thread.start()

    def _on_connect(self, client, userdata, flags, rc):
        """Callback para quando a conexão é estabelecida."""
        if rc == 0:
            logger.info(f"[MQTT] Conectado com sucesso ao broker em {self.broker_ip}")
            self._is_connected = True
        else:
            logger.error(f"[MQTT] Falha ao conectar, código de retorno: {rc}")
            self._is_connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Callback para quando a conexão é perdida."""
        logger.warning(f"[MQTT] Desconectado do broker. Tentando reconectar...")
        self._is_connected = False

    def _manage_connection(self):
        """
        Loop para manter a conexão MQTT ativa. Roda em uma thread separada.
        """
        while True:
            if not self._is_connected:
                try:
                    # Tenta conectar e entra no loop de rede
                    self._client.connect(self.broker_ip, self.broker_port, 60)
                    self._client.loop_forever() # Bloqueia aqui até desconectar
                except Exception as e:
                    logger.error(f"[MQTT] Erro na conexão: {e}. Tentando novamente em 5 segundos.")
                    time.sleep(5)
            time.sleep(1) # Pausa para evitar uso excessivo de CPU se loop_forever sair

    def send_alert(self, topic, message):
        """Publica um alerta em um tópico específico."""
        if self.is_connected:
            try:
                self._client.publish(topic, message, qos=1)
                logger.info(f"Alerta enviado ao tópico '{topic}': {message}")
                time.sleep(0.1) # Adicionado para garantir o envio
            except Exception as e:
                logger.error(f"Falha ao enviar alerta para o tópico '{topic}': {e}")
        else:
            logger.warning(f"[MQTT] Não foi possível enviar alerta. Cliente não conectado.")

    @property
    def is_connected(self):
        return self._is_connected
