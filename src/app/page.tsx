import Link from "next/link";
import { AdSlot } from "@/components/AdSlot";
import { ArticleCard, ArticleRow } from "@/components/ArticleCard";
import { Cover } from "@/components/Cover";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { StoryGrid, type Story } from "@/components/StoryGrid";
import stories from "@/data/stories.json";
import {
  activeCategories,
  allArticles,
  byCategory,
  categorySlug,
  formatBnDate,
} from "@/lib/articles";

const wire = stories as Story[];

export default function Home() {
  const articles = allArticles();
  const [hero, ...rest] = articles;
  const latestRail = rest.slice(0, 6);
  const gridTop = rest.slice(6, 12);
  const cats = activeCategories().slice(0, 3);

  return (
    <main className="mx-auto max-w-6xl px-4 pb-12">
      <SiteHeader />

      {/* Breaking strip */}
      <div className="-mx-4 mt-3 bg-ink px-4 py-2 text-paper">
        <p className="mx-auto flex max-w-6xl items-center gap-3 font-[family-name:var(--font-bengali)] text-sm">
          <span className="shrink-0 bg-crimson px-2 py-0.5 text-xs font-bold">
            সর্বশেষ
          </span>
          <Link href={`/news/${hero.slug}`} className="truncate hover:underline">
            {hero.title}
          </Link>
        </p>
      </div>

      {/* Lead story + latest rail */}
      <section className="grid gap-8 border-b border-rule py-8 lg:grid-cols-[1.9fr_1fr]">
        <Link
          href={`/news/${hero.slug}`}
          className="group block font-[family-name:var(--font-bengali)]"
        >
          <Cover
            slug={hero.slug}
            category={hero.category}
            title={hero.title}
            image={hero.image}
          />
          <p className="mt-4 text-xs font-bold tracking-[0.25em] text-crimson">
            {hero.category}
          </p>
          <h2
            lang="bn"
            className="mt-2 text-3xl font-bold leading-tight group-hover:underline sm:text-4xl"
          >
            {hero.title}
          </h2>
          <p className="mt-3 text-base leading-relaxed text-ink-soft">
            {hero.lead}
          </p>
          <p className="mt-3 text-xs text-ink-soft">
            বিডি সাইট নিউজ ডেস্ক · {formatBnDate(hero.publishedAt)}
          </p>
        </Link>

        <aside className="font-[family-name:var(--font-bengali)]">
          <h2 className="border-b-2 border-ink pb-2 text-sm font-bold tracking-widest">
            সর্বশেষ খবর
          </h2>
          <div className="mt-1">
            {latestRail.map((a, i) => (
              <ArticleRow key={a.slug} article={a} index={i} />
            ))}
          </div>
        </aside>
      </section>

      <AdSlot placement="leaderboard" />

      {/* Main grid */}
      {gridTop.length > 0 && (
        <section className="grid gap-x-7 gap-y-9 border-b border-rule py-9 sm:grid-cols-2 lg:grid-cols-3">
          {gridTop.map((a) => (
            <ArticleCard key={a.slug} article={a} />
          ))}
        </section>
      )}

      <AdSlot placement="in-feed" />

      {/* Category sections — more internal links, more indexable depth */}
      {cats.map((c) => {
        const items = byCategory(c.bn).slice(0, 3);
        if (items.length === 0) return null;
        return (
          <section key={c.slug} className="border-b border-rule py-9">
            <div className="flex items-baseline justify-between font-[family-name:var(--font-bengali)]">
              <h2 className="border-b-2 border-crimson pb-1 text-xl font-bold">
                {c.bn}
              </h2>
              <Link
                href={`/category/${c.slug}`}
                className="text-sm font-semibold text-crimson hover:underline"
              >
                সব দেখুন →
              </Link>
            </div>
            <div className="mt-6 grid gap-x-7 gap-y-9 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((a) => (
                <ArticleCard key={a.slug} article={a} />
              ))}
            </div>
          </section>
        );
      })}

      {/* External headline wire */}
      <section className="pt-9">
        <h2 className="border-b-2 border-ink pb-2 font-[family-name:var(--font-serif-news)] text-xl font-semibold">
          World Wire
          <span className="ml-2 font-[family-name:var(--font-bengali)] text-sm font-normal text-ink-soft">
            · আন্তর্জাতিক শিরোনাম
          </span>
        </h2>
        <StoryGrid stories={wire} />
      </section>

      <SiteFooter />
    </main>
  );
}
