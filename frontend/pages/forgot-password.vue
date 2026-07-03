<script setup lang="ts">
const state = reactive({
  email: "",
})

const isSubmitting = ref(false)
const submitted = ref(false)

const { apiFetch } = useApi()

async function handleSubmit() {
  isSubmitting.value = true
  try {
    await apiFetch("/auth/password-reset/request", {
      method: "POST",
      body: { email: state.email },
    })
  } finally {
    // Always show the same outcome, whether or not the email matched an
    // account — the backend's response is generic for the same reason.
    submitted.value = true
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex max-w-sm flex-col gap-6">
    <div class="text-center">
      <h1 class="text-2xl font-semibold text-(--ui-text-highlighted)">
        Forgot password
      </h1>
      <p class="mt-1 text-sm text-(--ui-text-muted)">
        We'll email you a link to reset it.
      </p>
    </div>

    <UCard v-if="!submitted">
      <UForm :state="state" class="flex flex-col gap-4" @submit="handleSubmit">
        <UFormField label="Email" name="email" required>
          <UInput v-model="state.email" type="email" class="w-full" autocomplete="email" />
        </UFormField>

        <UButton type="submit" block :loading="isSubmitting">Send reset link</UButton>
      </UForm>
    </UCard>

    <UCard v-else>
      <UAlert
        color="success"
        variant="subtle"
        title="Check your email"
        description="If that email exists, we've sent password reset instructions."
      />
    </UCard>

    <p class="text-center text-sm text-(--ui-text-muted)">
      Remembered it?
      <ULink to="/login" class="font-medium text-(--ui-primary)">Log in</ULink>
    </p>
  </div>
</template>
