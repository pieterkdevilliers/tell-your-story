<script setup lang="ts">
import type { Question } from "~/types/question"

definePageMeta({ middleware: "auth" })

const auth = useAuthStore()
const { apiFetch } = useApi()
const toast = useToast()

const questions = ref<Question[]>([])
const isAddOpen = ref(false)
const newQuestionText = ref("")
const isSubmitting = ref(false)

const isOwner = computed(() => auth.user?.role === "owner")

async function loadQuestions() {
  questions.value = await apiFetch<Question[]>("/questions")
}

async function handleAdd() {
  if (!newQuestionText.value.trim()) return
  isSubmitting.value = true
  try {
    await apiFetch("/questions", {
      method: "POST",
      body: { text: newQuestionText.value.trim() },
    })
    newQuestionText.value = ""
    isAddOpen.value = false
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
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-(--ui-text-highlighted)">Questions</h1>
        <p class="text-sm text-(--ui-text-muted)">
          The questions the storyteller will be asked.
        </p>
      </div>
      <UButton v-if="isOwner" icon="i-lucide-plus" @click="isAddOpen = true">
        Add question
      </UButton>
    </div>

    <UCard :ui="{ body: 'p-0 sm:p-0' }">
      <ul class="divide-y divide-(--ui-border)">
        <li
          v-for="(question, index) in questions"
          :key="question.id"
          class="flex items-center justify-between gap-4 px-4 py-3"
        >
          <span class="text-sm text-(--ui-text-highlighted)">
            <span class="text-(--ui-text-muted)">{{ index + 1 }}.</span>
            {{ question.text }}
          </span>
          <UButton
            v-if="isOwner"
            color="error"
            variant="ghost"
            size="sm"
            icon="i-lucide-trash-2"
            @click="handleDelete(question)"
          />
        </li>
      </ul>
    </UCard>

    <UModal v-model:open="isAddOpen" title="Add question">
      <template #body>
        <div class="flex flex-col gap-4">
          <UFormField label="Question" name="text" required>
            <UTextarea v-model="newQuestionText" class="w-full" autofocus />
          </UFormField>
          <div class="flex justify-end gap-2 pt-2">
            <UButton color="neutral" variant="ghost" @click="isAddOpen = false">
              Cancel
            </UButton>
            <UButton :loading="isSubmitting" @click="handleAdd">Add question</UButton>
          </div>
        </div>
      </template>
    </UModal>
  </div>
</template>
