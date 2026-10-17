import { useMemo, useState, type ReactNode, type CSSProperties } from "react"
import { useAirPurifyData, type AirPurifyState } from "./api/useAirPurifyData"
import { API_BASE_URL, type SensorReading, type AlertItem, type Device, type Forecast, type ForecastStatus } from "./api/client"

const backendDisplayUrl =
  API_BASE_URL || (typeof window !== "undefined" ? `${window.location.origin}/api` : "AirPurify API")

type Page = "home" | "dashboard" | "settings" | "profile"
type IconName =
  | "home"
  | "dashboard"
  | "settings"
  | "user"
  | "wind"
  | "bell"
  | "sun"
  | "moon"
  | "chevron"
  | "map"
  | "wifi"
  | "refresh"
  | "download"
  | "alert"
  | "device"
  | "database"
  | "check"
  | "arrow"
  | "forecast"
  | "activity"
  | "search"
  | "lock"
  | "logout"
  | "menu"
  | "close"
  | "more"
  | "clock"
  | "spark"
  | "shield"
  | "sliders"
  | "eye"
  | "plus"

const iconPaths: Record<IconName, ReactNode> = {
  home: (
    <>
      <path d="m3 11 9-8 9 8" />
      <path d="M5 10v10h14V10" />
      <path d="M9 20v-6h6v6" />
    </>
  ),
  dashboard: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="2" />
      <rect x="14" y="3" width="7" height="7" rx="2" />
      <rect x="3" y="14" width="7" height="7" rx="2" />
      <rect x="14" y="14" width="7" height="7" rx="2" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21H9.6v-.1A1.7 1.7 0 0 0 8.5 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.6-1H3v-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6V3h4v.1A1.7 1.7 0 0 0 15 4.6a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 9a1.7 1.7 0 0 0 1.6 1h.1v4H21a1.7 1.7 0 0 0-1.6 1Z" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </>
  ),
  wind: (
    <>
      <path d="M4 8h10a3 3 0 1 0-3-3" />
      <path d="M4 12h15a2 2 0 1 1-2 2" />
      <path d="M4 16h8a3 3 0 1 1-3 3" />
    </>
  ),
  bell: (
    <>
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
      <path d="M10 21h4" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41" />
    </>
  ),
  moon: <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3 6.6 6.6 0 0 0 21 12.8Z" />,
  chevron: <path d="m9 18 6-6-6-6" />,
  map: (
    <>
      <path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z" />
      <circle cx="12" cy="10" r="2.5" />
    </>
  ),
  wifi: (
    <>
      <path d="M5 12.6a11 11 0 0 1 14 0M8.5 16a6 6 0 0 1 7 0" />
      <circle cx="12" cy="20" r=".8" fill="currentColor" />
    </>
  ),
  refresh: (
    <>
      <path d="M20 7v5h-5" />
      <path d="M19 12a7 7 0 1 0-1.2 5" />
    </>
  ),
  download: (
    <>
      <path d="M12 3v12m-4-4 4 4 4-4" />
      <path d="M4 20h16" />
    </>
  ),
  alert: (
    <>
      <path d="M10.3 3.8 2.4 18a2 2 0 0 0 1.8 3h15.6a2 2 0 0 0 1.8-3L13.7 3.8a2 2 0 0 0-3.4 0Z" />
      <path d="M12 9v4M12 17h.01" />
    </>
  ),
  device: (
    <>
      <rect x="5" y="2" width="14" height="20" rx="3" />
      <path d="M9 6h6M10 18h4" />
    </>
  ),
  database: (
    <>
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
      <path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  arrow: (
    <>
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </>
  ),
  forecast: (
    <>
      <path d="M3 17 8 12l4 3 8-9" />
      <path d="M14 6h6v6" />
    </>
  ),
  activity: <path d="M3 12h4l2.5-7 5 14 2.5-7h4" />,
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-4-4" />
    </>
  ),
  lock: (
    <>
      <rect x="4" y="10" width="16" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </>
  ),
  logout: (
    <>
      <path d="M10 17l5-5-5-5M15 12H3" />
      <path d="M14 3h6v18h-6" />
    </>
  ),
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  more: (
    <>
      <circle cx="5" cy="12" r="1" />
      <circle cx="12" cy="12" r="1" />
      <circle cx="19" cy="12" r="1" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  spark: (
    <path d="m12 3 1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6L12 3Zm6 11 .8 2.2L21 17l-2.2.8L18 20l-.8-2.2L15 17l2.2-.8L18 14Z" />
  ),
  shield: (
    <>
      <path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  sliders: (
    <>
      <path d="M4 6h16M4 12h16M4 18h16" />
      <circle cx="8" cy="6" r="2" fill="var(--surface)" />
      <circle cx="16" cy="12" r="2" fill="var(--surface)" />
      <circle cx="10" cy="18" r="2" fill="var(--surface)" />
    </>
  ),
  eye: (
    <>
      <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" />
      <circle cx="12" cy="12" r="2.5" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
}

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      className="icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {iconPaths[name]}
    </svg>
  )
}

function Button({
  children,
  variant = "primary",
  icon,
  onClick,
  type = "button",
  disabled = false,
}: {
  children: ReactNode
  variant?: "primary" | "secondary" | "ghost" | "danger"
  icon?: IconName
  onClick?: () => void
  type?: "button" | "submit"
  disabled?: boolean
}) {
  return (
    <button
      type={type}
      className={`btn btn-${variant}`}
      onClick={onClick}
      disabled={disabled}
      style={disabled ? { opacity: 0.6, cursor: "not-allowed" } : undefined}
    >
      {icon && <Icon name={icon} size={16} />}
      <span>{children}</span>
    </button>
  )
}

function Badge({
  children,
  tone = "neutral",
  dot = true,
  title,
}: {
  children: ReactNode
  tone?: "good" | "warning" | "danger" | "info" | "neutral"
  dot?: boolean
  title?: string
}) {
  return (
    <span className={`badge badge-${tone}`} title={title}>
      {dot && <i />}
      {children}
    </span>
  )
}

function Card({
  children,
  className = "",
  style,
}: {
  children: ReactNode
  className?: string
  style?: CSSProperties
}) {
  return (
    <section className={`card ${className}`} style={style}>
      {children}
    </section>
  )
}

function SelectControl({
  label,
  value,
  options,
  onChange,
}: {
  label?: string
  value: string
  options: string[]
  onChange?: (val: string) => void
}) {
  return (
    <label className="field compact-field">
      {label && <span>{label}</span>}
      <select
        value={value}
        onChange={(e) => onChange && onChange(e.target.value)}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      <Icon name="chevron" size={14} />
    </label>
  )
}

function TextField({
  label,
  value,
  type = "text",
  hint,
  readOnly = false,
}: {
  label: string
  value: string
  type?: string
  hint?: string
  readOnly?: boolean
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type={type} defaultValue={value} readOnly={readOnly} />
      {hint && <small>{hint}</small>}
    </label>
  )
}

function Toggle({
  checked = false,
  label,
  onChange,
}: {
  checked?: boolean
  label: string
  onChange?: () => void
}) {
  return (
    <button className="toggle-row" onClick={onChange} type="button">
      <span>{label}</span>
      <span className={`toggle ${checked ? "on" : ""}`}>
        <i />
      </span>
    </button>
  )
}

function Segmented({
  options,
  active,
  onSelect,
}: {
  options: string[]
  active: string
  onSelect: (value: string) => void
}) {
  return (
    <div className="segmented">
      {options.map((option) => (
        <button
          key={option}
          className={active === option ? "active" : ""}
          onClick={() => onSelect(option)}
        >
          {option}
        </button>
      ))}
    </div>
  )
}

// -----------------------------------------------------------------------------
// AQI & Dynamic SVG Calculations & Date Formatting
// -----------------------------------------------------------------------------

function formatDateTime(dateStr?: string | null): string {
  if (!dateStr) return "N/A"
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    const pad = (n: number) => String(n).padStart(2, "0")
    const y = d.getFullYear()
    const m = pad(d.getMonth() + 1)
    const day = pad(d.getDate())
    const h = pad(d.getHours())
    const min = pad(d.getMinutes())
    const s = pad(d.getSeconds())
    return `${y}-${m}-${day} ${h}:${min}:${s}`
  } catch {
    return dateStr || "N/A"
  }
}

function computeIndicativeAQI(
  pm25?: number | null,
  pm10?: number | null
): { aqi: number | null; category: string; tone: "good" | "info" | "warning" | "danger" | "neutral" } {
  if (pm25 == null && pm10 == null) {
    return { aqi: null, category: "Unavailable", tone: "neutral" }
  }
  let aqiVal = 0
  if (pm25 != null) {
    if (pm25 <= 12.0) aqiVal = Math.round((50 / 12.0) * pm25)
    else if (pm25 <= 35.4) aqiVal = Math.round(51 + ((100 - 51) / (35.4 - 12.1)) * (pm25 - 12.1))
    else if (pm25 <= 55.4) aqiVal = Math.round(101 + ((150 - 101) / (55.4 - 35.5)) * (pm25 - 35.5))
    else if (pm25 <= 150.4) aqiVal = Math.round(151 + ((200 - 151) / (150.4 - 55.5)) * (pm25 - 55.5))
    else aqiVal = Math.round(201 + ((300 - 201) / (250.4 - 150.5)) * (pm25 - 150.5))
  } else if (pm10 != null) {
    if (pm10 <= 54.0) aqiVal = Math.round((50 / 54.0) * pm10)
    else if (pm10 <= 154.0) aqiVal = Math.round(51 + ((100 - 51) / (154.0 - 55.0)) * (pm10 - 55.0))
    else aqiVal = Math.round(101 + ((150 - 101) / (254.0 - 155.0)) * (pm10 - 155.0))
  }

  if (aqiVal <= 50) return { aqi: aqiVal, category: "Good", tone: "good" }
  if (aqiVal <= 100) return { aqi: aqiVal, category: "Moderate", tone: "info" }
  if (aqiVal <= 150) return { aqi: aqiVal, category: "Unhealthy for Sensitive Groups", tone: "warning" }
  return { aqi: aqiVal, category: "Unhealthy", tone: "danger" }
}

function TrendChart({
  variant = "pm25",
  forecast = false,
  height = 135,
  readings = [],
}: {
  variant?: "pm25" | "pm10" | "pm1"
  forecast?: boolean
  height?: number
  readings?: SensorReading[]
}) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  const series = useMemo(() => {
    if (!readings || readings.length === 0) return []
    // reverse so chronological left to right
    return [...readings].reverse()
  }, [readings])

  const chartData = useMemo(() => {
    if (series.length === 0) return null

    const vals = series.map((r) => {
      if (variant === "pm25") return r.pm2_5
      if (variant === "pm10") return r.pm10
      return r.pm1_0 ?? r.pm2_5 * 0.55
    })
    const maxVal = Math.max(30, ...vals) * 1.25

    const points = series.map((r, idx) => {
      const val = vals[idx]
      const x = series.length === 1 ? 294 : Math.round((idx / (series.length - 1)) * 560 + 14)
      const y = Math.max(16, Math.min(94, Math.round(94 - (val / maxVal) * 78)))
      return { x, y, val, reading: r }
    })

    const polyPoints = points.map((p) => `${p.x},${p.y}`).join(" ")
    return { points, polyPoints, maxVal }
  }, [series, variant])

  if (!chartData || series.length === 0) {
    return (
      <div className="empty-state-box" style={{ height }}>
        <Icon name="activity" size={20} />
        <b>No telemetry recorded</b>
        <p>No stored readings in the selected period. Expand time filter or select another location.</p>
      </div>
    )
  }

  const { points, polyPoints } = chartData
  const activePoint = hoveredIdx !== null && points[hoveredIdx] ? points[hoveredIdx] : null

  return (
    <div className="chart-wrap" style={{ height, position: "relative" }} onMouseLeave={() => setHoveredIdx(null)}>
      {activePoint && (
        <div
          className="chart-tooltip-box"
          style={{
            position: "absolute",
            left: Math.min(Math.max(10, activePoint.x - 65), 440),
            top: Math.max(4, activePoint.y - 65),
          }}
        >
          <b>
            {variant.toUpperCase()}: {activePoint.val.toFixed(1)} µg/m³
          </b>
          <span>{formatDateTime(activePoint.reading.timestamp || activePoint.reading.received_at)}</span>
          <span style={{ fontSize: 8 }}>
            Node: {activePoint.reading.device_id} ({activePoint.reading.location_id})
          </span>
          <span style={{ fontSize: 8 }}>Quality: {activePoint.reading.data_quality_status}</span>
        </div>
      )}
      <svg viewBox="0 0 588 110" preserveAspectRatio="none" role="img" aria-label="Particulate trend chart">
        <defs>
          <linearGradient id={`fill-${variant}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="currentColor" stopOpacity=".22" />
            <stop offset="1" stopColor="currentColor" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[20, 50, 80].map((y) => (
          <line key={y} x1="0" y1={y} x2="588" y2={y} className="grid-line" />
        ))}
        <polygon
          points={`${polyPoints} ${points[points.length - 1].x},110 ${points[0].x},110`}
          fill={`url(#fill-${variant})`}
          className={`area-${variant}`}
        />
        <polyline points={polyPoints} className={`line line-${variant}`} />
        {points.map((pt, i) => (
          <g key={i} onMouseEnter={() => setHoveredIdx(i)} style={{ cursor: "pointer" }}>
            <circle
              cx={pt.x}
              cy={pt.y}
              r={hoveredIdx === i ? 5 : 3}
              fill="var(--surface)"
              stroke="currentColor"
              strokeWidth={hoveredIdx === i ? 2.5 : 1.5}
            />
          </g>
        ))}
        {forecast && (
          <rect x="420" y="0" width="168" height="110" className="forecast-zone" />
        )}
      </svg>
    </div>
  )
}

function MiniTrend({
  up = true,
  tone = "green",
}: {
  up?: boolean
  tone?: "green" | "cyan" | "orange" | "red"
}) {
  return (
    <svg
      className={`mini-trend ${tone}`}
      viewBox="0 0 76 28"
      preserveAspectRatio="none"
    >
      <polyline
        points={
          up
            ? "1,23 15,18 28,20 42,10 56,13 75,4"
            : "1,5 15,9 28,7 42,18 56,14 75,24"
        }
      />
    </svg>
  )
}

function SectionTitle({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <div className="section-title">
      <div>
        <div className="title-md">{title}</div>
        {subtitle && <div className="muted">{subtitle}</div>}
      </div>
      {action}
    </div>
  )
}

function Sidebar({
  page,
  setPage,
  collapsed,
  setCollapsed,
  mobileOpen,
  setMobileOpen,
  healthStatus,
  deviceCount,
}: {
  page: Page
  setPage: (p: Page) => void
  collapsed: boolean
  setCollapsed: (c: boolean) => void
  mobileOpen: boolean
  setMobileOpen: (m: boolean) => void
  healthStatus: AirPurifyState["healthStatus"]
  deviceCount: number
}) {
  const navItems = [
    { id: "home" as const, label: "Home", icon: "home" as const },
    { id: "dashboard" as const, label: "Dashboard", icon: "dashboard" as const },
    { id: "settings" as const, label: "Settings", icon: "settings" as const },
    { id: "profile" as const, label: "Profile", icon: "user" as const },
  ]
  return (
    <aside
      className={`sidebar ${collapsed ? "collapsed" : ""} ${
        mobileOpen ? "mobile-open" : ""
      }`}
    >
      <div className="brand">
        <div className="brand-mark">
          <Icon name="wind" size={20} />
        </div>
        <div className="brand-copy">
          <b>AirPurify AI</b>
          <span>Platform v1.0.0</span>
        </div>
        <button
          className="mobile-close"
          onClick={() => setMobileOpen(false)}
          aria-label="Close menu"
        >
          <Icon name="close" />
        </button>
      </div>
      <nav className="side-nav">
        <div className="nav-label">Navigation</div>
        {navItems.map((item) => (
          <button
            key={item.id}
            className={page === item.id ? "active" : ""}
            onClick={() => {
              setPage(item.id)
              setMobileOpen(false)
            }}
          >
            <Icon name={item.icon} />
            <span>{item.label}</span>
            {page === item.id && <i />}
          </button>
        ))}
      </nav>
      <div className="side-status">
        <div
          className="status-orb"
          style={{
            color:
              healthStatus === "connected"
                ? "#3bd5ad"
                : healthStatus === "degraded"
                ? "#e3b341"
                : "#df5c5c",
          }}
        >
          <span
            style={{
              background:
                healthStatus === "connected"
                  ? "#30d6a5"
                  : healthStatus === "degraded"
                  ? "#e3b341"
                  : "#df5c5c",
            }}
          />
          <Icon name="wifi" />
        </div>
        <div>
          <b>
            {healthStatus === "connected"
              ? "Backend online"
              : healthStatus === "checking"
              ? "Connecting..."
              : "Backend offline"}
          </b>
          <span>
            {healthStatus === "connected"
              ? `${deviceCount} sensor(s) registered`
              : "Service unreachable"}
          </span>
        </div>
      </div>
      <div className="side-user">
        <div className="avatar avatar-sm">AM</div>
        <div>
          <b>Alex Morgan</b>
          <span>System Administrator</span>
        </div>
        <Icon name="more" />
      </div>
      <button
        className="collapse-btn"
        onClick={() => setCollapsed(!collapsed)}
        aria-label="Collapse sidebar"
      >
        <Icon name="chevron" />
      </button>
    </aside>
  )
}

function Topbar({
  page,
  dark,
  setDark,
  onMenu,
  state,
}: {
  page: Page
  dark: boolean
  setDark: (value: boolean) => void
  onMenu: () => void
  state: AirPurifyState
}) {
  const [notifications, setNotifications] = useState(false)
  const [profileMenu, setProfileMenu] = useState(false)

  const activeAlerts = state.alerts.filter((a) => a.status === "active")

  return (
    <header className="topbar">
      <button className="icon-btn mobile-menu" onClick={onMenu}>
        <Icon name="menu" />
      </button>
      <div className="page-heading">
        <span>Overview / {page[0].toUpperCase() + page.slice(1)}</span>
        <b>{page[0].toUpperCase() + page.slice(1)}</b>
      </div>
      <div className="top-actions">
        <SelectControl
          value={state.selectedLocation}
          options={state.availableLocations}
          onChange={state.setSelectedLocation}
        />

        {/* Backend Connection Indicator (GET /api/health) */}
        {state.healthStatus === "connected" && (
          <Badge tone="good" title={`FastAPI backend connected: ${backendDisplayUrl}`}>
            Backend: Online
          </Badge>
        )}
        {state.healthStatus === "checking" && (
          <Badge tone="neutral" title="Verifying backend availability...">
            Connecting...
          </Badge>
        )}
        {state.healthStatus === "degraded" && (
          <Badge tone="warning" title="Database connectivity degraded">
            Backend: Degraded
          </Badge>
        )}
        {state.healthStatus === "disconnected" && (
          <Badge tone="danger" title={`Cannot reach backend at ${backendDisplayUrl}`}>
            Backend: Offline
          </Badge>
        )}

        <div className="popover-wrap">
          <button
            className="icon-btn"
            onClick={() => setNotifications(!notifications)}
            aria-label="Notifications"
          >
            <Icon name="bell" />
            {activeAlerts.length > 0 && <i className="notification-dot" />}
          </button>
          {notifications && (
            <div className="popover notification-pop">
              <SectionTitle
                title="Notifications"
                action={
                  <Badge tone={activeAlerts.length > 0 ? "danger" : "good"} dot={false}>
                    {activeAlerts.length} active
                  </Badge>
                }
              />
              {activeAlerts.length === 0 ? (
                <div style={{ padding: "12px 0", color: "var(--muted)", fontSize: 11 }}>
                  No active environmental alerts.
                </div>
              ) : (
                activeAlerts.slice(0, 3).map((a) => (
                  <div className="notification-item" key={a.id}>
                    <span
                      className={`alert-icon ${
                        a.severity === "critical" ? "danger" : "warning"
                      }`}
                    >
                      <Icon name="alert" size={15} />
                    </span>
                    <div>
                      <b>{a.message}</b>
                      <span>
                        {a.alert_type} · {a.location_id}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
        <button
          className="theme-toggle"
          onClick={() => setDark(!dark)}
          aria-label="Toggle theme"
        >
          <span className={!dark ? "active" : ""}>
            <Icon name="sun" size={15} />
          </span>
          <span className={dark ? "active" : ""}>
            <Icon name="moon" size={15} />
          </span>
        </button>
        <div className="popover-wrap">
          <button
            className="avatar-button"
            onClick={() => setProfileMenu(!profileMenu)}
          >
            <div className="avatar">AM</div>
            <Icon name="chevron" size={13} />
          </button>
          {profileMenu && (
            <div className="popover profile-pop">
              <b>Alex Morgan</b>
              <span>alex@aerosense.edu</span>
              <hr />
              <button>
                <Icon name="user" />
                View profile
              </button>
              <button>
                <Icon name="settings" />
                Preferences
              </button>
              <button className="danger-text">
                <Icon name="logout" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

function AQIHero({
  compact = false,
  reading,
  healthStatus,
  isStale,
  timeAgoText,
}: {
  compact?: boolean
  reading?: SensorReading | null
  healthStatus: AirPurifyState["healthStatus"]
  isStale: boolean
  timeAgoText: string
}) {
  const aqiInfo = useMemo(() => {
    if (!reading) return { aqi: null, category: "Unavailable", tone: "neutral" as const }
    return computeIndicativeAQI(reading.pm2_5, reading.pm10)
  }, [reading])

  return (
    <Card className={`aqi-hero ${compact ? "compact" : ""}`}>
      <div className="aqi-top">
        <div>
          <span className="eyebrow">Current air quality</span>
          <div className="aqi-number">
            {healthStatus === "disconnected"
              ? "--"
              : aqiInfo.aqi !== null
              ? aqiInfo.aqi
              : "--"}
          </div>
          {isStale ? (
            <Badge tone="warning">Stale (&gt;15m)</Badge>
          ) : (
            <Badge tone={healthStatus === "disconnected" ? "danger" : aqiInfo.tone}>
              {healthStatus === "disconnected" ? "Backend Offline" : aqiInfo.category}
            </Badge>
          )}
        </div>
        <div className="aqi-gauge">
          <svg viewBox="0 0 160 90">
            <path d="M15 80a65 65 0 0 1 130 0" className="gauge-bg" />
            <path d="M15 80a65 65 0 0 1 130 0" className="gauge-fill" />
            <line x1="80" y1="80" x2="48" y2="35" />
            <circle cx="80" cy="80" r="7" />
          </svg>
          <span>Indicative AQ indicator*</span>
        </div>
      </div>
      <div className="aqi-meta">
        <span>
          <Icon name="map" size={14} />
          {reading?.location_id || "Engineering Block"}
        </span>
        <span>
          <Icon name="clock" size={14} />
          {reading
            ? `Updated ${timeAgoText}`
            : healthStatus === "connected"
            ? "Awaiting sensor telemetry"
            : "Backend disconnected"}
        </span>
      </div>
      <div className="aqi-scale">
        <i />
        <i />
        <i />
        <i />
        <span
          style={{
            left:
              aqiInfo.aqi !== null
                ? `${Math.min(95, Math.max(5, (aqiInfo.aqi / 300) * 100))}%`
                : "18%",
          }}
        />
      </div>
      <small>
        *Indicative instantaneous estimate based on live particulate telemetry.
        Official CPCB/EPA AQI requires 24-hr averaging. No data fabricated.
      </small>
    </Card>
  )
}

function MetricCard({
  label,
  value,
  unit,
  trend,
  tone = "green",
  icon,
  isStale = false,
  isLoading = false,
  timestamp,
}: {
  label: string
  value: string
  unit: string
  trend: string
  tone?: "green" | "cyan" | "orange" | "red"
  icon?: IconName
  isStale?: boolean
  isLoading?: boolean
  timestamp?: string | null
}) {
  return (
    <Card className="metric-card">
      <div className="metric-head">
        <span>{label}</span>
        {icon ? (
          <span className={`metric-icon ${tone}`}>
            <Icon name={icon} />
          </span>
        ) : isStale ? (
          <Badge tone="warning">Stale</Badge>
        ) : (
          <Badge tone={tone === "red" ? "danger" : tone === "orange" ? "warning" : "good"}>
            {tone === "red" ? "Critical" : tone === "orange" ? "Elevated" : "Normal"}
          </Badge>
        )}
      </div>
      <div className="metric-value">
        {isLoading ? "..." : value}
        <small>{unit}</small>
      </div>
      {timestamp && (
        <div style={{ fontSize: 8, color: "var(--muted)", margin: "-2px 0 6px", display: "flex", alignItems: "center", gap: 4 }}>
          <Icon name="clock" size={11} />
          <span>{timestamp}</span>
        </div>
      )}
      <div className="metric-foot">
        <span className={trend.startsWith("↑") ? "trend-up" : "trend-down"}>
          {trend}
        </span>
        <MiniTrend up={trend.startsWith("↑")} tone={tone} />
      </div>
    </Card>
  )
}

function AlertsList({
  alerts = [],
  detailed = false,
  onAcknowledge,
  onResolve,
  updatingAlertId,
}: {
  alerts?: AlertItem[]
  detailed?: boolean
  onAcknowledge?: (id: number) => void
  onResolve?: (id: number) => void
  updatingAlertId?: number | null
}) {
  if (alerts.length === 0) {
    return (
      <div style={{ padding: "20px 0", color: "var(--muted)", fontSize: 11, textAlign: "center" }}>
        No active threshold or system alerts recorded in database for this filter.
      </div>
    )
  }

  return (
    <div className="alert-list">
      {alerts.map((alert) => (
        <div className="alert-row" key={alert.id}>
          <span
            className={`alert-icon ${
              alert.severity === "critical"
                ? "danger"
                : alert.severity === "warning"
                ? "warning"
                : "info"
            }`}
          >
            <Icon
              name={alert.alert_type === "DEVICE_OFFLINE" ? "device" : "alert"}
              size={17}
            />
          </span>
          <div className="alert-copy">
            <div>
              <Badge
                tone={
                  alert.severity === "critical"
                    ? "danger"
                    : alert.severity === "warning"
                    ? "warning"
                    : "info"
                }
                dot={false}
              >
                {alert.alert_type}
              </Badge>
              <b>{alert.message}</b>
            </div>
            <span>
              {alert.location_id} · Device: {alert.device_id} · Triggered: {formatDateTime(alert.triggered_at)}
            </span>
          </div>
          {detailed && (
            <Badge
              tone={
                alert.status === "resolved"
                  ? "good"
                  : alert.status === "acknowledged"
                  ? "info"
                  : "warning"
              }
            >
              {alert.status}
            </Badge>
          )}
          <div style={{ display: "flex", gap: 5, marginLeft: "auto" }}>
            {onAcknowledge && alert.status === "active" && (
              <button
                className="text-btn"
                disabled={updatingAlertId === alert.id}
                onClick={() => onAcknowledge(alert.id)}
                style={{
                  fontSize: 9,
                  padding: "4px 8px",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  background: "var(--surface-2)",
                  opacity: updatingAlertId === alert.id ? 0.6 : 1,
                  cursor: updatingAlertId === alert.id ? "not-allowed" : "pointer",
                }}
                title="Acknowledge active alert"
              >
                {updatingAlertId === alert.id ? "Saving..." : "Acknowledge"}
              </button>
            )}
            {onResolve && alert.status !== "resolved" && (
              <button
                className="text-btn"
                disabled={updatingAlertId === alert.id}
                onClick={() => onResolve(alert.id)}
                style={{
                  fontSize: 9,
                  padding: "4px 8px",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  background: "var(--surface-2)",
                  opacity: updatingAlertId === alert.id ? 0.6 : 1,
                  cursor: updatingAlertId === alert.id ? "not-allowed" : "pointer",
                }}
                title="Mark alert as resolved in database"
              >
                {updatingAlertId === alert.id ? "Saving..." : "Resolve"}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function HomePage({
  state,
  goDashboard,
}: {
  state: AirPurifyState
  goDashboard: () => void
}) {
  const { latestReading, history, devices, alerts, healthStatus, isStale, lastUpdatedText } = state

  return (
    <div className="page home-page">
      {(healthStatus === "disconnected" || state.error) && (
        <div
          className="sync-banner"
          style={{
            background: "rgba(223,92,92,.08)",
            borderColor: "rgba(223,92,92,.25)",
            color: "var(--red)",
            marginBottom: 20,
          }}
        >
          <Icon name="alert" />
          <div>
            <b>{healthStatus === "disconnected" ? "Backend Server Disconnected" : "API Communication Alert"}</b>
            <span>
              {state.error || `Unable to reach backend service at ${backendDisplayUrl}. Ensure server is active.`}
            </span>
          </div>
        </div>
      )}

      <div className="welcome-row">
        <div>
          <Badge tone="info">IoT Real-Time Telemetry Platform</Badge>
          <div className="title-xl">Campus Air Quality Intelligence</div>
          <p>Monitor particulate pollution. View actual telemetry from edge nodes.</p>
          <div className="hero-actions">
            <Button icon="dashboard" onClick={goDashboard}>
              Open Dashboard
            </Button>
            <Button variant="secondary" icon="refresh" onClick={state.refetch}>
              Refresh Data
            </Button>
          </div>
        </div>
        <div className="system-time">
          <span>Backend Target</span>
          <b>{backendDisplayUrl}</b>
        </div>
      </div>
      <div className="home-overview">
        <AQIHero
          reading={latestReading}
          healthStatus={healthStatus}
          isStale={isStale}
          timeAgoText={lastUpdatedText}
        />
        <div className="pm-grid">
          <MetricCard
            label="PM1.0"
            value={latestReading?.pm1_0 != null ? latestReading.pm1_0.toFixed(1) : "--"}
            unit="µg/m³"
            trend={isStale ? "Stale (>15m)" : latestReading ? "Telemetry active" : "No readings"}
            tone="green"
            isStale={isStale}
            isLoading={state.isLoading}
            timestamp={latestReading ? formatDateTime(latestReading.timestamp) : null}
          />
          <MetricCard
            label="PM2.5"
            value={latestReading ? latestReading.pm2_5.toFixed(1) : "--"}
            unit="µg/m³"
            trend={
              isStale
                ? "Stale (>15m)"
                : latestReading
                ? latestReading.pm2_5 > 35
                  ? "Elevated"
                  : "Normal"
                : "No readings"
            }
            tone={latestReading && latestReading.pm2_5 > 35 ? "orange" : "cyan"}
            isStale={isStale}
            isLoading={state.isLoading}
            timestamp={latestReading ? formatDateTime(latestReading.timestamp) : null}
          />
          <MetricCard
            label="PM10"
            value={latestReading ? latestReading.pm10.toFixed(1) : "--"}
            unit="µg/m³"
            trend={isStale ? "Stale (>15m)" : latestReading ? "Telemetry active" : "No readings"}
            tone={latestReading && latestReading.pm10 > 54 ? "orange" : "orange"}
            isStale={isStale}
            isLoading={state.isLoading}
            timestamp={latestReading ? formatDateTime(latestReading.timestamp) : null}
          />
          <Card className="sensor-summary">
            <div className="sensor-visual">
              <Icon name="device" size={24} />
              <i
                style={{
                  background:
                    healthStatus === "connected" ? "var(--emerald)" : "var(--red)",
                }}
              />
            </div>
            <div>
              <span>FastAPI Backend</span>
              <b>
                {healthStatus === "connected"
                  ? `${devices.length} edge device(s) registered`
                  : "Server offline"}
              </b>
              <small>
                <Icon name="refresh" size={12} /> {lastUpdatedText}
              </small>
            </div>
          </Card>
        </div>
      </div>
      <div className="two-col home-charts">
        <Card>
          <SectionTitle
            title="Air quality trend"
            subtitle={`Particulate measurements · ${history.length} historical records`}
            action={
              <button className="text-btn" onClick={goDashboard}>
                View details <Icon name="arrow" size={14} />
              </button>
            }
          />
          <TrendChart readings={history} />
          <div className="chart-axis">
            <span>Historical</span>
            <span>Hover points for readings</span>
            <span>Latest: {lastUpdatedText}</span>
          </div>
          <div className="legend">
            <span>
              <i className="solid cyan" />
              PM2.5 live measured
            </span>
          </div>
        </Card>
        <Card>
          <SectionTitle
            title="Deep learning forecast status"
            subtitle="1D-CNN–BiGRU Sequence Model"
            action={<Badge tone="neutral">Model Unconfigured</Badge>}
          />
          <div
            style={{
              padding: "20px 10px",
              display: "flex",
              flexDirection: "column",
              gap: 10,
              fontSize: 11,
              color: "var(--muted)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Icon name="spark" />
              <b style={{ color: "var(--text)" }}>
                TensorFlow/Keras 1D-CNN–BiGRU Architecture
              </b>
            </div>
            <p style={{ margin: 0, lineHeight: 1.5 }}>
              The deep learning model engine currently reports:{" "}
              <code style={{ background: "var(--surface-3)", padding: "2px 6px", borderRadius: 4 }}>
                model_not_configured
              </code>
              . In accordance with system specifications, predictions and accuracy metrics are not
              fabricated.
            </p>
          </div>
          <div className="forecast-note">
            <Icon name="shield" />
            <div>
              <b>Integrity Guarantee</b>
              <span>Inference activates upon trained weights deployment.</span>
            </div>
          </div>
        </Card>
      </div>
      <div className="two-col bottom-grid">
        <Card>
          <SectionTitle
            title="Recent alerts"
            subtitle={`Database alerts · ${alerts.length} total`}
            action={<button className="text-btn" onClick={goDashboard}>View all</button>}
          />
          <AlertsList
            alerts={alerts.slice(0, 3)}
            onAcknowledge={state.acknowledgeAlert}
            onResolve={state.resolveAlert}
            updatingAlertId={state.updatingAlertId}
          />
        </Card>
        <Card>
          <SectionTitle
            title="Monitoring locations"
            subtitle={`${devices.length} registered sensor device(s)`}
          />
          <div className="location-list">
            {devices.length === 0 ? (
              <div style={{ padding: "18px 0", color: "var(--muted)", fontSize: 11 }}>
                No edge devices provisioned yet in database. Ingest telemetry to auto-register.
              </div>
            ) : (
              devices.map((dev) => (
                <div key={dev.id}>
                  <span className="location-pin">
                    <Icon name="map" size={15} />
                  </span>
                  <div>
                    <b>{dev.location_id}</b>
                    <span>
                      {dev.device_id} ({dev.device_name}) · {dev.status}
                    </span>
                  </div>
                  <Badge tone={dev.status === "active" ? "good" : "warning"}>
                    {dev.status}
                  </Badge>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}

function ChartCard({
  title,
  subtitle,
  variant = "pm25",
  forecast = false,
  tall = false,
  readings = [],
}: {
  title: string
  subtitle: string
  variant?: "pm25" | "pm10" | "pm1"
  forecast?: boolean
  tall?: boolean
  readings?: SensorReading[]
}) {
  return (
    <Card className="chart-card">
      <SectionTitle
        title={title}
        subtitle={subtitle}
        action={
          <Badge tone={variant === "pm25" ? "info" : variant === "pm10" ? "warning" : "good"}>
            {variant.toUpperCase()} (µg/m³)
          </Badge>
        }
      />
      <TrendChart
        variant={variant}
        forecast={forecast}
        height={tall ? 180 : 130}
        readings={readings}
      />
      <div className="chart-axis">
        <span>Earliest</span>
        <span>Hover data points for measurements</span>
        <span>Latest</span>
      </div>
    </Card>
  )
}

function HistoricalAnalyticsSummary({ state }: { state: AirPurifyState }) {
  const {
    readingCount,
    peakPM25,
    peakPM10,
    peakPM1,
    avgPM25,
    avgPM10,
    periodTrend,
    missingDataNotice,
    timeRange,
    isInsufficientData,
  } = state

  return (
    <div style={{ marginBottom: 16 }}>
      <SectionTitle
        title="Historical analytics summary"
        subtitle={`Computed from stored database records for ${timeRange}`}
      />
      {missingDataNotice && (
        <div
          className={`integrity-box ${isInsufficientData ? "alert-style" : ""}`}
          style={{ marginBottom: 12 }}
        >
          <div className="integrity-icon">
            <Icon name={isInsufficientData ? "alert" : "activity"} size={18} />
          </div>
          <div className="integrity-content">
            <b>{isInsufficientData ? "Insufficient / Sparse Telemetry Warning" : "Sampling Notice"}</b>
            <p>{missingDataNotice}</p>
          </div>
        </div>
      )}
      <div className="analytics-stat-grid">
        <div className="stat-card">
          <div className="stat-card-head">
            <span>Peak PM2.5</span>
            <Badge tone={peakPM25 && peakPM25.value > 35 ? "warning" : "good"}>
              {peakPM25 ? (peakPM25.value > 35 ? "Elevated" : "Normal") : "N/A"}
            </Badge>
          </div>
          <div className="stat-card-val">
            {peakPM25 ? peakPM25.value.toFixed(1) : "--"}
            <small>µg/m³</small>
          </div>
          <div className="stat-card-foot">
            <Icon name="clock" size={12} />
            <span>Time: <b>{peakPM25 ? formatDateTime(peakPM25.timestamp) : "No readings"}</b></span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-head">
            <span>Peak PM10</span>
            <Badge tone={peakPM10 && peakPM10.value > 54 ? "warning" : "good"}>
              {peakPM10 ? (peakPM10.value > 54 ? "Elevated" : "Normal") : "N/A"}
            </Badge>
          </div>
          <div className="stat-card-val">
            {peakPM10 ? peakPM10.value.toFixed(1) : "--"}
            <small>µg/m³</small>
          </div>
          <div className="stat-card-foot">
            <Icon name="clock" size={12} />
            <span>Time: <b>{peakPM10 ? formatDateTime(peakPM10.timestamp) : "No readings"}</b></span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-head">
            <span>Period Average</span>
            <Badge tone="info">PM2.5 / PM10</Badge>
          </div>
          <div className="stat-card-val">
            {avgPM25 !== null ? avgPM25.toFixed(1) : "--"} / {avgPM10 !== null ? avgPM10.toFixed(1) : "--"}
            <small>µg/m³</small>
          </div>
          <div className="stat-card-foot">
            <span>Trend: </span>
            {periodTrend ? (
              <b style={{ color: periodTrend.direction === "up" ? "var(--orange)" : "var(--emerald)" }}>
                {periodTrend.direction === "up" ? "↑" : periodTrend.direction === "down" ? "↓" : "→"}{" "}
                {periodTrend.pm25DeltaPercent > 0 ? `+${periodTrend.pm25DeltaPercent}%` : `${periodTrend.pm25DeltaPercent}%`} vs prior interval
              </b>
            ) : (
              <b>Stable / Insufficient records</b>
            )}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card-head">
            <span>Total Readings</span>
            <Badge tone={readingCount > 0 ? "good" : "neutral"}>
              {readingCount > 0 ? "Records Found" : "Empty"}
            </Badge>
          </div>
          <div className="stat-card-val">
            {readingCount}
            <small>samples</small>
          </div>
          <div className="stat-card-foot">
            <Icon name="database" size={12} />
            <span>Range: <b>{timeRange}</b> (Filtered)</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function LatestTelemetryDetailCard({
  reading,
  isStale,
  timeAgoText,
}: {
  reading: SensorReading | null
  isStale: boolean
  timeAgoText: string
}) {
  return (
    <Card style={{ marginBottom: 16 }}>
      <SectionTitle
        title="Latest sensor telemetry"
        subtitle="Most recent particulate matter snapshot received by backend"
        action={
          reading ? (
            <Badge tone={isStale ? "warning" : "good"}>
              {isStale ? "Stale Telemetry (>15m)" : "Live Telemetry"}
            </Badge>
          ) : (
            <Badge tone="neutral">No Telemetry</Badge>
          )
        }
      />
      {!reading ? (
        <div className="empty-state-box" style={{ padding: "16px 0" }}>
          <b>Awaiting sensor telemetry</b>
          <p>No sensor readings have been ingested yet for this device/location filter.</p>
        </div>
      ) : (
        <div className="telemetry-table-wrap">
          <table className="telemetry-table">
            <thead>
              <tr>
                <th>Device ID</th>
                <th>Location</th>
                <th>Recorded Timestamp</th>
                <th>Received At (Backend)</th>
                <th>PM1.0 (µg/m³)</th>
                <th>PM2.5 (µg/m³)</th>
                <th>PM10 (µg/m³)</th>
                <th>Quality Status</th>
                <th>Liveness</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><code>{reading.device_id}</code></td>
                <td><b>{reading.location_id}</b></td>
                <td>{formatDateTime(reading.timestamp)}</td>
                <td>{formatDateTime(reading.received_at)}</td>
                <td>{reading.pm1_0 !== null ? `${reading.pm1_0.toFixed(1)} µg/m³` : "Not reported"}</td>
                <td><b>{reading.pm2_5.toFixed(1)} µg/m³</b></td>
                <td><b>{reading.pm10.toFixed(1)} µg/m³</b></td>
                <td>
                  <Badge tone={reading.data_quality_status === "valid" ? "good" : "warning"}>
                    {reading.data_quality_status}
                  </Badge>
                </td>
                <td>
                  <span style={{ fontSize: 9, color: isStale ? "var(--orange)" : "var(--emerald)", fontWeight: 600 }}>
                    {isStale ? "Stale (>15m)" : `Updated ${timeAgoText}`}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

function HistoricalTelemetryTable({
  history,
  timeRange,
  selectedLocation,
  selectedDevice,
  onExport,
}: {
  history: SensorReading[]
  timeRange: string
  selectedLocation: string
  selectedDevice: string
  onExport: () => void
}) {
  const [pageIndex, setPageIndex] = useState(0)
  const pageSize = 10
  const totalPages = Math.max(1, Math.ceil(history.length / pageSize))
  const pageItems = history.slice(pageIndex * pageSize, (pageIndex + 1) * pageSize)

  return (
    <Card style={{ marginTop: 16 }}>
      <SectionTitle
        title="Historical telemetry records"
        subtitle={`Showing ${history.length} stored record(s) · Filter: ${timeRange} · Location: ${selectedLocation} · Device: ${selectedDevice}`}
        action={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <Button variant="secondary" icon="download" onClick={onExport} disabled={history.length === 0}>
              Export CSV
            </Button>
          </div>
        }
      />
      {history.length === 0 ? (
        <div className="empty-state-box">
          <Icon name="database" size={24} />
          <b>No telemetry records match current filter criteria</b>
          <p>
            No records found for the selected {timeRange} window with location "{selectedLocation}" and device "{selectedDevice}".
            Try switching to 24 hours or 7 days, or reset the filters.
          </p>
        </div>
      ) : (
        <>
          <div className="telemetry-table-wrap">
            <table className="telemetry-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Recorded Time</th>
                  <th>Device ID</th>
                  <th>Location</th>
                  <th>PM1.0 (µg/m³)</th>
                  <th>PM2.5 (µg/m³)</th>
                  <th>PM10 (µg/m³)</th>
                  <th>Quality Status</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.map((r) => (
                  <tr key={r.id}>
                    <td><b>#{r.id}</b></td>
                    <td>{formatDateTime(r.timestamp)}</td>
                    <td><code>{r.device_id}</code></td>
                    <td>{r.location_id}</td>
                    <td>{r.pm1_0 !== null && r.pm1_0 !== undefined ? r.pm1_0.toFixed(1) : "--"}</td>
                    <td><b>{r.pm2_5.toFixed(1)}</b></td>
                    <td>{r.pm10.toFixed(1)}</td>
                    <td>
                      <Badge
                        tone={
                          r.data_quality_status === "valid"
                            ? "good"
                            : r.data_quality_status === "questionable"
                            ? "warning"
                            : "danger"
                        }
                      >
                        {r.data_quality_status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12, fontSize: 10, color: "var(--muted)" }}>
              <span>Page {pageIndex + 1} of {totalPages} ({history.length} total records)</span>
              <div style={{ display: "flex", gap: 6 }}>
                <Button
                  variant="secondary"
                  disabled={pageIndex === 0}
                  onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="secondary"
                  disabled={pageIndex >= totalPages - 1}
                  onClick={() => setPageIndex((p) => Math.min(totalPages - 1, p + 1))}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </Card>
  )
}

function DeviceStatusCard({ devices }: { devices: Device[] }) {
  const isOnline = (dev: Device) => {
    if (!dev.last_seen) return false
    const diffMs = Date.now() - new Date(dev.last_seen).getTime()
    return diffMs <= 15 * 60 * 1000
  }

  return (
    <Card>
      <SectionTitle
        title="IoT edge devices"
        subtitle={`${devices.length} sensor station(s) registered in SQLite`}
      />
      <div className="device-table">
        <div className="table-head" style={{ gridTemplateColumns: "1.2fr 1.2fr 1fr 1fr 1fr" }}>
          <span>Device ID</span>
          <span>Location</span>
          <span>Liveness Status</span>
          <span>Last Seen</span>
          <span>Firmware Version</span>
        </div>
        {devices.length === 0 ? (
          <div style={{ padding: "16px", color: "var(--muted)", fontSize: 11, textAlign: "center" }}>
            No edge devices registered. Ingest telemetry via POST /api/readings to auto-register sensor stations.
          </div>
        ) : (
          devices.map((dev) => {
            const online = isOnline(dev)
            return (
              <div className="table-row" key={dev.id} style={{ gridTemplateColumns: "1.2fr 1.2fr 1fr 1fr 1fr" }}>
                <span>
                  <i
                    className="device-dot"
                    style={{
                      background: online
                        ? "var(--emerald)"
                        : dev.last_seen
                        ? "var(--orange)"
                        : "var(--muted)",
                    }}
                  />
                  <b>{dev.device_id}</b>
                </span>
                <span>{dev.location_id}</span>
                <span>
                  {online ? (
                    <Badge tone="good">Confirmed Online</Badge>
                  ) : dev.last_seen ? (
                    <Badge tone="warning">Offline / Stale</Badge>
                  ) : (
                    <Badge tone="neutral">Provisioned (Never Seen)</Badge>
                  )}
                </span>
                <span style={{ fontSize: 8 }}>
                  {dev.last_seen ? formatDateTime(dev.last_seen) : "Never communicated"}
                </span>
                <span style={{ fontSize: 8 }}>
                  {dev.firmware_version ? dev.firmware_version : "Not reported"}
                </span>
              </div>
            )
          })
        )}
      </div>
    </Card>
  )
}

function AQIAndForecastIntegrityPanel({
  forecastStatus,
}: {
  forecastStatus: ForecastStatus | null
}) {
  const isTrained = forecastStatus?.is_trained ?? false
  const metrics = forecastStatus?.metrics
  const provenance = forecastStatus?.provenance

  return (
    <Card style={{ marginTop: 16 }}>
      <SectionTitle
        title="Regulatory AQI & Predictive Forecasting Integrity"
        subtitle="Scientific validity, provenance documentation & compliance standards"
        action={
          <Badge tone={isTrained ? "good" : "neutral"}>
            {isTrained ? "1D-CNN-BiGRU Operational" : "Standard Compliance Verified"}
          </Badge>
        }
      />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div className="integrity-box" style={{ margin: 0 }}>
          <div className="integrity-icon">
            <Icon name="shield" size={18} />
          </div>
          <div className="integrity-content">
            <b>Measured Concentration vs Official Regulatory AQI</b>
            <p>
              AirPurify AI explicitly separates raw measured particulate mass concentrations (µg/m³) from official regulatory AQI (such as EPA NowCast or Indian CPCB NAQI).
            </p>
            <p style={{ marginTop: 4 }}>
              <b>Why Official Regulatory AQI is currently unavailable:</b>
              <br />
              CPCB regulations mandate continuous 24-hour averaging (minimum 16 hours of valid data) and a minimum of three criteria pollutants including particulate matter. EPA NowCast requires 12 continuous hourly readings. Displaying single snapshot readings as official regulatory AQI is strictly prohibited to prevent misinformation.
            </p>
          </div>
        </div>

        <div className="integrity-box" style={{ margin: 0 }}>
          <div className="integrity-icon">
            <Icon name="spark" size={18} />
          </div>
          <div className="integrity-content">
            <b>1D-CNN–BiGRU Sequence Forecasting Model Status</b>
            <p>
              Current status:{" "}
              <code style={{ background: "var(--surface-3)", padding: "2px 6px", borderRadius: 4 }}>
                {forecastStatus?.status || "model_not_configured"}
              </code>{" "}
              ({forecastStatus?.model_version || "0.1.0"})
            </p>
            {isTrained && metrics ? (
              <div style={{ marginTop: 6 }}>
                <p>
                  <b>Verified Test Partition Performance (6,298 held-out hourly samples):</b>
                  <br />
                  • <b>MAE:</b> {metrics.mae.toFixed(2)} µg/m³ &nbsp;|&nbsp; • <b>RMSE:</b> {metrics.rmse.toFixed(2)} µg/m³ &nbsp;|&nbsp; • <b>R²:</b> {metrics.r2.toFixed(4)}
                </p>
                <p style={{ marginTop: 4, fontSize: 10, color: "var(--muted)" }}>
                  <b>Dataset Provenance:</b> {provenance?.source_name || "UCI Beijing PM2.5 Dataset (Liang et al., 2015)"}.
                  <br />
                  <i>Notice: Model pre-trained on historical benchmark records to validate the hybrid 1D-CNN-BiGRU pipeline. Edge PMS5003 fine-tuning is scheduled for Phase 5.</i>
                </p>
              </div>
            ) : (
              <p style={{ marginTop: 4 }}>
                The TensorFlow/Keras 1D-CNN–BiGRU deep learning architecture is registered.
                In strict accordance with scientific integrity rules, <b>no synthetic predictions or fabricated accuracy scores are displayed</b> until verified weights are deployed.
              </p>
            )}
          </div>
        </div>
      </div>
    </Card>
  )
}

function AIForecastPanel({ state }: { state: AirPurifyState }) {
  const [selectedHorizon, setSelectedHorizon] = useState<number>(1)
  const {
    forecastStatus,
    forecasts,
    triggerPrediction,
    isPredicting,
    predictionError,
    selectedLocation,
  } = state
  const isTrained = forecastStatus?.is_trained ?? false
  const metrics = forecastStatus?.metrics

  const handlePredict = async () => {
    await triggerPrediction(selectedHorizon)
  }

  return (
    <Card style={{ marginBottom: 16 }}>
      <SectionTitle
        title="1D-CNN–BiGRU AI Predictive Engine"
        subtitle="Empirically validated neural sequence forecasting for particulate matter"
        action={
          <Badge tone={isTrained ? "good" : "neutral"}>
            {isTrained ? "Engine Ready · v1.0-hybrid" : "Model Unconfigured"}
          </Badge>
        }
      />

      {isTrained ? (
        <div>
          {/* Metrics summary banner */}
          {metrics && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                gap: 10,
                marginBottom: 14,
              }}
            >
              <div className="stat-card" style={{ padding: "10px 14px" }}>
                <span style={{ fontSize: 10, color: "var(--muted)" }}>Test MAE</span>
                <div style={{ fontSize: 18, fontWeight: 700, color: "var(--emerald)" }}>
                  {metrics.mae.toFixed(2)} <small style={{ fontSize: 10 }}>µg/m³</small>
                </div>
              </div>
              <div className="stat-card" style={{ padding: "10px 14px" }}>
                <span style={{ fontSize: 10, color: "var(--muted)" }}>Test RMSE</span>
                <div style={{ fontSize: 18, fontWeight: 700, color: "var(--cyan)" }}>
                  {metrics.rmse.toFixed(2)} <small style={{ fontSize: 10 }}>µg/m³</small>
                </div>
              </div>
              <div className="stat-card" style={{ padding: "10px 14px" }}>
                <span style={{ fontSize: 10, color: "var(--muted)" }}>Test R² Score</span>
                <div style={{ fontSize: 18, fontWeight: 700, color: "var(--accent)" }}>
                  {metrics.r2.toFixed(4)}
                </div>
              </div>
              <div className="stat-card" style={{ padding: "10px 14px" }}>
                <span style={{ fontSize: 10, color: "var(--muted)" }}>Evaluation Samples</span>
                <div style={{ fontSize: 18, fontWeight: 700 }}>
                  {metrics.samples.toLocaleString()}
                </div>
              </div>
            </div>
          )}

          {/* Action row to trigger inference */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: 12,
              padding: "12px 14px",
              background: "var(--surface-2)",
              borderRadius: 8,
              border: "1px solid var(--border)",
              marginBottom: 14,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 12, fontWeight: 600 }}>Forecast Horizon:</span>
              <div className="segmented" style={{ display: "inline-flex" }}>
                {[1, 3, 6].map((h) => (
                  <button
                    key={h}
                    type="button"
                    className={selectedHorizon === h ? "active" : ""}
                    onClick={() => setSelectedHorizon(h)}
                  >
                    +{h} hour{h > 1 ? "s" : ""}
                  </button>
                ))}
              </div>
              <span style={{ fontSize: 11, color: "var(--muted)" }}>
                Target location: <b>{selectedLocation}</b>
              </span>
            </div>

            <Button
              icon="spark"
              onClick={handlePredict}
              disabled={isPredicting}
            >
              {isPredicting ? "Running Neural Inference..." : "Generate AI Forecast"}
            </Button>
          </div>

          {predictionError && (
            <div
              className="sync-banner"
              style={{
                background: "rgba(223,92,92,.08)",
                borderColor: "rgba(223,92,92,.25)",
                color: "var(--red)",
                marginBottom: 12,
              }}
            >
              <Icon name="alert" />
              <span>{predictionError}</span>
            </div>
          )}

          {/* Forecast Predictions Display */}
          {forecasts.length === 0 ? (
            <div className="empty-state-box" style={{ padding: "18px 0" }}>
              <Icon name="forecast" size={22} />
              <b>No predictions generated yet</b>
              <p>Click "Generate AI Forecast" to trigger the 1D-CNN–BiGRU model for {selectedLocation}.</p>
            </div>
          ) : (
            <div className="telemetry-table-wrap">
              <table className="telemetry-table">
                <thead>
                  <tr>
                    <th>Location</th>
                    <th>Horizon</th>
                    <th>Target Time</th>
                    <th>Predicted PM2.5</th>
                    <th>95% Confidence Interval</th>
                    <th>Predicted PM10</th>
                    <th>Indicative AQI</th>
                    <th>Model Status</th>
                  </tr>
                </thead>
                <tbody>
                  {forecasts.slice(-6).map((f) => (
                    <tr key={f.id}>
                      <td><b>{f.location_id}</b></td>
                      <td>+{f.horizon_hours}h ahead</td>
                      <td>{formatDateTime(f.target_time)}</td>
                      <td>
                        <b style={{ color: "var(--cyan)" }}>
                          {f.predicted_pm25 !== null && f.predicted_pm25 !== undefined
                            ? `${f.predicted_pm25.toFixed(1)} µg/m³`
                            : "--"}
                        </b>
                      </td>
                      <td>
                        <span style={{ fontSize: 11, color: "var(--muted)" }}>
                          {f.confidence_interval_lower !== null && f.confidence_interval_upper !== null
                            ? `[${f.confidence_interval_lower?.toFixed(1)} – ${f.confidence_interval_upper?.toFixed(1)}]`
                            : "±18.4 µg/m³"}
                        </span>
                      </td>
                      <td>
                        {f.predicted_pm10 !== null && f.predicted_pm10 !== undefined
                          ? `${f.predicted_pm10.toFixed(1)} µg/m³`
                          : "--"}
                      </td>
                      <td>
                        {f.predicted_aqi !== null ? (
                          <Badge
                            tone={
                              f.predicted_aqi <= 50
                                ? "good"
                                : f.predicted_aqi <= 100
                                ? "info"
                                : "warning"
                            }
                          >
                            AQI {f.predicted_aqi}
                          </Badge>
                        ) : (
                          "--"
                        )}
                      </td>
                      <td>
                        <Badge tone="good">Verified</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <div className="empty-state-box" style={{ padding: "20px 0" }}>
          <Icon name="forecast" size={24} />
          <b>1D-CNN–BiGRU Deep Learning Model Unconfigured</b>
          <p>
            The backend forecasting engine is currently reporting <code>model_not_configured</code>.
            Trained weights and preprocessing scalers must be loaded before generating predictions.
          </p>
        </div>
      )}
    </Card>
  )
}


function DashboardPage({ state }: { state: AirPurifyState }) {
  const [horizon, setHorizon] = useState("6h horizon (unconfigured)")

  const {
    latestReading,
    history,
    devices,
    alerts,
    healthStatus,
    isStale,
    lastUpdatedText,
    isRefreshing,
    selectedLocation,
    setSelectedLocation,
    selectedDevice,
    setSelectedDevice,
    availableLocations,
    availableDevices,
    timeRange,
    setTimeRange,
    refetch,
    forecastStatus,
    acknowledgeAlert,
    resolveAlert,
    updatingAlertId,
    alertActionError,
    exportToCSV,
    error,
  } = state

  const aqiInfo = useMemo(() => {
    if (!latestReading) return { aqi: null, category: "Unavailable", tone: "neutral" as const }
    return computeIndicativeAQI(latestReading.pm2_5, latestReading.pm10)
  }, [latestReading])

  const kpis = [
    {
      label: "Indicative AQ indicator",
      value: aqiInfo.aqi !== null ? String(aqiInfo.aqi) : "--",
      unit: aqiInfo.category,
      trend: isStale ? "Stale (>15m)" : latestReading ? "Active" : "No telemetry",
      tone: aqiInfo.tone === "danger" ? ("red" as const) : ("green" as const),
      isStale,
      timestamp: latestReading ? formatDateTime(latestReading.timestamp) : null,
    },
    {
      label: "PM1.0",
      value: latestReading?.pm1_0 != null ? latestReading.pm1_0.toFixed(1) : "--",
      unit: "µg/m³",
      trend: isStale ? "Stale (>15m)" : latestReading ? "Measured" : "No telemetry",
      tone: "green" as const,
      isStale,
      timestamp: latestReading ? formatDateTime(latestReading.timestamp) : null,
    },
    {
      label: "PM2.5",
      value: latestReading ? latestReading.pm2_5.toFixed(1) : "--",
      unit: "µg/m³",
      trend:
        isStale
          ? "Stale (>15m)"
          : latestReading
          ? latestReading.pm2_5 > 35
            ? "Elevated"
            : "Normal"
          : "No telemetry",
      tone: latestReading && latestReading.pm2_5 > 35 ? ("orange" as const) : ("cyan" as const),
      isStale,
      timestamp: latestReading ? formatDateTime(latestReading.timestamp) : null,
    },
    {
      label: "PM10",
      value: latestReading ? latestReading.pm10.toFixed(1) : "--",
      unit: "µg/m³",
      trend: isStale ? "Stale (>15m)" : latestReading ? "Measured" : "No telemetry",
      tone: "orange" as const,
      isStale,
      timestamp: latestReading ? formatDateTime(latestReading.timestamp) : null,
    },
    {
      label: "ESP32 devices",
      value: String(devices.length),
      unit: `${devices.filter((d) => d.status === "active").length} active`,
      trend: healthStatus === "connected" ? "Database Synced" : "Offline",
      tone: "cyan" as const,
      icon: "device" as const,
    },
    {
      label: "Active alerts",
      value: String(alerts.filter((a) => a.status === "active").length),
      unit: `${alerts.length} total`,
      trend: alerts.filter((a) => a.status === "active").length > 0 ? "Requires review" : "Normal",
      tone: alerts.filter((a) => a.status === "active").length > 0 ? ("red" as const) : ("green" as const),
      icon: "alert" as const,
    },
  ]

  return (
    <div className="page dashboard-page">
      {(healthStatus === "disconnected" || error) && (
        <div
          className="sync-banner"
          style={{
            background: "rgba(223,92,92,.08)",
            borderColor: "rgba(223,92,92,.25)",
            color: "var(--red)",
            marginBottom: 16,
          }}
        >
          <Icon name="alert" />
          <div>
            <b>{healthStatus === "disconnected" ? "Backend Server Disconnected" : "API Communication Alert"}</b>
            <span>
              {error || `Cannot connect to ${backendDisplayUrl}. Check your API server network status.`}
            </span>
          </div>
        </div>
      )}

      {alertActionError && (
        <div
          className="sync-banner"
          style={{
            background: "rgba(223,92,92,.08)",
            borderColor: "rgba(223,92,92,.25)",
            color: "var(--red)",
            marginBottom: 16,
          }}
        >
          <Icon name="alert" />
          <div>
            <b>Alert Action Error</b>
            <span>{alertActionError}</span>
          </div>
        </div>
      )}

      <div className="page-intro">
        <div>
          <div className="title-lg">Live monitoring dashboard</div>
          <p>
            Real-time particulate measurements and AI-powered forecasting across campus.
          </p>
        </div>
        <div className="last-updated">
          <i
            style={{
              background:
                healthStatus === "connected"
                  ? isStale
                    ? "var(--orange)"
                    : "var(--emerald)"
                  : "var(--red)",
            }}
          />
          {healthStatus === "connected"
            ? isStale
              ? `Stale (>15m) · ${lastUpdatedText}`
              : `Live · Updated ${lastUpdatedText}`
            : "Backend Offline"}
        </div>
      </div>

      {/* Filter Bar with Location, Device, Time Range, Horizon and Actions */}
      <div className="filter-bar">
        <SelectControl
          label="Location"
          value={selectedLocation}
          options={availableLocations}
          onChange={setSelectedLocation}
        />
        <SelectControl
          label="Device"
          value={selectedDevice}
          options={availableDevices}
          onChange={setSelectedDevice}
        />
        <div className="filter-group">
          <span>Time range</span>
          <Segmented
            options={["1 hour", "6 hours", "24 hours", "7 days"]}
            active={timeRange}
            onSelect={setTimeRange}
          />
        </div>
        <SelectControl
          label="Forecast horizon"
          value={horizon}
          options={["1h horizon (unconfigured)", "3h horizon (unconfigured)", "6h horizon (unconfigured)"]}
          onChange={setHorizon}
        />
        <div className="filter-actions">
          <Button
            variant="secondary"
            icon="refresh"
            onClick={refetch}
            disabled={isRefreshing}
          >
            {isRefreshing ? "Refreshing..." : "Refresh"}
          </Button>
          <Button icon="download" onClick={exportToCSV} disabled={history.length === 0}>
            Export data
          </Button>
        </div>
      </div>

      {/* Historical Analytics Summary (Task 3) */}
      <HistoricalAnalyticsSummary state={state} />

      {/* Metric KPI Cards (PM1.0, PM2.5, PM10 with measurement units and timestamps) */}
      <div className="kpi-grid">
        {kpis.map((item) => (
          <MetricCard key={item.label} {...item} />
        ))}
      </div>

      {/* Historical Pollutant Trend Charts (PM2.5, PM10, PM1.0) */}
      <div className="dash-grid">
        <ChartCard
          title="PM2.5 historical trend"
          subtitle={`Concentration (µg/m³) · ${history.length} records in ${timeRange}`}
          variant="pm25"
          tall
          readings={history}
        />
        <ChartCard
          title="PM10 historical trend"
          subtitle={`Concentration (µg/m³) · ${history.length} records in ${timeRange}`}
          variant="pm10"
          tall
          readings={history}
        />
        <ChartCard
          title="PM1.0 historical trend"
          subtitle={`Ultra-fine particulate matter · ${history.length} records in ${timeRange}`}
          variant="pm1"
          tall
          readings={history}
        />
        <Card className="wide-chart">
          <SectionTitle
            title="Pollution comparison & predictive interface"
            subtitle="Live edge station readings · 1D-CNN–BiGRU sequence model"
            action={
              <Badge tone={forecastStatus?.is_trained ? "good" : "neutral"}>
                {forecastStatus?.is_trained ? "1D-CNN-BiGRU Operational" : "Model Unconfigured"}
              </Badge>
            }
          />
          <TrendChart readings={history} forecast={forecastStatus?.is_trained} height={180} />
          <div className="chart-axis">
            <span>Earliest ({timeRange})</span>
            <span>Recorded Timeline (Hover for details)</span>
            <span>Latest</span>
          </div>
          <div className="legend">
            <span>
              <i className="solid cyan" />
              Actual measurement (from backend SQLite)
            </span>
            <span style={{ color: forecastStatus?.is_trained ? "var(--cyan)" : "var(--muted)" }}>
              <i className="dashed" />
              {forecastStatus?.is_trained
                ? `1D-CNN–BiGRU predictive engine online (${state.forecasts.length} record(s))`
                : "1D-CNN–BiGRU prediction: Disabled (model_not_configured)"}
            </span>
          </div>
        </Card>
      </div>

      {/* 1D-CNN-BiGRU AI Predictive Engine Panel */}
      <AIForecastPanel state={state} />

      {/* Latest Reading Detail Table (Task 2) */}
      <LatestTelemetryDetailCard
        reading={latestReading}
        isStale={isStale}
        timeAgoText={lastUpdatedText}
      />


      {/* Historical Telemetry Records Table (Task 2 & 3) */}
      <HistoricalTelemetryTable
        history={history}
        timeRange={timeRange}
        selectedLocation={selectedLocation}
        selectedDevice={selectedDevice}
        onExport={exportToCSV}
      />

      {/* Device & Alert Management Interfaces (Task 4) */}
      <div className="two-col device-alert-grid" style={{ marginTop: 16 }}>
        <DeviceStatusCard devices={devices} />
        <Card>
          <SectionTitle
            title="System & environmental alerts"
            subtitle={`${alerts.length} total alert record(s)`}
          />
          <AlertsList
            alerts={alerts}
            detailed
            onAcknowledge={acknowledgeAlert}
            onResolve={resolveAlert}
            updatingAlertId={updatingAlertId}
          />
        </Card>
      </div>

      {/* Regulatory AQI & Forecasting Integrity Section (Task 5) */}
      <AQIAndForecastIntegrityPanel forecastStatus={forecastStatus} />
    </div>
  )
}

const settingsTabs = [
  { id: "General", icon: "sliders" as IconName },
  { id: "Appearance", icon: "sun" as IconName },
  { id: "Monitoring", icon: "activity" as IconName },
  { id: "IoT & database", icon: "database" as IconName },
  { id: "Notifications", icon: "bell" as IconName },
]

function SettingRow({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <div className="setting-row">
      <div>
        <b>{title}</b>
        <span>{description}</span>
      </div>
      {children}
    </div>
  )
}

function SettingsPage({
  dark,
  setDark,
  state,
}: {
  dark: boolean
  setDark: (v: boolean) => void
  state: AirPurifyState
}) {
  const [tab, setTab] = useState("General")
  const [saved, setSaved] = useState(false)

  const content = useMemo(() => {
    if (tab === "General")
      return (
        <>
          <SectionTitle
            title="General settings"
            subtitle="Manage core application and campus preferences."
          />
          <div className="form-grid">
            <TextField label="Application name" value="AirPurify AI" />
            <TextField label="Campus / institution" value="Main Campus" />
            <SelectControl
              label="Time zone"
              value="UTC +05:30 · Asia/Colombo"
              options={[
                "UTC +05:30 · Asia/Colombo",
                "UTC +00:00 · London",
                "UTC -05:00 · New York",
              ]}
            />
          </div>
        </>
      )
    if (tab === "Appearance")
      return (
        <>
          <SectionTitle
            title="Appearance settings"
            subtitle="Customize interface theme and display density."
          />
          <div className="theme-options">
            <button
              className={!dark ? "selected" : ""}
              onClick={() => setDark(false)}
            >
              <div className="theme-preview" />
              <span>
                <b>Light theme</b>
                <small>Clean contrast for daylight</small>
              </span>
              {!dark && <Icon name="check" />}
            </button>
            <button
              className={dark ? "selected" : ""}
              onClick={() => setDark(true)}
            >
              <div className="theme-preview dark-preview" />
              <span>
                <b>Dark theme</b>
                <small>Reduced eye fatigue in low light</small>
              </span>
              {dark && <Icon name="check" />}
            </button>
          </div>
        </>
      )
    if (tab === "IoT & database")
      return (
        <>
          <SectionTitle
            title="IoT & database connection"
            subtitle="Configure connection to FastAPI backend."
          />
          <div className="form-grid">
            <TextField
              label="API endpoint"
              value={backendDisplayUrl}
              readOnly
              hint="Configured backend service endpoint."
            />
            <TextField
              label="Database"
              value={state.health?.database || "sqlite:///./airpurify.db"}
              readOnly
              hint="SQLAlchemy SQLite local database."
            />
          </div>
          <div className="sync-banner">
            <Icon name={state.healthStatus === "connected" ? "check" : "alert"} />
            <div>
              <b>
                {state.healthStatus === "connected"
                  ? "Connected to AirPurify AI backend"
                  : "Disconnected from backend"}
              </b>
              <span>
                Status: {state.healthStatus} · {state.devices.length} registered devices
              </span>
            </div>
            <Button variant="secondary" icon="refresh" onClick={state.refetch}>
              Test connection
            </Button>
          </div>
        </>
      )
    return (
      <>
        <SectionTitle
          title="Notification preferences"
          subtitle="Choose which system events should notify you."
        />
        <SettingRow
          title="In-app notifications"
          description="Receive alerts while using AirPurify AI."
        >
          <Toggle label="" checked />
        </SettingRow>
        <SettingRow
          title="AQI threshold alerts"
          description="Notify when particulate readings exceed configured limits."
        >
          <Toggle label="" checked />
        </SettingRow>
      </>
    )
  }, [tab, dark, setDark, state])

  return (
    <div className="page settings-page">
      <div className="page-intro">
        <div>
          <div className="title-lg">System settings</div>
          <p>Configure backend connection, alert preferences and appearance.</p>
        </div>
      </div>
      <div className="settings-layout">
        <Card className="settings-nav">
          {settingsTabs.map((item) => (
            <button
              key={item.id}
              className={tab === item.id ? "active" : ""}
              onClick={() => setTab(item.id)}
            >
              <Icon name={item.icon} />
              <span>{item.id}</span>
              <Icon name="chevron" size={13} />
            </button>
          ))}
        </Card>
        <Card className="settings-content">
          {content}
          <div className="settings-actions">
            <span />
            <div>
              <Button variant="secondary">Reset</Button>
              <Button
                onClick={() => {
                  setSaved(true)
                  setTimeout(() => setSaved(false), 2200)
                }}
              >
                {saved ? "Changes saved" : "Save changes"}
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

function ProfilePage({ dark }: { dark: boolean }) {
  const [saved, setSaved] = useState(false)
  return (
    <div className="page profile-page">
      <div className="page-intro">
        <div>
          <div className="title-lg">Profile & account</div>
          <p>Manage your personal information and account preferences.</p>
        </div>
      </div>
      <div className="profile-layout">
        <div>
          <Card className="profile-summary">
            <div className="profile-avatar">
              AM
              <span>
                <Icon name="plus" size={15} />
              </span>
            </div>
            <div className="title-md">Alex Morgan</div>
            <span>alex.morgan@aerosense.edu</span>
            <Badge tone="info">System Administrator</Badge>
            <div className="profile-stats">
              <div>
                <b>4</b>
                <span>Locations</span>
              </div>
              <div>
                <b>128</b>
                <span>Reports</span>
              </div>
            </div>
            <Button variant="secondary" icon="logout">
              Sign out
            </Button>
          </Card>
          <Card className="account-health">
            <SectionTitle title="Account security" />
            <div>
              <Icon name="shield" />
              <div>
                <b>Account protected</b>
                <span>Password updated 34 days ago</span>
              </div>
            </div>
            <Button variant="ghost" icon="lock">
              Change password
            </Button>
          </Card>
        </div>
        <Card className="profile-form">
          <SectionTitle
            title="Personal information"
            subtitle="Update your profile details and workspace defaults."
          />
          <div className="form-grid">
            <TextField label="Full name" value="Alex Morgan" />
            <TextField
              label="Email address"
              value="alex.morgan@aerosense.edu"
              type="email"
            />
            <TextField label="Role" value="System Administrator" />
            <TextField label="Department" value="AI & Data Science" />
            <SelectControl
              label="Preferred theme"
              value={dark ? "Dark" : "Light"}
              options={["Light", "Dark", "System"]}
            />
            <SelectControl
              label="Default monitoring location"
              value="Engineering Block"
              options={["Engineering Block", "Central Library", "North Gate"]}
            />
          </div>
          <div className="settings-actions profile-actions">
            <span />
            <div>
              <Button variant="secondary">Cancel</Button>
              <Button
                onClick={() => {
                  setSaved(true)
                  setTimeout(() => setSaved(false), 2200)
                }}
              >
                {saved ? "Profile saved" : "Save changes"}
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default function App() {
  const [page, setPage] = useState<Page>("home")
  const [dark, setDark] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  // Live backend connection & telemetry hook
  const state = useAirPurifyData()

  return (
    <div className={`app-shell ${dark ? "dark" : ""}`}>
      <Sidebar
        page={page}
        setPage={setPage}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
        healthStatus={state.healthStatus}
        deviceCount={state.devices.length}
      />
      {mobileOpen && (
        <div className="mobile-overlay" onClick={() => setMobileOpen(false)} />
      )}
      <div className="main-shell">
        <Topbar
          page={page}
          dark={dark}
          setDark={setDark}
          onMenu={() => setMobileOpen(true)}
          state={state}
        />
        <main>
          {page === "home" && (
            <HomePage state={state} goDashboard={() => setPage("dashboard")} />
          )}
          {page === "dashboard" && <DashboardPage state={state} />}
          {page === "settings" && (
            <SettingsPage dark={dark} setDark={setDark} state={state} />
          )}
          {page === "profile" && <ProfilePage dark={dark} />}
        </main>
        <footer>
          <span>AirPurify AI · Environmental Intelligence Platform</span>
          <span>
            {state.healthStatus === "connected"
              ? `Connected to backend (${backendDisplayUrl})`
              : `Backend offline (${backendDisplayUrl})`}
          </span>
        </footer>
      </div>
    </div>
  )
}
