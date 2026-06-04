import { useEffect, useRef, useCallback } from 'react';

export interface MapSpot {
  name: string;
  longitude: number;
  latitude: number;
  description?: string;
}

export interface MapRoute {
  origin: [number, number];
  destination: [number, number];
  waypoints?: [number, number][];
}

interface AMapViewProps {
  spots?: MapSpot[];
  route?: MapRoute;
  style?: React.CSSProperties;
  zoom?: number;
  center?: [number, number];
  onSpotClick?: (spot: MapSpot) => void;
}

declare global {
  interface Window {
    AMap: any;
    _AMapSecurityConfig: any;
  }
}

let mapScriptLoaded = false;
let mapScriptLoading = false;
const loadCallbacks: (() => void)[] = [];

function loadAMapScript(key: string): Promise<void> {
  if (mapScriptLoaded) return Promise.resolve();
  return new Promise((resolve) => {
    if (mapScriptLoading) {
      loadCallbacks.push(resolve);
      return;
    }
    mapScriptLoading = true;

    window._AMapSecurityConfig = { securityJsCode: '' };
    const script = document.createElement('script');
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${key}&plugin=AMap.Driving,AMap.Scale,AMap.ToolBar`;
    script.onload = () => {
      mapScriptLoaded = true;
      mapScriptLoading = false;
      resolve();
      loadCallbacks.forEach((cb) => cb());
      loadCallbacks.length = 0;
    };
    document.head.appendChild(script);
  });
}

const AMAP_KEY = import.meta.env.VITE_AMAP_KEY || '';

export default function AMapView({
  spots = [],
  route,
  style = { width: '100%', height: 400 },
  zoom = 12,
  center,
  onSpotClick,
}: AMapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const drivingRef = useRef<any>(null);

  const initMap = useCallback(async () => {
    if (!containerRef.current || !AMAP_KEY) return;
    await loadAMapScript(AMAP_KEY);
    const AMap = window.AMap;
    if (!AMap) return;

    const defaultCenter = center || (spots.length > 0
      ? [spots[0].longitude, spots[0].latitude]
      : [116.397428, 39.90923]);

    mapRef.current = new AMap.Map(containerRef.current, {
      zoom,
      center: defaultCenter,
      viewMode: '2D',
    });

    mapRef.current.addControl(new AMap.Scale());
    mapRef.current.addControl(new AMap.ToolBar({ position: 'RT' }));
  }, []);

  useEffect(() => {
    initMap();
    return () => {
      if (mapRef.current) {
        mapRef.current.destroy();
        mapRef.current = null;
      }
    };
  }, [initMap]);

  useEffect(() => {
    if (!mapRef.current || !window.AMap) return;
    const AMap = window.AMap;

    markersRef.current.forEach((m) => mapRef.current.remove(m));
    markersRef.current = [];

    spots.forEach((spot, index) => {
      const marker = new AMap.Marker({
        position: [spot.longitude, spot.latitude],
        title: spot.name,
        label: {
          content: `<div style="padding:2px 6px;background:#1677ff;color:#fff;border-radius:10px;font-size:12px;white-space:nowrap;">${index + 1}. ${spot.name}</div>`,
          direction: 'top',
          offset: new AMap.Pixel(0, -5),
        },
      });

      if (onSpotClick) {
        marker.on('click', () => onSpotClick(spot));
      }

      marker.setMap(mapRef.current);
      markersRef.current.push(marker);
    });

    if (spots.length > 0) {
      mapRef.current.setFitView(markersRef.current, false, [60, 60, 60, 60]);
    }
  }, [spots, onSpotClick]);

  useEffect(() => {
    if (!mapRef.current || !window.AMap || !route) return;
    const AMap = window.AMap;

    if (drivingRef.current) {
      drivingRef.current.clear();
    }

    drivingRef.current = new AMap.Driving({
      map: mapRef.current,
      policy: AMap.DrivingPolicy?.LEAST_TIME,
      hideMarkers: true,
    });

    const waypoints = route.waypoints?.map((w) => new AMap.LngLat(w[0], w[1])) || [];

    drivingRef.current.search(
      new AMap.LngLat(route.origin[0], route.origin[1]),
      new AMap.LngLat(route.destination[0], route.destination[1]),
      { waypoints },
    );
  }, [route]);

  if (!AMAP_KEY) {
    return (
      <div style={{
        ...style,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f5f5f5',
        borderRadius: 8,
        color: '#999',
      }}>
        请配置 VITE_AMAP_KEY 环境变量以启用地图功能
      </div>
    );
  }

  return <div ref={containerRef} style={{ borderRadius: 8, ...style }} />;
}
