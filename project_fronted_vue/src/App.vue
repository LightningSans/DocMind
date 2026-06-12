<template>
  <router-view />
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import { onMounted } from 'vue'

const appStore = useAppStore()
onMounted(() => {
  appStore.loadFromStorage()
})
</script>
