/**
 * SIAC Industrial Dashboard - Main Controller
 * HTML5 + JavaScript Moderno para controle industrial
 */

import { WebSocketManager } from './websocket.js';
import { UIComponents } from './components.js';
import { ToastNotification } from './notifications.js';

class SiacDashboard {
    constructor() {
        this.ws = null;
        this.ui = new UIComponents();
        this.toast = new ToastNotification();
        this.data = {
            setores: [],
            cameras: [],
            status: {},
            produtos: []
        };
        this.selectedCamera = null;
        this.selectedProduct = null;
        
        // Bind methods
        this.handleWebSocketMessage = this.handleWebSocketMessage.bind(this);
        this.refreshData = this.refreshData.bind(this);
        
        this.init();
    }
    
    async init() {
        console.log('🏭 Inicializando SIAC Dashboard...');
        
        try {
            // Setup UI event listeners
            this.setupEventListeners();
            
            // Load initial data
            await this.loadInitialData();
            
            // Setup WebSocket
            this.setupWebSocket();
            
            // Start time updates
            this.startTimeUpdates();
            
            // Hide loading overlay
            this.hideLoading();
            
            console.log('✅ Dashboard inicializado com sucesso!');
            this.toast.show('Sistema inicializado com sucesso!', 'success');
            
        } catch (error) {
            console.error('❌ Erro ao inicializar dashboard:', error);
            this.toast.show('Erro ao inicializar sistema', 'error');
            this.showError('Falha na inicialização do sistema');
        }
    }
    
    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', this.refreshData);
        }
        
        // Modal close buttons
        const modalCloses = document.querySelectorAll('.modal-close');
        modalCloses.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.closeModal(e.target.closest('.modal-overlay'));
            });
        });
        
        // Modal overlay clicks (close on backdrop)
        const modalOverlays = document.querySelectorAll('.modal-overlay');
        modalOverlays.forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    this.closeModal(overlay);
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
            applyProductBtn.addEventListener('click', () => {
                this.applyProductChange();
            });
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
    }
    
    async loadInitialData() {
        console.log('📊 Carregando dados iniciais...');
        
        try {
            // Load dashboard data
            const dashboardResponse = await fetch('/dashboard');
            if (!dashboardResponse.ok) {
                throw new Error(`Dashboard API error: ${dashboardResponse.status}`);
            }
            const dashboardData = await dashboardResponse.json();
            
            // Load setores
            const setoresResponse = await fetch('/setores');
            if (!setoresResponse.ok) {
                throw new Error(`Setores API error: ${setoresResponse.status}`);
            }
            const setores = await setoresResponse.json();
            
            // Load produtos
            const produtosResponse = await fetch('/produtos');
            if (!produtosResponse.ok) {
                throw new Error(`Produtos API error: ${produtosResponse.status}`);
            }
            const produtos = await produtosResponse.json();
            
            // Update data
            this.data.status = dashboardData.status || {};
            this.data.setores = setores || [];
            this.data.produtos = produtos || [];
            
            // Load cameras for each setor/linha
            await this.loadCamerasData();
            
            // Render initial UI
            this.renderDashboard();
            
            console.log('✅ Dados iniciais carregados:', {
                setores: this.data.setores.length,
                cameras: this.data.cameras.length,
                produtos: this.data.produtos.length
            });
            
        } catch (error) {
            console.error('❌ Erro ao carregar dados:', error);
            throw error;
        }
    }
    
    async loadCamerasData() {
        try {
            const camerasResponse = await fetch('/cameras');
            if (!camerasResponse.ok) {
                throw new Error(`Cameras API error: ${camerasResponse.status}`);
            }
            
            this.data.cameras = await camerasResponse.json();
            
            // Load status for each camera
            for (const camera of this.data.cameras) {
                try {
                    const statusResponse = await fetch(`/cameras/${camera.id}/status`);
                    if (statusResponse.ok) {
                        camera.status = await statusResponse.json();
                    } else {
                        camera.status = { running: false, error: 'Status não disponível' };
                    }
                } catch (error) {
                    console.warn(`Erro ao carregar status da câmera ${camera.id}:`, error);
                    camera.status = { running: false, error: 'Erro de conexão' };
                }
            }
            
        } catch (error) {
            console.error('❌ Erro ao carregar dados das câmeras:', error);
            this.data.cameras = [];
        }
    }
    
    setupWebSocket() {
        console.log('🔌 Configurando WebSocket...');
        
        this.ws = new WebSocketManager('ws://localhost:8000/ws/dashboard');
        
        this.ws.onMessage = this.handleWebSocketMessage;
        
        this.ws.onConnect = () => {
            console.log('✅ WebSocket conectado');
            this.updateConnectionStatus('online');
            this.toast.show('Conexão em tempo real estabelecida', 'success');
        };
        
        this.ws.onDisconnect = () => {
            console.log('⚠️ WebSocket desconectado');
            this.updateConnectionStatus('offline');
            this.toast.show('Conexão perdida - tentando reconectar...', 'warning');
        };
        
        this.ws.onError = (error) => {
            console.error('❌ Erro no WebSocket:', error);
            this.updateConnectionStatus('offline');
            this.toast.show('Erro na conexão em tempo real', 'error');
        };
        
        this.ws.connect();
    }
    
    handleWebSocketMessage(data) {
        console.log('📡 Mensagem WebSocket recebida:', data);
        
        switch (data.type) {
            case 'status':
                this.handleStatusUpdate(data.data);
                break;
                
            case 'camera_status_changed':
                this.handleCameraStatusChange(data.data);
                break;
                
            case 'detection_update':
                this.handleDetectionUpdate(data.data);
                break;
                
            case 'alert_triggered':
                this.handleAlert(data.data);
                break;
                
            case 'pong':
                // Heartbeat response
                break;
                
            default:
                console.log('Tipo de mensagem desconhecido:', data.type);
        }
    }
    
    handleStatusUpdate(statusData) {
        this.data.status = { ...this.data.status, ...statusData };
        this.updateOverviewCards();
    }
    
    handleCameraStatusChange(cameraData) {
        const camera = this.data.cameras.find(c => c.id === cameraData.camera_id);
        if (camera) {
            camera.status = { ...camera.status, ...cameraData };
            this.updateCameraStatus(camera);
        }
    }
    
    handleDetectionUpdate(detectionData) {
        // Update detection data in real-time
        const camera = this.data.cameras.find(c => c.id === detectionData.camera_id);
        if (camera) {
            camera.detection = detectionData;
            this.updateCameraDetection(camera);
        }
    }
    
    handleAlert(alertData) {
        console.log('🚨 Alerta recebido:', alertData);
        
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
        console.log('🎨 Renderizando dashboard...');
        
        // Update overview cards
        this.updateOverviewCards();
        
        // Render setores
        this.renderSetores();
        
        // Update breadcrumb
        this.updateBreadcrumb(['Dashboard']);
    }
    
    updateOverviewCards() {
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
    
    renderSetores() {
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
        
        this.data.setores.forEach(setor => {
            const setorCard = this.ui.createSetorCard(setor, this.data.cameras);
            setoresGrid.appendChild(setorCard);
        });
    }
    
    updateConnectionStatus(status) {
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
        console.log('🔄 Atualizando dados...');
        
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<span class="btn-icon">⏳</span> Atualizando...';
        }
        
        try {
            await this.loadInitialData();
            this.toast.show('Dados atualizados com sucesso!', 'success');
        } catch (error) {
            console.error('❌ Erro ao atualizar dados:', error);
            this.toast.show('Erro ao atualizar dados', 'error');
        } finally {
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<span class="btn-icon">🔄</span> Atualizar';
            }
        }
    }
    
    // Camera control methods
    async toggleCamera(cameraId, action) {
        console.log(`🎥 ${action} câmera ${cameraId}...`);
        
        try {
            const response = await fetch(`/cameras/${cameraId}/${action}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Erro ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            const actionText = action === 'start' ? 'iniciada' : 'parada';
            this.toast.show(`Câmera ${actionText} com sucesso!`, 'success');
            
            // Update camera status
            const camera = this.data.cameras.find(c => c.id === cameraId);
            if (camera) {
                camera.status.running = action === 'start';
                this.updateCameraStatus(camera);
            }
            
        } catch (error) {
            console.error(`❌ Erro ao ${action} câmera:`, error);
            this.toast.show(`Erro ao controlar câmera: ${error.message}`, 'error');
        }
    }
    
    showCameraModal(cameraId) {
        const camera = this.data.cameras.find(c => c.id === cameraId);
        if (!camera) return;
        
        this.selectedCamera = camera;
        
        const modal = document.getElementById('cameraModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalContent = document.getElementById('modalContent');
        
        if (modalTitle) {
            modalTitle.textContent = `📹 ${camera.nome}`;
        }
        
        if (modalContent) {
            modalContent.innerHTML = this.ui.createCameraDetailContent(camera);
            
            // Add event listeners for camera controls
            this.setupCameraControlListeners(camera.id);
        }
        
        this.showModal(modal);
    }
    
    showProductModal(cameraId) {
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
    
    async applyProductChange() {
        if (!this.selectedCamera || !this.selectedProduct) return;
        
        console.log(`📦 Alterando produto da câmera ${this.selectedCamera.id} para ${this.selectedProduct}...`);
        
        try {
            const response = await fetch(`/cameras/${this.selectedCamera.id}/produto`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    produto_id: this.selectedProduct
                })
            });
            
            if (!response.ok) {
                throw new Error(`Erro ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            this.toast.show('Produto alterado com sucesso!', 'success');
            
            // Update camera data
            this.selectedCamera.produto_id = this.selectedProduct;
            
            // Close modal
            this.closeModal(document.getElementById('productModal'));
            
            // Refresh data
            await this.refreshData();
            
        } catch (error) {
            console.error('❌ Erro ao alterar produto:', error);
            this.toast.show(`Erro ao alterar produto: ${error.message}`, 'error');
        }
    }
    
    setupCameraControlListeners(cameraId) {
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
        // Update detection data in camera cards
        const detectionElements = document.querySelectorAll(`[data-detection-camera="${camera.id}"]`);
        detectionElements.forEach(el => {
            if (camera.detection) {
                el.textContent = `Contagem: ${camera.detection.contagem || 0}`;
            }
        });
    }
    
    updateBreadcrumb(items) {
        const breadcrumb = document.getElementById('breadcrumb');
        if (!breadcrumb) return;
        
        breadcrumb.innerHTML = items.map((item, index) => {
            const isLast = index === items.length - 1;
            return `<span class="breadcrumb-item ${isLast ? 'active' : ''}">${item}</span>`;
        }).join(' › ');
    }
    
    showModal(modal) {
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }
    
    closeModal(modal) {
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    }
    
    closeAllModals() {
        const modals = document.querySelectorAll('.modal-overlay');
        modals.forEach(modal => this.closeModal(modal));
    }
    
    hideLoading() {
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.classList.add('hidden');
        }
    }
    
    showError(message) {
        const main = document.querySelector('.dashboard-main');
        if (main) {
            main.innerHTML = `
                <div class="card text-center">
                    <div class="card-content">
                        <h2>❌ Erro</h2>
                        <p>${message}</p>
                        <button class="btn btn-primary" onclick="location.reload()">
                            🔄 Recarregar Página
                        </button>
                    </div>
                </div>
            `;
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.siacDashboard = new SiacDashboard();
});

// Export for potential external use
export default SiacDashboard;
