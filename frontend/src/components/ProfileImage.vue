<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'
import { prepareImage } from '../images'
defineProps<{ image?: string | null; name: string }>()
const emit = defineEmits<{ saved: [user: any] }>()
const busy = ref(false), error = ref('')
async function upload(event: Event) {
  const input = event.target as HTMLInputElement, file = input.files?.[0]
  if (!file || busy.value) return
  busy.value = true; error.value = ''
  try {
    const image = await prepareImage(file, 512)
    emit('saved', await api('/api/profile/image', { method: 'PUT', body: JSON.stringify({ image }) }))
  } catch (e: any) { error.value = e.message || 'Foto laden mislukt.' }
  finally { busy.value = false; input.value = '' }
}
</script>
<template>
  <section class="profile-editor" aria-label="Profielfoto">
    <label class="profile-photo-picker" :class="{ busy }">
      <img v-if="image" :src="image" :alt="'Profielfoto van ' + name" class="avatar" />
      <span v-else class="avatar avatar-fallback profile-plus" aria-hidden="true">+</span>
      <span v-if="image" class="photo-edit-badge" aria-hidden="true">+</span>
      <input type="file" accept="image/jpeg,image/png,image/webp" :aria-label="image ? 'Profielfoto wijzigen' : 'Profielfoto toevoegen'" :disabled="busy" @change="upload" />
    </label>
    <div><strong>{{ name }}</strong><small>{{ busy ? 'Foto opslaan…' : image ? 'Tik op je foto om die te wijzigen' : 'Tik op + om je foto toe te voegen' }}</small><p v-if="error" role="alert">{{ error }}</p></div>
  </section>
</template>
