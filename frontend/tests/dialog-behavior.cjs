const assert = require('node:assert/strict')
const fs = require('node:fs')
const vm = require('node:vm')
const { parse, compileScript } = require('@vue/compiler-sfc')
const ts = require('typescript')
const source = compileScript(parse(fs.readFileSync('src/components/GameActionDialog.vue', 'utf8')).descriptor, { id: 'dialog-test' }).content
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true } }).outputText
let exposed, dispose, timer, nextResponse
const events = [], calls = [], moduleObject = { exports: {} }
vm.runInNewContext(code, {
  exports: moduleObject.exports, module: moduleObject,
  require: name => name === 'vue' ? { defineComponent: x => x, ref: value => ({ value }), computed: fn => ({ get value() { return fn() } }), onBeforeUnmount: fn => dispose = fn } : { api: async (path, options) => { calls.push({ path, options }); if (nextResponse instanceof Error) throw nextResponse; return nextResponse } },
  window: { setTimeout: fn => { timer = fn; return 1 } }, clearTimeout: () => { timer = null },
})
const state = moduleObject.exports.default.setup({}, { expose: x => exposed = x, emit: (...args) => events.push(args) })
let opened = false
state.dialog.value = { showModal() { opened = true }, close() { opened = false } }
async function run() {
  nextResponse = { question: 'Wat is het geheime woord?' }
  await exposed.open('puzzle', { id: 'p1', name: 'Raadsel' })
  assert.equal(opened, true)
  assert.equal(state.question.value, nextResponse.question)
  await state.submit()
  assert.ok(state.error.value, 'Empty answer has inline validation')
  state.input.value = ' fout '
  nextResponse = { correct: false, points: 0 }; await state.submit()
  assert.equal(state.success.value, false)
  assert.ok(state.result.value.includes('Probeer'))
  assert.equal(JSON.parse(calls.at(-1).options.body).answer, 'fout')
  nextResponse = { correct: true, points: 50 }; await state.submit()
  assert.equal(state.success.value, true)
  assert.ok(state.result.value.includes('50'))
  await exposed.open('scan')
  state.input.value = 'duck-code'; nextResponse = new Error('Ongeldige code'); await state.submit()
  assert.equal(state.error.value, 'Ongeldige code')
  nextResponse = { name: 'Eend', points: 20 }; await state.submit()
  assert.equal(calls.at(-1).path, '/api/ducks/scan')
  assert.equal(state.success.value, true)
  await exposed.open('capture', { id: 'c1', name: 'Vlag', activation_radius_meters: 40 })
  nextResponse = { started: true }; await state.submit()
  assert.equal(state.capturing.value, true)
  state.close(); assert.equal(opened, false)
  nextResponse = { state: 'CAPTURING' }; await timer()
  assert.equal(state.activeCapture.value, 'c1', 'Closing the window keeps capture polling alive')
  nextResponse = { state: 'COMPLETED' }; await timer()
  assert.equal(state.activeCapture.value, null)
  assert.ok(events.some(event => event[0] === 'notice' && event[1].includes('veroverd')))
  dispose(); assert.equal(timer, null)
  console.log('Dialog behavior passed: puzzle question, validation, retry, success, scan failure/success, capture after close and cleanup.')
}
run().catch(error => { console.error(error); process.exitCode = 1 })
