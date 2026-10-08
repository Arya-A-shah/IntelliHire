// Turn rows into a CSV file and make the browser download it.
// Used by the Export buttons (they previously had no onClick at all).

function cell(value) {
  const text = value === null || value === undefined ? "" : String(value);
  // Quote cells containing commas, quotes or line breaks; double inner quotes.
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function downloadCsv(filename, columns, rows) {
  const lines = [
    columns.map((c) => cell(c.label)).join(","),
    ...rows.map((row) => columns.map((c) => cell(c.value(row))).join(",")),
  ];
  // A byte-order mark ("\uFEFF") makes Excel read UTF-8 names (e.g. accents) correctly
  const blob = new Blob(["\uFEFF" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const candidateCsvColumns = [
  { label: "Name", value: (a) => a.candidate?.name },
  { label: "Email", value: (a) => a.candidate?.email },
  { label: "Job", value: (a) => a.job?.title },
  { label: "Stage", value: (a) => a.status },
  { label: "Match score (%)", value: (a) => (a.match_score ?? "") },
  { label: "Applied", value: (a) => (a.applied_at ? new Date(a.applied_at).toLocaleDateString() : "") },
  { label: "Resume", value: (a) => a.resume_url },
];
