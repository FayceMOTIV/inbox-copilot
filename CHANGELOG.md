# Changelog

All notable changes to Inbox Copilot are documented here.

## [v1.1.4] - 2024-12-23

### Fixed
- **EmailDrawer buttons regression**: "Traité" and "En attente" buttons now work
  - Fixed thread status endpoint to upsert (create if not exists)
  - Threads are created on-demand when marking status
- **Documents rule creation**: Creating surveillance rules now works
  - Made `due_date` optional in API (defaults to empty string)
  - Fixed ObjectId serialization error in response
- **Improved error handling**: All drawer actions now show proper error toasts

### Changed
- `update_thread_status` in threads.py now uses upsert for create-if-not-exists behavior

## [v1.1.3] - 2024-12-23

### Changed
- Debug page shows 404 content in production (soft 404, not redirect)
- Added runtime debug_key param for prod testing

## [v1.1.2] - 2024-12-23

### Added
- **Debug Page** (`/debug`): DEV-only diagnostics page showing:
  - Backend health (API + MongoDB status)
  - Connected accounts
  - Notifications unread count
  - Silence mode status and ranges
  - Last recap timestamps
  - Last API error captured
- **Feedback Button**: One-click copy of debug info to clipboard
- **API Error Capture**: Centralized error handling with sessionStorage persistence
- **Providers Component**: Unified context wrapper for theme + error handling

### Changed
- Layout now uses `Providers` wrapper for cleaner context management

## [v1.1.1] - 2024-12-23

### Fixed
- **SSR/Hydration crash**: Fixed "e[0] is not a function" error on page refresh
  - Added SSR guards to `useTTS` hook (`speak()` and `stop()` functions)
  - Added `mounted` state to `useMediaQuery` and `useIsMobile` hooks to prevent hydration mismatch

## [v1.1.0] - 2024-12-23

### Added
- **Notifications Center** (P1):
  - Backend: `GET /api/notifications` with `unread_only` filter
  - Backend: `POST /api/notifications/mark_read` (batch)
  - Backend: `POST /api/notifications/mark_all_read`
  - Notification generation on recap (URGENT, VIP, DOCUMENT, WAITING_OVERDUE)
  - Respects Mode Silence (silenced flag)
  - Frontend: Bell icon dropdown (desktop) / bottom sheet (mobile)
  - Click notification opens EmailDrawer

- **Voice Support** (P1):
  - `VoiceInputButton`: STT via Web Speech API with visual feedback
  - `TTSToggleButton`: Toggle to read AI responses aloud
  - `useTTS` hook: SpeechSynthesis with auto-summarize for long text
  - `ListeningOverlay`: Fullscreen recording indicator

- **Assistant Result Cards** (P1):
  - `AssistantMessageText`: Formatted text with bullet truncation
  - `AssistantEmailCard`: Priority/VIP colored cards
  - `AssistantResultList`: Email results with click handlers
  - `AssistantDocCard`/`AssistantDocList`: Document cards
  - `AssistantActionSuggestions`: Quick action chips
  - `AssistantResponse`: Unified wrapper component

- **Mobile Polish** (P1):
  - `Skeletons.jsx`: Loading states for emails, notifications, VIPs
  - `EmptyStates.jsx`: Contextual empty states with CTAs
  - Enhanced tap targets (>=44px)
  - Micro-interactions with Framer Motion

## [v1.0.0] - 2024-12-22

### Added
- **Core Features**:
  - AI-powered email assistant with natural language chat
  - Gmail OAuth integration
  - Email search, compose, and reply
  - Attachment download (single and batch)

- **Dashboard Pages**:
  - `/` - Assistant chat interface
  - `/aujourdhui` - Today's email summary
  - `/recaps` - Morning/evening recap history
  - `/documents` - Document detection (invoices, contracts, etc.)
  - `/memoire` - VIP contact management
  - `/parametres` - Settings and account management

- **Smart Features**:
  - VIP contact detection and prioritization
  - Urgent email detection with confidence scoring
  - Waiting thread tracking
  - Mode Silence (quiet hours)
  - AI-generated reminders

- **UI/UX**:
  - Mobile-first responsive design
  - Desktop sidebar navigation
  - Mobile bottom navigation
  - Dark mode support
  - Email panel/drawer for viewing emails
