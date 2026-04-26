import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const hash = window.location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    if (!match) {
      navigate("/login", { replace: true });
      return;
    }
    const session_id = match[1];

    (async () => {
      try {
        const { data } = await api.post("/auth/google/session", { session_id });
        setUser(data);
        // Strip hash & navigate
        window.history.replaceState({}, document.title, "/");
        navigate(data.onboarded ? "/dashboard" : "/onboarding", { replace: true });
      } catch (err) {
        navigate("/login?error=oauth", { replace: true });
      }
    })();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-sand-100">
      <div className="text-olive-700 font-display text-lg">Signing you in…</div>
    </div>
  );
}
