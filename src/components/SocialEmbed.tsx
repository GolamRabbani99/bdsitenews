import type { Article } from "@/lib/articles";

/**
 * Embed a public social post beneath a report.
 *
 * Embedding is not copying: the platform serves the content from its own
 * servers, attribution is automatic, and the author can delete it and have it
 * disappear here too. That is what makes it lawful where saving the image and
 * republishing it is not.
 *
 * Deliberately an iframe rather than each platform's JavaScript SDK. The SDKs
 * load a tracking script into every page on the site; the iframe loads only on
 * the article that has an embed, and only that article.
 */
const BUILDERS: Record<string, (url: string) => string | null> = {
  facebook: (url) =>
    "https://www.facebook.com/plugins/post.php?href=" +
    encodeURIComponent(url) +
    "&show_text=true&width=500",
  youtube: (url) => {
    const id =
      url.match(/[?&]v=([\w-]{11})/)?.[1] ??
      url.match(/youtu\.be\/([\w-]{11})/)?.[1] ??
      url.match(/shorts\/([\w-]{11})/)?.[1];
    // youtube-nocookie so a reader who never plays the video is not tracked.
    return id ? `https://www.youtube-nocookie.com/embed/${id}` : null;
  },
};

export function SocialEmbed({ article }: { article: Article }) {
  const embed = article.embed;
  if (!embed?.url) return null;

  const src = BUILDERS[embed.platform]?.(embed.url);
  if (!src) return null;

  const isVideo = embed.platform === "youtube";

  return (
    <figure className="my-8">
      <div
        className={
          isVideo
            ? "relative w-full overflow-hidden rounded-lg pt-[56.25%]"
            : "overflow-hidden rounded-lg border border-rule"
        }
      >
        <iframe
          src={src}
          title={embed.caption || "সংযুক্ত পোস্ট"}
          loading="lazy"
          allow="encrypted-media; picture-in-picture; web-share"
          referrerPolicy="strict-origin-when-cross-origin"
          scrolling="no"
          className={
            isVideo
              ? "absolute inset-0 h-full w-full border-0"
              : "h-[640px] w-full border-0"
          }
        />
      </div>

      {embed.caption && (
        <figcaption
          className="mt-2 font-[family-name:var(--font-bengali)] text-xs text-ink-soft"
          lang="bn"
        >
          {embed.caption}
        </figcaption>
      )}
    </figure>
  );
}
