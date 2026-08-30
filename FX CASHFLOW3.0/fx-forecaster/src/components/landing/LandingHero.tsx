import React, { useState, useEffect, useRef } from "react"

interface LandingHeroProps {
  onOpenLogin: () => void
  onNavigateDashboard: () => void
  onLoginSuccess: () => void
}

const COIN_IMAGE_URI =
  "data:image/webp;base64,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"

export function LandingHero({
  onOpenLogin,
  onNavigateDashboard,
  onLoginSuccess,
}: LandingHeroProps) {
  const [email, setEmail] = useState("treasury@acmeglobal.com")
  const [password, setPassword] = useState("masterkey123")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isCardVisible, setIsCardVisible] = useState(false)

  const coinRef = useRef<HTMLDivElement>(null)
  const coinFloatRef = useRef<HTMLDivElement>(null)
  const coinShadowRef = useRef<HTMLDivElement>(null)
  const signupCardRef = useRef<HTMLDivElement>(null)

  // ---------------------------------------------------------------------------
  // 3D Coin Rotation & Floating Physics
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const coin = coinRef.current
    const coinFloat = coinFloatRef.current
    const coinShadow = coinShadowRef.current
    if (!coin || !coinFloat || !coinShadow) return

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    const startTime = performance.now()
    let animationFrameId: number

    let currentAngle = 0
    let targetAngle = 0
    let lastScrollY = window.scrollY

    const onScroll = () => {
      const scrollY = window.scrollY
      const delta = scrollY - lastScrollY
      lastScrollY = scrollY
      targetAngle += delta * 0.9
    }
    window.addEventListener("scroll", onScroll, { passive: true })

    const FLOAT_AMPLITUDE = 14 // px, how high/low it drifts
    const FLOAT_PERIOD_MS = 4200 // ms, one full up-down cycle

    const animate = (now: number) => {
      if (!reduceMotion) {
        const elapsed = now - startTime

        // -- rotation with momentum ease --
        currentAngle += (targetAngle - currentAngle) * 0.08
        targetAngle += 0.025 // gentle idle drift so it's never fully still
        const wobble = Math.sin(currentAngle * (Math.PI / 180) * 2) * 3.5
        coin.style.transform = `rotateY(${currentAngle}deg) rotateX(${wobble}deg)`

        // -- float --
        const floatPhase = (elapsed / FLOAT_PERIOD_MS) * Math.PI * 2
        const floatY = Math.sin(floatPhase) * FLOAT_AMPLITUDE
        coinFloat.style.transform = `translateY(${floatY}px)`

        // -- shadow reacts to float height --
        const floatNorm = (floatY + FLOAT_AMPLITUDE) / (FLOAT_AMPLITUDE * 2) // 0..1
        const shadowScale = 0.85 + (1 - floatNorm) * 0.22
        const shadowOpacity = 0.55 + (1 - floatNorm) * 0.45
        coinShadow.style.transform = `translateX(-50%) scale(${shadowScale.toFixed(3)})`
        coinShadow.style.opacity = shadowOpacity.toFixed(3)
      }
      animationFrameId = requestAnimationFrame(animate)
    }

    animationFrameId = requestAnimationFrame(animate)

    return () => {
      window.removeEventListener("scroll", onScroll)
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

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
          "--coin-image": `url('${COIN_IMAGE_URI}')`,
        } as React.CSSProperties
      }
      className="bg-[var(--bg-cream)] text-[var(--ink)] w-full overflow-x-hidden font-sans select-none"
    >
      {/* ============================================================
          SECTION 1: HERO
      ============================================================= */}
      <section
        id="hero"
        className="relative min-h-screen flex items-center px-6 sm:px-12 lg:px-16 overflow-hidden"
      >
        {/* Top Eyebrow Header */}
        <div className="absolute top-6 left-6 sm:left-12 lg:left-16 font-mono text-xs text-[var(--ink)] opacity-75 tracking-wider">
          FX // FORECASTER — sandboxed treasury simulation environment. Not connected to production funds.
        </div>

        {/* Left Copy Block */}
        <div className="relative z-10 max-w-[640px] my-auto pt-16 sm:pt-0">
          <h1
            style={{ fontFamily: "var(--display)" }}
            className="text-4xl sm:text-5xl lg:text-[62px] leading-[1.05] tracking-tight text-[var(--ink)] font-black"
          >
            See your future balance as a risk range, not a guess — and fix it in one click.
          </h1>

          <div className="flex flex-wrap gap-3.5 mt-10">
            <button
              onClick={handleLaunchClick}
              style={{ fontFamily: "var(--mono)" }}
              className="px-6 py-4 rounded bg-[var(--ink)] text-[var(--bg-cream)] text-xs sm:text-sm font-bold tracking-wider hover:opacity-90 transition-transform active:scale-95 shadow-sm inline-flex items-center gap-2 border border-[var(--ink)] cursor-pointer"
            >
              LAUNCH TREASURY TERMINAL →
            </button>
            <button
              onClick={onOpenLogin}
              style={{ fontFamily: "var(--mono)" }}
              className="px-6 py-4 rounded bg-transparent text-[var(--ink)] border border-[var(--border-soft)] text-xs sm:text-sm font-bold tracking-wider hover:border-[var(--ink)] transition-colors active:scale-95 cursor-pointer"
            >
              WISE SANDBOX
            </button>
          </div>
        </div>

        {/* Right 3D Revolving Coin Stage */}
        <div
          className="absolute right-[-14%] sm:right-[-6%] lg:right-[-2%] top-1/2 -translate-y-1/2 w-[380px] h-[380px] sm:w-[540px] sm:h-[540px] lg:w-[640px] lg:h-[640px] pointer-events-none z-0"
          aria-hidden="true"
        >
          {/* Float container */}
          <div
            ref={coinFloatRef}
            className="absolute inset-0 m-auto w-[340px] h-[340px] sm:w-[480px] sm:h-[480px] lg:w-[560px] lg:h-[560px]"
            style={{ willChange: "transform" }}
          >
            {/* Perspective wrapper */}
            <div
              className="absolute inset-0"
              style={{ perspective: "1600px" }}
            >
              {/* Coin 3D flip card */}
              <div
                ref={coinRef}
                className="absolute inset-0"
                style={{
                  transformStyle: "preserve-3d",
                  willChange: "transform",
                }}
              >
                {/* Front Face */}
                <div
                  className="absolute inset-0"
                  style={{
                    backfaceVisibility: "hidden",
                    backgroundImage: "var(--coin-image)",
                    backgroundSize: "contain",
                    backgroundRepeat: "no-repeat",
                    backgroundPosition: "center",
                    filter: "drop-shadow(0 22px 28px rgba(80, 55, 10, 0.30))",
                  }}
                />
                {/* Back Face (Mirrored so symbol stays correct) */}
                <div
                  className="absolute inset-0"
                  style={{
                    backfaceVisibility: "hidden",
                    transform: "rotateY(180deg) scaleX(-1)",
                    backgroundImage: "var(--coin-image)",
                    backgroundSize: "contain",
                    backgroundRepeat: "no-repeat",
                    backgroundPosition: "center",
                    filter: "drop-shadow(0 22px 28px rgba(80, 55, 10, 0.30))",
                  }}
                />
              </div>
            </div>
          </div>

          {/* Realistic Floor Shadow */}
          <div
            ref={coinShadowRef}
            className="absolute left-1/2 bottom-[8%] w-[58%] h-[40px] -translate-x-1/2"
            style={{
              background:
                "radial-gradient(ellipse at center, rgba(30, 20, 0, 0.32) 0%, rgba(30, 20, 0, 0.12) 55%, transparent 75%)",
              filter: "blur(3px)",
              willChange: "transform, opacity",
            }}
          />
        </div>

        {/* Hero Bottom Caption */}
        <div className="absolute left-6 sm:left-12 lg:left-16 bottom-6 font-mono text-[11px] text-[var(--ink)] opacity-60">
          FX // FORECASTER — sandboxed treasury simulation environment. Not connected to production funds.
        </div>
      </section>

      {/* Seam continuous divider */}
      <div
        className="h-[1px] mx-6 sm:mx-12 lg:mx-16"
        style={{
          background:
            "linear-gradient(90deg, transparent, var(--border-soft) 20%, var(--border-soft) 80%, transparent)",
        }}
      />

      {/* ============================================================
          SECTION 2: SIGNUP / AUTHENTICATION
      ============================================================= */}
      <section
        id="signup"
        className="min-h-screen flex flex-col items-center justify-center px-6 sm:px-12 py-20 sm:py-28 relative"
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
          className={`w-full max-w-[620px] bg-[var(--bg-cream)] border-[1.5px] border-[var(--ink)] rounded-[22px] p-8 sm:p-14 shadow-xl transition-all duration-700 ease-out ${
            isCardVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-10"
          }`}
        >
          <h2
            style={{ fontFamily: "var(--display)" }}
            className="text-2xl sm:text-3xl lg:text-[34px] font-black text-[var(--ink)] tracking-tight text-center sm:text-left"
          >
            Unseal the Risk Tapestry
          </h2>
          <p
            style={{ fontFamily: "var(--mono)" }}
            className="text-sm font-normal text-[var(--ink)] opacity-75 mt-3 text-center sm:text-left"
          >
            Authenticate to view the unscripted future.
          </p>

          <form onSubmit={handleLoginSubmit} className="mt-8 space-y-6">
            {/* Email Field */}
            <div>
              <label
                htmlFor="email"
                style={{ fontFamily: "var(--mono)" }}
                className="text-xs font-bold text-[var(--ink)] block mb-2"
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
                className="w-full px-4 py-3.5 rounded-md border border-[var(--border-soft)] bg-[var(--input-bg)] text-sm text-[var(--ink)] outline-none focus:border-[var(--ink)] focus:ring-2 focus:ring-[rgba(20,18,14,0.12)] transition-all"
              />
            </div>

            {/* Password Field */}
            <div>
              <label
                htmlFor="password"
                style={{ fontFamily: "var(--mono)" }}
                className="text-xs font-bold text-[var(--ink)] block mb-2"
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
                className="w-full px-4 py-3.5 rounded-md border border-[var(--border-soft)] bg-[var(--input-bg)] text-sm text-[var(--ink)] outline-none focus:border-[var(--ink)] focus:ring-2 focus:ring-[rgba(20,18,14,0.12)] transition-all"
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
                className="text-xs text-[var(--ink)] opacity-80 underline hover:opacity-100 bg-transparent border-none cursor-pointer"
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
                className="w-full py-4 px-6 rounded-lg font-bold text-sm bg-[var(--ink)] text-[var(--bg-cream)] border border-[var(--ink)] hover:opacity-90 transition-all active:scale-[0.99] cursor-pointer"
              >
                {isSubmitting ? "Manifesting Forecast..." : "Manifest the Forecast"}
              </button>

              <button
                type="button"
                onClick={onNavigateDashboard}
                style={{ fontFamily: "var(--mono)" }}
                className="w-full py-4 px-6 rounded-lg font-bold text-sm bg-[var(--input-bg)] text-[var(--ink)] border border-[var(--border-soft)] hover:border-[var(--ink)] transition-all active:scale-[0.99] cursor-pointer"
              >
                Forge a New Path
              </button>
            </div>
          </form>
        </div>

        {/* Footer Tag */}
        <div
          style={{ fontFamily: "var(--mono)" }}
          className="mt-12 text-[11px] opacity-50 tracking-wider text-center text-[var(--ink)]"
        >
          FX // FORECASTER // SECURE ACCESS PORTAL
        </div>
      </section>
    </div>
  )
}

export default LandingHero
