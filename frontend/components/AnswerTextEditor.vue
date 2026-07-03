<script setup lang="ts">
import type { Answer } from "~/types/question"

const props = defineProps<{
  questionId: number
  existingAnswer: Answer | null
}>()

const emit = defineEmits<{
  saved: [answer: Answer]
  deleted: []
}>()

const { apiFetch } = useApi()
const toast = useToast()

const text = ref(props.existingAnswer?.answer_type === "text" ? props.existingAnswer.text ?? "" : "")
const isSaving = ref(false)
const isDeleting = ref(false)

const hasExistingTextAnswer = computed(
  () => props.existingAnswer?.answer_type === "text",
)

watch(
  () => props.existingAnswer,
  (answer) => {
    text.value = answer?.answer_type === "text" ? answer.text ?? "" : ""
  },
)

async function handleSave() {
  isSaving.value = true
  try {
    const answer = await apiFetch<Answer>(`/questions/${props.questionId}/answer`, {
      method: "PUT",
      body: { text: text.value },
    })
    emit("saved", answer)
    toast.add({ title: "Answer saved", color: "success" })
  } catch {
    toast.add({ title: "Could not save answer", color: "error" })
  } finally {
    isSaving.value = false
  }
}

async function handleDelete() {
  isDeleting.value = true
  try {
    await apiFetch(`/questions/${props.questionId}/answer`, { method: "DELETE" })
    text.value = ""
    emit("deleted")
    toast.add({ title: "Answer deleted", color: "success" })
  } catch {
    toast.add({ title: "Could not delete answer", color: "error" })
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <UCard>
    <UFormField label="Your answer" name="answer">
      <UTextarea v-model="text" class="w-full" :rows="6" />
    </UFormField>
    <div class="flex justify-end gap-2 pt-4">
      <UButton
        v-if="hasExistingTextAnswer"
        color="error"
        variant="outline"
        icon="i-lucide-trash-2"
        :loading="isDeleting"
        @click="handleDelete"
      >
        Delete
      </UButton>
      <UButton :loading="isSaving" @click="handleSave">Save answer</UButton>
    </div>
  </UCard>
</template>
