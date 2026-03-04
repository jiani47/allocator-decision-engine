import { useWizard } from "@/context/WizardContext"
import { AppSidebar } from "@/components/AppSidebar"
import { MandateForm } from "@/steps/MandateForm"
import { UploadReview } from "@/steps/UploadReview"
import { RankingView } from "@/steps/RankingView"
import { MemoExport } from "@/steps/MemoExport"

const STEP_COMPONENTS = [MandateForm, UploadReview, RankingView, MemoExport]

export function AppLayout() {
  const { step } = useWizard()
  const StepComponent = STEP_COMPONENTS[step]

  return (
    <div className="grid h-screen grid-cols-[auto_1fr] overflow-hidden">
      <AppSidebar />
      <main className="overflow-y-auto scrollbar-thin">
        <div className="mx-auto max-w-5xl px-8 py-8 animate-fade-in-up" key={step}>
          <StepComponent />
        </div>
      </main>
    </div>
  )
}
