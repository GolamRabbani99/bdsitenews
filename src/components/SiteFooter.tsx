import Link from "next/link";
import { site } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-rule pt-8 pb-4 text-center text-sm text-ink-soft">
      <p className="font-[family-name:var(--font-bengali)]">{site.description}</p>
      <p className="mt-3 font-[family-name:var(--font-bengali)] text-xs">
        বাংলা প্রতিবেদনগুলো আন্তর্জাতিক সংবাদমাধ্যমের যাচাইকৃত তথ্যের ভিত্তিতে
        নিজস্ব ভাষায় লেখা; প্রতিটি প্রতিবেদনে তথ্যসূত্র উল্লেখ করা আছে।
      </p>
      <nav className="mt-5 flex flex-wrap justify-center gap-x-6 gap-y-2 text-xs uppercase tracking-widest">
        <Link href="/" className="hover:text-crimson">Home</Link>
        <Link href="/about" className="hover:text-crimson">About</Link>
        <Link href="/contact" className="hover:text-crimson">Contact</Link>
        <Link href="/privacy" className="hover:text-crimson">Privacy Policy</Link>
      </nav>
      <p className="mt-4 text-xs">
        © {new Date().getFullYear()} {site.name} · bdsitenews.com
      </p>
    </footer>
  );
}
