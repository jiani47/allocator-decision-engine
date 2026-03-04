import { STEPS, useWizard } from "@/context/WizardContext"
import { cn } from "@/lib/utils"
import { Check } from "lucide-react"

export function StepIndicator() {
  const { step, highestStepReached, canNavigateTo, setStep } = useWizard()

  return (
    <nav className="mb-8 flex items-center">
      {STEPS.map((label, i) => {
        const isActive = i === step
        const isCompleted = i < highestStepReached
        const isReachable = canNavigateTo(i)
        const isLast = i === STEPS.length - 1

        return (
          <div key={label} className="flex items-center">
            <button
              disabled={!isReachable}
              onClick={() => isReachable && setStep(i)}
              className={cn(
                "flex items-center gap-2.5",
                isReachable && !isActive && "cursor-pointer",
                !isReachable && "cursor-default",
              )}
            >
              {/* Circle indicator — matches landmark stepper.tsx pattern */}
              <div
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                  isCompleted && "border-primary bg-primary",
                  isActive && !isCompleted && "border-primary",
                  !isActive && !isCompleted && "border-muted",
                )}
              >
                {isCompleted ? (
                  <Check className="h-4 w-4 text-primary-foreground" />
                ) : (
                  <span
                    className={cn(
                      "text-sm font-medium",
                      isActive ? "text-primary" : "text-muted-foreground",
                    )}
                  >
                    {i + 1}
                  </span>
                )}
              </div>

              {/* Label */}
              <span
                className={cn(
                  "hidden text-sm font-medium sm:inline",
                  isActive ? "text-foreground" : "text-muted-foreground",
                )}
              >
                {label}
              </span>
            </button>

            {/* Connector line */}
            {!isLast && (
              <div
                className={cn(
                  "mx-4 h-0.5 w-12",
                  isCompleted ? "bg-primary" : "bg-muted",
                )}
              />
            )}
          </div>
        )
      })}
    </nav>
  )
}
