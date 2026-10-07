<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api, wsUrl } from './api'
import GameMap from './components/GameMap.vue'
import RadarView from './components/RadarView.vue'
import PushSettings from './components/PushSettings.vue'
import RoundTimer from './components/RoundTimer.vue'
import { formatTimer, timerSeconds } from './roundTime'
import Scoreboard from './components/Scoreboard.vue'
import { objectIcon } from './icons'
const captureNotice = ref('')
let noticeTimer = 0
function showCaptureNotice(message: string) { captureNotice.value = message; clearTimeout(noticeTimer); noticeTimer = window.setTimeout(() => captureNotice.value = '', 12000) }
import GameActionDialog from './components/GameActionDialog.vue'
const actionDialog = ref<InstanceType<typeof GameActionDialog>>()
function refreshAfterAction() { load().catch(() => flash('Score vernieuwen mislukt. Probeer het later opnieuw.')) }
type User = { id: string; name: string; role: string; team_id: string | null; team_name?: string; game_id?: string; profile_image?: string | null }
type Game = { id: string; code: string | null; name: string; status: string; ends_at?: string | null; timer_remaining_seconds?: number | null; server_now?: string }
const user = ref<User | null>(null), adminName = ref('admin'), adminPassword = ref(''), gameCode = ref('RONDE-A'), teamName = ref(''), adminMode = ref(false), error = ref(''), status = ref('')
const objects = ref<any[]>([]), scores = ref<any[]>([]), locations = ref<any[]>([]), tab = ref<'dashboard'|'map'|'score'|'admin'|'timer'>('dashboard')
const round = ref<Game | null>(null), clockOffset = ref(0)
let clockTicker = 0, refreshedDeadline = '', lastBonus = ''
const remainingSeconds = computed(() => timerSeconds(round.value, now.value + clockOffset.value))
const countdown = computed(() => formatTimer(remainingSeconds.value))
const roundFinished = computed(() => round.value?.status === 'FINISHED' || (round.value?.status === 'RUNNING' && remainingSeconds.value === 0))
const roundRunning = computed(() => round.value?.status === 'RUNNING' && !roundFinished.value)
function syncRound(game: Game) { round.value = game; if (game.server_now) clockOffset.value = Date.parse(game.server_now) - Date.now(); now.value = Date.now() }
const games = ref<Game[]>([]), selectedGameId = ref(''), newGameCode = ref(''), adminSubTab = ref<'rounds'|'objects'>('rounds')
const form = ref({ type: 'PUZZLE', name: '', description: '', latitude: 0, longitude: 0, activation_radius_meters: 40, reward_points: 500, question: '', answer: '', points_per_minute: 1, capture_seconds: 60, cooldown_seconds: 300, search_radius_meters: 50 })
let watcher = 0, timer = 0, refreshTimer = 0, socket: WebSocket | undefined
const isAdmin = computed(() => user.value?.role === 'ADMIN')
const phoneLocation = ref<any>(null), gpsState = ref('waiting'), gpsError = ref(''), now = ref(Date.now())
const gpsStale = computed(() => Boolean(phoneLocation.value && now.value - phoneLocation.value.updatedAt > 60000))
const gpsProblem = computed(() => gpsState.value === 'error' || gpsStale.value)
const gpsLabel = computed(() => gpsState.value === 'error' ? gpsError.value : gpsStale.value ? 'GPS verouderd' : phoneLocation.value ? `GPS ± ${Math.round(phoneLocation.value.accuracy)} m` : 'GPS zoeken…')
const mapLocations = computed(() => !isAdmin.value && phoneLocation.value && user.value ? [{ player_id: user.value.id, team_id: user.value.team_id, name: user.value.name, team_name: user.value.team_name, profile_image: user.value.profile_image, location: phoneLocation.value }] : locations.value)
function mapAction(object: any) { if (object.type === 'PUZZLE') solve(object); else if (object.type === 'CAPTURE_POINT') capture(object); else if (object.type === 'PHOTO_POINT') actionDialog.value?.open('photo', object); else scan() }
const mascotLogo = 'https://lh3.googleusercontent.com/aida-public/AB6AXuCI316EyPZYN-dEftmLoX_hN9zPIdqM9dqO6-U6-WWOQgjTut0YjabkA1dT_FwdumJG_oEYNpOejgOhkgxRcbvle-A2tlid4vhrRH9FAdE_pCXpn5DRTJRa7bd54zqkxR84nK7F8ST6ll2Ma6SxYXdjAt5AazGe4ubrWSWe3hf0SP0_aoHGefH5-8aOxhKaIXopF4pNJ8EodUvoulgMhsP3DAoTwWAOUcYoquV039ZwmZh0BhXfazGA'
const gameQuery = () => isAdmin.value && selectedGameId.value ? `?game_id=${encodeURIComponent(selectedGameId.value)}` : ''
async function loadGames() { if (!isAdmin.value) return; games.value = await api('/api/admin/games'); if (!selectedGameId.value && games.value[0]) selectedGameId.value = games.value[0].id }
async function load() { await loadGames(); if (isAdmin.value && !selectedGameId.value) { objects.value=[];scores.value=[];locations.value=[];round.value=null;return }; const [nextObjects, nextScores, nextLocations, game] = await Promise.all([api('/api/game-objects'+gameQuery()), api('/api/scores'+gameQuery()), api('/api/locations'+gameQuery()), api('/api/game'+gameQuery())]); objects.value=nextObjects; const bonus=nextObjects.find((object:any)=>object.bonus_active); const bonusKey=bonus ? `${bonus.id}:${bonus.bonus_cycle}` : ''; if(bonusKey && bonusKey!==lastBonus) showCaptureNotice(`🌈 ${bonus.name} is vijf minuten lang de bonuslocatie: dubbele punten per minuut!`); lastBonus=bonusKey; scores.value=nextScores; locations.value=nextLocations; syncRound(game) }
function beginRefresh() { clearInterval(refreshTimer); clearInterval(clockTicker); refreshTimer = window.setInterval(() => load().catch(() => {}), 15000); clockTicker = window.setInterval(() => { now.value=Date.now(); const deadline=round.value?.ends_at; if (deadline && remainingSeconds.value===0 && refreshedDeadline!==deadline) { refreshedDeadline=deadline; load().catch(() => {}) } }, 1000) }
function profileSaved(updated: User) { user.value = updated; refreshAfterAction() }
async function completeSession(x:any) { localStorage.setItem('cyberjoti-token',x.access_token); user.value=x.user; if(isAdmin.value) await loadGames(); await load(); if(!isAdmin.value) { beginGps(); tab.value='map' }; beginRefresh(); connect() }
async function joinGame() { try { error.value=''; const x = await api('/api/games/join', {method:'POST', body:JSON.stringify({game_code:gameCode.value,team_name:teamName.value})}); await completeSession(x) } catch(e:any) { error.value=e.message } }
async function loginAdmin() { try { error.value=''; const x = await api('/api/auth/login', {method:'POST', body:JSON.stringify({name:adminName.value,password:adminPassword.value})}); await completeSession(x) } catch(e:any) { error.value=e.message } }
function logout() { api('/api/push/subscriptions', { method: 'DELETE' }).catch(() => {}); clearTimeout(noticeTimer); captureNotice.value=''; localStorage.removeItem('cyberjoti-token'); user.value=null; phoneLocation.value=null; gpsState.value='waiting'; tab.value='dashboard'; navigator.geolocation?.clearWatch(watcher); clearInterval(timer); clearInterval(refreshTimer); clearInterval(clockTicker); round.value=null; refreshedDeadline=''; lastBonus=''; socket?.close() }
async function sendLocation(p: GeolocationPosition) {
  if (!user.value || isAdmin.value) return
  phoneLocation.value = { lat: p.coords.latitude, lng: p.coords.longitude, accuracy: p.coords.accuracy, updatedAt: p.timestamp }
  now.value = Date.now(); gpsState.value = 'ready'; gpsError.value = ''
  try { await api('/api/location', { method: 'POST', body: JSON.stringify({ latitude: p.coords.latitude, longitude: p.coords.longitude, accuracy: p.coords.accuracy, timestamp: new Date(p.timestamp).toISOString() }) }); await load() }
  catch { status.value = 'Locatie delen mislukt. Controleer je verbinding.' }
}
function beginGps() {
  navigator.geolocation?.clearWatch(watcher); clearInterval(timer)
  gpsState.value = 'waiting'; gpsError.value = ''
  timer = window.setInterval(() => { now.value = Date.now() }, 15000)
  if (!window.isSecureContext || !navigator.geolocation) { gpsState.value = 'error'; gpsError.value = 'GPS vereist HTTPS en locatieondersteuning'; return }
  watcher = navigator.geolocation.watchPosition(sendLocation, e => {
    gpsState.value = 'error'
    gpsError.value = e.code === 1 ? 'Sta locatie toe in je browser' : e.code === 3 ? 'GPS duurt langer · probeer opnieuw' : 'GPS niet beschikbaar'
  }, { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 })
}
function connect() {
  if(socket) { socket.onclose = null; socket.close() }
  socket = new WebSocket(wsUrl(isAdmin.value ? selectedGameId.value : user.value?.game_id))
  socket.onmessage = event => {
    try {
      const message = JSON.parse(event.data)
      if(message.type === 'HEARTBEAT') return
      if(message.type === 'GAME_UPDATED' && message.data.id === round.value?.id) syncRound(message.data)
      if(message.type === 'CAPTURE_COMPLETED') showCaptureNotice(message.data.owner_team_name + ' heeft ' + message.data.object_name + ' veroverd!')
      load().catch(() => {})
    } catch {}
  }
  socket.onclose = () => setTimeout(() => user.value && connect(), 3000)
}
function canPlay() { if (roundRunning.value) return true; flash(roundFinished.value ? 'Het spel is afgelopen.' : 'De spelronde is nog niet gestart of is gepauzeerd.'); return false }
function solve(obj: any) { if (canPlay()) actionDialog.value?.open('puzzle', obj) }
function capture(obj: any) { if (canPlay()) actionDialog.value?.open('capture', obj) }
function scan() { if (canPlay()) actionDialog.value?.open('scan') }
function place(coords:{latitude:number;longitude:number}) { form.value.latitude=Number(coords.latitude.toFixed(6)); form.value.longitude=Number(coords.longitude.toFixed(6)); status.value='Punt op kaart gekozen. Vul de details in en sla op.' }
function flash(message: string) { status.value = message; window.setTimeout(() => { if (status.value === message) status.value = '' }, 5000) }
async function addObject() { try { const created=await api('/api/admin/game-objects',{method:'POST',body:JSON.stringify({...form.value,game_id:selectedGameId.value})}); flash(created.scan_token ? `NFC-token (kopieer nu): ${created.scan_token}` : `${created.name} is toegevoegd.`); form.value.name=''; form.value.description=''; form.value.question=''; form.value.answer=''; await load() } catch(e:any){flash(e.message)} }
function removeObject(obj: any) { actionDialog.value?.open('remove', { ...obj, game_id: selectedGameId.value }) }
async function createGame() { try { const game=await api('/api/admin/games',{method:'POST',body:JSON.stringify({game_code:newGameCode.value})}); await loadGames(); selectedGameId.value=game.id; newGameCode.value=''; await load(); connect() } catch(e:any){error.value=e.message} }
async function switchGame() { await load(); connect() }
async function setRoundStatus(game: Game, status: string) { try { await api('/api/admin/games/'+game.id+'/status',{method:'PUT',body:JSON.stringify({status})}); await loadGames(); await load() } catch(e:any){error.value=e.message} }
onMounted(async()=>{if(!localStorage.getItem('cyberjoti-token'))return; try{user.value=await api('/api/auth/me');await load();if(!isAdmin.value) { beginGps(); tab.value='map' };beginRefresh();connect()}catch{logout()}})
onBeforeUnmount(logout)
</script>
<template>
  <main v-if="!user" class="login"><section class="login-shell"><div class="network-meta"><span><i></i>NET_STATUS: SECURE</span><span><span class="material-symbols-outlined icon-inline">radar</span> NODE: ALLART_HQ</span></div><div class="terminal-hero"><p class="pill">✺ ALLART VAN HEEMSTEDE // JOTI-EDITION</p><div class="crest"><img :src="mascotLogo" alt="CyberJoti eend-mascotte"></div><h1>CYBERJOTI<br>HACK TERMINAL</h1><p>Voer je spelcode en teamnaam in. Gebruik dezelfde gegevens om je bestaande team te hervatten.</p></div><p class="system-banner">● SYSTEM ONLINE <span>• GPS READY • NFC ACTIVE</span></p><form v-if="!adminMode" class="auth-card" @submit.prevent="joinGame"><div class="section-title"><span><span class="material-symbols-outlined icon-inline">groups</span> TEAM START</span><small>[ CODE // 01 ]</small></div><label>SPELCODE<input v-model="gameCode" required autocomplete="off" /></label><label>TEAMNAAM<input v-model="teamName" required autocomplete="organization" /></label><button><span class="material-symbols-outlined icon-inline">bolt</span> START OF HERVAT JE TEAM</button><button type="button" class="subtle" @click="adminMode=true">ADMIN LOGIN</button><p v-if="error" class="error">{{ error }}</p></form><form v-else class="auth-card" @submit.prevent="loginAdmin"><div class="section-title"><span><span class="material-symbols-outlined icon-inline">key</span> ADMIN LOGIN</span></div><label>GEBRUIKERSNAAM<input v-model="adminName" autocomplete="username" /></label><label>WACHTWOORD<input v-model="adminPassword" type="password" autocomplete="current-password" /></label><button>INLOGGEN ALS ADMIN</button><button type="button" class="subtle" @click="adminMode=false">TERUG NAAR TEAM START</button><p v-if="error" class="error">{{ error }}</p></form><p class="login-footer">◈ SCOUTING ALLART VAN HEEMSTEDE · PROTOCOL CYBER-2025</p></section></main>
  <main v-else class="app" :class="{ 'is-map-view': tab === 'map' }"><header class="hud"><div class="brand"><b class="brand-mark"><img :src="mascotLogo" alt=""></b><b>CYBERJOTI</b></div><div class="user-meta"><span v-if="remainingSeconds != null" class="round-timer" role="timer" aria-label="Resterende speeltijd" :title="round?.status === 'PAUSED' ? 'Timer gepauzeerd' : 'Spel stopt wanneer de timer op nul staat'">{{ countdown }}<small v-if="round?.status === 'PAUSED'">PAUZE</small></span><span v-else class="online-dot"></span><small>{{ user.team_name || user.name }}</small><button class="subtle" aria-label="Uitloggen" @click="logout"><span class="material-symbols-outlined">logout</span></button></div></header><p v-if="status" class="status" role="status">{{ status }}</p>
    <p v-if="roundFinished" class="round-finished" role="status">Het spel is afgelopen. Bekijk de eindstand op het scoreboard.</p>
    <section v-if="tab==='dashboard'" class="dashboard"><div class="team-hero"><div class="team-badge"><img :src="mascotLogo" alt=""></div><div><p class="eyebrow">{{ isAdmin ? 'GAME MASTER // LIVE' : 'VELDTEAM // LIVE' }}</p><h1>{{ isAdmin ? 'CONTROL CENTER' : user?.team_name }}</h1><p>{{ isAdmin ? (games.find(g=>g.id===selectedGameId)?.name || 'Kies een spelronde') : 'Scouting Allart' }}</p></div><strong>#{{ scores.findIndex(x => x.team_id === user?.team_id) + 1 || '—' }}</strong></div><div class="stat-grid"><article><small>OBJECTEN</small><b>{{ objects.length }}</b></article><article><small>{{ isAdmin ? 'TEAMS IN RONDE' : 'GPS STATUS' }}</small><b>{{ isAdmin ? locations.length : (locations[0]?.location ? '●' : '—') }}</b></article><article><small>RANG</small><b>#{{ scores.findIndex(x => x.team_id === user?.team_id) + 1 || '—' }}</b></article></div><article v-if="objects[0]" class="mission"><p class="eyebrow"><span class="material-symbols-outlined icon-inline">crisis_alert</span> ACTIEVE MISSIE</p><h2>{{ objects[0].name }}</h2><p>{{ objects[0].description || 'Nieuwe operatie beschikbaar.' }}</p><button @click="tab='map'"><span class="material-symbols-outlined icon-inline">map</span> BEKIJK OP KAART</button></article><button v-if="!isAdmin" class="nfc-quick" @click="scan"><span class="material-symbols-outlined">contactless</span><b>NFC SCANNER STARTEN</b><span class="material-symbols-outlined">arrow_forward</span></button><div class="mission-list"><article v-for="obj in objects" :key="obj.id"><span class="object-icon" v-html="objectIcon(obj.type)"></span><div><small>{{ obj.type.replace('_',' ') }}</small><b>{{ obj.name }}</b></div><button v-if="!isAdmin && obj.type==='PUZZLE'" @click="solve(obj)">OPEN</button><button v-else-if="!isAdmin && obj.type==='CAPTURE_POINT'" @click="capture(obj)">CAPTURE</button><button v-else-if="!isAdmin" @click="mapAction(obj)">{{ obj.type === 'PHOTO_POINT' ? 'FOTO' : 'SCAN' }}</button></article></div></section>
    <RadarView v-else-if="tab==='map'" :objects="objects" :locations="mapLocations" :own-team-id="isAdmin ? undefined : user?.team_id || undefined" :admin="isAdmin" :gps-label="gpsLabel" :gps-problem="gpsProblem" @retry-gps="beginGps" @action="mapAction" @remove="removeObject" />
    <Scoreboard v-else-if="tab==='score'" :scores="scores" :own-team-id="user.team_id" :profile="!isAdmin ? user : undefined" @saved="profileSaved" />
    <RoundTimer v-else-if="tab==='timer' && isAdmin" :game="round" :countdown="countdown" @updated="refreshAfterAction" />
    <section v-else-if="tab==='admin' && isAdmin" class="admin-page"><p class="eyebrow">GAME MASTER // BEHEER</p><h1>Spelbeheer</h1><div class="filter-row"><button :class="{active:adminSubTab==='rounds'}" @click="adminSubTab='rounds'">SPEL RONDES</button><button :class="{active:adminSubTab==='objects'}" @click="adminSubTab='objects'">OBJECTEN</button></div><section v-if="adminSubTab==='rounds'"><form class="builder" @submit.prevent="createGame"><label>NIEUWE SPELCODE<input v-model="newGameCode" placeholder="RONDE-A" required /></label><button>＋ SPELRONDE MAKEN</button></form><div class="mission-list"><article v-for="game in games" :key="game.id"><div><small>{{ game.status }}</small><b>{{ game.code || game.name }}</b></div><button @click="selectedGameId=game.id;switchGame()">KIES</button><button v-if="game.status!=='RUNNING'" @click="setRoundStatus(game,'RUNNING')">START</button><button v-else @click="setRoundStatus(game,'PAUSED')">PAUZE</button></article></div></section><section v-else><p class="helper">Geselecteerde ronde: {{ games.find(g=>g.id===selectedGameId)?.code || 'kies eerst een ronde' }}. Klik op de kaart om een locatie te kiezen.</p><GameMap v-if="selectedGameId" :objects="objects" :locations="locations" editable @place="place"/><div v-if="selectedGameId" class="mission-list"><article v-for="obj in objects" :key="obj.id"><div><b>{{ obj.name }}</b><small>{{ obj.type }}</small></div><button class="danger" @click="removeObject(obj)">Verwijderen</button></article></div><form v-if="selectedGameId" class="builder" @submit.prevent="addObject"><label>TYPE<select v-model="form.type"><option value="PUZZLE">Puzzel</option><option value="CAPTURE_POINT">Capture point</option><option value="PHYSICAL_DUCK">Fysieke eend</option><option value="PHOTO_POINT">Fotopunt</option></select></label><label>NAAM<input v-model="form.name" required /></label><label class="wide">BESCHRIJVING<textarea v-model="form.description" /></label><label>LATITUDE<input v-model.number="form.latitude" type="number" step="any" required /></label><label>LONGITUDE<input v-model.number="form.longitude" type="number" step="any" required /></label><label>RADIUS (M)<input v-model.number="form.activation_radius_meters" type="number" min="5" /></label><label>{{ form.type === 'CAPTURE_POINT' ? 'PUNTEN BIJ CAPTURE' : 'PUNTEN' }}<input v-model.number="form.reward_points" type="number" min="0" /></label><template v-if="form.type==='CAPTURE_POINT'"><label>PUNTEN PER MINUUT<input v-model.number="form.points_per_minute" type="number" min="1" required /></label><label>CAPTURETIJD (SEC)<input v-model.number="form.capture_seconds" type="number" min="5" required /></label><label>COOLDOWN (SEC)<input v-model.number="form.cooldown_seconds" type="number" min="0" required /></label></template><template v-if="form.type==='PUZZLE'"><label class="wide">VRAAG<textarea v-model="form.question" required /></label><label class="wide">ANTWOORD<input v-model="form.answer" required /></label></template><button>＋ OBJECT TOEVOEGEN</button></form></section></section>
    <div v-if="captureNotice" class="capture-toast" role="status"><span>⚑ {{ captureNotice }}</span><button aria-label="Melding sluiten" @click="captureNotice = ''">✕</button></div>
    <PushSettings v-if="!isAdmin && tab === 'dashboard'" />
    <GameActionDialog ref="actionDialog" :admin="isAdmin" :game-running="roundRunning" @updated="refreshAfterAction" @notice="flash" />
    <nav :class="{admin: isAdmin}"><button :class="{active:tab==='dashboard'}" @click="tab='dashboard'"><b>▣</b>Dashboard</button><button :class="{active:tab==='map'}" @click="tab='map'"><b>◎</b>Radar kaart</button><button :class="{active:tab==='score'}" @click="tab='score'"><b>♜</b>Scoreboard</button><button v-if="isAdmin" :class="{active:tab==='admin'}" @click="tab='admin'"><b>⚙</b>Beheer</button><button v-if="isAdmin" :class="{active:tab==='timer'}" @click="tab='timer'"><b>◷</b>Timer</button></nav></main>
</template>
