import { useState, useEffect } from "react"
import { useWizard, STEPS } from "@/context/WizardContext"
import { cn } from "@/lib/utils"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  ClipboardList,
  Upload,
  BarChart3,
  FileText,
  PanelLeftClose,
  PanelLeft,
  Check,
  type LucideIcon,
} from "lucide-react"

const STEP_ICONS: LucideIcon[] = [ClipboardList, Upload, BarChart3, FileText]

const STORAGE_KEY = "equi-sidebar-collapsed"

export function AppSidebar() {
  const { step, setStep, canNavigateTo, highestStepReached } = useWizard()
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === "true"
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(collapsed))
    } catch {
      // ignore
    }
  }, [collapsed])

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "flex h-screen flex-col border-r border-sidebar-border bg-sidebar",
          "transition-[width] duration-200 ease-in-out overflow-hidden",
          collapsed ? "w-[56px]" : "w-60",
        )}
      >
        {/* Brand */}
        <div
          className={cn(
            "flex h-14 shrink-0 items-center border-b border-sidebar-border",
            collapsed ? "justify-center px-2" : "px-4",
          )}
        >
          {collapsed ? (
            <span className="text-lg font-bold text-sidebar-foreground">E</span>
          ) : (
            <span className="text-lg font-bold text-sidebar-foreground">Equi</span>
          )}
        </div>

        {/* Step Navigation */}
        <nav className="flex-1 space-y-1 px-2 py-4">
          {STEPS.map((label, i) => {
            const Icon = STEP_ICONS[i]
            const isActive = i === step
            const isCompleted = i < highestStepReached
            const isReachable = canNavigateTo(i)

            const navItem = (
              <button
                key={label}
                disabled={!isReachable}
                onClick={() => isReachable && setStep(i)}
                className={cn(
                  "relative flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium",
                  "transition-colors duration-150",
                  isActive && "bg-sidebar-accent text-sidebar-accent-foreground",
                  !isActive && isReachable && "text-sidebar-foreground hover:bg-sidebar-accent/50",
                  !isReachable && "cursor-not-allowed text-muted-foreground opacity-40",
                  collapsed && "justify-center px-0",
                )}
              >
                <div className="relative shrink-0">
                  <Icon className="h-[18px] w-[18px]" />
                  {isCompleted && (
                    <Check className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-sidebar text-green-600" />
                  )}
                </div>
                {!collapsed && <span className="truncate">{label}</span>}
              </button>
            )

            if (collapsed) {
              return (
                <Tooltip key={label}>
                  <TooltipTrigger asChild>{navItem}</TooltipTrigger>
                  <TooltipContent side="right" sideOffset={8}>
                    {label}
                  </TooltipContent>
                </Tooltip>
              )
            }
            return navItem
          })}
        </nav>

        {/* Collapse toggle */}
        <div className="shrink-0 border-t border-sidebar-border p-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={() => setCollapsed((c) => !c)}
                className={cn(
                  "flex w-full items-center rounded-md p-2 text-sidebar-foreground transition-colors hover:bg-sidebar-accent/50",
                  collapsed ? "justify-center" : "gap-2 px-3",
                )}
              >
                {collapsed ? (
                  <PanelLeft className="h-4 w-4" />
                ) : (
                  <>
                    <PanelLeftClose className="h-4 w-4" />
                    <span className="text-sm font-normal">Collapse</span>
                  </>
                )}
              </button>
            </TooltipTrigger>
            {collapsed && (
              <TooltipContent side="right" sideOffset={8}>
                Expand sidebar
              </TooltipContent>
            )}
          </Tooltip>
        </div>
      </aside>
    </TooltipProvider>
  )
}
