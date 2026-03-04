import { useWizard } from "@/context/WizardContext"
import { StepIndicator } from "@/components/StepIndicator"
import { MandateForm } from "@/steps/MandateForm"
import { UploadReview } from "@/steps/UploadReview"
import { RankingView } from "@/steps/RankingView"
import { MemoExport } from "@/steps/MemoExport"

const STEP_COMPONENTS = [MandateForm, UploadReview, RankingView, MemoExport]

export function WizardShell() {
  const { step } = useWizard()
  const StepComponent = STEP_COMPONENTS[step]

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <StepIndicator />
        <StepComponent />
      </div>
    </div>
  )
}
