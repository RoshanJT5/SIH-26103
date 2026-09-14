export default function HeroArt() {
  return (
    <figure className="hero-art" style={{ margin: 0 }}>
      <svg viewBox="0 0 640 400" role="img" aria-label="Editorial illustration of roads, a bridge, rail line, power lines and public buildings connected by data lines to a monitoring dashboard">
        <rect width="640" height="400" fill="#F3F7FB" />
        <g stroke="#D9E1EA" strokeWidth="1">
          <path d="M0 60 H640 M0 120 H640 M0 180 H640 M0 240 H640 M0 300 H640 M0 360 H640" />
          <path d="M80 0 V400 M180 0 V400 M280 0 V400 M380 0 V400 M480 0 V400 M580 0 V400" />
        </g>
        <ellipse cx="320" cy="352" rx="250" ry="26" fill="#E2E8F0" />
        <g>
          <rect x="60" y="150" width="120" height="150" rx="4" fill="#0D3157" />
          <rect x="76" y="166" width="26" height="22" fill="#F3D9A8" />
          <rect x="110" y="166" width="26" height="22" fill="#F3D9A8" />
          <rect x="144" y="166" width="20" height="22" fill="#F3D9A8" />
          <rect x="76" y="198" width="26" height="22" fill="#CFE3D8" />
          <rect x="110" y="198" width="26" height="22" fill="#CFE3D8" />
          <rect x="144" y="198" width="20" height="22" fill="#CFE3D8" />
          <rect x="76" y="230" width="88" height="10" fill="#F39A24" />
          <rect x="60" y="132" width="120" height="10" fill="#164A7A" />
        </g>
        <g>
          <path d="M230 300 L230 210 M410 300 L410 210 M230 230 L410 230" stroke="#164A7A" strokeWidth="10" strokeLinecap="round" />
          <path d="M230 230 L260 200 L290 230 L320 200 L350 230 L380 200 L410 230" fill="none" stroke="#F39A24" strokeWidth="4" />
          <rect x="222" y="196" width="16" height="16" rx="3" fill="#16827A" />
          <rect x="312" y="186" width="16" height="16" rx="3" fill="#16827A" />
          <rect x="402" y="196" width="16" height="16" rx="3" fill="#16827A" />
        </g>
        <g>
          <path d="M450 310 L560 310" stroke="#0D3157" strokeWidth="8" strokeLinecap="round" />
          <path d="M450 310 L470 270 L490 310 M500 310 L520 270 L540 310" fill="none" stroke="#0D3157" strokeWidth="5" />
          <rect x="462" y="252" width="56" height="20" rx="4" fill="#164A7A" />
          <rect x="468" y="257" width="14" height="10" fill="#F3D9A8" />
          <rect x="486" y="257" width="14" height="10" fill="#F3D9A8" />
        </g>
        <g stroke="#0D3157" strokeWidth="3">
          <path d="M120 90 L120 140 M200 70 L200 140 M300 84 L300 140" />
          <path d="M96 100 Q160 78 224 100 M176 80 Q240 58 304 80 M276 94 Q330 76 384 94" fill="none" />
        </g>
        <circle cx="120" cy="90" r="5" fill="#F39A24" />
        <circle cx="200" cy="70" r="5" fill="#F39A24" />
        <circle cx="300" cy="84" r="5" fill="#F39A24" />
        <g>
          <rect x="430" y="40" width="170" height="118" rx="8" fill="#0D3157" />
          <rect x="430" y="40" width="170" height="26" rx="8" fill="#164A7A" />
          <circle cx="444" cy="53" r="4" fill="#F39A24" />
          <circle cx="458" cy="53" r="4" fill="#16827A" />
          <circle cx="472" cy="53" r="4" fill="#fff" />
          <rect x="442" y="78" width="90" height="10" rx="2" fill="#F39A24" />
          <rect x="442" y="94" width="130" height="7" rx="2" fill="#4A82C2" />
          <rect x="442" y="107" width="110" height="7" rx="2" fill="#16827A" />
          <rect x="442" y="120" width="70" height="7" rx="2" fill="#7FA8D0" />
          <rect x="442" y="136" width="120" height="10" rx="2" fill="#fff" opacity="0.85" />
        </g>
        <g fill="none" strokeWidth="2.5" className="data-line-group">
          <path className="data-line" d="M180 150 C 260 120, 340 120, 430 90" stroke="#F39A24" />
          <path className="data-line" d="M320 200 C 360 170, 400 150, 432 120" stroke="#16827A" />
          <path className="data-line" d="M200 140 C 280 110, 350 100, 432 105" stroke="#164A7A" />
        </g>
        <circle className="pulse-node" cx="180" cy="150" r="7" fill="#F39A24" stroke="#fff" strokeWidth="2" />
        <circle className="pulse-node" cx="320" cy="200" r="7" fill="#16827A" stroke="#fff" strokeWidth="2" />
        <circle className="pulse-node" cx="432" cy="105" r="7" fill="#164A7A" stroke="#fff" strokeWidth="2" />
        <g fontFamily="Noto Sans, sans-serif" fontSize="11" fontWeight="700" fill="#0D3157">
          <text x="60" y="322">ROADS</text>
          <text x="252" y="322">BRIDGES</text>
          <text x="452" y="332">RAIL · POWER</text>
        </g>
      </svg>
      <figcaption>Illustrative view of infrastructure monitoring — roads, bridges, rail and power linked to a risk dashboard.</figcaption>
    </figure>
  );
}
