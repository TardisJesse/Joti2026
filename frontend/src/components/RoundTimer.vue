<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'
defineProps<{ game?: any; countdown: string }>()
const emit = defineEmits<{ updated: [] }>()
const minutes = ref(60), busy = ref(false), error = ref(''), result = ref('')
async function change(gameId: string, remove = false) {
  if (busy.value) return
  if (!remove && (!Number.isInteger(minutes.value) || minutes.value < 1 || minutes.value > 1440)) { error.value = 'Kies tussen 1 en 1440 hele minuten.'; return }
  busy.value = true; error.value = ''; result.value = ''
  try {
    await api('/api/admin/games/' + gameId + '/timer', { method: remove ? 'DELETE' : 'PUT', ...(remove ? {} : { body: JSON.stringify({ duration_seconds: minutes.value * 60 }) }) })
    result.value = remove ? 'Timer verwijderd.' : 'Timer gestart voor alle spelers.'
    emit('updated')
  } catch (e: any) { error.value = e.message }
  finally { busy.value = false }
}
</script>
<template>
  <section class="admin-page timer-page"><p class="eyebrow">GAME MASTER // TIMER</p><h1>Speltimer</h1>
    <p v-if="!game" class="helper">Maak of kies eerst een spelronde bij Beheer.</p>
    <template v-else><p class="helper">Spelronde: {{ game.code || game.name }}</p>
      <div v-if="game.ends_at || game.timer_remaining_seconds != null" class="timer-preview"><strong>{{ countdown }}</strong><span>{{ game.status === 'FINISHED' ? 'Spel afgelopen' : game.status === 'PAUSED' ? 'Gepauzeerd' : 'Resterende speeltijd' }}</span></div>
      <form class="timer-form" @submit.prevent="change(game.id)"><label>Speeltijd in minuten<input v-model.number="minutes" type="number" min="1" max="1440" step="1" required :disabled="busy" /></label><p>De timer start de ronde en verschijnt rood in de bovenbalk bij iedereen. Bij 00:00 stopt het spel automatisch. Als je de ronde pauzeert, pauzeert ook de timer.</p><button class="primary-action" type="submit" :disabled="busy">{{ busy ? 'Even wachten…' : game.ends_at || game.timer_remaining_seconds != null ? 'Timer opnieuw starten' : 'Timer starten' }}</button><button v-if="game.ends_at || game.timer_remaining_seconds != null" class="secondary-action" type="button" :disabled="busy" @click="change(game.id, true)">Timer verwijderen</button></form>
      <p v-if="error" class="dialog-error" role="alert">{{ error }}</p><p v-if="result" class="dialog-result success" role="status">{{ result }}</p>
    </template>
  </section>
</template>
