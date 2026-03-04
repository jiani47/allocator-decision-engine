import { WizardProvider } from "@/context/WizardContext"
import { AppLayout } from "@/components/AppLayout"
import { ErrorBoundary } from "@/components/ErrorBoundary"

export default function App() {
  return (
    <ErrorBoundary>
      <WizardProvider>
        <AppLayout />
      </WizardProvider>
    </ErrorBoundary>
  )
}
