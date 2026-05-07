import { type FormEvent, useRef, useState } from "react";
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

function UserIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" />
    </svg>
  );
}

function LockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path
        fillRule="evenodd"
        d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function EyeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
      <path
        fillRule="evenodd"
        d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function EyeSlashIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M3.28 2.22a.75.75 0 00-1.06 1.06l14.5 14.5a.75.75 0 101.06-1.06l-1.745-1.745A10.029 10.029 0 0018 10c-1.274-4.057-5.064-7-9.542-7a10.029 10.029 0 00-4.198.928L3.28 2.22zM10 5.75a4.25 4.25 0 014.122 3.197l-1.53-1.53A2.75 2.75 0 0010 5.75zM5.87 6.143l1.528 1.53A2.75 2.75 0 0010 13.25c.51 0 .994-.14 1.41-.388l1.858 1.858A4.238 4.238 0 0110 15.75a4.25 4.25 0 01-4.122-3.197l-1.53 1.53A5.738 5.738 0 0010 16.75c1.794 0 3.4-.76 4.542-1.962l2.18 2.18A10.03 10.03 0 0110 17C5.522 17 1.732 14.057.458 10a10.03 10.03 0 012.588-4.194l2.824 2.824z"
      />
      <path d="M12.25 9.75l-2.5-2.5a2.75 2.75 0 012.5 2.5z" />
    </svg>
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
