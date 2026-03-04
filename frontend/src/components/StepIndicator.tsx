import { STEPS, useWizard } from "@/context/WizardContext"
import { cn } from "@/lib/utils"

export function StepIndicator() {
  const { step } = useWizard()

  return (
    <nav className="flex items-center gap-2 mb-8">
      {STEPS.map((label, i) => (
        <div key={label} className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium",
                i < step && "bg-primary text-primary-foreground",
                i === step && "bg-primary text-primary-foreground ring-2 ring-ring ring-offset-2",
                i > step && "bg-muted text-muted-foreground",
              )}
            >
              {i + 1}
            </div>
            <span
              className={cn(
                "text-sm hidden sm:inline",
                i === step ? "font-medium" : "text-muted-foreground",
              )}
            >
              {label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div
              className={cn(
                "h-px w-8",
                i < step ? "bg-primary" : "bg-border",
              )}
            />
          )}
        </div>
      ))}
    </nav>
  )
}
