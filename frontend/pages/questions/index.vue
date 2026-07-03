<script setup lang="ts">
import type { Question, QuestionCategory } from "~/types/question"

definePageMeta({ middleware: "auth" })

const auth = useAuthStore()
const { apiFetch } = useApi()
const toast = useToast()

const questions = ref<Question[]>([])
const addingCategory = ref<QuestionCategory | null>(null)
const newQuestionText = ref("")
const isSubmitting = ref(false)

const isOwner = computed(() => auth.user?.role === "owner")

const sections = computed(() =>
  QUESTION_CATEGORY_ORDER.map((category) => ({
    category,
    label: QUESTION_CATEGORY_LABELS[category],
    questions: questions.value.filter((q) => q.category === category),
  })).filter((section) => section.questions.length > 0),
)

async function loadQuestions() {
  questions.value = await apiFetch<Question[]>("/questions")
}

function openAdd(category: QuestionCategory) {
  addingCategory.value = category
  newQuestionText.value = ""
}

async function handleAdd() {
  if (!addingCategory.value || !newQuestionText.value.trim()) return
  isSubmitting.value = true
  try {
    await apiFetch("/questions", {
      method: "POST",
      body: { category: addingCategory.value, text: newQuestionText.value.trim() },
    })
    addingCategory.value = null
    await loadQuestions()
    toast.add({ title: "Question added", color: "success" })
  } catch {
    toast.add({ title: "Could not add question", color: "error" })
  } finally {
    isSubmitting.value = false
  }
}

async function handleDelete(question: Question) {
  try {
    await apiFetch(`/questions/${question.id}`, { method: "DELETE" })
    await loadQuestions()
    toast.add({ title: "Question deleted", color: "success" })
  } catch {
    toast.add({ title: "Could not delete question", color: "error" })
  }
}

await loadQuestions()
</script>

<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-semibold text-(--ui-text-highlighted)">Questions</h1>
      <p class="text-sm text-(--ui-text-muted)">
        The questions the storyteller will be asked.
      </p>
    </div>

    <UCard v-for="section in sections" :key="section.category" :ui="{ body: 'p-0 sm:p-0' }">
      <template #header>
        <div class="flex items-center justify-between">
          <p class="text-sm font-medium text-(--ui-text-highlighted)">
            {{ section.label }}
          </p>
          <UButton
            v-if="isOwner"
            color="neutral"
            variant="ghost"
            size="sm"
            icon="i-lucide-plus"
            @click="openAdd(section.category)"
          >
            Add question
          </UButton>
        </div>
      </template>

      <ul class="divide-y divide-(--ui-border)">
        <li
          v-for="(question, index) in section.questions"
          :key="question.id"
          class="flex cursor-pointer items-center justify-between gap-4 px-4 py-3 hover:bg-(--ui-bg-elevated)"
          @click="navigateTo(`/questions/${question.id}`)"
        >
          <span class="flex min-w-0 items-center gap-2 text-sm text-(--ui-text-highlighted)">
            <span class="text-(--ui-text-muted)">{{ index + 1 }}.</span>
            <span class="truncate">{{ question.text }}</span>
            <UBadge
              v-if="question.answer"
              color="success"
              variant="subtle"
              size="sm"
              icon="i-lucide-check"
              class="shrink-0"
            >
              Answered
            </UBadge>
          </span>
          <UButton
            v-if="isOwner"
            color="error"
            variant="ghost"
            size="sm"
            icon="i-lucide-trash-2"
            class="shrink-0"
            @click.stop="handleDelete(question)"
          />
        </li>
      </ul>
    </UCard>

    <UModal
      :open="!!addingCategory"
      :title="addingCategory ? `Add question to ${QUESTION_CATEGORY_LABELS[addingCategory]}` : ''"
      @update:open="(v) => !v && (addingCategory = null)"
    >
      <template #body>
        <div class="flex flex-col gap-4">
          <UFormField label="Question" name="text" required>
            <UTextarea v-model="newQuestionText" class="w-full" autofocus />
          </UFormField>
          <div class="flex justify-end gap-2 pt-2">
            <UButton color="neutral" variant="ghost" @click="addingCategory = null">
              Cancel
            </UButton>
            <UButton :loading="isSubmitting" @click="handleAdd">Add question</UButton>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>
