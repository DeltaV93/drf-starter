import { useState, useCallback } from 'react'
import { apiCall } from '../lib/api'

export interface TripHome {
  id: number
  address: string
  start_time: string
  end_time: string
  lat: number
  lng: number
  visit_order: number
  zpid?: string
  price?: number
  bedrooms?: number
  bathrooms?: number
  sqft?: number
  photos?: string[]
}

export interface Trip {
  id: number
  name: string
  start_address: string
  end_address: string
  homes: TripHome[]
  created_at: string
  updated_at: string
}

interface CreateTripPayload {
  name: string
  start_address: string
  end_address: string
  homes: Omit<TripHome, 'id' | 'created_at' | 'visit_order'>[]
}

export function useTrips() {
  const [trips, setTrips] = useState<Trip[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadTrips = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiCall('/trips/', { method: 'GET' })
      setTrips(response.data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trips')
    } finally {
      setLoading(false)
    }
  }, [])

  const createTrip = useCallback(async (payload: CreateTripPayload) => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiCall('/trips/', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      const newTrip = response.data
      setTrips((prev) => [...prev, newTrip])
      return newTrip
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create trip'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const updateTrip = useCallback(async (id: number, payload: Partial<CreateTripPayload>) => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiCall(`/trips/${id}/`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      })
      const updated = response.data
      setTrips((prev) => prev.map((t) => (t.id === id ? updated : t)))
      return updated
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update trip'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const deleteTrip = useCallback(async (id: number) => {
    setLoading(true)
    setError(null)
    try {
      await apiCall(`/trips/${id}/`, { method: 'DELETE' })
      setTrips((prev) => prev.filter((t) => t.id !== id))
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete trip'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    trips,
    loading,
    error,
    loadTrips,
    createTrip,
    updateTrip,
    deleteTrip,
  }
}
