<script setup lang="ts">
import type { Memoir } from "~/types/memoir"

definePageMeta({ middleware: "auth" })

const auth = useAuthStore()
const { apiFetch } = useApi()
const toast = useToast()

const memoir = ref<Memoir | null>(null)
const isTriggering = ref(false)
const isDownloading = ref(false)

const isStoryteller = computed(() => auth.user?.user_type === "storyteller")

async function loadMemoir() {
  try {
    memoir.value = await apiFetch<Memoir>("/memoir")
  } catch (error) {
    if ((error as { response?: { status?: number } })?.response?.status === 404) {
      memoir.value = null
    } else {
      throw error
    }
  }
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

onBeforeUnmount(stopPolling)

async function triggerGenerate() {
  isTriggering.value = true
  try {
    memoir.value = await apiFetch<Memoir>("/memoir/generate", { method: "POST" })
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
  if (memoir.value?.status === "failed") return "Try again"
  return memoir.value ? "Regenerate Memoir" : "Generate Memoir"
})

const isBusy = computed(
  () => memoir.value?.status === "pending" || memoir.value?.status === "processing",
)
</script>

<template>
  <div class="mx-auto flex max-w-2xl flex-col gap-6">
    <div>
      <h1 class="font-heading text-2xl font-semibold text-(--ui-text-highlighted)">
        Memoir
      </h1>
      <p class="text-sm text-(--ui-text-muted)">
        A written memoir, woven together from every answered question.
      </p>
    </div>

    <UCard>
      <div class="flex flex-col items-center gap-4 py-6 text-center">
        <p v-if="!memoir" class="text-(--ui-text-muted)">No memoir has been created yet.</p>

        <template v-else-if="isBusy">
          <p class="text-(--ui-text-highlighted)">Generating your memoir…</p>
          <p class="text-sm text-(--ui-text-muted)">This can take a minute or two.</p>
        </template>

        <template v-else-if="memoir.status === 'failed'">
          <p class="text-(--ui-error)">
            Something went wrong generating the memoir.
          </p>
        </template>

        <template v-else-if="memoir.status === 'completed'">
          <p class="text-(--ui-text-highlighted)">Your memoir is ready.</p>
          <UButton
            icon="i-lucide-download"
            :loading="isDownloading"
            @click="downloadPdf"
          >
            Download PDF
          </UButton>
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
  </div>
</template>
