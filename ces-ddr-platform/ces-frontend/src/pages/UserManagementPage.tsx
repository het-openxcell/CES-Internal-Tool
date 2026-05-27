import { useEffect, useRef, useState } from "react";
import { UserPlus } from "lucide-react";

import { ApiError, type CreateUserRequest, type User, apiClient } from "@/lib/api";
import { authToken } from "@/lib/auth";
import { cn } from "@/lib/utils";

function fmtTs(ts: number) {
  const d = new Date(ts * 1000);
  const today = new Date();
  if (d.toDateString() === today.toDateString()) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) {
    return `Yesterday ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  }
  return d.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
}

export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [forbidden, setForbidden] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [createEmail, setCreateEmail] = useState("");
  const [createPassword, setCreatePassword] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editEmail, setEditEmail] = useState("");
  const [editError, setEditError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const editInputRef = useRef<HTMLInputElement>(null);

  const [confirmDeactivate, setConfirmDeactivate] = useState<string | null>(null);
  const [deactivateErrors, setDeactivateErrors] = useState<Record<string, string>>({});

  const myId = authToken.getUserId();

  useEffect(() => {
    apiClient.getUsers().then(setUsers).catch((err) => {
      if (err instanceof ApiError && err.status === 403) {
        setForbidden(true);
      } else {
        setLoadError("Failed to load users.");
      }
    });
  }, []);

  useEffect(() => {
    if (editingId) editInputRef.current?.focus();
  }, [editingId]);

  if (forbidden) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center text-gray-500">
          <p className="text-[16px] font-medium">Access denied</p>
          <p className="text-[14px] mt-1">You do not have permission to manage users.</p>
        </div>
      </main>
    );
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateError(null);
    setCreating(true);
    try {
      const req: CreateUserRequest = { email: createEmail, password: createPassword };
      const created = await apiClient.createUser(req);
      setUsers((prev) => [...prev, created]);
      setCreateEmail("");
      setCreatePassword("");
      setShowCreate(false);
    } catch {
      setCreateError("Failed to create user.");
    } finally {
      setCreating(false);
    }
  }

  function startEdit(user: User) {
    setEditingId(user.id);
    setEditEmail(user.email);
    setEditError(null);
  }

  function cancelEdit() {
    setEditingId(null);
    setEditEmail("");
    setEditError(null);
  }

  async function handleSaveEdit(userId: string) {
    setEditError(null);
    setSaving(true);
    try {
      const updated = await apiClient.updateUser(userId, { email: editEmail });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      setEditingId(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setEditError("Email already in use.");
      } else {
        setEditError("Failed to update.");
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(userId: string) {
    setDeactivateErrors((prev) => ({ ...prev, [userId]: "" }));
    try {
      const updated = await apiClient.deactivateUser(userId);
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } catch {
      setDeactivateErrors((prev) => ({ ...prev, [userId]: "Deactivation failed." }));
    } finally {
      setConfirmDeactivate(null);
    }
  }

  return (
    <main id="main-content" className="flex-1 overflow-auto p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-[18px] font-semibold text-text-primary">User Management</h1>
          <button
            type="button"
            onClick={() => { setShowCreate((v) => !v); setCreateError(null); }}
            className="inline-flex items-center gap-1.5 h-9 px-3 rounded-md text-[13px] font-semibold bg-ces-red text-white hover:bg-ces-red-dark transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ces-red focus-visible:ring-offset-2"
          >
            <UserPlus className="w-4 h-4" />
            Create User
          </button>
        </div>

        {showCreate && (
          <form
            onSubmit={handleCreate}
            className="mb-6 p-4 rounded-lg border border-border-default bg-surface flex flex-col gap-3 max-w-sm"
          >
            <h2 className="text-[14px] font-semibold text-text-primary">New User</h2>
            <input
              required
              type="email"
              placeholder="Email"
              value={createEmail}
              onChange={(e) => setCreateEmail(e.target.value)}
              className="h-9 px-3 text-[13px] rounded-md border border-border-default focus:outline-none focus:border-text-muted bg-white"
            />
            <input
              required
              type="password"
              placeholder="Password"
              value={createPassword}
              onChange={(e) => setCreatePassword(e.target.value)}
              className="h-9 px-3 text-[13px] rounded-md border border-border-default focus:outline-none focus:border-text-muted bg-white"
            />
            {createError && <p className="text-[12px] text-error-text">{createError}</p>}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={creating}
                className="h-8 px-3 rounded-md text-[13px] font-semibold bg-ces-red text-white hover:bg-ces-red-dark disabled:opacity-50 transition-colors"
              >
                {creating ? "Creating…" : "Create"}
              </button>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="h-8 px-3 rounded-md text-[13px] font-medium text-text-secondary hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {loadError && <p className="text-[13px] text-error-text mb-4">{loadError}</p>}

        <div className="rounded-lg border border-border-default overflow-hidden">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="bg-surface border-b border-border-default">
                <th className="px-4 py-3 text-left font-semibold text-text-secondary">Email</th>
                <th className="px-4 py-3 text-left font-semibold text-text-secondary">Roles</th>
                <th className="px-4 py-3 text-left font-semibold text-text-secondary">Status</th>
                <th className="px-4 py-3 text-left font-semibold text-text-secondary">Created</th>
                <th className="px-4 py-3 text-left font-semibold text-text-secondary">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-border-default last:border-0 hover:bg-surface/50 transition-colors">
                  <td className="px-4 py-3 font-medium text-text-primary">
                    {editingId === user.id ? (
                      <div className="flex flex-col gap-1">
                        <input
                          ref={editInputRef}
                          type="email"
                          value={editEmail}
                          onChange={(e) => setEditEmail(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleSaveEdit(user.id);
                            if (e.key === "Escape") cancelEdit();
                          }}
                          className="h-8 px-2 text-[13px] rounded border border-border-default focus:outline-none focus:border-text-muted bg-white w-56"
                        />
                        {editError && <p className="text-[11px] text-error-text">{editError}</p>}
                      </div>
                    ) : (
                      user.email
                    )}
                  </td>
                  <td className="px-4 py-3 text-text-secondary">{user.roles.join(", ") || "—"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold",
                        user.is_active
                          ? "bg-emerald-50 text-emerald-800"
                          : "bg-gray-100 text-gray-600"
                      )}
                    >
                      {user.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-text-secondary">{fmtTs(user.created_at)}</td>
                  <td className="px-4 py-3">
                    {editingId === user.id ? (
                      <span className="inline-flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleSaveEdit(user.id)}
                          disabled={saving || !editEmail}
                          className="text-[12px] font-semibold text-ces-red hover:underline disabled:opacity-50"
                        >
                          {saving ? "Saving…" : "Save"}
                        </button>
                        <button
                          type="button"
                          onClick={cancelEdit}
                          className="text-[12px] text-text-secondary hover:text-text-primary"
                        >
                          Cancel
                        </button>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-3">
                        <button
                          type="button"
                          onClick={() => startEdit(user)}
                          className="text-[12px] font-medium text-text-secondary hover:text-text-primary transition-colors"
                        >
                          Edit
                        </button>
                        {user.is_active && user.id !== myId && (
                          <>
                            {confirmDeactivate === user.id ? (
                              <span className="inline-flex items-center gap-2">
                                <span className="text-text-secondary text-[12px]">Confirm deactivate?</span>
                                <button
                                  type="button"
                                  onClick={() => handleDeactivate(user.id)}
                                  className="text-[12px] font-semibold text-error-text hover:underline"
                                >
                                  Yes
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setConfirmDeactivate(null)}
                                  className="text-[12px] text-text-secondary hover:text-text-primary"
                                >
                                  Cancel
                                </button>
                              </span>
                            ) : (
                              <button
                                type="button"
                                onClick={() => setConfirmDeactivate(user.id)}
                                className="text-[12px] font-medium text-text-secondary hover:text-error-text transition-colors"
                              >
                                Deactivate
                              </button>
                            )}
                            {deactivateErrors[user.id] && (
                              <p className="text-[11px] text-error-text mt-0.5">{deactivateErrors[user.id]}</p>
                            )}
                          </>
                        )}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {users.length === 0 && !loadError && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-text-secondary">No users found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
