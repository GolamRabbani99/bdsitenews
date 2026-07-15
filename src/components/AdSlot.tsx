import { site } from "@/lib/site";

/** AdSense-ready slot. Renders nothing until adsensePublisherId is set in
 * src/lib/site.ts — then swap the placeholder for the real <ins> unit.
 * Slots: "leaderboard" (home, under masthead), "in-grid" (home, between
 * sections), "in-article" (article pages, after the lead). */
export function AdSlot({ slot }: { slot: "leaderboard" | "in-grid" | "in-article" }) {
  if (!site.adsensePublisherId) return null;

  const height = slot === "leaderboard" ? "min-h-[90px]" : "min-h-[250px]";
  return (
    <div
      className={`my-6 flex w-full items-center justify-center border border-dashed border-rule ${height}`}
      aria-hidden="true"
    >
      {/* Replace with the AdSense <ins class="adsbygoogle"> unit for this
          slot once approved. data-ad-client={site.adsensePublisherId} */}
      <span className="text-[10px] uppercase tracking-widest text-ink-soft">
        বিজ্ঞাপন · Advertisement
      </span>
    </div>
  );
}
