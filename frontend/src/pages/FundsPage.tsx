import { PageHeader } from "@/components/PageHeader"

export function FundsPage() {
  return (
    <div>
      <PageHeader
        title="Funds"
        description="Uploaded fund universes and performance data."
      />
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-sm text-muted-foreground">No fund data uploaded yet.</p>
      </div>
    </div>
  )
}
