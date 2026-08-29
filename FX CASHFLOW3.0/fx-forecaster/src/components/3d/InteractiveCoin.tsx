import React, { useRef, useState, useMemo } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { useSpring, a } from "@react-spring/three";
import * as THREE from "three";

export const CURRENCIES = [
  { symbol: "$", code: "USD", name: "US Dollar", color: "#B45309" },
  { symbol: "₹", code: "INR", name: "Indian Rupee", color: "#18181B" },
  { symbol: "€", code: "EUR", name: "Euro", color: "#1D4ED8" },
  { symbol: "£", code: "GBP", name: "British Pound", color: "#047857" },
];

function createCoinTexture(symbol: string, code: string) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext("2d")!;

  // Background gradient (brushed metallic gold/brass)
  const grad = ctx.createRadialGradient(256, 256, 50, 256, 256, 256);
  grad.addColorStop(0, "#FCE79A");
  grad.addColorStop(0.5, "#EAB308");
  grad.addColorStop(0.85, "#CA8A04");
  grad.addColorStop(1, "#854D0E");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.arc(256, 256, 250, 0, Math.PI * 2);
  ctx.fill();

  // Outer ring border
  ctx.strokeStyle = "#FEF08A";
  ctx.lineWidth = 14;
  ctx.beginPath();
  ctx.arc(256, 256, 235, 0, Math.PI * 2);
  ctx.stroke();

  // Beaded rim
  ctx.fillStyle = "#FEF08A";
  for (let i = 0; i < 48; i++) {
    const angle = (i / 48) * Math.PI * 2;
    const x = 256 + Math.cos(angle) * 215;
    const y = 256 + Math.sin(angle) * 215;
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  }

  // Inner ring
  ctx.strokeStyle = "#854D0E";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(256, 256, 195, 0, Math.PI * 2);
  ctx.stroke();

  // Currency Symbol
  ctx.fillStyle = "#713F12";
  ctx.font = "bold 170px serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(symbol, 256, 240);

  // Currency Code / Label
  ctx.font = "600 32px monospace";
  ctx.fillStyle = "#854D0E";
  ctx.fillText(`FX // ${code}`, 256, 350);

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

export function InteractiveCoin({
  onCurrencyChange,
}: {
  onCurrencyChange?: (c: typeof CURRENCIES[0]) => void;
}) {
  const meshRef = useRef<THREE.Group>(null);
  const [currencyIndex, setCurrencyIndex] = useState(0);
  const [isFlipping, setIsFlipping] = useState(false);
  const { pointer } = useThree();

  // Pre-generate textures for smooth mid-flip swap
  const textures = useMemo(
    () => CURRENCIES.map((c) => createCoinTexture(c.symbol, c.code)),
    []
  );

  // Spring physics for click-to-toss flip
  const [{ flipRotation, tossY }, api] = useSpring(() => ({
    flipRotation: 0,
    tossY: 0,
    config: { mass: 1.2, tension: 140, friction: 14 },
  }));

  const handlePointerDown = (e: any) => {
    e.stopPropagation();
    if (isFlipping) return;
    setIsFlipping(true);

    const nextIndex = (currencyIndex + 1) % CURRENCIES.length;

    // Toss up and spin 3 full rotations (6 * PI)
    api.start({
      to: async (next) => {
        // Trigger toss jump & rapid spin
        await next({
          tossY: 1.4,
          flipRotation: Math.PI * 4,
          config: { mass: 0.8, tension: 220, friction: 12 },
        });

        // Mid-flight: switch texture when passing edge-on
        setCurrencyIndex(nextIndex);
        if (onCurrencyChange) onCurrencyChange(CURRENCIES[nextIndex]);

        // Settle back to base height
        await next({
          tossY: 0,
          flipRotation: Math.PI * 6,
          config: { mass: 1.5, tension: 160, friction: 18 },
        });

        // Reset rotation accumulator
        api.set({ flipRotation: 0 });
        setIsFlipping(false);
      },
    });
  };

  // Mouse tracking damping
  useFrame((_state, delta) => {
    if (!meshRef.current) return;
    if (!isFlipping) {
      // Damped tilt towards pointer
      const targetRotX = -pointer.y * 0.45;
      const targetRotY = pointer.x * 0.45;
      meshRef.current.rotation.x = THREE.MathUtils.damp(
        meshRef.current.rotation.x,
        targetRotX,
        4,
        delta
      );
      meshRef.current.rotation.y = THREE.MathUtils.damp(
        meshRef.current.rotation.y,
        targetRotY,
        4,
        delta
      );
    }
  });

  return (
    <a.group
      ref={meshRef}
      position-y={tossY}
      rotation-y={flipRotation}
      onPointerDown={handlePointerDown}
      scale={[2.2, 2.2, 2.2]}
    >
      {/* Coin Cylinder Geometry */}
      <mesh castShadow receiveShadow>
        <cylinderGeometry args={[1, 1, 0.12, 64, 1, false]} />
        <meshStandardMaterial
          color="#D97706"
          metalness={0.92}
          roughness={0.25}
          bumpScale={0.05}
        />
      </mesh>

      {/* Front Face Disk */}
      <mesh position={[0, 0.061, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.98, 64]} />
        <meshStandardMaterial
          map={textures[currencyIndex]}
          metalness={0.85}
          roughness={0.28}
        />
      </mesh>

      {/* Back Face Disk */}
      <mesh position={[0, -0.061, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.98, 64]} />
        <meshStandardMaterial
          map={textures[currencyIndex]}
          metalness={0.85}
          roughness={0.28}
        />
      </mesh>
    </a.group>
  );
}
