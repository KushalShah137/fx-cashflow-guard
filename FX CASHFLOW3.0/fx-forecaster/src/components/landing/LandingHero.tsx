import React, { useState } from "react"
import { ScrollCoinCanvas } from "./ScrollCoinCanvas"

interface LandingHeroProps {
  onOpenLogin: () => void
  onNavigateDashboard: () => void
  onLoginSuccess: () => void
}

export function LandingHero({ onOpenLogin, onNavigateDashboard, onLoginSuccess }: LandingHeroProps) {
  const [email, setEmail] = useState("treasury@acmeglobal.com")
  const [password, setPassword] = useState("masterkey123")
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setTimeout(() => {
      setIsSubmitting(false)
      onLoginSuccess()
    }, 600)
  }

  return (
    <>
      <main className="hero">
        <ScrollCoinCanvas />

        {/* Hero Headline & CTA Actions */}
        <div className="hero-text">
          <h1 className="hero-title">
            See your future balance as a risk range, not a guess — and fix it in one click.
          </h1>
          <div className="cta-row">
            <button 
              onClick={onNavigateDashboard}
              className="btn btn-dark uppercase font-bold"
            >
              LAUNCH TREASURY TERMINAL →
            </button>
            <button 
              onClick={onOpenLogin}
              className="btn btn-light uppercase font-bold"
            >
              Wise Sandbox
            </button>
          </div>
        </div>

        {/* Sign In to Treasury Form Card */}
        <div className="signin-card">
          <h2>Sign in to Treasury</h2>
          <p className="sub">Access automated risk hedging and live sandbox feeds</p>

          <form onSubmit={handleLogin}>
            <label className="signin-label">Corporate Email</label>
            <div className="field">
<<<<<<< HEAD
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#4a4a46]">
=======
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#71717A]">
>>>>>>> e52636e7bdd5aab167bdf11d78c590d4c59ba74b
                <rect x="2" y="4" width="20" height="16" rx="2" />
                <path d="M22 6l-10 7L2 6" />
              </svg>
              <input 
                type="email" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="treasury@acmeglobal.com"
                required
              />
            </div>

            <label className="signin-label">Master Key / Password</label>
            <div className="field">
<<<<<<< HEAD
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#4a4a46]">
=======
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#71717A]">
>>>>>>> e52636e7bdd5aab167bdf11d78c590d4c59ba74b
                <rect x="4" y="10" width="16" height="10" rx="2" />
                <path d="M8 10V7a4 4 0 0 1 8 0v3" />
              </svg>
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
              />
            </div>

            <button type="submit" className="signin-submit font-bold" disabled={isSubmitting}>
              {isSubmitting ? "Authenticating..." : "Log in to Workspace →"}
            </button>
          </form>
          
          <div className="demo-link">
            Exploring the interface?{" "}
            <button 
              type="button"
              onClick={onNavigateDashboard}
<<<<<<< HEAD
              className="underline cursor-pointer font-bold text-[#111111] border-none bg-transparent p-0"
=======
              className="underline cursor-pointer font-bold text-[#18181B] border-none bg-transparent p-0"
>>>>>>> e52636e7bdd5aab167bdf11d78c590d4c59ba74b
            >
              Try interactive demo
            </button>
          </div>
        </div>
      </main>

      <div className="footnote">
        FX // FORECASTER — sandboxed treasury simulation environment. Not connected to production funds.
      </div>
    </>
  )
}
