<script setup lang="ts">
const auth = useAuthStore()

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
          Daily Tasks
        </NuxtLink>

        <nav class="flex items-center gap-3">
          <template v-if="auth.isAuthenticated">
            <span class="hidden text-sm text-(--ui-text-muted) sm:inline">
              {{ auth.account?.name }}
            </span>
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
