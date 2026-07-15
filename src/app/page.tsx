import Link from "next/link";
import { site } from "@/lib/site";
import stories from "@/data/stories.json";
import articles from "@/data/articles.json";
import { StoryGrid, type Story } from "@/components/StoryGrid";

const wire = stories as Story[];

function todayLine(): string {
  return new Date().toLocaleDateString("bn-BD", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Asia/Dhaka",
  });
}

export default function Home() {
  const [hero, ...rest] = articles;

  return (
    <main className="mx-auto max-w-6xl px-4 pb-16">
      {/* Breaking strip */}
      <div className="-mx-4 bg-ink px-4 py-2 text-paper">
        <p className="mx-auto max-w-6xl truncate font-[family-name:var(--font-bengali)] text-sm">
          <span className="mr-3 bg-crimson px-2 py-0.5 text-xs font-bold uppercase tracking-widest">
            সর্বশেষ
          </span>
          {hero.title}
        </p>
      </div>

      {/* Masthead */}
      <header className="py-8 text-center">
        <p className="font-[family-name:var(--font-bengali)] text-xs tracking-widest text-ink-soft">
          {todayLine()} · ঢাকা
        </p>
        <h1 className="mt-3 font-[family-name:var(--font-serif-news)] text-5xl font-semibold tracking-tight sm:text-6xl">
          {site.name}
        </h1>
        <p className="mt-1 font-[family-name:var(--font-bengali)] text-2xl font-semibold text-crimson sm:text-3xl">
          {site.nameBn}
        </p>
        <p className="mt-3 font-[family-name:var(--font-bengali)] text-base text-ink-soft">
          {site.taglineBn}
        </p>
      </header>

      <div className="rule-double" />

      {/* Hero article (Bangla) */}
      <Link
        href={`/news/${hero.slug}`}
        className="group block border-b border-rule py-10 text-center font-[family-name:var(--font-bengali)]"
      >
        <p className="text-xs font-bold tracking-[0.25em] text-crimson">
          {hero.category}
        </p>
        <h2 lang="bn" className="mx-auto mt-4 max-w-4xl text-3xl font-semibold leading-snug group-hover:underline sm:text-4xl">
          {hero.title}
        </h2>
        <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-ink-soft">
          {hero.lead}
        </p>
        <p className="mt-5 text-xs tracking-widest text-ink-soft">
          বিডি সাইট নিউজ ডেস্ক
        </p>
      </Link>

      {/* Bangla article grid */}
      <section className="grid gap-x-8 gap-y-10 border-b border-rule py-10 font-[family-name:var(--font-bengali)] sm:grid-cols-2 lg:grid-cols-3">
        {rest.map((article) => (
          <Link
            key={article.slug}
            href={`/news/${article.slug}`}
            className="group flex flex-col"
          >
            <p className="text-[11px] font-bold tracking-[0.2em] text-crimson">
              {article.category}
            </p>
            <h3 lang="bn" className="mt-2 text-xl font-semibold leading-snug group-hover:underline">
              {article.title}
            </h3>
            <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-ink-soft">
              {article.lead}
            </p>
          </Link>
        ))}
      </section>

      {/* English wire headlines */}
      <section className="pt-10">
        <h2 className="text-center font-[family-name:var(--font-serif-news)] text-2xl font-medium">
          World Wire{" "}
          <span className="font-[family-name:var(--font-bengali)] text-lg text-ink-soft">
            · আন্তর্জাতিক শিরোনাম
          </span>
        </h2>
        <StoryGrid stories={wire} />
      </section>

      {/* Footer */}
      <footer className="mt-16 border-t border-rule pt-8 text-center text-sm text-ink-soft">
        <p className="font-[family-name:var(--font-bengali)]">
          {site.description}
        </p>
        <p className="mt-3 font-[family-name:var(--font-bengali)] text-xs">
          বাংলা প্রতিবেদনগুলো আন্তর্জাতিক সংবাদমাধ্যমের যাচাইকৃত তথ্যের ভিত্তিতে
          নিজস্ব ভাষায় লেখা; প্রতিটি প্রতিবেদনে তথ্যসূত্র উল্লেখ করা আছে।
        </p>
        <p className="mt-3 text-xs">
          World Wire headlines link to the original reports at BBC, The Guardian,
          Al Jazeera, NPR, TechCrunch and ESPN.
        </p>
      </footer>
    </main>
  );
}
