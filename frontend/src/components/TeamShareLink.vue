<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'

const link = ref(''), expiry = ref(''), busy = ref(false), message = ref(''), error = ref('')
const input = ref<HTMLInputElement>()
async function createLink() {
  if (busy.value) return
  busy.value = true; error.value = ''; message.value = ''
  try {
    const response = await api('/api/team/view-link', { method: 'POST' })
    link.value = window.location.origin + window.location.pathname + '#team=' + encodeURIComponent(response.token)
    expiry.value = new Date(response.expires_at).toLocaleString('nl-NL', { dateStyle: 'short', timeStyle: 'short' })
  } catch (e: any) { error.value = e.message }
  finally { busy.value = false }
}
async function copyLink() {
  try { await navigator.clipboard.writeText(link.value); message.value = 'Teamlink gekopieerd. Deel hem met je teamleden.' }
  catch { input.value?.focus(); input.value?.select(); message.value = 'Selecteer en kopieer de teamlink hieronder.' }
}
</script>

<template>
  <section class="team-share" aria-labelledby="team-share-title">
    <h2 id="team-share-title">Laat je team meekijken</h2>
    <p>Deel een teamlink voor de kaart, jullie locatie, voortgang en score. Teamleden kunnen meekijken; jij blijft de speler die acties uitvoert.</p>
    <button v-if="!link" type="button" class="secondary-action" :disabled="busy" @click="createLink">{{ busy ? 'Link maken…' : 'Teamlink maken' }}</button>
    <template v-else><label>Alleen-lezen teamlink<input ref="input" :value="link" readonly @focus="input?.select()" /></label><button type="button" class="primary-action" @click="copyLink">Teamlink kopiëren</button><small>Geldig tot {{ expiry }}. Iedereen met deze link kan jullie team volgen.</small></template>
    <p v-if="message" role="status">{{ message }}</p><p v-if="error" class="dialog-error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
.team-share{padding:20px;margin:18px 0;border:1px solid #355a70;border-radius:16px;background:#0c2335;color:#e2f4ff}.team-share h2{margin:0 0 10px;font-size:20px}.team-share p{line-height:1.6}.team-share label{display:grid;gap:8px;margin:16px 0}.team-share input{width:100%;padding:12px;min-height:48px;border:1px solid #537084;border-radius:10px;background:#051727;color:#e8f9ff;font:inherit}.team-share small{display:block;margin-top:12px;line-height:1.6;color:#b9cfdd}.team-share button{min-height:48px}.team-share :focus-visible{outline:3px solid #62e8f5;outline-offset:3px}
</style>
