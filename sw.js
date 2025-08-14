// Service Worker para Firebase Messaging v8
importScripts('https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/8.10.1/firebase-messaging.js');

console.log('[SW] Carregando Service Worker...');

const firebaseConfig = {
  apiKey: "AIzaSyAibNVfTL0kvG_R3rKYYSnAeQWc5oVBFYk",
  authDomain: "livel-analytics.firebaseapp.com",
  projectId: "livel-analytics",
  storageBucket: "livel-analytics.appspot.com",
  messagingSenderId: "168707812242",
  appId: "1:168707812242:web:59b4c1df4fc553410c6f4b"
};

try {
  firebase.initializeApp(firebaseConfig);
  const messaging = firebase.messaging();
  console.log('[SW] Firebase inicializado');
  
  messaging.onBackgroundMessage(function(payload) {
    console.log('[SW] Mensagem em background:', payload);
    
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
  console.error('[SW] Erro:', error);
}

self.addEventListener('notificationclick', function(event) {
  console.log('[SW] Clique na notificação');
  event.notification.close();
  
  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('https://gc-livelo-analytics.github.io/')
    );
  }
});

self.addEventListener('activate', function(event) {
  console.log('[SW] Service Worker ativado');
});
