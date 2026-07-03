<script setup lang="ts">
const route = useRoute()
const token = computed(() => String(route.query.token ?? ""))

const state = reactive({
  password: "",
  confirmPassword: "",
})

const errorMessage = ref("")
const isSubmitting = ref(false)

const { apiFetch } = useApi()
const toast = useToast()

async function handleSubmit() {
  errorMessage.value = ""

  if (!token.value) {
    errorMessage.value = "This reset link is missing its token."
    return
  }
  if (state.password !== state.confirmPassword) {
    errorMessage.value = "Passwords don't match."
    return
  }

  isSubmitting.value = true
  try {
    await apiFetch("/auth/password-reset/confirm", {
      method: "POST",
      body: { token: token.value, new_password: state.password },
    })
    toast.add({ title: "Password reset. Please log in.", color: "success" })
    await navigateTo("/login")
  } catch {
    errorMessage.value = "This reset link is invalid or has expired."
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex max-w-sm flex-col gap-6">
    <div class="text-center">
      <h1 class="text-2xl font-semibold text-(--ui-text-highlighted)">
        Reset password
      </h1>
      <p class="mt-1 text-sm text-(--ui-text-muted)">Choose a new password.</p>
    </div>

    <UCard>
      <UForm :state="state" class="flex flex-col gap-4" @submit="handleSubmit">
        <UAlert
          v-if="errorMessage"
          color="error"
          variant="subtle"
          :title="errorMessage"
        />

        <UFormField label="New password" name="password" required>
          <UInput
            v-model="state.password"
            type="password"
            class="w-full"
            autocomplete="new-password"
          />
        </UFormField>

        <UFormField label="Confirm new password" name="confirmPassword" required>
          <UInput
            v-model="state.confirmPassword"
            type="password"
            class="w-full"
            autocomplete="new-password"
          />
        </UFormField>

        <UButton type="submit" block :loading="isSubmitting">Reset password</UButton>
      </UForm>
    </UCard>
  </div>
</template>
