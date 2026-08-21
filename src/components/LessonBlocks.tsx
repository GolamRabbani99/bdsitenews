import type { Article } from "@/lib/articles";

/**
 * ইংরেজি শিখুন lesson layout.
 *
 * Every English line is paired with its Bangla meaning, always — a beginner
 * who meets an unglossed English sentence stops reading, and the whole point
 * of the desk is that they finish the lesson.
 */
export function LessonBlocks({ article }: { article: Article }) {
  const l = article.lesson;
  if (!l) return null;

  return (
    <div className="font-[family-name:var(--font-bengali)]" lang="bn">
      {/* The formula, given the weight it deserves — this is the one thing
          a reader should be able to copy away from the lesson. */}
      {l.pattern && (
        <div className="my-7 rounded-lg bg-ink px-5 py-5 text-paper">
          <p className="text-xs font-semibold opacity-70">গঠন</p>
          <p className="mt-2 text-xl font-bold leading-relaxed">{l.pattern}</p>
        </div>
      )}

      {l.examples.length > 0 && (
        <section className="mt-8">
          <h2 className="border-l-4 border-crimson pl-3 text-lg font-bold">
            উদাহরণ
          </h2>
          <ul className="mt-4 space-y-4">
            {l.examples.map((e, i) => (
              <li key={i} className="rounded-md border border-rule px-4 py-3">
                <p className="text-[17px] font-semibold" lang="en">
                  {e.english}
                </p>
                <p className="mt-1 text-[15px] text-ink-soft">{e.bangla}</p>
                {e.note && (
                  <p className="mt-1.5 text-[13px] text-crimson">{e.note}</p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {l.mistakes.length > 0 && (
        <section className="mt-9">
          <h2 className="border-l-4 border-crimson pl-3 text-lg font-bold">
            যে ভুলটা বেশি হয়
          </h2>
          <ul className="mt-4 space-y-4">
            {l.mistakes.map((m, i) => (
              <li key={i} className="rounded-md bg-rule/30 px-4 py-3">
                <p className="text-[16px] text-ink-soft line-through" lang="en">
                  {m.wrong}
                </p>
                <p className="mt-1 text-[17px] font-bold text-crimson" lang="en">
                  {m.right}
                </p>
                <p className="mt-1.5 text-[14px]">{m.why}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {l.speakingTip && (
        <section className="mt-9 rounded-lg border border-crimson/25 bg-crimson/[0.04] px-5 py-4">
          <h2 className="text-base font-bold text-crimson">বলার সময় খেয়াল রাখুন</h2>
          <p className="mt-2 text-[15px] leading-relaxed">{l.speakingTip}</p>
        </section>
      )}

      {l.practice.length > 0 && (
        <section className="mt-9">
          <h2 className="border-l-4 border-crimson pl-3 text-lg font-bold">
            নিজে চেষ্টা করুন
          </h2>
          <ol className="mt-4 list-decimal space-y-2 pl-6 text-[16px] leading-relaxed">
            {l.practice.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
