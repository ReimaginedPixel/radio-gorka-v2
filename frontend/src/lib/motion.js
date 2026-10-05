export function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

export function canHover() {
  return typeof window !== 'undefined' && window.matchMedia?.('(hover: hover)').matches
}

/**
 * Leci kopią okładki z jednego miejsca na ekranie w drugie po łuku.
 * Dzięki temu widać, że wybrana okładka "staje się" miniaturką w kolejce.
 */
export function flyImage({ src, from, to, rotate = 0, fromRadius = 20, toRadius = 14, duration = 680 }) {
  if (!src || !from || !to || prefersReducedMotion()) return Promise.resolve()
  const el = document.createElement('img')
  el.src = src
  el.alt = ''
  Object.assign(el.style, {
    position: 'fixed',
    left: `${from.left}px`,
    top: `${from.top}px`,
    width: `${from.width}px`,
    height: `${from.height}px`,
    objectFit: 'cover',
    borderRadius: `${fromRadius}px`,
    zIndex: '600',
    pointerEvents: 'none',
    margin: '0',
    transformOrigin: '50% 50%',
    boxShadow: '0 22px 44px -16px rgba(0,0,0,.75)',
    willChange: 'transform',
  })
  document.body.appendChild(el)

  const dx = to.left + to.width / 2 - (from.left + from.width / 2)
  const dy = to.top + to.height / 2 - (from.top + from.height / 2)
  const sx = to.width / from.width
  const sy = to.height / from.height
  const lift = Math.min(140, Math.abs(dy) * 0.3 + 50)
  const mid = 1 + (Math.max(sx, sy) - 1) * 0.35

  const anim = el.animate(
    [
      { transform: `translate(0px, 0px) rotate(${rotate}deg) scale(1)`, borderRadius: `${fromRadius}px` },
      {
        transform: `translate(${dx * 0.4}px, ${dy * 0.4 - lift}px) rotate(${rotate * 0.4}deg) scale(${mid * 1.06})`,
        offset: 0.42,
      },
      { transform: `translate(${dx}px, ${dy}px) rotate(0deg) scale(${sx}, ${sy})`, borderRadius: `${toRadius / sx}px` },
    ],
    { duration, easing: 'cubic-bezier(.5,.05,.2,1)', fill: 'forwards' },
  )
  const cleanup = () => el.remove()
  return anim.finished.then(cleanup, cleanup)
}

export function rectOf(el) {
  if (!el) return null
  const r = el.getBoundingClientRect()
  return { left: r.left, top: r.top, width: r.width, height: r.height }
}

export function inViewport(rect, margin = 0) {
  return rect && rect.bottom !== 0 && rect.top + rect.height > -margin && rect.top < window.innerHeight + margin
}
