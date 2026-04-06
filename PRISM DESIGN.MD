# Prism Deep Sea: Design System Document

### 1. Overview & Creative North Star
**Creative North Star: The Refractive Monolith**

Prism Deep Sea is a high-end editorial design system built for technical precision and architectural depth. It moves away from the "flat web" by treating the UI as a series of layered, translucent glass panes submerged in a dark, oceanic environment. The system prioritizes "Architectural Clarity" over standard templates, using high-contrast typography scales and intentional asymmetry to guide the user's eye through complex data landscapes. 

The aesthetic is characterized by:
*   **Extreme Contrast:** Ultra-dark backgrounds paired with vibrant, neon-flecked accents.
*   **Refractive Light:** Elements don't just sit on the page; they glow and distort the layers beneath them.
*   **Technical Elegance:** A focus on monospace details and "data-viz" aesthetics as core decorative elements.

---

### 2. Colors
The palette is rooted in the "Abyssal" zone (Surfaces) and the "Photic" zone (Primary accents).

*   **Primary (#00daf3):** The "Accent Cyan." Used sparingly for critical focus points, status indicators, and primary CTAs.
*   **Secondary (#007ea7):** A deep aquatic blue used for structural depth and gradients.
*   **Surface Hierarchy:**
    *   `Surface Container Lowest` (#05070a): The deepest background level.
    *   `Surface Container High` (#13171f): The standard card or section background.
*   **The "No-Line" Rule:** 1px solid borders are strictly prohibited for structural sectioning. Division must be achieved through background shifts (e.g., transitioning from `surface` to `surface_container_low`). 
*   **Surface Hierarchy & Nesting:** Depth is created by nesting `surface_container_lowest` elements within `surface_container` sections to create a "recessed" or "carved" look.
*   **Glass & Gradient Rule:** Floating elements (modals, nav bars) must use the `glass-card` property: `rgba(19, 23, 31, 0.6)` with a `24px` backdrop blur. Use "Refractive Gradients" (Cyan to Deep Blue) for primary interaction points.

---

### 3. Typography
The system uses a dual-type approach to balance human readability with a machine-precise aesthetic.

**Extracted Scale:**
*   **Display (8xl/6xl):** 3.75rem - 6rem. Manrope Extrabold. Used for hero messaging with tight `0.95` leading and `tracking-tighter`.
*   **Headline (4xl/5xl):** 2.25rem - 3rem. Manrope Bold. Used for section titles.
*   **Title/Body Large:** 1.25rem - 1.5rem. Inter Light. High-end editorial feel for sub-headers.
*   **Small/Label:** 10px (0.625rem). Inter Bold. Used for "Metadata" labels with `tracking-widest` and uppercase transform.

**Typographic Rhythm:**
The contrast between the massive, tight-tracked headlines and the tiny, wide-tracked monospace-style labels creates a sense of "technical luxury." Italics should be used as a highlight color within headlines to add a signature editorial touch.

---

### 4. Elevation & Depth
Elevation in Prism Deep Sea is achieved through light and layering, not shadow alone.

*   **The Layering Principle:** Stack `surface-container` tiers. A card (`surface_container_high`) sits on a background (`surface`). Inside that card, input areas are recessed (`surface_container_lowest`).
*   **Ambient Shadows:** Use the system's `shadow-2xl` and `shadow-xl` for large cards. These are high-spread, low-opacity shadows that simulate a soft glow rather than a hard drop.
*   **The Ghost Border:** If a boundary is required for accessibility, use `outline_variant` (#2d3748) at 10-20% opacity.
*   **Data Prism Glow:** Active status elements or primary "Prisms" use a `drop-shadow(0 0 12px rgba(0, 218, 243, 0.5))` to simulate light emission.

---

### 5. Components
*   **Buttons:**
    *   *Primary:* `refractive-gradient` background with `on-primary-container` text. Rounded-xl (0.5rem).
    *   *Secondary:* `surface-container-highest` with a 1px `white/5` border.
*   **Cards:** Use the `glass-card` style for interactive dashboard elements. Incorporate a "Security Header" with three-dot window controls for technical personality.
*   **Bento Grid:** Use varied `surface-container` colors to distinguish grid items rather than lines.
*   **Inputs:** Recessed `surface-container-lowest` backgrounds with `outline-variant` borders that glow on focus.
*   **Status Indicators:** Use a `2px` rounded-full "Pulse" dot in `accent-cyan` for live-data contexts.

---

### 6. Do's and Don'ts
**Do:**
*   Use `italic` Manrope for emphasis in large displays.
*   Apply `backdrop-blur` to all fixed navigation and modal elements.
*   Use wide letter spacing for all text under 12px.
*   Leverage gradients to imply motion and light direction.

**Don't:**
*   Use standard grey (#808080) for text; use `slate-400` or `outline` colors to maintain the blue-tinted dark mode.
*   Use sharp corners; maintain a consistent `rounded-xl` (8px) for cards and `rounded-lg` (4px) for smaller components.
*   Use solid black (#000000) for backgrounds; keep the "Deep Sea" blue-black tones (#05070a).