<script setup lang="ts">
import { onMounted, ref } from "vue"

import {
  addConsumptionHistory,
  createItem,
  listItems,
  type ContentItem,
  updateItemStatus,
} from "./api"

const items = ref<ContentItem[]>([])
const loading = ref(true)
const error = ref("")
const query = ref("")
const status = ref("")

const addDialog = ref(false)
const newTitle = ref("")
const newContentType = ref("video")
const savingNewItem = ref(false)

const historyDialog = ref(false)
const historyItem = ref<ContentItem | null>(null)
const historyDate = ref("")
const historyRating = ref<number | null>(null)
const historyComment = ref("")
const savingHistory = ref(false)

const statusOptions = [
  { title: "All", value: "" },
  { title: "Planned", value: "planned" },
  { title: "Active", value: "active" },
  { title: "Completed", value: "completed" },
  { title: "Dropped", value: "dropped" },
]

const contentTypeOptions = [
  { title: "Video", value: "video" },
  { title: "TV", value: "tv" },
  { title: "Radio", value: "radio" },
  { title: "Podcast", value: "podcast" },
  { title: "Book", value: "book" },
  { title: "Manga", value: "manga" },
  { title: "Article", value: "article" },
  { title: "Other", value: "other" },
]

function localDateTimeValue(): string {
  const date = new Date()
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

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

function openAddDialog() {
  newTitle.value = ""
  newContentType.value = "video"
  addDialog.value = true
}

async function saveNewItem() {
  const title = newTitle.value.trim()
  if (!title) return

  savingNewItem.value = true
  error.value = ""
  try {
    await createItem({
      title,
      content_type: newContentType.value,
      status: "planned",
    })
    addDialog.value = false
    await loadItems()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Failed to create content"
  } finally {
    savingNewItem.value = false
  }
}

function openHistoryDialog(item: ContentItem) {
  historyItem.value = item
  historyDate.value = localDateTimeValue()
  historyRating.value = null
  historyComment.value = ""
  historyDialog.value = true
}

async function saveHistory() {
  if (!historyItem.value || !historyDate.value) return

  savingHistory.value = true
  error.value = ""
  try {
    await addConsumptionHistory(historyItem.value.id, {
      consumed_at: new Date(historyDate.value).toISOString(),
      rating: historyRating.value,
      comment: historyComment.value.trim(),
    })
    historyDialog.value = false
    await loadItems()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Failed to record history"
  } finally {
    savingHistory.value = false
  }
}

onMounted(loadItems)
</script>

<template>
  <v-app>
    <v-app-bar title="content-tracker">
      <template #append>
        <v-btn prepend-icon="mdi-plus" @click="openAddDialog">
          Add content
        </v-btn>
      </template>
    </v-app-bar>

    <v-main>
      <v-container class="py-8">
        <h1 class="text-h4 mb-2">Content</h1>
        <p class="text-medium-emphasis mb-6">
          Track what you plan to watch, listen to, read, and revisit.
        </p>

        <v-alert
          v-if="error"
          class="mb-4"
          closable
          type="error"
          :text="error"
          @click:close="error = ''"
        />

        <v-row class="mb-4">
          <v-col cols="12" md="8">
            <v-text-field
              v-model="query"
              label="Search"
              clearable
              hide-details
              @keyup.enter="loadItems"
              @click:clear="loadItems"
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
              <div class="d-flex align-center ga-2">
                <v-btn
                  icon="mdi-check"
                  size="small"
                  variant="text"
                  title="Record consumption"
                  @click="openHistoryDialog(item)"
                />
                <v-select
                  :model-value="item.status"
                  :items="statusOptions.slice(1)"
                  density="compact"
                  hide-details
                  style="min-width: 150px"
                  @update:model-value="value => changeStatus(item, value)"
                />
              </div>
            </template>
          </v-list-item>
        </v-list>
      </v-container>
    </v-main>

    <v-dialog v-model="addDialog" max-width="520">
      <v-card title="Add content">
        <v-card-text>
          <v-text-field
            v-model="newTitle"
            autofocus
            label="Title"
            @keyup.enter="saveNewItem"
          />
          <v-select
            v-model="newContentType"
            :items="contentTypeOptions"
            label="Content type"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="addDialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            :disabled="!newTitle.trim()"
            :loading="savingNewItem"
            @click="saveNewItem"
          >
            Add
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="historyDialog" max-width="520">
      <v-card :title="`Record consumption: ${historyItem?.title ?? ''}`">
        <v-card-text>
          <v-text-field
            v-model="historyDate"
            label="Consumed at"
            type="datetime-local"
          />
          <v-select
            v-model="historyRating"
            :items="[1, 2, 3, 4, 5]"
            clearable
            label="Rating"
          />
          <v-textarea
            v-model="historyComment"
            label="Comment"
            rows="3"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="historyDialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            :loading="savingHistory"
            @click="saveHistory"
          >
            Record
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-app>
</template>
