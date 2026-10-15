import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './style.css'
import './map-theme.css'
import './prototype-details.css'
import './radar-overrides.css'
import './wide-layout.css'
import './command-board.css'
import './persistent-footer.css'
import './dashboard-stack.css'
import './mobile-field.css'
import './photos.css'
import './round-ui.css'
import './bonus.css'
import './motion.css'
import './field-features.css'
createApp(App).use(createPinia()).mount('#app')

// Use the same worker as push settings so app installation and notifications share one scope.
if ('serviceWorker' in navigator) window.addEventListener('load', () => { navigator.serviceWorker.register('/push-sw.js').catch(() => {}) })
