// Service Worker para Firebase Messaging v9 (CORRIGIDO)
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

console.log('[SW] Service Worker carregando...');

const firebaseConfig = {
    apiKey: "AIzaSyAibNVfTL0kvG_R3rKYYSnAeQWc5oVBFYk",
    authDomain: "livel-analytics_PLACEHOLDER.firebaseapp.com",
    projectId: "livel-analytics_PLACEHOLDER",
    storageBucket: "livel-analytics_PLACEHOLDER.appspot.com",
    messagingSenderId: "168707812242_PLACEHOLDER",
    appId: "1:168707812242:web:59b4c1df4fc553410c6f4b_PLACEHOLDER"
};

let messaging;

try {
    if (!firebase.apps.length) {
        firebase.initializeApp(firebaseConfig);
    }
    
    messaging = firebase.messaging();
    console.log('[SW] Firebase Messaging inicializado');
    
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
