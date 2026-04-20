# 🎨 Design System Reference - Complete Color & Component Guide

## Color Palette

### Core Colors

#### Primary Accent
```
Name:     Primary Blue
Hex:      #3b82f6
RGB:      59, 130, 246
Usage:    Primary actions, active states, focus states
Example:  Buttons, active nav link, accent borders
```

#### Semantic Colors
```
Success:  #10b981 (Emerald Green)     → OK, Normal, Success status
Danger:   #ef4444 (Red)               → Critical, Error, Fail
Warning:  #f59e0b (Amber)             → High priority, Warning
Info:     #06b6d4 (Cyan)              → Medium, Secondary action
```

#### Secondary Accent
```
Purple:   #8b5cf6 → Complex operations, Priority actions
Green Light: #34d399 → Highlighting, Success feedback
Blue Light:  #60a5fa → Hover states, Glow effects
Red Light:   #f87171 → Danger hover states
```

### Background Colors

```
Base:     #0f1419  (Deep dark)     → Page background
Surface:  #1a1e2e  (Medium dark)   → Header, footer
Elevated: #242d3d  (Slightly lighter) → Sidebar, overlays
Card:     #15191e  (Very dark)     → Card backgrounds
Border:   #3c4556  (Medium gray)   → Borders, dividers
Text Primary: #f1f5f9 (Nearly white) → Main text
Text Secondary: #cbd5e1 (Light gray) → Secondary text
Text Muted: #94a3b8 (Medium gray)  → Inactive, disabled
```

---

## Component Styles

### KPI Cards

**Anatomy:**
```
┌─[GRADIENT BORDER]─────────────────┐
│                                    │
│  🎯 ICON                          │
│  LABEL (uppercase, small)          │
│  VALUE (2.2rem, bold)              │
│  UNIT (small, secondary)           │ 
│  ▓▓▓▓▓▓▓░░░░░░░ PROGRESS BAR      │
│                                    │
└────────────────────────────────────┘
```

**States:**
- Default: Subtle border, soft shadow
- Hover: Elevated (+4px), blue border, large shadow
- Alert-OK: Green top border
- Alert-Warning: Amber top border  
- Alert-Danger: Red top border

**Dimensions:**
- Min Width: 210px (auto-fill grid)
- Height: Auto
- Padding: 22px
- Border: 1px solid --border-light
- Radius: --radius-md (12px)
- Top Border: 3px gradient

---

### Badge Components

**Types:**
```
DANGER     ━║ Red      #ef4444
HIGH       ━║ Amber    #f59e0b
MEDIUM     ━║ Cyan     #06b6d4
LOW        ━║ Green    #10b981
NORMAL     ━║ Gray     #94a3b8
```

**Features:**
- Background: Semi-transparent color (20% opacity)
- Text color: Matching color (full opacity)
- Border: 1px matching color
- Box-shadow: Glow effect (8px rgba with 30% opacity)
- Animation: Pulse effect on update (0.5s)

**Example:**
```
.badge-danger {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border: 1px solid #ef4444;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.3);
}
```

---

### Progress Bars

**Design:**
```
Background: var(--bg-base)  [Dark container]
Fill:       Gradient        [Green → Cyan]
Height:     5px
Radius:     3px
Shadow:     Drop glow #10b981

Animation:  0.8s transition on value change
Easing:     cubic-bezier(0.4, 0, 0.2, 1)
```

**Variants:**
- Default: Green-to-Cyan gradient
- Network:  Blue-to-Purple gradient

---

### Buttons

**Primary Button:**
```
Background: Linear gradient (Blue → Light Blue)
Color:      White
Padding:    10px 18px
Radius:     8px
Weight:     Bold 700
Shadow:     0 4px 12px rgba(59, 130, 246, 0.3)
Hover:      Elevation +2px, Shadow increase
```

**Secondary Button:**
```
Background: Transparent
Border:     1px --border
Color:      White
Hover:      Background tint, border highlight
```

---

### Tables

**Header:**
```
Padding:     12px 16px
Background:  rgba(0, 0, 0, 0.2)
Border:      2px solid --border
Text:        Uppercase, 0.7rem, 800 weight
Color:       --text-muted
```

**Rows:**
```
Padding:     14px 16px
Border:      1px solid --border-light
Hover:       Background tint (blue 8% opacity)
Transition:  0.2s ease
```

**Status Colors:**
- Danger:  --accent-red (#ef4444)
- Warning: --accent-amber (#f59e0b)
- OK:      --accent-green (#10b981)
- Info:    --accent-cyan (#06b6d4)

---

### Modal/Dialog

**Structure:**
```
┌─ Backdrop ─────────────────────────────┐
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  ░┌─[MODAL WINDOW]──────────────────┐░ │
│  ░│ Title                     [✕]    │░ │
│  ░├────────────────────────────────┤░ │
│  ░│ Content message                 │░ │
│  ░├────────────────────────────────┤░ │
│  ░│ [Cancel]         [Confirm]      │░ │
│  ░└────────────────────────────────┘░ │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
└────────────────────────────────────────┘
```

**Styling:**
- Backdrop: rgba(0,0,0,0.7) + blur(5px)
- Card: Gradient (elevated → card)
- Border: 1px --border
- Radius: --radius-lg (16px)
- Shadow: 0 20px 60px rgba(0,0,0,0.5)
- Animation: slideIn 0.4s cubic-bezier

---

### Chat Widget

**Button:**
```
Size:        64x64px
Shape:       Circle (50% radius)
Background:  Linear gradient (blue → purple)
Border:      2px rgba(255,255,255,0.15)
Shadow:      0 8px 24px rgba(59,130,246,0.4)
Hover:       Scale 1.08, shadow increase, border glow
Transition:  0.2s ease
```

**Window:**
```
Size:        400x520px (mobile: 100%x60vh)
Position:    Fixed bottom-right
Background:  var(--bg-card)
Border:      1px --border
Radius:      12px (top), 0 (bottom on mobile)
Shadow:      0 16px 48px rgba(0,0,0,0.6)
Animation:   slideIn 0.3s, scale from 0.95
Z-index:     1000
```

---

## Spacing System

```
4px   - Smallest gaps
8px   - Small gaps
12px  - Default card padding
16px  - Standard padding
20px  - Large padding
28px  - Section padding
32px  - Page padding
```

## Typography

```
Font:       Inter, -apple-system, system-ui, sans-serif
Page:       14px (base)
H1/Title:   1.3rem, 700 weight, gradient text
Heading:    0.95rem, 700 weight
Label:      0.7rem, 600 weight, uppercase
Code:       0.8rem, monospace
Body:       0.9rem, 400 weight
```

## Shadow System

```
--shadow-sm:  0 2px 8px rgba(0, 0, 0, 0.15)   [Subtle]
--shadow-md:  0 4px 16px rgba(0, 0, 0, 0.25)  [Medium]
--shadow-lg:  0 8px 32px rgba(0, 0, 0, 0.4)   [Elevated]

Glow Shadows:
  Blue:   0 0 8px rgba(59, 130, 246, 0.3)
  Green:  0 0 8px rgba(16, 185, 129, 0.3)
  Red:    0 0 8px rgba(239, 68, 68, 0.3)
  Amber:  0 0 8px rgba(245, 158, 11, 0.3)
  Cyan:   0 0 8px rgba(6, 182, 212, 0.3)
```

## Border Radius

```
--radius-sm: 8px    [Small rounded corners]
--radius-md: 12px   [Medium, standard]
--radius-lg: 16px   [Large, modals]
Circle:      50%    [Buttons, avatars]
```

## Transitions

```
--transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1)

Fast:     0.2s
Standard: 0.3s
Slow:     0.5s - 0.8s (value animations)
```

---

## Gradient Examples

**Primary Accent:**
```css
background: linear-gradient(135deg, #3b82f6, #0ea5e9);
```

**Success:**
```css
background: linear-gradient(90deg, #10b981, #34d399);
```

**Danger:**
```css
background: linear-gradient(90deg, #ef4444, #f87171);
```

**Warning:**
```css
background: linear-gradient(90deg, #f59e0b, #fbbf24);
```

**Complex:**
```css
background: linear-gradient(135deg, 
  rgba(59, 130, 246, 0.15) 0%,  /* Blue tint */
  rgba(16, 185, 129, 0.15) 100% /* Green tint */
);
```

---

## Responsive Breakpoints

```
Desktop:   > 1200px   [2+ column layouts]
Tablet:    768-1200px [1-2 columns]
Mobile:    < 768px    [Full width, no sidebar]
```

**Key Changes at 768px:**
- Sidebar hides (transform: translateX(-100%))
- Main content full width
- Cards become single column
- Chat window mobile (full height)
- Header padding reduced

---

## Animation Timing Functions

```
Easing:     cubic-bezier(0.4, 0, 0.2, 1)  [Standard]
In-Out:     cubic-bezier(0.4, 0, 0.2, 1) 
Bounce:     cubic-bezier(0.175, 0.885, 0.32, 1.275)

Durations:
  Fast:     0.2s  [Hover, status changes]
  Standard: 0.3s  [Transitions]
  Slow:     0.5s  [Value animations]
  Very Slow: 0.8s [Smooth number updates]
  Extended: 1.0s  [Loading, complex]
```

---

## Icon Sizes

```
Sidebar Nav:  20x20px
Card Icons:   32x32px  (hover glow added)
Badges:       1.1rem   (emoji/icons)
Buttons:      Standard sizing
Spinners:     20x20px (regular), 14x14px (small)
```

---

## Z-Index Scale

```
1:    Default (stacked in order)
10:   Loading overlays, spinners
50:   Page header (sticky)
100:  Sidebar
1000: Modal, chat widget, tooltips
2000: Top-level alerts
3000: Toast notifications
```

---

## Hover Effects

```
Cards:        translateY(-4px), shadow increase
Icons:        Color shift, glow add
Buttons:      Brightness increase, translateY
Navigation:   Background tint, color change
Tables:       Row background tint
Badges:       Brightness increase
```

---

## Active/Focus States

```
Links:        Color change to --accent-blue
Inputs:       Border-color: --accent-blue, glow shadow
Buttons:      Brightness filter + translateY
Nav items:    Left border bar appears
```

---

## Loading States

**Spinner:**
```
20x20px circle
Border: 3px solid --border
Top border: Accent color
Animation: 1s linear infinite rotation
```

**Skeleton:**
```
Background: Gradient shimmer animation
Size: Flexible
Radius: --radius-sm
Animation: 1.5s shimmer infinity
```

**Override:**
```
Container: opacity 0.6
Pointer events: disabled
Central spinner overlay
```

---

## Accessibility

```
Color Contrast:
  Text on Background:  4.5:1 (WCAG AA)
  Accent on Background: 3:1+ (WCAG AA)

Font Sizes:
  Minimum: 12px (labels)
  Standard: 14px
  Readable: 16px+ on mobile

Focus Indicators:
  Outline: 2px solid --accent-blue
  Offset: 2px
  Visible on keyboard navigation
```

---

## Performance Notes

✅ GPU-accelerated:
  - transform: translateY()
  - opacity transitions
  - backdrop-filter effects

❌ Avoid:
  - width/height animations (causes reflow)
  - left/top animations (use transform instead)
  - shadow animations (expensive)
  - box-shadow on frequent updates

---

This design system ensures consistency, professionalism, and excellent user experience across your Software Aging Analyzer dashboard!
