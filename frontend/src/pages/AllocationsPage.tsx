import { useWizard } from "@/context/WizardContext"
import { PageHeader } from "@/components/PageHeader"
import { StepIndicator } from "@/components/StepIndicator"
import { Button } from "@/components/ui/button"
import { MandateForm } from "@/steps/MandateForm"
import { UploadReview } from "@/steps/UploadReview"
import { RankingView } from "@/steps/RankingView"
import { MemoExport } from "@/steps/MemoExport"
import { Plus } from "lucide-react"

const STEP_COMPONENTS = [MandateForm, UploadReview, RankingView, MemoExport]

export function AllocationsPage() {
  const { allocationActive, startAllocation, step } = useWizard()

  if (!allocationActive) {
    return (
      <div>
        <PageHeader
          title="Allocations"
          description="Fund allocation recommendations for IC approval."
        />
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
          <p className="mb-4 text-sm text-muted-foreground">No allocations yet.</p>
          <Button onClick={startAllocation}>
            <Plus className="mr-2 h-4 w-4" />
            New Allocation
          </Button>
        </div>
      </div>
    )
  }

  const StepComponent = STEP_COMPONENTS[step]

  return (
    <div>
      <h2 className="mb-2 text-lg font-semibold">New Allocation</h2>
      <StepIndicator />
      <StepComponent />
    </div>
  )
}
