// Exercise the real SFC setup with a MapLibre double; no browser or live GPS needed.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const { parse, compileScript } = require('vue/compiler-sfc')
const ts = require('typescript')
const source = compileScript(parse(fs.readFileSync('src/components/GameMap.vue', 'utf8')).descriptor, { id: 'map-test' }).content
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true } }).outputText

function mount(locations = []) {
  let mounted, update, dispose, map, exposed
  const events = [], pins = []
  class FakeMap {
    constructor(options) { map = this; this.options = options; this.handlers = {}; this.moves = []; this.sources = {}; this.layers = [] }
    getSource(name) { return this.sources[name] }
    addSource(name, source) { this.sources[name] = { data: source.data, setData(data) { this.data = data } } }
    addLayer(layer) { this.layers.push(layer) }
    on(name, fn) { (this.handlers[name] ||= []).push(fn) }
    fire(name, data = {}) { (this.handlers[name] || []).forEach(fn => fn(data)) }
    project([lng, lat]) { return { x: 200 + (lng - 4.35) * 10000, y: 200 - (lat - 51.94) * 10000 } }
    addControl() {}
    jumpTo(options) { this.moves.push(options); this.fire('zoomstart'); this.fire('moveend') }
    resize() {}
    remove() {}
  }
  class Marker {
    constructor(options) { pins.push(options.element) }
    setLngLat() { return this } setPopup() { return this } addTo() { return this } remove() {}
  }
  class Popup { setText() { return this } }
  const module = { exports: {} }
  vm.runInNewContext(code, {
    exports: module.exports, module,
    require: name => name === 'vue' ? { defineComponent: value => value, ref: value => ({ value }), onMounted: fn => mounted = fn, onBeforeUnmount: fn => dispose = fn, watch: (_, fn) => update = fn } : name === 'maplibre-gl' ? { Map: FakeMap, Marker, Popup, NavigationControl: class {}, AttributionControl: class {} } : { objectIcon: type => `<svg>${type}</svg>` },
    document: { createElement: () => ({ style: {}, handlers: {}, children: [], appendChild(child) { this.children.push(child) }, setAttribute() {}, addEventListener(name, fn) { this.handlers[name] = fn } }) },
    ResizeObserver: class { observe() {} disconnect() {} },
  })
  const props = { locations, ownTeamId: 'own', objects: [{ id: 'puzzle', name: 'Testpuzzel', type: 'PUZZLE', longitude: 4.3, latitude: 51.9 }] }
  const state = module.exports.default.setup(props, { expose: value => exposed = value, emit: (...args) => events.push(args) })
  mounted()
  return { state, props, events, pins, map, update: () => update(), load: () => map.fire('load'), dispose: () => dispose(), get actions() { return exposed } }
}
const fix = { team_id: 'own', name: 'team-internal-id', team_name: 'Testteam', profile_image: 'data:image/jpeg;base64,test', location: { lat: 51.94, lng: 4.35 } }
const other = { team_id: 'other', location: { lat: 52, lng: 5 } }
const app = mount([other, fix])
assert.equal(app.map.options.center[0], fix.location.lng, 'Start on the own team, not the first other team')
app.load()
const portrait = app.pins.find(pin => pin.className?.includes('is-current-player'))
assert.equal(portrait.title, 'Testteam', 'Show team names instead of internal usernames')
assert.equal(portrait.children[0].src, fix.profile_image, 'Photo sits inside the player marker')
app.props.selectedObject = { type: 'CAPTURE_POINT', latitude: 51.94, longitude: 4.35, activation_radius_meters: 80 }
app.update()
const circle = app.map.sources['capture-area'].data.features[0].geometry.coordinates[0]
assert.equal(circle.length, 65)
assert.equal(circle[0][0], circle[64][0])
assert.ok(Math.abs((circle[0][1] - 51.94) * Math.PI / 180 * 6371000 - 80) < 0.01, 'Circle radius uses actual metres')
app.props.selectedObject = undefined; app.update()
assert.equal(app.map.sources['capture-area'].data.features.length, 0, 'Deselecting clears the capture zone')
assert.deepEqual(app.events.at(-1), ['radarMode', true])
app.map.fire('zoomstart', { originalEvent: {} })
const moves = app.map.moves.length
app.props.locations = [{ ...fix, location: { lat: 51.95, lng: 4.36 } }]
app.update()
assert.equal(app.map.moves.length, moves, 'GPS refresh must not reset manual zoom/pan')
assert.deepEqual(app.events.at(-1), ['radarMode', false])
app.actions.recenter()
assert.equal(app.map.moves.at(-1).center[0], 4.36)
assert.deepEqual(app.events.at(-1), ['radarMode', true])
app.actions.focusObject(app.props.objects[0])
assert.deepEqual(app.events.at(-1), ['radarMode', false])
app.pins.find(pin => pin.className?.includes('map-pin')).handlers.click({ stopPropagation() {} })
assert.equal(app.events.at(-1)[0], 'select')
app.props.objects.push({ id: 'tower', type: 'CAPTURE_POINT', name: 'Mast', latitude: 51.94, longitude: 4.35, activation_radius_meters: 40 })
app.props.selectedObject = undefined; app.update()
assert.equal(app.map.sources['capture-area'].data.features.length, 1, 'Capture territories are visible without selecting a point')
app.props.selectedObject = app.props.objects[1]; app.update()
assert.equal(app.map.sources['capture-area'].data.features.length, 1, 'Selecting a capture does not duplicate its territory')
app.props.selectedObject = { id: 'photo', type: 'PHOTO_POINT', latitude: 51.941, longitude: 4.351, activation_radius_meters: 35 }; app.update()
assert.equal(app.map.sources['capture-area'].data.features.length, 2, 'Photo selection keeps the capture territories visible')
assert.equal(app.map.sources['capture-area'].data.features[1].properties.color, '#ba9aff')
app.dispose()

const waiting = mount()
waiting.map.fire('dragstart', { originalEvent: {} })
waiting.props.locations = [fix]
waiting.load(); waiting.update()
assert.equal(waiting.map.moves.length, 0, 'Late GPS must not steal the camera after exploration')
assert.equal(waiting.events.some(event => event[1] === true), false)
waiting.dispose()

const late = mount()
late.load(); late.props.locations = [fix]; late.update()
assert.equal(late.map.moves.at(-1).center[0], 4.35)
assert.deepEqual(late.events.at(-1), ['radarMode', true])
late.dispose()
console.log('Map behavior passed: own GPS, late GPS, manual exploration, recenter, selection and cleanup.')
const boundary = { type: 'Polygon', coordinates: [[[4.34,51.93],[4.36,51.93],[4.36,51.95],[4.34,51.93]]] }
app.props.playArea = boundary
app.update()
assert.match(app.state.fogStyle.value.maskImage, /radial-gradient\(circle at/, 'The play area uses a circular feathered mask')
assert.ok(!app.map.layers.some(layer => layer.id === 'play-area-border'), 'No hard play-area border is drawn')
const maskBeforeMove = app.state.fogStyle.value.maskImage
app.map.project = ([lng, lat]) => ({ x: 300 + (lng - 4.35) * 20000, y: 300 - (lat - 51.94) * 20000 })
app.map.fire('move')
assert.notEqual(app.state.fogStyle.value.maskImage, maskBeforeMove, 'Fog follows map panning and zoom')
app.props.playArea = undefined
app.update()
assert.equal(app.state.fogStyle.value, null, 'Changing to a round without a boundary clears the fog')
