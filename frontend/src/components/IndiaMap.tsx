const REGIONS = [
  { name: "Northern Region", count: 32, x: 150, y: 78, color: "#164A7A" },
  { name: "Western Region", count: 28, x: 92, y: 150, color: "#16827A" },
  { name: "Southern Region", count: 41, x: 150, y: 218, color: "#F39A24" },
  { name: "Eastern Region", count: 19, x: 208, y: 150, color: "#C98A2E" },
];

export default function IndiaMap() {
  return (
    <div>
      <svg className="map-svg" viewBox="0 0 300 300" role="img" aria-label="Illustrative map of project distribution across four regions of India">
        <defs>
          <pattern id="mapgrid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M20 0 H0 V20" fill="none" stroke="#D9E1EA" strokeWidth="0.7" />
          </pattern>
        </defs>
        <rect width="300" height="300" fill="#F3F7FB" rx="8" />
        <rect width="300" height="300" fill="url(#mapgrid)" rx="8" />
        <path d="M150 30 L196 70 L226 120 L214 190 L176 244 L150 272 L124 244 L86 190 L74 120 L104 70 Z" fill="none" stroke="#164A7A" strokeWidth="1.6" strokeDasharray="6 4" opacity="0.55" />
        <g stroke="#B9C9E4" strokeWidth="1" opacity="0.8">
          <path d="M92 150 H208 M150 78 V218 M110 105 L190 195 M190 105 L110 195" strokeDasharray="3 4" />
        </g>
        {REGIONS.map((r) => (
          <g key={r.name} className="map-marker">
            <circle cx={r.x} cy={r.y} r="16" fill={r.color} opacity="0.16" />
            <circle cx={r.x} cy={r.y} r="7" fill={r.color} stroke="#fff" strokeWidth="2" />
            <text x={r.x} y={r.y - 22} textAnchor="middle" fontSize="11" fontWeight="700" fill="#0D3157">{r.count}</text>
          </g>
        ))}
        <text x="12" y="288" fontSize="10" fill="#52606D">28.61° N · 77.20° E — national grid (illustrative)</text>
      </svg>
      <ul className="region-list">
        {REGIONS.map((r) => (
          <li key={r.name}><i style={{ background: r.color }} aria-hidden="true" />{r.name}<strong>{r.count} projects</strong></li>
        ))}
      </ul>
      <p className="map-note">Map view is illustrative. Refer to project records for authoritative data.</p>
    </div>
  );
}
