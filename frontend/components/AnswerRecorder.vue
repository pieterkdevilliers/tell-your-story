<script setup lang="ts">
import type { Answer } from "~/types/question"

const props = defineProps<{
  mode: "audio" | "video"
  questionId: number
  existingAnswer: Answer | null
}>()

const emit = defineEmits<{
  saved: [answer: Answer]
  deleted: []
}>()

const { apiFetch } = useApi()
const toast = useToast()

type Phase =
  | "loading"
  | "empty"
  | "recording"
  | "preview"
  | "uploading"
  | "saved"
  | "error"

const phase = ref<Phase>("loading")
const errorMessage = ref("")
const elapsedSeconds = ref(0)
const savedUrl = ref<string | null>(null)
const previewUrl = ref<string | null>(null)

const liveVideoEl = ref<HTMLVideoElement | null>(null)

let mediaStream: MediaStream | null = null
let mediaRecorder: MediaRecorder | null = null
let recordedChunks: Blob[] = []
let recordedBlob: Blob | null = null
let elapsedTimer: ReturnType<typeof setInterval> | null = null

const preferredMimeType = computed(() =>
  props.mode === "video" ? "video/webm" : "audio/webm",
)

async function loadExisting() {
  // Guards against navigating to a different question mid-recording, which
  // would otherwise leave the mic/camera stream open indefinitely.
  if (phase.value === "recording") {
    stopStreamTracks()
    clearElapsedTimer()
    mediaRecorder = null
  }
  if (savedUrl.value) {
    URL.revokeObjectURL(savedUrl.value)
    savedUrl.value = null
  }
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
  recordedBlob = null
  if (props.existingAnswer?.answer_type === props.mode) {
    phase.value = "loading"
    try {
      savedUrl.value = await fetchAnswerMediaUrl(apiFetch, props.questionId)
      phase.value = "saved"
    } catch {
      phase.value = "error"
      errorMessage.value = "Could not load the saved recording."
    }
  } else {
    phase.value = "empty"
  }
}

watch(() => props.existingAnswer, loadExisting, { immediate: true })

function stopStreamTracks() {
  mediaStream?.getTracks().forEach((track) => track.stop())
  mediaStream = null
}

function clearElapsedTimer() {
  if (elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
}

function dismissError() {
  phase.value = props.existingAnswer?.answer_type === props.mode ? "saved" : "empty"
}

async function startRecording() {
  errorMessage.value = ""
  let stream: MediaStream
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: props.mode === "video",
    })
  } catch {
    phase.value = "error"
    errorMessage.value =
      props.mode === "video"
        ? "Could not access your camera/microphone. Check your browser permissions and try again."
        : "Could not access your microphone. Check your browser permissions and try again."
    return
  }
  mediaStream = stream

  phase.value = "recording"
  await nextTick()
  if (props.mode === "video" && liveVideoEl.value) {
    liveVideoEl.value.srcObject = mediaStream
  }

  const options = MediaRecorder.isTypeSupported(preferredMimeType.value)
    ? { mimeType: preferredMimeType.value }
    : {}
  recordedChunks = []
  mediaRecorder = new MediaRecorder(mediaStream, options)
  const actualMimeType = mediaRecorder.mimeType || preferredMimeType.value

  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) recordedChunks.push(event.data)
  }
  mediaRecorder.onstop = () => {
    recordedBlob = new Blob(recordedChunks, { type: actualMimeType })
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = URL.createObjectURL(recordedBlob)
    stopStreamTracks()
    clearElapsedTimer()
    phase.value = "preview"
  }
  mediaRecorder.start()

  elapsedSeconds.value = 0
  elapsedTimer = setInterval(() => (elapsedSeconds.value += 1), 1000)
}

function stopRecording() {
  mediaRecorder?.stop()
}

function discardPreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
  recordedBlob = null
  phase.value = savedUrl.value ? "saved" : "empty"
}

async function saveRecording() {
  if (!recordedBlob) return
  phase.value = "uploading"
  try {
    const formData = new FormData()
    formData.append("answer_type", props.mode)
    formData.append("file", recordedBlob, "answer.webm")
    const answer = await apiFetch<Answer>(
      `/questions/${props.questionId}/answer/media`,
      { method: "PUT", body: formData },
    )
    if (previewUrl.value) {
      URL.revokeObjectURL(previewUrl.value)
      previewUrl.value = null
    }
    recordedBlob = null
    emit("saved", answer)
    toast.add({ title: "Answer saved", color: "success" })
  } catch {
    toast.add({ title: "Could not save recording", color: "error" })
    phase.value = "preview"
  }
}

async function deleteExisting() {
  try {
    await apiFetch(`/questions/${props.questionId}/answer`, { method: "DELETE" })
    if (savedUrl.value) {
      URL.revokeObjectURL(savedUrl.value)
      savedUrl.value = null
    }
    emit("deleted")
    toast.add({ title: "Answer deleted", color: "success" })
    phase.value = "empty"
  } catch {
    toast.add({ title: "Could not delete answer", color: "error" })
  }
}

function formatElapsed(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, "0")}`
}

onBeforeUnmount(() => {
  stopStreamTracks()
  clearElapsedTimer()
  if (savedUrl.value) URL.revokeObjectURL(savedUrl.value)
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<template>
  <UCard>
    <div v-if="phase === 'loading'" class="py-8 text-center text-(--ui-text-muted)">
      Loading...
    </div>

    <div v-else-if="phase === 'error'" class="flex flex-col items-center gap-3 py-8 text-center">
      <p class="text-(--ui-text-highlighted)">{{ errorMessage }}</p>
      <UButton color="neutral" variant="outline" @click="dismissError">Dismiss</UButton>
    </div>

    <div v-else-if="phase === 'empty'" class="flex flex-col items-center gap-3 py-8">
      <p class="text-sm text-(--ui-text-muted)">No {{ mode }} answer yet.</p>
      <UButton icon="i-lucide-circle" color="error" @click="startRecording">
        Start recording
      </UButton>
    </div>

    <div v-else-if="phase === 'recording'" class="flex flex-col items-center gap-4 py-4">
      <video
        v-if="mode === 'video'"
        ref="liveVideoEl"
        autoplay
        muted
        playsinline
        class="w-full max-w-sm rounded-md bg-black"
      />
      <div class="flex items-center gap-2 text-(--ui-error)">
        <span class="size-2 animate-pulse rounded-full bg-(--ui-error)" />
        <span class="font-mono text-sm">{{ formatElapsed(elapsedSeconds) }}</span>
      </div>
      <UButton color="error" icon="i-lucide-square" @click="stopRecording">
        Stop recording
      </UButton>
    </div>

    <div
      v-else-if="phase === 'preview' || phase === 'uploading'"
      class="flex flex-col items-center gap-4 py-4"
    >
      <video
        v-if="mode === 'video'"
        :src="previewUrl || ''"
        controls
        class="w-full max-w-sm rounded-md"
      />
      <audio v-else :src="previewUrl || ''" controls />
      <div class="flex gap-2">
        <UButton
          color="neutral"
          variant="outline"
          :disabled="phase === 'uploading'"
          @click="discardPreview"
        >
          Discard
        </UButton>
        <UButton :loading="phase === 'uploading'" @click="saveRecording">
          Save recording
        </UButton>
      </div>
    </div>

    <div v-else-if="phase === 'saved'" class="flex flex-col items-center gap-4 py-4">
      <video
        v-if="mode === 'video'"
        :src="savedUrl || ''"
        controls
        class="w-full max-w-sm rounded-md"
      />
      <audio v-else :src="savedUrl || ''" controls />
      <div class="flex gap-2">
        <UButton
          color="error"
          variant="outline"
          icon="i-lucide-trash-2"
          @click="deleteExisting"
        >
          Delete
        </UButton>
        <UButton
          color="neutral"
          variant="outline"
          icon="i-lucide-circle"
          @click="startRecording"
        >
          Re-record
        </UButton>
      </div>
    </div>
  </UCard>
</template>
