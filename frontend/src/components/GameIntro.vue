<script setup lang="ts">
import { ref } from 'vue'
const dialog = ref<HTMLDialogElement | null>(null), video = ref<HTMLVideoElement | null>(null), failed = ref(false)
function close() { video.value?.pause(); dialog.value?.close() }
defineExpose({ open: () => dialog.value?.showModal() })
</script>
<template>
  <dialog ref="dialog" class="game-dialog intro-dialog" aria-labelledby="intro-title" @close="video?.pause()" @cancel="video?.pause()">
    <div class="dialog-heading"><p class="eyebrow">WELKOM OP CYBERJOTI</p><button class="dialog-close" aria-label="Speluitleg sluiten" @click="close">✕</button></div>
    <h2 id="intro-title">Maak jouw team groot</h2>
    <video ref="video" controls playsinline preload="none" poster="/intro/poster.jpg" @error="failed = true"><source src="/intro/cyberjoti-intro.mp4" type="video/mp4"><track default kind="captions" src="/intro/cyberjoti-intro.vtt" srclang="nl" label="Nederlands"></video>
    <p v-if="failed" role="status">De video kan niet geladen worden. Lees hieronder de volledige uitleg.</p>
    <a href="/intro/cyberjoti-intro-ondertiteld.mp4" download>Video downloaden voor het gezamenlijke startmoment</a>
    <details :open="failed"><summary>Speluitleg lezen</summary>
      <p>Jullie team heeft een eigen kanaal op CyberJoti. Trek eropuit, werk samen en verzamel volgers. Het team met de meeste volgers bij het einde wint.</p>
      <h3>Vijf soorten spelpunten</h3>
      <ul><li><strong>Puzzel:</strong> ga naar het vraagteken en los de vraag op. Een goed antwoord levert je team volgers op.</li><li><strong>Fotopunt:</strong> maak binnen de cirkel de gevraagde foto van jezelf met je team. Eén inzending per team en per fotopunt levert volgers op. Op de locatie kun je de teamfoto’s bekijken.</li><li><strong>Zendmast:</strong> start een capture en blijf tijdens de verovering binnen de cirkel. Je verdient een veroveringsbeloning en zolang je team de post bezit komen er volgers per minuut bij. Andere teams kunnen de post overnemen.</li><li><strong>NFC-eend:</strong> zoek het fysieke eendje, lees de NFC-tag en voer de code in terwijl je in de buurt bent. Je team verdient de beloning één keer per eendje.</li><li><strong>Scannerpunt:</strong> open de scanner binnen de cirkel om recente locaties van andere teams te zien. Zodra je weggaat of de scanner sluit, verdwijnen ze. Je krijgt hiervoor geen volgers; het gebruik blijft geheim.</li></ul>
      <h3>Bonus, beloningen en regels</h3><p>Na tien speelminuten wordt een zendmast vijf minuten lang een bonuslocatie. De draaiende regenboogrand betekent dubbele volgers per minuut, zonder verdubbeling van de veroveringsbeloning. Elke tien speelminuten wisselt de bonuspost. De ingestelde beloningen staan bij de spelpunten.</p>
      <p>Blijf als team bij elkaar en binnen het afgesproken speelgebied. Voer opdrachten ter plekke uit met echte GPS-locaties. Maak de gevraagde teamfoto en speel sportief. De beheerder helpt bij vragen en kan het spel pauzeren.</p>
      <p>Meld je aan met spelcode en teamnaam. Gebruik dezelfde gegevens om je team te hervatten. De nieuwsfeed vertelt wat er in de ronde gebeurt. Volg de rode timer: bij nul stopt het verdienen van volgers. Bekijk daarna het podium en de eindstand.</p>
    </details><button class="primary-action" @click="close">Klaar voor het spel</button>
  </dialog>
</template>
