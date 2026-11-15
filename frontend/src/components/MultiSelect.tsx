import { useEffect, useId, useRef, useState } from 'react';

interface Props {
  label: string;
  options: { id: string; label: string; color?: string }[];
  value: string[];
  onChange: (ids: string[]) => void;
  placeholder?: string;
}

/** Dropdown with checkboxes. Selected items show as removable chips below the button. */
export function MultiSelect({ label, options, value, onChange, placeholder = 'Choose…' }: Props) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const listId = useId();
  const labelId = useId();

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => { if (!root.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('pointerdown', onDown);
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('pointerdown', onDown); document.removeEventListener('keydown', onKey); };
  }, [open]);

  const toggle = (id: string) => onChange(value.includes(id) ? value.filter((v) => v !== id) : options.filter((o) => o.id === id || value.includes(o.id)).map((o) => o.id));
  const selected = options.filter((o) => value.includes(o.id));
  const summary = selected.length ? `${selected.length} selected` : placeholder;

  return (
    <div className="ms" ref={root}>
      <span className="field-label" id={labelId}>{label}</span>
      <button type="button" className="ms-btn" aria-haspopup="listbox" aria-expanded={open} aria-controls={listId} aria-labelledby={labelId} onClick={() => setOpen((o) => !o)}>
        <span className={selected.length ? '' : 'ms-ph'}>{summary}</span>
        <span aria-hidden="true" className="ms-caret">▾</span>
      </button>
      {open && (
        <div className="ms-list" id={listId} role="group" aria-labelledby={labelId}>
          {options.map((o) => (
            <label key={o.id} className="ms-opt">
              <input type="checkbox" checked={value.includes(o.id)} onChange={() => toggle(o.id)} />
              {o.color && <i style={{ background: o.color }} aria-hidden="true" />}
              {o.label}
            </label>
          ))}
          <div className="ms-actions">
            <button type="button" onClick={() => onChange(options.map((o) => o.id))}>All</button>
            <button type="button" onClick={() => onChange([])}>None</button>
          </div>
        </div>
      )}
      {selected.length > 0 && (
        <ul className="chips">
          {selected.map((o) => (
            <li key={o.id}>
              {o.color && <i style={{ background: o.color }} aria-hidden="true" />}
              {o.label}
              <button type="button" aria-label={`Remove ${o.label}`} onClick={() => toggle(o.id)}>×</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
