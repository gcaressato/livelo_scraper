// user-registration.js
// Sistema para registrar usuários para notificações

class LiveloNotificationRegistry {
    constructor() {
        this.apiEndpoint = 'https://api.github.com/repos/SEU_USERNAME/SEU_REPO/issues';
        this.userStorageKey = 'livelo-user-registration';
        this.backupEndpoint = 'https://formspree.io/f/YOUR_FORM_ID'; // Backup usando Formspree
    }

    // Registrar usuário para notificações
    async registerUser(fcmToken, userEmail = null) {
        try {
            const userData = {
                fcm_token: fcmToken,
                favoritos: this.getFavoritos(),
                email: userEmail,
                registered_at: new Date().toISOString(),
                user_agent: navigator.userAgent,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
            };

            // Salvar localmente primeiro
            localStorage.setItem(this.userStorageKey, JSON.stringify(userData));

            // Enviar para o servidor (via GitHub Issues como fallback)
            await this.sendUserDataToServer(userData);

            console.log('✅ Usuário registrado para notificações');
            return true;

        } catch (error) {
            console.error('❌ Erro ao registrar usuário:', error);
            return false;
        }
    }

    // Obter favoritos do localStorage
    getFavoritos() {
        try {
            return JSON.parse(localStorage.getItem('livelo-favoritos') || '[]');
        } catch {
            return [];
        }
    }

    // Atualizar favoritos do usuário
    async updateUserFavorites() {
        try {
            const userData = JSON.parse(localStorage.getItem(this.userStorageKey) || '{}');
            if (!userData.fcm_token) return false;

            userData.favoritos = this.getFavoritos();
            userData.updated_at = new Date().toISOString();

            localStorage.setItem(this.userStorageKey, JSON.stringify(userData));
            
            // Sincronizar com servidor
            await this.sendUserDataToServer(userData, 'update');

            console.log('✅ Favoritos atualizados no servidor');
            return true;

        } catch (error) {
            console.error('❌ Erro ao atualizar favoritos:', error);
            return false;
        }
    }

    // Enviar dados para servidor (via GitHub Issues)
    async sendUserDataToServer(userData, action = 'register') {
        try {
            // Método 1: GitHub Issues (requer token público limitado)
            await this.sendViaGitHubIssue(userData, action);

        } catch (error) {
            console.log('GitHub Issues falhou, tentando Formspree...');
            
            try {
                // Método 2: Formspree como backup
                await this.sendViaFormspree(userData, action);
            } catch (backupError) {
                console.log('Formspree também falhou, apenas local storage');
                throw new Error('Todos os métodos de sincronização falharam');
            }
        }
    }

    // Enviar via GitHub Issues
    async sendViaGitHubIssue(userData, action) {
        const issueTitle = `📱 Registro de Notificação - ${action.toUpperCase()}`;
        const issueBody = `
## 🔔 Registro para Notificações Push

**Ação:** ${action}
**Data:** ${new Date().toLocaleString('pt-BR')}

### 📊 Dados do Usuário:
- **Token FCM:** \`${userData.fcm_token.substring(0, 20)}...\`
- **Favoritos:** ${userData.favoritos.length} parceiros
- **Timezone:** ${userData.timezone}
- **User Agent:** ${userData.user_agent.substring(0, 50)}...

### ⭐ Favoritos Atuais:
${userData.favoritos.map(fav => `- ${fav}`).join('\n')}

---
*Registro automático do sistema de notificações*
*Para remover, feche esta issue com comentário "UNSUBSCRIBE"*
        `;

        const response = await fetch(this.apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/vnd.github.v3+json'
            },
            body: JSON.stringify({
                title: issueTitle,
                body: issueBody,
                labels: ['notification-registry', 'automated', action]
            })
        });

        if (!response.ok) {
            throw new Error(`GitHub API error: ${response.status}`);
        }

        const result = await response.json();
        console.log('✅ Registrado via GitHub Issues:', result.number);
        
        return result;
    }

    // Enviar via Formspree (backup)
    async sendViaFormspree(userData, action) {
        const formData = new FormData();
        formData.append('action', action);
        formData.append('fcm_token', userData.fcm_token);
        formData.append('favoritos', JSON.stringify(userData.favoritos));
        formData.append('registered_at', userData.registered_at);
        formData.append('timezone', userData.timezone);

        const response = await fetch(this.backupEndpoint, {
            method: 'POST',
            body: formData,
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Formspree error: ${response.status}`);
        }

        console.log('✅ Registrado via Formspree');
        return await response.json();
    }

    // Verificar se usuário está registrado
    isUserRegistered() {
        const userData = localStorage.getItem(this.userStorageKey);
        return !!userData;
    }

    // Obter dados do usuário
    getUserData() {
        try {
            return JSON.parse(localStorage.getItem(this.userStorageKey) || '{}');
        } catch {
            return {};
        }
    }

    // Cancelar registro
    async unregisterUser() {
        try {
            // Remover do localStorage
            localStorage.removeItem(this.userStorageKey);

            // Notificar servidor (opcionalmente)
            await this.sendViaGitHubIssue({ action: 'unregister' }, 'unregister');

            console.log('✅ Usuário removido do sistema de notificações');
            return true;

        } catch (error) {
            console.error('❌ Erro ao cancelar registro:', error);
            return false;
        }
    }
}

// Integração com o sistema principal
window.notificationRegistry = new LiveloNotificationRegistry();

// Função para facilitar o registro
window.registerForNotifications = async function(email = null) {
    if (!window.firebaseMessaging) {
        alert('Firebase não está configurado. Tente recarregar a página.');
        return false;
    }

    try {
        // Solicitar permissão
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            alert('Permissão para notificações é necessária.');
            return false;
        }

        // Obter token FCM
        const { getToken } = await import('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging.js');
        const token = await getToken(window.firebaseMessaging, {
            vapidKey: 'YOUR_VAPID_KEY_HERE' // Será substituído
        });

        if (!token) {
            alert('Não foi possível obter token de notificação.');
            return false;
        }

        // Registrar usuário
        const success = await window.notificationRegistry.registerUser(token, email);
        
        if (success) {
            alert('✅ Registrado com sucesso! Você receberá notificações quando seus favoritos entrarem em oferta.');
            return true;
        } else {
            alert('❌ Erro ao registrar. Tente novamente.');
            return false;
        }

    } catch (error) {
        console.error('Erro no registro:', error);
        alert('❌ Erro técnico no registro. Verifique o console.');
        return false;
    }
};

// Função para atualizar favoritos automaticamente
window.updateNotificationFavorites = async function() {
    if (window.notificationRegistry.isUserRegistered()) {
        await window.notificationRegistry.updateUserFavorites();
    }
};

// Auto-atualizar favoritos quando mudarem
document.addEventListener('DOMContentLoaded', function() {
    // Interceptar mudanças nos favoritos
    const originalToggleFavorito = window.toggleFavorito;
    
    if (typeof originalToggleFavorito === 'function') {
        window.toggleFavorito = function(...args) {
            // Executar função original
            const result = originalToggleFavorito.apply(this, args);
            
            // Atualizar no servidor
            setTimeout(() => {
                window.updateNotificationFavorites();
            }, 1000);
            
            return result;
        };
    }
});

// Função para mostrar prompt de registro
window.showNotificationPrompt = function() {
    if (window.notificationRegistry.isUserRegistered()) {
        console.log('Usuário já registrado para notificações');
        return;
    }

    if (localStorage.getItem('notification-prompt-dismissed')) {
        return;
    }

    // Criar modal de registro
    const modal = document.createElement('div');
    modal.className = 'notification-register-modal';
    modal.innerHTML = `
        <div class="modal-overlay" onclick="dismissNotificationPrompt()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h5>🔔 Ativar Notificações</h5>
                    <button onclick="dismissNotificationPrompt()">×</button>
                </div>
                <div class="modal-body">
                    <p>Receba alertas instantâneos quando seus parceiros favoritos entrarem em oferta!</p>
                    <ul>
                        <li>✅ Notificações apenas para seus favoritos</li>
                        <li>⚡ Alertas em tempo real</li>
                        <li>📱 Funciona mesmo com app fechado</li>
                        <li>🔐 Seus dados ficam seguros</li>
                    </ul>
                    <input type="email" id="userEmail" placeholder="Email (opcional)" class="form-control mb-2">
                </div>
                <div class="modal-footer">
                    <button onclick="dismissNotificationPrompt()" class="btn btn-secondary">Agora não</button>
                    <button onclick="activateNotifications()" class="btn btn-primary">🔔 Ativar</button>
                </div>
            </div>
        </div>
    `;

    // Adicionar CSS do modal
    const style = document.createElement('style');
    style.textContent = `
        .notification-register-modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        }
        .notification-register-modal .modal-content {
            background: white;
            border-radius: 12px;
            max-width: 500px;
            width: 90%;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        .notification-register-modal .modal-header {
            padding: 20px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .notification-register-modal .modal-body {
            padding: 20px;
        }
        .notification-register-modal .modal-footer {
            padding: 20px;
            border-top: 1px solid #eee;
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }
        .notification-register-modal ul {
            margin: 15px 0;
            padding-left: 20px;
        }
        .notification-register-modal li {
            margin: 5px 0;
        }
        .notification-register-modal .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
        }
        .notification-register-modal .btn-primary {
            background: #ff0a8c;
            color: white;
        }
        .notification-register-modal .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .notification-register-modal .form-control {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
    `;

    document.head.appendChild(style);
    document.body.appendChild(modal);
};

// Função para dispensar prompt
window.dismissNotificationPrompt = function() {
    const modal = document.querySelector('.notification-register-modal');
    if (modal) {
        modal.remove();
    }
    localStorage.setItem('notification-prompt-dismissed', 'true');
};

// Função para ativar notificações via modal
window.activateNotifications = async function() {
    const emailInput = document.getElementById('userEmail');
    const email = emailInput ? emailInput.value : null;
    
    const success = await window.registerForNotifications(email);
    
    if (success) {
        window.dismissNotificationPrompt();
    }
};

// Mostrar prompt após 10 segundos se não estiver registrado
setTimeout(() => {
    if (typeof window.isNotificationSupported === 'function' && window.isNotificationSupported()) {
        window.showNotificationPrompt();
    }
}, 10000);
