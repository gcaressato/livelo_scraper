// Service Worker para Livelo Analytics Pro
// Gerencia notificações push e cache offline

importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

// Configuração Firebase (será substituída pelo GitHub Actions)
firebase.initializeApp({
  apiKey: "AIzaSyAibNVfTL0kvG_R3rKYYSnAeQWc5oVBFYk",
  authDomain: "livel-analytics.firebaseapp.com",
  projectId: "livel-analytics",
  storageBucket: "livel-analytics.appspot.com",
  messagingSenderId: "168707812242",
  appId: "1:168707812242:web:59b4c1df4fc553410c6f4b"
});

const messaging = firebase.messaging();

const CACHE_NAME = 'livelo-analytics-v1.2';
const urlsToCache = [
  '/',
  '/index.html',
  '/manifest.json',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css'
];

// Instalar Service Worker
self.addEventListener('install', (event) => {
  console.log('SW: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('SW: Caching app shell');
        return cache.addAll(urlsToCache);
      })
      .then(() => {
        console.log('SW: Skip waiting');
        return self.skipWaiting();
      })
  );
});

// Ativar Service Worker
self.addEventListener('activate', (event) => {
  console.log('SW: Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('SW: Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('SW: Claim clients');
      return self.clients.claim();
    })
  );
});

// Interceptar requisições (Cache First Strategy)
self.addEventListener('fetch', (event) => {
  // Apenas para requisições GET
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Se encontrou no cache, retorna
        if (response) {
          return response;
        }

        // Senão, busca na rede
        return fetch(event.request).then((response) => {
          // Verifica se é uma resposta válida
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }

          // Clona a resposta
          const responseToCache = response.clone();

          // Adiciona ao cache
          caches.open(CACHE_NAME)
            .then((cache) => {
              cache.put(event.request, responseToCache);
            });

          return response;
        });
      })
      .catch(() => {
        // Se falhar, retorna uma página offline básica
        if (event.request.destination === 'document') {
          return caches.match('/index.html');
        }
      })
  );
});

// NOTIFICAÇÕES PUSH - Handler principal
messaging.onBackgroundMessage((payload) => {
  console.log('SW: Mensagem recebida em background:', payload);

  const notificationTitle = payload.notification?.title || 'Livelo Analytics';
  const notificationOptions = {
    body: payload.notification?.body || 'Novo update disponível',
    icon: payload.notification?.icon || 'https://via.placeholder.com/192x192/ff0a8c/ffffff?text=L',
    badge: 'https://via.placeholder.com/96x96/ff0a8c/ffffff?text=L',
    tag: 'livelo-offer',
    renotify: true,
    requireInteraction: true,
    actions: [
      {
        action: 'view',
        title: '👀 Ver Oferta',
        icon: 'https://via.placeholder.com/32x32/28a745/ffffff?text=✓'
      },
      {
        action: 'dismiss',
        title: '✖️ Dispensar',
        icon: 'https://via.placeholder.com/32x32/dc3545/ffffff?text=✖'
      }
    ],
    data: {
      url: payload.data?.url || '/',
      parceiro: payload.data?.parceiro || '',
      pontos: payload.data?.pontos || '',
      timestamp: Date.now()
    },
    vibrate: [200, 100, 200],
    silent: false
  };

  return self.registration.showNotification(notificationTitle, notificationOptions);
});

// Clique na notificação
self.addEventListener('notificationclick', (event) => {
  console.log('SW: Clique na notificação:', event);

  const action = event.action;
  const notification = event.notification;
  const data = notification.data || {};

  // Fechar a notificação
  notification.close();

  if (action === 'dismiss') {
    // Apenas fecha
    return;
  }

  // Ação padrão ou 'view' - abrir o app
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Verificar se já existe uma janela aberta
        for (let client of clientList) {
          if (client.url.includes(self.location.origin)) {
            // Focar na janela existente
            return client.focus().then(() => {
              // Enviar mensagem para a janela sobre a notificação clicada
              client.postMessage({
                type: 'NOTIFICATION_CLICKED',
                data: data,
                action: action
              });
            });
          }
        }

        // Se não houver janela aberta, abrir nova
        const urlToOpen = data.url || '/';
        return clients.openWindow(urlToOpen);
      })
  );
});

// Fechar notificação
self.addEventListener('notificationclose', (event) => {
  console.log('SW: Notificação fechada:', event.notification.tag);
  
  // Analytics opcional - registrar que foi fechada
  const data = event.notification.data || {};
  console.log('Notificação fechada - dados:', data);
});

// Listener para mensagens do app principal
self.addEventListener('message', (event) => {
  console.log('SW: Mensagem recebida:', event.data);

  if (event.data && event.data.type) {
    switch (event.data.type) {
      case 'SKIP_WAITING':
        self.skipWaiting();
        break;
      
      case 'CHECK_FAVORITES':
        // Verificar favoritos com ofertas
        checkFavoritesOffers(event.data.favorites);
        break;
      
      case 'UPDATE_TOKEN':
        // Atualizar token FCM
        console.log('Token FCM atualizado:', event.data.token);
        break;
    }
  }
});

// Função para verificar ofertas dos favoritos
function checkFavoritesOffers(favorites) {
  // Esta função seria chamada pelo app principal
  // para verificar se algum favorito tem oferta nova
  console.log('SW: Verificando ofertas para favoritos:', favorites);
}

// Sincronização em background (se suportado)
self.addEventListener('sync', (event) => {
  console.log('SW: Sync event:', event.tag);
  
  if (event.tag === 'check-offers') {
    event.waitUntil(
      // Verificar ofertas mesmo quando app está fechado
      checkOffersInBackground()
    );
  }
});

async function checkOffersInBackground() {
  try {
    // Tentar buscar dados atualizados
    const response = await fetch('/api/check-offers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log('SW: Ofertas verificadas em background:', data);
    }
  } catch (error) {
    console.log('SW: Erro ao verificar ofertas em background:', error);
  }
}

// Versão do SW para debug
console.log('SW: Livelo Analytics Service Worker v1.2 carregado');
