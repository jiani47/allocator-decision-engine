import { PageHeader } from "@/components/PageHeader"

export function SettingsPage() {
  return (
    <div>
      <PageHeader
        title="Settings"
        description="Application configuration and preferences."
      />
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-sm text-muted-foreground">Settings coming soon.</p>
      </div>
    </div>
  )
}
