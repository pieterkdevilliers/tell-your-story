<script setup lang="ts">
import type { CurrentAccount, CurrentUser } from "~/types/auth"

const state = reactive({
  accountName: "",
  email: "",
  password: "",
})

const errorMessage = ref("")
const isSubmitting = ref(false)

const auth = useAuthStore()
const { apiFetch } = useApi()

async function handleSubmit() {
  errorMessage.value = ""
  isSubmitting.value = true
  try {
    const response = await apiFetch<{
      account: CurrentAccount
      user: CurrentUser
      access_token: string
    }>("/auth/signup", {
      method: "POST",
      body: {
        account_name: state.accountName,
        email: state.email,
        password: state.password,
      },
    })
    auth.setSession(response.access_token, response.user, response.account)
    await navigateTo("/users")
  } catch {
    errorMessage.value = "Could not create account. Please check your details."
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex max-w-sm flex-col gap-6">
    <div class="text-center">
      <h1 class="text-2xl font-semibold text-(--ui-text-highlighted)">
        Create an account
      </h1>
      <p class="mt-1 text-sm text-(--ui-text-muted)">
        Set up your account and you're in.
      </p>
    </div>

    <UCard>
      <UForm :state="state" class="flex flex-col gap-4" @submit="handleSubmit">
        <UAlert
          v-if="errorMessage"
          color="error"
          variant="subtle"
          :title="errorMessage"
        />

        <UFormField label="Account name" name="accountName" required>
          <UInput v-model="state.accountName" class="w-full" autocomplete="organization" />
        </UFormField>

        <UFormField label="Email" name="email" required>
          <UInput v-model="state.email" type="email" class="w-full" autocomplete="email" />
        </UFormField>

        <UFormField label="Password" name="password" required>
          <UInput
            v-model="state.password"
            type="password"
            class="w-full"
            autocomplete="new-password"
          />
        </UFormField>

        <UButton type="submit" block :loading="isSubmitting">Sign up</UButton>
      </UForm>
    </UCard>

    <p class="text-center text-sm text-(--ui-text-muted)">
      Already have an account?
      <ULink to="/login" class="font-medium text-(--ui-primary)">Log in</ULink>
    </p>
  </div>
</template>
