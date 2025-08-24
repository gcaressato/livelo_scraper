// Configuração Firebase dinâmica - Livelo Analytics Pro
// Placeholders substituídos automaticamente pelo GitHub Actions

// Configuração principal do Firebase
window.firebaseConfig = {
    apiKey: "{{FIREBASE_API_KEY}}",
    authDomain: "{{FIREBASE_AUTH_DOMAIN}}",
    projectId: "{{FIREBASE_PROJECT_ID}}",
    storageBucket: "{{FIREBASE_STORAGE_BUCKET}}",
    messagingSenderId: "{{FIREBASE_MESSAGING_SENDER_ID}}",
    appId: "{{FIREBASE_APP_ID}}"
};

// Chave VAPID para notificações web push
window.firebaseVapidKey = "{{FIREBASE_VAPID_KEY}}";

// Função para verificar se Firebase foi configurado
window.checkFirebaseConfig = function() {
    const config = window.firebaseConfig;
    const vapidKey = window.firebaseVapidKey;
    
    if (!config.apiKey || config.apiKey.includes('{{')) {
        console.warn('⚠️ Firebase config não foi substituída corretamente');
        return false;
    }
    
    if (!vapidKey || vapidKey.includes('{{')) {
        console.warn('⚠️ VAPID key não foi substituída corretamente');
        return false;
    }
    
    console.log('✅ Firebase config carregada:', config.projectId);
    return true;
};

// Verificar automaticamente ao carregar
if (window.checkFirebaseConfig()) {
    console.log('🔥 Firebase pronto para uso');
    console.log('📱 Notificações web push disponíveis');
} else {
    console.log('⚠️ Firebase não configurado - modo somente leitura');
}

// Expor globalmente para debug (apenas em desenvolvimento)
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    window.debugFirebase = {
        config: window.firebaseConfig,
        vapidKey: window.firebaseVapidKey ? window.firebaseVapidKey.substring(0, 10) + '...' : 'não definida',
        checkConfig: window.checkFirebaseConfig
    };
    console.log('🔍 Debug Firebase disponível em window.debugFirebase');
}
