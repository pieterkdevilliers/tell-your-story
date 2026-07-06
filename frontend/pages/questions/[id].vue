<script setup lang="ts">
import type { Answer, AnswerType, Question } from "~/types/question"

definePageMeta({ middleware: "auth" })

const route = useRoute()
const auth = useAuthStore()
const { apiFetch } = useApi()

const questions = ref<Question[]>([])
const activeTab = ref<AnswerType>("text")
const readOnlyMediaUrl = ref<string | null>(null)

async function loadQuestions() {
  questions.value = await apiFetch<Question[]>("/questions")
}

await loadQuestions()

const isStoryteller = computed(() => auth.user?.user_type === "storyteller")

const currentIndex = computed(() =>
  questions.value.findIndex((q) => String(q.id) === route.params.id),
)
const currentQuestion = computed(() =>
  currentIndex.value === -1 ? null : questions.value[currentIndex.value],
)
const previousQuestion = computed(() =>
  currentIndex.value > 0 ? questions.value[currentIndex.value - 1] : null,
)
const nextQuestion = computed(() =>
  currentIndex.value !== -1 && currentIndex.value < questions.value.length - 1
    ? questions.value[currentIndex.value + 1]
    : null,
)

const answerType = computed(() => currentQuestion.value?.answer?.answer_type ?? null)

const transcriptionStatus = computed(
  () => currentQuestion.value?.answer?.transcription_status ?? null,
)

let transcriptionPollTimer: ReturnType<typeof setInterval> | null = null

function stopTranscriptionPolling() {
  if (transcriptionPollTimer) {
    clearInterval(transcriptionPollTimer)
    transcriptionPollTimer = null
  }
}

watch(
  transcriptionStatus,
  (status) => {
    stopTranscriptionPolling()
    if (status === "pending" || status === "processing") {
      transcriptionPollTimer = setInterval(loadQuestions, 3000)
    }
  },
  { immediate: true },
)

onBeforeUnmount(stopTranscriptionPolling)

const tabItems = computed(() =>
  (["text", "audio", "video"] as AnswerType[]).map((value) => ({
    label: value === "text" ? "Text" : value === "audio" ? "Audio" : "Video",
    value,
    disabled: answerType.value !== null && answerType.value !== value,
  })),
)

async function loadReadOnlyMedia() {
  if (readOnlyMediaUrl.value) {
    URL.revokeObjectURL(readOnlyMediaUrl.value)
    readOnlyMediaUrl.value = null
  }
  const answer = currentQuestion.value?.answer
  if (!isStoryteller.value && answer && answer.answer_type !== "text") {
    readOnlyMediaUrl.value = await fetchAnswerMediaUrl(apiFetch, answer.question_id)
  }
}

watch(
  currentQuestion,
  (question) => {
    activeTab.value = question?.answer?.answer_type ?? "text"
    loadReadOnlyMedia()
  },
  { immediate: true },
)

function handleAnswerSaved(answer: Answer) {
  if (!currentQuestion.value) return
  currentQuestion.value.answer = answer
}

function handleAnswerDeleted() {
  if (!currentQuestion.value) return
  currentQuestion.value.answer = null
}
</script>

<template>
  <div class="mx-auto flex max-w-2xl flex-col gap-6">
    <ULink to="/questions" class="text-sm text-(--ui-primary)">← Back to Questions</ULink>

    <div v-if="!currentQuestion" class="flex flex-col items-center gap-4 py-16 text-center">
      <p class="text-(--ui-text-highlighted)">Question not found.</p>
      <UButton to="/questions">Back to Questions</UButton>
    </div>

    <template v-else>
      <div>
        <p class="text-sm font-medium text-(--ui-primary)">
          {{ QUESTION_CATEGORY_LABELS[currentQuestion.category] }}
        </p>
        <p class="text-sm text-(--ui-text-muted)">
          Question {{ currentIndex + 1 }} of {{ questions.length }}
        </p>
      </div>

      <UCard>
        <p class="font-heading text-xl font-semibold text-(--ui-text-highlighted)">
          {{ currentQuestion.text }}
        </p>
      </UCard>

      <template v-if="isStoryteller">
        <UTabs v-model="activeTab" :items="tabItems" />
        <p v-if="answerType" class="-mt-2 text-xs text-(--ui-text-muted)">
          Delete your {{ answerType }} answer to switch to a different type.
        </p>

        <AnswerTextEditor
          v-if="activeTab === 'text'"
          :question-id="currentQuestion.id"
          :existing-answer="currentQuestion.answer ?? null"
          @saved="handleAnswerSaved"
          @deleted="handleAnswerDeleted"
        />
        <AnswerRecorder
          v-else-if="activeTab === 'audio'"
          mode="audio"
          :question-id="currentQuestion.id"
          :existing-answer="currentQuestion.answer ?? null"
          @saved="handleAnswerSaved"
          @deleted="handleAnswerDeleted"
        />
        <AnswerRecorder
          v-else
          mode="video"
          :question-id="currentQuestion.id"
          :existing-answer="currentQuestion.answer ?? null"
          @saved="handleAnswerSaved"
          @deleted="handleAnswerDeleted"
        />
      </template>

      <UCard v-else-if="currentQuestion.answer?.answer_type === 'text'">
        <p class="text-sm font-medium text-(--ui-text-muted)">Answer</p>
        <p class="mt-1 whitespace-pre-wrap text-(--ui-text-highlighted)">
          {{ currentQuestion.answer.text }}
        </p>
      </UCard>

      <UCard v-else-if="currentQuestion.answer?.answer_type === 'video'">
        <video
          v-if="readOnlyMediaUrl"
          :src="readOnlyMediaUrl"
          controls
          class="mx-auto w-full max-w-sm rounded-md"
        />
      </UCard>

      <UCard v-else-if="currentQuestion.answer?.answer_type === 'audio'">
        <div class="flex justify-center">
          <audio v-if="readOnlyMediaUrl" :src="readOnlyMediaUrl" controls />
        </div>
      </UCard>

      <UCard v-else :ui="{ body: 'text-center text-(--ui-text-muted)' }">
        No answer yet.
      </UCard>

      <UCard v-if="currentQuestion.answer && currentQuestion.answer.answer_type !== 'text'">
        <p class="text-sm font-medium text-(--ui-text-muted)">Transcript</p>
        <p
          v-if="transcriptionStatus === 'completed'"
          class="mt-1 whitespace-pre-wrap text-(--ui-text-highlighted)"
        >
          {{ currentQuestion.answer.transcript }}
        </p>
        <p v-else-if="transcriptionStatus === 'failed'" class="mt-1 text-(--ui-error)">
          Transcription failed.
        </p>
        <p v-else class="mt-1 italic text-(--ui-text-muted)">Transcribing…</p>
      </UCard>

      <div class="flex justify-between">
        <UButton
          :disabled="!previousQuestion"
          color="neutral"
          variant="outline"
          icon="i-lucide-chevron-left"
          :to="previousQuestion ? `/questions/${previousQuestion.id}` : undefined"
        >
          Previous
        </UButton>
        <UButton
          :disabled="!nextQuestion"
          trailing-icon="i-lucide-chevron-right"
          :to="nextQuestion ? `/questions/${nextQuestion.id}` : undefined"
        >
          Next
        </UButton>
      </div>
    </template>
  </div>
</template>
