import { defineStore } from "pinia"
import type { CurrentAccount, CurrentUser } from "~/types/auth"

export const useAuthStore = defineStore("auth", () => {
  // useCookie (not localStorage) so the token is readable during SSR too —
  // otherwise a hard refresh on a protected page would redirect to /login
  // before client JS ever runs.
  const token = useCookie<string | null>("auth_token", {
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 7,
  })
  const user = ref<CurrentUser | null>(null)
  const account = ref<CurrentAccount | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  function setSession(
    accessToken: string,
    currentUser: CurrentUser,
    currentAccount: CurrentAccount,
  ) {
    token.value = accessToken
    user.value = currentUser
    account.value = currentAccount
  }

  function logout() {
    token.value = null
    user.value = null
    account.value = null
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      const me = await $fetch<{ user: CurrentUser; account: CurrentAccount }>(
        "/auth/me",
        {
          baseURL: useApiBase(),
          headers: { Authorization: `Bearer ${token.value}` },
        },
      )
      user.value = me.user
      account.value = me.account
    } catch {
      logout()
    }
  }

  return {
    token,
    user,
    account,
    isAuthenticated,
    setSession,
    logout,
    fetchMe,
  }
})
