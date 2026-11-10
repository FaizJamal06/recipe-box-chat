/** Substitution diff (M5 stub): side-by-side ingredients/steps with removed struck through and added in green,
 *  "Verified" vs "Predicted" blocks. Renders a placeholder until T3 substitution ships. */
export function DiffView() {
  return (
    <section className="rounded-lg border border-dashed border-rule p-3 text-[12.5px] text-ink-soft">
      <h3 className="mb-1 font-display text-[14px] font-semibold text-ink">Substitution evidence</h3>
      Candidate · role · tier · support · lift · strength, with a side-by-side diff
      (<span className="line-through decoration-bad">removed</span> / <span className="text-ok">added</span>) — arrives with substitutions (M5).
    </section>
  );
}
