export const Icon = ({ name, size = 20, stroke = 1.8 }) => {
  const paths = {
    discuss: <><path d="M21 11.5a8.5 8.5 0 0 1-12.2 7.7L3 21l1.8-5.3A8.5 8.5 0 1 1 21 11.5Z" /><path d="M8.5 11h.01M12 11h.01M15.5 11h.01" /></>,
    home: <><path d="M3 10.2 12 3l9 7.2" /><path d="M5 9.5V21h14V9.5" /><path d="M9.5 21v-6h5v6" /></>,
    user: <><circle cx="12" cy="8" r="3.4" /><path d="M5 20a7 7 0 0 1 14 0" /></>,
    bulb: <><path d="M9 18h6M10 21h4" /><path d="M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.2 1.1 2h5c.1-.8.5-1.5 1.1-2A6 6 0 0 0 12 3Z" /></>,
    chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
    doc: <><path d="M7 3h7l4 4v14H7z" /><path d="M14 3v4h4M10 13h6M10 17h6" /></>,
    edit: <><path d="M5 19h14" /><path d="M14.5 5.5 18 9 8 19l-4 1 1-4z" /></>,
    pulse: <path d="M3 12h4l2-6 4 12 2-6h6" />,
    megaphone: <><path d="M4 10v4a1 1 0 0 0 1 1h2l8 4V5L7 9H5a1 1 0 0 0-1 1Z" /><path d="M18 8a4 4 0 0 1 0 8" /></>,
    bookmark: <path d="M6 3h12v18l-6-4-6 4z" />,
    plus: <path d="M12 5v14M5 12h14" />,
    arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
    send: <path d="M4 12 20 4l-7 16-2.5-6.5L4 12Z" />,
    check: <path d="M5 12.5 10 17l9-10" />,
    sparkle: <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" />,
    target: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /><circle cx="12" cy="12" r="1" /></>,
    pin: <><path d="M12 21s7-6.3 7-11a7 7 0 0 0-14 0c0 4.7 7 11 7 11Z" /><circle cx="12" cy="10" r="2.5" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    refresh: <><path d="M3 12a9 9 0 0 1 15-6.7L21 8" /><path d="M21 3v5h-5" /><path d="M21 12a9 9 0 0 1-15 6.7L3 16" /><path d="M3 21v-5h5" /></>,
    chevron: <path d="M9 6l6 6-6 6" />,
    play: <path d="M7 4v16l13-8z" />,
    more: <><circle cx="5" cy="12" r="1.2" /><circle cx="12" cy="12" r="1.2" /><circle cx="19" cy="12" r="1.2" /></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>
}
