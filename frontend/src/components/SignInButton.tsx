import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { login, register, getGoogleLoginUrl } from "@/services/api";

export function SignInButton() {
  const { user, logout } = useAuth();
  const [showModal, setShowModal] = useState(false);

  if (user) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-400">{user.display_name || user.email}</span>
        <button onClick={logout}
          className="text-xs text-gray-500 hover:text-white transition-colors">
          Sign out
        </button>
      </div>
    );
  }

  return (
    <>
      <button onClick={() => setShowModal(true)}
        className="text-xs text-gray-400 hover:text-ember transition-colors border border-dark-600 px-3 py-1.5 rounded-lg hover:border-ember">
        Sign in
      </button>

      {showModal && <LoginModal onClose={() => setShowModal(false)} />}
    </>
  );
}

function LoginModal({ onClose }: { onClose: () => void }) {
  const { setAuth } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      const res = mode === "login"
        ? await login(email, password)
        : await register(email, password, name || undefined);
      setAuth(res.access_token, res.user);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    try {
      const { auth_url } = await getGoogleLoginUrl();
      window.location.href = auth_url;
    } catch {
      setError("Google login unavailable");
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4"
         onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="bg-dark-800 border border-dark-600 rounded-xl p-6 w-full max-w-sm">
        <h3 className="text-lg font-bold text-white mb-4">
          {mode === "login" ? "Sign in" : "Create account"}
        </h3>

        <button onClick={handleGoogle}
          className="w-full py-2.5 bg-white text-gray-800 rounded-lg font-medium text-sm mb-4 hover:bg-gray-100 transition-colors">
          Continue with Google
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 h-px bg-dark-600" />
          <span className="text-xs text-gray-500">or</span>
          <div className="flex-1 h-px bg-dark-600" />
        </div>

        <div className="space-y-3">
          {mode === "register" && (
            <input value={name} onChange={(e) => setName(e.target.value)}
              placeholder="Display name (optional)"
              className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-ember" />
          )}
          <input value={email} onChange={(e) => setEmail(e.target.value)}
            type="email" placeholder="Email"
            className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-ember" />
          <input value={password} onChange={(e) => setPassword(e.target.value)}
            type="password" placeholder="Password (min 8 chars)"
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            className="w-full px-3 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-ember" />
        </div>

        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}

        <button onClick={handleSubmit} disabled={loading || !email || !password}
          className="w-full mt-4 py-2.5 bg-ember hover:bg-ember-hover text-white rounded-lg font-semibold text-sm transition-colors disabled:opacity-50">
          {loading ? "..." : mode === "login" ? "Sign in" : "Create account"}
        </button>

        <p className="text-center text-xs text-gray-500 mt-3">
          {mode === "login" ? "Don't have an account? " : "Already have one? "}
          <button onClick={() => setMode(mode === "login" ? "register" : "login")}
            className="text-ember hover:underline">
            {mode === "login" ? "Sign up" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}
