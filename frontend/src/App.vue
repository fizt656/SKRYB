<script setup lang="ts">
// Import necessary components and potentially router/store later
// import { RouterLink, RouterView } from 'vue-router'
// import HelloWorld from './components/HelloWorld.vue'
</script>

<template>
  <div id="app">
    <header class="app-header">
      <img alt="SKRYB Logo" class="logo" src="/skryb_logo.png" />
    </header>

    <main class="app-main">
      <!-- RouterView or main content component will go here -->
      <RouterView />
      <!-- We will add components for input forms, style selection, etc. here -->
    </main>
  </div>
</template>

<style>
/* Import global dark mode styles */
@import './assets/styles/dark-mode.css';

/* Basic App layout styles */
#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  background-color: var(--color-background-soft);
  padding: 1rem;
  display: flex;
  align-items: center;
  justify-content: center; /* Center header content */
  border-bottom: 1px solid var(--color-border);
}

.app-header .logo {
  height: 150px; /* Adjust size as needed */
}

.app-main {
  flex-grow: 1;
  padding: 2rem;
  background-color: var(--color-background);
  color: var(--color-text);
}
</style>
