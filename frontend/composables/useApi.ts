export function useApi() {
  const auth = useAuthStore()

  const apiFetch = $fetch.create({
    baseURL: useApiBase(),
    onRequest({ options }) {
      if (auth.token) {
        const headers = new Headers(options.headers)
        headers.set("Authorization", `Bearer ${auth.token}`)
        options.headers = headers
      }
    },
    onResponseError({ response }) {
      if (response.status === 401) {
        auth.logout()
        navigateTo("/login")
      }
    },
  })

  return { apiFetch }
}
