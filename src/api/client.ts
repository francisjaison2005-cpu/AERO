/**
 * AirPurify AI - TypeScript API Client
 * Connects the React frontend to the FastAPI backend service
 */

export interface HealthResponse {
  status: string
  app_name: string
  version: string
  database: string
  timestamp: string
}

export interface SensorReading {
  id: number
  device_id: string
  location_id: string
  timestamp: string
  received_at: string
  pm1_0: number | null
  pm2_5: number
  pm10: number
  data_quality_status: string
}

export interface Device {
  id: number
  device_id: string
  device_name: string
  location_id: string
  last_seen: string | null
  status: string
  firmware_version: string | null
}

export interface Forecast {
  id: number
  location_id: string
  model_name: string
  model_version: string
  issued_at: string
  target_time: string
  horizon_hours: number
  predicted_aqi: number | null
  predicted_pm25?: number | null
  predicted_pm10?: number | null
  confidence_interval_lower?: number | null
  confidence_interval_upper?: number | null
  status: string
}

export interface ForecastMetrics {
  mae: number
  rmse: number
  r2: number
  samples: number
}

export interface ForecastStatus {
  model_name: string
  model_version: string
  status: string
  architecture: string
  is_trained: boolean
  message: string
  metrics?: ForecastMetrics | null
  provenance?: {
    source_name?: string
    citation?: string
    time_range?: string
    target_pollutant?: string
    sensor_type_disclaimer?: string
  } | null
  training_info?: {
    train_samples?: number
    test_samples?: number
    sequence_length?: number
    baselines?: {
      persistence?: { mae: number; rmse: number; r2: number }
      historical_mean?: { mae: number; rmse: number; r2: number }
    }
  } | null
}

export interface AlertItem {
  id: number
  location_id: string
  device_id: string
  alert_type: string
  severity: "info" | "warning" | "critical" | string
  message: string
  triggered_at: string
  status: "active" | "acknowledged" | "resolved" | string
}

export const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || (import.meta.env.DEV ? "http://127.0.0.1:8001" : "")
export const API_KEY =
  (import.meta as any).env?.VITE_API_KEY || (import.meta.env.DEV ? "airpurify-dev-key-2026" : "")
export const ADMIN_KEY =
  (import.meta as any).env?.VITE_ADMIN_KEY || (import.meta.env.DEV ? "airpurify-admin-dev-key-2026" : "")

async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string> || {}),
  }

  // In development, provide dev keys if set. In production, only include if explicitly injected
  if (API_KEY && !headers["X-API-Key"]) {
    headers["X-API-Key"] = API_KEY
  }
  if (ADMIN_KEY && !headers["X-Admin-Key"]) {
    headers["X-Admin-Key"] = ADMIN_KEY
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })


  if (!response.ok) {
    if (response.status === 404) {
      const err = new Error(`Resource not found at ${endpoint}`)
      ;(err as any).status = 404
      throw err
    }
    const errBody = await response.text()
    throw new Error(`API Error ${response.status}: ${errBody || response.statusText}`)
  }

  return response.json()
}

export const apiClient = {
  /**
   * Health check and database connectivity verification
   */
  async getHealth(): Promise<HealthResponse> {
    return apiFetch<HealthResponse>("/api/health")
  },

  /**
   * Fetch the latest sensor reading (filtered by device or location)
   */
  async getLatestReading(params?: {
    device_id?: string
    location_id?: string
  }): Promise<SensorReading | null> {
    const query = new URLSearchParams()
    if (params?.device_id && params.device_id !== "All devices" && params.device_id !== "All locations") {
      query.set("device_id", params.device_id)
    }
    if (params?.location_id && params.location_id !== "All locations") {
      query.set("location_id", params.location_id)
    }
    const qStr = query.toString() ? `?${query.toString()}` : ""
    try {
      return await apiFetch<SensorReading>(`/api/readings/latest${qStr}`)
    } catch (err: any) {
      if (err.status === 404) {
        return null
      }
      throw err
    }
  },

  /**
   * Fetch historical sensor telemetry
   */
  async getReadingHistory(params?: {
    device_id?: string
    location_id?: string
    limit?: number
    start_time?: string
    end_time?: string
  }): Promise<SensorReading[]> {
    const query = new URLSearchParams()
    if (params?.device_id && params.device_id !== "All devices" && params.device_id !== "All locations") {
      query.set("device_id", params.device_id)
    }
    if (params?.location_id && params.location_id !== "All locations") {
      query.set("location_id", params.location_id)
    }
    if (params?.limit) {
      query.set("limit", String(params.limit))
    }
    if (params?.start_time) {
      query.set("start_time", params.start_time)
    }
    if (params?.end_time) {
      query.set("end_time", params.end_time)
    }
    const qStr = query.toString() ? `?${query.toString()}` : ""
    try {
      return await apiFetch<SensorReading[]>(`/api/readings/history${qStr}`)
    } catch (err: any) {
      if (err.status === 404) {
        return []
      }
      throw err
    }
  },

  /**
   * List all registered devices
   */
  async getDevices(): Promise<Device[]> {
    try {
      return await apiFetch<Device[]>("/api/devices")
    } catch (err) {
      return []
    }
  },

  /**
   * Retrieve single device
   */
  async getDevice(deviceId: string): Promise<Device | null> {
    try {
      return await apiFetch<Device>(`/api/devices/${encodeURIComponent(deviceId)}`)
    } catch (err: any) {
      if (err.status === 404) return null
      throw err
    }
  },

  /**
   * Retrieve forecast records
   */
  async getForecasts(locationId?: string): Promise<Forecast[]> {
    const qStr = locationId && locationId !== "All locations" ? `?location_id=${encodeURIComponent(locationId)}` : ""
    try {
      return await apiFetch<Forecast[]>(`/api/forecasts${qStr}`)
    } catch {
      return []
    }
  },

  /**
   * Check status of the 1D-CNN–BiGRU deep learning model
   */
  async getForecastStatus(): Promise<ForecastStatus | null> {
    try {
      return await apiFetch<ForecastStatus>("/api/forecasts/status")
    } catch {
      return null
    }
  },

  /**
   * Retrieve alerts from backend
   */
  async getAlerts(params?: {
    device_id?: string
    location_id?: string
    status?: string
    severity?: string
    limit?: number
  }): Promise<AlertItem[]> {
    const query = new URLSearchParams()
    if (params?.device_id && params.device_id !== "All devices" && params.device_id !== "All locations") query.set("device_id", params.device_id)
    if (params?.location_id && params.location_id !== "All locations") query.set("location_id", params.location_id)
    if (params?.status) query.set("status", params.status)
    if (params?.severity) query.set("severity", params.severity)
    if (params?.limit) query.set("limit", String(params.limit))
    const qStr = query.toString() ? `?${query.toString()}` : ""
    try {
      return await apiFetch<AlertItem[]>(`/api/alerts${qStr}`)
    } catch {
      return []
    }
  },

  /**
   * Update alert status (acknowledge or resolve)
   */
  async updateAlertStatus(
    alertId: number,
    status: "acknowledged" | "resolved" | "active"
  ): Promise<AlertItem> {
    return await apiFetch<AlertItem>(`/api/alerts/${alertId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    })
  },

  /**
   * Trigger 1D-CNN-BiGRU AI inference for a location
   */
  async predictForecast(params: {
    location_id: string
    horizon_hours?: number
    recent_pm25_sequence?: number[]
    save_to_db?: boolean
  }): Promise<any> {
    const saveQuery = params.save_to_db !== false ? "?save_to_db=true" : "?save_to_db=false"
    return await apiFetch<any>(`/api/forecasts/predict${saveQuery}`, {
      method: "POST",
      body: JSON.stringify({
        location_id: params.location_id,
        horizon_hours: params.horizon_hours || 1,
        recent_pm25_sequence: params.recent_pm25_sequence,
      }),
    })
  },
}

