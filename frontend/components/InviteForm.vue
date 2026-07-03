<script setup lang="ts">
import type { UserType } from "~/types/auth"

const props = defineProps<{
  canInviteStoryteller: boolean
  canInviteViewer: boolean
}>()

const emit = defineEmits<{
  submit: [payload: { email: string; user_type: UserType }]
  cancel: []
}>()

const options = computed(() => {
  const opts: { label: string; value: UserType }[] = []
  if (props.canInviteStoryteller) opts.push({ label: "Storyteller", value: "storyteller" })
  if (props.canInviteViewer) opts.push({ label: "Viewer", value: "viewer" })
  return opts
})

const state = reactive({
  email: "",
  userType: options.value[0]?.value as UserType,
})

function handleSubmit() {
  emit("submit", { email: state.email, user_type: state.userType })
}
</script>

<template>
  <UForm :state="state" class="flex flex-col gap-4" @submit="handleSubmit">
    <UFormField label="Email" name="email" required>
      <UInput v-model="state.email" type="email" class="w-full" autocomplete="email" />
    </UFormField>

    <UFormField label="Invite as" name="userType" required>
      <USelect v-model="state.userType" :items="options" value-key="value" class="w-full" />
    </UFormField>

    <div class="flex justify-end gap-2 pt-2">
      <UButton color="neutral" variant="ghost" @click="emit('cancel')">Cancel</UButton>
      <UButton type="submit">Send invite</UButton>
    </div>
  </UForm>
</template>
