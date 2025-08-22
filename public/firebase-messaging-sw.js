importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

// Configuração será substituída dinamicamente
const firebaseConfig = {
  apiKey: "{{FIREBASE_API_KEY}}",
  authDomain: "{{FIREBASE_AUTH_DOMAIN}}",
  projectId: "{{FIREBASE_PROJECT_ID}}",
  storageBucket: "{{FIREBASE_STORAGE_BUCKET}}",
  messagingSenderId: "{{FIREBASE_MESSAGING_SENDER_ID}}",
  appId: "{{FIREBASE_APP_ID}}",
  measurementId: "{{FIREBASE_MEASUREMENT_ID}}"
};

firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  console.log('Mensagem recebida em segundo plano:', payload);

  const notificationTitle = payload.notification?.title || 'Livelo Analytics';
  const notificationOptions = {
    body: payload.notification?.body || 'Você tem atualizações sobre seus parceiros favoritos',
    icon: payload.notification?.icon || '/icon-192.png',
    badge: '/badge-72.png',
    tag: 'livelo-update',
    requireInteraction: true,
    data: payload.data || {},
    actions: [
      {
        action: 'view',
        title: 'Ver Carteira'
      },
      {
        action: 'dismiss',
        title: 'Dispensar'
      }
    ]
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});

self.addEventListener('notificationclick', (event) => {
  console.log('Clique na notificação:', event);
  
  event.notification.close();
  
  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('https://gcaressato.github.io/livelo_scraper/')
    );
  } else if (event.action === 'dismiss') {
    console.log('Notificação dispensada');
  } else {
    event.waitUntil(
      clients.openWindow('https://gcaressato.github.io/livelo_scraper/')
    );
  }
});
