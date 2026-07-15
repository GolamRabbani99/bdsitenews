import type { Metadata } from "next";
import Link from "next/link";
import { site } from "@/lib/site";
import { SiteFooter } from "@/components/SiteFooter";

export const metadata: Metadata = {
  title: `Contact — ${site.name}`,
  description: `Contact the ${site.name} editorial team.`,
};

export default function ContactPage() {
  return (
    <main className="mx-auto max-w-3xl px-4">
      <header className="py-6 text-center">
        <Link href="/" className="font-[family-name:var(--font-serif-news)] text-2xl font-semibold">
          {site.name} <span className="text-crimson font-[family-name:var(--font-bengali)]">{site.nameBn}</span>
        </Link>
      </header>
      <div className="rule-double" />

      <article className="pt-8 leading-relaxed">
        <h1 className="font-[family-name:var(--font-serif-news)] text-3xl font-semibold">Contact</h1>

        <p className="mt-4 font-[family-name:var(--font-bengali)]" lang="bn">
          মতামত, সংশোধনী, সংবাদ-টিপ কিংবা বিজ্ঞাপন — যেকোনো প্রয়োজনে আমাদের লিখুন।
        </p>

        <div className="mt-6 space-y-4">
          <p>
            <span className="font-semibold">Editorial &amp; corrections:</span>{" "}
            <a href={`mailto:${site.contactEmail}`} className="text-crimson underline">
              {site.contactEmail}
            </a>
          </p>
          <p>
            <span className="font-semibold">Advertising &amp; partnerships:</span>{" "}
            <a href={`mailto:${site.contactEmail}?subject=Advertising`} className="text-crimson underline">
              {site.contactEmail}
            </a>
          </p>
        </div>

        <p className="mt-6 text-sm text-ink-soft">
          We aim to respond within 48 hours. For corrections, please include the
          article link and the specific claim in question.
        </p>
      </article>

      <SiteFooter />
    </main>
  );
}
