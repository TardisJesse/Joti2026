<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '../api'

type Adjustment = { id: string; team_name: string; points: number; reason: string; admin_name: string; created_at: string }
const props = defineProps<{ gameId?: string; finished: boolean; scores: any[] }>()
const emit = defineEmits<{ updated: [] }>()
const teamId = ref(''), points = ref(50), reason = ref('')
const history = ref<Adjustment[]>([]), busy = ref(false), loading = ref(false)
const error = ref(''), historyError = ref(''), result = ref('')
const teams = computed(() => [...props.scores].sort((a, b) => a.name.localeCompare(b.name)))
const selectedTeam = computed(() => props.scores.find(team => team.team_id === teamId.value))
let historyVersion = 0
let pending: { signature: string; id: string } | null = null

async function loadHistory() {
  const version = ++historyVersion, gameId = props.gameId
  if (!gameId) { history.value = []; loading.value = false; return }
  loading.value = true; historyError.value = ''
  try {
    const rows = await api('/api/admin/games/' + gameId + '/score-adjustments')
    if (version === historyVersion && gameId === props.gameId) history.value = rows
  } catch (e: any) { if (version === historyVersion) historyError.value = e.message }
  finally { if (version === historyVersion) loading.value = false }
}
watch(() => props.gameId, () => {
  teamId.value = ''; reason.value = ''; error.value = ''; result.value = ''; history.value = []; pending = null
  loadHistory()
}, { immediate: true })
watch(() => props.scores.map(team => `${team.team_id}:${team.score}`).join('|'), () => {
  if (props.gameId) loadHistory()
})

async function submit() {
  if (busy.value || !props.gameId || !props.finished) return
  if (!selectedTeam.value) { error.value = 'Kies een team uit deze spelronde.'; return }
  if (!Number.isInteger(points.value) || points.value < 1 || points.value > 100000) { error.value = 'Vul 1 tot en met 100.000 hele punten in.'; return }
  const explanation = reason.value.trim()
  if (explanation.length < 3 || explanation.length > 180) { error.value = 'Geef een reden van 3 tot en met 180 tekens.'; return }
  const gameId = props.gameId, target = teamId.value, amount = points.value
  const signature = JSON.stringify([gameId, target, amount, explanation])
  // Keep this ID after a lost response: retrying cannot award the same points twice.
  if (!pending || pending.signature !== signature) pending = { signature, id: crypto.randomUUID() }
  const requestId = pending.id
  busy.value = true; error.value = ''; result.value = ''
  try {
    const saved: Adjustment = await api('/api/admin/games/' + gameId + '/teams/' + target + '/score-adjustments/' + requestId, {
      method: 'PUT', body: JSON.stringify({ points: amount, reason: explanation }),
    })
    if (gameId !== props.gameId) return
    pending = null; reason.value = ''
    result.value = `+${saved.points} punten bijgeschreven aan ${saved.team_name}.`
    emit('updated')
    await loadHistory()
  } catch (e: any) {
    if (gameId === props.gameId) { error.value = e.message; await loadHistory() }
  } finally { busy.value = false }
}

const timestamp = (value: string) => new Date(value).toLocaleString('nl-NL', { dateStyle: 'short', timeStyle: 'short' })
</script>

<template>
  <section class="score-adjustments" aria-labelledby="score-adjustments-title">
    <p class="eyebrow">GAME MASTER // RECTIFICATIE</p>
    <h2 id="score-adjustments-title">Punten bijschrijven</h2>
    <p>Herstel gemiste punten na afloop van de spelronde. Iedere bijschrijving blijft met reden en beheerder bewaard.</p>
    <p v-if="!gameId" role="status">Kies eerst een spelronde bij Beheer.</p>
    <p v-else-if="!finished" role="status">Punten bijschrijven is beschikbaar zodra deze spelronde is afgelopen.</p>
    <form v-else @submit.prevent="submit">
      <label>Team<select v-model="teamId" required :disabled="busy"><option value="" disabled>Kies een team</option><option v-for="team in teams" :key="team.team_id" :value="team.team_id">{{ team.name }} · {{ team.score }} punten</option></select></label>
      <label>Punten erbij<input v-model.number="points" type="number" min="1" max="100000" step="1" required :disabled="busy" /></label>
      <label class="wide">Reden<textarea v-model="reason" minlength="3" maxlength="180" rows="3" required :disabled="busy" placeholder="Bijvoorbeeld: juiste oplossing door een storing niet geregistreerd" /></label>
      <p v-if="selectedTeam && Number.isInteger(points) && points > 0" class="wide adjustment-preview">{{ selectedTeam.name }}: {{ selectedTeam.score }} → {{ selectedTeam.score + points }} punten (+{{ points }}).</p>
      <button class="primary-action" type="submit" :disabled="busy || !teams.length">{{ busy ? 'Bijschrijven…' : 'Punten bijschrijven' }}</button>
    </form>
    <p v-if="error" class="dialog-error" role="alert">{{ error }}</p>
    <p v-if="result" class="dialog-result success" role="status">{{ result }}</p>
    <h3>Eerdere rectificaties</h3>
    <p v-if="loading" role="status">Rectificaties laden…</p>
    <p v-if="historyError" class="dialog-error" role="alert">{{ historyError }} <button type="button" class="secondary-action" @click="loadHistory">Opnieuw laden</button></p>
    <p v-else-if="!loading && !history.length">Nog geen rectificaties in deze spelronde.</p>
    <ol v-if="history.length" class="adjustment-history"><li v-for="item in history" :key="item.id"><strong>{{ item.team_name }} · {{ item.points > 0 ? '+' : '' }}{{ item.points }} punten</strong><p>{{ item.reason }}</p><small>{{ item.admin_name }} · {{ timestamp(item.created_at) }}</small></li></ol>
    <small v-if="history.length === 200">De laatste 200 rectificaties worden getoond.</small>
  </section>
</template>

<style scoped>
.score-adjustments{margin:20px auto;max-width:960px;padding:24px;background:#0c2335;border:1px solid #355a70;border-radius:18px;color:#e2f4ff}.score-adjustments h2{margin:8px 0 12px}.score-adjustments h3{margin:26px 0 12px}.score-adjustments p{line-height:1.6;overflow-wrap:anywhere}.score-adjustments form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:20px}.score-adjustments label{display:grid;gap:8px}.score-adjustments input,.score-adjustments select,.score-adjustments textarea{width:100%;min-height:48px;padding:12px;border:1px solid #537084;border-radius:10px;background:#051727;color:#e8f9ff;font:inherit}.score-adjustments .wide{grid-column:1/-1}.score-adjustments button:disabled{opacity:.5}.adjustment-preview{padding:12px;background:#123c32;border-radius:10px}.adjustment-history{list-style:none;padding:0;display:grid;gap:12px}.adjustment-history li{padding:14px;border:1px solid #355a70;border-radius:12px}.adjustment-history p{margin:8px 0}.adjustment-history small{color:#b9cfdd}.score-adjustments :focus-visible{outline:3px solid #62e8f5;outline-offset:3px}@media(max-width:600px){.score-adjustments{padding:18px}.score-adjustments form{grid-template-columns:1fr}}
</style>
