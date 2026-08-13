import Link from "next/link";
import { site } from "@/lib/site";
import { activeCategories } from "@/lib/articles";

/** Sticky masthead + category bar. Navigation is revenue: every extra
 * click a reader can make is another page of ad inventory. */
export function SiteHeader({ compact = false }: { compact?: boolean }) {
  const cats = activeCategories();

  return (
    <header className="sticky top-0 z-30 -mx-4 border-b border-rule bg-paper/95 px-4 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-baseline justify-between gap-3 py-3">
        <Link href="/" className="shrink-0" aria-label={site.name}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo.png"
            alt={`${site.name} — ${site.taglineBn}`}
            width={587}
            height={200}
            // The logo carries its own tagline, so it needs real size to stay
            // legible — full masthead on the front page, trimmer elsewhere.
            className={
              compact ? "h-10 w-auto sm:h-12" : "h-12 w-auto sm:h-16"
            }
            fetchPriority="high"
          />
        </Link>
        {!compact && (
          <span className="hidden font-[family-name:var(--font-bengali)] text-xs text-ink-soft sm:block">
            {new Date().toLocaleDateString("bn-BD", {
              weekday: "long",
              day: "numeric",
              month: "long",
              timeZone: "Asia/Dhaka",
            })}
          </span>
        )}
      </div>

      <nav className="mx-auto flex max-w-6xl gap-1 overflow-x-auto pb-2 font-[family-name:var(--font-bengali)] text-sm">
        <Link
          href="/"
          className="whitespace-nowrap px-3 py-1 font-semibold hover:text-crimson"
        >
          সর্বশেষ
        </Link>
        {cats.map((c) => (
          <Link
            key={c.slug}
            href={`/category/${c.slug}`}
            className="whitespace-nowrap px-3 py-1 font-semibold text-ink-soft hover:text-crimson"
          >
            {c.bn}
          </Link>
        ))}
      </nav>
    </header>
  );
}
