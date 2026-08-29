<script setup lang="ts">
import { onMounted, ref } from "vue"
import { listItems, type ContentItem } from "./api"

const items = ref<ContentItem[]>([])
const loading = ref(true)
const error = ref("")

onMounted(async () => {
  try {
    items.value = await listItems()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Failed to load content"
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <v-app>
    <v-app-bar title="content-tracker" />
    <v-main>
      <v-container class="py-8">
        <h1 class="text-h4 mb-2">Content</h1>
        <p class="text-medium-emphasis mb-6">
          Track what you plan to watch, listen to, read, and revisit.
        </p>
        <v-progress-linear v-if="loading" indeterminate />
        <v-alert v-else-if="error" type="error" :text="error" />
        <v-alert v-else-if="items.length === 0" type="info"
                 text="No content has been added yet." />
        <v-list v-else lines="two">
          <v-list-item v-for="item in items" :key="item.id"
                       :title="item.title"
                       :subtitle="`${item.content_type} · ${item.status}`" />
        </v-list>
      </v-container>
    </v-main>
  </v-app>
</template>
