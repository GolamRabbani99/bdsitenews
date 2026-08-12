import Link from "next/link";
import { ArticleCard, ArticleRow } from "@/components/ArticleCard";
import { type Article, categorySlug } from "@/lib/articles";

/**
 * End-of-article recirculation — the highest-value block on the page.
 * A reader who finishes an article either clicks here or leaves the site,
 * so this is what turns 1 pageview per visitor into 2–3.
 */
export function RelatedArticles({
  articles,
  category,
}: {
  articles: Article[];
  category: string;
}) {
  if (articles.length === 0) return null;
  const [featured, ...rest] = articles;

  return (
    <section className="mt-12 border-t-[3px] border-double border-ink pt-6 font-[family-name:var(--font-bengali)]">
      <h2 className="text-lg font-bold">আরও পড়ুন</h2>

      <div className="mt-5 grid gap-6 sm:grid-cols-2">
        <ArticleCard article={featured} />
        <div>
          {rest.map((a) => (
            <ArticleRow key={a.slug} article={a} />
          ))}
        </div>
      </div>

      <p className="mt-6 text-center">
        <Link
          href={`/category/${categorySlug(category)}`}
          className="inline-block border border-ink px-5 py-2 text-sm font-semibold hover:bg-ink hover:text-paper"
        >
          {category} বিভাগের সব খবর →
        </Link>
      </p>
    </section>
  );
}
