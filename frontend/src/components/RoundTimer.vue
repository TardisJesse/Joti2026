<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '../api'
const props = defineProps<{ game?: any; countdown: string }>()
const emit = defineEmits<{ updated: [] }>()
const minutes = ref(60), busy = ref(false), error = ref(''), result = ref('')
const delayedStart = ref(false), startMinutes = ref(5)
const startPending = computed(() => props.game?.status === 'READY' && Boolean(props.game?.scheduled_start_at))
const canSchedule = computed(() => ['READY', 'DRAFT'].includes(props.game?.status))
const playingTimer = computed(() => !startPending.value && (props.game?.ends_at || props.game?.timer_remaining_seconds != null))
watch([() => props.game?.id, () => props.game?.scheduled_start_at], () => {
  delayedStart.value = startPending.value
  if (startPending.value && props.game.timer_remaining_seconds != null) minutes.value = props.game.timer_remaining_seconds / 60
}, { immediate: true })
watch(() => props.game?.id, () => { error.value = ''; result.value = '' })
async function change(gameId: string, remove = false) {
  if (busy.value) return
  if (!remove && (!Number.isInteger(minutes.value) || minutes.value < 1 || minutes.value > 1440)) { error.value = 'Kies tussen 1 en 1440 hele minuten.'; return }
  const schedule = !remove && delayedStart.value && canSchedule.value
  if (schedule && (!Number.isInteger(startMinutes.value) || startMinutes.value < 1 || startMinutes.value > 1440)) { error.value = 'Kies een starttijd tussen 1 en 1440 hele minuten.'; return }
  busy.value = true; error.value = ''; result.value = ''
  try {
    const startTimer = schedule || (remove && startPending.value)
    await api('/api/admin/games/' + gameId + (startTimer ? '/start-timer' : '/timer'), {
      method: remove ? 'DELETE' : 'PUT',
      ...(remove ? {} : { body: JSON.stringify(schedule
        ? { delay_seconds: startMinutes.value * 60, play_duration_seconds: minutes.value * 60 }
        : { duration_seconds: minutes.value * 60 }) }),
    })
    result.value = remove ? (startTimer ? 'Starttimer geannuleerd. De ronde is nog niet gestart.' : 'Timer verwijderd.') : schedule
      ? `Groene starttimer gestart. Over ${startMinutes.value} minuten begint de ronde met ${minutes.value} minuten speeltijd.`
      : 'Timer gestart voor alle spelers.'
    emit('updated')
  } catch (e: any) { error.value = e.message }
  finally { busy.value = false }
}
</script>
<template>
  <section class="admin-page timer-page"><p class="eyebrow">GAME MASTER // TIMER</p><h1>Speltimer</h1>
    <p v-if="!game" class="helper">Maak of kies eerst een spelronde bij Beheer.</p>
    <template v-else><p class="helper">Spelronde: {{ game.code || game.name }}</p>
      <div v-if="startPending || playingTimer" class="timer-preview" :class="{ 'is-start-timer': startPending }"><strong>{{ countdown }}</strong><span>{{ startPending ? 'Tot de start' : game.status === 'FINISHED' ? 'Spel afgelopen' : game.status === 'PAUSED' ? 'Gepauzeerd' : 'Resterende speeltijd' }}</span><small v-if="startPending">Daarna {{ game.timer_remaining_seconds / 60 }} minuten speeltijd.</small></div>
      <form class="timer-form" @submit.prevent="change(game.id)">
        <label>Speeltijd in minuten<input v-model.number="minutes" type="number" min="1" max="1440" step="1" required :disabled="busy" /></label>
        <label v-if="canSchedule" class="start-timer-toggle"><input v-model="delayedStart" type="checkbox" :disabled="busy" />Eerst een groene starttimer</label>
        <label v-if="delayedStart && canSchedule">Start over (minuten)<input v-model.number="startMinutes" type="number" min="1" max="1440" step="1" required :disabled="busy" /></label>
        <p v-if="delayedStart && canSchedule">Iedereen ziet een groene countdown en kan alvast het speelveld in. Spelacties blijven vergrendeld. Bij 00:00 start de ronde automatisch en begint de rode speeltimer met de gekozen speeltijd.</p>
        <p v-else>De timer start de ronde direct en verschijnt rood in de bovenbalk bij iedereen. Bij 00:00 stopt het spel automatisch. Als je de ronde pauzeert, pauzeert ook de timer.</p>
        <button class="primary-action" :class="{ 'start-timer-action': delayedStart && canSchedule }" type="submit" :disabled="busy">{{ busy ? 'Even wachten…' : delayedStart && canSchedule ? (startPending ? 'Starttimer opnieuw starten' : 'Starttimer starten') : startPending ? 'Ronde nu starten' : playingTimer ? 'Timer opnieuw starten' : 'Timer starten' }}</button>
        <button v-if="startPending || playingTimer" class="secondary-action" type="button" :disabled="busy" @click="change(game.id, true)">{{ startPending ? 'Starttimer annuleren' : 'Timer verwijderen' }}</button>
      </form>
      <p v-if="error" class="dialog-error" role="alert">{{ error }}</p><p v-if="result" class="dialog-result success" role="status">{{ result }}</p>
    </template>
  </section>
</template>
