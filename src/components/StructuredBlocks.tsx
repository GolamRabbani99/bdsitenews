import type { Article } from "@/lib/articles";

/**
 * The blocks that differentiate this paper: a reader gets the event, then
 * immediately what it means for them, then how it came about — and, where a
 * viral claim is involved, a plain verdict. Designed to be scannable on a
 * phone, which is where nearly all Bangladeshi readers arrive.
 */

const VERDICT_STYLE: Record<string, string> = {
  সত্য: "bg-[#1a6b3c] text-white",
  মিথ্যা: "bg-crimson text-white",
  "আংশিক সত্য": "bg-[#9a6b12] text-white",
  "যাচাই করা যায়নি": "bg-ink-soft text-white",
};

export function FactCheckBox({
  factcheck,
}: {
  factcheck: NonNullable<Article["factcheck"]>;
}) {
  const style = VERDICT_STYLE[factcheck.verdict] ?? "bg-ink text-white";
  return (
    <section className="mt-7 border-2 border-ink font-[family-name:var(--font-bengali)]">
      <div className="flex flex-wrap items-center gap-2 border-b border-rule bg-rule/40 px-4 py-2">
        <span className="text-xs font-bold tracking-widest">🔍 যাচাই</span>
        <span className={`px-2.5 py-0.5 text-xs font-bold ${style}`}>
          {factcheck.verdict}
        </span>
      </div>
      <div className="px-4 py-3">
        <p className="text-xs font-semibold text-ink-soft">যে দাবিটি ছড়িয়েছে</p>
        <p lang="bn" className="mt-1 text-[15px] leading-relaxed">
          {factcheck.claim}
        </p>
      </div>
    </section>
  );
}

export function ImpactBox({ impact }: { impact: string[] }) {
  return (
    <section className="mt-7 border-l-4 border-crimson bg-rule/25 px-4 py-4 font-[family-name:var(--font-bengali)]">
      <h2 className="text-sm font-bold tracking-wide">
        এতে সাধারণ মানুষের কী বদলাবে
      </h2>
      {impact.map((p, i) => (
        <p key={i} lang="bn" className="mt-2 text-[16px] leading-loose">
          {p}
        </p>
      ))}
    </section>
  );
}

export function ContextBox({ context }: { context: string[] }) {
  return (
    <section className="mt-7 border-t border-rule pt-4 font-[family-name:var(--font-bengali)]">
      <h2 className="text-sm font-bold tracking-wide text-ink-soft">
        প্রেক্ষাপট — এর পেছনে যা ঘটেছিল
      </h2>
      {context.map((p, i) => (
        <p key={i} lang="bn" className="mt-2 text-[16px] leading-loose">
          {p}
        </p>
      ))}
    </section>
  );
}

/** The ব্যাখ্যা format: the questions a reader actually has, answered. */
export function ExplainerQA({
  questions,
}: {
  questions: NonNullable<Article["questions"]>;
}) {
  return (
    <div className="mt-7 font-[family-name:var(--font-bengali)]">
      {questions.map((q, i) => (
        <section
          key={i}
          className="mt-6 border-t border-rule pt-5 first:mt-0 first:border-0 first:pt-0"
        >
          <h2
            lang="bn"
            className="flex gap-2.5 text-[19px] font-bold leading-snug"
          >
            <span className="mt-0.5 shrink-0 bg-crimson px-2 py-0.5 text-xs font-bold text-paper">
              {i + 1}
            </span>
            <span>{q.question}</span>
          </h2>
          {q.answer.map((p, j) => (
            <p key={j} lang="bn" className="mt-3 text-[17px] leading-loose">
              {p}
            </p>
          ))}
        </section>
      ))}
    </div>
  );
}

/** Small badge shown on cards so readers can spot explained stories in a list. */
export function StructureBadges({ article }: { article: Article }) {
  const badges: string[] = [];
  if (article.questions?.length) badges.push("🧠 ব্যাখ্যা");
  if (article.factcheck) badges.push("🔍 যাচাই");
  if (article.impact?.length) badges.push("💡 কী বদলাবে");
  if (badges.length === 0) return null;
  return (
    <span className="ml-2 inline-flex gap-1.5 align-middle">
      {badges.map((b) => (
        <span
          key={b}
          className="bg-ink/90 px-1.5 py-0.5 text-[10px] font-semibold text-paper"
        >
          {b}
        </span>
      ))}
    </span>
  );
}
