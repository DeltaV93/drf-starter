import { useState, useCallback } from 'react'
import { apiData } from '../lib/api'
import { routes } from '../lib/routes'
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
      const result = await apiData<GeocodeResult>({
        url: routes.api.geocode(),
        method: 'POST',
        data: { address },
      })
      if (!result) throw new Error('No geocoding result returned')
      return result
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to geocode address'
      throw new Error(message)
    }
  }, [])

  const optimizeRoute = useCallback(
    async (homes: Omit<TripHome, 'id' | 'created_at' | 'visit_order'>[]) => {
      setLoading(true)
      setError(null)
      try {
        const data = await apiData<OptimizationResult>({
          url: routes.api.optimizeRoute(),
          method: 'POST',
          data: { homes },
        })
        if (data) setResult(data)
        return data
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
