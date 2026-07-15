/** Editorial cover: a real photo when the article has one, otherwise a
 * branded SVG graphic keyed to the category — zero copyright risk. */

type CoverImage = { url: string; alt: string; credit?: string };

const PALETTES: Record<string, { from: string; to: string; accent: string }> = {
  "আন্তর্জাতিক": { from: "#0f2a52", to: "#1d4e89", accent: "#7fb3ff" },
  "খেলাধুলা": { from: "#0b3d2e", to: "#14691f", accent: "#8be28b" },
  "প্রযুক্তি": { from: "#2d1b52", to: "#5b2d89", accent: "#c9a6ff" },
  "অর্থনীতি": { from: "#5c3a08", to: "#976810", accent: "#ffd479" },
  "রাজনীতি": { from: "#521b1b", to: "#8f2626", accent: "#ff9d9d" },
  "বাংলাদেশ": { from: "#0b4d3d", to: "#0f7a49", accent: "#ff6b6b" },
};

const DEFAULT_PALETTE = { from: "#1c1815", to: "#4a4038", accent: "#d8d1c5" };

function seedFrom(text: string): number {
  let h = 0;
  for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) % 997;
  return h;
}

export function Cover({
  slug,
  category,
  title,
  image,
  className = "",
}: {
  slug: string;
  category: string;
  title: string;
  image?: CoverImage | null;
  className?: string;
}) {
  const seed = seedFrom(slug);

  if (image?.url) {
    // Per-article variation so a page of covers doesn't move in lockstep.
    const duration = 14 + (seed % 8);
    const direction = seed % 2 === 0 ? "alternate" : "alternate-reverse";
    return (
      <figure className={className}>
        <div className="aspect-video w-full overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={image.url}
            alt={image.alt}
            className="kenburns h-full w-full object-cover"
            style={{ animationDuration: `${duration}s`, animationDirection: direction }}
            loading="lazy"
          />
        </div>
        {image.credit && (
          <figcaption className="mt-1 text-right text-[10px] text-ink-soft">
            ছবি: {image.credit}
          </figcaption>
        )}
      </figure>
    );
  }

  const palette = PALETTES[category] ?? DEFAULT_PALETTE;
  const angle = 15 + (seed % 30);          // subtle per-article variation
  const offset = 60 + (seed % 120);
  const gid = `g-${slug}`;

  return (
    <svg
      viewBox="0 0 800 450"
      className={`aspect-video w-full ${className}`}
      role="img"
      aria-label={title}
    >
      <defs>
        <linearGradient id={gid} gradientTransform={`rotate(${angle})`}>
          <stop offset="0%" stopColor={palette.from} />
          <stop offset="100%" stopColor={palette.to} />
        </linearGradient>
      </defs>
      <rect width="800" height="450" fill={`url(#${gid})`} />
      {/* halftone-style dots, a nod to print */}
      {Array.from({ length: 6 }).map((_, row) =>
        Array.from({ length: 10 }).map((_, col) => (
          <circle
            key={`${row}-${col}`}
            cx={40 + col * 80 + (row % 2) * 40}
            cy={40 + row * 75}
            r={2 + ((seed + row * col) % 3)}
            fill="#ffffff"
            opacity="0.08"
          />
        )),
      )}
      <rect x="0" y="0" width="800" height="6" fill={palette.accent} />
      <line x1="48" y1={180 + (offset % 40)} x2="220" y2={180 + (offset % 40)}
            stroke={palette.accent} strokeWidth="3" />
      <text
        x="48"
        y={250 + (offset % 40)}
        fontSize="64"
        fontWeight="700"
        fill="#ffffff"
        fontFamily="'Noto Sans Bengali', sans-serif"
      >
        {category}
      </text>
      <text
        x="48"
        y="410"
        fontSize="20"
        fill={palette.accent}
        fontFamily="'Noto Sans Bengali', sans-serif"
      >
        বিডি সাইট নিউজ
      </text>
    </svg>
  );
}
