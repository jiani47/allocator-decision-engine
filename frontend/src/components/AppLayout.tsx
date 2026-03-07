import { useState, useCallback } from "react"
import { useWizard } from "@/context/WizardContext"
import { AppSidebar, type View } from "@/components/AppSidebar"
import { PortfoliosPage } from "@/pages/PortfoliosPage"
import { AllocationsPage } from "@/pages/AllocationsPage"
import { FundsPage } from "@/pages/FundsPage"
import { BenchmarksPage } from "@/pages/BenchmarksPage"
import { SettingsPage } from "@/pages/SettingsPage"

const PAGE_COMPONENTS: Record<View, React.FC> = {
  portfolios: PortfoliosPage,
  funds: FundsPage,
  benchmarks: BenchmarksPage,
  settings: SettingsPage,
}

export function AppLayout() {
  const [view, setView] = useState<View>("portfolios")
  const { allocationActive, startAllocation } = useWizard()

  const handleNewAllocation = useCallback(() => {
    startAllocation()
  }, [startAllocation])

  const PageComponent = allocationActive ? AllocationsPage : PAGE_COMPONENTS[view]

  return (
    <div className="grid h-screen grid-cols-[auto_1fr] overflow-hidden">
      <AppSidebar view={view} onNavigate={setView} onNewAllocation={handleNewAllocation} />
      <main className="overflow-y-auto scrollbar-thin">
        <div className="mx-auto max-w-5xl px-8 py-8 animate-fade-in-up" key={allocationActive ? "allocation" : view}>
          <PageComponent />
        </div>
      </main>
    </div>
  )
}
