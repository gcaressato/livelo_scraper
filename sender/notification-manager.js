import { messaging } from './firebase-config.js';
import { getToken, onMessage } from 'firebase/messaging';

class NotificationManager {
  constructor() {
    // VAPID key será injetada dinamicamente pelo GitHub Actions
    this.vapidKey = window.FIREBASE_VAPID_KEY || 'placeholder-will-be-replaced';
    this.token = null;
  }

  async requestPermission() {
    try {
      const permission = await Notification.requestPermission();
      
      if (permission === 'granted') {
        console.log('Permissão para notificações concedida');
        await this.getRegistrationToken();
        return true;
      } else {
        console.log('Permissão negada');
        return false;
      }
    } catch (error) {
      console.error('Erro ao solicitar permissão:', error);
      return false;
    }
  }

  async getRegistrationToken() {
    try {
      const token = await getToken(messaging, { 
        vapidKey: this.vapidKey 
      });
      
      if (token) {
        this.token = token;
        console.log('Token FCM obtido:', token);
        
        // Salvar token no localStorage
        localStorage.setItem('fcm-token', token);
        
        // Expor token globalmente para debug
        window.livelFCMToken = token;
        
        return token;
      } else {
        console.log('Não foi possível obter o token');
        return null;
      }
    } catch (error) {
      console.error('Erro ao obter token:', error);
      return null;
    }
  }

  setupForegroundListener() {
    onMessage(messaging, (payload) => {
      console.log('Mensagem recebida em primeiro plano:', payload);
      this.showNotification(payload);
    });
  }

  showNotification(payload) {
    const { title, body, icon } = payload.notification || {};
    
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.ready.then((registration) => {
        registration.showNotification(title || 'Nova notificação', {
          body: body || 'Você tem atualizações sobre seus parceiros favoritos',
          icon: icon || '/icon-192.png',
          badge: '/badge-72.png',
          tag: 'livelo-update',
          requireInteraction: true,
          actions: [
            {
              action: 'view',
              title: 'Ver Ofertas'
            },
            {
              action: 'dismiss',
              title: 'Dispensar'
            }
          ]
        });
      });
    }
  }

  async testConnection() {
    try {
      console.log('Testando conexão Firebase...');
      
      const hasPermission = await this.requestPermission();
      if (!hasPermission) {
        throw new Error('Permissão não concedida');
      }

      const token = await this.getRegistrationToken();
      if (!token) {
        throw new Error('Não foi possível obter token FCM');
      }

      console.log('Conexão Firebase OK!');
      return {
        success: true,
        token: token,
        message: 'Conexão estabelecida com sucesso'
      };
      
    } catch (error) {
      console.error('Erro na conexão Firebase:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
}

// Criar funções globais para compatibilidade
window.getLivelToken = () => window.livelFCMToken;
window.testLivelSystem = () => {
  const manager = new NotificationManager();
  return manager.testConnection();
};

export default NotificationManager;
