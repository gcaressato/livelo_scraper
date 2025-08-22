import { initializeApp } from 'firebase/app';
import { getMessaging, getToken, onMessage } from 'firebase/messaging';
import { getFirestore } from 'firebase/firestore';

// Configuração será injetada pelo GitHub Actions
const firebaseConfig = window.FIREBASE_CONFIG || {
  apiKey: "placeholder",
  authDomain: "placeholder",
  projectId: "placeholder", 
  storageBucket: "placeholder",
  messagingSenderId: "placeholder",
  appId: "placeholder",
  measurementId: "placeholder"
};

const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);
const db = getFirestore(app);

export { messaging, db };
sender/notification-manager.js (versão segura):
javascript// sender/notification-manager.js - VAPID key dinâmica
import { messaging } from './firebase-config.js';
import { getToken, onMessage } from 'firebase/messaging';

class NotificationManager {
  constructor() {
    // VAPID key será injetada pelo GitHub Actions
    this.vapidKey = window.FIREBASE_VAPID_KEY || 'placeholder';
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
        
        // Salvar token localmente
        localStorage.setItem('fcm-token', token);
        
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

  // Resto do código igual ao seu original...
}

export default NotificationManager;
