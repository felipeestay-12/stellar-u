// main.js - Gestión de Comunicación y Teclado

// 1. Conexión única (usamos var para permitir re-declaración segura si fuera necesario)
var socket = io();
window.socket = socket;

const logBox = document.getElementById('log-box');

// --- Funciones Auxiliares ---
function agregarLog(mensaje) {
    if (!logBox) return;
    const linea = document.createElement('div');
    linea.innerHTML = `> ${mensaje}`;
    logBox.appendChild(linea);
    logBox.scrollTop = logBox.scrollHeight; 
}

// --- Eventos de Conexión ---
socket.on('connect', () => {
    agregarLog("<span style='color: #00d4ff;'>Enlace establecido con el NUC.</span>");
});

socket.on('disconnect', () => {
    agregarLog("<span style='color: #f00;'>¡CONEXIÓN PERDIDA! Reintentando...</span>");
});

// --- Control por Teclado (WASD y Flechas) ---
const keyMap = {
    'ArrowUp': 'up',    'w': 'up',    'W': 'up',
    'ArrowDown': 'down', 's': 'down', 'S': 'down',
    'ArrowLeft': 'left', 'a': 'left', 'A': 'left',
    'ArrowRight': 'right','d': 'right','D': 'right'
};

let currentDirection = null;

document.addEventListener('keydown', (event) => {
    const direction = keyMap[event.key];
    if (direction && currentDirection !== direction) {
        currentDirection = direction;
        socket.emit('command', { action: 'start', direction: direction });
    }

    if (event.key === 'm' || event.key === 'M' || event.key === ' ') {
        if (typeof toggleCmd === "function") toggleCmd('mic');
    }
});

document.addEventListener('keyup', (event) => {
    const direction = keyMap[event.key];
    if (direction && currentDirection === direction) {
        currentDirection = null;
        socket.emit('command', { action: 'stop', direction: direction });
    }
});

// Mensajes genéricos del servidor
socket.on('estado_servidor', (data) => {
    agregarLog(data);
});