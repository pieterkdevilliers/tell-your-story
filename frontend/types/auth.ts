export type AccountRole = "owner" | "member"
export type UserType = "storyteller" | "story_requester" | "viewer"
export type SignupUserType = Extract<UserType, "storyteller" | "story_requester">

export interface CurrentUser {
  id: number
  email: string
  role: AccountRole
  user_type: UserType
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

export interface InviteRead {
  id: number
  email: string
  invited_user_type: UserType
  account_id: number
  expires_at: string
  accepted_at: string | null
  created_at: string
}

export interface InvitePreview {
  account_name: string
  email: string
  user_type: UserType
}

export interface AccountMembership {
  id: number
  name: string
  role: AccountRole
  user_type: UserType
  is_current: boolean
}
