export type MemoirStatus = "pending" | "processing" | "completed" | "failed"

export interface Memoir {
  id: number
  status: MemoirStatus
  created_at: string
  updated_at: string
}
