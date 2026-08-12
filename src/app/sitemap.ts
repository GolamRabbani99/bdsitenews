import type { MetadataRoute } from "next";
import { CATEGORIES, allArticles } from "@/lib/articles";
import { site } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const staticPages = ["", "/about", "/contact", "/privacy"].map((path) => ({
    url: `${site.baseUrl}${path}`,
    lastModified: new Date(),
    changeFrequency: (path === "" ? "hourly" : "monthly") as
      | "hourly"
      | "monthly",
    priority: path === "" ? 1 : 0.4,
  }));

  const categoryPages = CATEGORIES.map((c) => ({
    url: `${site.baseUrl}/category/${c.slug}`,
    lastModified: new Date(),
    changeFrequency: "hourly" as const,
    priority: 0.7,
  }));

  const articlePages = allArticles().map((a) => ({
    url: `${site.baseUrl}/news/${a.slug}`,
    lastModified: new Date(a.publishedAt),
    changeFrequency: "daily" as const,
    priority: 0.9,
  }));

  return [...staticPages, ...categoryPages, ...articlePages];
}
