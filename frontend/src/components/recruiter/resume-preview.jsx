export function ResumePreview({ url }) {
  // Simple placeholder container for resume iframe or viewer integration
  return (
    <div className="rounded-xl border border-border/60 bg-background/40 h-[360px] lg:h-[520px] flex items-center justify-center text-sm text-muted-foreground">
      {url ? (
        <iframe
          src={url}
          title="Resume"
          className="w-full h-full rounded-xl"
          aria-label="Resume preview"
        />
      ) : (
        <div className="px-6 text-center">
          Resume preview is unavailable. Attach a PDF URL to view here.
        </div>
      )}
    </div>
  );
}
