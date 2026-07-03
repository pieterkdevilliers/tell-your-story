export default defineAppConfig({
  ui: {
    colors: {
      primary: "pink",
      secondary: "purple",
      neutral: "slate",
    },
    button: {
      slots: {
        base: "rounded-full font-medium",
      },
    },
    badge: {
      slots: {
        base: "rounded-full",
      },
    },
  },
})
