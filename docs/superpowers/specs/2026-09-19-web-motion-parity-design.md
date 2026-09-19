# Food Radar Web Motion Parity Design

## Goal

Restore the motion and transition behavior already present in the native WeChat mini-program so the mobile Web version feels like the original application rather than a static visual copy. The work must not redesign pages, replace existing image assets, or alter business flows.

## Scope

The Web version will reproduce the mini-program's existing motion vocabulary:

- The scan page hero enters with the original short upward fade.
- The ingredient-label illustration contains the original four scan-frame corners and a green scan line that sweeps vertically on a 2.2-second loop.
- Home-page feature blocks use the original staggered `cardRise`, `softPop`, and `scorePop` behavior.
- The mobile bottom tab bar animates active icons, preserves press feedback, and gives the central scan action the original `scanTabPop` response when selected.
- Route changes on mobile receive a restrained upward fade consistent with the mini-program page-entry motion.
- Existing bottom sheets, dialogs, loading layers, expandable selectors, cards, and buttons receive the matching fade, slide, rotation, and press transitions where the mini-program defines them.

Desktop keeps the same content and layout. Route transitions remain subtle on desktop, while touch-oriented press and tab effects are concentrated on mobile.

## Implementation Structure

Motion remains dependency-free. CSS keyframes and transitions are defined in the existing global and page style files, while React supplies only the state or route key required to restart an animation.

`AppShell` wraps the current route outlet in a location-keyed motion container. It does not delay navigation, maintain duplicate pages, or implement gesture-based routing. The scan illustration markup is expanded to match the mini-program's label card, scan frame, corners, and scan line rather than using a static approximation.

Reusable motion classes cover page entry, staggered card entry, active-tab pop, overlay fade, panel slide, and press feedback. Page-specific timing stays aligned with the WXSS values instead of introducing a new animation system.

## Accessibility And Performance

All animation uses opacity and transforms where practical to avoid layout thrashing. Infinite motion is limited to the scan line. `prefers-reduced-motion: reduce` disables looping and entrance animations and shortens state transitions, while leaving every control and status visible.

Animations must not block pointer or keyboard interaction. Route changes render their destination immediately, and loading/error states continue to use the existing behavior.

## Verification

- Compare the Web scan hero against `miniprogram/pages/scan/scan.wxml` and `scan.wxss` at 375px, 390px, and 414px widths.
- Verify the scan line loops, the scan tab pops when selected, and route entry restarts after navigation.
- Verify the home score and cards animate in the same order as the mini-program.
- Verify bottom sheets and dialogs animate without remaining invisible or intercepting input after closing.
- Verify reduced-motion mode removes nonessential movement.
- Run Web lint and production build, then create a new Vercel Preview deployment.
