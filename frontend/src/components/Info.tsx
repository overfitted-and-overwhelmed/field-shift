import { Info as InfoIcon, X } from 'lucide-react';
import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

const WIDTH = 320;

/**
 * Info point: a small button that opens a short explanation next to it. Not a modal: the page stays usable, a click
 * outside, Escape or scrolling closes it. Rendered into <body> so no panel or table clips it.
 */
export function Info({ label, children }: { label: string; children: ReactNode }) {
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const btn = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const id = useId();

  const open = () => {
    const r = btn.current!.getBoundingClientRect();
    const left = Math.min(Math.max(12, r.left + r.width / 2 - WIDTH / 2), window.innerWidth - WIDTH - 12);
    const below = r.bottom + 8, fitsBelow = below + 180 < window.innerHeight;
    setPos({ top: fitsBelow ? below : Math.max(12, r.top - 8 - 180), left });
  };

  useEffect(() => {
    if (!pos) return;
    const close = () => setPos(null);
    const onDown = (e: PointerEvent) => { if (!panel.current?.contains(e.target as Node) && !btn.current?.contains(e.target as Node)) close(); };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') { close(); btn.current?.focus(); } };
    document.addEventListener('pointerdown', onDown);
    document.addEventListener('keydown', onKey);
    window.addEventListener('scroll', close, true);
    window.addEventListener('resize', close);
    return () => {
      document.removeEventListener('pointerdown', onDown); document.removeEventListener('keydown', onKey);
      window.removeEventListener('scroll', close, true); window.removeEventListener('resize', close);
    };
  }, [pos]);

  return (
    <>
      <button ref={btn} type="button" className="info-btn" aria-label={`About: ${label}`} aria-expanded={!!pos} aria-controls={pos ? id : undefined}
        onClick={() => (pos ? setPos(null) : open())}>
        <InfoIcon size={16} strokeWidth={2} aria-hidden="true" />
      </button>
      {pos && createPortal(
        <div ref={panel} id={id} role="dialog" aria-label={label} className="info-pop" style={{ top: pos.top, left: pos.left, width: WIDTH }}>
          <div className="info-head"><b>{label}</b>
            <button type="button" className="icon-btn" aria-label="Close" onClick={() => setPos(null)}><X size={16} aria-hidden="true" /></button>
          </div>
          <div className="info-body">{children}</div>
        </div>,
        document.body,
      )}
    </>
  );
}
