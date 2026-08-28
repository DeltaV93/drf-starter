import { useState, useCallback } from 'react'
import { apiCall } from '../lib/api'
import type { TripHome } from './useTrips'

export interface OptimizationResult {
  schedule: TripHome[]
  start_coords: [number, number]
  end_coords: [number, number]
  total_distance: number
  skipped_homes: string[]
}

interface GeocodeResult {
  lat: number
  lng: number
}

export function useRouteOptimization() {
  const [result, setResult] = useState<OptimizationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const geocodeAddress = useCallback(async (address: string): Promise<GeocodeResult> => {
    try {
      const response = await apiCall('/geocode/', {
        method: 'POST',
        body: JSON.stringify({ address }),
      })
      return response.data
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to geocode address'
      throw new Error(message, { cause: err })
    }
  }, [])

  const optimizeRoute = useCallback(
    async (homes: Omit<TripHome, 'id' | 'created_at' | 'visit_order'>[]) => {
      setLoading(true)
      setError(null)
      try {
        const response = await apiCall('/optimize-route/', {
          method: 'POST',
          body: JSON.stringify({ homes }),
        })
        setResult(response.data)
        return response.data
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to optimize route'
        setError(message)
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  return {
    result,
    loading,
    error,
    geocodeAddress,
    optimizeRoute,
  }
}
