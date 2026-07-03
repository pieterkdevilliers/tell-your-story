<script setup lang="ts">
import type { CurrentUser, InviteRead, UserType } from "~/types/auth"

definePageMeta({ middleware: "auth" })

const auth = useAuthStore()
const { apiFetch } = useApi()
const toast = useToast()

const users = ref<CurrentUser[]>([])
const invites = ref<InviteRead[]>([])
const isCreateOpen = ref(false)
const isInviteOpen = ref(false)
const editingUser = ref<CurrentUser | null>(null)

const isOwner = computed(() => auth.user?.role === "owner")
const hasStoryteller = computed(() => users.value.some((u) => u.user_type === "storyteller"))
const isStoryRequester = computed(() => auth.user?.user_type === "story_requester")
const canInvite = computed(() => auth.user?.user_type !== "viewer")
const canInviteStoryteller = computed(() => isStoryRequester.value && !hasStoryteller.value)
const canInviteViewer = computed(() => hasStoryteller.value && canInvite.value)

const columns = [
  { accessorKey: "email", header: "Email" },
  { accessorKey: "role", header: "Role" },
  { accessorKey: "user_type", header: "Type" },
  { accessorKey: "is_active", header: "Active" },
  { accessorKey: "id", header: "" },
]

const userTypeLabels: Record<UserType, string> = {
  storyteller: "Storyteller",
  story_requester: "Story requester",
  viewer: "Viewer",
}

async function loadUsers() {
  users.value = await apiFetch<CurrentUser[]>("/users")
}

async function loadInvites() {
  if (!canInvite.value) return
  invites.value = await apiFetch<InviteRead[]>("/invites")
}

async function handleCreate(payload: {
  email: string
  password: string
  role: string
  user_type: string
}) {
  try {
    await apiFetch("/users", { method: "POST", body: payload })
    isCreateOpen.value = false
    await loadUsers()
    toast.add({ title: "User added", color: "success" })
  } catch {
    toast.add({ title: "Could not create user", color: "error" })
  }
}

async function handleUpdate(payload: {
  email: string
  password: string
  role: string
  user_type: string
}) {
  if (!editingUser.value) return
  const body: Record<string, unknown> = { email: payload.email }
  if (payload.password) body.password = payload.password
  if (isOwner.value) {
    body.role = payload.role
    body.user_type = payload.user_type
  }

  try {
    await apiFetch(`/users/${editingUser.value.id}`, { method: "PATCH", body })
    editingUser.value = null
    await loadUsers()
    toast.add({ title: "User updated", color: "success" })
  } catch {
    toast.add({ title: "Could not update user", color: "error" })
  }
}

async function handleDelete(user: CurrentUser) {
  try {
    await apiFetch(`/users/${user.id}`, { method: "DELETE" })
    await loadUsers()
    toast.add({ title: "User deleted", color: "success" })
  } catch {
    toast.add({
      title: "Could not delete user",
      description: "An account must keep at least one owner.",
      color: "error",
    })
  }
}

async function handleInvite(payload: { email: string; user_type: UserType }) {
  try {
    await apiFetch("/invites", { method: "POST", body: payload })
    isInviteOpen.value = false
    await loadInvites()
    toast.add({ title: "Invite sent", color: "success" })
  } catch {
    toast.add({ title: "Could not send invite", color: "error" })
  }
}

await loadUsers()
await loadInvites()
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="font-heading text-2xl font-semibold text-(--ui-text-highlighted)">
          {{ auth.account?.name }}
        </h1>
        <p class="text-sm text-(--ui-text-muted)">Manage who has access to this account.</p>
      </div>
      <div class="flex gap-2">
        <UButton
          v-if="canInviteStoryteller || canInviteViewer"
          color="neutral"
          variant="outline"
          icon="i-lucide-send"
          @click="isInviteOpen = true"
        >
          Invite
        </UButton>
        <UButton v-if="isOwner" icon="i-lucide-plus" @click="isCreateOpen = true">
          Add user
        </UButton>
      </div>
    </div>

    <UCard :ui="{ body: 'p-0 sm:p-0' }">
      <UTable :data="users" :columns="columns">
        <template #role-cell="{ row }">
          <UBadge
            :color="row.original.role === 'owner' ? 'primary' : 'neutral'"
            variant="subtle"
          >
            {{ row.original.role }}
          </UBadge>
        </template>

        <template #user_type-cell="{ row }">
          <UBadge color="neutral" variant="outline">
            {{ userTypeLabels[row.original.user_type] }}
          </UBadge>
        </template>

        <template #is_active-cell="{ row }">
          <UBadge :color="row.original.is_active ? 'success' : 'neutral'" variant="subtle">
            {{ row.original.is_active ? "Active" : "Inactive" }}
          </UBadge>
        </template>

        <template #id-cell="{ row }">
          <div class="flex justify-end gap-2">
            <UButton
              v-if="row.original.id === auth.user?.id || isOwner"
              color="neutral"
              variant="ghost"
              size="sm"
              icon="i-lucide-pencil"
              @click="editingUser = row.original"
            >
              Edit
            </UButton>
            <UButton
              v-if="isOwner"
              color="error"
              variant="ghost"
              size="sm"
              icon="i-lucide-trash-2"
              @click="handleDelete(row.original)"
            >
              Delete
            </UButton>
          </div>
        </template>
      </UTable>
    </UCard>

    <UCard v-if="canInvite && invites.length" :ui="{ body: 'p-0 sm:p-0' }">
      <template #header>
        <p class="text-sm font-medium text-(--ui-text-highlighted)">Pending invites</p>
      </template>
      <UTable
        :data="invites"
        :columns="[
          { accessorKey: 'email', header: 'Email' },
          { accessorKey: 'invited_user_type', header: 'Invited as' },
          { accessorKey: 'expires_at', header: 'Expires' },
        ]"
      >
        <template #invited_user_type-cell="{ row }">
          <UBadge color="neutral" variant="outline">
            {{ userTypeLabels[row.original.invited_user_type] }}
          </UBadge>
        </template>
        <template #expires_at-cell="{ row }">
          {{ new Date(row.original.expires_at).toLocaleDateString() }}
        </template>
      </UTable>
    </UCard>

    <UModal v-model:open="isCreateOpen" title="Add user">
      <template #body>
        <UserForm
          mode="create"
          :is-owner="isOwner"
          :is-story-requester="isStoryRequester"
          :has-storyteller="hasStoryteller"
          @submit="handleCreate"
          @cancel="isCreateOpen = false"
        />
      </template>
    </UModal>

    <UModal :open="!!editingUser" title="Edit user" @update:open="(v) => !v && (editingUser = null)">
      <template #body>
        <UserForm
          v-if="editingUser"
          mode="edit"
          :is-owner="isOwner"
          :is-story-requester="isStoryRequester"
          :has-storyteller="hasStoryteller"
          :initial-email="editingUser.email"
          :initial-role="editingUser.role"
          :initial-user-type="editingUser.user_type"
          @submit="handleUpdate"
          @cancel="editingUser = null"
        />
      </template>
    </UModal>

    <UModal v-model:open="isInviteOpen" title="Invite someone">
      <template #body>
        <InviteForm
          :can-invite-storyteller="canInviteStoryteller"
          :can-invite-viewer="canInviteViewer"
          @submit="handleInvite"
          @cancel="isInviteOpen = false"
        />
      </template>
    </UModal>
  </div>
</template>
