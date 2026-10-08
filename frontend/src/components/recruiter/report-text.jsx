// Renders the Gemini report.
//
// FIX for the "gibberish report": Gemini writes Markdown (**bold**, "- " bullets,
// "## headings"). The drawer printed it as plain text, so the recruiter saw raw
// asterisks and hashes. This turns the common Markdown pieces into real HTML.
// It also copes with reports that came back wrapped in ```code fences``` or as
// a JSON string, which made older reports look like unparsed JSON.

function renderInline(text, keyPrefix) {
  // Split on **bold** and keep the bold parts (odd indexes after the split).
  return text.split(/\*\*(.+?)\*\*/g).map((part, i) =>
    i % 2 === 1 ? (
      <strong key={`${keyPrefix}-${i}`}>{part}</strong>
    ) : (
      part
    )
  );
}

function normalize(raw) {
  let text = String(raw ?? "").trim();

  // Strip ```markdown ... ``` or ```json ... ``` fences.
  const fence = text.match(/^```[a-zA-Z]*\n([\s\S]*?)\n?```$/);
  if (fence) text = fence[1].trim();

  // A JSON report: pull out the text field, or join its string values.
  if (text.startsWith("{") || text.startsWith('"')) {
    try {
      const parsed = JSON.parse(text);
      if (typeof parsed === "string") return parsed;
      const field =
        parsed.report ?? parsed.summary ?? parsed.text ?? parsed.content;
      if (typeof field === "string") return field;
      return Object.entries(parsed)
        .map(([k, v]) => `**${k}:** ${typeof v === "string" ? v : JSON.stringify(v)}`)
        .join("\n\n");
    } catch {
      // not JSON after all: show as text
    }
  }
  return text;
}

export function ReportText({ text }) {
  const blocks = normalize(text).split(/\n\s*\n/); // paragraphs

  return (
    <div className="space-y-3 text-sm leading-relaxed">
      {blocks.map((block, b) => {
        const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
        if (lines.length === 0) return null;

        // A block made only of "- item" / "* item" / "1. item" lines -> list
        const isList = lines.every((l) => /^([-*•]|\d+\.)\s+/.test(l));
        if (isList) {
          return (
            <ul key={b} className="list-disc pl-5 space-y-1">
              {lines.map((l, i) => (
                <li key={i}>
                  {renderInline(l.replace(/^([-*•]|\d+\.)\s+/, ""), `${b}-${i}`)}
                </li>
              ))}
            </ul>
          );
        }

        return lines.map((l, i) => {
          const heading = l.match(/^#{1,6}\s+(.*)$/);
          if (heading) {
            return (
              <p key={`${b}-${i}`} className="font-semibold">
                {renderInline(heading[1], `${b}-${i}`)}
              </p>
            );
          }
          return <p key={`${b}-${i}`}>{renderInline(l, `${b}-${i}`)}</p>;
        });
      })}
    </div>
  );
}
