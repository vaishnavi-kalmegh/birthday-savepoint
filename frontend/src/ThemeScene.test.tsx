import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import ThemeScene, { resolveScene } from "./ThemeScene";

afterEach(() => cleanup());

describe("personalized theme scenes", () => {
  it("uses a safe default for missing or unknown theme data", () => {
    expect(resolveScene(undefined)).toBe("moonlit-hills");
    expect(resolveScene({ scene: "unknown-theme" })).toBe("moonlit-hills");
    render(<ThemeScene theme={{ scene: "unknown-theme" }} />);
    expect(screen.getByRole("img", { name: /under the moon/i })).toBeInTheDocument();
  });

  it.each([
    ["cat-garden", /quiet garden/i],
    ["racing-night", /night circuit/i],
    ["comic-rooftop", /rooftop above/i],
    ["moonlit-hills", /under the moon/i],
  ] as const)("renders the %s scene", (scene, label) => {
    const { container } = render(<ThemeScene theme={{ scene }} />);
    expect(screen.getByRole("img", { name: label })).toBeInTheDocument();
    expect(container.firstElementChild).toHaveClass(`scene--${scene}`);
  });
});
