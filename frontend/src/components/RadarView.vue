<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import GameMap from './GameMap.vue'
const props = defineProps<{ objects: any[]; locations: any[]; ownTeamId?: string; admin: boolean; gpsLabel: string; gpsProblem: boolean }>()
const emit = defineEmits<{ retryGps: []; action: [object: any] }>()
const map = ref<InstanceType<typeof GameMap>>()
const radar = ref(false), expanded = ref(false), selectedId = ref<string | null>(null), filter = ref('ALL')
const categories = [{ id: 'ALL', label: 'Alles' }, { id: 'PUZZLE', label: 'Puzzels' }, { id: 'PHYSICAL_DUCK', label: 'Eendjes' }, { id: 'CAPTURE_POINT', label: 'Posten' }]
const visible = computed(() => props.objects.filter(object => filter.value === 'ALL' || object.type === filter.value))
const selected = computed(() => visible.value.find(object => object.id === selectedId.value))
const own = computed(() => props.locations.find(player => props.ownTeamId && player.team_id === props.ownTeamId)?.location)
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
    <div class="map-filters" role="group" aria-label="Filter spelpunten">
      <button v-for="category in categories" :key="category.id" :aria-pressed="filter === category.id" @click="filter = category.id">{{ category.label }}</button>
    </div>
    <div class="radar-shell">
      <GameMap ref="map" :objects="visible" :locations="locations" :own-team-id="ownTeamId" @radar-mode="radar = $event" @select="choose($event)" />
      <div v-if="radar" class="radar-rings" aria-hidden="true"><i></i><i></i><i></i></div>
      <button v-if="!admin" class="locate-button" @click="locate"><span aria-hidden="true">◎</span>{{ gpsProblem || !own ? 'GPS inschakelen' : 'Mijn positie' }}</button>
    </div>
    <aside class="point-sheet" aria-label="Spelpunten">
      <button class="sheet-toggle" :aria-expanded="expanded" aria-controls="point-details" @click="expanded = !expanded"><span><strong>{{ selected ? selected.name : `${visible.length} spelpunten` }}</strong><small>{{ selected ? typeLabel(selected) : own ? 'Dichtstbijzijnde eerst' : 'Ontdek punten op de kaart' }}</small></span><span aria-hidden="true">{{ expanded ? '⌄' : '⌃' }}</span></button>
      <div v-if="expanded" id="point-details" class="sheet-content">
        <template v-if="selected">
          <p class="point-meta">{{ distanceLabel(selected) }} · Actieradius {{ selected.activation_radius_meters }} m</p>
          <p v-if="selected.description">{{ selected.description }}</p>
          <div class="point-actions"><button class="secondary-action" @click="selectedId = null">Alle punten</button><button v-if="!admin" class="primary-action" @click="emit('action', selected)">{{ selected.type === 'PUZZLE' ? 'Open puzzel' : selected.type === 'CAPTURE_POINT' ? 'Start capture' : 'Scan eendje' }}</button></div>
        </template>
        <template v-else>
          <p v-if="!visible.length" class="empty-points">Geen punten in deze categorie. Kies een ander filter of wacht tot de beheerder punten plaatst.</p>
          <button v-for="object in nearby" :key="object.id" class="point-row" @click="choose(object, true)"><span class="point-symbol" aria-hidden="true">{{ object.type === 'PUZZLE' ? '◆' : object.type === 'CAPTURE_POINT' ? '◉' : '♧' }}</span><span><strong>{{ object.name }}</strong><small>{{ typeLabel(object) }} · {{ distanceLabel(object) }}</small></span><span aria-hidden="true">›</span></button>
        </template>
      </div>
    </aside>
  </section>
</template>
