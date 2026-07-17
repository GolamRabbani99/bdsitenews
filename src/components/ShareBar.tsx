"use client";

import { useState } from "react";

/** Share buttons: Facebook + WhatsApp first (Bangladesh's channels), then X
 * and copy-link. Plain share URLs — no SDKs, no trackers. */
export function ShareBar({ url, title }: { url: string; title: string }) {
  const [copied, setCopied] = useState(false);
  const u = encodeURIComponent(url);
  const t = encodeURIComponent(title);

  const links = [
    {
      label: "ফেসবুকে শেয়ার",
      href: `https://www.facebook.com/sharer/sharer.php?u=${u}`,
      className: "bg-[#1877f2] text-white",
    },
    {
      label: "হোয়াটসঅ্যাপ",
      href: `https://wa.me/?text=${t}%0A${u}`,
      className: "bg-[#25d366] text-white",
    },
    {
      label: "X",
      href: `https://x.com/intent/tweet?text=${t}&url=${u}`,
      className: "bg-ink text-paper",
    },
  ];

  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable — ignore */
    }
  }

  return (
    <div className="mt-8 flex flex-wrap items-center gap-2 border-y border-rule py-4">
      <span className="mr-1 text-xs font-bold uppercase tracking-widest text-ink-soft">
        শেয়ার করুন
      </span>
      {links.map((l) => (
        <a
          key={l.label}
          href={l.href}
          target="_blank"
          rel="noopener noreferrer"
          className={`px-3 py-1.5 text-xs font-bold ${l.className} hover:opacity-85`}
        >
          {l.label}
        </a>
      ))}
      <button
        onClick={copy}
        className="border border-rule px-3 py-1.5 text-xs font-bold text-ink-soft hover:text-crimson"
      >
        {copied ? "কপি হয়েছে ✓" : "লিংক কপি"}
      </button>
    </div>
  );
}
