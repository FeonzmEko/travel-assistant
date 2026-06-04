import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react';

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
  style?: CSSProperties;
  zoom?: number;
  center?: [number, number];
  onSpotClick?: (spot: MapSpot) => void;
}

interface AMapMap {
  addControl: (control: unknown) => void;
  destroy: () => void;
  remove: (marker: AMapMarker) => void;
  setFitView: (
    markers: AMapMarker[],
    immediately?: boolean,
    avoid?: [number, number, number, number],
  ) => void;
}

interface AMapMarker {
  on: (event: string, handler: () => void) => void;
  setMap: (map: AMapMap) => void;
}

interface AMapDriving {
  clear: () => void;
  search: (origin: unknown, destination: unknown, options: { waypoints: unknown[] }) => void;
}

type AMapConstructor<T> = new (...args: unknown[]) => T;

interface AMapNamespace {
  Map: AMapConstructor<AMapMap>;
  Scale: AMapConstructor<unknown>;
  ToolBar: AMapConstructor<unknown>;
  Marker: AMapConstructor<AMapMarker>;
  Pixel: AMapConstructor<unknown>;
  Driving: AMapConstructor<AMapDriving>;
  LngLat: AMapConstructor<unknown>;
  DrivingPolicy?: {
    LEAST_TIME?: unknown;
  };
}

declare global {
  interface Window {
    AMap?: AMapNamespace;
    _AMapSecurityConfig?: {
      securityJsCode: string;
    };
  }
}

let mapScriptLoaded = false;
let mapScriptLoading = false;
const loadCallbacks: {
  resolve: () => void;
  reject: (error: Error) => void;
}[] = [];

function loadAMapScript(key: string, securityCode?: string): Promise<void> {
  if (mapScriptLoaded) return Promise.resolve();
  return new Promise((resolve, reject) => {
    if (mapScriptLoading) {
      loadCallbacks.push({ resolve, reject });
      return;
    }
    mapScriptLoading = true;

    if (securityCode) {
      window._AMapSecurityConfig = { securityJsCode: securityCode };
    }
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${key}&plugin=AMap.Driving,AMap.Scale,AMap.ToolBar`;
    script.onload = () => {
      mapScriptLoaded = true;
      mapScriptLoading = false;
      resolve();
      loadCallbacks.forEach((cb) => cb.resolve());
      loadCallbacks.length = 0;
    };
    script.onerror = () => {
      const error = new Error('高德地图脚本加载失败，请检查 VITE_AMAP_KEY 与 VITE_AMAP_SECURITY_CODE');
      mapScriptLoading = false;
      reject(error);
      loadCallbacks.forEach((cb) => cb.reject(error));
      loadCallbacks.length = 0;
    };
    document.head.appendChild(script);
  });
}

function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (char) => {
    const entities: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    };
    return entities[char];
  });
}

const AMAP_KEY = import.meta.env.VITE_AMAP_KEY || '';
const AMAP_SECURITY_CODE = import.meta.env.VITE_AMAP_SECURITY_CODE || '';

export default function AMapView({
  spots = [],
  route,
  style = { width: '100%', height: 400 },
  zoom = 12,
  center,
  onSpotClick,
}: AMapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<AMapMap | null>(null);
  const markersRef = useRef<AMapMarker[]>([]);
  const drivingRef = useRef<AMapDriving | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const initMap = useCallback(async () => {
    if (!containerRef.current || !AMAP_KEY) return;
    try {
      await loadAMapScript(AMAP_KEY, AMAP_SECURITY_CODE);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : '高德地图脚本加载失败');
      return;
    }
    const AMap = window.AMap;
    if (!AMap || !containerRef.current) return;

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
    setMapReady(true);
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
    if (!mapReady || !mapRef.current || !window.AMap) return;
    const AMap = window.AMap;
    const map = mapRef.current;

    markersRef.current.forEach((m) => map.remove(m));
    markersRef.current = [];

    spots.forEach((spot, index) => {
      const marker = new AMap.Marker({
        position: [spot.longitude, spot.latitude],
        title: spot.name,
        label: {
          content: `<div style="padding:2px 6px;background:#1677ff;color:#fff;border-radius:10px;font-size:12px;white-space:nowrap;">${index + 1}. ${escapeHtml(spot.name)}</div>`,
          direction: 'top',
          offset: new AMap.Pixel(0, -5),
        },
      });

      if (onSpotClick) {
        marker.on('click', () => onSpotClick(spot));
      }

      marker.setMap(map);
      markersRef.current.push(marker);
    });

    if (spots.length > 0) {
      map.setFitView(markersRef.current, false, [60, 60, 60, 60]);
    }
  }, [mapReady, spots, onSpotClick]);

  useEffect(() => {
    if (!mapReady || !mapRef.current || !window.AMap || !route) return;
    const AMap = window.AMap;
    const map = mapRef.current;

    if (drivingRef.current) {
      drivingRef.current.clear();
    }

    drivingRef.current = new AMap.Driving({
      map,
      policy: AMap.DrivingPolicy?.LEAST_TIME,
      hideMarkers: true,
    });

    const waypoints = route.waypoints?.map((w) => new AMap.LngLat(w[0], w[1])) || [];

    drivingRef.current.search(
      new AMap.LngLat(route.origin[0], route.origin[1]),
      new AMap.LngLat(route.destination[0], route.destination[1]),
      { waypoints },
    );
  }, [mapReady, route]);

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
        请配置 VITE_AMAP_KEY；若启用 JS API 安全密钥，请同时配置 VITE_AMAP_SECURITY_CODE
      </div>
    );
  }

  if (loadError) {
    return (
      <div style={{
        ...style,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#fff2f0',
        borderRadius: 8,
        color: '#cf1322',
      }}>
        {loadError}
      </div>
    );
  }

  return <div ref={containerRef} style={{ borderRadius: 8, ...style }} />;
}
