<script setup lang="ts">
import type { AccountRole } from "~/types/auth"

const props = withDefaults(
  defineProps<{
    mode: "create" | "edit"
    isOwner: boolean
    initialEmail?: string
    initialRole?: AccountRole
  }>(),
  { initialEmail: "", initialRole: "member" },
)

const emit = defineEmits<{
  submit: [payload: { email: string; password: string; role: AccountRole }]
  cancel: []
}>()

const state = reactive({
  email: props.initialEmail,
  password: "",
  role: props.initialRole as AccountRole,
})

const roleOptions = [
  { label: "Member", value: "member" },
  { label: "Owner", value: "owner" },
]

function handleSubmit() {
  emit("submit", { email: state.email, password: state.password, role: state.role })
}
</script>

<template>
  <UForm :state="state" class="flex flex-col gap-4" @submit="handleSubmit">
    <UFormField label="Email" name="email" required>
      <UInput v-model="state.email" type="email" class="w-full" autocomplete="email" />
    </UFormField>

    <UFormField
      :label="props.mode === 'create' ? 'Password' : 'New password'"
      name="password"
      :hint="props.mode === 'edit' ? 'Leave blank to keep current password' : undefined"
      :required="props.mode === 'create'"
    >
      <UInput
        v-model="state.password"
        type="password"
        class="w-full"
        autocomplete="new-password"
      />
    </UFormField>

    <UFormField v-if="props.isOwner" label="Role" name="role">
      <USelect v-model="state.role" :items="roleOptions" value-key="value" class="w-full" />
    </UFormField>

    <div class="flex justify-end gap-2 pt-2">
      <UButton color="neutral" variant="ghost" @click="emit('cancel')">Cancel</UButton>
      <UButton type="submit">{{ props.mode === "create" ? "Add user" : "Save" }}</UButton>
    </div>
  </UForm>
</template>
