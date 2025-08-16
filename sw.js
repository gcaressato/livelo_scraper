// Service Worker para Firebase Messaging v9 (CORRIGIDO)
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

console.log('[SW] Service Worker carregando...');

// Configuração Firebase (será substituída pelo GitHub Actions)
const firebaseConfig = {
    apiKey: "API_KEY_PLACEHOLDER",
    authDomain: "PROJECT_ID.firebaseapp.com",
    projectId: "PROJECT_ID",
    storageBucket: "PROJECT_ID.appspot.com",
    messagingSenderId: "SENDER_ID",
    appId: "APP_ID"
};

let messaging;

try {
    // Inicializar Firebase
    if (!firebase.apps.length) {
        firebase.initializeApp(firebaseConfig);
    }
    
    messaging = firebase.messaging();
    console.log('[SW] Firebase Messaging inicializado');
    
    // Listener para mensagens em background
    messaging.onBackgroundMessage(function(payload) {
        console.log('[SW] Mensagem em background recebida:', payload);
        
        const notificationTitle = payload.notification?.title || 'Livelo Analytics';
        const notificationOptions = {
            body: payload.notification?.body || 'Nova oferta disponível!',
            icon: 'https://via.placeholder.com/192x192/ff0a8c/ffffff?text=L',
            badge: 'https://via.placeholder.com/96x96/ff0a8c/ffffff?text=L',
            tag: 'livelo-offer',
            requireInteraction: true,
            data: payload.data || {},
            actions: [
                {
                    action: 'view',
                    title: '👀 Ver Oferta'
                },
                {
                    action: 'dismiss',
                    title: '✖️ Dispensar'
                }
            ]
        };
        
        return self.registration.showNotification(notificationTitle, notificationOptions);
    });
    
} catch (error) {
    console.error('[SW] Erro ao inicializar Firebase:', error);
}

// Event listeners
self.addEventListener('notificationclick', function(event) {
    console.log('[SW] Clique na notificação:', event.action);
    event.notification.close();
    
    if (event.action === 'view') {
        event.waitUntil(
            clients.openWindow('https://gcaressato.github.io/livelo_scraper/')
        );
    }
});

self.addEventListener('activate', function(event) {
    console.log('[SW] Service Worker ativado');
    event.waitUntil(self.clients.claim());
});

self.addEventListener('install', function(event) {
    console.log('[SW] Service Worker instalado');
    self.skipWaiting();
});
