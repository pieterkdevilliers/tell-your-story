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
    <header class="bg-brand-gradient shadow-sm">
      <UContainer class="flex h-16 items-center justify-between">
        <NuxtLink to="/" class="font-heading text-lg font-semibold tracking-wide text-white">
          Tell Your Story
        </NuxtLink>

        <nav class="flex items-center gap-3">
          <template v-if="auth.isAuthenticated">
            <AccountSwitcher />
            <UButton
              v-if="isStoryteller"
              color="neutral"
              size="sm"
              icon="i-lucide-book-open"
              class="bg-white text-(--ui-primary) hover:bg-white/90"
              @click="handleTellYourStory"
            >
              Tell Your Story
            </UButton>
            <UButton
              to="/questions"
              variant="ghost"
              size="sm"
              class="text-white hover:bg-white/10"
            >
              Questions
            </UButton>
            <UButton
              to="/users"
              variant="ghost"
              size="sm"
              class="text-white hover:bg-white/10"
            >
              Users
            </UButton>
            <UButton
              to="/memoir"
              variant="ghost"
              size="sm"
              class="text-white hover:bg-white/10"
            >
              Memoir
            </UButton>
            <UButton
              variant="outline"
              size="sm"
              class="border-white/50 text-white hover:bg-white/10"
              @click="handleLogout"
            >
              Log out
            </UButton>
          </template>
          <template v-else>
            <UButton
              to="/login"
              variant="ghost"
              size="sm"
              class="text-white hover:bg-white/10"
            >
              Log in
            </UButton>
            <UButton
              to="/signup"
              size="sm"
              color="neutral"
              class="bg-white text-(--ui-primary) hover:bg-white/90"
            >
              Sign up
            </UButton>
          </template>
        </nav>
      </UContainer>
    </header>

    <UContainer class="py-10">
      <slot />
    </UContainer>
  </div>
</template>
