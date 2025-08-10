importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyAibNVfTL0kvG_R3rKYYSnAeQWc5oVBFYk",
  authDomain: "livel-analytics.firebaseapp.com",
  projectId: "livel-analytics",
  storageBucket: "livel-analytics.firebasestorage.app",
  messagingSenderId: "168707812242",
  appId: "1:168707812242:web:59b4c1df4fc553410c6f4b"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  console.log('📨 Background Message recebida:', payload);
  
  const notificationTitle = payload.notification?.title || 'Nova oferta Livelo!';
  const notificationOptions = {
    body: payload.notification?.body || 'Confira as novas oportunidades disponíveis',
    icon: 'https://via.placeholder.com/192x192/ff0a8c/ffffff?text=L',
    badge: 'https://via.placeholder.com/96x96/ff0a8c/ffffff?text=L',
    tag: 'livelo-offer',
    requireInteraction: true,
    data: payload.data || {},
    actions: [
      {
        action: 'open',
        title: 'Ver Dashboard',
        icon: 'https://via.placeholder.com/24x24/ff0a8c/ffffff?text=→'
      },
      {
        action: 'close',
        title: 'Fechar',
        icon: 'https://via.placeholder.com/24x24/6c757d/ffffff?text=X'
      }
    ]
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});

self.addEventListener('notificationclick', (event) => {
  console.log('🖱️ Notificação clicada:', event);
  event.notification.close();
  
  if (event.action === 'open' || !event.action) {
    event.waitUntil(
      clients.matchAll({ type: 'window' }).then((clientList) => {
        // Se já há uma aba aberta, focar nela
        for (const client of clientList) {
          if (client.url === '/' && 'focus' in client) {
            return client.focus();
          }
        }
        // Caso contrário, abrir nova aba
        if (clients.openWindow) {
          return clients.openWindow('/');
        }
      })
    );
  }
});

self.addEventListener('notificationclose', (event) => {
  console.log('❌ Notificação fechada:', event);
});
