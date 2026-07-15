import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import articles from "@/data/articles.json";
import { AdSlot } from "@/components/AdSlot";
import { Cover } from "@/components/Cover";
import { SiteFooter } from "@/components/SiteFooter";
import { site } from "@/lib/site";

type Article = (typeof articles)[number];
type WithImage = { image?: { url: string; alt: string; credit?: string } };

export function generateStaticParams() {
  return articles.map((a) => ({ slug: a.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const article = articles.find((a) => a.slug === slug);
  if (!article) return {};
  return {
    title: `${article.title} — ${site.name}`,
    description: article.lead,
  };
}

export default async function ArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article: Article | undefined = articles.find((a) => a.slug === slug);
  if (!article) notFound();

  return (
    <main className="mx-auto max-w-3xl px-4 pb-16 font-[family-name:var(--font-bengali)]">
      <header className="py-6 text-center">
        <Link
          href="/"
          className="font-[family-name:var(--font-serif-news)] text-2xl font-semibold tracking-tight"
        >
          {site.name}{" "}
          <span className="text-crimson">{site.nameBn}</span>
        </Link>
      </header>
      <div className="rule-double" />

      <article lang="bn" className="pt-8">
        <p className="text-xs font-bold uppercase tracking-[0.25em] text-crimson">
          {article.category}
        </p>
        <h1 className="mt-3 text-3xl font-semibold leading-snug sm:text-4xl">
          {article.title}
        </h1>
        <p className="mt-3 text-sm text-ink-soft">
          বিডি সাইট নিউজ ডেস্ক ·{" "}
          {new Date(article.publishedAt).toLocaleDateString("bn-BD", {
            day: "numeric",
            month: "long",
            year: "numeric",
            timeZone: "Asia/Dhaka",
          })}
        </p>

        <Cover
          slug={article.slug}
          category={article.category}
          title={article.title}
          image={(article as WithImage).image}
          className="mt-6"
        />

        <p className="mt-6 border-l-4 border-crimson pl-4 text-lg font-semibold leading-relaxed">
          {article.lead}
        </p>

        <AdSlot slot="in-article" />

        {article.body.map((paragraph, i) => (
          <p key={i} className="mt-5 text-base leading-loose">
            {paragraph}
          </p>
        ))}

        <footer className="mt-10 border-t border-rule pt-5">
          <p className="text-sm font-semibold">তথ্যসূত্র</p>
          <ul className="mt-2 space-y-1 text-sm text-ink-soft">
            {article.sources.map((s) => (
              <li key={s.url}>
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-crimson hover:underline"
                >
                  {s.name} ↗
                </a>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-ink-soft">
            এই প্রতিবেদনটি একাধিক আন্তর্জাতিক সংবাদমাধ্যমের যাচাইকৃত তথ্যের
            ভিত্তিতে বিডি সাইট নিউজের নিজস্ব ভাষায় লেখা।
          </p>
        </footer>
      </article>

      <p className="mt-10 text-center">
        <Link href="/" className="text-sm text-crimson hover:underline">
          ← প্রচ্ছদে ফিরুন
        </Link>
      </p>

      <SiteFooter />
    </main>
  );
}
