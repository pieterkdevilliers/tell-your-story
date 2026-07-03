export function useApiBase() {
  const config = useRuntimeConfig()
  return import.meta.server ? config.apiBaseInternal : config.public.apiBase
}
