---
name: Telkom Enterprise Core
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f4'
  surface-container: '#eeeeee'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1a1c1c'
  on-surface-variant: '#5e3f3a'
  inverse-surface: '#2f3131'
  inverse-on-surface: '#f0f1f1'
  outline: '#926e69'
  outline-variant: '#e8bdb6'
  surface-tint: '#c00000'
  primary: '#9e0000'
  on-primary: '#ffffff'
  primary-container: '#cc0000'
  on-primary-container: '#ffdad4'
  inverse-primary: '#ffb4a8'
  secondary: '#5d5f5f'
  on-secondary: '#ffffff'
  secondary-container: '#dcdddd'
  on-secondary-container: '#5f6161'
  tertiary: '#4d4c4c'
  on-tertiary: '#ffffff'
  tertiary-container: '#656464'
  on-tertiary-container: '#e4e1e1'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  background: '#f9f9f9'
  on-background: '#1a1c1c'
  surface-variant: '#e2e2e2'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  title-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  data-table:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  display-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  sidebar_width: 240px
  container_margin: 32px
  gutter: 24px
  stack_sm: 8px
  stack_md: 16px
  stack_lg: 24px
---

## Brand & Style

This design system is engineered for high-stakes enterprise productivity 
within Telkom Indonesia's ecosystem. The brand personality is authoritative, 
precise, and systematic, prioritizing functional efficiency over decorative flair.

The aesthetic follows a Corporate / Modern direction with heavy emphasis on 
Minimalism. Generous whitespace reduces cognitive load for employees managing 
complex data. Key visual markers: razor-sharp alignment, deliberate use of 
primary brand red for action only, structured information hierarchy.

---

## Colors

The palette is strictly functional. Telkom Red (#CC0000) is used exclusively 
for primary actions, critical alerts, and brand signifiers.

- Primary: #CC0000 — high-priority interaction points and brand identity
- Background: #F9F9F9 — main app canvas
- Surface: #FFFFFF — cards, tables, modals
- Body text: #1A1C1C — primary readable content
- Subtle stroke: #E0E0E0 — table borders, dividers
- Muted label: #666666 — table column headers, secondary text

---

## Typography

Dual-font approach: Plus Jakarta Sans for headlines, Inter for body and data.

| Token        | Font              | Size | Weight | Line Height |
|--------------|-------------------|------|--------|-------------|
| display-lg   | Plus Jakarta Sans | 32px | 700    | 40px        |
| headline-md  | Plus Jakarta Sans | 24px | 600    | 32px        |
| title-sm     | Plus Jakarta Sans | 18px | 600    | 24px        |
| body-lg      | Inter             | 16px | 400    | 24px        |
| body-md      | Inter             | 14px | 400    | 20px        |
| label-caps   | Inter             | 12px | 600    | 16px        |
| data-table   | Inter             | 13px | 400    | 18px        |

Column headers: label-caps in #666666.
Numeric data: tabular-lining figures.

---

## Layout & Spacing

Fixed Sidebar + Fluid Content model.

- Sidebar: 240px fixed left, persistent across all pages
- Main canvas: fluid, 32px outer margin (left+right), 16px on mobile
- Grid: 12 columns within content area
- Base unit: 8px — all spacing is a multiple of 8
- Breakpoint: 768px — sidebar collapses to hamburger, cards stack vertically

Spacing scale:
- stack_sm: 8px
- stack_md: 16px
- stack_lg: 24px
- gutter: 24px
- container_margin: 32px

---

## Elevation & Depth

No shadows. Depth via tonal layering only.

- Level 0 (Background): #F9F9F9
- Level 1 (Cards): #FFFFFF + 1px solid border #E0E0E0
- Level 2 (Dropdowns/Modals): #FFFFFF + 4px blur shadow opacity 5%

No gradients. No glass effects.

---

## Shapes

- Buttons, inputs, chips, small cards: 4px radius
- Large containers, modals: 8px radius
- NO pill/full-round buttons

---

## Components

### Buttons
- Primary: #CC0000 background, #FFFFFF text, 4px radius, 40px height
- Secondary: #FFFFFF background, 1px border #E0E0E0, #1A1C1C text
- Tertiary (Ghost): no background, no border, #CC0000 text
- All buttons: padding 12px 24px, body-md font

### Input Fields
- Height: 40px
- Border: 1px solid #D1D1D1, 4px radius
- Font: body-md (Inter 14px)
- Focus state: 1px border #CC0000 + 2px outer glow rgba(204,0,0,0.10)
- Placeholder: #999999

### Dropdown / Select
- Same sizing as input fields
- Chevron icon right-aligned
- Options list: Level 2 elevation, 4px radius

### Data Tables
- Header row: #FAFAFA background, label-caps, #666666 text
- Row height: 48px minimum
- Row border: 1px bottom #E0E0E0
- Hover: #F9F9F9 background
- Cell text: data-table (Inter 13px), #1A1C1C

### Chips & Status Badges
- Success: background #E6F4EA, text #1E7E34, 4px radius
- Pending: background #FFF8E1, text #B45309
- Critical: background #FDECEA, text #CC0000
- Font: label-caps, padding 4px 10px

### Navigation Sidebar
- Background: #FFFFFF
- Logo: top, 120px width, 24px margin top+left
- App title: "Productivity Suite", title-sm, #1A1C1C, 8px below logo
- Nav items: body-md, 48px height, 24px left padding
- Active state: 4px left border #CC0000 + background rgba(204,0,0,0.05)
- Inactive hover: background #F5F5F5
- Version label: bottom, label-caps, #999999, 24px margin

---

## Page Layouts

### Global Shell
```
┌─────────────────────────────────────────────────────┐
│  Sidebar (240px fixed)  │  Main Content (fluid)     │
│                         │  margin: 32px             │
│  [Logo]                 │                           │
│  Productivity Suite     │  [Page Content]           │
│                         │                           │
│  > Absensi              │                           │
│    Dashboard            │                           │
│    Artikel              │                           │
│                         │                           │
│  v1.0.0                 │                           │
└─────────────────────────────────────────────────────┘
```

---

### Page 1: Absensi

**Desktop layout (1280px)**
```
┌─ Main Content ──────────────────────────────────────┐
│  Page title: "Absensi"  [display-lg]    margin-b:24 │
│  Subtitle: "Catat kehadiran harian"     margin-b:32 │
│                                                     │
│  ┌─ Form Card (100%, max-width 560px) ────────────┐ │
│  │  padding: 32px                                 │ │
│  │                                                │ │
│  │  Nama Karyawan  [label-caps, margin-b:8]       │ │
│  │  [Dropdown — full width]          margin-b:16  │ │
│  │                                                │ │
│  │  Status         [label-caps, margin-b:8]       │ │
│  │  [Dropdown — full width]          margin-b:16  │ │
│  │  options: Hadir / Izin / Sakit / WFH           │ │
│  │                                                │ │
│  │  Catatan (Opsional) [label-caps, margin-b:8]   │ │
│  │  [Textarea — full width, 80px height]          │ │
│  │                                   margin-b:24  │ │
│  │                                                │ │
│  │  [SUCCESS BANNER — hidden by default]          │ │
│  │  bg:#E6F4EA, text:#1E7E34, 4px radius          │ │
│  │  "Absensi berhasil dicatat"       margin-b:16  │ │
│  │                                                │ │
│  │  [Button Primary — full width]                 │ │
│  │  "Catat Kehadiran"                             │ │
│  └────────────────────────────────────────────────┘ │
│                                       margin-t:32   │
│  ┌─ Audit Log ─────────────────────────────────── ┐ │
│  │  Section title: "Log Aktivitas"  [title-sm]    │ │
│  │                                   margin-b:16  │ │
│  │  [Data Table — full width]                     │ │
│  │  Columns: Timestamp | Nama | Status | Catatan  │ │
│  │  Widths:  180px     | auto | 120px  | auto     │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Mobile (<768px)**
- Form card: full width, margin 16px, padding 20px
- Table: horizontal scroll

---

### Page 2: Dashboard

**Desktop layout (1280px)**
```
┌─ Main Content ──────────────────────────────────────┐
│  "Dashboard"  [display-lg]                          │
│  [Filter bar — right aligned]             margin-b:32│
│  [Segmented control: Minggu Ini | Bulan Ini | Semua]│
│  height: 36px, border 1px #E0E0E0, 4px radius      │
│                                                     │
│  ── Row 1 ─────────────────────────────────────── ─│
│  ┌─ Bar Chart (12 col / full width) ──────────────┐ │
│  │  title: "Kehadiran Harian"  [title-sm]         │ │
│  │  height: 280px, padding: 24px                  │ │
│  │  Chart.js bar — color #CC0000                  │ │
│  └────────────────────────────────────────────────┘ │
│                                       margin-t:24   │
│  ── Row 2 (2 kolom, gutter 24px) ───────────────── │
│  ┌─ Donut Chart (6 col) ──────┐ ┌─ Line Chart ───┐ │
│  │ "Status Kehadiran"         │ │ "Tren Mingguan"│ │
│  │ height: 240px, pad: 24px   │ │ height: 240px  │ │
│  │ Chart.js doughnut          │ │ Chart.js line  │ │
│  │ Legend below chart         │ │ color #CC0000  │ │
│  └────────────────────────────┘ └────────────────┘ │
│                                       margin-t:24   │
│  ── Row 3 ──────────────────────────────────────── │
│  ┌─ Rekap Table (full width) ─────────────────────┐ │
│  │  title: "Rekap Per Karyawan"  [title-sm]       │ │
│  │  [Button Secondary "Export .xlsx" — top right] │ │
│  │                                                │ │
│  │  Columns:                                      │ │
│  │  Nama | Total Hadir | Izin | Sakit | Kluster   │ │
│  │  auto | 120px       | 80px | 80px  | 140px     │ │
│  │                                                │ │
│  │  Kluster column: Status Badge component        │ │
│  │  "Konsisten" → Success chip                    │ │
│  │  "Sering Izin" → Pending chip                  │ │
│  │  "Tidak Konsisten" → Critical chip             │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Mobile (<768px)**
- Row 2 charts: stack vertically
- Table: horizontal scroll

---

### Page 3: Artikel

**Desktop layout (1280px)**
```
┌─ Main Content ──────────────────────────────────────┐
│  "Artikel Generator"  [display-lg]      margin-b:32 │
│                                                     │
│  ┌─ 2 Column Layout (gutter: 24px) ───────────────┐ │
│  │                                                │ │
│  │  ┌─ Form (40% / ~480px) ──────────────────┐   │ │
│  │  │  padding: 32px                         │   │ │
│  │  │                                        │   │ │
│  │  │  Topik Artikel  [label-caps, mb:8]     │   │ │
│  │  │  [Input — full width]        mb:16     │   │ │
│  │  │                                        │   │ │
│  │  │  Keywords       [label-caps, mb:8]     │   │ │
│  │  │  [Input — full width]        mb:16     │   │ │
│  │  │  hint: "Pisahkan dengan koma"          │   │ │
│  │  │                                        │   │ │
│  │  │  Tone           [label-caps, mb:8]     │   │ │
│  │  │  [Segmented: Formal | Santai] mb:16    │   │ │
│  │  │                                        │   │ │
│  │  │  Panjang Artikel [label-caps, mb:8]    │   │ │
│  │  │  [Slider: Pendek–Sedang–Panjang] mb:24 │   │ │
│  │  │                                        │   │ │
│  │  │  [Button Primary — full width]         │   │ │
│  │  │  "Generate Artikel"                    │   │ │
│  │  └────────────────────────────────────────┘   │ │
│  │                                                │ │
│  │  ┌─ Preview (60% / ~680px) ───────────────┐   │ │
│  │  │  padding: 32px                         │   │ │
│  │  │                                        │   │ │
│  │  │  "Preview Artikel"  [title-sm, mb:16]  │   │ │
│  │  │  [Textarea read-only — full width]     │   │ │
│  │  │  height: 320px, bg:#FAFAFA             │   │ │
│  │  │                               mb:24    │   │ │
│  │  │  "Thumbnail"  [title-sm, mb:16]        │   │ │
│  │  │  [Image preview — full width]          │   │ │
│  │  │  aspect ratio 16:9, border 1px #E0E0E0 │   │ │
│  │  │  placeholder: #F5F5F5 + center icon    │   │ │
│  │  │                               mb:24    │   │ │
│  │  │  [Button Secondary "Download .docx"]   │   │ │
│  │  │  [Button Secondary "Download .jpg" ]   │   │ │
│  │  │  buttons: side by side, gap 12px       │   │ │
│  │  └────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Mobile (<768px)**
- 2 columns stack vertically: form atas, preview bawah
- Margin: 16px

---

## Responsive Rules Summary

| Element | Desktop (≥1280px) | Tablet (768px) | Mobile (<768px) |
|---|---|---|---|
| Sidebar | 240px fixed | 240px fixed | Hamburger collapse |
| Container margin | 32px | 24px | 16px |
| Dashboard row 2 | 2 columns | 2 columns | Stack vertical |
| Artikel layout | 40/60 split | 40/60 split | Stack vertical |
| Tables | Full display | Horizontal scroll | Horizontal scroll |