<script setup lang="ts">
const auth = useAuthStore()
</script>

<template>
  <div class="flex flex-col items-center gap-6 py-16 text-center">
    <h1 class="text-4xl font-bold tracking-tight text-(--ui-text-highlighted)">
      Daily Tasks
    </h1>
    <p class="max-w-md text-lg text-(--ui-text-muted)">
      A multi-tenant starter: create an account, invite your team, and manage
      who has access.
    </p>

    <div class="flex gap-3">
      <template v-if="auth.isAuthenticated">
        <UButton to="/users" size="lg">Go to your account</UButton>
      </template>
      <template v-else>
        <UButton to="/signup" size="lg">Create an account</UButton>
        <UButton to="/login" size="lg" color="neutral" variant="outline">
          Log in
        </UButton>
      </template>
    </div>
  </div>
</template>
