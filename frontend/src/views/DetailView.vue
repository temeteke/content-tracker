<script setup lang="ts">
import { onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import {
  addConsumptionHistory,
  addLink,
  deleteConsumptionHistory,
  deleteItem,
  deleteLink,
  formatApiError,
  getItem,
  listHistory,
  listItems,
  listLinks,
  mergeItems,
  patchItem,
  updateConsumptionHistory,
  type ConsumptionHistory,
  type ContentItem,
  type ContentLink,
} from "../api"
import {
  contentTypeOptions,
  formatDateTime,
  localDateTimeValue,
  statusOptions,
  toISOString,
} from "../constants"

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()

const item = ref<ContentItem | null>(null)
const loading = ref(true)
const error = ref("")
const notice = ref("")

const parentChain = ref<ContentItem[]>([])
const children = ref<ContentItem[]>([])
const links = ref<ContentLink[]>([])
const history = ref<ConsumptionHistory[]>([])

const editTitle = ref("")
const editContentType = ref("")
const editStatus = ref("")
const editDescription = ref("")
const editParentId = ref("")
const savingEdit = ref(false)

const newLinkUrl = ref("")
const newLinkType = ref("source")
const savingLink = ref(false)

const historyDialog = ref(false)
const editingHistoryId = ref<string | null>(null)
const historyDate = ref("")
const historyRating = ref<number | null>(null)
const historyComment = ref("")
const savingHistory = ref(false)

const mergeDialog = ref(false)
const mergeSourceId = ref("")
const merging = ref(false)

async function loadAll() {
  loading.value = true
  error.value = ""
  notice.value = ""
  try {
    const loaded = await getItem(props.id)
    item.value = loaded
    editTitle.value = loaded.title
    editContentType.value = loaded.content_type
    editStatus.value = loaded.status
    editDescription.value = loaded.description
    editParentId.value = loaded.parent_id ?? ""

    const [linkList, historyList, childList] = await Promise.all([
      listLinks(loaded.id),
      listHistory(loaded.id),
      listItems({ parentId: loaded.id, limit: 100 }),
    ])
    links.value = linkList
    history.value = historyList
    children.value = childList.items

    const chain: ContentItem[] = []
    let parentId = loaded.parent_id
    while (parentId) {
      const parent = await getItem(parentId)
      chain.unshift(parent)
      parentId = parent.parent_id
    }
    parentChain.value = chain
  } catch (cause) {
    error.value = formatApiError(cause, "Failed to load content")
    item.value = null
  } finally {
    loading.value = false
  }
}

async function saveEdit() {
  if (!item.value) return
  const title = editTitle.value.trim()
  if (!title) {
    error.value = "Title must not be empty"
    return
  }
  savingEdit.value = true
  error.value = ""
  notice.value = ""
  try {
    const payload: {
      revision: number
      title: string
      content_type: string
      status: string
      description: string
      parent_id?: string | null
    } = {
      revision: item.value.revision,
      title,
      content_type: editContentType.value,
      status: editStatus.value,
      description: editDescription.value,
    }
    const trimmedParent = editParentId.value.trim()
    const currentParent = item.value.parent_id ?? ""
    if (trimmedParent !== currentParent) {
      payload.parent_id = trimmedParent || null
    }
    item.value = await patchItem(item.value.id, payload)
    editParentId.value = item.value.parent_id ?? ""
    notice.value = "Saved."
    await loadAll()
  } catch (cause) {
    error.value = formatApiError(cause, "Failed to save content")
    await loadAll()
  } finally {
    savingEdit.value = false
  }
}

async function removeItem() {
  if (!item.value) return
  if (!window.confirm(`Delete "${item.value.title}"? Links and history are removed as well.`)) {
    return
  }
  try {
    await deleteItem(item.value.id, item.value.revision)
    void router.push({ name: "list" })
  } catch (cause) {
    error.value = formatApiError(cause, "Failed to delete content")
    await loadAll()
  }
}

async function saveLink() {
  if (!item.value || !newLinkUrl.value.trim()) return
  savingLink.value = true
  error.value = ""
  notice.value = ""
  try {
    const link = await addLink(item.value.id, {
      url: newLinkUrl.value.trim(),
      link_type: newLinkType.value,
    })
    links.value = [...links.value, link]
    newLinkUrl.value = ""
    notice.value = "Link added."
  } catch (cause) {
    error.value = formatApiError(cause, "Failed to add link")
  } finally {
    savingLink.value = false
  }
}

async function removeLink(link: ContentLink) {
  error.value = ""
  notice.value = ""
  try {
    await deleteLink(link.id)
    links.value = links.value.filter((entry) => entry.id !== link.id)
    notice.value = "Link deleted."
  } catch (cause) {
    error.value = formatApiError(cause, "Failed to delete link")
  }
}

function openAddHistoryDialog() {
  editingHistoryId.value = null
  historyDate.value = localDateTimeValue()
  historyRating.value = null
  historyComment.value = ""
  historyDialog.value = true
}

function openEditHistoryDialog(entry: ConsumptionHistory) {
  editingHistoryId.value = entry.id
  historyDate.value = localDateTimeValue(new Date(entry.consumed_at))
  historyRating.value = entry.rating
  historyComment.value = entry.comment
  historyDialog.value = true
}

async function saveHistoryDialog() {
  if (!item.value || !historyDate.value) return
  savingHistory.value = true
  error.value = ""
  notice.value = ""
  try {
    if (editingHistoryId.value) {
      const updated = await updateConsumptionHistory(editingHistoryId.value, {
        consumed_at: toISOString(historyDate.value),
        rating: historyRating.value,
        comment: historyComment.value.trim(),
      })
      history.value = history.value.map((entry) => (entry.id === updated.id ? updated : entry))
      notice.value = "History updated."
    } else {
      const created = await addConsumptionHistory(item.value.id, {
        consumed_at: toISOString(historyDate.value),
        rating: historyRating.value,
        comment: historyComment.value.trim(),
      })
      history.value = [created, ...history.value]
      notice.value = "Consumption recorded."
    }
    historyDialog.value = false
    await loadAll()
  } catch (cause) {
    error.value = formatApiError(cause, "Failed to save history")
  } finally {
    savingHistory.value = false
  }
}

async function removeHistory(entry: ConsumptionHistory) {
  if (!window.confirm("Delete this consumption record?")) return
  error.value = ""
  notice.value = ""
  try {
    await deleteConsumptionHistory(entry.id)
    history.value = history.value.filter((item) => item.id !== entry.id)
    notice.value = "History deleted."
    await loadAll()
  } catch (cause) {
    error.value = formatApiError(cause, "Failed to delete history")
  }
}

async function runMerge() {
  if (!item.value || !mergeSourceId.value.trim()) return
  merging.value = true
  error.value = ""
  notice.value = ""
  try {
    item.value = await mergeItems(item.value.id, mergeSourceId.value.trim())
    mergeDialog.value = false
    mergeSourceId.value = ""
    notice.value = "Merged successfully."
    await loadAll()
  } catch (cause) {
    error.value = formatApiError(cause, "Failed to merge items")
  } finally {
    merging.value = false
  }
}

function openChild(child: ContentItem) {
  void router.push({ name: "detail", params: { id: child.id } })
}

onMounted(() => {
  void loadAll().then(() => {
    if (route.query.showMerge === "1") mergeDialog.value = true
  })
})
watch(
  () => props.id,
  () => void loadAll(),
)
</script>

<template>
  <v-container class="py-8">
    <v-btn variant="text" prepend-icon="mdi-arrow-left" :to="{ name: 'list' }">
      Back to list
    </v-btn>

    <v-progress-linear v-if="loading" indeterminate class="mt-4" />

    <template v-else-if="item">
      <v-breadcrumbs
        v-if="parentChain.length > 0"
        class="px-0"
        :items="[
          ...parentChain.map((parent) => ({
            title: parent.title,
            to: { name: 'detail', params: { id: parent.id } },
          })),
          { title: item.title },
        ]"
      />

      <h1 class="text-h4 mb-2">{{ item.title }}</h1>
      <p class="text-medium-emphasis mb-6">
        {{ item.content_type }} · {{ item.status }} · revision {{ item.revision }}
      </p>

      <v-alert
        v-if="error"
        class="mb-4"
        closable
        type="error"
        :text="error"
        @click:close="error = ''"
      />
      <v-alert
        v-if="notice"
        class="mb-4"
        closable
        type="success"
        :text="notice"
        @click:close="notice = ''"
      />

      <v-card class="mb-6" title="Details">
        <v-card-text>
          <v-text-field v-model="editTitle" label="Title" />
          <v-row>
            <v-col cols="12" md="6">
              <v-select
                v-model="editContentType"
                :items="contentTypeOptions"
                label="Content type"
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-select v-model="editStatus" :items="statusOptions" label="Status" />
            </v-col>
          </v-row>
          <v-textarea v-model="editDescription" label="Description" rows="3" />
          <v-text-field
            v-model="editParentId"
            label="Parent ID (empty for top-level)"
            hint="Changing the parent moves this item in the hierarchy"
            persistent-hint
          />
          <p class="text-body-2 mt-4">
            Published: {{ formatDateTime(item.published_at) }} · Duration:
            {{ item.duration_seconds ?? "-" }} · Updated: {{ formatDateTime(item.updated_at) }}
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="error" variant="text" @click="removeItem">Delete</v-btn>
          <v-btn color="primary" :loading="savingEdit" @click="saveEdit">Save</v-btn>
        </v-card-actions>
      </v-card>

      <v-card class="mb-6" title="Children">
        <v-card-text>
          <v-alert v-if="children.length === 0" type="info" text="No children." />
          <v-list v-else lines="one">
            <v-list-item
              v-for="child in children"
              :key="child.id"
              :title="child.title"
              :subtitle="`${child.content_type} · ${child.status}`"
              @click="openChild(child)"
            />
          </v-list>
        </v-card-text>
      </v-card>

      <v-card class="mb-6" title="Links">
        <v-card-text>
          <v-alert v-if="links.length === 0" type="info" text="No links yet." />
          <v-list v-else lines="one">
            <v-list-item
              v-for="link in links"
              :key="link.id"
              :title="link.url"
              :subtitle="link.link_type"
            >
              <template #append>
                <v-btn
                  icon="mdi-delete"
                  size="small"
                  variant="text"
                  title="Delete link"
                  @click="removeLink(link)"
                />
              </template>
            </v-list-item>
          </v-list>
          <v-row class="mt-2">
            <v-col cols="12" md="8">
              <v-text-field v-model="newLinkUrl" label="URL (https://…)" hide-details />
            </v-col>
            <v-col cols="12" md="2">
              <v-select
                v-model="newLinkType"
                :items="[
                  { title: 'Source', value: 'source' },
                  { title: 'Info', value: 'info' },
                ]"
                label="Type"
                hide-details
              />
            </v-col>
            <v-col cols="12" md="2" class="d-flex align-center">
              <v-btn
                color="primary"
                :disabled="!newLinkUrl.trim()"
                :loading="savingLink"
                @click="saveLink"
              >
                Add
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <v-card class="mb-6" title="Consumption history">
        <v-card-text>
          <v-alert v-if="history.length === 0" type="info" text="No consumption records yet." />
          <v-list v-else lines="two">
            <v-list-item
              v-for="entry in history"
              :key="entry.id"
              :title="formatDateTime(entry.consumed_at)"
              :subtitle="`Rating: ${entry.rating ?? '-'} · ${entry.comment || 'no comment'}`"
            >
              <template #append>
                <v-btn
                  icon="mdi-pencil"
                  size="small"
                  variant="text"
                  title="Edit"
                  @click="openEditHistoryDialog(entry)"
                />
                <v-btn
                  icon="mdi-delete"
                  size="small"
                  variant="text"
                  title="Delete"
                  @click="removeHistory(entry)"
                />
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" variant="tonal" @click="openAddHistoryDialog">
            Record consumption
          </v-btn>
        </v-card-actions>
      </v-card>

      <v-card class="mb-6" title="Merge duplicate">
        <v-card-text>
          <p class="text-body-2">
            Merge another item into this one. Its links, history, and children move here, then the
            source item is deleted.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="warning" variant="tonal" @click="mergeDialog = true"> Merge… </v-btn>
        </v-card-actions>
      </v-card>

      <v-dialog v-model="historyDialog" max-width="520">
        <v-card :title="editingHistoryId ? 'Edit consumption' : 'Record consumption'">
          <v-card-text>
            <v-text-field v-model="historyDate" label="Consumed at" type="datetime-local" />
            <v-select v-model="historyRating" :items="[1, 2, 3, 4, 5]" clearable label="Rating" />
            <v-textarea v-model="historyComment" label="Comment" rows="3" />
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn @click="historyDialog = false">Cancel</v-btn>
            <v-btn color="primary" :loading="savingHistory" @click="saveHistoryDialog">
              Save
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-dialog v-model="mergeDialog" max-width="520">
        <v-card :title="`Merge into ${item.title}`">
          <v-card-text>
            <v-text-field v-model="mergeSourceId" label="Source item ID" autofocus />
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn @click="mergeDialog = false">Cancel</v-btn>
            <v-btn
              color="warning"
              :disabled="!mergeSourceId.trim()"
              :loading="merging"
              @click="runMerge"
            >
              Merge
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </template>
  </v-container>
</template>
