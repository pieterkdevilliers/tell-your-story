<script setup lang="ts">
import type { AccountMembership, CurrentAccount, CurrentUser } from "~/types/auth"

const auth = useAuthStore()
const { apiFetch } = useApi()
const toast = useToast()

const accounts = ref<AccountMembership[]>([])
const isSwitching = ref(false)

async function loadAccounts() {
  accounts.value = await apiFetch<AccountMembership[]>("/auth/accounts")
}

async function switchTo(accountId: number) {
  if (isSwitching.value) return
  isSwitching.value = true
  try {
    const response = await apiFetch<{
      access_token: string
      user: CurrentUser
      account: CurrentAccount
    }>("/auth/switch-account", {
      method: "POST",
      body: { account_id: accountId },
    })
    auth.setSession(response.access_token, response.user, response.account)
    await navigateTo("/users", { external: true })
  } catch {
    toast.add({ title: "Could not switch accounts", color: "error" })
  } finally {
    isSwitching.value = false
  }
}

const items = computed(() =>
  accounts.value.map((account) => ({
    label: account.name,
    icon: account.is_current ? "i-lucide-check" : undefined,
    disabled: account.is_current,
    onSelect: () => switchTo(account.id),
  })),
)

await loadAccounts()
</script>

<template>
  <span
    v-if="accounts.length <= 1"
    class="hidden text-sm text-(--ui-text-muted) sm:inline"
  >
    {{ auth.account?.name }}
  </span>

  <UDropdownMenu v-else :items="items" :content="{ align: 'end' }">
    <UButton
      color="neutral"
      variant="ghost"
      size="sm"
      trailing-icon="i-lucide-chevron-down"
      :loading="isSwitching"
    >
      {{ auth.account?.name }}
    </UButton>
  </UDropdownMenu>
</template>
