<script setup lang="ts">
import type { CurrentAccount, CurrentUser, InvitePreview } from "~/types/auth"

const route = useRoute()
const token = String(route.params.token ?? "")

const { apiFetch } = useApi()
const auth = useAuthStore()

const preview = ref<InvitePreview | null>(null)
const loadError = ref("")
const state = reactive({ password: "", confirmPassword: "" })
const errorMessage = ref("")
const isSubmitting = ref(false)

const userTypeLabels: Record<string, string> = {
  storyteller: "storyteller",
  story_requester: "story requester",
  viewer: "viewer",
}

try {
  preview.value = await apiFetch<InvitePreview>(`/invites/${token}`)
} catch {
  loadError.value = "This invite link is invalid or has expired."
}

async function handleSubmit() {
  errorMessage.value = ""
  if (state.password !== state.confirmPassword) {
    errorMessage.value = "Passwords don't match."
    return
  }

  isSubmitting.value = true
  try {
    const response = await apiFetch<{
      access_token: string
      user: CurrentUser
      account: CurrentAccount
    }>("/invites/accept", {
      method: "POST",
      body: { token, password: state.password },
    })
    auth.setSession(response.access_token, response.user, response.account)
    await navigateTo("/users")
  } catch {
    errorMessage.value = "Could not accept this invite. The link may have expired."
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto flex max-w-sm flex-col gap-6">
    <div class="text-center">
      <h1 class="font-heading text-3xl font-semibold text-gradient-brand">
        You're invited
      </h1>
      <p v-if="preview" class="mt-1 text-sm text-(--ui-text-muted)">
        Join <strong>{{ preview.account_name }}</strong> on Tell Your Story as a
        {{ userTypeLabels[preview.user_type] }}.
      </p>
    </div>

    <UAlert v-if="loadError" color="error" variant="subtle" :title="loadError" />

    <UCard v-else>
      <UForm :state="state" class="flex flex-col gap-4" @submit="handleSubmit">
        <UAlert
          v-if="errorMessage"
          color="error"
          variant="subtle"
          :title="errorMessage"
        />

        <UFormField label="Password" name="password" required>
          <UInput
            v-model="state.password"
            type="password"
            class="w-full"
            autocomplete="new-password"
          />
        </UFormField>

        <UFormField label="Confirm password" name="confirmPassword" required>
          <UInput
            v-model="state.confirmPassword"
            type="password"
            class="w-full"
            autocomplete="new-password"
          />
        </UFormField>

        <UButton type="submit" block :loading="isSubmitting">Accept invite</UButton>
      </UForm>
    </UCard>
  </div>
</template>
