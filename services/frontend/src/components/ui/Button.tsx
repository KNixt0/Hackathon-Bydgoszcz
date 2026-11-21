import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from "react";

type Variant = "default" | "primary" | "ghost";

interface StyleProps {
  variant?: Variant;
  size?: "md" | "sm";
  iconOnly?: boolean;
}

function classes({ variant = "default", size = "md", iconOnly }: StyleProps, extra?: string) {
  return ["btn", variant !== "default" && `btn--${variant}`, size === "sm" && "btn--sm", iconOnly && "btn--icon", extra]
    .filter(Boolean)
    .join(" ");
}

export function Button({ variant, size, iconOnly, className, type = "button", ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & StyleProps) {
  return <button type={type} className={classes({ variant, size, iconOnly }, className)} {...rest} />;
}

/** A link that looks like a button (downloads, external targets). */
export function ButtonLink({ variant, size, iconOnly, className, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & StyleProps) {
  return <a className={classes({ variant, size, iconOnly }, className)} {...rest} />;
}
