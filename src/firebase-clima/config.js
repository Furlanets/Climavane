// --- ARQUIVO: config.js ---

// 1. Suas chaves de acesso
const firebaseConfig = {
    apiKey: "AIzaSyDVxvD8PmDK0jjvrNWPq1GfwSNL3lALg8c",
    authDomain: "puclima.firebaseapp.com",
    databaseURL: "https://puclima-default-rtdb.firebaseio.com",
    projectId: "puclima",
    storageBucket: "puclima.firebasestorage.app",
    messagingSenderId: "790645096867",
    appId: "1:790645096867:web:2fa98e72b214c149c71a16",
    measurementId: "G-CQZJ8MHTXR"
};

// 2. Inicializa o Firebase (Verifica se já não existe para evitar erro)
if (typeof firebase !== 'undefined' && !firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}