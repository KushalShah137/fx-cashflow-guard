import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { Float, Environment } from "@react-three/drei";
import { InteractiveCoin, CURRENCIES } from "./InteractiveCoin";

interface CoinCanvasProps {
  onCurrencyChange?: (currency: typeof CURRENCIES[0]) => void;
  className?: string;
}

export function CoinCanvas({ onCurrencyChange, className }: CoinCanvasProps) {
  return (
    <div className={`relative w-full h-[380px] md:h-[480px] select-none ${className || ""}`}>
      <Canvas
        camera={{ position: [0, 0, 4.5], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
        dpr={[1, 2]}
      >
        <ambientLight intensity={1.2} />
        <directionalLight position={[5, 8, 5]} intensity={2.4} color="#FFFBEB" castShadow />
        <directionalLight position={[-5, -2, -2]} intensity={0.8} color="#D97706" />
        <pointLight position={[0, 4, 3]} intensity={1.5} color="#FEF08A" />

        <Suspense fallback={null}>
          <Float
            speed={1.5}
            rotationIntensity={0.2}
            floatIntensity={0.3}
            floatingRange={[-0.05, 0.05]}
          >
            <InteractiveCoin onCurrencyChange={onCurrencyChange} />
          </Float>
          <Environment preset="city" />
        </Suspense>
      </Canvas>
      <div className="absolute bottom-2 left-0 right-0 text-center pointer-events-none">
        <span className="font-mono text-[11px] uppercase tracking-wider text-[#71717A] bg-[#F9F8F5]/80 px-2 py-0.5 border border-[#E4E2D9] rounded-sm">
          CLICK COIN TO TOSS & SWITCH CURRENCY // DRAG TO TILT
        </span>
      </div>
    </div>
  );
}
