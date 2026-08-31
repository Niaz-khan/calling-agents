/* Minimal inline icon set — no icon library dependency. */

const base = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': 'true',
}

export function DashboardIcon(props) {
  return (
    <svg {...props} {...base}>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  )
}

export function AgentIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M12 12a4 4 0 100-8 4 4 0 000 8z" />
      <path d="M4 20c0-3.3 3.6-5 8-5s8 1.7 8 5" />
    </svg>
  )
}

export function DeployIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  )
}

export function PhoneIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6A19.79 19.79 0 012.12 4.18 2 2 0 014.11 2h3a2 2 0 012 1.72c.13.96.36 1.9.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0122 16.92z" />
    </svg>
  )
}

export function CallIcon(props) {
  return <PhoneIcon {...props} />
}

export function UsersIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M17 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2" />
      <circle cx="9.5" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 00-3-3.87M15.5 3.13a4 4 0 010 7.75" />
    </svg>
  )
}

export function CalendarIcon(props) {
  return (
    <svg {...props} {...base}>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
    </svg>
  )
}

export function BookIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
    </svg>
  )
}

export function ServiceIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M3 18v-6a9 9 0 0118 0v6" />
      <path d="M21 19a2 2 0 01-2 2h-1a2 2 0 01-2-2v-3a2 2 0 012-2h3zM3 19a2 2 0 002 2h1a2 2 0 002-2v-3a2 2 0 00-2-2H3z" />
    </svg>
  )
}

export function ChartIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M3 3v18h18" />
      <path d="M7 14l4-4 3 3 5-6" />
    </svg>
  )
}

export function SettingsIcon(props) {
  return (
    <svg {...props} {...base}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 11-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 110 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  )
}

export function UserIcon(props) {
  return (
    <svg {...props} {...base}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 3.6-6 8-6s8 2 8 6" />
    </svg>
  )
}

export function SearchIcon(props) {
  return (
    <svg {...props} {...base}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.35-4.35" />
    </svg>
  )
}

export function BellIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 01-3.46 0" />
    </svg>
  )
}

export function MenuIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M3 6h18M3 12h18M3 18h18" />
    </svg>
  )
}

export function CloseIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  )
}

export function LogoutIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
      <path d="M16 17l5-5-5-5M21 12H9" />
    </svg>
  )
}

export function ArrowLeftIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M19 12H5M12 19l-7-7 7-7" />
    </svg>
  )
}

export function PlusIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}
export function WebsiteIcon(props) {
  return (
    <svg {...props} {...base}>
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
    </svg>
  )
}

export function KnowledgeIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M12 3v18M7 6H4a2 2 0 00-2 2v1a2 2 0 002 2h3M17 6h3a2 2 0 012 2v1a2 2 0 01-2 2h-3" />
      <path d="M7 6h10v4a5 5 0 01-10 0V6z" />
    </svg>
  )
}

export function TransferIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M4 7h13M17 3l4 4-4 4M20 17H7M7 13l-4 4 4 4" />
    </svg>
  )
}

export function OutboundIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6A19.79 19.79 0 012.12 4.18 2 2 0 014.11 2h3a2 2 0 012 1.72c.13.96.36 1.9.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0122 16.92z" />
      <path d="M13 11l6-6M15 5h4v4" />
    </svg>
  )
}

export function CheckIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M20 6L9 17l-5-5" />
    </svg>
  )
}

export function ArrowRightIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  )
}

export function ChevronDownIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M6 9l6 6 6-6" />
    </svg>
  )
}

export function QuoteIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M3 21c3-1 5-3 5-7V5H3v9h4" />
      <path d="M13 21c3-1 5-3 5-7V5h-5v9h4" />
    </svg>
  )
}

export function OrganizationIcon(props) {
  return (
    <svg {...props} {...base}>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="9" rx="1.5" />
      <path d="M3 21h18" />
      <path d="M6.5 16v2M17.5 16v2" />
    </svg>
  )
}

export function GlobeIcon(props) {
  return (
    <svg {...props} {...base}>
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20" />
      <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
    </svg>
  )
}

export function LayersIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M12 2l9 5-9 5-9-5 9-5z" />
      <path d="M3 12l9 5 9-5M3 17l9 5 9-5" />
    </svg>
  )
}

export function PaletteIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M12 22a10 10 0 1110-10c0 2.2-1.8 3-3.5 3H16a2 2 0 00-2 2c0 .6.3 1.1.7 1.4.8.7.6 2.6-2.7 2.6z" />
      <circle cx="7.5" cy="11.5" r="1" />
      <circle cx="10.5" cy="7.5" r="1" />
      <circle cx="15" cy="7.5" r="1" />
    </svg>
  )
}

export function LayoutIcon(props) {
  return (
    <svg {...props} {...base}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 9h18M9 21V9" />
    </svg>
  )
}

export function CopyIcon(props) {
  return (
    <svg {...props} {...base}>
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
    </svg>
  )
}

export function TrashIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6" />
    </svg>
  )
}

export function EditIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M12 20h9M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
    </svg>
  )
}

export function EyeIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

export function EyeOffIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M17.9 17.9A10.4 10.4 0 0112 20c-7 0-11-8-11-8a20 20 0 014.1-5.9M9.9 4.24A9.9 9.9 0 0112 4c7 0 11 8 11 8a20 20 0 01-2.16 3.19" />
      <path d="M1 1l22 22M9.86 9.86a3 3 0 004.28 4.28" />
    </svg>
  )
}

export function StoreIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M3 9l1-5h16l1 5M3 9a3 3 0 106 0 3 3 0 106 0 3 3 0 106 0M5 9v12h14V9" />
      <path d="M9 21v-6h6v6" />
    </svg>
  )
}

export function HomeIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
      <path d="M9 22V12h6v10" />
    </svg>
  )
}

export function WrenchIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M14.7 6.3a4.5 4.5 0 00-6 6L3 18l3 3 5.7-5.7a4.5 4.5 0 006-6L14.5 13 11 9.5z" />
    </svg>
  )
}

export function ScissorsIcon(props) {
  return (
    <svg {...props} {...base}>
      <circle cx="6" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <path d="M20 4L8.12 15.88M14.47 14.48L20 20M8.12 8.12L12 12" />
    </svg>
  )
}

export function RestaurantIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M6 2v6a2 2 0 004 0V2M8 2v20" />
      <path d="M18 2c-2 2-3 5-3 8v4h3V2zM18 14v8" />
    </svg>
  )
}

export function HealthIcon(props) {
  return (
    <svg {...props} {...base}>
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16" />
    </svg>
  )
}

export function BriefcaseIcon(props) {
  return (
    <svg {...props} {...base}>
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2" />
    </svg>
  )
}

export function SparkIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" />
      <path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z" />
    </svg>
  )
}

export function ListIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M8 6h13M8 12h13M8 18h13" />
      <path d="M3 6h.01M3 12h.01M3 18h.01" />
    </svg>
  )
}

export function ExternalIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
      <path d="M15 3h6v6M10 14L21 3" />
    </svg>
  )
}

export function ShieldIcon(props) {
  return (
    <svg {...props} {...base}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  )
}

export function ClockIcon(props) {
  return (
    <svg {...props} {...base}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  )
}
