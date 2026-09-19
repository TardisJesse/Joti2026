<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import maplibregl, { type Map, type Marker } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
const props = defineProps<{ objects: any[]; locations: any[]; editable?: boolean; ownTeamId?: string }>()
const emit = defineEmits<{ place: [coords: { latitude: number; longitude: number }] }>()
const element = ref<HTMLDivElement | null>(null)
let map: Map | undefined, markers: Marker[] = [], centeredOnGps = false
// Scouting Allart van Heemstede, Lemsterlandhoeve 70, 3137 GM Vlaardingen.
const allartHq = [4.3553432, 51.94281191] as [number, number]
const style = {
  version: 8,
  sources: {
    cartoDark: {
      type: 'raster',
      tiles: [
        'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
      ],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors © CARTO',
    },
  },
  layers: [{ id: 'cyber-dark-base', type: 'raster', source: 'cartoDark' }],
} as any
const glyph = (type: string) => type === 'PUZZLE' ? '◆' : type === 'CAPTURE_POINT' ? '◉' : '🦆'
function draw() {
  if (!map) return
  markers.forEach(marker => marker.remove()); markers = []
  for (const item of props.objects) {
    const pin = document.createElement('button'); pin.className = 'map-pin ' + item.type.toLowerCase(); pin.textContent = glyph(item.type); pin.title = item.name
    markers.push(new maplibregl.Marker({ element: pin, anchor: 'bottom' }).setLngLat([item.longitude, item.latitude]).setPopup(new maplibregl.Popup({ offset: 25 }).setText(item.name + ' · ' + item.activation_radius_meters + 'm')).addTo(map))
  }
  for (const player of props.locations) {
    if (!player.location) continue
    const pin = document.createElement('span'); pin.className = 'player-pin' + (player.team_id === props.ownTeamId ? ' is-current-player' : ''); pin.textContent = '◉'; pin.title = player.team_id === props.ownTeamId ? 'Jij' : player.name
    markers.push(new maplibregl.Marker({ element: pin }).setLngLat([player.location.lng, player.location.lat]).setPopup(new maplibregl.Popup({ offset: 12 }).setText(player.name)).addTo(map))
  }
}
function centerOnFirstGps() {
  const player = props.ownTeamId ? props.locations.find(x => x.team_id === props.ownTeamId && x.location) : undefined
  if (player?.location && map && !centeredOnGps) {
    centeredOnGps = true
    map.flyTo({ center: [player.location.lng, player.location.lat], zoom: 17, duration: 750, essential: true })
  }
}
onMounted(() => {
  map = new maplibregl.Map({ container: element.value!, style, center: allartHq, zoom: 15 })
  map.addControl(new maplibregl.NavigationControl(), 'top-right')
  map.on('load', () => {
    const pin = document.createElement('span'); pin.className = 'hq-pin'; pin.textContent = '⌂'; pin.title = 'Allart van Heemstede HQ'
    new maplibregl.Marker({ element: pin, anchor: 'bottom' }).setLngLat(allartHq).setPopup(new maplibregl.Popup({ offset: 16 }).setText('Allart van Heemstede HQ · Lemsterlandhoeve 70')).addTo(map!)
    draw(); centerOnFirstGps()
  })
  map.on('click', event => { if (props.editable) emit('place', { latitude: event.lngLat.lat, longitude: event.lngLat.lng }) })
})
watch(() => [props.objects, props.locations], () => { draw(); centerOnFirstGps() }, { deep: true })
onBeforeUnmount(() => map?.remove())
</script>
<template><div ref="element" class="live-map" :class="{ editable }"></div></template>
