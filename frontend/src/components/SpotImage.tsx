import { useEffect, useMemo, useState, type CSSProperties } from 'react';

interface SpotImageProps {
  src?: string;
  seed?: string;
  name: string;
  style?: CSSProperties;
}

function placeholderSvg(name: string): string {
  const label = (name || '景点').slice(0, 8);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400">
    <defs>
      <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#F6C9A6"/>
        <stop offset="100%" stop-color="#C25430"/>
      </linearGradient>
    </defs>
    <rect width="600" height="400" fill="url(#g)"/>
    <text x="50%" y="48%" font-size="120" text-anchor="middle" dominant-baseline="middle">🏞️</text>
    <text x="50%" y="72%" font-size="36" fill="#ffffff" text-anchor="middle" dominant-baseline="middle" font-family="sans-serif">${label}</text>
  </svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

/**
 * 景点图片：依次尝试后端图片、Picsum 景色兜底、本地 SVG 占位，
 * 确保无论外部图片服务是否可用，都能稳定显示画面。
 */
export default function SpotImage({ src, seed, name, style }: SpotImageProps) {
  const sources = useMemo(() => {
    const list: string[] = [];
    if (src) list.push(src);
    const key = encodeURIComponent(seed || name || 'spot');
    list.push(`https://picsum.photos/seed/${key}/600/400`);
    list.push(placeholderSvg(name));
    return Array.from(new Set(list));
  }, [src, seed, name]);

  const [idx, setIdx] = useState(0);

  useEffect(() => {
    setIdx(0);
  }, [sources]);

  return (
    <img
      src={sources[Math.min(idx, sources.length - 1)]}
      alt={name}
      loading="lazy"
      style={{ display: 'block', width: '100%', objectFit: 'cover', ...style }}
      onError={() => setIdx((i) => (i < sources.length - 1 ? i + 1 : i))}
    />
  );
}
