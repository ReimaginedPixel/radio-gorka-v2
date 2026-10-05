<template>
  <div class="nf">
    <div class="nf-art">
      <span class="nf-glow" aria-hidden="true" />
      <img :src="speaker" alt="" class="nf-speaker floaty" width="233" height="311" />
    </div>
    <div class="nf-copy">
      <span class="nf-code led" aria-label="404">
        <span v-for="(d, i) in digits" :key="i" class="nf-digit" :style="{ animationDelay: `${i * 0.14}s` }">{{ d }}</span>
      </span>
      <h1 class="nf-title">Cisza w eterze</h1>
      <p class="nf-text">Nie ma takiej strony. Sprawdź adres albo wróć na antenę.</p>
      <RouterLink to="/" class="btn btn-primary nf-btn">Wróć na stronę główną</RouterLink>
    </div>
  </div>
</template>

<script setup>
import speaker from '../assets/img/speaker.png'

const digits = ['4', '0', '4']
</script>

<style scoped>
.nf {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 20px;
  padding: clamp(10px, 4vw, 40px) 0;
}

.nf-art {
  position: relative;
  flex: 1 1 260px;
  min-width: 240px;
  display: flex;
  justify-content: center;
}

.nf-glow {
  position: absolute;
  width: 220px;
  height: 160px;
  top: 50%;
  left: 50%;
  translate: -50% -40%;
  border-radius: 50%;
  background: radial-gradient(circle, var(--acc), transparent 70%);
  opacity: 0.28;
  filter: blur(30px);
}

.nf-speaker {
  position: relative;
  width: clamp(170px, 27vw, 250px);
  height: auto;
  animation-duration: 6.5s;
  filter: drop-shadow(0 30px 40px rgba(0, 0, 0, 0.55));
}

.nf-copy {
  flex: 1 1 280px;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-start;
}

.nf-code {
  font-size: clamp(56px, 11vw, 96px);
  line-height: 0.9;
  color: var(--acc);
  letter-spacing: 2px;
}

/* cyfry łapią sygnał jedna po drugiej, jak strojenie radia */
.nf-digit {
  display: inline-block;
  animation: tune 2.6s steps(1, end) infinite;
}

@keyframes tune {
  0%,
  6%,
  10%,
  100% {
    opacity: 1;
  }
  3%,
  8% {
    opacity: 0.2;
  }
}

.nf-title {
  margin: 0;
  font-size: clamp(18px, 2.6vw, 23px);
  font-weight: 700;
  letter-spacing: -0.3px;
}

.nf-text {
  margin: 0;
  font-size: 14px;
  color: var(--dim);
  max-width: 34ch;
  text-wrap: pretty;
}

.nf-btn {
  margin-top: 4px;
  height: 48px;
  padding: 0 20px;
  border-radius: 15px;
  font-size: 14.5px;
}

.nf-btn:hover {
  text-decoration: none;
  color: var(--accInk);
}
</style>
