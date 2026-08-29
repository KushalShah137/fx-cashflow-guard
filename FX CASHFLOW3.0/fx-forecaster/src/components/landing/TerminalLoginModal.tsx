import React, { useState } from "react"
import { LiquidButton, MetalButton } from "@/components/ui/liquid-glass-button"
import { ShieldCheck, Terminal, X, Lock, Key } from "lucide-react"

interface TerminalLoginModalProps {
  isOpen: boolean
  onClose: () => void
  onLoginSuccess: () => void
}

export function TerminalLoginModal({
  isOpen,
  onClose,
  onLoginSuccess,
}: TerminalLoginModalProps) {
  const [email, setEmail] = useState("treasury.demo@enterprise.io")
  const [passphrase, setPassphrase] = useState("••••••••••••")
  const [isLoading, setIsLoading] = useState(false)

  if (!isOpen) return null

  const handleAuthenticate = (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setTimeout(() => {
      setIsLoading(false)
      onLoginSuccess()
    }, 600)
  }

  const handleQuickDemo = () => {
    setIsLoading(true)
    setTimeout(() => {
      setIsLoading(false)
      onLoginSuccess()
    }, 400)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-md bg-[#FAF9F5] border border-[#18181B] shadow-2xl p-6 rounded-none">
        {/* Terminal Header */}
        <div className="flex items-center justify-between border-b border-[#E4E2D9] pb-3 mb-5">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 bg-[#18181B] rounded-none" />
            <span className="font-mono text-xs font-bold tracking-wider uppercase">
              NODE_01 // SECURE_AUTH_GATEWAY
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-[#71717A] hover:text-[#18181B] transition-colors p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Security Badge */}
        <div className="bg-[#F4F3EE] border border-[#E4E2D9] p-3 mb-5 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-[#047857] shrink-0 mt-0.5" />
          <div>
            <div className="font-mono text-[11px] font-bold text-[#18181B] uppercase">
              WISE SANDBOX ENVIRONMENT CONNECTED
            </div>
            <div className="text-xs text-[#71717A] font-mono mt-0.5">
              Protocol: OAuth 2.0 PKCE • Sandbox Node ID: TRX-9941
            </div>
          </div>
        </div>

        <form onSubmit={handleAuthenticate} className="space-y-4">
          <div>
            <label className="block font-mono text-[11px] uppercase tracking-wider text-[#71717A] mb-1">
              Operator Identifier
            </label>
            <div className="relative">
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-[#FFFFFF] border-b border-[#18181B] font-mono text-sm px-3 py-2 text-[#18181B] focus:outline-none focus:border-b-2"
                placeholder="operator@treasury.bank"
                required
              />
            </div>
          </div>

          <div>
            <label className="block font-mono text-[11px] uppercase tracking-wider text-[#71717A] mb-1">
              API Security Key / Passphrase
            </label>
            <div className="relative">
              <input
                type="password"
                value={passphrase}
                onChange={(e) => setPassphrase(e.target.value)}
                className="w-full bg-[#FFFFFF] border-b border-[#18181B] font-mono text-sm px-3 py-2 text-[#18181B] focus:outline-none focus:border-b-2"
                placeholder="••••••••••••"
                required
              />
            </div>
          </div>

          <div className="pt-2 space-y-3">
            <MetalButton
              type="submit"
              variant="default"
              className="w-full h-11 text-xs uppercase tracking-wider font-mono"
            >
              {isLoading ? "AUTHENTICATING SECURE SESSION..." : "AUTHENTICATE NODE_01"}
            </MetalButton>

            <div className="relative flex py-1 items-center">
              <div className="flex-grow border-t border-[#E4E2D9]"></div>
              <span className="flex-shrink mx-3 font-mono text-[10px] uppercase text-[#71717A]">
                EVALUATION ACCESS
              </span>
              <div className="flex-grow border-t border-[#E4E2D9]"></div>
            </div>

            <LiquidButton
              type="button"
              onClick={handleQuickDemo}
              className="w-full h-11 text-xs uppercase tracking-wider font-mono"
            >
              <Terminal className="w-3.5 h-3.5 mr-1" />
              1-CLICK QUICK DEMO ACCESS (BYPASS)
            </LiquidButton>
          </div>
        </form>

        <div className="mt-4 pt-3 border-t border-[#E4E2D9] text-center">
          <p className="font-mono text-[10px] text-[#71717A]">
            LOCAL ENCLAVE VERIFIED • 256-BIT ENCRYPTION
          </p>
        </div>
      </div>
    </div>
  )
}
