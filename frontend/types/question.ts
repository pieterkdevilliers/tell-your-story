export type QuestionCategory =
  | "early_life_family"
  | "childhood_family_life"
  | "school_growing_up"
  | "career_work"
  | "love_relationships"
  | "major_life_events"
  | "values_beliefs_reflections"
  | "advice_legacy"

export interface Answer {
  id: number
  question_id: number
  text: string
  created_at: string
  updated_at: string
}

export interface Question {
  id: number
  category: QuestionCategory
  text: string
  account_id: number
  created_at: string
  answer?: Answer | null
}
