import type { QuestionCategory } from "~/types/question"

export const QUESTION_CATEGORY_ORDER: QuestionCategory[] = [
  "early_life_family",
  "childhood_family_life",
  "school_growing_up",
  "career_work",
  "love_relationships",
  "major_life_events",
  "values_beliefs_reflections",
  "advice_legacy",
]

export const QUESTION_CATEGORY_LABELS: Record<QuestionCategory, string> = {
  early_life_family: "Early life & family",
  childhood_family_life: "Childhood & family life",
  school_growing_up: "School & growing up",
  career_work: "Career & work",
  love_relationships: "Love & relationships",
  major_life_events: "Major life events",
  values_beliefs_reflections: "Values, beliefs & reflections",
  advice_legacy: "Advice & legacy",
}
