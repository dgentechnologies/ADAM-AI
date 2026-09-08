# ADAM Companion Applications

ADAM is supported by a modern suite of client and dashboard applications designed for desktop workstations and mobile devices.

---

## 1. Application Ecosystem Overview

```text
                                 ┌─────────────────────────┐
                                 │   ADAM Robot Hardware   │
                                 │ (Pi Zero 2 W / ESP / Pico)
                                 └────────────┬────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      │ LAN WebSocket / REST                          │ Bluetooth LE / mDNS
                      ▼                                               ▼
            ┌───────────────────┐                           ┌───────────────────┐
            │   PC Dashboard    │                           │    Mobile App     │
            │     (apps/pc)     │                           │   (apps/mobile)   │
            │  (React / Vite)   │                           │  (Expo / React N) │
            └───────────────────┘                           └───────────────────┘
```

---

## 2. Directory Structure

```text
apps/
├── README.md               # Ecosystem documentation (this file)
│
├── pc/                     # PC Desktop Dashboard (React 18 + Vite + Tailwind CSS)
│   ├── package.json        # Frontend dependencies & scripts
│   ├── vite.config.ts      # Vite configuration
│   ├── tailwind.config.js  # Styling configuration
│   ├── tsconfig.json       # TypeScript configuration
│   ├── src/                # UI components, dashboard widgets, and WebSocket clients
│   └── public/             # Static web assets & icons
│
└── mobile/                 # Mobile Companion App (Turborepo + Expo / React Native)
    ├── package.json        # Monorepo root configuration
    ├── pnpm-workspace.yaml # Workspace definitions
    ├── turbo.json          # Turbo build pipeline
    ├── apps/
    │   ├── mobile-shell/   # Expo / React Native mobile application
    │   ├── web/            # Responsive web companion
    │   └── api/            # Local backend service bridge
    ├── packages/
    │   ├── ui/             # Shared cross-platform UI components
    │   ├── types/          # Shared TypeScript type definitions
    │   └── config/         # Shared ESLint, Tailwind, & TS configs
    └── docs/               # Mobile architecture and state management documentation
```

---

## 3. PC Desktop Dashboard (`apps/pc`)

The **PC Dashboard** provides a real-time command center for developers, researchers, and users to monitor ADAM's internal telemetry, view conversation transcripts, inspect sensor feeds, and control robot parameters directly.

### Key Features
- **Live Multimodal Telemetry**: Visual display of sound localization angles, active microphone RMS levels, and camera duty-cycle states.
- **Transcript Viewer**: Live streaming transcription of both user speech and Gemini responses.
- **Emotion & Actuation Override**: Manual controls to trigger facial expressions, pan servo angles, and tilt servo positions.
- **System Health Monitor**: Core temperature, memory usage, and serial bus integrity graphs.

### Tech Stack
- **Framework**: [Vite](https://vitejs.dev/) + [React 18](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Icons**: Lucide React
- **Communications**: Native WebSockets (`ws_server.py` on Pi)

### Setup & Development
```bash
cd apps/pc
npm install
npm run dev
# Dashboard launches at http://localhost:5173
```

---

## 4. Mobile Companion Application (`apps/mobile`)

The **ADAM Mobile App** is a cross-platform companion application for iOS and Android, allowing users to configure, calibrate, and interact with ADAM remotely.

### Key Features
- **Effortless Onboarding**: Bluetooth Low Energy (BLE) provisioning to connect ADAM to local Wi-Fi networks.
- **Voice Persona Selection**: Switch Gemini voices, speaking styles, and system prompt personality profiles.
- **Face & Memory Management**: Register new user faces and review/edit ADAM's long-term memory entries.
- **Remote Teleoperation**: Dual virtual joysticks for manual pan-tilt camera steering and remote audio listening.

### Tech Stack
- **Architecture**: [Turborepo](https://turbo.build/) monorepo
- **Framework**: [Expo](https://expo.dev/) / [React Native](https://reactnative.dev/)
- **Package Manager**: [pnpm](https://pnpm.io/)
- **State Management**: Zustand
- **Navigation**: Expo Router

### Setup & Development
```bash
cd apps/mobile
pnpm install
pnpm dev
```
