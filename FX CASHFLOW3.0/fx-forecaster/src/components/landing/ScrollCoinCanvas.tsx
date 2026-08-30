import React, { useEffect, useRef, useState } from "react"
import * as THREE from "three"

export function ScrollCoinCanvas() {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)")
    setPrefersReducedMotion(mediaQuery.matches)
    const listener = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches)
    mediaQuery.addEventListener("change", listener)
    return () => mediaQuery.removeEventListener("change", listener)
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    let animationFrameId: number
    let width = container.clientWidth || 500
    let height = container.clientHeight || 500

    // 1. Setup WebGL Renderer
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        alpha: true,
        antialias: true,
        powerPreference: "high-performance",
      })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
      renderer.setSize(width, height)
      renderer.toneMapping = THREE.ACESFilmicToneMapping
      renderer.toneMappingExposure = 1.2
    } catch (e) {
      console.warn("WebGL initialization failed:", e)
      return
    }

    // 2. Setup Scene & Perspective Camera
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 100)
    camera.position.set(0, 0, 7.5)

    // 3. Studio Lights for Rich Gold Depth and Specular Highlights
    const ambientLight = new THREE.AmbientLight(0xfff6e4, 0.8)
    scene.add(ambientLight)

    const keyLight = new THREE.DirectionalLight(0xfff0c8, 2.4)
    keyLight.position.set(4, 5, 5)
    scene.add(keyLight)

    const rimLight = new THREE.DirectionalLight(0xffd470, 1.5)
    rimLight.position.set(-5, -2, -3)
    scene.add(rimLight)

    const topFill = new THREE.PointLight(0xffe8aa, 1.0, 10)
    topFill.position.set(0, 3, 4)
    scene.add(topFill)

    // 4. Create High-Resolution Minted Gold Coin Face Texture
    function createCoinFaceTexture(symbol: string) {
      const size = 1024
      const c = document.createElement("canvas")
      c.width = size
      c.height = size
      const ctx = c.getContext("2d")
      if (!ctx) return new THREE.Texture()

      const center = size / 2
      const radius = size / 2 - 14

      // Rich Radial Gold Surface Gradient
      const grad = ctx.createRadialGradient(center - 100, center - 100, 60, center, center, radius)
      grad.addColorStop(0, "#fae48c")
      grad.addColorStop(0.3, "#e5b93d")
      grad.addColorStop(0.65, "#cb9622")
      grad.addColorStop(1, "#8e6513")
      ctx.fillStyle = grad
      ctx.beginPath()
      ctx.arc(center, center, radius, 0, Math.PI * 2)
      ctx.fill()

      // Brushed Concentric Rings
      ctx.strokeStyle = "rgba(255, 245, 205, 0.14)"
      ctx.lineWidth = 2
      for (let r = 90; r < radius - 40; r += 14) {
        ctx.beginPath()
        ctx.arc(center, center, r, 0, Math.PI * 2)
        ctx.stroke()
      }

      // Outer Beveled Edge Rings
      ctx.strokeStyle = "#ffe99b"
      ctx.lineWidth = 16
      ctx.beginPath()
      ctx.arc(center, center, radius - 22, 0, Math.PI * 2)
      ctx.stroke()

      ctx.strokeStyle = "rgba(90, 60, 8, 0.5)"
      ctx.lineWidth = 8
      ctx.beginPath()
      ctx.arc(center, center, radius - 36, 0, Math.PI * 2)
      ctx.stroke()

      // Beaded Perimeter Border
      const dots = 64
      for (let i = 0; i < dots; i++) {
        const angle = (i / dots) * Math.PI * 2
        const dx = center + Math.cos(angle) * (radius - 54)
        const dy = center + Math.sin(angle) * (radius - 54)
        ctx.fillStyle = "rgba(255, 245, 190, 0.9)"
        ctx.beginPath()
        ctx.arc(dx, dy, 4.5, 0, Math.PI * 2)
        ctx.fill()
        ctx.fillStyle = "rgba(70, 45, 5, 0.55)"
        ctx.beginPath()
        ctx.arc(dx + 1.5, dy + 1.5, 3.5, 0, Math.PI * 2)
        ctx.fill()
      }

      // 3D Embossed Currency Symbol
      ctx.font = '900 460px "Space Grotesk", "Archivo Black", "Arial Black", sans-serif'
      ctx.textAlign = "center"
      ctx.textBaseline = "middle"

      // Drop shadow depth
      ctx.fillStyle = "rgba(60, 38, 4, 0.85)"
      ctx.fillText(symbol, center + 7, center + 20)

      // Inner shadow bevel
      ctx.fillStyle = "#80550f"
      ctx.fillText(symbol, center + 3.5, center + 12)

      // Main gold face
      ctx.fillStyle = "#f5d470"
      ctx.fillText(symbol, center, center + 8)

      // Specular highlight
      ctx.fillStyle = "rgba(255, 255, 235, 0.9)"
      ctx.fillText(symbol, center - 3.5, center + 3)

      const tex = new THREE.CanvasTexture(c)
      tex.needsUpdate = true
      return tex
    }

    function createReededEdgeTexture() {
      const c = document.createElement("canvas")
      c.width = 512
      c.height = 64
      const ctx = c.getContext("2d")
      if (!ctx) return null

      for (let x = 0; x < 512; x += 8) {
        ctx.fillStyle = "#8a6112"
        ctx.fillRect(x, 0, 4, 64)
        ctx.fillStyle = "#fae28e"
        ctx.fillRect(x + 4, 0, 4, 64)
      }

      const tex = new THREE.CanvasTexture(c)
      tex.wrapS = THREE.RepeatWrapping
      tex.wrapT = THREE.ClampToEdgeWrapping
      tex.repeat.set(24, 1)
      tex.needsUpdate = true
      return tex
    }

    const frontTexture = createCoinFaceTexture("$")
    const backTexture = createCoinFaceTexture("$")
    const sideTexture = createReededEdgeTexture()

    // 5. Create 3D Cylinder with Real Depth
    // Parameters: radiusTop, radiusBottom, height/thickness, radialSegments
    const coinGeometry = new THREE.CylinderGeometry(2.35, 2.35, 0.38, 128, 1, false)

    const sideMaterial = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      metalness: 0.88,
      roughness: 0.28,
      map: sideTexture || undefined,
      bumpMap: sideTexture || undefined,
      bumpScale: 0.035,
    })

    const topMaterial = new THREE.MeshStandardMaterial({
      map: frontTexture,
      bumpMap: frontTexture,
      bumpScale: 0.06,
      metalness: 0.84,
      roughness: 0.22,
    })

    const bottomMaterial = new THREE.MeshStandardMaterial({
      map: backTexture,
      bumpMap: backTexture,
      bumpScale: 0.06,
      metalness: 0.84,
      roughness: 0.22,
    })

    const coinMesh = new THREE.Mesh(coinGeometry, [sideMaterial, topMaterial, bottomMaterial])
    // Orient cylinder upright so the face stands perpendicular to camera
    coinMesh.rotation.x = Math.PI / 2

    // Parent group for fixed vertical axis rotation and floating
    const coinGroup = new THREE.Group()
    coinGroup.add(coinMesh)
    scene.add(coinGroup)

    // 6. Scroll Rotation Dynamics & Easing
    let currentAngle = 0
    let targetAngle = 0
    let lastScrollY = window.scrollY

    const onScroll = () => {
      const scrollY = window.scrollY
      const delta = scrollY - lastScrollY
      lastScrollY = scrollY
      // Rotate coin on vertical axis on scroll
      targetAngle += delta * 0.014
    }
    window.addEventListener("scroll", onScroll, { passive: true })

    const onResize = () => {
      if (!container || !renderer) return
      width = container.clientWidth || 500
      height = container.clientHeight || 500
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      renderer.setSize(width, height)
    }
    window.addEventListener("resize", onResize)

    // 7. Animation Loop
    const startTime = performance.now()
    const animate = (now: number) => {
      const elapsed = now - startTime

      if (!prefersReducedMotion) {
        // Smooth momentum easing towards target scroll angle
        currentAngle += (targetAngle - currentAngle) * 0.08
        targetAngle += 0.0035 // Constant subtle idle spin

        // Fixed-axis Y rotation
        coinGroup.rotation.y = currentAngle

        // Natural micro wobble for metallic glint reflections
        const wobble = Math.sin(currentAngle * 2) * 0.08
        coinMesh.rotation.x = Math.PI / 2 + wobble

        // Smooth vertical hover floating
        const floatY = Math.sin(elapsed * 0.0016) * 0.12
        coinGroup.position.y = floatY
      }

      renderer.render(scene, camera)
      animationFrameId = requestAnimationFrame(animate)
    }

    animationFrameId = requestAnimationFrame(animate)

    // 8. Cleanup
    return () => {
      window.removeEventListener("scroll", onScroll)
      window.removeEventListener("resize", onResize)
      cancelAnimationFrame(animationFrameId)

      frontTexture.dispose()
      backTexture.dispose()
      if (sideTexture) sideTexture.dispose()

      coinGeometry.dispose()
      sideMaterial.dispose()
      topMaterial.dispose()
      bottomMaterial.dispose()
      renderer.dispose()
    }
  }, [prefersReducedMotion])

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full min-h-[380px] sm:min-h-[480px] lg:min-h-[540px] flex items-center justify-center pointer-events-none select-none"
    >
      <canvas
        ref={canvasRef}
        className="w-full h-full max-w-[540px] max-h-[540px] block"
        style={{ display: "block" }}
      />
    </div>
  )
}

export default ScrollCoinCanvas
