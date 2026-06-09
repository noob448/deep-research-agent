import { useEffect, useState, Suspense, lazy } from 'react'

// tsparticles has complex ESM types — lazy-load to avoid build-time issues
const Particles = lazy(() => import('@tsparticles/react').then(m => ({ default: m.default || (m as any).Particles })))

export default function ParticleBg() {
  const [mounted, setMounted] = useState(false)
  useEffect(() => { setMounted(true) }, [])

  if (!mounted) return null

  return (
    <Suspense fallback={null}>
      <Particles
        style={{ position: 'fixed', top: 0, left: 0, zIndex: 0 } as any}
        options={{
          fpsLimit: 60,
          particles: {
            number: { value: 40, density: { enable: true } },
            color: { value: ['#00d4ff', '#7b2fff', '#64748b'] },
            opacity: { value: 0.15 },
            size: { value: { min: 1, max: 3 } },
            move: { enable: true, speed: 0.6 },
            links: { enable: true, color: '#334155', opacity: 0.1, distance: 150 },
          },
          interactivity: {
            events: { onHover: { enable: true, mode: 'grab' } },
            modes: { grab: { distance: 180, links: { opacity: 0.3 } } },
          },
        }}
      />
    </Suspense>
  )
}
