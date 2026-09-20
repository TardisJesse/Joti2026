<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const message = ref(''), active = ref(false), busy = ref(false), publicKey = ref('')
let registration: ServiceWorkerRegistration | undefined
onMounted(async () => {
  if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) { message.value = 'Op iPhone: voeg de app toe aan je beginscherm en open hem daar voor telefoonmeldingen.'; return }
  try {
    const config = await api('/api/push/config')
    if (!config.enabled) { message.value = 'Telefoonmeldingen wachten op configuratie door de beheerder.'; return }
    publicKey.value = config.public_key
    registration = await navigator.serviceWorker.register('/push-sw.js')
    registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.getSubscription()
    if (subscription) { await api('/api/push/subscriptions', { method: 'POST', body: JSON.stringify(subscription) }); active.value = true }
  } catch { message.value = 'Meldingen konden niet worden geladen. Probeer later opnieuw.' }
})
async function toggle() {
  if (!registration) return
  busy.value = true; message.value = ''
  try {
    if (active.value) {
      await api('/api/push/subscriptions', { method: 'DELETE' })
      await (await registration.pushManager.getSubscription())?.unsubscribe()
      active.value = false
    } else {
      if (await Notification.requestPermission() !== 'granted') { message.value = 'Sta meldingen toe in je browserinstellingen.'; return }
      const bytes = Uint8Array.from(atob(publicKey.value.replace(/-/g, '+').replace(/_/g, '/')), char => char.charCodeAt(0))
      const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: bytes })
      await api('/api/push/subscriptions', { method: 'POST', body: JSON.stringify(subscription) })
      active.value = true
    }
  } catch (e: any) { message.value = e.message || 'Meldingen inschakelen mislukt.' }
  finally { busy.value = false }
}
</script>
<template><div class="push-settings"><button v-if="publicKey" class="secondary-action" :disabled="busy" @click="toggle">{{ busy ? 'Even wachten…' : active ? 'Telefoonmeldingen uitschakelen' : 'Telefoonmeldingen inschakelen' }}</button><p v-if="message" role="status">{{ message }}</p></div></template>
<style>.push-settings{padding:8px 16px;color:#b9cfdd;font-size:13px}.push-settings button{width:100%}.push-settings p{margin:0;line-height:1.5}</style>
