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

        <div className="hero-text">
          <h1 className="hero-title">See your future balance as a risk range, not a guess — and fix it in one click.</h1>
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
              OPERATOR LOGIN (NODE_01)
            </button>
          </div>
        </div>

        <div className="signin-card">
          <h2>Sign in to Treasury</h2>
          <p className="sub">Access automated risk hedging and live sandbox feeds</p>

          <form onSubmit={handleLogin}>
            <label className="signin-label">Corporate Email</label>
            <div className="field">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 4h16v16H4z" opacity="0"/>
                <path d="M22 6l-10 7L2 6"/>
                <path d="M2 6h20v12H2z"/>
              </svg>
              <input 
                type="text" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <label className="signin-label">Master Key / Password</label>
            <div className="field">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="4" y="10" width="16" height="10" rx="2"/>
                <path d="M8 10V7a4 4 0 0 1 8 0v3"/>
              </svg>
              <input 
                type="password" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="signin-submit" disabled={isSubmitting}>
              {isSubmitting ? "Logging in..." : "Log in to Workspace →"}
            </button>
          </form>
          
          <div className="demo-link">
            Exploring the interface?{" "}
            <button 
              onClick={onNavigateDashboard}
              className="underline cursor-pointer font-bold text-black border-none bg-transparent p-0"
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
