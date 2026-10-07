<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import maplibregl, { type Map, type Marker, type GeoJSONSource } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { objectIcon } from '../icons'
const props = defineProps<{ objects: any[]; locations: any[]; editable?: boolean; ownTeamId?: string; selectedObject?: any }>()
const emit = defineEmits<{ place: [coords: { latitude: number; longitude: number }]; radarMode: [active: boolean]; select: [object: any] }>()
const element = ref<HTMLDivElement | null>(null)
let map: Map | undefined, markers: Marker[] = [], centeredOnGps = false, mapReady = false, automaticCameraMove = false
let explored = false, observer: ResizeObserver | undefined
// Scouting Allart van Heemstede, Lemsterlandhoeve 70, 3137 GM Vlaardingen.
const allartHq = [4.3553432, 51.94281191] as [number, number]
// OpenFreeMap's dark vector style is free and needs no key, account, or billing setup.
// Demo: attribution UI hidden at the user's request. Restore visible attribution before public release.
// Map credits: OpenFreeMap https://openfreemap.org/ · © OpenMapTiles https://openmaptiles.org/
// Data: © OpenStreetMap contributors https://www.openstreetmap.org/copyright
const style = 'https://tiles.openfreemap.org/styles/dark'
function drawCaptureArea() {
  if (!mapReady || !map) return
  const point = props.selectedObject
  const features: any[] = []
  if (['CAPTURE_POINT', 'PHOTO_POINT'].includes(point?.type) && Number(point.activation_radius_meters) > 0) {
    // Destination-point formula: the radius is in metres, independent of zoom.
    const angular = Number(point.activation_radius_meters) / 6371000
    const lat = point.latitude * Math.PI / 180, lng = point.longitude * Math.PI / 180
    const ring: number[][] = []
    for (let i = 0; i < 64; i++) {
      const bearing = i * 2 * Math.PI / 64
      const y = Math.asin(Math.sin(lat) * Math.cos(angular) + Math.cos(lat) * Math.sin(angular) * Math.cos(bearing))
      const x = lng + Math.atan2(Math.sin(bearing) * Math.sin(angular) * Math.cos(lat), Math.cos(angular) - Math.sin(lat) * Math.sin(y))
      ring.push([x * 180 / Math.PI, y * 180 / Math.PI])
    }
    ring.push([...ring[0]])
    features.push({ type: 'Feature', properties: { color: point.owner_team_color || '#ffcf6a' }, geometry: { type: 'Polygon', coordinates: [ring] } })
  }
  const data = { type: 'FeatureCollection' as const, features }
  const source = map.getSource('capture-area') as GeoJSONSource | undefined
  if (source) source.setData(data)
  else {
    map.addSource('capture-area', { type: 'geojson', data })
    map.addLayer({ id: 'capture-area-fill', type: 'fill', source: 'capture-area', paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.18 } })
    map.addLayer({ id: 'capture-area-border', type: 'line', source: 'capture-area', paint: { 'line-color': ['get', 'color'], 'line-width': 3, 'line-opacity': 0.95 } })
  }
}
function ownPlayer() { return props.ownTeamId ? props.locations.find(x => x.team_id === props.ownTeamId && x.location) : undefined }
function playerCenter(player: any): [number, number] { return [player.location.lng, player.location.lat] }
function showRadar() { if (!explored) emit('radarMode', true) }
function releaseRadar(event?: { originalEvent?: unknown }) {
  if (automaticCameraMove && !event?.originalEvent) return
  explored = true
  emit('radarMode', false)
}
function recenter() {
  const player = ownPlayer()
  if (!map || !player) return
  explored = false
  centeredOnGps = true
  automaticCameraMove = true
  map.jumpTo({ center: playerCenter(player), zoom: 17, bearing: 0, pitch: 0 })
  automaticCameraMove = false
  showRadar()
}
function focusObject(object: any) {
  explored = true
  emit('radarMode', false)
  map?.jumpTo({ center: [object.longitude, object.latitude], zoom: 17 })
}
defineExpose({ recenter, focusObject })
function draw() {
  if (!map) return
  markers.forEach(marker => marker.remove()); markers = []
  for (const item of props.objects) {
    const pin = document.createElement('button'); pin.type = 'button'; pin.className = 'map-pin ' + item.type.toLowerCase(); pin.innerHTML = objectIcon(item.type); pin.title = item.name
    pin.setAttribute('aria-label', item.name)
    if (item.type === 'CAPTURE_POINT') { pin.style.background = item.owner_team_color || '#ffcf6a'; pin.style.color = '#031426'; pin.title = item.name + ' · ' + (item.owner_team_name || 'Onbezet') }
    pin.addEventListener('click', event => { event.stopPropagation(); emit('select', item) })
    markers.push(new maplibregl.Marker({ element: pin, anchor: item.type === 'CAPTURE_POINT' ? 'center' : 'bottom' }).setLngLat([item.longitude, item.latitude]).setPopup(new maplibregl.Popup({ offset: 25 }).setText(item.name + ' · ' + item.activation_radius_meters + 'm')).addTo(map))
    pin.setAttribute('aria-label', item.name)
  }
  for (const player of props.locations) {
    if (!player.location) continue
    const name = player.team_name || player.name || 'Team'
    const pin = document.createElement('button'); pin.type = 'button'; pin.className = 'player-pin' + (player.team_id === props.ownTeamId ? ' is-current-player' : ''); pin.title = name; pin.setAttribute('aria-label', name)
    if (player.profile_image) {
      const image = document.createElement('img'); image.src = player.profile_image; image.alt = ''; pin.appendChild(image)
    } else pin.textContent = name.slice(0, 2).toUpperCase()
    const marker = new maplibregl.Marker({ element: pin }).setLngLat([player.location.lng, player.location.lat]).setPopup(new maplibregl.Popup({ offset: 28 }).setText(name)).addTo(map)
    pin.setAttribute('aria-label', name)
    pin.addEventListener('click', event => { event.stopPropagation(); marker.togglePopup() })
    markers.push(marker)
  }
}
function centerOnFirstGps() {
  const player = ownPlayer()
  if (player?.location && map && mapReady && !centeredOnGps && !explored) {
    centeredOnGps = true
    automaticCameraMove = true
    map.jumpTo({ center: playerCenter(player), zoom: 17 })
    automaticCameraMove = false
    showRadar()
  }
}
onMounted(() => {
  const player = ownPlayer()
  centeredOnGps = Boolean(player)
  map = new maplibregl.Map({ container: element.value!, style, center: player ? playerCenter(player) : allartHq, zoom: player ? 17 : 15, attributionControl: false })
  map.addControl(new maplibregl.NavigationControl(), 'top-right')
  map.on('load', () => {
    mapReady = true
    const pin = document.createElement('span'); pin.className = 'hq-pin'; pin.textContent = '⌂'; pin.title = 'Allart van Heemstede HQ'
    new maplibregl.Marker({ element: pin, anchor: 'bottom' }).setLngLat(allartHq).setPopup(new maplibregl.Popup({ offset: 16 }).setText('Allart van Heemstede HQ · Lemsterlandhoeve 70')).addTo(map!)
    draw(); drawCaptureArea()
    if (player) showRadar(); else centerOnFirstGps()
  })
  map.on('click', event => { if (props.editable) emit('place', { latitude: event.lngLat.lat, longitude: event.lngLat.lng }) })
  map.on('dragstart', releaseRadar)
  map.on('zoomstart', releaseRadar)
  map.on('rotatestart', releaseRadar)
  map.on('pitchstart', releaseRadar)
  observer = new ResizeObserver(() => map?.resize())
  observer.observe(element.value!)
})
watch(() => [props.objects, props.locations, props.selectedObject], () => {
  drawCaptureArea()
  draw(); centerOnFirstGps()
  const player = ownPlayer()
  if (mapReady && centeredOnGps && !explored && player && map) {
    automaticCameraMove = true
    map.jumpTo({ center: playerCenter(player) })
    automaticCameraMove = false
  }
}, { deep: true })
onBeforeUnmount(() => { observer?.disconnect(); emit('radarMode', false); map?.remove() })
</script>
<template><div ref="element" class="live-map" :class="{ editable }"></div></template>
