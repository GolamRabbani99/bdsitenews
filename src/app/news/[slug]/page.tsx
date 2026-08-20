import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AdSlot } from "@/components/AdSlot";
import { Cover } from "@/components/Cover";
import { RelatedArticles } from "@/components/RelatedArticles";
import { ShareBar } from "@/components/ShareBar";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import {
  ContextBox,
  ExplainerQA,
  FactCheckBox,
  ImpactBox,
} from "@/components/StructuredBlocks";
import { OpportunityPanel } from "@/components/OpportunityPanel";
import { SocialEmbed } from "@/components/SocialEmbed";
import {
  allArticles,
  formatBnDate,
  getArticle,
  readingMinutes,
  relatedArticles,
} from "@/lib/articles";
import { site } from "@/lib/site";

export function generateStaticParams() {
  return allArticles().map((a) => ({ slug: a.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const article = getArticle(slug);
  if (!article) return {};

  const url = `${site.baseUrl}/news/${article.slug}`;
  // With a photo we share the photo; otherwise the branded site card.
  // (A per-article PNG carrying the Bangla headline was tried and removed:
  // Satori has no complex-script shaping, so it mis-places Bangla vowel
  // signs — নিয়ে renders as "নয়িে". Broken Bangla is worse than generic.)
  const images = article.image
    ? [{ url: `${site.baseUrl}${article.image.url}`, alt: article.image.alt }]
    : [{ url: `${site.baseUrl}/opengraph-image`, alt: site.name }];

  return {
    title: `${article.title} — ${site.name}`,
    description: article.lead,
    alternates: { canonical: url },
    openGraph: {
      type: "article",
      url,
      siteName: site.name,
      locale: "bn_BD",
      title: article.title,
      description: article.lead,
      publishedTime: article.publishedAt,
      images,
    },
    twitter: {
      card: "summary_large_image",
      title: article.title,
      description: article.lead,
    },
  };
}

export default async function ArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = getArticle(slug);
  if (!article) notFound();

  const url = `${site.baseUrl}/news/${article.slug}`;
  const related = relatedArticles(article, 5);
  const minutes = readingMinutes(article);

  // Google News / Discover eligibility — a major traffic source for
  // Bangladeshi news sites, and free.
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: article.title,
    description: article.lead,
    inLanguage: "bn-BD",
    datePublished: article.publishedAt,
    dateModified: article.publishedAt,
    articleSection: article.category,
    mainEntityOfPage: { "@type": "WebPage", "@id": url },
    author: { "@type": "Organization", name: site.name, url: site.baseUrl },
    publisher: { "@type": "Organization", name: site.name, url: site.baseUrl },
    ...(article.image
      ? { image: [`${site.baseUrl}${article.image.url}`] }
      : {}),
  };

  // Split the body so an in-content ad sits after the opening paragraphs,
  // where engagement is highest.
  const splitAt = Math.min(2, article.body.length);
  const opening = article.body.slice(0, splitAt);
  const remainder = article.body.slice(splitAt);

  return (
    <main className="mx-auto max-w-3xl px-4 pb-12">
      {/* JSON.stringify does not escape "<", so a headline arriving from an
          external feed containing "</script>" would break out of this block
          and execute. Escape the three characters that can. */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(jsonLd)
            .replace(/</g, "\\u003c")
            .replace(/>/g, "\\u003e")
            .replace(/&/g, "\\u0026"),
        }}
      />
      <SiteHeader compact />

      <article lang="bn" className="pt-7 font-[family-name:var(--font-bengali)]">
        {/* No letter-spacing on Bangla: it separates conjunct clusters and
            makes বিতর্ক read as বি ত র্ ক. */}
        <p className="text-xs font-bold text-crimson">
          {article.category}
        </p>
        <h1 className="mt-3 text-[27px] font-bold leading-snug sm:text-4xl">
          {article.title}
        </h1>
        <p className="mt-3 flex flex-wrap items-center gap-x-2 text-sm text-ink-soft">
          <span className="font-semibold">বিডি সাইট নিউজ ডেস্ক</span>
          <span>·</span>
          <span>{formatBnDate(article.publishedAt)}</span>
          <span>·</span>
          <span>{minutes} মিনিটের পড়া</span>
        </p>

        <Cover
          slug={article.slug}
          category={article.category}
          title={article.title}
          image={article.image}
          className="mt-5"
        />

        <p className="mt-6 border-l-4 border-crimson pl-4 text-lg font-semibold leading-relaxed">
          {article.lead}
        </p>

        {article.factcheck && <FactCheckBox factcheck={article.factcheck} />}

        {/* High in the page on purpose: a student scanning for the deadline
            should not have to read the report to find it. */}
        <OpportunityPanel article={article} />

        {article.questions?.length ? (
          <>
            <ExplainerQA questions={article.questions.slice(0, 2)} />
            <AdSlot placement="in-article" />
            {article.questions.length > 2 && (
              <ExplainerQA questions={article.questions.slice(2)} />
            )}
          </>
        ) : (
          <>
            {opening.map((paragraph, i) => (
              <p key={i} className="mt-5 text-[17px] leading-loose">
                {paragraph}
              </p>
            ))}

            <AdSlot placement="in-article" />

            {remainder.map((paragraph, i) => (
              <p key={i} className="mt-5 text-[17px] leading-loose">
                {paragraph}
              </p>
            ))}
          </>
        )}

        {article.impact?.length ? <ImpactBox impact={article.impact} /> : null}
        {article.context?.length ? (
          <ContextBox context={article.context} />
        ) : null}

        {article.stats && (
          <div className="mt-8 overflow-x-auto">
            <p className="border-l-4 border-crimson pl-3 text-sm font-bold">
              {article.stats.title}
            </p>
            <table className="mt-3 w-full border-collapse text-sm">
              <thead>
                <tr className="bg-ink text-paper">
                  {article.stats.headers.map((h, i) => (
                    <th key={i} className="px-3 py-2 text-left font-semibold">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {article.stats.rows.map((row, i) => (
                  <tr key={i} className={i % 2 ? "bg-paper" : "bg-rule/30"}>
                    {row.map((cell, j) => (
                      <td
                        key={j}
                        className={`px-3 py-2 ${j === 0 ? "font-semibold" : ""}`}
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <ShareBar url={url} title={article.title} />

        <footer className="mt-8 border-t border-rule pt-5">
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
          <p className="mt-3 text-xs text-ink-soft">
            এই প্রতিবেদনটি আন্তর্জাতিক সংবাদমাধ্যমের যাচাইকৃত তথ্যের ভিত্তিতে
            বিডি সাইট নিউজের নিজস্ব ভাষায় লেখা।
          </p>
        </footer>
        {/* After the reporting, before the sources: the post is supporting
            material, not the story. */}
        <SocialEmbed article={article} />
      </article>

      <AdSlot placement="end-article" />

      <RelatedArticles articles={related} category={article.category} />

      <SiteFooter />
    </main>
  );
}
