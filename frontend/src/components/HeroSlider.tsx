import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

type Slide = { src: string; alt: string; tag: string; title: string; text: string; cta: { to: string; label: string } };

const SLIDES: Slide[] = [
  {
    src: "https://picsum.photos/seed/bharat-highway-corridor/1200/700",
    alt: "National highway corridor at dawn",
    tag: "Snapshot-based oversight",
    title: "1,700+ project snapshots, one institutional view",
    text: "Reported cost, schedule and implementation signals — with dataset dates shown beside every number.",
    cta: { to: "/dashboard", label: "Explore Dashboard" },
  },
  {
    src: "https://picsum.photos/seed/railway-bridge-project/1200/700",
    alt: "Railway bridge construction over a river",
    tag: "Risk signals with sources",
    title: "Every score carries its source and limitation",
    text: "Missing revised figures stay unavailable — never silently treated as safe.",
    cta: { to: "/documents", label: "View Method" },
  },
  {
    src: "https://picsum.photos/seed/power-grid-expansion/1200/700",
    alt: "Power transmission lines across the landscape",
    tag: "SameekshaSetu Platform",
    title: "Built to show how public monitoring can work",
    text: "A credible national infrastructure project monitoring portal.",
    cta: { to: "/projects", label: "Browse Projects" },
  },
];

export default function HeroSlider() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const timer = useRef<number | null>(null);

  const go = useCallback((next: number) => {
    setIndex((next + SLIDES.length) % SLIDES.length);
  }, []);

  useEffect(() => {
    if (paused || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    timer.current = window.setTimeout(() => go(index + 1), 6000);
    return () => { if (timer.current) window.clearTimeout(timer.current); };
  }, [index, paused, go]);

  const slide = SLIDES[index];

  return (
    <div
      className="hero-slider"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      role="region"
      aria-roledescription="carousel"
      aria-label="Portal highlights"
    >
      <div className="slides">
        {SLIDES.map((s, i) => (
          <div key={s.src} className={`slide${i === index ? " active" : ""}`} aria-hidden={i !== index}>
            <img src={s.src} alt={s.alt} loading={i === 0 ? "eager" : "lazy"} />
          </div>
        ))}
      </div>
      <div className="slide-caption" aria-live="polite">
        <p className="slide-tag">{slide.tag}</p>
        <p className="slide-title">{slide.title}</p>
        <p className="slide-text">{slide.text}</p>
        <Link className="btn btn-primary btn-sm" to={slide.cta.to}>{slide.cta.label}</Link>
      </div>
      <button className="slide-arrow prev" type="button" onClick={() => go(index - 1)} aria-label="Previous slide">‹</button>
      <button className="slide-arrow next" type="button" onClick={() => go(index + 1)} aria-label="Next slide">›</button>
      <div className="slide-dots" role="tablist" aria-label="Choose slide">
        {SLIDES.map((s, i) => (
          <button key={s.src} type="button" role="tab" aria-selected={i === index} aria-label={`Slide ${i + 1}: ${s.tag}`} className={`dot${i === index ? " active" : ""}`} onClick={() => go(i)} />
        ))}
      </div>
    </div>
  );
}
