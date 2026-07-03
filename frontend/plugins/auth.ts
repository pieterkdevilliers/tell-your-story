export default defineNuxtPlugin(async () => {
  const auth = useAuthStore()
  if (auth.token && !auth.user) {
    await auth.fetchMe()
  }
})
