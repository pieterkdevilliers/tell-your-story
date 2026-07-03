<script setup lang="ts">
import type { AccountRole, UserType } from "~/types/auth"

const props = withDefaults(
  defineProps<{
    mode: "create" | "edit"
    isOwner: boolean
    isStoryRequester: boolean
    hasStoryteller: boolean
    initialEmail?: string
    initialRole?: AccountRole
    initialUserType?: UserType
  }>(),
  { initialEmail: "", initialRole: "member", initialUserType: "viewer" },
)

const emit = defineEmits<{
  submit: [payload: { email: string; password: string; role: AccountRole; user_type: UserType }]
  cancel: []
}>()

const userTypeOptions = computed(() => {
  const opts: { label: string; value: UserType }[] = []
  if (props.isStoryRequester && (!props.hasStoryteller || props.initialUserType === "storyteller")) {
    opts.push({ label: "Storyteller", value: "storyteller" })
  }
  opts.push({ label: "Viewer", value: "viewer" })
  return opts
})

const defaultUserType = userTypeOptions.value.some((o) => o.value === props.initialUserType)
  ? props.initialUserType
  : userTypeOptions.value[0]?.value

const state = reactive({
  email: props.initialEmail,
  password: "",
  role: props.initialRole as AccountRole,
  userType: defaultUserType as UserType,
})

const roleOptions = [
  { label: "Member", value: "member" },
  { label: "Owner", value: "owner" },
]

function handleSubmit() {
  emit("submit", {
    email: state.email,
    password: state.password,
    role: state.role,
    user_type: state.userType,
  })
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

    <UFormField v-if="props.isOwner" label="Type" name="userType">
      <USelect
        v-model="state.userType"
        :items="userTypeOptions"
        value-key="value"
        class="w-full"
      />
    </UFormField>

    <div class="flex justify-end gap-2 pt-2">
      <UButton color="neutral" variant="ghost" @click="emit('cancel')">Cancel</UButton>
      <UButton type="submit">{{ props.mode === "create" ? "Add user" : "Save" }}</UButton>
    </div>
  </UForm>
</template>
