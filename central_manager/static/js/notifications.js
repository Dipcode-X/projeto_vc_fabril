/**
 * SIAC Industrial Dashboard - Toast Notifications
 * Sistema de notificações toast para feedback visual
 */

export class ToastNotification {
    constructor(options = {}) {
        this.options = {
            duration: 5000,
            position: 'top-right',
            maxToasts: 5,
            ...options
        };
        
        this.toasts = [];
        this.container = this.createContainer();
        
        console.log('🍞 Toast Notification System inicializado');
    }
    
    /**
     * Cria container de toasts
     */
    createContainer() {
        let container = document.getElementById('toastContainer');
        
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        
        return container;
    }
    
    /**
     * Mostra toast notification
     */
    show(message, type = 'info', options = {}) {
        const toastOptions = { ...this.options, ...options };
        
        // Limitar número de toasts
        if (this.toasts.length >= this.options.maxToasts) {
            this.removeOldest();
        }
        
        const toast = this.createToast(message, type, toastOptions);
        this.toasts.push(toast);
        
        // Adicionar ao DOM
        this.container.appendChild(toast.element);
        
        // Animar entrada
        setTimeout(() => {
            toast.element.classList.add('show');
        }, 10);
        
        // Auto-remover se duração especificada
        if (toastOptions.duration > 0) {
            toast.timer = setTimeout(() => {
                this.remove(toast.id);
            }, toastOptions.duration);
        }
        
        console.log(`🍞 Toast mostrado: ${type} - ${message}`);
        
        return toast.id;
    }
    
    /**
     * Cria elemento toast
     */
    createToast(message, type, options) {
        const id = this.generateId();
        const element = document.createElement('div');
        
        element.className = `toast ${type}`;
        element.dataset.toastId = id;
        
        const icon = this.getTypeIcon(type);
        const title = this.getTypeTitle(type);
        
        element.innerHTML = `
            <div class="toast-header">
                <span class="toast-icon">${icon}</span>
                <span class="toast-title">${title}</span>
                <button class="toast-close" onclick="window.toastNotification.remove('${id}')">×</button>
            </div>
            <div class="toast-message">${message}</div>
            ${options.actions ? this.createActions(options.actions, id) : ''}
        `;
        
        return {
            id,
            element,
            type,
            message,
            timer: null,
            timestamp: Date.now()
        };
    }
    
    /**
     * Cria ações do toast
     */
    createActions(actions, toastId) {
        return `
            <div class="toast-actions">
                ${actions.map(action => `
                    <button class="toast-action-btn" onclick="${action.callback}('${toastId}')">
                        ${action.text}
                    </button>
                `).join('')}
            </div>
        `;
    }
    
    /**
     * Remove toast por ID
     */
    remove(id) {
        const toastIndex = this.toasts.findIndex(t => t.id === id);
        if (toastIndex === -1) return;
        
        const toast = this.toasts[toastIndex];
        
        // Limpar timer
        if (toast.timer) {
            clearTimeout(toast.timer);
        }
        
        // Animar saída
        toast.element.classList.remove('show');
        
        // Remover do DOM após animação
        setTimeout(() => {
            if (toast.element.parentNode) {
                toast.element.parentNode.removeChild(toast.element);
            }
        }, 300);
        
        // Remover da lista
        this.toasts.splice(toastIndex, 1);
        
        console.log(`🍞 Toast removido: ${id}`);
    }
    
    /**
     * Remove toast mais antigo
     */
    removeOldest() {
        if (this.toasts.length === 0) return;
        
        const oldest = this.toasts[0];
        this.remove(oldest.id);
    }
    
    /**
     * Remove todos os toasts
     */
    removeAll() {
        const toastIds = this.toasts.map(t => t.id);
        toastIds.forEach(id => this.remove(id));
    }
    
    /**
     * Gera ID único para toast
     */
    generateId() {
        return `toast_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Obtém ícone por tipo
     */
    getTypeIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        return icons[type] || icons.info;
    }
    
    /**
     * Obtém título por tipo
     */
    getTypeTitle(type) {
        const titles = {
            success: 'Sucesso',
            error: 'Erro',
            warning: 'Atenção',
            info: 'Informação'
        };
        
        return titles[type] || titles.info;
    }
    
    /**
     * Mostra toast de sucesso
     */
    success(message, options = {}) {
        return this.show(message, 'success', options);
    }
    
    /**
     * Mostra toast de erro
     */
    error(message, options = {}) {
        return this.show(message, 'error', { duration: 8000, ...options });
    }
    
    /**
     * Mostra toast de aviso
     */
    warning(message, options = {}) {
        return this.show(message, 'warning', { duration: 6000, ...options });
    }
    
    /**
     * Mostra toast de informação
     */
    info(message, options = {}) {
        return this.show(message, 'info', options);
    }
    
    /**
     * Mostra toast persistente (sem auto-remoção)
     */
    persistent(message, type = 'info', options = {}) {
        return this.show(message, type, { duration: 0, ...options });
    }
    
    /**
     * Mostra toast com ações
     */
    withActions(message, type, actions, options = {}) {
        return this.show(message, type, { actions, ...options });
    }
    
    /**
     * Obtém estatísticas dos toasts
     */
    getStats() {
        return {
            total: this.toasts.length,
            byType: this.toasts.reduce((acc, toast) => {
                acc[toast.type] = (acc[toast.type] || 0) + 1;
                return acc;
            }, {}),
            oldest: this.toasts.length > 0 ? this.toasts[0].timestamp : null,
            newest: this.toasts.length > 0 ? this.toasts[this.toasts.length - 1].timestamp : null
        };
    }
}

// Instância global para uso direto
export const toast = new ToastNotification();

// Disponibilizar globalmente para uso em HTML
if (typeof window !== 'undefined') {
    window.toastNotification = toast;
}

export default ToastNotification;
