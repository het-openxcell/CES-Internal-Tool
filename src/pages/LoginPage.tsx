import { type FormEvent, useRef, useState } from "react";
import { Eye as EyeIcon, EyeOff as EyeSlashIcon, Lock as LockIcon, User as UserIcon } from "lucide-react";
import { useNavigate } from "react-router";

import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api";
import { authToken } from "@/lib/auth";

function CesLogo({ className }: { className?: string }) {
  return (
    <img
      src="/logo.png"
      alt="CES Energy Solutions"
      className={className}
      width={262}
      height={62}
      loading="eager"
    />
  );
}

function Spinner({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle
        className="spinner-track"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
        opacity="0.25"
      />
      <path
        className="spinner-lead"
        d="M22 12a10 10 0 00-10-10"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function LoginPage() {
  const navigate = useNavigate();
  const passwordRef = useRef<HTMLInputElement>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [shake, setShake] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const response = await apiClient.login({ username, password });
      authToken.store(response.token);

      navigate("/", { replace: true });
    } catch (caughtError) {
      setShake(true);
      setTimeout(() => setShake(false), 500);

      if (caughtError instanceof ApiError && caughtError.code === "UNAUTHORIZED") {
        setError("Invalid username or password");
        setPassword("");
        passwordRef.current?.focus();
      } else {
        setError("Unable to sign in. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-shell">
      <div className="login-bg" aria-hidden="true" />
      <section className={`login-panel ${shake ? "login-shake" : ""}`} aria-labelledby="login-title">
        <div className="login-brand">
          <CesLogo className="login-logo" />
          <div className="login-brand-text">
            <p className="eyebrow">CES Internal Tool</p>
            <h1 id="login-title" className="login-title">
              Sign in
            </h1>
          </div>
        </div>

        <form className="login-form" onSubmit={handleSubmit} noValidate>
          <div className="input-group">
            <label className="field-label" htmlFor="username">
              Username
            </label>
            <div className="input-wrap">
              <UserIcon className="input-icon" />
              <input
                autoComplete="username"
                className="text-field text-field--icon"
                id="username"
                name="username"
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Enter your username"
                required
                type="text"
                value={username}
              />
            </div>
          </div>

          <div className="input-group">
            <label className="field-label" htmlFor="password">
              Password
            </label>
            <div className="input-wrap">
              <LockIcon className="input-icon" />
              <input
                ref={passwordRef}
                autoComplete="current-password"
                className="text-field text-field--icon text-field--action"
                id="password"
                name="password"
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                required
                type={showPassword ? "text" : "password"}
                value={password}
              />
              <button
                type="button"
                className="input-action"
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                tabIndex={-1}
              >
                {showPassword ? <EyeSlashIcon className="input-action-icon" /> : <EyeIcon className="input-action-icon" />}
              </button>
            </div>
          </div>

          {error ? (
            <p className="form-error" role="alert" aria-live="assertive">
              {error}
            </p>
          ) : null}

          <Button type="submit" disabled={isSubmitting || !username || !password} className="login-submit">
            {isSubmitting ? (
              <>
                <Spinner className="spinner" />
                Signing in&hellip;
              </>
            ) : (
              "Sign in"
            )}
          </Button>
        </form>

        <footer className="login-footer">
          <p>&copy; {new Date().getFullYear()} Canadian Energy Services. All rights reserved.</p>
        </footer>
      </section>
    </main>
  );
}
