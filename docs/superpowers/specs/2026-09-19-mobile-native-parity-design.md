# Food Radar Mobile Native-Parity Design

## Goal

Make the browser version at 375–414px widths visually follow the native mini-program rather than merely sharing its colors and content.

## Source Of Truth

For every migrated route, the matching `miniprogram/pages/*/*.wxml` determines hierarchy and visible content, the matching `.wxss` determines spacing and appearance, `miniprogram/app.wxss` supplies shared tokens and iconfont glyphs, and `miniprogram/custom-tab-bar` determines mobile navigation. Existing PNG assets are used only where the original WXML uses an `<image>`; original `iconfont` glyphs are used where the WXML uses an `iconfont` class.

## Mobile Rules

- Convert `rpx` at the mini-program's 750rpx design width to CSS pixels at a 2:1 ratio for the 375px baseline.
- Use 14px page gutters, 12px primary card radii, 10px secondary radii, and the original font sizes and weights.
- Preserve the original single-column order, card grouping, list density, bottom spacing, and fixed custom tab bar.
- Remove decorative Web-only leading icons, arrows, captions, and card wrappers when the original page does not contain them.
- Keep browser-required controls accessible while styling them as their original mini-program rows.
- Apply desktop adaptations only at 900px and above so desktop work does not alter mobile parity.

## Icon Policy

- Home quick actions and camera/scan actions use the original PNG assets.
- AI chat uses the original nutritionist avatar.
- Scan abilities, toolbox services, report actions, list arrows, search, family actions, and settings use `FoodRadarIconfont` glyphs exactly as referenced by the original WXML.
- Lucide is retained only where the original has no supplied glyph or asset and the control is browser-specific.

## Verification

Compare rendered 375px, 390px, and 414px screenshots against the WXML/WXSS structure for all five tab pages, then smoke-test every route, navigation, search, forms, and empty states. The final client must pass lint and production build without changing `miniprogram/` or `backend/`.
