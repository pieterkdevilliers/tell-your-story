<script setup lang="ts">
import type { Answer, Question } from "~/types/question"

definePageMeta({ middleware: "auth" })

const route = useRoute()
const auth = useAuthStore()
const { apiFetch } = useApi()
const toast = useToast()

const questions = ref<Question[]>([])
const answerText = ref("")
const isSaving = ref(false)

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

watch(
  currentQuestion,
  (question) => {
    answerText.value = question?.answer?.text ?? ""
  },
  { immediate: true },
)

async function handleSave() {
  if (!currentQuestion.value) return
  isSaving.value = true
  try {
    const answer = await apiFetch<Answer>(
      `/questions/${currentQuestion.value.id}/answer`,
      { method: "PUT", body: { text: answerText.value } },
    )
    currentQuestion.value.answer = answer
    toast.add({ title: "Answer saved", color: "success" })
  } catch {
    toast.add({ title: "Could not save answer", color: "error" })
  } finally {
    isSaving.value = false
  }
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
        <p class="text-xl font-semibold text-(--ui-text-highlighted)">
          {{ currentQuestion.text }}
        </p>
      </UCard>

      <UCard v-if="isStoryteller">
        <UFormField label="Your answer" name="answer">
          <UTextarea v-model="answerText" class="w-full" :rows="6" />
        </UFormField>
        <div class="flex justify-end pt-4">
          <UButton :loading="isSaving" @click="handleSave">Save answer</UButton>
        </div>
      </UCard>

      <UCard v-else-if="currentQuestion.answer">
        <p class="text-sm font-medium text-(--ui-text-muted)">Answer</p>
        <p class="mt-1 whitespace-pre-wrap text-(--ui-text-highlighted)">
          {{ currentQuestion.answer.text }}
        </p>
      </UCard>

      <UCard v-else :ui="{ body: 'text-center text-(--ui-text-muted)' }">
        No answer yet.
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
