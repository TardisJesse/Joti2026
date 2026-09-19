<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import maplibregl, { type Map, type Marker } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
const props = defineProps<{ objects: any[]; locations: any[]; editable?: boolean; ownTeamId?: string }>()
const emit = defineEmits<{ place: [coords: { latitude: number; longitude: number }]; radarMode: [active: boolean] }>()
const element = ref<HTMLDivElement | null>(null)
let map: Map | undefined, markers: Marker[] = [], centeredOnGps = false, mapReady = false, automaticCameraMove = false
// Scouting Allart van Heemstede, Lemsterlandhoeve 70, 3137 GM Vlaardingen.
const allartHq = [4.3553432, 51.94281191] as [number, number]
// OpenFreeMap's dark vector style is free and needs no key, account, or billing setup.
const style = 'https://tiles.openfreemap.org/styles/dark'
const glyph = (type: string) => type === 'PUZZLE' ? '◆' : type === 'CAPTURE_POINT' ? '◉' : '🦆'
function ownPlayer() { return props.ownTeamId ? props.locations.find(x => x.team_id === props.ownTeamId && x.location) : undefined }
function playerCenter(player: any): [number, number] { return [player.location.lng, player.location.lat] }
function showRadar() { emit('radarMode', true) }
function releaseRadar() { if (!automaticCameraMove) emit('radarMode', false) }
function draw() {
  if (!map) return
  markers.forEach(marker => marker.remove()); markers = []
  for (const item of props.objects) {
    const pin = document.createElement('button'); pin.className = 'map-pin ' + item.type.toLowerCase(); pin.textContent = glyph(item.type); pin.title = item.name
    markers.push(new maplibregl.Marker({ element: pin, anchor: 'bottom' }).setLngLat([item.longitude, item.latitude]).setPopup(new maplibregl.Popup({ offset: 25 }).setText(item.name + ' · ' + item.activation_radius_meters + 'm')).addTo(map))
  }
  for (const player of props.locations) {
    if (!player.location) continue
    const pin = document.createElement('span'); pin.className = 'player-pin' + (player.team_id === props.ownTeamId ? ' is-current-player' : ''); pin.textContent = '◉'; pin.title = player.team_id === props.ownTeamId ? 'Eigen GPS-positie' : player.name
    markers.push(new maplibregl.Marker({ element: pin }).setLngLat([player.location.lng, player.location.lat]).setPopup(new maplibregl.Popup({ offset: 12 }).setText(player.name)).addTo(map))
  }
}
function centerOnFirstGps() {
  const player = ownPlayer()
  if (player?.location && map && mapReady && !centeredOnGps) {
    centeredOnGps = true
    automaticCameraMove = true
    showRadar()
    map.flyTo({ center: playerCenter(player), zoom: 17, duration: 750, essential: true })
    map.once('moveend', () => { automaticCameraMove = false })
  }
}
onMounted(() => {
  const player = ownPlayer()
  centeredOnGps = Boolean(player)
  map = new maplibregl.Map({ container: element.value!, style, center: player ? playerCenter(player) : allartHq, zoom: player ? 17 : 15 })
  map.addControl(new maplibregl.NavigationControl(), 'top-right')
  map.on('load', () => {
    mapReady = true
    const pin = document.createElement('span'); pin.className = 'hq-pin'; pin.textContent = '⌂'; pin.title = 'Allart van Heemstede HQ'
    new maplibregl.Marker({ element: pin, anchor: 'bottom' }).setLngLat(allartHq).setPopup(new maplibregl.Popup({ offset: 16 }).setText('Allart van Heemstede HQ · Lemsterlandhoeve 70')).addTo(map!)
    draw()
    if (player) showRadar(); else centerOnFirstGps()
  })
  map.on('click', event => { if (props.editable) emit('place', { latitude: event.lngLat.lat, longitude: event.lngLat.lng }) })
  map.on('dragstart', releaseRadar)
  map.on('zoomstart', releaseRadar)
  map.on('rotatestart', releaseRadar)
})
watch(() => [props.objects, props.locations], () => { draw(); centerOnFirstGps() }, { deep: true })
onBeforeUnmount(() => { emit('radarMode', false); map?.remove() })
</script>
<template><div ref="element" class="live-map" :class="{ editable }"></div></template>
