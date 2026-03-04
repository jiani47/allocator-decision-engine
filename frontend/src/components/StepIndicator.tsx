import { STEPS, useWizard } from "@/context/WizardContext"
import { cn } from "@/lib/utils"
import { Check } from "lucide-react"

export function StepIndicator() {
  const { step, highestStepReached, canNavigateTo, setStep } = useWizard()

  return (
    <nav className="flex items-center gap-1 mb-8">
      {STEPS.map((label, i) => {
        const isActive = i === step
        const isCompleted = i < highestStepReached
        const isReachable = canNavigateTo(i)

        return (
          <div key={label} className="flex items-center gap-1">
            <button
              disabled={!isReachable}
              onClick={() => isReachable && setStep(i)}
              className={cn(
                "flex items-center gap-2 rounded-full px-3 py-1.5 text-sm transition-colors",
                isActive && "bg-primary text-primary-foreground",
                !isActive && isCompleted && "bg-muted text-foreground hover:bg-muted/80 cursor-pointer",
                !isActive && !isCompleted && !isReachable && "text-muted-foreground cursor-default",
                !isActive && !isCompleted && isReachable && "text-muted-foreground hover:bg-muted cursor-pointer",
              )}
            >
              <span
                className={cn(
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium",
                  isActive && "bg-primary-foreground/20",
                  isCompleted && !isActive && "bg-primary/10",
                  !isActive && !isCompleted && "bg-muted",
                )}
              >
                {isCompleted && !isActive ? (
                  <Check className="h-3.5 w-3.5" />
                ) : (
                  i + 1
                )}
              </span>
              <span className="hidden sm:inline font-medium">{label}</span>
            </button>
            {i < STEPS.length - 1 && (
              <div
                className={cn(
                  "h-px w-6",
                  i < highestStepReached ? "bg-primary/30" : "bg-border",
                )}
              />
            )}
          </div>
        )
      })}
    </nav>
  )
}
