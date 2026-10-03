<script setup lang="ts">
import { ref } from "vue"
import { useRouter } from "vue-router"

import { createItem, formatApiError } from "./api"
import { contentTypeOptions } from "./constants"

const router = useRouter()
const addDialog = ref(false)
const newTitle = ref("")
const newContentType = ref("video")
const savingNewItem = ref(false)
const error = ref("")

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
    const created = await createItem({
      title,
      content_type: newContentType.value,
      status: "planned",
    })
    addDialog.value = false
    await router.push({ name: "detail", params: { id: created.id } })
  } catch (cause) {
    error.value = formatApiError(cause, "Failed to create content")
  } finally {
    savingNewItem.value = false
  }
}
</script>

<template>
  <v-app>
    <v-app-bar title="content-tracker">
      <template #append>
        <v-btn prepend-icon="mdi-plus" @click="openAddDialog"> Add content </v-btn>
      </template>
    </v-app-bar>

    <v-main>
      <v-alert
        v-if="error"
        class="ma-4"
        closable
        type="error"
        :text="error"
        @click:close="error = ''"
      />
      <router-view :key="$route.fullPath" />
    </v-main>

    <v-dialog v-model="addDialog" max-width="520">
      <v-card title="Add content">
        <v-card-text>
          <v-text-field v-model="newTitle" autofocus label="Title" @keyup.enter="saveNewItem" />
          <v-select v-model="newContentType" :items="contentTypeOptions" label="Content type" />
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
  </v-app>
</template>
