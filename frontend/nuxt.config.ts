// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2024-11-01",
  devtools: { enabled: true },
  devServer: { host: "0.0.0.0", port: 3014 },
  modules: ["@pinia/nuxt", "@nuxt/ui"],
  css: ["~/assets/css/main.css"],
  runtimeConfig: {
    // Server-only: used for SSR fetches, which run inside the Docker
    // network and must reach the backend via its service name. Falls back
    // to the public URL for non-Docker local dev, where both run on the
    // host and "localhost" works for both server and browser.
    apiBaseInternal:
      process.env.NUXT_API_BASE_INTERNAL ||
      process.env.NUXT_PUBLIC_API_BASE ||
      "http://localhost:8014",
    public: {
      // Browser-facing: must be reachable from the user's machine, not
      // just from inside the Docker network.
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "http://localhost:8014",
    },
  },
});
