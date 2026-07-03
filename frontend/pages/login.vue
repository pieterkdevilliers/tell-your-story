<script setup lang="ts">
import type { AccountChoice, LoginResult } from "~/types/auth"

const state = reactive({
  email: "",
  password: "",
})

const errorMessage = ref("")
const isSubmitting = ref(false)
const accountChoices = ref<AccountChoice[] | null>(null)

const auth = useAuthStore()
const { apiFetch } = useApi()

async function submitLogin(accountId?: number) {
  errorMessage.value = ""
  isSubmitting.value = true
  try {
    const response = await apiFetch<LoginResult>("/auth/login", {
      method: "POST",
      body: {
        email: state.email,
        password: state.password,
        account_id: accountId ?? null,
      },
    })

    if (response.access_token && response.user && response.account) {
      auth.setSession(response.access_token, response.user, response.account)
      await navigateTo("/users")
      return
    }

    if (response.accounts?.length) {
      accountChoices.value = response.accounts
      return
    }

    errorMessage.value = "Login failed. Please try again."
  } catch {
    errorMessage.value = "Invalid email or password."
  } finally {
    isSubmitting.value = false
  }
}

function chooseAccount(accountId: number) {
  submitLogin(accountId)
}
</script>

<template>
  <div class="mx-auto flex max-w-sm flex-col gap-6">
    <div class="text-center">
      <h1 class="text-2xl font-semibold text-(--ui-text-highlighted)">Log in</h1>
      <p class="mt-1 text-sm text-(--ui-text-muted)">Welcome back.</p>
    </div>

    <UCard v-if="!accountChoices">
      <UForm :state="state" class="flex flex-col gap-4" @submit="() => submitLogin()">
        <UAlert
          v-if="errorMessage"
          color="error"
          variant="subtle"
          :title="errorMessage"
        />

        <UFormField label="Email" name="email" required>
          <UInput v-model="state.email" type="email" class="w-full" autocomplete="email" />
        </UFormField>

        <UFormField label="Password" name="password" required>
          <UInput
            v-model="state.password"
            type="password"
            class="w-full"
            autocomplete="current-password"
          />
        </UFormField>

        <div class="text-right">
          <ULink to="/forgot-password" class="text-sm text-(--ui-primary)">
            Forgot password?
          </ULink>
        </div>

        <UButton type="submit" block :loading="isSubmitting">Log in</UButton>
      </UForm>
    </UCard>

    <UCard v-else>
      <p class="mb-3 text-sm text-(--ui-text-muted)">
        This email belongs to multiple accounts. Choose one:
      </p>
      <div class="flex flex-col gap-2">
        <UButton
          v-for="choice in accountChoices"
          :key="choice.id"
          color="neutral"
          variant="outline"
          block
          :loading="isSubmitting"
          @click="chooseAccount(choice.id)"
        >
          {{ choice.name }}
        </UButton>
      </div>
    </UCard>

    <p class="text-center text-sm text-(--ui-text-muted)">
      Don't have an account?
      <ULink to="/signup" class="font-medium text-(--ui-primary)">Sign up</ULink>
    </p>
  </div>
</template>
