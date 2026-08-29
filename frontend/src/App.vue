<script setup lang="ts">
import { onMounted, ref } from "vue"
import { listItems, type ContentItem, updateItemStatus } from "./api"

const items = ref<ContentItem[]>([])
const loading = ref(true)
const error = ref("")
const query = ref("")
const status = ref("")

const statusOptions = [
  { title: "All", value: "" },
  { title: "Planned", value: "planned" },
  { title: "Active", value: "active" },
  { title: "Completed", value: "completed" },
  { title: "Dropped", value: "dropped" },
]

async function loadItems() {
  loading.value = true
  error.value = ""
  try {
    items.value = await listItems({
      query: query.value || undefined,
      status: status.value || undefined,
    })
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Failed to load content"
  } finally {
    loading.value = false
  }
}

async function changeStatus(item: ContentItem, nextStatus: string) {
  try {
    const updated = await updateItemStatus(item.id, nextStatus)
    Object.assign(item, updated)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Failed to update content"
  }
}

onMounted(loadItems)
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

        <v-row class="mb-4">
          <v-col cols="12" md="8">
            <v-text-field
              v-model="query"
              label="Search"
              clearable
              hide-details
              @keyup.enter="loadItems"
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-select
              v-model="status"
              :items="statusOptions"
              label="Status"
              hide-details
              @update:model-value="loadItems"
            />
          </v-col>
        </v-row>

        <v-progress-linear v-if="loading" indeterminate />
        <v-alert v-else-if="error" type="error" :text="error" />
        <v-alert
          v-else-if="items.length === 0"
          type="info"
          text="No content has been added yet."
        />

        <v-list v-else lines="two">
          <v-list-item
            v-for="item in items"
            :key="item.id"
            :title="item.title"
            :subtitle="item.content_type"
          >
            <template #append>
              <v-select
                :model-value="item.status"
                :items="statusOptions.slice(1)"
                density="compact"
                hide-details
                style="min-width: 150px"
                @update:model-value="value => changeStatus(item, value)"
              />
            </template>
          </v-list-item>
        </v-list>
      </v-container>
    </v-main>
  </v-app>
</template>
