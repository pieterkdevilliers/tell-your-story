export type AccountRole = "owner" | "member"

export interface CurrentUser {
  id: number
  email: string
  role: AccountRole
  is_active: boolean
  account_id: number
  created_at: string
}

export interface CurrentAccount {
  id: number
  name: string
  created_at: string
}

export interface AccountChoice {
  id: number
  name: string
}

export interface LoginResult {
  access_token?: string | null
  token_type?: string | null
  user?: CurrentUser | null
  account?: CurrentAccount | null
  accounts?: AccountChoice[] | null
}
