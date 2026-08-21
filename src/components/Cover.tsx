/** Editorial cover: a real photo when the article has one, otherwise a
 * designed headline card — category-coloured, with the headline set on it,
 * so a story without photography still looks intentional in a feed. */

type CoverImage = {
  url: string;
  alt: string;
  credit?: string;
  caption?: string;
  illustrative?: boolean;
};

const PALETTES: Record<string, { from: string; to: string; accent: string }> = {
  আন্তর্জাতিক: { from: "#0f2a52", to: "#1d4e89", accent: "#7fb3ff" },
  বিশ্ব: { from: "#0f2a52", to: "#1d4e89", accent: "#7fb3ff" },
  খেলা: { from: "#0b3d2e", to: "#14691f", accent: "#8be28b" },
  খেলাধুলা: { from: "#0b3d2e", to: "#14691f", accent: "#8be28b" },
  প্রযুক্তি: { from: "#2d1b52", to: "#5b2d89", accent: "#c9a6ff" },
  অর্থনীতি: { from: "#5c3a08", to: "#976810", accent: "#ffd479" },
  রাজনীতি: { from: "#521b1b", to: "#8f2626", accent: "#ff9d9d" },
  বাংলাদেশ: { from: "#0b4d3d", to: "#0f7a49", accent: "#ffd479" },
  অপরাধ: { from: "#3a1414", to: "#6d1f1f", accent: "#ff9d9d" },
  বিনোদন: { from: "#4a1340", to: "#8a2472", accent: "#ffb3ec" },
  শিক্ষা: { from: "#123a52", to: "#1b6585", accent: "#9fd8f2" },
  প্রবাস: { from: "#1e3357", to: "#39558c", accent: "#a8bde8" },
  জেলা: { from: "#2f3d1a", to: "#55702c", accent: "#cbe89a" },
  "ফ্যাক্ট চেক": { from: "#4a2a06", to: "#8a4c0a", accent: "#ffc880" },
  ব্যাখ্যা: { from: "#1c2b3a", to: "#33506b", accent: "#a9cbe8" },
};

const DEFAULT_PALETTE = { from: "#1c1815", to: "#4a4038", accent: "#d8d1c5" };

function seedFrom(text: string): number {
  let h = 0;
  for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) % 997;
  return h;
}

/** Wrap a Bangla headline into SVG lines — SVG has no automatic wrapping. */
function wrapHeadline(title: string, perLine = 24, maxLines = 4): string[] {
  const words = title.split(/\s+/);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length > perLine && current) {
      lines.push(current);
      current = word;
      if (lines.length === maxLines - 1) break;
    } else {
      current = candidate;
    }
  }
  if (current && lines.length < maxLines) lines.push(current);
  const used = lines.join(" ");
  if (used.length < title.length && lines.length) {
    lines[lines.length - 1] = lines[lines.length - 1].replace(/[।,;:]?$/, "…");
  }
  return lines;
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
        {(image.caption || image.credit || image.illustrative) && (
          <figcaption className="mt-1.5 text-[11px] leading-relaxed text-ink-soft">
            {/* The caption says what the picture shows; the line under it says
                where it came from and whether it is a stand-in. Two different
                claims, so they are never merged into one string. */}
            {image.caption && (
              <p
                className="font-[family-name:var(--font-bengali)] text-ink"
                lang="bn"
              >
                {image.caption}
              </p>
            )}
            <span className="mt-1 flex flex-wrap items-center justify-between gap-2 text-[10px]">
              {image.illustrative && (
                <span className="bg-ink/85 px-1.5 py-0.5 font-[family-name:var(--font-bengali)] font-semibold text-paper">
                  প্রতীকী ছবি
                </span>
              )}
              {image.credit && <span className="ml-auto">ছবি: {image.credit}</span>}
            </span>
          </figcaption>
        )}
      </figure>
    );
  }

  const palette = PALETTES[category] ?? DEFAULT_PALETTE;
  const angle = 15 + (seed % 30);
  const gid = `g-${slug}`;
  const lines = wrapHeadline(title);
  // Bottom-anchor the headline block so 1-line and 4-line cards both sit well.
  const lineHeight = 54;
  const firstBaseline = 384 - (lines.length - 1) * lineHeight;

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

      {/* halftone texture — a nod to newsprint */}
      {Array.from({ length: 5 }).map((_, row) =>
        Array.from({ length: 10 }).map((_, col) => (
          <circle
            key={`${row}-${col}`}
            cx={40 + col * 80 + (row % 2) * 40}
            cy={30 + row * 46}
            r={2 + ((seed + row * col) % 3)}
            fill="#ffffff"
            opacity="0.07"
          />
        )),
      )}

      <rect x="0" y="0" width="800" height="7" fill={palette.accent} />

      {/* category kicker */}
      <text
        x="48"
        y="72"
        fontSize="24"
        fontWeight="700"
        fill={palette.accent}
        style={{ fontFamily: "var(--font-bengali), sans-serif" }}
      >
        {category}
      </text>

      {/* the headline itself */}
      {lines.map((line, i) => (
        <text
          key={i}
          x="48"
          y={firstBaseline + i * lineHeight}
          fontSize="42"
          fontWeight="700"
          fill="#ffffff"
          style={{ fontFamily: "var(--font-bengali), sans-serif" }}
        >
          {line}
        </text>
      ))}

      <text
        x="752"
        y="72"
        textAnchor="end"
        fontSize="19"
        fill="#ffffff"
        opacity="0.75"
        style={{ fontFamily: "var(--font-bengali), sans-serif" }}
      >
        বিডি সাইট নিউজ
      </text>
    </svg>
  );
}
