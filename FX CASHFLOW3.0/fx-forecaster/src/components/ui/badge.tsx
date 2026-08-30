import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center px-2 py-0.5 text-xs font-mono font-medium border transition-colors focus:outline-none",
  {
    variants: {
      variant: {
        default: "border-[#18181B] bg-[#18181B] text-[#FAF9F5]",
        outline: "border-[#E4E2D9] text-[#18181B] bg-[#F9F8F5]",
        secondary: "border-[#DCD9CE] bg-[#F4F3EE] text-[#71717A]",
        caution: "border-[#B45309] bg-[#FEF3C7]/40 text-[#B45309]",
        danger: "border-[#B91C1C] bg-[#FEE2E2]/40 text-[#B91C1C]",
        protected: "border-[#047857] bg-[#D1FAE5]/40 text-[#047857]",
        accent: "border-[#2563EB] bg-[#DBEAFE]/40 text-[#1D4ED8]",
      },
      shape: {
        sharp: "rounded-none",
        subtle: "rounded-sm",
        pill: "rounded-full",
      },
    },
    defaultVariants: {
      variant: "default",
      shape: "subtle",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, shape, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant, shape }), className)} {...props} />
}

export { Badge, badgeVariants }
