<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import GameMap from './GameMap.vue'
import { objectIcon } from '../icons'
import { api } from '../api'
const props = defineProps<{ objects: any[]; locations: any[]; ownTeamId?: string; admin: boolean; gpsLabel: string; gpsProblem: boolean; gameRunning?: boolean; initialObject?: any; playArea?: any }>()
const emit = defineEmits<{ retryGps: []; action: [object: any]; remove: [object: any] }>()
const map = ref<InstanceType<typeof GameMap>>()
const radar = ref(false), expanded = ref(false), selectedId = ref<string | null>(null), filter = ref('ALL')
const categories = [{ id: 'ALL', label: 'Alles' }, { id: 'PUZZLE', label: 'Puzzels' }, { id: 'PHYSICAL_DUCK', label: 'Eendjes' }, { id: 'CAPTURE_POINT', label: 'Posten' }, { id: 'PHOTO_POINT', label: "Foto’s" }, { id: 'SCANNER_POINT', label: "Scanners" }]
const visible = computed(() => props.objects.filter(object => filter.value === 'ALL' || object.type === filter.value))
const selected = computed(() => visible.value.find(object => object.id === selectedId.value))
const bonus = computed(() => props.objects.find(object => object.bonus_active))
const goldenDucks = computed(() => props.objects.filter(object => object.golden))
const own = computed(() => props.locations.find(player => props.ownTeamId && player.team_id === props.ownTeamId)?.location)
const scannerId = ref<string | null>(null), revealed = ref<any[]>([]), scannerError = ref(''), clock = ref(Date.now())
let scannerPoll = 0, scanVersion = 0, scanAbort: AbortController | undefined, scannerBusy = false, serverOffset = 0
const tick = window.setInterval(()=>clock.value=Date.now(),1000)
const scannerPoint = computed(()=>props.objects.find(object=>object.id===scannerId.value))
const recentOwn = computed(()=>own.value && !props.gpsProblem && Number(own.value.accuracy) <= 50 && clock.value - Number(own.value.updatedAt ?? Date.parse(own.value.updated_at)) <= 60000)
const scannerValid = computed(()=>Boolean(scannerPoint.value && props.gameRunning && recentOwn.value && (distance(scannerPoint.value) ?? Infinity) <= scannerPoint.value.activation_radius_meters))
const displayLocations = computed(()=>[...props.locations,...(scannerValid.value ? revealed.value.filter(player=>clock.value+serverOffset-Date.parse(player.location.updated_at)<=180000) : [])])
function closeScanner() { scannerId.value=null; revealed.value=[]; scanVersion++; clearInterval(scannerPoll); scanAbort?.abort(); scannerBusy=false }
async function scanTeams() {
  if(!scannerValid.value) { closeScanner(); return }
  if(scannerBusy) return
  const request=scanVersion, id=scannerId.value; scannerBusy=true; scanAbort=new AbortController()
  try { const data=await api('/api/scanners/'+id+'/locations',{signal:scanAbort.signal}); if(request===scanVersion && scannerValid.value) { revealed.value=data.locations; serverOffset=Date.parse(data.server_now)-Date.now(); scannerError.value='' } }
  catch(e:any) { if(request===scanVersion) { closeScanner(); scannerError.value=e.message || 'Scannerverbinding verbroken. Open de scanner opnieuw.' } }
  finally { if(request===scanVersion) scannerBusy=false }
}
function action(object:any) {
  if(object.type!=='SCANNER_POINT') { emit('action',object); return }
  closeScanner(); scannerError.value=''; scannerId.value=object.id
  if(!scannerValid.value) { closeScanner(); scannerError.value='Ga met goede GPS binnen de scannercirkel staan tijdens de lopende ronde.'; return }
  scanTeams(); scannerPoll=window.setInterval(scanTeams,5000)
}
watch(scannerValid,valid=>{ if(!valid && scannerId.value) closeScanner() })
watch(selectedId,()=>{ closeScanner(); scannerError.value='' })
watch(()=>props.initialObject, object=>{ if(object) choose(object) },{immediate:true})
onBeforeUnmount(()=>{closeScanner();clearInterval(tick)})
const typeLabel = (object: any) => categories.find(category => category.id === object.type)?.label || 'Spelpunt'
function distance(object: any) {
  if (!own.value) return null
  const radians = (value: number) => value * Math.PI / 180
  const a = Math.sin(radians(object.latitude - own.value.lat) / 2) ** 2 + Math.cos(radians(own.value.lat)) * Math.cos(radians(object.latitude)) * Math.sin(radians(object.longitude - own.value.lng) / 2) ** 2
  return 6371000 * 2 * Math.asin(Math.sqrt(Math.min(1, a)))
}
const nearby = computed(() => [...visible.value].sort((a, b) => (distance(a) ?? Infinity) - (distance(b) ?? Infinity)))
function distanceLabel(object: any) {
  const meters = distance(object)
  return meters === null ? 'Afstand wacht op GPS' : meters < 1000 ? `${Math.round(meters)} m hemelsbreed` : `${(meters / 1000).toFixed(1)} km hemelsbreed`
}
function choose(object: any, move = false) {
  selectedId.value = object.id
  expanded.value = true
  if (move) map.value?.focusObject(object)
}
function locate() { if (own.value && !props.gpsProblem) map.value?.recenter(); else emit('retryGps') }
watch(filter, () => { selectedId.value = null })
</script>

<template>
  <section class="field-radar" aria-label="Spelkaart">
    <header class="radar-heading"><div><p class="eyebrow">ONTDEK HET SPEELVELD</p><h1>Radar</h1></div><span class="gps-state" :class="{ problem: gpsProblem }">{{ admin ? 'Ronde-overzicht' : gpsLabel }}</span></header>
    <button v-if="bonus" class="bonus-banner" @click="filter = 'ALL'; choose(bonus, true)">🌈 BONUS: {{ bonus.name }} · 2× volgers per minuut <small>Tot {{ new Date(bonus.bonus_ends_at).toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' }) }} · Bekijk locatie →</small></button>
    <button v-if="goldenDucks.length" class="golden-duck-banner" @click="filter = 'PHYSICAL_DUCK'">✦ {{ goldenDucks.length }} gouden eendje(s) · dubbele punten voor de eerste vinder<small>Laatste 15 minuten: vind een eendje dat nog door niemand gevonden is.</small></button>
    <div class="map-filters" role="group" aria-label="Filter spelpunten">
      <button v-for="category in categories" :key="category.id" :aria-pressed="filter === category.id" @click="filter = category.id">{{ category.label }}</button>
    </div>
    <div class="radar-shell">
      <GameMap ref="map" :play-area="playArea" :objects="visible" :locations="displayLocations" :own-team-id="ownTeamId" :selected-object="selected" @radar-mode="radar = $event" @select="choose($event)" />
      <div v-if="radar" class="radar-rings" aria-hidden="true"><i></i><i></i><i></i></div>
      <button v-if="!admin" class="locate-button" @click="locate"><span aria-hidden="true">◎</span>{{ gpsProblem || !own ? 'GPS inschakelen' : 'Mijn positie' }}</button>
    </div>
    <div v-if="scannerId" class="scanner-banner" role="status">◎ Scanner actief · {{ revealed.length }} team(s) in beeld <button @click="closeScanner">Scanner sluiten</button></div>
    <aside class="point-sheet" aria-label="Spelpunten">
      <button class="sheet-toggle" :aria-expanded="expanded" aria-controls="point-details" @click="expanded = !expanded"><span><strong>{{ selected ? selected.name : `${visible.length} spelpunten` }}</strong><small>{{ selected ? typeLabel(selected) : own ? 'Dichtstbijzijnde eerst' : 'Ontdek punten op de kaart' }}</small></span><span aria-hidden="true">{{ expanded ? '⌄' : '⌃' }}</span></button>
      <div v-if="expanded" id="point-details" class="sheet-content">
        <template v-if="selected">
          <p v-if="selected.golden" class="golden-duck-label" role="status">✦ Gouden eend: +{{ selected.reward_points }} volgers voor de eerste vinder. Daarna geldt de normale beloning.</p>
          <p v-if="selected.completed" class="completed-label" role="status">✓ Voltooid door jouw team</p>
          <p class="point-meta">{{ distanceLabel(selected) }} · Actieradius {{ selected.activation_radius_meters }} m</p>
          <p v-if="selected.type === 'CAPTURE_POINT'" class="point-owner"><span :style="{ background: selected.owner_team_color || '#ffcf6a' }"></span>{{ selected.owner_team_name ? 'In bezit van ' + selected.owner_team_name : 'Onbezet' }}</p>
          <button v-if="admin" class="secondary-action" @click="emit('remove', selected)">Punt verwijderen</button>
          <p v-if="selected.type === 'CAPTURE_POINT'" class="point-meta">De gekleurde cirkel is de capturezone. Blijf binnen deze zone om de vlag te veroveren.</p>
          <p v-if="selected.type === 'CAPTURE_POINT'" class="point-meta">+{{ (selected.points_per_minute || 1) * (selected.bonus_multiplier || 1) }} volger(s) per minuut voor het team dat deze post bezit. <strong v-if="selected.bonus_active">🌈 Tijdelijke bonus: 2× volgers!</strong></p>
          <p v-if="selected.type === 'PHOTO_POINT'" class="point-meta">Maak hier een foto met je team. Binnen de cirkel kun je foto's insturen en bekijken.</p>
          <p v-if="selected.reward_points != null" class="point-meta">Beloning: +{{ selected.reward_points }} volgers{{ selected.type === 'CAPTURE_POINT' ? ' bij verovering' : ' per team' }}.</p><p v-if="selected.type === 'SCANNER_POINT'" class="point-meta">Zie andere teams zolang je hier binnen de cirkel blijft. Geen volgers; het gebruik blijft geheim.</p><p v-if="scannerError" role="status">{{ scannerError }}</p><p v-if="selected.description">{{ selected.description }}</p>
          <div class="point-actions"><button class="secondary-action" @click="selectedId = null">Alle punten</button><button v-if="!admin || selected.type === 'PHOTO_POINT'" class="primary-action" :disabled="selected.type === 'SCANNER_POINT' && (!gameRunning || !recentOwn || (distance(selected) ?? Infinity) > selected.activation_radius_meters || Boolean(scannerId))" @click="action(selected)">{{ selected.type === 'PUZZLE' ? 'Open puzzel' : selected.type === 'CAPTURE_POINT' ? 'Start capture' : selected.type === 'PHOTO_POINT' ? 'Open fotopunt' : selected.type === 'SCANNER_POINT' ? 'Scanner openen' : 'Scan eendje' }}</button></div>
        </template>
        <template v-else>
          <p v-if="!visible.length" class="empty-points">Geen punten in deze categorie. Kies een ander filter of wacht tot de beheerder punten plaatst.</p>
          <button v-for="object in nearby" :key="object.id" class="point-row" :class="{ 'golden-duck': object.golden }" @click="choose(object, true)"><span class="point-symbol" aria-hidden="true" v-html="objectIcon(object.type)"></span><span><strong>{{ object.name }}<span v-if="object.golden" class="golden-duck-label"> · ✦ Goud · 2×</span><span v-if="object.completed" class="completed-label"> · ✓ Voltooid</span></strong><small>{{ typeLabel(object) }} · {{ distanceLabel(object) }}</small></span><span aria-hidden="true">›</span></button>
        </template>
      </div>
    </aside>
  </section>
</template>
