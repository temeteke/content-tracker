<script setup lang="ts">
import { onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"

import {
  createItem,
  deleteItem,
  formatApiError,
  ITEMS_PAGE_SIZE,
  listItems,
  patchItem,
  type ContentItem,
} from "../api"
import { contentTypeOptions, statusOptions } from "../constants"

const router = useRouter()

const items = ref<ContentItem[]>([])
const total = ref<number | null>(null)
const loading = ref(true)
const loadingMore = ref(false)
const hasMore = ref(false)
const error = ref("")
const query = ref("")
const status = ref("")
const contentType = ref("")
const appliedFilters = ref<{ query?: string; status?: string; contentType?: string }>({})
let listRequestId = 0
let searchTimer: ReturnType<typeof setTimeout> | null = null

const addDialog = ref(false)
const newTitle = ref("")
const newContentType = ref("video")
const newParentId = ref("")
const savingNewItem = ref(false)

async function loadItems() {
  const requestId = ++listRequestId
  loading.value = true
  error.value = ""
  const filters = {
    query: query.value || undefined,
    status: status.value || undefined,
    contentType: contentType.value || undefined,
  }
  try {
    const result = await listItems({
      ...filters,
      offset: 0,
      limit: ITEMS_PAGE_SIZE,
    })
    if (requestId !== listRequestId) return
    appliedFilters.value = filters
    total.value = result.total
    hasMore.value =
      result.items.length === ITEMS_PAGE_SIZE &&
      (result.total === null || result.total > ITEMS_PAGE_SIZE)
    items.value = result.items
  } catch (cause) {
    if (requestId !== listRequestId) return
    error.value = formatApiError(cause, "Failed to load content")
  } finally {
    if (requestId === listRequestId) loading.value = false
  }
}

function scheduleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void loadItems(), 350)
}

function searchNow() {
  if (searchTimer) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
  void loadItems()
}

async function loadMore() {
  if (loadingMore.value || !hasMore.value) return

  const requestId = listRequestId
  loadingMore.value = true
  error.value = ""
  try {
    const result = await listItems({
      ...appliedFilters.value,
      offset: items.value.length,
      limit: ITEMS_PAGE_SIZE,
    })
    if (requestId !== listRequestId) return
    total.value = result.total
    hasMore.value =
      result.items.length === ITEMS_PAGE_SIZE &&
      (result.total === null || items.value.length + result.items.length < result.total)
    items.value = [...items.value, ...result.items]
  } catch (cause) {
    if (requestId !== listRequestId) return
    error.value = formatApiError(cause, "Failed to load more content")
  } finally {
    loadingMore.value = false
  }
}

async function changeStatus(item: ContentItem, nextStatus: string) {
  try {
    const updated = await patchItem(item.id, { status: nextStatus, revision: item.revision })
    const filtersStatus = appliedFilters.value.status
    if (filtersStatus && updated.status !== filtersStatus) {
      items.value = items.value.filter((entry) => entry.id !== updated.id)
      if (total.value !== null) total.value -= 1
    } else {
      const current = items.value.find((entry) => entry.id === updated.id)
      if (current) Object.assign(current, updated)
    }
  } catch (cause) {
    error.value = formatApiError(cause, "Failed to update content")
    await loadItems()
  }
}

function openDetail(item: ContentItem) {
  void router.push({ name: "detail", params: { id: item.id } })
}

function openAddDialog() {
  newTitle.value = ""
  newContentType.value = "video"
  newParentId.value = ""
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
      parent_id: newParentId.value.trim() || undefined,
    })
    addDialog.value = false
    await loadItems()
  } catch (cause) {
    error.value = formatApiError(cause, "Failed to create content")
  } finally {
    savingNewItem.value = false
  }
}

function openDeleteConfirm(item: ContentItem) {
  if (window.confirm(`Delete "${item.title}"? Links and history are removed as well.`)) {
    void removeItem(item)
  }
}

async function removeItem(item: ContentItem) {
  try {
    await deleteItem(item.id, item.revision)
    items.value = items.value.filter((entry) => entry.id !== item.id)
    if (total.value !== null) total.value -= 1
  } catch (cause) {
    error.value = formatApiError(cause, "Failed to delete content")
    await loadItems()
  }
}

onMounted(loadItems)
watch([status, contentType], () => void loadItems())
</script>

<template>
  <v-container class="py-8">
    <div class="d-flex justify-space-between align-center mb-2">
      <h1 class="text-h4">Content</h1>
      <v-btn prepend-icon="mdi-plus" color="primary" @click="openAddDialog"> Add content </v-btn>
    </div>
    <p class="text-medium-emphasis mb-6">
      Track what you plan to watch, listen to, read, and revisit.
      <span v-if="total !== null">{{ total }} item(s).</span>
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
      <v-col cols="12" md="6">
        <v-text-field
          v-model="query"
          label="Search"
          clearable
          hide-details
          @keyup.enter="searchNow"
          @click:clear="searchNow"
          @update:model-value="scheduleSearch"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-select
          v-model="status"
          :items="[{ title: 'All', value: '' }, ...statusOptions]"
          label="Status"
          hide-details
          clearable
          @update:model-value="loadItems"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-select
          v-model="contentType"
          :items="[{ title: 'All', value: '' }, ...contentTypeOptions]"
          label="Content type"
          hide-details
          clearable
          @update:model-value="loadItems"
        />
      </v-col>
    </v-row>

    <v-progress-linear v-if="loading" indeterminate />
    <v-alert v-else-if="items.length === 0" type="info" text="No content has been added yet." />

    <v-list v-else lines="two">
      <v-list-item
        v-for="item in items"
        :key="item.id"
        :title="item.title"
        :subtitle="`${item.content_type} · ${item.status}`"
        @click="openDetail(item)"
      >
        <template #append>
          <div class="d-flex align-center ga-2" @click.stop>
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="text"
              title="Open detail"
              @click="openDetail(item)"
            />
            <v-btn
              icon="mdi-call-merge"
              size="small"
              variant="text"
              title="Merge duplicate"
              @click="
                $router.push({ name: 'detail', params: { id: item.id }, query: { showMerge: '1' } })
              "
            />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              title="Delete"
              @click="openDeleteConfirm(item)"
            />
            <v-select
              :model-value="item.status"
              :items="statusOptions"
              density="compact"
              hide-details
              style="min-width: 150px"
              @update:model-value="(value) => changeStatus(item, String(value))"
            />
          </div>
        </template>
      </v-list-item>
    </v-list>

    <div v-if="!loading && hasMore" class="d-flex justify-center mt-4">
      <v-btn :loading="loadingMore" variant="tonal" @click="loadMore"> Load more </v-btn>
    </div>

    <v-dialog v-model="addDialog" max-width="520">
      <v-card title="Add content">
        <v-card-text>
          <v-text-field v-model="newTitle" autofocus label="Title" @keyup.enter="saveNewItem" />
          <v-select v-model="newContentType" :items="contentTypeOptions" label="Content type" />
          <v-text-field
            v-model="newParentId"
            label="Parent ID (optional)"
            hint="Leave empty for top-level items"
            persistent-hint
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
  </v-container>
</template>
