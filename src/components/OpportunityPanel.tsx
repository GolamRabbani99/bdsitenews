import type { Article } from "@/lib/articles";

/**
 * The details a student needs in order to actually apply, pulled out of the
 * prose and into a scannable panel.
 *
 * Every field is optional on purpose. A missing deadline is left visibly
 * absent rather than filled with a guess: a wrong date here costs somebody a
 * scholarship, so the panel says "not stated" and sends them to the official
 * page instead.
 */
export function OpportunityPanel({ article }: { article: Article }) {
  const o = article.opportunity;
  if (!o) return null;

  const facts = [
    { label: "দেশ", value: o.country },
    { label: "প্রতিষ্ঠান", value: o.institution },
    { label: "পর্যায়", value: o.level },
  ].filter((f) => f.value);

  const lists = [
    { label: "যা যা কভার করে", items: o.funding },
    { label: "যোগ্যতা", items: o.eligibility },
    { label: "আবেদনের ধাপ", items: o.howToApply, ordered: true },
  ].filter((l) => l.items && l.items.length > 0);

  if (facts.length === 0 && lists.length === 0 && !o.deadline) return null;

  return (
    <aside
      className="my-8 rounded-lg border border-crimson/25 bg-crimson/[0.04] p-5 font-[family-name:var(--font-bengali)]"
      lang="bn"
    >
      <h2 className="text-lg font-bold text-crimson">এক নজরে</h2>

      {facts.length > 0 && (
        <dl className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {facts.map((f) => (
            <div key={f.label}>
              <dt className="text-xs font-semibold text-ink-soft">{f.label}</dt>
              <dd className="mt-0.5 text-sm font-semibold">{f.value}</dd>
            </div>
          ))}
        </dl>
      )}

      <div className="mt-4 rounded-md bg-white/70 px-4 py-3">
        <span className="text-xs font-semibold text-ink-soft">
          আবেদনের শেষ সময়
        </span>
        <p className="mt-0.5 text-base font-bold">
          {o.deadline || "সূত্রে উল্লেখ নেই — অফিশিয়াল পেজে দেখে নিন"}
        </p>
      </div>

      {lists.map((l) =>
        l.ordered ? (
          <div key={l.label} className="mt-5">
            <h3 className="text-sm font-bold">{l.label}</h3>
            <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-sm leading-relaxed">
              {l.items!.map((x, i) => (
                <li key={i}>{x}</li>
              ))}
            </ol>
          </div>
        ) : (
          <div key={l.label} className="mt-5">
            <h3 className="text-sm font-bold">{l.label}</h3>
            <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-relaxed">
              {l.items!.map((x, i) => (
                <li key={i}>{x}</li>
              ))}
            </ul>
          </div>
        ),
      )}

      {o.officialUrl && (
        <a
          href={o.officialUrl}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className="mt-5 inline-block rounded-md bg-crimson px-4 py-2 text-sm font-bold text-white"
        >
          অফিশিয়াল আবেদন পেজ →
        </a>
      )}

      {/* Deadlines and terms change without notice, and we are not the
          awarding body. Say so plainly rather than let a reader treat a news
          report as the application form. */}
      <p className="mt-4 text-xs leading-relaxed text-ink-soft">
        তথ্যগুলো সংবাদসূত্র থেকে নেওয়া। আবেদনের আগে অবশ্যই সংশ্লিষ্ট
        বিশ্ববিদ্যালয় বা বৃত্তি কর্তৃপক্ষের অফিশিয়াল ওয়েবসাইটে শর্ত ও
        সময়সীমা যাচাই করে নিন।
      </p>
    </aside>
  );
}
