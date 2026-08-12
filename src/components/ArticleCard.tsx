import Link from "next/link";
import { Cover } from "@/components/Cover";
import { type Article, formatBnDate } from "@/lib/articles";

/** Compact card used in grids and recirculation lists. */
export function ArticleCard({
  article,
  showImage = true,
}: {
  article: Article;
  showImage?: boolean;
}) {
  return (
    <Link
      href={`/news/${article.slug}`}
      className="group flex flex-col font-[family-name:var(--font-bengali)]"
    >
      {showImage && (
        <Cover
          slug={article.slug}
          category={article.category}
          title={article.title}
          image={article.image}
          className="mb-3"
        />
      )}
      <p className="text-[11px] font-bold tracking-[0.18em] text-crimson">
        {article.category}
      </p>
      <h3
        lang="bn"
        className="mt-1.5 text-lg font-semibold leading-snug group-hover:underline"
      >
        {article.title}
      </h3>
      <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-ink-soft">
        {article.lead}
      </p>
      <p className="mt-2 text-[11px] text-ink-soft">
        {formatBnDate(article.publishedAt)}
      </p>
    </Link>
  );
}

/** Dense text-only row — used for "more news" rails where images would
 * slow the page and dilute the click. */
export function ArticleRow({
  article,
  index,
}: {
  article: Article;
  index?: number;
}) {
  return (
    <Link
      href={`/news/${article.slug}`}
      className="group flex gap-3 border-b border-rule py-3 font-[family-name:var(--font-bengali)] last:border-0"
    >
      {index !== undefined && (
        <span className="w-6 shrink-0 font-[family-name:var(--font-serif-news)] text-xl font-semibold text-rule">
          {index + 1}
        </span>
      )}
      <div className="min-w-0">
        <h4
          lang="bn"
          className="text-[15px] font-semibold leading-snug group-hover:text-crimson"
        >
          {article.title}
        </h4>
        <p className="mt-1 text-[11px] text-ink-soft">
          {article.category} · {formatBnDate(article.publishedAt)}
        </p>
      </div>
    </Link>
  );
}
