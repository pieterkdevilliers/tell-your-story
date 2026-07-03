<script setup lang="ts">
import type { Question } from "~/types/question"

const auth = useAuthStore()
const { apiFetch } = useApi()

const isStoryteller = computed(() => auth.user?.user_type === "storyteller")

async function handleTellYourStory() {
  const questions = await apiFetch<Question[]>("/questions")
  if (questions.length) {
    await navigateTo(`/questions/${questions[0].id}`)
  } else {
    await navigateTo("/questions")
  }
}

function handleLogout() {
  auth.logout()
  navigateTo("/login")
}
</script>

<template>
  <div class="min-h-screen bg-(--ui-bg-elevated)">
    <header class="border-b border-(--ui-border) bg-(--ui-bg)">
      <UContainer class="flex h-16 items-center justify-between">
        <NuxtLink to="/" class="text-lg font-semibold text-(--ui-text-highlighted)">
          Tell Your Story
        </NuxtLink>

        <nav class="flex items-center gap-3">
          <template v-if="auth.isAuthenticated">
            <AccountSwitcher />
            <UButton
              v-if="isStoryteller"
              color="primary"
              size="sm"
              icon="i-lucide-book-open"
              @click="handleTellYourStory"
            >
              Tell Your Story
            </UButton>
            <UButton to="/questions" color="neutral" variant="ghost" size="sm">
              Questions
            </UButton>
            <UButton to="/users" color="neutral" variant="ghost" size="sm">
              Users
            </UButton>
            <UButton color="neutral" variant="outline" size="sm" @click="handleLogout">
              Log out
            </UButton>
          </template>
          <template v-else>
            <UButton to="/login" color="neutral" variant="ghost" size="sm">
              Log in
            </UButton>
            <UButton to="/signup" color="primary" size="sm">Sign up</UButton>
          </template>
        </nav>
      </UContainer>
    </header>

    <UContainer class="py-10">
      <slot />
    </UContainer>
  </div>
</template>
