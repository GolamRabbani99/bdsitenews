"use client";

import { useMemo, useState } from "react";

export type Story = {
  title: string;
  url: string;
  summary: string;
  category: string;
  source: string;
  publishedAt: string;
};

function timeLabel(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Dhaka",
  });
}

export function StoryGrid({
  stories,
  defaultCategory = "All",
}: {
  stories: Story[];
  defaultCategory?: string;
}) {
  const categories = useMemo(
    () => ["All", ...Array.from(new Set(stories.map((s) => s.category))).sort()],
    [stories],
  );
  const [active, setActive] = useState(
    categories.includes(defaultCategory) ? defaultCategory : "All",
  );

  const visible =
    active === "All" ? stories : stories.filter((s) => s.category === active);

  return (
    <section>
      {/* Category chips */}
      <nav className="flex flex-wrap justify-center gap-2 border-b border-rule py-5">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActive(cat)}
            className={`px-4 py-1.5 text-xs font-bold uppercase tracking-widest transition-colors ${
              active === cat
                ? "bg-ink text-paper"
                : "text-ink-soft hover:text-crimson"
            }`}
          >
            {cat}
          </button>
        ))}
      </nav>

      {/* Grid */}
      <div className="grid gap-x-8 gap-y-10 pt-10 sm:grid-cols-2 lg:grid-cols-3">
        {visible.map((story) => (
          <a
            key={story.url}
            href={story.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex flex-col border-b border-rule pb-6"
          >
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-crimson">
              {story.category}
            </p>
            <h3 className="mt-2 font-[family-name:var(--font-serif-news)] text-xl font-medium leading-snug group-hover:underline">
              {story.title}
            </h3>
            {story.summary && (
              <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-ink-soft">
                {story.summary}
              </p>
            )}
            <p className="mt-auto pt-3 text-[11px] uppercase tracking-widest text-ink-soft">
              {story.source} · {timeLabel(story.publishedAt)}
            </p>
          </a>
        ))}
      </div>

      {visible.length === 0 && (
        <p className="py-16 text-center text-ink-soft">
          No stories in this section right now.
        </p>
      )}
    </section>
  );
}
