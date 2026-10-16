<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { api } from '../api'
import { prepareImage } from '../images'
import { objectIcon } from '../icons'

type Kind = 'puzzle' | 'scan' | 'capture' | 'remove' | 'photo'
const props = defineProps<{ admin?: boolean; gameRunning?: boolean }>()
const emit = defineEmits<{ updated: []; notice: [message: string] }>()
const dialog = ref<HTMLDialogElement | null>(null)
const kind = ref<Kind>('puzzle'), object = ref<any>(null), input = ref(''), question = ref('')
const busy = ref(false), loading = ref(false), error = ref(''), result = ref(''), success = ref(false)
const scanning = ref(false), backup = ref(false), nfcMessage = ref('')
let nfcAbort: AbortController | null = null
type DuckIdentifier = { serial_number: string } | { duck_number: number } | { token: string }
type NfcReader = { scan(options: { signal: AbortSignal }): Promise<void>; onreading: ((event: { serialNumber: string }) => void) | null; onreadingerror: (() => void) | null }
function stopNfc() { nfcAbort?.abort(); nfcAbort = null; scanning.value = false }
async function scanNfc() {
  if (scanning.value || busy.value || success.value || props.gameRunning === false) return
  error.value = ''; nfcMessage.value = ''
  const Reader = (window as unknown as { NDEFReader?: new () => NfcReader }).NDEFReader
  if (!window.isSecureContext || !Reader) {
    nfcMessage.value = !window.isSecureContext ? 'NFC-scannen vereist een beveiligde verbinding (HTTPS). Gebruik het eendnummer hieronder.' : 'Deze browser ondersteunt geen NFC-scanner. Gebruik het eendnummer hieronder; dat werkt ook op iPhone.'
    backup.value = true; return
  }
  const request = version, controller = new AbortController()
  nfcAbort = controller; scanning.value = true
  try {
    const reader = new Reader()
    reader.onreading = async event => {
      if (controller.signal.aborted || request !== version || !dialog.value?.open) return
      stopNfc()
      if (!event.serialNumber) { nfcMessage.value = 'Deze tag geeft geen serienummer door. Gebruik het eendnummer hieronder.'; backup.value = true; return }
      await submit({ serial_number: event.serialNumber })
    }
    reader.onreadingerror = () => {
      if (controller.signal.aborted || request !== version) return
      stopNfc(); nfcMessage.value = 'Tag niet leesbaar. Probeer opnieuw of gebruik het eendnummer hieronder.'; backup.value = true
    }
    // Calling scan from this button click triggers the browser permission prompt.
    await reader.scan({ signal: controller.signal })
    if (!controller.signal.aborted && request === version) nfcMessage.value = 'Houd je telefoon tegen de NFC-tag in het eendje.'
  } catch (e: any) {
    if (controller.signal.aborted || request !== version) return
    stopNfc(); backup.value = true
    nfcMessage.value = e.name === 'NotAllowedError' ? 'NFC-toestemming geweigerd. Sta NFC toe in je browser of gebruik het eendnummer hieronder.' : 'NFC niet beschikbaar. Controleer of NFC aanstaat of gebruik het eendnummer hieronder.'
  }
}
function dialogClosed() { stopNfc(); version++; busy.value = false }
const photo = ref(''), gallery = ref<any[]>([]), photoAllowed = ref(false), photoBusy = ref(false)
async function choosePhoto(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0], request = version
  if (!file) return
  photoBusy.value = true; error.value = ''
  try { const image = await prepareImage(file); if (request === version) photo.value = image }
  catch (e: any) { if (request === version) error.value = e.message || 'Foto laden mislukt.' }
  finally { photoBusy.value = false }
}
async function loadPhotos(id: string, request: number) {
  const response = await api('/api/photos/' + id)
  if (request !== version) return
  gallery.value = response.photos; photoAllowed.value = true; success.value = response.submitted || Boolean(props.admin)
  object.value = { ...object.value, golden: response.golden, reward_points: response.reward_points }
  if (response.submitted) result.value = 'Je team heeft hier al een foto ingestuurd.'
}
const activeCapture = ref<string | null>(null)
let poll = 0, version = 0, disposed = false
const duration = ref(60), remaining = ref(60)
let countdown = 0, deadline = 0
function syncProgress(response: any) {
  duration.value = response.capture_seconds || duration.value
  remaining.value = Math.max(0, Math.ceil(response.remaining_seconds ?? duration.value))
  deadline = Date.now() + remaining.value * 1000
  clearInterval(countdown)
  countdown = window.setInterval(() => { remaining.value = Math.max(0, Math.ceil((deadline - Date.now()) / 1000)) }, 250)
}
const progress = computed(() => Math.min(99, Math.round((1 - remaining.value / duration.value) * 100)))
const title = computed(() => kind.value === 'scan' ? 'NFC-eendje scannen' : object.value?.name || 'Spelactie')
const capturing = computed(() => kind.value === 'capture' && activeCapture.value === object.value?.id)
const captureMessage = 'Capture bezig. Blijf binnen de gemarkeerde cirkel. Je locatie wordt elke seconde gecontroleerd.'

async function open(nextKind: Kind, nextObject?: any) {
  stopNfc(); backup.value = false; nfcMessage.value = ''; busy.value = false
  const request = ++version
  kind.value = nextKind; object.value = nextObject; input.value = ''; question.value = ''
  error.value = ''; result.value = ''; success.value = false; loading.value = false
  photo.value = ''; gallery.value = []; photoAllowed.value = false
  dialog.value?.showModal()
  if (nextKind === 'puzzle') {
    loading.value = true
    try {
      const details = await api('/api/game-objects/' + nextObject.id)
      if (request === version) question.value = details.question || nextObject.description || 'Vul je antwoord in.'
    } catch (e: any) { if (request === version) error.value = e.message }
    finally { if (request === version) loading.value = false }
  }
  if (nextKind === 'photo') {
    loading.value = true
    try { await loadPhotos(nextObject.id, request) }
    catch (e: any) { if (request === version) error.value = e.message }
    finally { if (request === version) loading.value = false }
  }
}
function close() { dialogClosed(); dialog.value?.close() }
function finishCapture(id: string, message: string, won: boolean) {
  clearInterval(countdown)
  activeCapture.value = null
  if (kind.value === 'capture' && object.value?.id === id) { result.value = message; success.value = won }
  emit('notice', message); emit('updated')
}
async function checkCapture(id: string) {
  if (disposed || activeCapture.value !== id) return
  if (props.gameRunning === false) { finishCapture(id, 'De spelronde is gestopt. Capture beëindigd.', false); return }
  try {
    const response = await api('/api/capture/' + id + '/status')
    if (disposed || activeCapture.value !== id) return
    if (response.state === 'CAPTURING') { syncProgress(response); poll = window.setTimeout(() => checkCapture(id), 1000) }
    else finishCapture(id, response.state === 'COMPLETED' ? 'Vlag veroverd! Je teamscore is bijgewerkt.' : 'Capture gestopt. Controleer je GPS en ga terug binnen de cirkel.', response.state === 'COMPLETED')
  } catch (e: any) {
    if (!disposed) finishCapture(id, 'Capturecontrole mislukt: ' + e.message + ' Open het punt om opnieuw te starten.', false)
  }
}
async function submit(scanIdentifier?: DuckIdentifier) {
  if (busy.value || loading.value || photoBusy.value || success.value || capturing.value) return
  const request = version, actionKind = kind.value, target = object.value
  if (actionKind !== 'remove' && props.gameRunning === false) { error.value = 'De spelronde is gestopt. Je kunt geen volgers meer verdienen.'; return }
  if (actionKind === 'puzzle' && !input.value.trim()) { error.value = 'Vul eerst je antwoord in.'; return }
  if (actionKind === 'scan' && !scanIdentifier) {
    if (!/^(?:0?[1-9]|1[0-9]|20)$/.test(input.value.trim())) { error.value = 'Vul het nummer op het eendje in: 1 t/m 20.'; return }
    scanIdentifier = { duck_number: Number(input.value.trim()) }
    stopNfc()
  }
  if (actionKind === 'capture' && activeCapture.value) { error.value = 'Er loopt al een capture. Rond die eerst af.'; return }
  if (actionKind === 'photo' && (!photo.value || !photoAllowed.value)) { error.value = 'Kies eerst een teamfoto terwijl je binnen de cirkel staat.'; return }
  busy.value = true; error.value = ''; result.value = ''
  try {
    if (actionKind === 'photo') {
      const response = await api('/api/photos/' + target.id, { method: 'POST', body: JSON.stringify({ image: photo.value }) })
      if (disposed || request !== version) return
      success.value = true; photo.value = ''; emit('updated')
      await loadPhotos(target.id, request)
      result.value = (response.golden ? 'Eerste foto op een gouden fotopunt! +' : 'Teamfoto ingestuurd! +') + response.points + ' volgers'
    } else if (actionKind === 'remove') {
      await api('/api/admin/game-objects/' + target.id + '?game_id=' + encodeURIComponent(target.game_id), { method: 'DELETE' })
      if (disposed || request !== version) return
      result.value = 'Punt verwijderd uit de spelronde.'; success.value = true; emit('updated')
    } else if (actionKind === 'capture') {
      const response = await api('/api/capture/' + target.id + '/start', { method: 'POST' })
      if (disposed) return
      activeCapture.value = target.id
      syncProgress(response)
      poll = window.setTimeout(() => checkCapture(target.id), 1000)
    } else {
      const response = await api(actionKind === 'puzzle' ? '/api/puzzles/' + target.id + '/answer' : '/api/ducks/scan', {
        method: 'POST', body: JSON.stringify(actionKind === 'puzzle' ? { answer: input.value.trim() } : scanIdentifier),
      })
      if (disposed || request !== version) return
      success.value = actionKind === 'scan' || response.correct
      result.value = success.value ? (actionKind === 'scan' ? (response.golden ? 'Gouden ' : '') + response.name + ' gevonden! +' : 'Goed antwoord! +') + response.points + ' volgers' : 'Dat antwoord klopt nog niet. Probeer het opnieuw.'
      emit('updated')
    }
  } catch (e: any) { if (!disposed && request === version) error.value = e.message }
  finally { if (request === version) busy.value = false }
}
onBeforeUnmount(() => { stopNfc(); disposed = true; version++; clearTimeout(poll); clearInterval(countdown); dialog.value?.close() })
defineExpose({ open })
</script>

<template>
  <dialog ref="dialog" class="game-dialog" aria-labelledby="game-dialog-title" aria-describedby="game-dialog-description" @cancel="dialogClosed" @close="dialogClosed">
    <div class="dialog-heading"><span class="dialog-symbol" aria-hidden="true" v-html="objectIcon(kind === 'puzzle' ? 'PUZZLE' : kind === 'capture' ? 'CAPTURE_POINT' : kind === 'photo' ? 'PHOTO_POINT' : 'PHYSICAL_DUCK')"></span><button type="button" class="dialog-close" aria-label="Venster sluiten" @click="close">✕</button></div>
    <p class="eyebrow">{{ kind === 'puzzle' ? 'PUZZEL' : kind === 'photo' ? 'FOTOPUNT' : kind === 'capture' ? 'CAPTURE THE FLAG' : kind === 'remove' ? 'PUNT VERWIJDEREN' : 'NFC SCANNER' }}</p>
    <h2 id="game-dialog-title">{{ title }}</h2>
    <p id="game-dialog-description">{{ kind === 'puzzle' ? 'Los de puzzel op en verdien volgers voor je team.' : kind === 'photo' ? `Ga binnen ${object?.activation_radius_meters} meter van dit punt staan. Stuur een foto van jezelf met je team op deze plek. Hier kun je ook de teamfoto’s bekijken.` : kind === 'remove' ? 'Dit punt verdwijnt voor alle spelers in deze ronde. Eerder behaalde scores blijven bewaard.' : kind === 'capture' ? `Ga binnen de cirkel van ${object?.activation_radius_meters ?? '—'} meter staan en blijf daar tijdens de capture.` : 'Ga naar het eendje, druk op SCAN NFC en geef toestemming. Houd je telefoon tegen de tag. Beide manieren werken alleen als je met recente GPS in de buurt bent.' }}</p>
    <p v-if="kind === 'photo' && object?.golden && !success" class="golden-point-label">✦ Gouden fotopunt: dubbele punten voor het eerste team dat hier een foto instuurt. De server bevestigt de beloning bij het insturen.</p>
    <p v-if="kind === 'scan' && object?.golden" class="golden-point-label">✦ Gouden eend: dubbele punten voor de eerste vinder. De server bevestigt de beloning bij het scannen.</p>
    <form @submit.prevent="submit()">
      <p v-if="loading" role="status">Puzzel laden…</p>
      <p v-else-if="kind === 'puzzle' && question" class="puzzle-question">{{ question }}</p>
      <label v-if="kind === 'puzzle' && !success" class="dialog-label">Jouw antwoord<input v-model="input" :disabled="busy || loading" placeholder="Typ je antwoord…" autocomplete="off" required /></label>
      <section v-if="kind === 'scan' && !success" class="duck-scan">
        <button type="button" class="primary-action scan-nfc" :disabled="busy || scanning || props.gameRunning === false" @click="scanNfc"><span class="material-symbols-outlined" aria-hidden="true">contactless</span>{{ scanning ? 'SCANNER ACTIEF…' : 'SCAN NFC' }}</button>
        <p v-if="nfcMessage" class="nfc-status" role="status">{{ nfcMessage }}</p>
        <button v-if="scanning" type="button" class="secondary-action" @click="stopNfc">Scannen stoppen</button>
        <details class="duck-backup" :open="backup" @toggle="backup = ($event.target as HTMLDetailsElement).open"><summary>NFC werkt niet? Voer het eendnummer in</summary><label class="dialog-label">Nummer op het eendje (1–20)<input v-model="input" inputmode="numeric" pattern="(?:0?[1-9]|1[0-9]|20)" maxlength="2" autocomplete="off" :disabled="busy" placeholder="Bijvoorbeeld 3" /></label><button type="submit" class="secondary-action" :disabled="busy || props.gameRunning === false">{{ busy ? 'Controleren…' : 'Eendnummer controleren' }}</button></details>
      </section>
      <template v-if="kind === 'photo' && photoAllowed && !success"><label class="dialog-label">Teamfoto<input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" :disabled="busy || photoBusy" @change="choosePhoto" /></label><p v-if="photoBusy" role="status">Foto voorbereiden…</p><img v-if="photo" :src="photo" alt="Voorbeeld van je teamfoto" class="photo-preview" /></template>
      <div v-if="kind === 'photo' && photoAllowed" class="photo-gallery"><h3>Teamfoto’s op dit punt</h3><p v-if="!gallery.length">Nog geen foto's. Maak de eerste met je team!</p><figure v-for="item in gallery" :key="item.id"><img :src="item.image" :alt="'Teamfoto van ' + item.team_name" /><figcaption>{{ item.team_name }}</figcaption></figure></div>
      <p v-if="error" class="dialog-error" role="alert">{{ error }}</p>
      <p v-if="result" class="dialog-result" :class="{ success }" role="status">{{ result }}</p>
      <div v-if="capturing" class="capture-state" role="status"><span class="capture-beacon" aria-hidden="true"></span><p>{{ captureMessage }}</p><progress :value="progress" max="100" aria-label="Capturevoortgang"></progress><strong class="capture-clock">{{ remaining > 0 ? `${remaining} seconden resterend` : 'Tijd voorbij · server bevestigt…' }}</strong><small>Je kunt dit venster sluiten. De controle blijft lopen zolang de app open is.</small></div>
      <p v-if="kind !== 'remove' && props.gameRunning === false" class="dialog-result" role="status">De spelronde is gepauzeerd of afgelopen. Je kunt nu geen volgers verdienen.</p>
      <div class="dialog-actions"><button type="button" class="secondary-action" @click="close">{{ success ? 'Sluiten' : capturing ? 'Terug naar kaart' : 'Terug' }}</button><button v-if="!success && !capturing && kind !== 'scan'" type="submit" class="primary-action" :disabled="busy || loading || photoBusy || (kind !== 'remove' && props.gameRunning === false) || (kind === 'puzzle' && !question) || (kind === 'photo' && (!photoAllowed || !photo))">{{ busy ? 'Even wachten…' : kind === 'photo' ? 'Teamfoto insturen' : kind === 'puzzle' ? 'Antwoord versturen' : kind === 'capture' ? 'Start capture' : kind === 'remove' ? 'Verwijderen' : 'Code controleren' }}</button></div>
    </form>
  </dialog>
</template>

<style>
.scan-nfc{display:flex;align-items:center;justify-content:center;gap:12px;width:100%;min-height:88px;margin-top:20px;font-size:22px;font-weight:800}.scan-nfc .material-symbols-outlined{font-size:36px}.duck-backup{margin-top:14px;font-size:13px;color:#b9cfdd}.duck-backup summary{cursor:pointer;padding:8px 0}.duck-backup .dialog-label{margin:12px 0}.duck-backup button{width:100%;min-height:44px}.nfc-status{font-size:14px;color:#b9cfdd}

.capture-state progress{width:100%;height:14px;accent-color:#00dff2}.capture-clock{display:block;margin:10px 0 16px}.capture-state .capture-beacon{animation:capture-pulse 1s ease-in-out infinite}@keyframes capture-pulse{50%{box-shadow:0 0 0 12px #ffcf6a11;opacity:.6}}@media(prefers-reduced-motion:reduce){.capture-state .capture-beacon{animation:none}}

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
