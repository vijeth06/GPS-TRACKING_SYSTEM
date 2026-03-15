import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Play, Pause, SkipBack, SkipForward, Route } from 'lucide-react'
import { getDeviceTrail } from '../services/api'

function RouteReplayTimeline({ selectedDevice, onReplayPointChange }) {
  const [trail, setTrail] = useState(null)
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [loading, setLoading] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => {
    const loadTrail = async () => {
      if (!selectedDevice?.device_id) {
        setTrail(null)
        setIndex(0)
        setPlaying(false)
        onReplayPointChange?.(null)
        return
      }

      setLoading(true)
      try {
        const end = new Date()
        const start = new Date(end.getTime() - 6 * 60 * 60 * 1000)
        const data = await getDeviceTrail(selectedDevice.device_id, start, end)
        setTrail(data)
        setIndex(0)
        if (data?.points?.length) {
          onReplayPointChange?.(data.points[0])
        } else {
          onReplayPointChange?.(null)
        }
      } catch {
        setTrail(null)
        onReplayPointChange?.(null)
      } finally {
        setLoading(false)
      }
    }

    loadTrail()
  }, [selectedDevice?.device_id])

  useEffect(() => {
    if (!playing || !trail?.points?.length) return

    timerRef.current = setInterval(() => {
      setIndex((prev) => {
        const next = prev + 1
        if (next >= trail.points.length) {
          setPlaying(false)
          return trail.points.length - 1
        }
        return next
      })
    }, 400)

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
    }
  }, [playing, trail])

  useEffect(() => {
    if (!trail?.points?.length) return
    const point = trail.points[index]
    onReplayPointChange?.(point || null)
  }, [index, trail])

  const total = trail?.points?.length || 0
  const current = trail?.points?.[index] || null

  const timeLabel = useMemo(() => {
    if (!current?.timestamp) return 'No replay point'
    return new Date(current.timestamp).toLocaleString()
  }, [current])

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
          <Route className="w-4 h-4 text-blue-600" /> Route Replay Timeline
        </h3>
        <span className="text-xs text-gray-500">{selectedDevice?.device_id || 'No device selected'}</span>
      </div>

      {loading && <p className="text-sm text-gray-500">Loading replay trail...</p>}
      {!loading && (!trail?.points || trail.points.length === 0) && (
        <p className="text-sm text-gray-500">Select a device with recent trail points.</p>
      )}

      {trail?.points?.length > 0 && (
        <>
          <input
            type="range"
            min={0}
            max={Math.max(total - 1, 0)}
            value={index}
            onChange={(e) => setIndex(Number(e.target.value))}
            className="w-full"
          />

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
              onClick={() => {
                setPlaying(false)
                setIndex(0)
              }}
            >
              <SkipBack className="w-4 h-4" />
            </button>
            <button
              type="button"
              className="px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
              onClick={() => setPlaying((v) => !v)}
            >
              {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
            <button
              type="button"
              className="px-2 py-1 rounded bg-gray-100 hover:bg-gray-200"
              onClick={() => setIndex((prev) => Math.min(prev + 1, total - 1))}
            >
              <SkipForward className="w-4 h-4" />
            </button>
            <p className="text-xs text-gray-600 ml-2">{index + 1} / {total}</p>
          </div>

          <div className="text-xs text-gray-600 grid grid-cols-2 gap-2">
            <p>Time: {timeLabel}</p>
            <p>Speed: {current?.speed ?? 'N/A'} km/h</p>
            <p>Lat: {current?.lat?.toFixed?.(5)}</p>
            <p>Lng: {current?.lng?.toFixed?.(5)}</p>
          </div>
        </>
      )}
    </div>
  )
}

export default RouteReplayTimeline
