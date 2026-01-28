// Theme System - Dark Grey with Blue Accent
// Inspired by Modal.com GPU Glossary design

export const colors = {
  // Backgrounds - Charcoal progression
  bg: {
    primary: '#0c0c0c',      // Deepest background (page)
    secondary: '#141414',    // Card backgrounds
    tertiary: '#1c1c1c',     // Elevated surfaces
    hover: '#242424',        // Hover states
    active: '#2c2c2c',       // Active/pressed states
  },

  // Borders
  border: {
    subtle: '#1f1f1f',       // Barely visible
    default: '#2a2a2a',      // Standard borders
    hover: '#3a3a3a',        // Hover state
    active: '#4a4a4a',       // Active state
  },

  // Text
  text: {
    primary: '#f5f5f5',      // Headlines, important
    secondary: '#a3a3a3',    // Body text
    tertiary: '#6b6b6b',     // Muted, hints
    inverse: '#0c0c0c',      // On light backgrounds
  },

  // Primary accent - Blue
  accent: {
    primary: '#3b82f6',      // Blue-500
    hover: '#2563eb',        // Blue-600
    muted: 'rgba(59, 130, 246, 0.15)',
    glow: 'rgba(59, 130, 246, 0.4)',
  },

  // Status colors
  status: {
    success: '#10b981',      // Emerald-500
    warning: '#f59e0b',      // Amber-500
    error: '#ef4444',        // Red-500
    info: '#3b82f6',         // Blue-500
  },

  // Chart colors
  chart: {
    up: '#22c55e',           // Green-500
    down: '#ef4444',         // Red-500
    volume: 'rgba(59, 130, 246, 0.3)',
    grid: '#1f1f1f',
  },
}

export const typography = {
  fontFamily: {
    sans: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
    mono: '"SF Mono", "Fira Code", "JetBrains Mono", monospace',
  },

  fontSize: {
    xs: '11px',
    sm: '13px',
    base: '14px',
    md: '16px',
    lg: '18px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '32px',
    '4xl': '40px',
  },

  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
}

export const spacing = {
  0: '0',
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
}

export const borderRadius = {
  sm: '4px',
  md: '6px',
  lg: '8px',
  xl: '12px',
  '2xl': '16px',
  full: '9999px',
}

// Pre-built component styles
export const componentStyles = {
  card: {
    default: {
      backgroundColor: colors.bg.secondary,
      border: `1px solid ${colors.border.default}`,
      borderRadius: borderRadius.xl,
    },
    elevated: {
      backgroundColor: colors.bg.tertiary,
      border: `1px solid ${colors.border.default}`,
      borderRadius: borderRadius.xl,
    },
  },

  button: {
    primary: {
      background: `linear-gradient(135deg, ${colors.accent.primary} 0%, ${colors.accent.hover} 100%)`,
      color: '#ffffff',
      border: 'none',
      borderRadius: borderRadius.lg,
      fontWeight: typography.fontWeight.semibold,
      boxShadow: `0 4px 20px ${colors.accent.glow}`,
    },
    secondary: {
      backgroundColor: 'transparent',
      color: colors.text.primary,
      border: `1px solid ${colors.border.hover}`,
      borderRadius: borderRadius.lg,
      fontWeight: typography.fontWeight.medium,
    },
    ghost: {
      backgroundColor: 'transparent',
      color: colors.text.secondary,
      border: 'none',
      borderRadius: borderRadius.lg,
    },
  },

  input: {
    default: {
      backgroundColor: colors.bg.secondary,
      color: colors.text.primary,
      border: `1px solid ${colors.border.default}`,
      borderRadius: borderRadius.lg,
      fontSize: typography.fontSize.base,
    },
  },
}

export default {
  colors,
  typography,
  spacing,
  borderRadius,
  componentStyles,
}
