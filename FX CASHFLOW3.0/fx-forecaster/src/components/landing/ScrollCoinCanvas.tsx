import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";

export function ScrollCoinCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mediaQuery.matches);
    const listener = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener("change", listener);
    return () => mediaQuery.removeEventListener("change", listener);
  }, []);

  useEffect(() => {
    if (prefersReducedMotion) return;

    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    let width = container.clientWidth || 300;
    let height = container.clientHeight || 300;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(width, height);
    } catch (e) {
      console.warn("WebGL not supported or disabled:", e);
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, width / height, 0.1, 100);
    camera.position.set(0, 0, 9);

    // lights
    const key = new THREE.DirectionalLight(0xfff1cf, 1.5);
    key.position.set(3, 4, 5);
    scene.add(key);

    const rim = new THREE.DirectionalLight(0xffd98a, 0.7);
    rim.position.set(-4, -2, -3);
    scene.add(rim);

    const amb = new THREE.AmbientLight(0xfff6e6, 0.65);
    scene.add(amb);

    const coinGroup = new THREE.Group();

    function makeFaceTexture(symbol: string) {
      const size = 512;
      const c = document.createElement("canvas");
      c.width = size;
      c.height = size;
      const ctx = c.getContext("2d");
      if (!ctx) return new THREE.Texture();

      ctx.fillStyle = "#cba135";
      ctx.beginPath();
      ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = "rgba(255,240,190,0.4)";
      ctx.lineWidth = 10;
      ctx.beginPath();
      ctx.arc(size / 2, size / 2, size / 2 - 28, 0, Math.PI * 2);
      ctx.stroke();

      ctx.fillStyle = "rgba(90,64,10,0.6)";
      ctx.font = '700 260px "Helvetica Neue", Arial, sans-serif';
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(symbol, size / 2, size / 2 + 18);

      const tex = new THREE.CanvasTexture(c);
      tex.needsUpdate = true;
      return tex;
    }

    const dollarTex = makeFaceTexture("$");
    const rupeeTex = makeFaceTexture("\u20B9");

    const bodyGeo = new THREE.CylinderGeometry(2.6, 2.6, 0.42, 90);
    const sideMat = new THREE.MeshStandardMaterial({
      color: 0xc9a227,
      metalness: 0.55,
      roughness: 0.48,
    });
    const topMat = new THREE.MeshStandardMaterial({
      map: dollarTex,
      metalness: 0.5,
      roughness: 0.5,
    });
    const bottomMat = new THREE.MeshStandardMaterial({
      map: rupeeTex,
      metalness: 0.5,
      roughness: 0.5,
    });

    const body = new THREE.Mesh(bodyGeo, [sideMat, topMat, bottomMat]);
    coinGroup.add(body);

    const ringGeo = new THREE.TorusGeometry(2.35, 0.05, 16, 90);
    const ringMat = new THREE.MeshStandardMaterial({
      color: 0xe8c765,
      metalness: 0.55,
      roughness: 0.42,
    });
    const ringTop = new THREE.Mesh(ringGeo, ringMat);
    ringTop.rotation.x = Math.PI / 2;
    ringTop.position.y = 0.22;
    coinGroup.add(ringTop);

    const ringBottom = ringTop.clone();
    ringBottom.position.y = -0.22;
    coinGroup.add(ringBottom);

    const edgeCount = 70;
    const edgeGeo = new THREE.BoxGeometry(0.06, 0.42, 0.1);
    const edgeMat = new THREE.MeshStandardMaterial({
      color: 0xa67c1e,
      metalness: 0.5,
      roughness: 0.5,
    });
    for (let i = 0; i < edgeCount; i++) {
      const m = new THREE.Mesh(edgeGeo, edgeMat);
      const a = (i / edgeCount) * Math.PI * 2;
      m.position.set(Math.cos(a) * 2.6, 0, Math.sin(a) * 2.6);
      m.rotation.y = -a;
      coinGroup.add(m);
    }

    scene.add(coinGroup);

    coinGroup.position.set(0, -0.15, 0);
    coinGroup.rotation.set(0.35, 0.55, 1.05);
    coinGroup.scale.set(0.8, 0.8, 0.8);

    const baseRotation = { x: coinGroup.rotation.x, y: coinGroup.rotation.y, z: coinGroup.rotation.z };

    function resize() {
      if (!container || !renderer || !camera) return;
      width = container.clientWidth;
      height = container.clientHeight;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }
    window.addEventListener("resize", resize);

    let targetExtra = 0;
    let currentExtra = 0;

    function onScroll() {
      const scrollable = Math.max(document.body.scrollHeight - window.innerHeight, 1);
      const progress = Math.min(Math.max(window.scrollY / scrollable, 0), 1);
      targetExtra = progress * Math.PI * 2;
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    let animationFrameId: number;

    function animate() {
      animationFrameId = requestAnimationFrame(animate);
      currentExtra += (targetExtra - currentExtra) * 0.08;
      coinGroup.rotation.y = baseRotation.y + currentExtra;
      renderer.render(scene, camera);
    }
    animate();

    return () => {
      window.removeEventListener("resize", resize);
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(animationFrameId);

      // Clean up Three.js resources
      bodyGeo.dispose();
      sideMat.dispose();
      topMat.dispose();
      bottomMat.dispose();
      dollarTex.dispose();
      rupeeTex.dispose();
      ringGeo.dispose();
      ringMat.dispose();
      edgeGeo.dispose();
      edgeMat.dispose();
      renderer.dispose();
    };
  }, [prefersReducedMotion]);

  if (prefersReducedMotion) return null;

  return (
    <div ref={containerRef} className="absolute inset-0 z-1 pointer-events-none">
      <canvas ref={canvasRef} id="coin-canvas" className="w-full h-full" />
    </div>
  );
}
