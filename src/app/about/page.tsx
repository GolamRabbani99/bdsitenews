import type { Metadata } from "next";
import Link from "next/link";
import { site } from "@/lib/site";
import { SiteFooter } from "@/components/SiteFooter";

export const metadata: Metadata = {
  title: `About — ${site.name}`,
  description: `How ${site.name} produces original, fact-based news in Bangla and English.`,
};

export default function AboutPage() {
  return (
    <main className="mx-auto max-w-3xl px-4">
      <header className="py-6 text-center">
        <Link href="/" className="font-[family-name:var(--font-serif-news)] text-2xl font-semibold">
          {site.name} <span className="text-crimson font-[family-name:var(--font-bengali)]">{site.nameBn}</span>
        </Link>
      </header>
      <div className="rule-double" />

      <article className="prose-sm pt-8 leading-relaxed">
        <h1 className="font-[family-name:var(--font-serif-news)] text-3xl font-semibold">
          About BD Site News
        </h1>

        <p className="mt-4 font-[family-name:var(--font-bengali)] text-base" lang="bn">
          বিডি সাইট নিউজ একটি স্বাধীন ডিজিটাল সংবাদমাধ্যম। আমরা বিশ্বের নির্ভরযোগ্য
          সংবাদ সংস্থার যাচাইকৃত তথ্যের ভিত্তিতে বাংলাদেশি পাঠকদের জন্য সম্পূর্ণ
          মৌলিক ভাষায় সংবাদ পরিবেশন করি — বিশেষ গুরুত্ব খেলাধুলা, আন্তর্জাতিক ও
          প্রযুক্তি সংবাদে।
        </p>

        <h2 className="mt-8 text-xl font-semibold">How we work</h2>
        <p className="mt-3">
          BD Site News uses an AI-assisted editorial pipeline with human oversight.
          For every story we:
        </p>
        <ul className="mt-3 list-disc space-y-2 pl-6">
          <li>Read reports from multiple trusted sources (BBC, The Guardian, Al Jazeera, NPR, ESPN, and leading Bangladeshi outlets).</li>
          <li>Extract and cross-check the facts — claims are marked verified, disputed, or unverified.</li>
          <li>Write a completely original article in Bangla. We never copy or translate another outlet&apos;s text.</li>
          <li>List our sources at the end of every article, with links to the original reports.</li>
          <li>Apply editorial review for accuracy, fairness, and legal safety before publishing.</li>
        </ul>

        <h2 className="mt-8 text-xl font-semibold">Corrections</h2>
        <p className="mt-3">
          Accuracy matters more to us than speed. If you spot an error, write to{" "}
          <a href={`mailto:${site.contactEmail}`} className="text-crimson underline">
            {site.contactEmail}
          </a>{" "}
          and we will review and correct it promptly.
        </p>

        <h2 className="mt-8 text-xl font-semibold">Images</h2>
        <p className="mt-3">
          Photographs are used under open licenses (public domain, Creative Commons)
          with credits shown beneath each image, or are original graphics created by
          BD Site News.
        </p>
      </article>

      <SiteFooter />
    </main>
  );
}
