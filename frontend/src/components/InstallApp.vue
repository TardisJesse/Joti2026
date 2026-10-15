<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
type InstallPrompt = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> }
const prompt = ref<InstallPrompt | null>(null), help = ref<HTMLDialogElement | null>(null)
const installed = ref(window.matchMedia('(display-mode: standalone)').matches || Boolean((navigator as Navigator & { standalone?: boolean }).standalone))
function available(event: Event) { event.preventDefault(); prompt.value = event as InstallPrompt }
function done() { installed.value = true; prompt.value = null; help.value?.close() }
async function install() {
  if (!prompt.value) { help.value?.showModal(); return }
  const event = prompt.value
  prompt.value = null
  try { await event.prompt(); if ((await event.userChoice).outcome === 'accepted') done() }
  catch { help.value?.showModal() }
}
onMounted(() => { window.addEventListener('beforeinstallprompt', available); window.addEventListener('appinstalled', done) })
onBeforeUnmount(() => { window.removeEventListener('beforeinstallprompt', available); window.removeEventListener('appinstalled', done) })
</script>
<template>
  <button v-if="!installed" type="button" class="intro-button" @click="install">＋ Installeer als app</button>
  <dialog ref="help" class="install-help" aria-label="CyberJoti installeren">
    <h2>Installeer CyberJoti</h2>
    <p>iPhone of iPad: open deze pagina in Safari, tik op Delen en kies ‘Zet op beginscherm’.</p>
    <p>Android of computer: open het browsermenu en kies ‘App installeren’ of ‘Toevoegen aan startscherm’.</p>
    <p>Zie je die optie niet? Open deze pagina in Safari, Chrome of Edge. Je kunt ook direct verder spelen in de browser.</p>
    <button type="button" @click="help?.close()">Sluiten</button>
  </dialog>
</template>
