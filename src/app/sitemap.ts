import type { MetadataRoute } from "next";
import articles from "@/data/articles.json";
import { site } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const staticPages = ["", "/about", "/contact", "/privacy"].map((path) => ({
    url: `${site.baseUrl}${path}`,
    lastModified: new Date(),
  }));
  const articlePages = articles.map((a) => ({
    url: `${site.baseUrl}/news/${a.slug}`,
    lastModified: new Date(a.publishedAt),
  }));
  return [...staticPages, ...articlePages];
}
