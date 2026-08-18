import type { MetadataRoute } from "next";
import { CATEGORIES, allArticles, byCategory } from "@/lib/articles";
import { site } from "@/lib/site";

/** Bump only when the policy or about copy actually changes. */
const STATIC_PAGES_UPDATED = new Date("2026-07-15T00:00:00+06:00");

export default function sitemap(): MetadataRoute.Sitemap {
  const articles = allArticles();
  // The homepage genuinely changes whenever something is published.
  const newest = articles.length
    ? new Date(articles[0].publishedAt)
    : STATIC_PAGES_UPDATED;

  const staticPages = ["", "/about", "/contact", "/privacy"].map((path) => ({
    url: `${site.baseUrl}${path}`,
    // Never new Date(): stamping every build made /privacy claim it changed
    // several times a day, and a lastmod that is always "now" is one Google
    // learns to ignore — on every URL, including the ones that did change.
    lastModified: path === "" ? newest : STATIC_PAGES_UPDATED,
    changeFrequency: (path === "" ? "hourly" : "monthly") as
      | "hourly"
      | "monthly",
    priority: path === "" ? 1 : 0.4,
  }));

  const categoryPages = CATEGORIES.map((c) => {
    const inCategory = byCategory(c.bn);
    return {
      url: `${site.baseUrl}/category/${c.slug}`,
      // A desk was last modified when its newest story landed.
      lastModified: inCategory.length
        ? new Date(inCategory[0].publishedAt)
        : STATIC_PAGES_UPDATED,
      changeFrequency: "daily" as const,
      priority: 0.7,
    };
  });

  const articlePages = allArticles().map((a) => ({
    url: `${site.baseUrl}/news/${a.slug}`,
    lastModified: new Date(a.publishedAt),
    changeFrequency: "daily" as const,
    priority: 0.9,
  }));

  return [...staticPages, ...categoryPages, ...articlePages];
}
