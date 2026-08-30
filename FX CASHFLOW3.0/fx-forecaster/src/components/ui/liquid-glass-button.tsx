"use client"
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center cursor-pointer justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-zinc-900 text-white hover:bg-zinc-800",
        destructive: "bg-red-700 text-white hover:bg-red-800",
        cool: "border border-zinc-300 bg-white text-zinc-900 shadow-sm hover:bg-zinc-50",
        outline: "border border-zinc-300 bg-transparent hover:bg-zinc-100 text-zinc-900",
        secondary: "bg-zinc-200 text-zinc-900 hover:bg-zinc-300",
        ghost: "hover:bg-zinc-100 text-zinc-900",
        link: "text-zinc-900 underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-10 rounded-md px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

const liquidbuttonVariants = cva(
  "inline-flex items-center transition-colors justify-center cursor-pointer gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-[color,box-shadow] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-zinc-400",
  {
    variants: {
      variant: {
        default: "bg-transparent hover:scale-[1.02] duration-200 transition text-zinc-900",
        destructive: "bg-red-700 text-white hover:bg-red-800",
        outline: "border border-zinc-300 bg-white hover:bg-zinc-50",
        secondary: "bg-zinc-100 text-zinc-900 hover:bg-zinc-200",
        ghost: "hover:bg-zinc-100 text-zinc-900",
        link: "text-zinc-900 underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 text-xs px-3",
        lg: "h-10 rounded-md px-6",
        xl: "h-12 rounded-md px-8 text-base",
        xxl: "h-14 rounded-md px-10 text-lg font-medium",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "xl",
    },
  }
)

function LiquidButton({
  className,
  variant,
  size,
  asChild = false,
  children,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof liquidbuttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"
  return (
    <>
      <Comp
        data-slot="button"
        className={cn(
          "relative border border-zinc-300 bg-white/70 backdrop-blur-sm shadow-sm overflow-hidden",
          liquidbuttonVariants({ variant, size, className })
        )}
        {...props}
      >
        <div className="absolute top-0 left-0 z-0 h-full w-full rounded-md shadow-[inset_0_1px_1px_rgba(255,255,255,0.8),inset_0_-1px_1px_rgba(0,0,0,0.05)]" />
        <div
          className="absolute top-0 left-0 isolate -z-10 h-full w-full overflow-hidden rounded-md"
          style={{ backdropFilter: 'url("#container-glass")' }}
        />
        <div className="pointer-events-none z-10 font-medium flex items-center justify-center gap-2">
          {children}
        </div>
        <GlassFilter />
      </Comp>
    </>
  )
}

function GlassFilter() {
  return (
    <svg className="hidden">
      <defs>
        <filter
          id="container-glass"
          x="0%"
          y="0%"
          width="100%"
          height="100%"
          colorInterpolationFilters="sRGB"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.05 0.05"
            numOctaves="1"
            seed="1"
            result="turbulence"
          />
          <feGaussianBlur in="turbulence" stdDeviation="2" result="blurredNoise" />
          <feDisplacementMap
            in="SourceGraphic"
            in2="blurredNoise"
            scale="40"
            xChannelSelector="R"
            yChannelSelector="B"
            result="displaced"
          />
          <feGaussianBlur in="displaced" stdDeviation="2" result="finalBlur" />
          <feComposite in="finalBlur" in2="finalBlur" operator="over" />
        </filter>
      </defs>
    </svg>
  );
}

type ColorVariant = "default" | "primary" | "success" | "error" | "gold" | "bronze";

interface MetalButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ColorVariant;
}

const colorVariants: Record<
  ColorVariant,
  { outer: string; inner: string; button: string; textColor: string; textShadow: string }
> = {
  default: {
    outer: "bg-gradient-to-b from-[#18181B] to-[#71717A]",
    inner: "bg-gradient-to-b from-[#FAFAFA] via-[#3E3E3E] to-[#E5E5E5]",
    button: "bg-gradient-to-b from-[#27272A] to-[#18181B]",
    textColor: "text-white",
    textShadow: "[text-shadow:_0_-1px_0_rgb(0_0_0_/_80%)]",
  },
  primary: {
    outer: "bg-gradient-to-b from-[#1E293B] to-[#475569]",
    inner: "bg-gradient-to-b from-[#334155] via-[#1E293B] to-[#0F172A]",
    button: "bg-gradient-to-b from-[#334155] to-[#1E293B]",
    textColor: "text-white",
    textShadow: "[text-shadow:_0_-1px_0_rgb(15_23_42_/_80%)]",
  },
  success: {
    outer: "bg-gradient-to-b from-[#065F46] to-[#10B981]",
    inner: "bg-gradient-to-b from-[#D1FAE5] via-[#047857] to-[#065F46]",
    button: "bg-gradient-to-b from-[#059669] to-[#047857]",
    textColor: "text-white",
    textShadow: "[text-shadow:_0_-1px_0_rgb(6_78_59_/_80%)]",
  },
  error: {
    outer: "bg-gradient-to-b from-[#991B1B] to-[#EF4444]",
    inner: "bg-gradient-to-b from-[#FEE2E2] via-[#B91C1C] to-[#7F1D1D]",
    button: "bg-gradient-to-b from-[#DC2626] to-[#991B1B]",
    textColor: "text-white",
    textShadow: "[text-shadow:_0_-1px_0_rgb(153_27_27_/_80%)]",
  },
  gold: {
    outer: "bg-gradient-to-b from-[#854D0E] to-[#EAB308]",
    inner: "bg-gradient-to-b from-[#FEF08A] via-[#CA8A04] to-[#854D0E]",
    button: "bg-gradient-to-b from-[#D97706] to-[#B45309]",
    textColor: "text-white",
    textShadow: "[text-shadow:_0_-1px_0_rgb(133_77_14_/_80%)]",
  },
  bronze: {
    outer: "bg-gradient-to-b from-[#7C2D12] to-[#F97316]",
    inner: "bg-gradient-to-b from-[#FFEDD5] via-[#C2410C] to-[#7C2D12]",
    button: "bg-gradient-to-b from-[#EA580C] to-[#9A3412]",
    textColor: "text-white",
    textShadow: "[text-shadow:_0_-1px_0_rgb(124_45_18_/_80%)]",
  },
};

const metalButtonVariants = (
  variant: ColorVariant = "default",
  isPressed: boolean,
  isHovered: boolean,
  isTouchDevice: boolean
) => {
  const colors = colorVariants[variant];
  const transitionStyle = "all 200ms cubic-bezier(0.1, 0.4, 0.2, 1)";
  return {
    wrapper: cn("relative inline-flex transform-gpu rounded-md p-[1px] will-change-transform", colors.outer),
    wrapperStyle: {
      transform: isPressed ? "translateY(1.5px) scale(0.99)" : "translateY(0) scale(1)",
      boxShadow: isPressed ? "0 1px 2px rgba(0,0,0,0.15)" : isHovered && !isTouchDevice ? "0 4px 12px rgba(0,0,0,0.1)" : "0 2px 4px rgba(0,0,0,0.05)",
      transition: transitionStyle,
    },
    inner: cn("absolute inset-[1px] transform-gpu rounded-md will-change-transform", colors.inner),
    innerStyle: {
      transition: transitionStyle,
      filter: isHovered && !isPressed && !isTouchDevice ? "brightness(1.05)" : "none",
    },
    button: cn(
      "relative z-10 m-[1px] rounded-md inline-flex h-10 transform-gpu cursor-pointer items-center justify-center overflow-hidden px-5 py-2 text-sm font-mono tracking-tight will-change-transform outline-none select-none disabled:opacity-50 disabled:cursor-not-allowed",
      colors.button,
      colors.textColor,
      colors.textShadow
    ),
    buttonStyle: {
      transform: isPressed ? "scale(0.98)" : "scale(1)",
      transition: transitionStyle,
    },
  };
};

export const MetalButton = React.forwardRef<HTMLButtonElement, MetalButtonProps>(
  ({ children, className, variant = "default", ...props }, ref) => {
    const [isPressed, setIsPressed] = React.useState(false);
    const [isHovered, setIsHovered] = React.useState(false);
    const [isTouchDevice, setIsTouchDevice] = React.useState(false);
    React.useEffect(() => {
      setIsTouchDevice("ontouchstart" in window || navigator.maxTouchPoints > 0);
    }, []);
    const variants = metalButtonVariants(variant, isPressed, isHovered, isTouchDevice);
    return (
      <div className={variants.wrapper} style={variants.wrapperStyle}>
        <div className={variants.inner} style={variants.innerStyle}></div>
        <button
          ref={ref}
          className={cn(variants.button, className)}
          style={variants.buttonStyle}
          {...props}
          onMouseDown={() => setIsPressed(true)}
          onMouseUp={() => setIsPressed(false)}
          onMouseLeave={() => { setIsPressed(false); setIsHovered(false); }}
          onMouseEnter={() => { if (!isTouchDevice) setIsHovered(true); }}
          onTouchStart={() => setIsPressed(true)}
          onTouchEnd={() => setIsPressed(false)}
        >
          {children || "Execute"}
        </button>
      </div>
    );
  }
);
MetalButton.displayName = "MetalButton";

export { Button, buttonVariants, liquidbuttonVariants, LiquidButton };
