import { useEffect, useMemo, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { useCreateJob, useUpdateJob } from "@/hooks/useCreateJob";

const JOB_TYPES = ["Full-time", "Part-time", "Contract"];

// Pass `job` to edit an existing job instead of creating one.
// FIX: the "Edit" button on the Jobs table had no onClick; it now opens this.
export function PostJobDialog({ open, setOpen, onCreated, job = null }) {
  const isEdit = !!job;
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [type, setType] = useState("Full-time");
  const [tags, setTags] = useState([]);
  const [tagDraft, setTagDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const { mutateAsync: createJob, isPending: isCreating } = useCreateJob();
  const { mutateAsync: updateJob, isPending: isUpdating } = useUpdateJob();
  const isPending = isCreating || isUpdating;

  // Fill the form with the job's current values when editing
  useEffect(() => {
    if (open && job) {
      setTitle(job.title ?? "");
      setDescription(job.description ?? "");
      setLocation(job.location ?? "");
      setType(job.type ?? "Full-time");
      setTags(job.tags ?? []);
    }
  }, [open, job]);

  useEffect(() => {
    if (!open) {
      setTitle("");
      setDescription("");
      setLocation("");
      setType("Full-time");
      setTags([]);
      setTagDraft("");
      setSubmitting(false);
    }
  }, [open]);

  const canSubmit = useMemo(() => {
    return (
      title.trim().length >= 2 &&
      description.trim().length >= 10 &&
      location.trim().length >= 2 &&
      !!type
    );
  }, [title, description, location, type]);

  function addTagFromDraft() {
    const t = tagDraft.trim();
    if (!t) return;
    if (!tags.includes(t)) setTags((prev) => [...prev, t]);
    setTagDraft("");
  }

  async function onSubmit() {
    if (!canSubmit || isPending) return;

    const fields = {
      title: title.trim(),
      description: description.trim(),
      location: location.trim(),
      type,
      tags,
    };

    try {
      if (isEdit) {
        await updateJob({ id: job.id, ...fields });
        toast.success("Job updated");
        setOpen(false);
        return;
      }
      const data = await createJob(fields);
      toast.success("Job posted", {
        description: "Your job has been created successfully.",
      });
      setOpen(false);
      onCreated?.(data.insertedId);
    } catch (e) {
      toast.error(isEdit ? "Failed to update job" : "Failed to create job", {
        description: e.message || "Unknown error",
      });
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-xl rounded-2xl border border-border bg-card shadow-lg">
        <DialogHeader>
          <DialogTitle className="text-lg lg:text-xl">
            {isEdit ? "Edit Job" : "Post a Job"}
          </DialogTitle>
          <DialogDescription>
            Fill in the role details. All fields except Tags are required.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Senior ML Engineer"
              className="rounded-xl"
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Briefly describe the role, responsibilities, must-haves..."
              className="min-h-28 max-h-96 overflow-y-auto resize-none rounded-xl"
            />
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="location">Location</Label>
              <Input
                id="location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Remote, NYC, SF..."
                className="rounded-xl"
              />
            </div>

            <div className="grid gap-2">
              <Label>Type</Label>
              <Select value={type} onValueChange={(v) => setType(v)}>
                <SelectTrigger className="rounded-xl">
                  <SelectValue placeholder="Choose type" />
                </SelectTrigger>
                <SelectContent>
                  {JOB_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-2">
            <Label>Tags</Label>
            <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border/60 bg-background p-2">
              {tags.map((t) => (
                <Badge key={t} variant="secondary" className="rounded-full">
                  {t}
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="ml-1 h-5 w-5 rounded-full"
                    onClick={() =>
                      setTags((prev) => prev.filter((x) => x !== t))
                    }
                    aria-label={`Remove ${t}`}
                  >
                    ×
                  </Button>
                </Badge>
              ))}
              <Input
                value={tagDraft}
                onChange={(e) => setTagDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addTagFromDraft();
                  }
                }}
                placeholder="Add tag and press Enter"
                className="h-8 flex-1 min-w-[160px] border-none focus-visible:ring-0"
              />
            </div>
          </div>
        </div>

        <Separator className="my-1" />
        <DialogFooter>
          <Button
            variant="ghost"
            className="rounded-xl"
            onClick={() => setOpen(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            className="rounded-xl"
            onClick={onSubmit}
            disabled={!canSubmit || isPending}
          >
            {isPending ? "Saving…" : isEdit ? "Save changes" : "Post Job"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
