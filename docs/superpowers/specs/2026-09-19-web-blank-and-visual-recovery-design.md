# Food Radar Web Blank-Screen And Visual Recovery Design

## Goal

Make the deployed Web application render real page content after onboarding and restore the mini-program's existing visual assets instead of presenting a generic line-icon interface.

## Confirmed Cause

The authenticated route wrapper is nested under React Router but returns a `children` prop that React Router does not provide. When a local profile exists, the wrapper therefore renders `undefined`, leaving the application shell visible and the main content area empty. The wrapper must render an `Outlet`.

## Visual Direction

The mini-program remains the source of truth. The Web version keeps its white cards, `#F7F8FA` page background, `#07C160` brand green, compact Chinese typography, rounded bottom navigation, 3D action illustrations, and feature PNGs. Core navigation and feature identities use the copied images under `web/public/images`; Lucide remains only for universal controls such as back, close, edit, search, and directional arrows.

## Scope

- Repair guarded nested routing and add a visible crash fallback so failures never become a silent white screen.
- Replace mobile and desktop primary-navigation line icons with original active/inactive tab images.
- Replace scan capabilities, exploration services, profile/report entry points, result signals, and AI avatar imagery with the original resource images where mappings exist.
- Keep all 17 routes and current browser-native behavior intact.
- Verify first-run onboarding, returning-user home, direct child routes, mobile and desktop layouts, lint, and production build.
- Preserve `miniprogram/` and `backend/` unchanged.

## Backend Boundary

The visual and routing fixes work without a backend. OCR analysis, DeepSeek chat, server-backed comparison, and remote data still require a configured HTTPS API through `VITE_API_BASE_URL`; unavailable server features must show a useful error and must not blank the application.
