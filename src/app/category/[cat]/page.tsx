import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AdSlot } from "@/components/AdSlot";
import { ArticleCard } from "@/components/ArticleCard";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { CATEGORIES, byCategory, categoryBn } from "@/lib/articles";
import { site } from "@/lib/site";

export function generateStaticParams() {
  return CATEGORIES.map((c) => ({ cat: c.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ cat: string }>;
}): Promise<Metadata> {
  const { cat } = await params;
  const bn = categoryBn(cat);
  if (!bn) return {};
  return {
    title: `${bn} — ${site.name}`,
    description: `${bn} বিভাগের সর্বশেষ খবর — ${site.name}`,
    alternates: { canonical: `${site.baseUrl}/category/${cat}` },
  };
}

export default async function CategoryPage({
  params,
}: {
  params: Promise<{ cat: string }>;
}) {
  const { cat } = await params;
  const bn = categoryBn(cat);
  if (!bn) notFound();

  const articles = byCategory(bn);

  return (
    <main className="mx-auto max-w-6xl px-4 pb-12">
      <SiteHeader compact />

      <h1 className="mt-7 border-b-[3px] border-double border-ink pb-3 font-[family-name:var(--font-bengali)] text-2xl font-bold">
        {bn}
        <span className="ml-3 text-sm font-normal text-ink-soft">
          {articles.length}টি প্রতিবেদন
        </span>
      </h1>

      {articles.length === 0 ? (
        <p className="py-16 text-center font-[family-name:var(--font-bengali)] text-ink-soft">
          এই বিভাগে এখনো কোনো প্রতিবেদন নেই।
        </p>
      ) : (
        <>
          <div className="grid gap-x-7 gap-y-9 py-8 sm:grid-cols-2 lg:grid-cols-3">
            {articles.slice(0, 6).map((a) => (
              <ArticleCard key={a.slug} article={a} />
            ))}
          </div>

          {articles.length > 6 && (
            <>
              <AdSlot placement="in-feed" />
              <div className="grid gap-x-7 gap-y-9 pb-8 sm:grid-cols-2 lg:grid-cols-3">
                {articles.slice(6).map((a) => (
                  <ArticleCard key={a.slug} article={a} />
                ))}
              </div>
            </>
          )}
        </>
      )}

      <SiteFooter />
    </main>
  );
}
