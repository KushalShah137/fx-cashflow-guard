'use client'

import { Canvas, useFrame } from '@react-three/fiber'
import { Environment, Text } from '@react-three/drei'
import { motion } from 'framer-motion-3d'
import { useAnimation } from 'framer-motion'
import { useEffect, useRef, useState } from 'react'
import type { Group } from 'three'
import type { CanvasProps } from '@react-three/fiber'

const SYMBOLS = ['$', '₹', '€', '£']

function Coin() {
  const group = useRef<Group>(null)
  const controls = useAnimation()
  const [hovered, setHovered] = useState(false)
  const [symbolIndex, setSymbolIndex] = useState(0)
  const [reducedMotion, setReducedMotion] = useState(false)
  const pointer = useRef({ x: 0, y: 0 })
  const target = useRef({ x: 0, y: 0 })
  const busy = useRef(false)

  useEffect(() => {
    setReducedMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  }, [])

  useFrame((_, delta) => {
    if (!group.current || busy.current) return
    target.current.x = hovered ? pointer.current.y * 0.24 : 0
    target.current.y = hovered ? pointer.current.x * 0.42 : 0
    const nextX = Math.PI / 2 + target.current.x
    const nextY = target.current.y
    group.current.rotation.x += (nextX - group.current.rotation.x) * Math.min(1, delta * 5)
    group.current.rotation.y += (nextY - group.current.rotation.y) * Math.min(1, delta * 5)
  })

  const toss = async () => {
    if (busy.current) return
    busy.current = true
    const duration = reducedMotion ? 0.55 : 1.25
    const nextIndex = (symbolIndex + 1) % SYMBOLS.length
    await controls.start({ y: 2.5, rotateY: Math.PI * 2, transition: { duration: duration / 2, ease: 'easeOut' } })
    setSymbolIndex(nextIndex)
    await controls.start({ y: 0, rotateY: Math.PI * 4, transition: { duration: duration / 2, ease: 'easeInOut' } })
    busy.current = false
  }

  return (
    <motion.group ref={group} animate={controls} initial={{ y: 0, rotateX: Math.PI / 2, rotateY: 0 }} onClick={toss}>
      <mesh castShadow receiveShadow>
        <cylinderGeometry args={[1.55, 1.55, 0.28, 96, 6]} />
        <meshStandardMaterial color="#d6a62a" metalness={0.96} roughness={0.14} envMapIntensity={1.8} />
      </mesh>
      <mesh position={[0, 0.151, 0]} rotation={[Math.PI / 2, 0, 0]} castShadow onPointerEnter={() => setHovered(true)} onPointerLeave={() => setHovered(false)} onPointerMove={(event) => { pointer.current.x = event.pointer.x; pointer.current.y = event.pointer.y }}>
        <ringGeometry args={[1.18, 1.43, 96]} />
        <meshStandardMaterial color="#f2c94c" metalness={0.98} roughness={0.1} />
      </mesh>
      <mesh position={[0, -0.151, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.18, 1.43, 96]} />
        <meshStandardMaterial color="#b88616" metalness={0.98} roughness={0.12} />
      </mesh>
      <Text fontSize={0.86} anchorX="center" anchorY="middle" position={[0, 0.19, 0]} rotation={[-Math.PI / 2, 0, 0]} depthOffset={-0.2}>
        {SYMBOLS[symbolIndex]}
        <meshStandardMaterial color="#8f650d" metalness={0.92} roughness={0.2} />
      </Text>
    </motion.group>
  )
}

export function InteractiveCoinCanvas({ className, ...props }: CanvasProps & { className?: string }) {
  return (
    <div className={className ?? 'h-screen w-full'} role="img" aria-label="Interactive gold currency coin. Hover to tilt and click to toss.">
      <Canvas shadows camera={{ position: [0, 0.15, 5.2], fov: 38 }} dpr={[1, 2]} {...props}>
        <color attach="background" args={['#101114']} />
        <ambientLight intensity={0.65} />
        <spotLight position={[3, 4, 4]} angle={0.38} penumbra={0.9} intensity={90} castShadow shadow-mapSize={[1024, 1024]} />
        <directionalLight position={[-4, 1, -5]} intensity={5} color="#fff0c2" />
        <pointLight position={[2, -2, 3]} intensity={8} color="#d6a62a" />
        <Coin />
        <Environment preset="city" />
      </Canvas>
    </div>
  )
}

export default InteractiveCoinCanvas
