export const StartMateLogo = ({ size = 36 }) => (
  <svg
    aria-hidden="true"
    height={size}
    viewBox="0 0 64 64"
    width={size}
  >
    <defs>
      <linearGradient id="startmateLogoBg" x1="8" x2="56" y1="6" y2="58" gradientUnits="userSpaceOnUse">
        <stop stopColor="#f7f9ff" />
        <stop offset="1" stopColor="#dfe5ff" />
      </linearGradient>
      <linearGradient id="startmateLogoBlue" x1="18" x2="50" y1="8" y2="48" gradientUnits="userSpaceOnUse">
        <stop stopColor="#1f5fff" />
        <stop offset="1" stopColor="#5d8cff" />
      </linearGradient>
      <linearGradient id="startmateLogoLeaf" x1="17" x2="53" y1="36" y2="59" gradientUnits="userSpaceOnUse">
        <stop stopColor="#c7e96d" />
        <stop offset="1" stopColor="#7fbe43" />
      </linearGradient>
    </defs>
    <rect width="64" height="64" rx="17" fill="url(#startmateLogoBg)" />
    <path d="M17 39c-6-17 5-34 22-33 9 .5 17 5 22 12l-8 5c-4-5-9-8-16-8-11-.5-19 11-15 22l-5 2Z" fill="url(#startmateLogoBlue)" />
    <path d="M41 10 59 1l-1 19-5-5c-8 17-18 21-20 43-3-21 9-34 17-46l-9-2Z" fill="url(#startmateLogoBlue)" />
    <circle cx="31" cy="22" r="6" fill="#fff" />
    <path d="M31 29c-8 4-13 8-14 16 5-5 12-1 14 13 1-16 5-23 13-29-5 2-9 3-13 0Z" fill="#fff" />
    <path d="M31 58c4-15 12-21 22-24 5-2 8-8 8-15-5 10-16 9-23 17-4 5-6 12-7 22Z" fill="url(#startmateLogoLeaf)" />
    <path d="M31 58c-4-12-10-17-19-19 3 8 9 10 14 11 3 1 4 4 5 8Z" fill="url(#startmateLogoLeaf)" />
  </svg>
)
