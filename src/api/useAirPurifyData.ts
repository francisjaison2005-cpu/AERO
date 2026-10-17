/**
 * React hook to manage live AirPurify AI backend telemetry and connection state.
 *
 * Implements:
 * - Dynamic time filters (1h, 6h, 24h, 7d) mapped to ISO start_time queries
 * - Location and Device query filtering
 * - Statistical summaries (Peak PM2.5/PM10, timestamps, averages, trend comparisons)
 * - Sparse/Missing data indicators
 * - Alert acknowledgement and resolution with optimistic update and pending states
 * - Actual filtered telemetry CSV export
 */

import { useState, useEffect, useCallback, useMemo } from "react"
import {
  apiClient,
  API_BASE_URL,
  type HealthResponse,
  type SensorReading,
  type Device,
  type ForecastStatus,
  type Forecast,
  type AlertItem,
} from "./client"

export interface PeakMetric {
  value: number
  timestamp: string
}

export interface PeriodTrend {
  pm25DeltaPercent: number
  direction: "up" | "down" | "flat"
}

export interface AirPurifyState {
  health: HealthResponse | null
  healthStatus: "checking" | "connected" | "disconnected" | "degraded"
  latestReading: SensorReading | null
  history: SensorReading[]
  devices: Device[]
  forecastStatus: ForecastStatus | null
  forecasts: Forecast[]
  alerts: AlertItem[]
  isLoading: boolean
  isRefreshing: boolean
  lastUpdatedText: string
  isStale: boolean
  error: string | null
  selectedLocation: string
  setSelectedLocation: (loc: string) => void
  availableLocations: string[]
  selectedDevice: string
  setSelectedDevice: (dev: string) => void
  availableDevices: string[]
  timeRange: string
  setTimeRange: (range: string) => void
  refetch: () => Promise<void>
  acknowledgeAlert: (alertId: number) => Promise<void>
  resolveAlert: (alertId: number) => Promise<void>
  updatingAlertId: number | null
  alertActionError: string | null
  exportToCSV: () => void
  triggerPrediction: (horizonHours?: number) => Promise<any>
  isPredicting: boolean
  predictionError: string | null
  // Historical analytics summaries (Task 3)
  readingCount: number
  peakPM25: PeakMetric | null
  peakPM10: PeakMetric | null
  peakPM1: PeakMetric | null
  avgPM25: number | null
  avgPM10: number | null
  avgPM1: number | null
  periodTrend: PeriodTrend | null
  missingDataNotice: string | null
  isInsufficientData: boolean
}


function calculateTimeAgo(dateStr?: string | null): { text: string; isStale: boolean } {
  if (!dateStr) return { text: "No telemetry recorded", isStale: false }
  try {
    const time = new Date(dateStr).getTime()
    if (isNaN(time)) return { text: "Unknown", isStale: false }
    const now = Date.now()
    const diffSec = Math.max(0, Math.floor((now - time) / 1000))

    const isStale = diffSec > 15 * 60 // Older than 15 minutes is stale per system rule

    if (diffSec < 45) return { text: "Just now", isStale }
    if (diffSec < 90) return { text: "1 min ago", isStale }
    if (diffSec < 3600) return { text: `${Math.floor(diffSec / 60)} min ago`, isStale }
    if (diffSec < 86400) return { text: `${Math.floor(diffSec / 3600)}h ago`, isStale }
    return { text: new Date(dateStr).toLocaleDateString(), isStale }
  } catch {
    return { text: "Invalid date", isStale: false }
  }
}

export function useAirPurifyData(pollIntervalMs = 15000): AirPurifyState {
  const [selectedLocation, setSelectedLocation] = useState<string>("All locations")
  const [selectedDevice, setSelectedDevice] = useState<string>("All devices")
  const [timeRange, setTimeRange] = useState<string>("24 hours")
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthStatus, setHealthStatus] = useState<AirPurifyState["healthStatus"]>("checking")
  const [latestReading, setLatestReading] = useState<SensorReading | null>(null)
  const [history, setHistory] = useState<SensorReading[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [forecastStatus, setForecastStatus] = useState<ForecastStatus | null>(null)
  const [forecasts, setForecasts] = useState<Forecast[]>([])
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false)
  const [updatingAlertId, setUpdatingAlertId] = useState<number | null>(null)
  const [alertActionError, setAlertActionError] = useState<string | null>(null)
  const [isPredicting, setIsPredicting] = useState<boolean>(false)
  const [predictionError, setPredictionError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Calculate actual ISO start_time according to selected time filter
  const startTimeIso = useMemo(() => {
    const now = Date.now()
    let hoursAgo = 24
    if (timeRange === "1 hour") hoursAgo = 1
    else if (timeRange === "6 hours") hoursAgo = 6
    else if (timeRange === "24 hours") hoursAgo = 24
    else if (timeRange === "7 days") hoursAgo = 24 * 7
    return new Date(now - hoursAgo * 3600 * 1000).toISOString()
  }, [timeRange])

  const rangeLimit = useMemo(() => {
    switch (timeRange) {
      case "1 hour":
        return 60
      case "6 hours":
        return 180
      case "24 hours":
        return 500
      case "7 days":
        return 1000
      default:
        return 500
    }
  }, [timeRange])

  const fetchData = useCallback(
    async (isInitial = false) => {
      if (isInitial) {
        setIsLoading(true)
      } else {
        setIsRefreshing(true)
      }
      setError(null)

      try {
        // 1. Health check
        let currentHealth: HealthResponse | null = null
        try {
          currentHealth = await apiClient.getHealth()
          setHealth(currentHealth)
          setHealthStatus(currentHealth.database === "connected" ? "connected" : "degraded")
        } catch {
          setHealth(null)
          setHealthStatus("disconnected")
          const target = API_BASE_URL || (typeof window !== "undefined" ? window.location.origin : "API")
          setError(`AirPurify AI backend service is currently unreachable (${target}). Check network connectivity or service status.`)
          setIsLoading(false)
          setIsRefreshing(false)
          return
        }

        // 2. Fetch telemetry, history, devices, alerts in parallel
        const locFilter = selectedLocation === "All locations" ? undefined : selectedLocation
        const devFilter = selectedDevice === "All devices" ? undefined : selectedDevice

        const [readingRes, historyRes, devicesRes, fStatusRes, fRes, alertsRes] =
          await Promise.allSettled([
            apiClient.getLatestReading({ location_id: locFilter, device_id: devFilter }),
            apiClient.getReadingHistory({
              location_id: locFilter,
              device_id: devFilter,
              start_time: startTimeIso,
              limit: rangeLimit,
            }),
            apiClient.getDevices(),
            apiClient.getForecastStatus(),
            apiClient.getForecasts(locFilter),
            apiClient.getAlerts({ location_id: locFilter, device_id: devFilter, limit: 30 }),
          ])

        if (readingRes.status === "fulfilled") {
          setLatestReading(readingRes.value)
        } else {
          setLatestReading(null)
        }

        if (historyRes.status === "fulfilled") {
          setHistory(historyRes.value)
        } else {
          setHistory([])
        }

        if (devicesRes.status === "fulfilled") {
          setDevices(devicesRes.value)
        }

        if (fStatusRes.status === "fulfilled") {
          setForecastStatus(fStatusRes.value)
        }

        if (fRes.status === "fulfilled") {
          setForecasts(fRes.value)
        }

        if (alertsRes.status === "fulfilled") {
          // De-duplicate alerts by unique ID
          const seenIds = new Set<number>()
          const uniqueAlerts: AlertItem[] = []
          for (const item of alertsRes.value) {
            if (!seenIds.has(item.id)) {
              seenIds.add(item.id)
              uniqueAlerts.push(item)
            }
          }
          setAlerts(uniqueAlerts)
        }
      } catch (err: any) {
        setError(err?.message || "Failed to communicate with AirPurify AI backend.")
      } finally {
        setIsLoading(false)
        setIsRefreshing(false)
      }
    },
    [selectedLocation, selectedDevice, startTimeIso, rangeLimit]
  )

  useEffect(() => {
    fetchData(true)
    const interval = setInterval(() => {
      fetchData(false)
    }, pollIntervalMs)
    return () => clearInterval(interval)
  }, [fetchData, pollIntervalMs])

  const { text: lastUpdatedText, isStale } = calculateTimeAgo(
    latestReading?.timestamp || latestReading?.received_at
  )

  // Dynamically compute all distinct locations from registered devices and canonical zones
  const availableLocations = useMemo(() => {
    const locSet = new Set<string>(["All locations"])
    devices.forEach((d) => {
      if (d.location_id) locSet.add(d.location_id)
    })
    locSet.add("Engineering Block")
    locSet.add("Central Library")
    locSet.add("North Gate")
    return Array.from(locSet)
  }, [devices])

  // Dynamically compute registered devices
  const availableDevices = useMemo(() => {
    const devSet = new Set<string>(["All devices"])
    devices.forEach((d) => {
      if (d.device_id) devSet.add(d.device_id)
    })
    return Array.from(devSet)
  }, [devices])

  // Acknowledge alert via backend PATCH /api/alerts/{id}
  const acknowledgeAlert = useCallback(
    async (alertId: number) => {
      setUpdatingAlertId(alertId)
      setAlertActionError(null)
      try {
        await apiClient.updateAlertStatus(alertId, "acknowledged")
        setAlerts((prev) =>
          prev.map((a) => (a.id === alertId ? { ...a, status: "acknowledged" } : a))
        )
      } catch (err: any) {
        console.error("Failed to acknowledge alert:", err)
        setAlertActionError(`Failed to acknowledge alert #${alertId}: ${err?.message || "Server error"}`)
      } finally {
        setUpdatingAlertId(null)
      }
    },
    []
  )

  // Resolve alert via backend PATCH /api/alerts/{id}
  const resolveAlert = useCallback(
    async (alertId: number) => {
      setUpdatingAlertId(alertId)
      setAlertActionError(null)
      try {
        await apiClient.updateAlertStatus(alertId, "resolved")
        setAlerts((prev) =>
          prev.map((a) => (a.id === alertId ? { ...a, status: "resolved" } : a))
        )
      } catch (err: any) {
        console.error("Failed to resolve alert:", err)
        setAlertActionError(`Failed to resolve alert #${alertId}: ${err?.message || "Server error"}`)
      } finally {
        setUpdatingAlertId(null)
      }
    },
    []
  )

  // Task 3: Historical analytics summaries calculated from actual stored records
  const historicalAnalytics = useMemo(() => {
    const count = history.length
    if (count === 0) {
      return {
        readingCount: 0,
        peakPM25: null,
        peakPM10: null,
        peakPM1: null,
        avgPM25: null,
        avgPM10: null,
        avgPM1: null,
        periodTrend: null,
        missingDataNotice: `No sensor telemetry found in the selected ${timeRange} window. Try expanding the time filter to 6 hours or 24 hours.`,
        isInsufficientData: true,
      }
    }

    let max25 = -Infinity
    let time25 = ""
    let max10 = -Infinity
    let time10 = ""
    let max1 = -Infinity
    let time1 = ""
    let sum25 = 0
    let sum10 = 0
    let sum1 = 0
    let count1 = 0

    for (const r of history) {
      if (r.pm2_5 > max25) {
        max25 = r.pm2_5
        time25 = r.timestamp || r.received_at
      }
      sum25 += r.pm2_5

      if (r.pm10 > max10) {
        max10 = r.pm10
        time10 = r.timestamp || r.received_at
      }
      sum10 += r.pm10

      if (r.pm1_0 !== null && r.pm1_0 !== undefined) {
        if (r.pm1_0 > max1) {
          max1 = r.pm1_0
          time1 = r.timestamp || r.received_at
        }
        sum1 += r.pm1_0
        count1++
      }
    }

    // Trend comparison: compare recent half vs older half
    let periodTrend: PeriodTrend | null = null
    if (count >= 2) {
      const half = Math.floor(count / 2)
      const recentSlice = history.slice(0, half)
      const olderSlice = history.slice(half)
      const recentAvg = recentSlice.reduce((acc, r) => acc + r.pm2_5, 0) / recentSlice.length
      const olderAvg = olderSlice.reduce((acc, r) => acc + r.pm2_5, 0) / olderSlice.length
      if (olderAvg > 0) {
        const delta = ((recentAvg - olderAvg) / olderAvg) * 100
        periodTrend = {
          pm25DeltaPercent: Math.round(delta * 10) / 10,
          direction: delta > 1.0 ? "up" : delta < -1.0 ? "down" : "flat",
        }
      }
    }

    // Determine missing data or sparsity indication
    let notice: string | null = null
    let insufficient = false
    if (count < 3) {
      notice = `Sparse telemetry: Only ${count} record(s) recorded in this ${timeRange} window. Insufficient data for full regulatory compliance or robust trend modeling.`
      insufficient = true
    } else if (timeRange === "24 hours" && count < 16) {
      notice = `Notice: ${count} readings available in the last 24h. CPCB/EPA official averaging requires continuous sampling (minimum 16-24 valid hourly records).`
    }

    return {
      readingCount: count,
      peakPM25: max25 >= 0 ? { value: max25, timestamp: time25 } : null,
      peakPM10: max10 >= 0 ? { value: max10, timestamp: time10 } : null,
      peakPM1: max1 >= 0 ? { value: max1, timestamp: time1 } : null,
      avgPM25: Math.round((sum25 / count) * 10) / 10,
      avgPM10: Math.round((sum10 / count) * 10) / 10,
      avgPM1: count1 > 0 ? Math.round((sum1 / count1) * 10) / 10 : null,
      periodTrend,
      missingDataNotice: notice,
      isInsufficientData: insufficient,
    }
  }, [history, timeRange])

  // Export actual filtered telemetry records as CSV
  const exportToCSV = useCallback(() => {
    if (history.length === 0) {
      alert(`No historical records found for the selected ${timeRange} window (${selectedLocation}, ${selectedDevice}) to export.`)
      return
    }

    const headers = [
      "Record ID",
      "Device ID",
      "Location ID",
      "Recorded Timestamp (ISO)",
      "Received At (UTC)",
      "PM1.0 (ug/m3)",
      "PM2.5 (ug/m3)",
      "PM10 (ug/m3)",
      "Quality Status",
    ]

    const rows = history.map((r) => [
      r.id,
      `"${r.device_id}"`,
      `"${r.location_id}"`,
      `"${r.timestamp}"`,
      `"${r.received_at}"`,
      r.pm1_0 !== null && r.pm1_0 !== undefined ? r.pm1_0 : "",
      r.pm2_5,
      r.pm10,
      `"${r.data_quality_status}"`,
    ])

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n")

    const encodedUri = encodeURI(csvContent)
    const link = document.createElement("a")
    link.setAttribute("href", encodedUri)
    const cleanLoc = selectedLocation.replace(/\s+/g, "_")
    const cleanDev = selectedDevice.replace(/\s+/g, "_")
    const cleanRange = timeRange.replace(/\s+/g, "_")
    link.setAttribute(
      "download",
      `airpurify_telemetry_${cleanLoc}_${cleanDev}_${cleanRange}_${new Date().toISOString().slice(0, 10)}.csv`
    )
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }, [history, selectedLocation, selectedDevice, timeRange])

  // Trigger on-demand deep learning inference using 1D-CNN-BiGRU model
  const triggerPrediction = useCallback(
    async (horizonHours: number = 1) => {
      setIsPredicting(true)
      setPredictionError(null)
      try {
        const targetLoc = selectedLocation !== "All locations" ? selectedLocation : "Engineering Block"
        const recentPm = history.map((r) => r.pm2_5)
        await apiClient.predictForecast({
          location_id: targetLoc,
          horizon_hours: horizonHours,
          recent_pm25_sequence: recentPm.length > 0 ? recentPm : undefined,
          save_to_db: true,
        })
        const updatedForecasts = await apiClient.getForecasts(
          selectedLocation !== "All locations" ? selectedLocation : undefined
        )
        setForecasts(updatedForecasts)
      } catch (err: any) {
        setPredictionError(err?.message || "Failed to execute 1D-CNN-BiGRU model inference")
      } finally {
        setIsPredicting(false)
      }
    },
    [selectedLocation, history]
  )

  return {
    health,
    healthStatus,
    latestReading,
    history,
    devices,
    forecastStatus,
    forecasts,
    alerts,
    isLoading,
    isRefreshing,
    lastUpdatedText,
    isStale,
    error,
    selectedLocation,
    setSelectedLocation,
    availableLocations,
    selectedDevice,
    setSelectedDevice,
    availableDevices,
    timeRange,
    setTimeRange,
    refetch: () => fetchData(false),
    acknowledgeAlert,
    resolveAlert,
    updatingAlertId,
    alertActionError,
    exportToCSV,
    triggerPrediction,
    isPredicting,
    predictionError,
    ...historicalAnalytics,
  }
}

