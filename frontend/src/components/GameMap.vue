<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import maplibregl, { type Map, type Marker } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
const props = defineProps<{ objects: any[]; locations: any[]; editable?: boolean }>()
const emit = defineEmits<{ place: [coords: { latitude: number; longitude: number }] }>()
const element = ref<HTMLDivElement | null>(null)
let map: Map | undefined, markers: Marker[] = []
const style = { version: 8, sources: { osm: { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: '© OpenStreetMap contributors' } }, layers: [{ id: 'osm', type: 'raster', source: 'osm' }] } as any
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
    const pin = document.createElement('span'); pin.className = 'player-pin'; pin.textContent = '●'; pin.title = player.name
    markers.push(new maplibregl.Marker({ element: pin }).setLngLat([player.location.lng, player.location.lat]).setPopup(new maplibregl.Popup({ offset: 12 }).setText(player.name)).addTo(map))
  }
}
function focus() {
  const source = props.locations.find(x => x.location) || props.objects[0]
  if (source && map) map.flyTo({ center: source.location ? [source.location.lng, source.location.lat] : [source.longitude, source.latitude], zoom: 17, essential: true })
}
onMounted(() => {
  map = new maplibregl.Map({ container: element.value!, style, center: [4.63, 52.349], zoom: 14 })
  map.addControl(new maplibregl.NavigationControl(), 'top-right')
  map.on('load', () => { draw(); focus() })
  map.on('click', event => { if (props.editable) emit('place', { latitude: event.lngLat.lat, longitude: event.lngLat.lng }) })
})
watch(() => [props.objects, props.locations], () => { draw(); focus() }, { deep: true })
onBeforeUnmount(() => map?.remove())
</script>
<template><div ref="element" class="live-map" :class="{ editable }"></div></template>
