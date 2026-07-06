export type MemoirStatus = "pending" | "processing" | "draft_ready" | "completed" | "failed"

export interface Memoir {
  id: number
  status: MemoirStatus
  content?: string | null
  has_cover_photo: boolean
  created_at: string
  updated_at: string
}
