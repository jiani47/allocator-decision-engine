import { PageHeader } from "@/components/PageHeader"

export function MandatesPage() {
  return (
    <div>
      <PageHeader
        title="Mandates"
        description="Saved constraint templates for reuse across allocations."
      />
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-sm text-muted-foreground">No saved mandates yet.</p>
      </div>
    </div>
  )
}
