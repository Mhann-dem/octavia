# Dashboard Pages Map

This document maps the existing HTML prototypes in the `dashboards-html/` directory against the completed Next.js pages for the Octavia Cloud Platform (SaaS).

## Page Inventory

| Category | Page Name | Status | Next.js Path | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Core** | **Landing Page** | 🟢 Completed (2025-11-23) | `octavia-web/app/page.tsx` | Public-facing home page with marketing content and features. |
| **Core** | **Hub / Dashboard** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/page.tsx` | Central hub with 6 feature cards (Video, Audio, Subtitles, etc.). |
| **Auth** | **Login** | � Completed (2025-11-23) | `octavia-web/app/login/page.tsx` | Email/password + Google/Apple social login. |
| **Auth** | **Sign Up** | 🟢 Completed (2025-11-23) | `octavia-web/app/signup/page.tsx` | Registration with email/password + social signup. |
| **Video** | **Video Translator Input** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/video/page.tsx` | Upload video, select source/target languages. |
| **Video** | **Translation Progress** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/video/progress/page.tsx` | 5-step pipeline progress (Splitting → Transcribing → Translating → Dubbing → Merging). |
| **Video** | **Review & Export** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/video/review/page.tsx` | Video player with stats and download options. |
| **Audio** | **Audio Translator** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/audio/page.tsx` | Audio upload with voice synthesis options. |
| **Audio** | **Subtitle to Audio** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/audio/subtitle-to-audio/page.tsx` | Convert SRT/VTT to spoken audio with voice selection. |
| **Subtitles** | **Subtitle Gen Input** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/subtitles/page.tsx` | Generate subtitles from video/audio with auto-detect. |
| **Subtitles** | **Subtitle Gen Progress** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/subtitles/progress/page.tsx` | 4-step pipeline (Audio Extraction → Speech Recognition → Timestamp Sync → Format Export). |
| **Subtitles** | **Subtitle Review** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/subtitles/review/page.tsx` | Edit and export generated subtitles (SRT, VTT, ASS). |
| **Subtitles** | **Subtitle Translator** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/subtitles/translate/page.tsx` | Translate existing subtitle files with context-aware AI. |
| **Settings** | **General Settings** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/settings/page.tsx` | Notifications, language & region preferences. |
| **Settings** | **Advanced Settings** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/settings/advanced/page.tsx` | Tabbed interface (Magic Mode, Performance, Data & Storage). |
| **Magic** | **My Voices** | � Completed (2025-11-23) | `octavia-web/app/dashboard/voices/page.tsx` | Manage cloned voices and voice profiles. |
| **Billing** | **Plans & Billing** | � Completed (2025-11-23) | `octavia-web/app/dashboard/billing/page.tsx` | Subscription management, usage stats, payment methods, invoices. |
| **Jobs** | **Job History** | � Completed (2025-11-23) | `octavia-web/app/dashboard/history/page.tsx` | List of past translations with status and download links. |
| **Account** | **Profile & Security** | � Completed (2025-11-23) | `octavia-web/app/dashboard/profile/page.tsx` | User profile, password change, 2FA settings. |
| **Account** | **Team / Organization** | � Completed (2025-11-23) | `octavia-web/app/dashboard/team/page.tsx` | Manage team members, roles, and invitations. |
| **Other** | **Projects** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/projects/page.tsx` | Organize translation projects with status tracking. |
| **Other** | **Help** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/help/page.tsx` | Help center with search, topics, and quick links. |
| **Other** | **Support** | 🟢 Completed (2025-11-23) | `octavia-web/app/dashboard/support/page.tsx` | Contact form, response times, and support channels. |

## Summary

- **Total Pages Required**: 24
- **Completed Pages**: 24 ✅
- **Status**: All pages migrated to Next.js with "Liquid Glass" design system

## Build Status

✅ **Build Successful** - All 21 routes compiled and pre-rendered as static content.

## Design System

All pages implement the **"Liquid Glass"** design system with:
- Glass panels with backdrop blur and shine effects
- Ambient purple/cyan/pink/green/orange glows with animations
- Framer Motion hover effects and transitions
- Lucide React icons throughout
- Consistent color palette (Purple primary #9333EA, Cyan/Pink accents)
- Border beam animated buttons
- Custom scrollbars and form inputs

## Routes Available

```
/                                    Landing page
/login                               Login page
/signup                              Signup page
/dashboard                           Hub (6 feature cards)
/dashboard/audio                     Audio translation
/dashboard/audio/subtitle-to-audio   Subtitle to audio
/dashboard/billing                   Plans & billing
/dashboard/help                      Help center
/dashboard/history                   Job history
/dashboard/profile                   Profile & security
/dashboard/projects                  Projects management
/dashboard/settings                  General settings
/dashboard/settings/advanced         Advanced settings
/dashboard/subtitles                 Subtitle generation
/dashboard/subtitles/progress        Subtitle progress
/dashboard/subtitles/review          Subtitle review
/dashboard/subtitles/translate       Subtitle translation
/dashboard/support                   Support contact
/dashboard/team                      Team management
/dashboard/video                     Video translation
/dashboard/video/progress            Video progress
/dashboard/video/review              Video review
/dashboard/voices                    My voices
```

## Migration Complete

All HTML prototypes have been successfully migrated to Next.js with:
- TypeScript for type safety
- Server components where applicable
- Client components for interactive elements
- Responsive layouts (mobile, tablet, desktop)
- SEO-friendly meta tags
- Optimized performance
