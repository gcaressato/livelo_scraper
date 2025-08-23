import { initializeApp } from 'firebase/app';
import { getMessaging, getToken, onMessage } from 'firebase/messaging';
import { getFirestore } from 'firebase/firestore';

// Configuração será injetada dinamicamente pelo GitHub Actions
const firebaseConfig = window.FIREBASE_CONFIG || {
  apiKey: "placeholder-will-be-replaced",
  authDomain: "placeholder-will-be-replaced",
  projectId: "placeholder-will-be-replaced",
  storageBucket: "placeholder-will-be-replaced",
  messagingSenderId: "placeholder-will-be-replaced",
  appId: "placeholder-will-be-replaced",
  measurementId: "placeholder-will-be-replaced"
};

const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);
const db = getFirestore(app); // ← Removida a duplicação

export { messaging, db };
