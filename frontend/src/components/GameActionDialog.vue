<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { api } from '../api'

type Kind = 'puzzle' | 'scan' | 'capture'
const emit = defineEmits<{ updated: []; notice: [message: string] }>()
const dialog = ref<HTMLDialogElement | null>(null)
const kind = ref<Kind>('puzzle'), object = ref<any>(null), input = ref(''), question = ref('')
const busy = ref(false), loading = ref(false), error = ref(''), result = ref(''), success = ref(false)
const activeCapture = ref<string | null>(null)
let poll = 0, version = 0, disposed = false
const title = computed(() => kind.value === 'scan' ? 'NFC-eendje scannen' : object.value?.name || 'Spelactie')
const capturing = computed(() => kind.value === 'capture' && activeCapture.value === object.value?.id)
const captureMessage = 'Capture bezig. Blijf binnen de gemarkeerde cirkel. Je locatie wordt elke 5 seconden gecontroleerd.'

async function open(nextKind: Kind, nextObject?: any) {
  const request = ++version
  kind.value = nextKind; object.value = nextObject; input.value = ''; question.value = ''
  error.value = ''; result.value = ''; success.value = false; loading.value = false
  dialog.value?.showModal()
  if (nextKind === 'puzzle') {
    loading.value = true
    try {
      const details = await api('/api/game-objects/' + nextObject.id)
      if (request === version) question.value = details.question || nextObject.description || 'Vul je antwoord in.'
    } catch (e: any) { if (request === version) error.value = e.message }
    finally { if (request === version) loading.value = false }
  }
}
function close() { dialog.value?.close() }
function finishCapture(id: string, message: string, won: boolean) {
  activeCapture.value = null
  if (kind.value === 'capture' && object.value?.id === id) { result.value = message; success.value = won }
  emit('notice', message); emit('updated')
}
async function checkCapture(id: string) {
  if (disposed || activeCapture.value !== id) return
  try {
    const response = await api('/api/capture/' + id + '/status')
    if (disposed || activeCapture.value !== id) return
    if (response.state === 'CAPTURING') poll = window.setTimeout(() => checkCapture(id), 5000)
    else finishCapture(id, response.state === 'COMPLETED' ? 'Vlag veroverd! Je teamscore is bijgewerkt.' : 'Capture gestopt. Controleer je GPS en ga terug binnen de cirkel.', response.state === 'COMPLETED')
  } catch (e: any) {
    if (!disposed) finishCapture(id, 'Capturecontrole mislukt: ' + e.message + ' Open het punt om opnieuw te starten.', false)
  }
}
async function submit() {
  if (busy.value || loading.value || success.value || capturing.value) return
  const request = version, actionKind = kind.value, target = object.value
  if (actionKind !== 'capture' && !input.value.trim()) { error.value = 'Vul eerst ' + (actionKind === 'puzzle' ? 'je antwoord' : 'de NFC-code') + ' in.'; return }
  if (actionKind === 'capture' && activeCapture.value) { error.value = 'Er loopt al een capture. Rond die eerst af.'; return }
  busy.value = true; error.value = ''; result.value = ''
  try {
    if (actionKind === 'capture') {
      await api('/api/capture/' + target.id + '/start', { method: 'POST' })
      if (disposed) return
      activeCapture.value = target.id
      poll = window.setTimeout(() => checkCapture(target.id), 5000)
    } else {
      const response = await api(actionKind === 'puzzle' ? '/api/puzzles/' + target.id + '/answer' : '/api/ducks/scan', {
        method: 'POST', body: JSON.stringify(actionKind === 'puzzle' ? { answer: input.value.trim() } : { token: input.value.trim() }),
      })
      if (disposed || request !== version) return
      success.value = actionKind === 'scan' || response.correct
      result.value = success.value ? (actionKind === 'scan' ? response.name + ' gevonden! +' : 'Goed antwoord! +') + response.points + ' punten' : 'Dat antwoord klopt nog niet. Probeer het opnieuw.'
      emit('updated')
    }
  } catch (e: any) { if (!disposed && request === version) error.value = e.message }
  finally { busy.value = false }
}
onBeforeUnmount(() => { disposed = true; version++; clearTimeout(poll); dialog.value?.close() })
defineExpose({ open })
</script>

<template>
  <dialog ref="dialog" class="game-dialog" aria-labelledby="game-dialog-title" aria-describedby="game-dialog-description">
    <div class="dialog-heading"><span class="dialog-symbol" aria-hidden="true">{{ kind === 'puzzle' ? '◆' : kind === 'capture' ? '⚑' : '◎' }}</span><button type="button" class="dialog-close" aria-label="Venster sluiten" @click="close">✕</button></div>
    <p class="eyebrow">{{ kind === 'puzzle' ? 'PUZZEL' : kind === 'capture' ? 'CAPTURE THE FLAG' : 'NFC SCANNER' }}</p>
    <h2 id="game-dialog-title">{{ title }}</h2>
    <p id="game-dialog-description">{{ kind === 'puzzle' ? 'Los de puzzel op en verdien punten voor je team.' : kind === 'capture' ? `Ga binnen de cirkel van ${object?.activation_radius_meters ?? '—'} meter staan en blijf daar tijdens de capture.` : 'Lees het eendje met je NFC-lezer en plak of typ de bijbehorende code hieronder.' }}</p>
    <form @submit.prevent="submit">
      <p v-if="loading" role="status">Puzzel laden…</p>
      <p v-else-if="kind === 'puzzle' && question" class="puzzle-question">{{ question }}</p>
      <label v-if="kind !== 'capture' && !success" class="dialog-label">{{ kind === 'puzzle' ? 'Jouw antwoord' : 'NFC-code' }}<input v-model="input" :disabled="busy || loading" :placeholder="kind === 'puzzle' ? 'Typ je antwoord…' : 'Plak of typ de code…'" autocomplete="off" :autocapitalize="kind === 'scan' ? 'none' : 'sentences'" :spellcheck="kind !== 'scan'" required /></label>
      <p v-if="error" class="dialog-error" role="alert">{{ error }}</p>
      <p v-if="result" class="dialog-result" :class="{ success }" role="status">{{ result }}</p>
      <div v-if="capturing" class="capture-state" role="status"><span class="capture-beacon" aria-hidden="true"></span><p>{{ captureMessage }}</p><small>Je kunt dit venster sluiten. De controle blijft lopen zolang de app open is.</small></div>
      <div class="dialog-actions"><button type="button" class="secondary-action" @click="close">{{ success ? 'Sluiten' : capturing ? 'Terug naar kaart' : 'Terug' }}</button><button v-if="!success && !capturing" type="submit" class="primary-action" :disabled="busy || loading || (kind === 'puzzle' && !question)">{{ busy ? 'Even wachten…' : kind === 'puzzle' ? 'Antwoord versturen' : kind === 'capture' ? 'Start capture' : 'Code controleren' }}</button></div>
    </form>
  </dialog>
</template>

<style>
.game-dialog { position: fixed; inset: 0; margin: auto; width: min(460px,calc(100% - 28px)); max-height: calc(100dvh - 32px - env(safe-area-inset-top,0px) - env(safe-area-inset-bottom,0px)); padding: 24px; overflow-y: auto; overscroll-behavior: contain; border: 1px solid #3a6e83; border-radius: 24px; background: #0c2335; color: #e2f4ff; box-shadow: 0 20px 80px #000b; }
.game-dialog::backdrop { background: #010b17c9; backdrop-filter: blur(5px); }
body:has(.game-dialog[open]) { overflow: hidden; }
.dialog-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.dialog-symbol { display: grid; place-items: center; width: 52px; height: 52px; background: #0b3b4b; color: #50e7f4; border-radius: 16px; font-size: 30px; }
.dialog-close { min-width: 48px; min-height: 48px; background: #203b50; color: #e2f4ff; border-radius: 12px; font-size: 20px; }
.game-dialog .eyebrow { color: #5de5f0; margin-bottom: 8px; }
.game-dialog h2 { font: 700 26px/1.2 'Space Grotesk',sans-serif; margin-bottom: 12px; overflow-wrap: anywhere; }
.game-dialog p { line-height: 1.55; overflow-wrap: anywhere; }
#game-dialog-description { color: #b9cfdd; font-size: 15px; }
.dialog-label { display: grid; gap: 8px; font-size: 14px; font-weight: 600; }
.dialog-label input { width: 100%; min-height: 52px; padding: 12px; background: #051727; color: #e8f9ff; border: 1px solid #537084; border-radius: 12px; font-size: 16px; }
.game-dialog :focus-visible { outline: 3px solid #62e8f5; outline-offset: 3px; }
.puzzle-question { padding: 14px; border-radius: 12px; border-left: 3px solid #00dff2; background: #163448; white-space: pre-wrap; }
.dialog-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px; }
.dialog-actions button { flex: 1 1 130px; min-height: 52px; }
.game-dialog button:disabled { opacity: .55; cursor: default; }
.dialog-error,.dialog-result { margin: 16px 0 0; padding: 12px; border-radius: 12px; background: #39252f; color: #ffc5b7; }
.dialog-result.success { background: #123c32; color: #b1f8cb; }
.capture-state { margin-top: 18px; padding: 16px; background: #183444; border: 1px solid #4b8898; border-radius: 16px; }
.capture-state small { color: #b9cfdd; line-height: 1.5; }
.capture-beacon { display: block; width: 16px; height: 16px; border-radius: 50%; background: #ffcf6a; box-shadow: 0 0 0 6px #ffcf6a22; margin: 6px 0 18px; }
@media(max-width:380px) { .game-dialog { padding: 18px; } }
</style>
