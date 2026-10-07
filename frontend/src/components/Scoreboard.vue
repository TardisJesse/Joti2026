<script setup lang="ts">
import { computed } from 'vue'
import ProfileImage from './ProfileImage.vue'
const props = defineProps<{ scores: any[]; ownTeamId?: string | null; profile?: any }>()
const emit = defineEmits<{ saved: [user: any] }>()
const ranked = computed(() => [...props.scores].sort((a, b) => b.score - a.score || a.name.localeCompare(b.name) || a.team_id.localeCompare(b.team_id)))
const leaders = computed(() => ranked.value.slice(0, 3))
</script>
<template>
  <section class="score-page"><p class="eyebrow">LIVE RANKINGS</p><h1>Scoreboard</h1>
    <ProfileImage v-if="profile" :image="profile.profile_image" :name="profile.team_name || profile.name" @saved="emit('saved', $event)" />
    <p v-if="!ranked.length">Er zijn nog geen teams in deze ronde.</p>
    <div v-else class="podium" aria-label="Top drie">
      <article v-for="(team, index) in leaders" :key="team.team_id" class="podium-place" :class="['place-' + (index + 1), { 'own-team': team.team_id === ownTeamId }]" :style="{ '--team-color': team.color }">
        <span class="podium-rank">{{ index + 1 }}</span>
        <img v-if="team.profile_image" :src="team.profile_image" :alt="'Foto van ' + team.name" class="avatar" />
        <span v-else class="avatar avatar-fallback" aria-hidden="true">{{ team.name.slice(0, 2).toUpperCase() }}</span>
        <h2>{{ team.name }}</h2><strong>{{ team.score }} <small>PTS</small></strong><span v-if="team.team_id === ownTeamId" class="your-team">Jouw team</span>
      </article>
    </div>
    <ol v-if="ranked.length > 3" start="4" class="rank-list"><li v-for="(team, index) in ranked.slice(3)" :key="team.team_id" :class="{ 'own-team': team.team_id === ownTeamId }"><em>#{{ index + 4 }}</em><img v-if="team.profile_image" :src="team.profile_image" :alt="'Foto van ' + team.name" class="avatar" /><span v-else class="avatar avatar-fallback" :style="{ borderColor: team.color }" aria-hidden="true">{{ team.name.slice(0, 2).toUpperCase() }}</span><span>{{ team.name }}</span><strong>{{ team.score }} PTS</strong></li></ol>
  </section>
</template>
