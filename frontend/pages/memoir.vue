<script setup lang="ts">
import type { Memoir } from "~/types/memoir"

definePageMeta({ middleware: "auth" })

const auth = useAuthStore()
const { apiFetch } = useApi()
const toast = useToast()

const memoir = ref<Memoir | null>(null)
const draftText = ref("")
const coverPhotoUrl = ref<string | null>(null)
const photoInput = ref<HTMLInputElement | null>(null)

const isTriggering = ref(false)
const isSavingContent = ref(false)
const isUploadingPhoto = ref(false)
const isRemovingPhoto = ref(false)
const isRendering = ref(false)
const isDownloading = ref(false)

const isStoryteller = computed(() => auth.user?.user_type === "storyteller")
const isBusy = computed(
  () => memoir.value?.status === "pending" || memoir.value?.status === "processing",
)
const isFailed = computed(() => memoir.value?.status === "failed")
const isCompleted = computed(() => memoir.value?.status === "completed")
const hasDraft = computed(() => !!memoir.value?.content)

function applyMemoir(next: Memoir | null) {
  memoir.value = next
  draftText.value = next?.content ?? ""
}

async function loadCoverPhoto() {
  if (coverPhotoUrl.value) {
    URL.revokeObjectURL(coverPhotoUrl.value)
    coverPhotoUrl.value = null
  }
  if (memoir.value?.has_cover_photo) {
    const blob = await apiFetch<Blob>("/memoir/photo", { responseType: "blob" })
    coverPhotoUrl.value = URL.createObjectURL(blob)
  }
}

async function loadMemoir() {
  try {
    applyMemoir(await apiFetch<Memoir>("/memoir"))
  } catch (error) {
    if ((error as { response?: { status?: number } })?.response?.status === 404) {
      applyMemoir(null)
    } else {
      throw error
    }
  }
  await loadCoverPhoto()
}

await loadMemoir()

let pollTimer: ReturnType<typeof setInterval> | null = null

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(
  () => memoir.value?.status,
  (status) => {
    stopPolling()
    if (status === "pending" || status === "processing") {
      pollTimer = setInterval(loadMemoir, 3000)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  stopPolling()
  if (coverPhotoUrl.value) URL.revokeObjectURL(coverPhotoUrl.value)
})

async function triggerGenerate() {
  isTriggering.value = true
  try {
    applyMemoir(await apiFetch<Memoir>("/memoir/generate", { method: "POST" }))
    await loadCoverPhoto()
  } catch {
    toast.add({
      title: "Could not start memoir generation",
      description: "Answer at least one question before generating a memoir.",
      color: "error",
    })
  } finally {
    isTriggering.value = false
  }
}

async function saveContent() {
  isSavingContent.value = true
  try {
    applyMemoir(
      await apiFetch<Memoir>("/memoir", {
        method: "PUT",
        body: { content: draftText.value },
      }),
    )
    toast.add({ title: "Draft updated", color: "success" })
  } catch {
    toast.add({ title: "Could not save changes", color: "error" })
  } finally {
    isSavingContent.value = false
  }
}

async function handlePhotoSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  isUploadingPhoto.value = true
  try {
    const formData = new FormData()
    formData.append("file", file)
    applyMemoir(
      await apiFetch<Memoir>("/memoir/photo", { method: "PUT", body: formData }),
    )
    await loadCoverPhoto()
    toast.add({ title: "Cover photo updated", color: "success" })
  } catch {
    toast.add({ title: "Could not upload photo", color: "error" })
  } finally {
    isUploadingPhoto.value = false
    input.value = ""
  }
}

async function removePhoto() {
  isRemovingPhoto.value = true
  try {
    applyMemoir(await apiFetch<Memoir>("/memoir/photo", { method: "DELETE" }))
    await loadCoverPhoto()
    toast.add({ title: "Cover photo removed", color: "success" })
  } catch {
    toast.add({ title: "Could not remove photo", color: "error" })
  } finally {
    isRemovingPhoto.value = false
  }
}

async function generatePdf() {
  isRendering.value = true
  try {
    applyMemoir(await apiFetch<Memoir>("/memoir/render", { method: "POST" }))
    toast.add({ title: "PDF generated", color: "success" })
  } catch {
    toast.add({ title: "Could not generate PDF", color: "error" })
  } finally {
    isRendering.value = false
  }
}

async function downloadPdf() {
  isDownloading.value = true
  try {
    const blob = await apiFetch<Blob>("/memoir/pdf", { responseType: "blob" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = "memoir.pdf"
    link.click()
    URL.revokeObjectURL(url)
  } catch {
    toast.add({ title: "Could not download memoir", color: "error" })
  } finally {
    isDownloading.value = false
  }
}

const generateButtonLabel = computed(() => {
  if (isFailed.value) return "Try again"
  return memoir.value ? "Regenerate Draft" : "Generate Draft"
})
</script>

<template>
  <div class="mx-auto flex max-w-2xl flex-col gap-6">
    <div>
      <h1 class="font-heading text-2xl font-semibold text-(--ui-text-highlighted)">
        Memoir
      </h1>
      <p class="text-sm text-(--ui-text-muted)">
        Review your memoir before generating the final PDF.
      </p>
    </div>

    <UCard>
      <div class="flex flex-col items-center gap-4 py-6 text-center">
        <p v-if="!memoir" class="text-(--ui-text-muted)">No memoir has been created yet.</p>

        <template v-else-if="isBusy">
          <p class="text-(--ui-text-highlighted)">Generating your memoir draft…</p>
          <p class="text-sm text-(--ui-text-muted)">This can take a minute or two.</p>
        </template>

        <template v-else-if="isFailed">
          <p class="text-(--ui-error)">Something went wrong generating the draft.</p>
        </template>

        <template v-else-if="isCompleted">
          <p class="text-(--ui-text-highlighted)">Your memoir is ready.</p>
          <UButton
            icon="i-lucide-download"
            :loading="isDownloading"
            @click="downloadPdf"
          >
            Download PDF
          </UButton>
        </template>

        <template v-else-if="hasDraft && isStoryteller">
          <p class="text-(--ui-text-muted)">
            Review your draft below, then generate the final PDF.
          </p>
        </template>

        <template v-else-if="hasDraft">
          <p class="text-(--ui-text-muted)">The storyteller is still reviewing the memoir.</p>
        </template>

        <UButton
          v-if="isStoryteller && !isBusy"
          color="neutral"
          variant="outline"
          icon="i-lucide-book-open"
          :loading="isTriggering"
          @click="triggerGenerate"
        >
          {{ generateButtonLabel }}
        </UButton>
      </div>
    </UCard>

    <UCard v-if="isStoryteller && hasDraft">
      <template #header>
        <p class="text-sm font-medium text-(--ui-text-highlighted)">Review &amp; edit</p>
      </template>

      <div class="flex flex-col gap-4">
        <UFormField label="Memoir text" name="content">
          <UTextarea v-model="draftText" class="w-full" :rows="16" />
        </UFormField>
        <div class="flex justify-end">
          <UButton :loading="isSavingContent" @click="saveContent">Save changes</UButton>
        </div>

        <div class="flex flex-col gap-3 border-t border-(--ui-border) pt-4">
          <p class="text-sm font-medium text-(--ui-text-highlighted)">Cover photo</p>
          <img
            v-if="coverPhotoUrl"
            :src="coverPhotoUrl"
            class="max-h-48 w-auto self-start rounded-md"
          />
          <div class="flex items-center gap-2">
            <UButton
              color="neutral"
              variant="outline"
              icon="i-lucide-image"
              :loading="isUploadingPhoto"
              @click="photoInput?.click()"
            >
              {{ memoir?.has_cover_photo ? "Replace photo" : "Upload photo" }}
            </UButton>
            <UButton
              v-if="memoir?.has_cover_photo"
              color="error"
              variant="ghost"
              icon="i-lucide-trash-2"
              :loading="isRemovingPhoto"
              @click="removePhoto"
            >
              Remove
            </UButton>
          </div>
          <input
            ref="photoInput"
            type="file"
            accept="image/*"
            class="hidden"
            @change="handlePhotoSelected"
          />
        </div>

        <div class="flex justify-end border-t border-(--ui-border) pt-4">
          <UButton icon="i-lucide-file-text" :loading="isRendering" @click="generatePdf">
            Generate PDF
          </UButton>
        </div>
      </div>
    </UCard>
  </div>
</template>
