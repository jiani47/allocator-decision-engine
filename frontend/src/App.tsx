import { WizardProvider } from "@/context/WizardContext"
import { WizardShell } from "@/components/WizardShell"
import { ErrorBoundary } from "@/components/ErrorBoundary"

export default function App() {
  return (
    <ErrorBoundary>
      <WizardProvider>
        <WizardShell />
      </WizardProvider>
    </ErrorBoundary>
  )
}
