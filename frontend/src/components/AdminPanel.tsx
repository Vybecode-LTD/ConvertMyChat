import { useState, useEffect } from "react";
import type { UserData, AdminStats } from "@/types";
import {
  adminListUsers, adminCreateUser, adminUpdateUser,
  adminResetPassword, adminDeleteUser, adminStats,
} from "@/services/api";

export function AdminPanel() {
  const [users, setUsers] = useState<UserData[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [search, setSearch] = useState("");
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [resetTarget, setResetTarget] = useState<UserData | null>(null);
  const [msg, setMsg] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [u, s] = await Promise.all([
        adminListUsers(0, 50, search || undefined),
        adminStats(),
      ]);
      setUsers(u.users);
      setTotal(u.total);
      setStats(s);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { load(); }, [search]);

  const flash = (m: string) => { setMsg(m); setTimeout(() => setMsg(""), 3000); };

  const toggleActive = async (u: UserData) => {
    await adminUpdateUser(u.id, { is_active: !u.is_active });
    flash(`${u.email} ${u.is_active ? "disabled" : "enabled"}`);
    load();
  };

  const toggleAdmin = async (u: UserData) => {
    try {
      await adminUpdateUser(u.id, { is_admin: !u.is_admin });
      flash(`${u.email} admin ${u.is_admin ? "revoked" : "granted"}`);
      load();
    } catch (e) { flash(e instanceof Error ? e.message : "Failed"); }
  };

  const handleDelete = async (u: UserData) => {
    if (!confirm(`Permanently delete ${u.email} and all their data?`)) return;
    try {
      await adminDeleteUser(u.id);
      flash(`Deleted ${u.email}`);
      load();
    } catch (e) { flash(e instanceof Error ? e.message : "Failed"); }
  };

  return (
    <div className="space-y-6">
      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            ["Users", stats.total_users],
            ["Active", stats.active_users],
            ["Exports", stats.total_exports],
            ["Cached", stats.cached_conversations],
          ].map(([label, val]) => (
            <div key={String(label)} className="bg-dark-800 border border-dark-600 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-white">{val}</p>
              <p className="text-xs text-gray-500">{label}</p>
            </div>
          ))}
        </div>
      )}

      {msg && <div className="text-sm text-green-400 bg-green-950/30 border border-green-800/50 rounded-lg px-4 py-2">{msg}</div>}

      {/* Controls */}
      <div className="flex gap-3">
        <input value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by email or name..."
          className="flex-1 px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-ember" />
        <button onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-ember hover:bg-ember-hover text-white rounded-lg text-sm font-semibold transition-colors">
          + Create user
        </button>
      </div>

      {/* User list */}
      {loading ? (
        <p className="text-gray-500 text-center py-4">Loading...</p>
      ) : (
        <div className="space-y-2">
          {users.map((u) => (
            <div key={u.id} className="bg-dark-800 border border-dark-600 rounded-lg p-4">
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-white truncate">{u.display_name || u.email}</p>
                    {u.is_admin && <span className="text-[10px] bg-ember/20 text-ember px-2 py-0.5 rounded">admin</span>}
                    {!u.is_active && <span className="text-[10px] bg-red-900/30 text-red-400 px-2 py-0.5 rounded">disabled</span>}
                  </div>
                  <p className="text-xs text-gray-500">{u.email} · {u.auth_provider} · joined {new Date(u.created_at).toLocaleDateString()}</p>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <button onClick={() => toggleActive(u)} title={u.is_active ? "Disable" : "Enable"}
                    className={`text-xs px-2 py-1 rounded border transition-colors ${u.is_active ? "border-dark-600 text-gray-400 hover:border-amber-600 hover:text-amber-400" : "border-green-800 text-green-400 hover:border-green-600"}`}>
                    {u.is_active ? "Disable" : "Enable"}
                  </button>
                  <button onClick={() => toggleAdmin(u)} title="Toggle admin"
                    className="text-xs px-2 py-1 border border-dark-600 rounded text-gray-400 hover:border-ember hover:text-ember transition-colors">
                    {u.is_admin ? "Remove admin" : "Make admin"}
                  </button>
                  <button onClick={() => setResetTarget(u)}
                    className="text-xs px-2 py-1 border border-dark-600 rounded text-gray-400 hover:border-blue-500 hover:text-blue-400 transition-colors">
                    Reset PW
                  </button>
                  <button onClick={() => handleDelete(u)}
                    className="text-xs px-2 py-1 text-red-400 hover:text-red-300 transition-colors">
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
          <p className="text-xs text-gray-600 text-center">{total} total users</p>
        </div>
      )}

      {/* Create user modal */}
      {showCreate && <CreateUserModal onClose={() => { setShowCreate(false); load(); }} onFlash={flash} />}

      {/* Reset password modal */}
      {resetTarget && <ResetPasswordModal user={resetTarget} onClose={() => { setResetTarget(null); }} onFlash={flash} />}
    </div>
  );
}

function CreateUserModal({ onClose, onFlash }: { onClose: () => void; onFlash: (m: string) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);
  const [error, setError] = useState("");

  const handleCreate = async () => {
    try {
      await adminCreateUser({ email, password, display_name: name || undefined, is_admin: isAdmin });
      onFlash(`Created ${email}`);
      onClose();
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="bg-dark-800 border border-dark-600 rounded-xl p-6 w-full max-w-sm space-y-3">
        <h3 className="text-lg font-bold text-white">Create user</h3>
        <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="Email"
          className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-ember" />
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Display name"
          className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-ember" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password (min 8)"
          className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-ember" />
        <label className="flex items-center gap-2 text-sm text-gray-400">
          <input type="checkbox" checked={isAdmin} onChange={(e) => setIsAdmin(e.target.checked)} />
          Admin access
        </label>
        {error && <p className="text-red-400 text-xs">{error}</p>}
        <div className="flex gap-2">
          <button onClick={handleCreate} disabled={!email || !password}
            className="flex-1 py-2 bg-ember hover:bg-ember-hover text-white rounded-lg text-sm font-semibold disabled:opacity-50">Create</button>
          <button onClick={onClose} className="flex-1 py-2 bg-dark-700 text-gray-400 rounded-lg text-sm hover:text-white">Cancel</button>
        </div>
      </div>
    </div>
  );
}

function ResetPasswordModal({ user, onClose, onFlash }: { user: UserData; onClose: () => void; onFlash: (m: string) => void }) {
  const [pw, setPw] = useState("");
  const [error, setError] = useState("");

  const handleReset = async () => {
    try {
      await adminResetPassword(user.id, pw);
      onFlash(`Password reset for ${user.email}`);
      onClose();
    } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="bg-dark-800 border border-dark-600 rounded-xl p-6 w-full max-w-sm space-y-3">
        <h3 className="text-lg font-bold text-white">Reset password</h3>
        <p className="text-sm text-gray-400">{user.email}</p>
        <input value={pw} onChange={(e) => setPw(e.target.value)} type="password" placeholder="New password (min 8)"
          onKeyDown={(e) => e.key === "Enter" && handleReset()}
          className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-ember" />
        {error && <p className="text-red-400 text-xs">{error}</p>}
        <div className="flex gap-2">
          <button onClick={handleReset} disabled={pw.length < 8}
            className="flex-1 py-2 bg-ember hover:bg-ember-hover text-white rounded-lg text-sm font-semibold disabled:opacity-50">Reset</button>
          <button onClick={onClose} className="flex-1 py-2 bg-dark-700 text-gray-400 rounded-lg text-sm hover:text-white">Cancel</button>
        </div>
      </div>
    </div>
  );
}
