import paho.mqtt.client as mqtt
import threading
import time
import logging
import json

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

        # Conecta e inicia o loop em uma thread de fundo. A biblioteca gerencia a reconexão.
        try:
            self._client.connect_async(self.broker_ip, self.broker_port, 60)
            self._client.loop_start() # Inicia a thread de rede que lida com reconexões
        except Exception as e:
            logger.error(f"[MQTT] Erro ao iniciar conexão: {e}")

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
        logger.warning(f"[MQTT] Desconectado do broker. A reconexão será tentada automaticamente.")
        self._is_connected = False

    def send_alert(self, topic, message):
        """Publica um alerta em um tópico específico."""
        if self._is_connected:
            try:
                self._client.publish(topic, message, qos=1)
                logger.info(f"Alerta enviado ao tópico '{topic}': {message}")
            except Exception as e:
                logger.error(f"Falha ao enviar alerta para o tópico '{topic}': {e}")
        else:
            logger.warning(f"[MQTT] Não foi possível enviar alerta. Cliente não conectado.")

    def publish_json(self, topic, payload, qos=1, retain=False):
        """Publica payload JSON em um tópico específico, com QoS e retain opcionais."""
        if self._is_connected:
            try:
                self._client.publish(topic, json.dumps(payload), qos=qos, retain=retain)
                logger.info(f"[MQTT] JSON publicado em '{topic}': {payload} (qos={qos}, retain={retain})")
            except Exception as e:
                logger.error(f"Falha ao publicar JSON para o tópico '{topic}': {e}")
        else:
            logger.warning(f"[MQTT] Não foi possível publicar JSON. Cliente não conectado.")

    @property
    def is_connected(self):
        return self._is_connected
