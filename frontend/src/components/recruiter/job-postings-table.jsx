import { useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useRecruiterJobs } from "@/hooks/useJobs";
import { JobPostingsSkeleton } from "../skeletons/JobPostingsSkeleton";

export function JobPostingsTable({ onViewCandidates, onPostJob, onEditJob }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");

  const { data: jobs = [], isLoading } = useRecruiterJobs();

  const filtered = useMemo(() => {
    return jobs.filter((j) => {
      const mQ = q
        ? j.title.toLowerCase().includes(q.toLowerCase()) ||
          j.location.toLowerCase().includes(q.toLowerCase())
        : true;
      const mS = status === "all" ? true : j.status.toLowerCase() === status;
      return mQ && mS;
    });
  }, [jobs, q, status]);

  if (isLoading) return <JobPostingsSkeleton />;

  return (
    <Card className="rounded-2xl border border-border/60 bg-card/60 backdrop-blur supports-[backdrop-filter]:bg-card/50 p-3 lg:p-4">
      {/* Search + Filters */}
      <div className="flex flex-col lg:flex-row lg:items-center gap-2 lg:gap-3 mb-3">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search jobs by title or location"
          className="rounded-xl"
        />
        <div className="flex gap-2">
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-40 rounded-xl">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="paused">Paused</SelectItem>
              <SelectItem value="closed">Closed</SelectItem>
            </SelectContent>
          </Select>
          <Button className="rounded-xl" onClick={onPostJob}>
            Post Job
          </Button>
        </div>
      </div>

      {/* Job List */}
      <div className="rounded-xl border border-border/60 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Applicants</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((j) => (
              <TableRow key={j.id}>
                <TableCell className="font-medium">{j.title}</TableCell>
                <TableCell className="text-muted-foreground">
                  {j.location}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {j.type}
                </TableCell>
                <TableCell>{j.applicants}</TableCell>
                <TableCell>
                  <Badge
                    variant={
                      j.status === "Open"
                        ? "default"
                        : j.status === "Paused"
                        ? "secondary"
                        : "outline"
                    }
                    className="rounded-full"
                  >
                    {j.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="ghost"
                      className="rounded-xl"
                      onClick={() => onEditJob?.(j)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="secondary"
                      className="rounded-xl"
                      onClick={() => onViewCandidates?.(j)}
                    >
                      View candidates
                    </Button>
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-1">
                    Updated {j.updatedAt}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}
