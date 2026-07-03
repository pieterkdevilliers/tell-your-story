<script setup lang="ts">
import type { CurrentAccount, CurrentUser, SignupUserType } from "~/types/auth"

const state = reactive({
  accountName: "",
  email: "",
  password: "",
  userType: "" as SignupUserType | "",
})

const userTypeOptions = [
  {
    label: "I want to tell my own story",
    description: "Answer questions about your own life.",
    value: "storyteller",
  },
  {
    label: "I'm setting this up for someone else",
    description: "e.g. inviting a parent to tell their story.",
    value: "story_requester",
  },
]

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
        user_type: state.userType,
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
      <h1 class="font-heading text-3xl font-semibold text-gradient-brand">
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

        <UFormField label="How will you use Tell Your Story?" name="userType" required>
          <URadioGroup v-model="state.userType" :items="userTypeOptions" value-key="value" />
        </UFormField>

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
