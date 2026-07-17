import type { Metadata } from "next";
import { Newsreader, Noto_Sans_Bengali } from "next/font/google";
import { GoogleAnalytics } from "@next/third-parties/google";
import { site } from "@/lib/site";
import "./globals.css";

const newsreader = Newsreader({
  subsets: ["latin"],
  style: ["normal", "italic"],
  variable: "--font-newsreader",
});

const bengali = Noto_Sans_Bengali({
  subsets: ["bengali"],
  weight: ["400", "600"],
  variable: "--font-bengali",
});

export const metadata: Metadata = {
  title: `${site.name} — ${site.tagline}`,
  description: site.description,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${newsreader.variable} ${bengali.variable}`}>
        {children}
      </body>
      {site.gaMeasurementId && <GoogleAnalytics gaId={site.gaMeasurementId} />}
    </html>
  );
}
