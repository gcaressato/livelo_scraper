// Service Worker para Firebase Cloud Messaging - Livelo Analytics

// Importar Firebase scripts (versão atualizada e estável)
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

// Configuração Firebase (placeholders substituídos pelo GitHub Actions)
const firebaseConfig = {
  apiKey: "{{FIREBASE_API_KEY}}",
  authDomain: "{{FIREBASE_AUTH_DOMAIN}}",
  projectId: "{{FIREBASE_PROJECT_ID}}",
  storageBucket: "{{FIREBASE_STORAGE_BUCKET}}",
  messagingSenderId: "{{FIREBASE_MESSAGING_SENDER_ID}}",
  appId: "{{FIREBASE_APP_ID}}",
  vapidKey: "{{FIREBASE_VAPID_KEY}}"
};

// Inicializar Firebase no Service Worker
try {
  firebase.initializeApp(firebaseConfig);
  console.log('[firebase-messaging-sw.js] ✅ Firebase inicializado:', firebaseConfig.projectId);
} catch (error) {
  console.error('[firebase-messaging-sw.js] ❌ Erro ao inicializar Firebase:', error);
}

// Obter instância do messaging
const messaging = firebase.messaging();

// Tratar mensagens em background (quando app não está em foco)
messaging.onBackgroundMessage((payload) => {
  console.log('[firebase-messaging-sw.js] 📱 Mensagem recebida em segundo plano:', payload);
  
  // Extrair dados da notificação
  const notificationTitle = payload.notification?.title || 'Livelo Analytics Pro';
  const notificationOptions = {
    body: payload.notification?.body || 'Você tem atualizações sobre seus parceiros favoritos',
    icon: payload.notification?.icon || '/icon-192.png',
    badge: '/icon-192.png',
    tag: 'livelo-update',
    requireInteraction: true,
    silent: false,
    data: payload.data || {},
    actions: [
      {
        action: 'view',
        title: 'Ver Ofertas',
        icon: '/icon-192.png'
      },
      {
        action: 'dismiss',
        title: 'Dispensar'
      }
    ]
  };

  // Mostrar notificação
  self.registration.showNotification(notificationTitle, notificationOptions)
    .then(() => {
      console.log('[firebase-messaging-sw.js] ✅ Notificação exibida com sucesso');
    })
    .catch((error) => {
      console.error('[firebase-messaging-sw.js] ❌ Erro ao exibir notificação:', error);
    });
});

// Tratar cliques nas notificações
self.addEventListener('notificationclick', (event) => {
  console.log('[firebase-messaging-sw.js] 🖱️ Clique na notificação:', event.action);
  
  // Fechar a notificação
  event.notification.close();
  
  if (event.action === 'view') {
    // Ação "Ver Ofertas"
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then((clientList) => {
          // Verificar se já existe uma janela aberta
          for (const client of clientList) {
            if (client.url.includes('livelo_scraper') && 'focus' in client) {
              return client.focus();
            }
          }
          // Abrir nova janela se não existir
          if (clients.openWindow) {
            return clients.openWindow('https://gcaressato.github.io/livelo_scraper/');
          }
        })
        .catch((error) => {
          console.error('[firebase-messaging-sw.js] Erro ao abrir janela:', error);
        })
    );
  } else if (event.action === 'dismiss') {
    // Ação "Dispensar"
    console.log('[firebase-messaging-sw.js] Notificação dispensada pelo usuário');
  } else {
    // Clique padrão na notificação (sem ação específica)
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then((clientList) => {
          for (const client of clientList) {
            if (client.url.includes('livelo_scraper') && 'focus' in client) {
              return client.focus();
            }
          }
          if (clients.openWindow) {
            return clients.openWindow('https://gcaressato.github.io/livelo_scraper/');
          }
        })
        .catch((error) => {
          console.error('[firebase-messaging-sw.js] Erro ao abrir janela:', error);
        })
    );
  }
});

// Evento de instalação do Service Worker
self.addEventListener('install', (event) => {
  console.log('[firebase-messaging-sw.js] 🔧 Service Worker instalado');
  // Pular waiting e ativar imediatamente
  self.skipWaiting();
});

// Evento de ativação do Service Worker  
self.addEventListener('activate', (event) => {
  console.log('[firebase-messaging-sw.js] 🚀 Service Worker ativado');
  
  // Tomar controle de todos os clients imediatamente
  event.waitUntil(
    clients.claim().then(() => {
      console.log('[firebase-messaging-sw.js] ✅ Service Worker assumiu controle de todos os clients');
    })
  );
});

// Evento de erro global
self.addEventListener('error', (event) => {
  console.error('[firebase-messaging-sw.js] ❌ Erro global no Service Worker:', event.error);
});

// Log de inicialização completa
console.log('[firebase-messaging-sw.js] 🎉 Service Worker Livelo Analytics carregado e pronto');
console.log('[firebase-messaging-sw.js] 📱 Pronto para receber notificações push');
