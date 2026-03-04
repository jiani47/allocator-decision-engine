import { useState, useCallback } from "react"
import { useWizard } from "@/context/WizardContext"
import { AppSidebar, type View } from "@/components/AppSidebar"
import { AllocationsPage } from "@/pages/AllocationsPage"
import { MandatesPage } from "@/pages/MandatesPage"
import { FundsPage } from "@/pages/FundsPage"
import { BenchmarksPage } from "@/pages/BenchmarksPage"
import { SettingsPage } from "@/pages/SettingsPage"

const PAGE_COMPONENTS: Record<View, React.FC> = {
  allocations: AllocationsPage,
  mandates: MandatesPage,
  funds: FundsPage,
  benchmarks: BenchmarksPage,
  settings: SettingsPage,
}

export function AppLayout() {
  const [view, setView] = useState<View>("allocations")
  const { startAllocation } = useWizard()
  const PageComponent = PAGE_COMPONENTS[view]

  const handleNewAllocation = useCallback(() => {
    startAllocation()
    setView("allocations")
  }, [startAllocation])

  return (
    <div className="grid h-screen grid-cols-[auto_1fr] overflow-hidden">
      <AppSidebar view={view} onNavigate={setView} onNewAllocation={handleNewAllocation} />
      <main className="overflow-y-auto scrollbar-thin">
        <div className="mx-auto max-w-5xl px-8 py-8 animate-fade-in-up" key={view}>
          <PageComponent />
        </div>
      </main>
    </div>
  )
}
