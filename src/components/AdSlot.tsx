import { site } from "@/lib/site";

/**
 * Ad inventory. Renders nothing until `adsensePublisherId` is set in
 * src/lib/site.ts, so the site stays fast and clean before approval.
 *
 * Placement notes (why these four):
 *  - in-article  : highest RPM on news sites; sits inside the read
 *  - end-article : catches the reader at the decision point
 *  - in-feed     : native-looking slot between homepage items
 *  - leaderboard : brand/impression slot at the top
 */
export type AdPlacement = "leaderboard" | "in-article" | "end-article" | "in-feed";

const FORMAT: Record<AdPlacement, { format: string; minH: string; label: boolean }> = {
  leaderboard: { format: "horizontal", minH: "min-h-[90px]", label: false },
  "in-article": { format: "fluid", minH: "min-h-[250px]", label: true },
  "end-article": { format: "rectangle", minH: "min-h-[250px]", label: true },
  "in-feed": { format: "fluid", minH: "min-h-[200px]", label: true },
};

export function AdSlot({ placement }: { placement: AdPlacement }) {
  if (!site.adsensePublisherId) return null;
  const cfg = FORMAT[placement];

  return (
    <aside className={`my-7 w-full ${cfg.minH}`} aria-label="বিজ্ঞাপন">
      {cfg.label && (
        <p className="mb-1 text-center text-[10px] uppercase tracking-[0.2em] text-ink-soft">
          বিজ্ঞাপন
        </p>
      )}
      <ins
        className="adsbygoogle block w-full"
        data-ad-client={site.adsensePublisherId}
        data-ad-format={cfg.format}
        data-full-width-responsive="true"
      />
      <script
        dangerouslySetInnerHTML={{
          __html: "(adsbygoogle = window.adsbygoogle || []).push({});",
        }}
      />
    </aside>
  );
}
