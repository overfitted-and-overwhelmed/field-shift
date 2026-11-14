import { useEffect, useRef } from 'react';

/** Global tooltip: any element with a data-tip attribute shows its text (HTML and SVG). */
export function Tooltip() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const tip = ref.current!;
    const move = (e: PointerEvent) => {
      const el = (e.target as Element | null)?.closest?.('[data-tip]');
      if (!el) return tip.classList.remove('on');
      tip.textContent = el.getAttribute('data-tip');
      tip.classList.add('on');
      const r = tip.getBoundingClientRect();
      tip.style.left = `${Math.min(e.clientX + 14, innerWidth - r.width - 8)}px`;
      tip.style.top = `${Math.max(8, e.clientY - r.height - 12)}px`;
    };
    const hide = () => tip.classList.remove('on');
    document.addEventListener('pointermove', move);
    document.addEventListener('pointerleave', hide);
    return () => { document.removeEventListener('pointermove', move); document.removeEventListener('pointerleave', hide); };
  }, []);
  return <div id="tip" role="tooltip" ref={ref} />;
}
