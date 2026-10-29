import type { CSSProperties } from "react";

export type SceneKey = "cat-garden" | "racing-night" | "comic-rooftop" | "moonlit-hills";

export function resolveScene(theme: Record<string, unknown> | undefined): SceneKey {
  const raw = theme?.scene;
  if (raw === "cat-garden" || raw === "racing-night" || raw === "comic-rooftop" || raw === "moonlit-hills") {
    return raw;
  }
  return "moonlit-hills";
}

const labels: Record<SceneKey, string> = {
  "cat-garden": "A quiet garden under the stars",
  "racing-night": "A night circuit beneath the lights",
  "comic-rooftop": "A rooftop above the sleeping city",
  "moonlit-hills": "A little place under the moon",
};

export default function ThemeScene({ theme }: { theme: Record<string, unknown> | undefined }) {
  const scene = resolveScene(theme);
  return (
    <div className={`landscape scene scene--${scene}`} role="img" aria-label={labels[scene]}>
      <div className="scene-sky-object" />
      <div className="scene-distant" />
      <div className="scene-midground" />
      <div className="scene-ground" />
      <div className="scene-feature">
        {scene === "cat-garden" && <><span className="scene-cat scene-cat--one" /><span className="scene-cat scene-cat--two" /><span className="scene-flower flower--one" /><span className="scene-flower flower--two" /></>}
        {scene === "racing-night" && <><span className="scene-track" /><span className="scene-car scene-car--one" /><span className="scene-car scene-car--two" /><span className="scene-checker" /></>}
        {scene === "comic-rooftop" && <><span className="scene-building building--one" /><span className="scene-building building--two" /><span className="scene-signal" /><span className="scene-rooftop-edge" /></>}
        {scene === "moonlit-hills" && <><span className="scene-tree" /><span className="scene-path" /></>}
      </div>
      <span className="scene-caption">{labels[scene]}</span>
    </div>
  );
}
