import React, { useState, useEffect, useRef } from "react"
import { ScrollCoinCanvas } from "./ScrollCoinCanvas"

interface LandingHeroProps {
  onOpenLogin: () => void
  onNavigateDashboard: () => void
  onLoginSuccess: () => void
}

export function LandingHero({
  onOpenLogin,
  onNavigateDashboard,
  onLoginSuccess,
}: LandingHeroProps) {
  const [email, setEmail] = useState("treasury@acmeglobal.com")
  const [password, setPassword] = useState("masterkey123")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isCardVisible, setIsCardVisible] = useState(false)

  const signupCardRef = useRef<HTMLDivElement>(null)

  // ---------------------------------------------------------------------------
  // Intersection Observer for Smooth Signup Entry
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const card = signupCardRef.current
    if (!card) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsCardVisible(true)
          }
        })
      },
      { threshold: 0.2 }
    )

    observer.observe(card)
    return () => observer.disconnect()
  }, [])

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setTimeout(() => {
      setIsSubmitting(false)
      onLoginSuccess()
    }, 500)
  }

  const handleLaunchClick = (e: React.MouseEvent) => {
    e.preventDefault()
    const signupEl = document.getElementById("signup")
    if (signupEl) {
      signupEl.scrollIntoView({ behavior: "smooth" })
    } else {
      onNavigateDashboard()
    }
  }

  return (
    <div
      style={
        {
          "--bg-cream": "#F5F1E8",
          "--ink": "#14120E",
          "--border-soft": "#DCD5C4",
          "--input-bg": "#E3DFD3",
          "--mono": "'JetBrains Mono', 'SFMono-Regular', ui-monospace, Menlo, Consolas, monospace",
          "--display": "'Archivo Black', 'Space Grotesk', 'Arial Black', sans-serif",
        } as React.CSSProperties
      }
      className="bg-[#F5F1E8] text-[#14120E] w-full overflow-x-hidden select-none"
    >
      {/* ============================================================
          SECTION 1: HERO WITH THREE.JS 3D CYLINDER GOLD COIN
      ============================================================= */}
      <section
        id="hero"
        className="relative min-h-screen flex items-center px-6 sm:px-12 lg:px-16 overflow-hidden bg-[#F5F1E8]"
      >
        {/* Top Eyebrow Header */}
        <div className="absolute top-6 left-6 sm:left-12 lg:left-16 font-mono text-xs text-[#14120E] opacity-75 tracking-wider z-20">
          FX // FORECASTER — sandboxed treasury simulation environment. Not connected to production funds.
        </div>

        {/* Hero Grid Container: Left Copy Block + Right 3D WebGL Coin */}
        <div className="relative z-10 w-full max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-center pt-20 pb-16 lg:py-0">
          {/* Left Copy Block */}
          <div className="lg:col-span-7 max-w-[620px]">
            <h1
              style={{ fontFamily: "var(--display)" }}
              className="text-4xl sm:text-5xl lg:text-[58px] leading-[1.08] tracking-tight text-[#14120E] font-black"
            >
              See your future balance as a risk range, not a guess — and fix it in one click.
            </h1>

            <div className="flex flex-wrap gap-3.5 mt-10">
              <button
                onClick={handleLaunchClick}
                style={{ fontFamily: "var(--mono)" }}
                className="px-6 py-4 rounded bg-[#14120E] text-[#F5F1E8] text-xs sm:text-sm font-bold tracking-wider hover:opacity-90 transition-transform active:scale-95 shadow-sm inline-flex items-center gap-2 border border-[#14120E] cursor-pointer"
              >
                LAUNCH TREASURY TERMINAL →
              </button>
              <button
                onClick={onOpenLogin}
                style={{ fontFamily: "var(--mono)" }}
                className="px-6 py-4 rounded bg-transparent text-[#14120E] border border-[#DCD5C4] text-xs sm:text-sm font-bold tracking-wider hover:border-[#14120E] transition-colors active:scale-95 cursor-pointer"
              >
                WISE SANDBOX
              </button>
            </div>
          </div>

          {/* Right 3D Revolving WebGL Gold Coin Stage */}
          <div className="lg:col-span-5 flex justify-center items-center relative min-h-[380px] sm:min-h-[480px] lg:min-h-[560px]">
            <div className="relative w-[340px] h-[340px] sm:w-[460px] sm:h-[460px] lg:w-[520px] lg:h-[520px] flex items-center justify-center">
              {/* WebGL 3D Coin Canvas */}
              <ScrollCoinCanvas />

              {/* Dynamic Soft Floor Shadow */}
              <div
                className="absolute left-1/2 bottom-[4%] w-[65%] h-[34px] -translate-x-1/2 pointer-events-none"
                style={{
                  background:
                    "radial-gradient(ellipse at center, rgba(30, 20, 0, 0.38) 0%, rgba(30, 20, 0, 0.12) 55%, transparent 75%)",
                  filter: "blur(4px)",
                }}
              />
            </div>
          </div>
        </div>

        {/* Hero Bottom Caption */}
        <div className="absolute left-6 sm:left-12 lg:left-16 bottom-6 font-mono text-[11px] text-[#14120E] opacity-60">
          FX // FORECASTER — sandboxed treasury simulation environment. Not connected to production funds.
        </div>
      </section>

      {/* Continuous Seam Divider */}
      <div
        className="h-[1px] mx-6 sm:mx-12 lg:mx-16"
        style={{
          background:
            "linear-gradient(90deg, transparent, #DCD5C4 20%, #DCD5C4 80%, transparent)",
        }}
      />

      {/* ============================================================
          SECTION 2: SIGNUP / AUTHENTICATION PORTAL
      ============================================================= */}
      <section
        id="signup"
        className="min-h-screen flex flex-col items-center justify-center px-6 sm:px-12 py-20 sm:py-28 relative bg-[#F5F1E8]"
      >
        {/* Floating Arrow */}
        <div
          className="font-mono text-2xl opacity-50 mb-6 animate-bounce select-none"
          aria-hidden="true"
        >
          ↑
        </div>

        {/* Signup Card */}
        <div
          ref={signupCardRef}
          className={`w-full max-w-[620px] bg-[#F5F1E8] border-[1.5px] border-[#14120E] rounded-[22px] p-8 sm:p-14 shadow-xl transition-all duration-700 ease-out ${
            isCardVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"
          }`}
        >
          <h2
            style={{ fontFamily: "var(--display)" }}
            className="text-2xl sm:text-3xl lg:text-[34px] font-black text-[#14120E] tracking-tight text-center sm:text-left"
          >
            Unseal the Risk Tapestry
          </h2>
          <p
            style={{ fontFamily: "var(--mono)" }}
            className="text-sm font-normal text-[#14120E] opacity-75 mt-3 text-center sm:text-left"
          >
            Authenticate to view the unscripted future.
          </p>

          <form onSubmit={handleLoginSubmit} className="mt-8 space-y-6">
            {/* Email Field */}
            <div>
              <label
                htmlFor="email"
                style={{ fontFamily: "var(--mono)" }}
                className="text-xs font-bold text-[#14120E] block mb-2"
              >
                Access Identifier (Email)
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
                style={{ fontFamily: "var(--mono)" }}
                className="w-full px-4 py-3.5 rounded-md border border-[#DCD5C4] bg-[#E3DFD3] text-sm text-[#14120E] outline-none focus:border-[#14120E] focus:ring-2 focus:ring-[rgba(20,18,14,0.12)] transition-all"
              />
            </div>

            {/* Password Field */}
            <div>
              <label
                htmlFor="password"
                style={{ fontFamily: "var(--mono)" }}
                className="text-xs font-bold text-[#14120E] block mb-2"
              >
                Temporal Cipher (Password)
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                style={{ fontFamily: "var(--mono)" }}
                className="w-full px-4 py-3.5 rounded-md border border-[#DCD5C4] bg-[#E3DFD3] text-sm text-[#14120E] outline-none focus:border-[#14120E] focus:ring-2 focus:ring-[rgba(20,18,14,0.12)] transition-all"
              />
            </div>

            {/* Forgot Link */}
            <div className="text-center pt-1">
              <button
                type="button"
                onClick={() => {
                  setEmail("treasury@acmeglobal.com")
                  setPassword("masterkey123")
                }}
                style={{ fontFamily: "var(--mono)" }}
                className="text-xs text-[#14120E] opacity-80 underline hover:opacity-100 bg-transparent border-none cursor-pointer"
              >
                Can't remember your cipher?
              </button>
            </div>

            {/* Action Buttons */}
            <div className="space-y-3 pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                style={{ fontFamily: "var(--mono)" }}
                className="w-full py-4 px-6 rounded-lg font-bold text-sm bg-[#14120E] text-[#F5F1E8] border border-[#14120E] hover:opacity-90 transition-all active:scale-[0.99] cursor-pointer"
              >
                {isSubmitting ? "Manifesting Forecast..." : "Manifest the Forecast"}
              </button>

              <button
                type="button"
                onClick={onNavigateDashboard}
                style={{ fontFamily: "var(--mono)" }}
                className="w-full py-4 px-6 rounded-lg font-bold text-sm bg-[#E3DFD3] text-[#14120E] border border-[#DCD5C4] hover:border-[#14120E] transition-all active:scale-[0.99] cursor-pointer"
              >
                Forge a New Path
              </button>
            </div>
          </form>
        </div>

        {/* Footer Tag */}
        <div
          style={{ fontFamily: "var(--mono)" }}
          className="mt-12 text-[11px] opacity-50 tracking-wider text-center text-[#14120E]"
        >
          FX // FORECASTER // SECURE ACCESS PORTAL
        </div>
      </section>
    </div>
  )
}

export default LandingHero
