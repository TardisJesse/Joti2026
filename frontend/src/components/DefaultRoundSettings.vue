<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '../api'

type Round = { id: string; code: string | null; name: string; status: string }
type DefaultRound = { game_id: string | null; game_code: string | null }
const props = defineProps<{ games: Round[]; defaultGameId: string }>()
const emit = defineEmits<{ saved: [value: DefaultRound] }>()
const chosen = ref(''), busy = ref(false), error = ref(''), result = ref('')
const choices = computed(() => props.games.filter(game => game.code))
watch(() => props.defaultGameId, value => { chosen.value = value }, { immediate: true })

async function save() {
  if (busy.value || !chosen.value) return
  busy.value = true; error.value = ''; result.value = ''
  try {
    const saved: DefaultRound = await api('/api/admin/default-game', {
      method: 'PUT', body: JSON.stringify({ game_id: chosen.value }),
    })
    emit('saved', saved)
    result.value = `${saved.game_code} is nu de standaardronde voor nieuwe spelers.`
  } catch (e: any) { error.value = e.message }
  finally { busy.value = false }
}
</script>

<template>
  <section class="default-round" aria-labelledby="default-round-title">
    <h2 id="default-round-title">Standaardronde</h2>
    <p>Deze spelcode staat alvast ingevuld op het startscherm. Kies hier de volgende ronde als je het spel nog een keer speelt. Bestaande teams blijven in hun eigen ronde.</p>
    <form @submit.prevent="save">
      <label>Standaard spelronde<select v-model="chosen" required :disabled="busy || !choices.length"><option value="" disabled>Kies een ronde</option><option v-for="game in choices" :key="game.id" :value="game.id">{{ game.code }} · {{ game.status }}</option></select></label>
      <button class="primary-action" type="submit" :disabled="busy || !chosen || chosen === defaultGameId">{{ busy ? 'Opslaan…' : 'Standaardronde opslaan' }}</button>
    </form>
    <p v-if="!choices.length">Maak hieronder eerst een spelronde aan.</p>
    <p v-if="error" class="dialog-error" role="alert">{{ error }}</p>
    <p v-if="result" class="dialog-result success" role="status">{{ result }}</p>
  </section>
</template>

<style scoped>
.default-round{padding:20px;margin-bottom:24px;border:1px solid #355a70;border-radius:16px;background:#0c2335}.default-round h2{margin:0 0 10px}.default-round p{color:#b9cfdd;font-size:14px;line-height:1.6}.default-round form{display:grid;gap:14px}.default-round label{display:grid;gap:8px;font-weight:600}.default-round select{width:100%;min-height:48px;padding:12px;border:1px solid #537084;border-radius:10px;background:#051727;color:#e8f9ff;font:inherit}.default-round button:disabled{opacity:.5;cursor:default}.default-round :focus-visible{outline:3px solid #62e8f5;outline-offset:3px}
</style>
