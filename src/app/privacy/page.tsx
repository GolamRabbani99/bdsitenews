import type { Metadata } from "next";
import Link from "next/link";
import { site } from "@/lib/site";
import { SiteFooter } from "@/components/SiteFooter";

export const metadata: Metadata = {
  title: `Privacy Policy — ${site.name}`,
  description: `How ${site.name} handles data, cookies, and advertising.`,
};

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-4">
      <header className="py-6 text-center">
        <Link href="/" className="font-[family-name:var(--font-serif-news)] text-2xl font-semibold">
          {site.name} <span className="text-crimson font-[family-name:var(--font-bengali)]">{site.nameBn}</span>
        </Link>
      </header>
      <div className="rule-double" />

      <article className="pt-8 text-sm leading-relaxed">
        <h1 className="font-[family-name:var(--font-serif-news)] text-3xl font-semibold">Privacy Policy</h1>
        <p className="mt-2 text-ink-soft">Last updated: 15 July 2026</p>

        <h2 className="mt-8 text-lg font-semibold">Who we are</h2>
        <p className="mt-2">
          BD Site News (bdsitenews.com) is a digital news publication. This policy
          explains what data we collect when you visit the site and how it is used.
        </p>

        <h2 className="mt-6 text-lg font-semibold">Data we collect</h2>
        <ul className="mt-2 list-disc space-y-2 pl-6">
          <li>
            <span className="font-semibold">Reading the site:</span> we do not require
            accounts and do not ask for personal information to read our articles.
          </li>
          <li>
            <span className="font-semibold">Hosting logs:</span> our hosting provider
            (Vercel) may process technical data such as IP address and browser type to
            deliver the site securely and measure aggregate performance.
          </li>
          <li>
            <span className="font-semibold">Email:</span> if you contact us, we keep
            your email only to respond to you.
          </li>
        </ul>

        <h2 className="mt-6 text-lg font-semibold">Cookies &amp; advertising</h2>
        <p className="mt-2">
          We may display advertising, including Google AdSense. Third-party vendors,
          including Google, use cookies to serve ads based on your prior visits to
          this or other websites. Google&apos;s use of advertising cookies enables it
          and its partners to serve ads based on your visits to this site and/or other
          sites on the Internet. You may opt out of personalised advertising by
          visiting{" "}
          <a href="https://www.google.com/settings/ads" className="text-crimson underline"
             target="_blank" rel="noopener noreferrer">
            Google Ads Settings
          </a>
          .
        </p>

        <h2 className="mt-6 text-lg font-semibold">Analytics</h2>
        <p className="mt-2">
          We may use privacy-respecting, aggregate analytics to understand which
          articles readers find useful. We do not sell personal data to anyone.
        </p>

        <h2 className="mt-6 text-lg font-semibold">External links</h2>
        <p className="mt-2">
          Our articles cite and link to original sources. Those sites have their own
          privacy policies which we do not control.
        </p>

        <h2 className="mt-6 text-lg font-semibold">Contact</h2>
        <p className="mt-2">
          Questions about this policy:{" "}
          <a href={`mailto:${site.contactEmail}`} className="text-crimson underline">
            {site.contactEmail}
          </a>
        </p>
      </article>

      <SiteFooter />
    </main>
  );
}
