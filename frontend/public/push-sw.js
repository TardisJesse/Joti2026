self.addEventListener('push', event => {
  let data = { title: 'CyberJoti', body: 'Er is nieuws in je spelronde.' }
  try { data = { ...data, ...event.data.json() } } catch {}
  event.waitUntil(self.registration.showNotification(data.title, { body: data.body, icon: '/app-icon.svg', data: { url: '/' } }))
})
self.addEventListener('notificationclick', event => {
  event.notification.close()
  event.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windows => {
    const app = windows.find(client => new URL(client.url).origin === self.location.origin)
    return app ? app.focus() : clients.openWindow('/')
  }))
})
