import articlesData from "@/data/articles.json";

export type Article = {
  slug: string;
  title: string;
  category: string;
  lead: string;
  /** কী ঘটেছে — the event itself */
  body: string[];
  /** এতে কী বদলাবে — concrete consequence for readers (omitted when unknown) */
  impact?: string[];
  /** প্রেক্ষাপট — background, only when the source supplied it */
  context?: string[];
  /** Verification of a viral claim, from a fact-checking source */
  factcheck?: { claim: string; verdict: string };
  /** ব্যাখ্যা format: the questions a reader actually has */
  questions?: { question: string; answer: string[] }[];
  /** For explainers — the desk the underlying story belongs to */
  topic?: string;
  sources: { name: string; url: string }[];
  publishedAt: string;
  image?: {
    url: string;
    alt: string;
    credit?: string;
    /** True when the photo illustrates the subject rather than the event */
    illustrative?: boolean;
  };
  stats?: { title: string; headers: string[]; rows: string[][] };
};

/**
 * Bangla category ⇄ ASCII slug. `aliases` keeps older articles working after
 * a rename (খেলাধুলা → খেলা, আন্তর্জাতিক → বিশ্ব) without rewriting data.
 */
export const CATEGORIES = [
  { slug: "bangladesh", bn: "বাংলাদেশ", aliases: [] as string[] },
  { slug: "politics", bn: "রাজনীতি", aliases: [] },
  { slug: "crime", bn: "অপরাধ", aliases: ["আইন-আদালত"] },
  { slug: "sports", bn: "খেলা", aliases: ["খেলাধুলা"] },
  { slug: "entertainment", bn: "বিনোদন", aliases: [] },
  { slug: "business", bn: "অর্থনীতি", aliases: ["ব্যবসা"] },
  { slug: "world", bn: "বিশ্ব", aliases: ["আন্তর্জাতিক"] },
  { slug: "tech", bn: "প্রযুক্তি", aliases: [] },
  { slug: "education", bn: "শিক্ষা", aliases: [] },
  { slug: "probash", bn: "প্রবাস", aliases: ["প্রবাসী"] },
  { slug: "district", bn: "জেলা", aliases: [] },
  { slug: "fact-check", bn: "ফ্যাক্ট চেক", aliases: [] },
  { slug: "explainer", bn: "ব্যাখ্যা", aliases: [] },
  { slug: "debate", bn: "বিতর্ক", aliases: [] },
] as const;

/** Canonical Bangla name for a category label (handles renamed categories). */
export function canonicalCategory(bn: string): string {
  const hit = CATEGORIES.find(
    (c) => c.bn === bn || (c.aliases as readonly string[]).includes(bn),
  );
  return hit?.bn ?? bn;
}

export function categorySlug(bn: string): string {
  const hit = CATEGORIES.find(
    (c) => c.bn === bn || (c.aliases as readonly string[]).includes(bn),
  );
  return hit?.slug ?? "news";
}

export function categoryBn(slug: string): string | undefined {
  return CATEGORIES.find((c) => c.slug === slug)?.bn;
}

// Normalise every article's category once, at load.
const all = (articlesData as Article[]).map((a) => ({
  ...a,
  category: canonicalCategory(a.category),
}));

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

/**
 * Categories that actually have articles, kept in masthead order. Empty
 * sections are hidden rather than shipping dead pages to Google — they
 * appear on their own as the desks fill up.
 */
export function activeCategories() {
  const counts = new Map<string, number>();
  for (const a of all) counts.set(a.category, (counts.get(a.category) ?? 0) + 1);
  return CATEGORIES.filter((c) => (counts.get(c.bn) ?? 0) > 0);
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
  const parts = [
    article.lead,
    ...article.body,
    ...(article.impact ?? []),
    ...(article.context ?? []),
    ...(article.questions ?? []).flatMap((q) => [q.question, ...q.answer]),
  ];
  const words = parts.join(" ").trim().split(/\s+/).length;
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
