import articlesData from "@/data/articles.json";

export type Article = {
  slug: string;
  title: string;
  category: string;
  lead: string;
  body: string[];
  sources: { name: string; url: string }[];
  publishedAt: string;
  image?: { url: string; alt: string; credit?: string };
  stats?: { title: string; headers: string[]; rows: string[][] };
};

/** Bangla category ⇄ ASCII slug, so category pages are indexable URLs. */
export const CATEGORIES = [
  { slug: "tech", bn: "প্রযুক্তি" },
  { slug: "sports", bn: "খেলাধুলা" },
  { slug: "world", bn: "আন্তর্জাতিক" },
  { slug: "business", bn: "অর্থনীতি" },
  { slug: "politics", bn: "রাজনীতি" },
  { slug: "bangladesh", bn: "বাংলাদেশ" },
] as const;

export function categorySlug(bn: string): string {
  return CATEGORIES.find((c) => c.bn === bn)?.slug ?? "news";
}

export function categoryBn(slug: string): string | undefined {
  return CATEGORIES.find((c) => c.slug === slug)?.bn;
}

const all = articlesData as Article[];

/** Newest first — the ordering every news site uses. */
export function allArticles(): Article[] {
  return [...all].sort(
    (a, b) =>
      new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime(),
  );
}

export function getArticle(slug: string): Article | undefined {
  return all.find((a) => a.slug === slug);
}

export function byCategory(bn: string): Article[] {
  return allArticles().filter((a) => a.category === bn);
}

/** Categories that actually have articles, ordered by article count. */
export function activeCategories() {
  const counts = new Map<string, number>();
  for (const a of all) counts.set(a.category, (counts.get(a.category) ?? 0) + 1);
  return CATEGORIES.filter((c) => counts.has(c.bn)).sort(
    (a, b) => (counts.get(b.bn) ?? 0) - (counts.get(a.bn) ?? 0),
  );
}

/**
 * Recirculation: same category first (most likely next click), then newest
 * from anywhere. This is the single biggest lever on pages-per-session.
 */
export function relatedArticles(current: Article, limit = 6): Article[] {
  const others = allArticles().filter((a) => a.slug !== current.slug);
  const sameCat = others.filter((a) => a.category === current.category);
  const rest = others.filter((a) => a.category !== current.category);
  return [...sameCat, ...rest].slice(0, limit);
}

export function readingMinutes(article: Article): number {
  const words = (article.lead + " " + article.body.join(" ")).split(/\s+/).length;
  return Math.max(1, Math.round(words / 180));
}

export function formatBnDate(iso: string): string {
  return new Date(iso).toLocaleDateString("bn-BD", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Asia/Dhaka",
  });
}
