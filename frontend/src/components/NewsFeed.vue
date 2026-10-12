<script setup lang="ts">
defineProps<{ events: any[]; failed?: boolean }>()
const timeLabel = (value: string) => new Date(value).toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' })
</script>
<template>
  <section class="news-feed" aria-labelledby="news-heading"><p class="eyebrow">CYBERJOTI // LIVE</p><h2 id="news-heading">Nieuws uit het speelveld</h2>
    <p v-if="failed" role="status">Nieuws vernieuwen lukt nu niet. We proberen het opnieuw.</p>
    <p v-else-if="!events.length">Nog geen nieuws. Hier verschijnen veroveringen, bonuslocaties en updates van de ronde.</p>
    <ol><li v-for="event in events" :key="event.id"><time :datetime="event.created_at">{{ timeLabel(event.created_at) }}</time><div><small v-if="event.team_name">{{ event.team_name }}</small><p>{{ event.message }}</p></div></li></ol>
  </section>
</template>
