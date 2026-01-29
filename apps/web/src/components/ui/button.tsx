import * as React from "react"
import { cn } from "@/lib/utils"

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
  size?: 'default' | 'sm' | 'lg' | 'icon'
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', asChild = false, ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ocean-500 disabled:pointer-events-none disabled:opacity-50"
    
    const variants = {
      default: "bg-ocean-600 text-white shadow hover:bg-ocean-500",
      destructive: "bg-red-500 text-white shadow-sm hover:bg-red-600",
      outline: "border border-gray-700 bg-transparent shadow-sm hover:bg-gray-800 hover:text-white",
      secondary: "bg-gray-800 text-white shadow-sm hover:bg-gray-700",
      ghost: "hover:bg-gray-800 hover:text-white",
      link: "text-ocean-400 underline-offset-4 hover:underline",
    }
    
    const sizes = {
      default: "h-9 px-4 py-2",
      sm: "h-8 rounded-md px-3 text-xs",
      lg: "h-10 rounded-md px-8",
      icon: "h-9 w-9",
    }
    
    return (
      <button
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
