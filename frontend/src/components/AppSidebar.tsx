import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Button } from "@/components/ui/button"
import {
  Briefcase,


  TrendingUp,
  LineChart,
  Settings,
  PanelLeftClose,
  PanelLeft,
  Plus,
  type LucideIcon,
} from "lucide-react"

export type View = "portfolios" | "funds" | "benchmarks" | "settings"

interface NavItem {
  label: string
  icon: LucideIcon
  view: View
}

const NAV_ITEMS: NavItem[] = [
  { label: "Portfolios", icon: Briefcase, view: "portfolios" },
  { label: "Funds", icon: TrendingUp, view: "funds" },
  { label: "Benchmarks", icon: LineChart, view: "benchmarks" },
  { label: "Settings", icon: Settings, view: "settings" },
]

const STORAGE_KEY = "equi-sidebar-collapsed"

interface AppSidebarProps {
  view: View
  onNavigate: (view: View) => void
  onNewAllocation: () => void
}

export function AppSidebar({ view, onNavigate, onNewAllocation }: AppSidebarProps) {
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
            <span className="text-lg font-bold text-sidebar-foreground">A</span>
          ) : (
            <span className="text-sm font-semibold text-sidebar-foreground">Allocator Decision OS</span>
          )}
        </div>

        {/* New Allocation CTA */}
        <div className="px-2 pt-4 pb-2">
          {collapsed ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="icon"
                  className="w-full"
                  onClick={onNewAllocation}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right" sideOffset={8}>
                New Allocation
              </TooltipContent>
            </Tooltip>
          ) : (
            <Button
              className="w-full justify-start gap-2"
              onClick={onNewAllocation}
            >
              <Plus className="h-4 w-4" />
              New Allocation
            </Button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-2 py-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            const isActive = item.view === view

            const navItem = (
              <button
                key={item.view}
                onClick={() => onNavigate(item.view)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium",
                  "transition-colors duration-150",
                  isActive && "bg-sidebar-accent text-sidebar-accent-foreground",
                  !isActive && "text-sidebar-foreground hover:bg-sidebar-accent/50",
                  collapsed && "justify-center px-0",
                )}
              >
                <Icon className="h-[18px] w-[18px] shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </button>
            )

            if (collapsed) {
              return (
                <Tooltip key={item.view}>
                  <TooltipTrigger asChild>{navItem}</TooltipTrigger>
                  <TooltipContent side="right" sideOffset={8}>
                    {item.label}
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
