import { PageHeader } from "@/components/PageHeader"

export function BenchmarksPage() {
  return (
    <div>
      <PageHeader
        title="Benchmarks"
        description="Benchmark indices for comparing fund performance."
      />
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-sm text-muted-foreground">No saved benchmarks yet.</p>
      </div>
    </div>
  )
}
