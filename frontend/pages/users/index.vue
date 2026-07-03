<script setup lang="ts">
import type { CurrentUser } from "~/types/auth"

definePageMeta({ middleware: "auth" })

const auth = useAuthStore()
const { apiFetch } = useApi()
const toast = useToast()

const users = ref<CurrentUser[]>([])
const isCreateOpen = ref(false)
const editingUser = ref<CurrentUser | null>(null)

const isOwner = computed(() => auth.user?.role === "owner")

const columns = [
  { accessorKey: "email", header: "Email" },
  { accessorKey: "role", header: "Role" },
  { accessorKey: "is_active", header: "Active" },
  { accessorKey: "id", header: "" },
]

async function loadUsers() {
  users.value = await apiFetch<CurrentUser[]>("/users")
}

async function handleCreate(payload: {
  email: string
  password: string
  role: string
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
}) {
  if (!editingUser.value) return
  const body: Record<string, unknown> = { email: payload.email }
  if (payload.password) body.password = payload.password
  if (isOwner.value) body.role = payload.role

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

await loadUsers()
</script>

<template>
  <div class="flex flex-col gap-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold text-(--ui-text-highlighted)">
          {{ auth.account?.name }}
        </h1>
        <p class="text-sm text-(--ui-text-muted)">Manage who has access to this account.</p>
      </div>
      <UButton v-if="isOwner" icon="i-lucide-plus" @click="isCreateOpen = true">
        Add user
      </UButton>
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

    <UModal v-model:open="isCreateOpen" title="Add user">
      <template #body>
        <UserForm mode="create" :is-owner="isOwner" @submit="handleCreate" @cancel="isCreateOpen = false" />
      </template>
    </UModal>

    <UModal :open="!!editingUser" title="Edit user" @update:open="(v) => !v && (editingUser = null)">
      <template #body>
        <UserForm
          v-if="editingUser"
          mode="edit"
          :is-owner="isOwner"
          :initial-email="editingUser.email"
          :initial-role="editingUser.role"
          @submit="handleUpdate"
          @cancel="editingUser = null"
        />
      </template>
    </UModal>
  </div>
</template>
