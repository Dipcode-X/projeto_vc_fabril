/**
 * SIAC Industrial Dashboard - Main Controller
 * HTML5 + JavaScript Moderno para controle industrial
 */

import { WebSocketManager } from './websocket.js';
import { UIComponents } from './components.js';
import { toast as Toast } from './notifications.js';

class SiacDashboard {
    constructor() {
        this.apiBase = '/api/v1'; // Base URL for all API calls
        this.wsUrl = `ws://${window.location.host}${this.apiBase}/dashboard`;
        this.ws = null;
        this.ui = new UIComponents();
        // Usa a instância singleton para sincronizar com o botão "x" dos toasts
        this.toast = Toast;
        this.data = {
            setores: [],
            cameras: [],
            status: {},
            produtos: [],
            linhas: []
        };
        this.selectedCamera = null;
        this.selectedProduct = null;
        
        // Bind methods
        this.handleWebSocketMessage = this.handleWebSocketMessage.bind(this);
        this.refreshData = this.refreshData.bind(this);
        
        this.init();
    }
    
    async init() {
        console.log('Iniciando inicialização do dashboard...');
        this.initEventListeners();
        this.startTimeUpdates();
         // Liga handlers de botões (fechar modais, refresh, etc.)
        this.setupEventListeners();
        
        // Watchdog: evita overlay eterno se algo travar na inicialização
        const initWatchdog = setTimeout(() => {
            const overlay = document.getElementById('loadingOverlay');
            if (overlay && window.getComputedStyle(overlay).display !== 'none') {
                console.warn('Watchdog: forçando ocultar overlay de loading após timeout.');
                this.hideLoading();
            }
        }, 15000);
        
        try {
            console.log('Carregando dados essenciais...');
            // Tenta carregar os dados essenciais primeiro
            await this.loadCoreData(); 
            console.log('Dados essenciais carregados com sucesso!');
            this.renderDashboard(); // Renderiza o que já tem


            this.toast.show('Dashboard inicializado. Verificando câmeras...', 'info');

            // Tenta carregar os status das câmeras, que podem falhar individualmente
            const cameraCheckSuccess = await this.checkAllCameraStatuses();

            if (cameraCheckSuccess) {
                this.toast.show('Sistema inicializado e todas as câmeras online!', 'success');
            } else {
                this.toast.show('Sistema inicializado, mas algumas câmeras falharam.', 'warning');
            }

            this.setupWebSocket();
        } catch (error) {
            console.error("Falha crítica na inicialização: ", error);
            this.toast.show('Erro crítico ao inicializar o sistema.', 'error');
            this.showError(`Falha na inicialização do sistema: ${error.message}`);
        } finally {
            clearTimeout(initWatchdog);
            // Garante que o overlay não fique preso
            this.hideLoading();
        }
        
        // Adiciona evento de clique para o botão de fechar o modal de stream
        document.getElementById('closeStreamModal')?.addEventListener('click', () => this.closeStreamModal());
        
        // Fecha o modal ao clicar no fundo escuro
        document.querySelector('#streamModal .modal-background')?.addEventListener('click', () => this.closeStreamModal());
    }
    
    initEventListeners() {
        console.log('Configurando manipuladores de eventos...');
        // Event listener for closing modals
        document.querySelectorAll('.modal .close, .modal-background').forEach(closeButton => {
            closeButton.addEventListener('click', (event) => {
                event.preventDefault();
                this.closeAllModals();
            });
        });

        // Global listener for 'View Analysis' buttons
        document.body.addEventListener('click', (event) => {
            const viewButton = event.target.closest('.btn-view-analysis');
            if (viewButton) {
                event.stopPropagation();
                const cameraId = viewButton.dataset.cameraId;
                if (cameraId) {
                    this.openCameraStream(cameraId);
                }
            }
        });
    }
    
    setupEventListeners() {
        console.log('Configurando manipuladores de eventos...');
        // Refresh button
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', this.refreshData);
        }
        
        // Modal close buttons (Bulma: .delete) and background
        document.querySelectorAll('.modal .delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.closeModal(e.target.closest('.modal'));
            });
        });
        // Modal overlay clicks (close on backdrop)
        document.querySelectorAll('.modal .modal-background').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    this.closeModal(overlay.closest('.modal'));
                }
            });
        });
        
        // Product modal buttons
        const cancelProductBtn = document.getElementById('cancelProductBtn');
        const applyProductBtn = document.getElementById('applyProductBtn');
        
        if (cancelProductBtn) {
            cancelProductBtn.addEventListener('click', () => {
                this.closeModal(document.getElementById('productModal'));
            });
        }
        
        if (applyProductBtn) {
            applyProductBtn.addEventListener('click', () => this.applyProductChange());
        }
        
        // Stream modal close handlers (Bulma modal)
        const streamModal = document.getElementById('streamModal');
        if (streamModal) {
            const closeBtn = streamModal.querySelector('.delete');
            const backdrop = streamModal.querySelector('.modal-background');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.closeStreamModal());
            }
            if (backdrop) {
                backdrop.addEventListener('click', () => this.closeStreamModal());
            }
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
            if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
                e.preventDefault();
                this.refreshData();
            }
        });
        
        // Botão fechar do painel inline de stream
        const closeStreamPanelBtn = document.getElementById('closeStreamPanel');
        if (closeStreamPanelBtn) {
            closeStreamPanelBtn.addEventListener('click', () => this.hideStreamPanel());
        }
    }
    
    async loadCoreData() {
        console.log('Carregando dados do sistema...');
        this.showLoading('Carregando dados do sistema...');
        const endpoints = {
            dashboard: `${this.apiBase}/dashboard`,
            setores: `${this.apiBase}/setores`,
            linhas: `${this.apiBase}/linhas`,
            produtos: `${this.apiBase}/produtos`,
            cameras: `${this.apiBase}/cameras`
        };

        const fetchWithTimeout = async (key, url, timeoutMs = 10000) => {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), timeoutMs);
            try {
                const res = await fetch(url, { signal: controller.signal, cache: 'no-store' });
                if (!res.ok) throw new Error(`Falha ao carregar ${key} (HTTP ${res.status})`);
                return await res.json();
            } catch (err) {
                console.error(`Erro ao buscar '${key}' em ${url}:`, err);
                throw err;
            } finally {
                clearTimeout(timer);
            }
        };

        const [dashboardData, setores, linhas, produtos, cameras] = await Promise.all([
            fetchWithTimeout('dashboard', endpoints.dashboard),
            fetchWithTimeout('setores', endpoints.setores),
            fetchWithTimeout('linhas', endpoints.linhas),
            fetchWithTimeout('produtos', endpoints.produtos),
            fetchWithTimeout('cameras', endpoints.cameras)
        ]);

        this.data.status = dashboardData.status || {};
        this.data.setores = setores || [];
        this.data.linhas = linhas || [];
        this.data.produtos = produtos || [];
        this.data.cameras = cameras || [];
    }

    async checkAllCameraStatuses() {
        console.log('Verificando status das câmeras...');
        let allOk = true;
        // Helper com timeout e no-store
        const fetchStatus = async (url, timeoutMs = 8000) => {
            const controller = new AbortController();
            const timer = setTimeout(() => controller.abort(), timeoutMs);
            try {
                const res = await fetch(url, { signal: controller.signal, cache: 'no-store' });
                return res;
            } finally {
                clearTimeout(timer);
            }
        };
        const statusPromises = this.data.cameras.map(async (camera) => {
            try {
                const statusResponse = await fetchStatus(`${this.apiBase}/cameras/${camera.id}/status`);
                if (statusResponse.ok) {
                    const status = await statusResponse.json();
                    camera.status = status;
                    if (!status.running) {
                        allOk = false;
                        console.warn(`Câmera ${camera.nome} (ID: ${camera.id}) não está rodando.`);
                    }
                } else {
                    allOk = false;
                    camera.status = { running: false, error: 'Status não disponível' };
                    console.error(`Falha ao obter status da câmera ${camera.id}. Status: ${statusResponse.status}`);
                }
            } catch (error) {
                allOk = false;
                camera.status = { running: false, error: 'Erro de conexão' };
                console.error(`Erro de conexão ao verificar status da câmera ${camera.id}:`, error);
            }
        });

        await Promise.all(statusPromises);
        this.renderDashboard(); // Re-renderiza com os status atualizados
        return allOk;
    }
    
    setupWebSocket() {
        console.log('Iniciando conexão WebSocket...');
        this.ws = new WebSocketManager(this.wsUrl);
        
        this.ws.onMessage = this.handleWebSocketMessage;
        
        this.ws.onConnect = () => {
            this.updateConnectionStatus('online');
            this.toast.show('Conexão em tempo real estabelecida', 'success');
        };
        
        this.ws.onDisconnect = () => {
            this.updateConnectionStatus('offline');
            this.toast.show('Conexão perdida - tentando reconectar...', 'warning');
        };
        
        this.ws.onError = (error) => {
            this.updateConnectionStatus('offline');
            this.toast.show('Erro na conexão em tempo real', 'error');
        };
        
        this.ws.connect();
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'camera_status_update':
                this.updateCameraStatus(data.payload.camera_id, data.payload.status);
                break;
            case 'detection_update':
                this.updateDetectionInfo(data.payload.camera_id, data.payload.detection_data);
                break;
            case 'alert':
                this.handleAlert(data.payload);
                break;
            case 'log':
                // If the log panel is open for this camera, display the log
                if (this.selectedCamera && this.selectedCamera.id === data.payload.camera_id) {
                    this.addLogToStreamPanel(data.payload.message);
                }
                break;
            default:
                console.warn('Tipo de mensagem WS desconhecida:', data.type);
        }
    }
    
    handleStatusUpdate(statusData) {
        console.log('Atualizando status do sistema...');
        this.data.status = { ...this.data.status, ...statusData };
        this.updateOverviewCards();
    }
    
    handleCameraStatusChange(cameraData) {
        console.log('Atualizando status da câmera...');
        const camera = this.data.cameras.find(c => c.id === cameraData.camera_id);
        if (camera) {
            camera.status = { ...camera.status, ...cameraData };
            this.updateCameraStatus(camera);
        }
    }
    
    handleDetectionUpdate(detectionData) {
        console.log('Atualizando dados de detecção...');
        // Update detection data in real-time
        const camera = this.data.cameras.find(c => c.id === detectionData.camera_id);
        if (camera) {
            camera.detection = detectionData;
            this.updateCameraDetection(camera);
        }
    }
    
    handleAlert(alertData) {
        console.log('Tratando alerta...');
        const alertTypes = {
            'error': 'error',
            'warning': 'warning',
            'info': 'info',
            'success': 'success'
        };
        
        const toastType = alertTypes[alertData.severity] || 'info';
        this.toast.show(alertData.message, toastType);
        
        // Update UI if needed
        if (alertData.camera_id) {
            const camera = this.data.cameras.find(c => c.id === alertData.camera_id);
            if (camera) {
                camera.lastAlert = alertData;
                this.updateCameraStatus(camera);
            }
        }
    }
    
    renderDashboard() {
        console.log('Renderizando dashboard...');
        // Update overview cards
        this.updateOverviewCards();
        
        // Render setores
        this.renderSetores();
        
        // Update breadcrumb
        this.updateBreadcrumb(['Dashboard']);
    }
    
    renderSetores() {
        console.log('Renderizando setores...');
        const setoresGrid = document.getElementById('setoresGrid');
        if (!setoresGrid) return;
        
        setoresGrid.innerHTML = '';
        
        if (this.data.setores.length === 0) {
            setoresGrid.innerHTML = `
                <div class="card">
                    <div class="card-content text-center">
                        <p>Nenhum setor encontrado</p>
                        <p class="text-secondary">Configure setores no sistema</p>
                    </div>
                </div>
            `;
            return;
        }
        
        let rendered = 0;
        for (const setor of this.data.setores) {
            const setorCameras = this.data.cameras.filter(c => c.setor_id === setor.id);
            const setorLinhas = this.data.linhas.filter(l => l.setor_id === setor.id);
            
            if (setorCameras.length === 0) {
                // Skip setores that are not connected to any camera
                continue;
            }
            
            const setorCard = this.ui.createSetorCard(setor, setorCameras, setorLinhas);
            setoresGrid.appendChild(setorCard);
            rendered += 1;
        }
        
        // If there are exactly two setor cards, append a placeholder to form 3 columns
        if (rendered === 2 && typeof this.ui.createSetorPlaceholderCard === 'function') {
            console.log('Exatamente 2 setores renderizados. Adicionando card placeholder para completar 3 colunas.');
            setoresGrid.appendChild(this.ui.createSetorPlaceholderCard());
        }
        
        if (rendered === 0) {
            setoresGrid.innerHTML = `
                <div class="card">
                    <div class="card-content text-center">
                        <p>Nenhum setor com câmeras vinculado</p>
                        <p class="text-secondary">Adicione câmeras aos setores no sistema</p>
                    </div>
                </div>`;
        }
    }
    
    updateOverviewCards() {
        console.log('Atualizando cards de visão geral...');
        // System status
        const systemStatusEl = document.getElementById('systemStatus');
        if (systemStatusEl) {
            const isOnline = this.data.status.sistema_online !== false;
            systemStatusEl.textContent = isOnline ? '🟢 Online' : '🔴 Offline';
            systemStatusEl.className = isOnline ? 'metric-value text-success' : 'metric-value text-error';
        }
        
        // Cameras
        const camerasActiveEl = document.getElementById('camerasActive');
        const camerasTotalEl = document.getElementById('camerasTotal');
        
        if (camerasActiveEl && camerasTotalEl) {
            const activeCameras = this.data.cameras.filter(c => c.status?.running).length;
            const totalCameras = this.data.cameras.length;
            
            camerasActiveEl.textContent = activeCameras;
            camerasTotalEl.textContent = totalCameras;
        }
        
        // Alerts
        const alertsPendingEl = document.getElementById('alertsPending');
        if (alertsPendingEl) {
            const pendingAlerts = this.data.status.alertas_pendentes || 0;
            alertsPendingEl.textContent = pendingAlerts;
        }
    }
    
    updateConnectionStatus(status) {
        console.log('Atualizando status da conexão...');
        const statusIndicator = document.getElementById('connectionStatus');
        if (!statusIndicator) return;
        
        const statusDot = statusIndicator.querySelector('.status-dot');
        const statusText = statusIndicator.querySelector('.status-text');
        
        if (statusDot && statusText) {
            statusDot.className = `status-dot ${status}`;
            
            const statusTexts = {
                'online': 'Conectado',
                'offline': 'Desconectado',
                'warning': 'Instável'
            };
            
            statusText.textContent = statusTexts[status] || 'Desconhecido';
        }
    }
    
    startTimeUpdates() {
        console.log('Iniciando atualizações de tempo...');
        const updateTime = () => {
            const timeEl = document.getElementById('systemTime');
            if (timeEl) {
                const now = new Date();
                timeEl.textContent = now.toLocaleString('pt-BR');
            }
        };
        
        updateTime();
        setInterval(updateTime, 1000);
    }
    
    async refreshData() {
        console.log('Atualizando dados...');
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<span class="btn-icon">⏳</span> Atualizando...';
        }
        
        this.showLoading('Atualizando dados...');
        
        try {
            await this.loadCoreData();
            await this.checkAllCameraStatuses();
            this.renderDashboard();
            this.toast.show('Dados atualizados com sucesso!', 'success');
        } catch (error) {
            this.toast.show('Erro ao atualizar dados', 'error');
        } finally {
            this.hideLoading();
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<span class="btn-icon">🔄</span> Atualizar';
            }
        }
    }
    
    // Camera control methods
    async toggleCamera(cameraId, action) {
        console.log(`Tentando ${action} câmera ${cameraId}...`);
        try {
            const response = await fetch(`${this.apiBase}/cameras/${cameraId}/${action}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            if (!response.ok) throw new Error(`Erro ${response.status}: ${response.statusText}`);

            const desiredRunning = action === 'start';
            const actionText = desiredRunning ? 'iniciada' : 'parada';
            this.toast.show(`Comando enviado. Aguardando câmera ser ${actionText}...`, 'info');

            // Aguarda o backend confirmar o estado desejado
            const ok = await this.waitForCameraState(cameraId, desiredRunning, 7000);
            const camera = this.data.cameras.find(c => c.id === cameraId);
            if (camera) this.updateCameraStatus(camera);

            if (ok) {
                this.toast.show(`Câmera ${actionText} com sucesso!`, 'success');
            } else {
                this.toast.show(`Tempo esgotado ao ${action === 'start' ? 'iniciar' : 'parar'} a câmera. Verifique o dispositivo.`, 'warning');
            }
        } catch (error) {
            this.toast.show(`Erro ao controlar câmera: ${error.message}`, 'error');
        }
    }
    
    showCameraModal(cameraId) {
        console.log(`Abrindo modal de câmera ${cameraId}...`);
        const camera = this.data.cameras.find(c => c.id === cameraId);
        if (!camera) return;
        
        this.selectedCamera = camera;
        
        const modal = document.getElementById('cameraModal');
        const modalTitle = document.getElementById('cameraModalTitle');
        const modalContent = document.getElementById('cameraModalContent');
        
        if (modalTitle) {
            modalTitle.textContent = `📹 ${camera.nome}`;
        }
        
        if (modalContent) {
            modalContent.innerHTML = this.ui.createCameraDetailContent(camera, this.data.produtos);
            
            // Add event listeners for camera controls
            this.setupCameraControlListeners(camera.id);
        }
        
        this.showModal(modal);
    }
    
    showProductModal(cameraId) {
        console.log(`Abrindo modal de produto para câmera ${cameraId}...`);
        const camera = this.data.cameras.find(c => c.id === cameraId);
        if (!camera) return;
        
        this.selectedCamera = camera;
        
        const modal = document.getElementById('productModal');
        const productList = document.getElementById('productList');
        
        if (productList) {
            productList.innerHTML = this.ui.createProductList(this.data.produtos, camera.produto_id);
            
            // Add event listeners for product selection
            const productItems = productList.querySelectorAll('.product-item');
            productItems.forEach(item => {
                item.addEventListener('click', () => {
                    productItems.forEach(i => i.classList.remove('selected'));
                    item.classList.add('selected');
                    this.selectedProduct = parseInt(item.dataset.productId);
                });
            });
        }
        
        this.showModal(modal);
    }
    
    openCameraStream(cameraId) {
        this.closeAllModals(); // Garante que modais abertos sejam fechados
        console.log(`Abrindo stream de câmera ${cameraId} (painel inline)...`);
        
        const camera = this.data.cameras.find(c => c.id === cameraId);
        if (!camera) {
            this.toast.show(`Câmera com ID ${cameraId} não encontrada.`, 'error');
            return;
        }

        this.selectedCamera = camera; // Track selected camera

        const panel = document.getElementById('streamPanel');
        const img = document.getElementById('streamPanelImg');
        const status = document.getElementById('streamPanelStatus');
        const title = document.getElementById('streamPanelTitle');
        const logContent = document.getElementById('streamLogContent');

        // Limpa logs antigos
        if(logContent) logContent.innerHTML = '';

        if (!panel || !img || !status || !title) {
            console.error('Elementos do painel de stream não encontrados.');
            return;
        }

        title.textContent = `Análise de Câmera: ${camera.nome}`;
        
        // Setup stream URL and loading
        const streamUrl = `${this.apiBase}/streams/camera/${cameraId}`;
        status.textContent = 'Conectando...';
        status.className = 'tag is-warning';
        
        img.onload = () => {
            console.log('Stream loaded successfully.');
            status.textContent = 'Ao Vivo';
            status.className = 'tag is-success';
        };
        
        img.onerror = () => {
            console.error('Failed to load stream.');
            status.textContent = 'Erro de Conexão';
            status.className = 'tag is-danger';
            img.src = ''; // Clear broken image
        };
        
        img.src = streamUrl;
        img.style.display = 'block';

        panel.classList.remove('hidden');
        panel.setAttribute('aria-hidden', 'false');

        // Adiciona um log inicial
        this.addLogToStreamPanel('Iniciando console de análise...');
    }

    /**
     * Adiciona uma mensagem ao painel de logs do stream.
     */
    addLogToStreamPanel(message) {
        const logContent = document.getElementById('streamLogContent');
        if (!logContent) return;

        const logEntry = document.createElement('p');
        logEntry.textContent = `[${new Date().toLocaleTimeString('pt-BR')}] ${message}`;
        
        logContent.appendChild(logEntry);
        
        // Auto-scroll para a última mensagem
        logContent.scrollTop = logContent.scrollHeight;
    }

    closeStreamModal() {
        // Mantém compatibilidade com handlers antigos chamando hideStreamPanel()
        console.log('Fechando stream (painel inline)...');
        this.hideStreamPanel();
    }
    
    setupCameraControlListeners(cameraId) {
        console.log('Configurando manipuladores de controle de câmera...');
        const startBtn = document.querySelector(`[data-action="start"][data-camera="${cameraId}"]`);
        const stopBtn = document.querySelector(`[data-action="stop"][data-camera="${cameraId}"]`);
        const changeProductBtn = document.querySelector(`[data-action="change-product"][data-camera="${cameraId}"]`);
        
        if (startBtn) {
            startBtn.addEventListener('click', () => this.toggleCamera(cameraId, 'start'));
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.toggleCamera(cameraId, 'stop'));
        }
        
        if (changeProductBtn) {
            changeProductBtn.addEventListener('click', () => {
                this.closeModal(document.getElementById('cameraModal'));
                setTimeout(() => this.showProductModal(cameraId), 300);
            });
        }
    }
    
    updateCameraStatus(camera) {
        console.log('Atualizando status da câmera...');
        // Update camera status in the UI
        const cameraDots = document.querySelectorAll(`[data-camera-id="${camera.id}"]`);
        cameraDots.forEach(dot => {
            const status = camera.status?.running ? 'online' : 'offline';
            dot.className = `camera-dot ${status}`;
        });
        
        // Update overview cards
        this.updateOverviewCards();
    }
    
    updateCameraDetection(camera) {
        console.log('Atualizando dados de detecção da câmera...');
        // Update detection data in camera cards
        const detectionElements = document.querySelectorAll(`[data-detection-camera="${camera.id}"]`);
        detectionElements.forEach(el => {
            if (camera.detection) {
                el.textContent = `Contagem: ${camera.detection.contagem || 0}`;
            }
        });
    }
    
    updateBreadcrumb(items) {
        console.log('Atualizando breadcrumb...');
        const breadcrumb = document.getElementById('breadcrumb');
        if (!breadcrumb) return;
        
        breadcrumb.innerHTML = items.map((item, index) => {
            const isLast = index === items.length - 1;
            return `<span class="breadcrumb-item ${isLast ? 'active' : ''}">${item}</span>`;
        }).join(' › ');
    }
    
    showModal(modal) {
        console.log('Abrindo modal...');
        if (modal) {
            modal.classList.add('is-active');
            document.body.style.overflow = 'hidden';
        }
    }
    
    closeModal(modal) {
        console.log('Fechando modal...');
        if (modal) {
            modal.classList.remove('is-active');
            document.body.style.overflow = '';
        }
    }
    
    closeAllModals() {
        console.log('Fechando todos os modais...');
        const modals = document.querySelectorAll('.modal.is-active, .modal');
        modals.forEach(modal => this.closeModal(modal));
        // Também oculta o painel inline de stream, se aberto
        this.hideStreamPanel();
    }

    showLoading(message = 'Carregando...') {
        console.log('Exibindo carregamento...');
        const loadingOverlay = document.getElementById('loadingOverlay');
        const loadingText = document.getElementById('loadingText');
        if (loadingOverlay) {
            if (loadingText) loadingText.textContent = message;
            // Remove classe hidden e força estilos visíveis
            loadingOverlay.classList.remove('hidden');
            loadingOverlay.style.display = 'flex';
            loadingOverlay.style.visibility = 'visible';
            loadingOverlay.style.opacity = '1';
            loadingOverlay.style.pointerEvents = 'auto';
            loadingOverlay.style.zIndex = '1000';
        }
    }
    
    hideLoading() {
        console.log('Ocultando carregamento...');
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            // Marca como hidden e força desaparecer via estilos inline
            loadingOverlay.classList.add('hidden');
            loadingOverlay.style.display = 'none';
            loadingOverlay.style.visibility = 'hidden';
            loadingOverlay.style.opacity = '0';
            loadingOverlay.style.pointerEvents = 'none';
            loadingOverlay.style.zIndex = '-1';

            // Fallback final: remove o nó do DOM após um pequeno atraso
            setTimeout(() => {
                const el = document.getElementById('loadingOverlay');
                if (el && el.parentElement) {
                    // Se ainda estiver visível por alguma razão, remove do DOM
                    if (window.getComputedStyle(el).display !== 'none') {
                        el.parentElement.removeChild(el);
                    }
                }
            }, 500);
        }
    }
    
    updateDashboardCards(data) {
        console.log('Atualizando cards do dashboard...');
        const camerasActiveElement = document.getElementById('camerasActive');
        if (camerasActiveElement) {
            camerasActiveElement.textContent = data.cameras_ativas || 0;
        }

        const camerasTotalElement = document.getElementById('camerasTotal');
        if (camerasTotalElement) {
            camerasTotalElement.textContent = data.total_cameras || 0;
        }
    }
    
    updateCameraListInSectors(cameras) {
        console.log('Atualizando lista de câmeras nos setores...');
        if (!cameras) return;

        // Atualiza a lista de câmeras local
        cameras.forEach(updatedCamera => {
            const index = this.data.cameras.findIndex(c => c.id === updatedCamera.id);
            if (index !== -1) {
                // Mescla o status para não perder dados
                const oldStatus = this.data.cameras[index].status;
                this.data.cameras[index] = { ...updatedCamera, status: oldStatus };
            } else {
                this.data.cameras.push(updatedCamera);
            }
        });

        // Re-renderiza os setores para refletir as mudanças
        this.renderSetores();
        this.updateOverviewCards();
    }
    
    // Busca status da câmera no backend e atualiza cache local
    async fetchCameraStatus(cameraId) {
        console.log('Buscando status da câmera...');
        const res = await fetch(`${this.apiBase}/cameras/${cameraId}/status`);
        if (!res.ok) throw new Error('Falha ao obter status');
        const status = await res.json();
        const cam = this.data.cameras.find(c => c.id === Number(cameraId));
        if (cam) cam.status = status;
        return status;
    }
    
    // Aguarda até que o status da câmera corresponda ao desejado ou até o timeout
    async waitForCameraState(cameraId, shouldBeRunning, timeoutMs = 6000) {
        console.log('Aguardando status da câmera...');
        const start = Date.now();
        while (Date.now() - start < timeoutMs) {
            try {
                const status = await this.fetchCameraStatus(cameraId);
                if (!!status?.running === !!shouldBeRunning) return true;
            } catch (_) { /* ignore and retry */ }
            await new Promise(r => setTimeout(r, 500));
        }
        return false;
    }
    
    // Helpers de painel inline de stream
    showStreamPanel() {
        const panel = document.getElementById('streamPanel');
        if (panel) {
            panel.classList.remove('hidden');
            panel.setAttribute('aria-hidden', 'false');
            // Garante visibilidade ao usuário
            panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    hideStreamPanel() {
        const panel = document.getElementById('streamPanel');
        const img = document.getElementById('streamPanelImg');
        if (img) img.src = '';
        if (panel && !panel.classList.contains('hidden')) {
            panel.classList.add('hidden');
            panel.setAttribute('aria-hidden', 'true');
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('Iniciando dashboard...');
    window.siacDashboard = new SiacDashboard();
});

// Export for potential external use
export default SiacDashboard;
