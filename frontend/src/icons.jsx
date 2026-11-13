// Inline SVG icons, stroke-based so they follow `currentColor`

const base = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

export function LogoIcon({ size = 18 }) {
  // faceted obsidian shard
  return (
    <svg {...base} width={size} height={size} strokeWidth={1.6}>
      <path d="M12 2.5 19.5 8 17 20.5H7L4.5 8Z" />
      <path d="M12 2.5 9.5 11 7 20.5M12 2.5l2.5 8.5 2.5 9.5M4.5 8l5 3h5l5-3" />
    </svg>
  );
}

export function ArrowUpIcon() {
  return (
    <svg {...base}>
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  );
}

export function StopIcon() {
  return (
    <svg {...base} fill="currentColor" stroke="none">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );
}

export function PlusIcon() {
  return (
    <svg {...base}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function CopyIcon() {
  return (
    <svg {...base} width={15} height={15}>
      <rect x="9" y="9" width="12" height="12" rx="2" />
      <path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1" />
    </svg>
  );
}

export function CheckIcon() {
  return (
    <svg {...base} width={15} height={15}>
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

export function RetryIcon() {
  return (
    <svg {...base} width={15} height={15}>
      <path d="M3 12a9 9 0 0 1 15.5-6.2L21 8M21 3v5h-5M21 12a9 9 0 0 1-15.5 6.2L3 16M3 21v-5h5" />
    </svg>
  );
}

export function TrashIcon() {
  return (
    <svg {...base} width={15} height={15}>
      <path d="M4 7h16M10 11v6M14 11v6M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2l1-12M9 7V4h6v3" />
    </svg>
  );
}

export function MenuIcon() {
  return (
    <svg {...base}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  );
}

export function NoteIcon() {
  return (
    <svg {...base} width={13} height={13}>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" />
      <path d="M14 3v5h5" />
    </svg>
  );
}

export function ArrowDownIcon() {
  return (
    <svg {...base}>
      <path d="M12 5v14M19 12l-7 7-7-7" />
    </svg>
  );
}
