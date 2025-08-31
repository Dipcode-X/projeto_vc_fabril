/**
 * SIAC Industrial Dashboard - WebSocket Manager
 * Gerenciamento de conexão WebSocket para atualizações em tempo real
 */

export class WebSocketManager {
    constructor(url, options = {}) {
        this.url = url;
        this.options = {
            reconnectInterval: 3000,
            maxReconnectAttempts: 10,
            heartbeatInterval: 30000,
            ...options
        };
        
        this.ws = null;
        this.reconnectAttempts = 0;
        this.isConnected = false;
        this.heartbeatTimer = null;
        this.reconnectTimer = null;
        
        // Event callbacks
        this.onConnect = null;
        this.onDisconnect = null;
        this.onMessage = null;
        this.onError = null;
        
        // Message queue for offline messages
        this.messageQueue = [];
        
        console.log('🔌 WebSocket Manager inicializado:', this.url);
    }
    
    /**
     * Conecta ao WebSocket
     */
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('⚠️ WebSocket já está conectado');
            return;
        }
        
        console.log('🔄 Conectando ao WebSocket...');
        
        try {
            this.ws = new WebSocket(this.url);
            this.setupEventListeners();
        } catch (error) {
            console.error('❌ Erro ao criar WebSocket:', error);
            this.handleError(error);
        }
    }
    
    /**
     * Desconecta do WebSocket
     */
    disconnect() {
        console.log('🔌 Desconectando WebSocket...');
        
        this.clearTimers();
        
        if (this.ws) {
            this.ws.close(1000, 'Desconexão solicitada');
            this.ws = null;
        }
        
        this.isConnected = false;
        this.reconnectAttempts = 0;
    }
    
    /**
     * Configura event listeners do WebSocket
     */
    setupEventListeners() {
        if (!this.ws) return;
        
        this.ws.onopen = (event) => {
            console.log('✅ WebSocket conectado');
            
            this.isConnected = true;
            this.reconnectAttempts = 0;
            
            // Processar fila de mensagens
            this.processMessageQueue();
            
            // Iniciar heartbeat
            this.startHeartbeat();
            
            // Callback de conexão
            if (this.onConnect) {
                this.onConnect(event);
            }
        };
        
        this.ws.onclose = (event) => {
            console.log('🔌 WebSocket desconectado:', event.code, event.reason);
            
            this.isConnected = false;
            this.clearTimers();
            
            // Callback de desconexão
            if (this.onDisconnect) {
                this.onDisconnect(event);
            }
            
            // Tentar reconectar se não foi fechamento intencional
            if (event.code !== 1000) {
                this.attemptReconnect();
            }
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('📡 Mensagem recebida:', data.type);
                
                // Processar mensagens especiais
                if (data.type === 'ping') {
                    this.send({ type: 'pong' });
                    return;
                }
                
                // Callback de mensagem
                if (this.onMessage) {
                    this.onMessage(data);
                }
                
            } catch (error) {
                console.error('❌ Erro ao processar mensagem:', error);
                console.error('Dados recebidos:', event.data);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('❌ Erro no WebSocket:', error);
            this.handleError(error);
        };
    }
    
    /**
     * Envia mensagem via WebSocket
     */
    send(message) {
        if (!this.isConnected || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.log('📤 WebSocket não conectado, adicionando à fila:', message);
            this.messageQueue.push(message);
            return false;
        }
        
        try {
            const messageStr = JSON.stringify(message);
            this.ws.send(messageStr);
            console.log('📤 Mensagem enviada:', message.type);
            return true;
        } catch (error) {
            console.error('❌ Erro ao enviar mensagem:', error);
            this.messageQueue.push(message);
            return false;
        }
    }
    
    /**
     * Processa fila de mensagens offline
     */
    processMessageQueue() {
        if (this.messageQueue.length === 0) return;
        
        console.log(`📬 Processando ${this.messageQueue.length} mensagens da fila`);
        
        const messages = [...this.messageQueue];
        this.messageQueue = [];
        
        messages.forEach(message => {
            this.send(message);
        });
    }
    
    /**
     * Inicia heartbeat para manter conexão viva
     */
    startHeartbeat() {
        this.clearHeartbeat();
        
        this.heartbeatTimer = setInterval(() => {
            if (this.isConnected) {
                this.send({ type: 'ping', timestamp: Date.now() });
            }
        }, this.options.heartbeatInterval);
        
        console.log('💓 Heartbeat iniciado');
    }
    
    /**
     * Para heartbeat
     */
    clearHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    /**
     * Limpa todos os timers
     */
    clearTimers() {
        this.clearHeartbeat();
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
    }
    
    /**
     * Tenta reconectar
     */
    attemptReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            console.error('❌ Máximo de tentativas de reconexão atingido');
            return;
        }
        
        this.reconnectAttempts++;
        
        console.log(`🔄 Tentativa de reconexão ${this.reconnectAttempts}/${this.options.maxReconnectAttempts}`);
        
        this.reconnectTimer = setTimeout(() => {
            this.connect();
        }, this.options.reconnectInterval);
    }
    
    /**
     * Manipula erros
     */
    handleError(error) {
        if (this.onError) {
            this.onError(error);
        }
    }
    
    /**
     * Obtém status da conexão
     */
    getStatus() {
        return {
            connected: this.isConnected,
            readyState: this.ws ? this.ws.readyState : WebSocket.CLOSED,
            reconnectAttempts: this.reconnectAttempts,
            queuedMessages: this.messageQueue.length,
            url: this.url
        };
    }
    
    /**
     * Subscreve a um tópico específico
     */
    subscribe(topic) {
        this.send({
            type: 'subscribe',
            topic: topic,
            timestamp: Date.now()
        });
    }
    
    /**
     * Cancela subscrição de um tópico
     */
    unsubscribe(topic) {
        this.send({
            type: 'unsubscribe',
            topic: topic,
            timestamp: Date.now()
        });
    }
}

export default WebSocketManager;
