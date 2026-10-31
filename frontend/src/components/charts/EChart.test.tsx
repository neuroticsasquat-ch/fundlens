import { DEFAULT_THEME } from "@mantine/core";
import { waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "../../test/app";
import { allOptions, click, init, lastOption } from "../../test/echarts";
import { matchMedia } from "../../test/media";
import EChart from "./EChart";

vi.mock("./echarts", () => import("../../test/echarts"));

describe("EChart", () => {
  it("inits once, replaces the option on every change and disposes on unmount", () => {
    const first = { series: [{ type: "line" as const, data: [1] }] };
    const second = { series: [{ type: "bar" as const, data: [2] }] };

    const { rerender, unmount } = renderWithProviders(<EChart option={first} className="chart" />);
    rerender(<EChart option={second} className="chart" />);

    expect(init).toHaveBeenCalledTimes(1);
    expect(allOptions().map((option) => option.series)).toEqual([first.series, second.series]);
    const chart = init.mock.results[0].value;
    expect(chart.setOption).toHaveBeenLastCalledWith(expect.objectContaining(second), {
      notMerge: true,
    });

    unmount();
    expect(chart.dispose).toHaveBeenCalledOnce();
  });

  it("calls the latest onClick with the clicked mark", () => {
    const first = vi.fn();
    const second = vi.fn();
    const option = { series: [] };

    const { rerender } = renderWithProviders(<EChart option={option} onClick={first} />);
    rerender(<EChart option={option} onClick={second} />);
    click({ name: "Maryland" });

    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledWith({ name: "Maryland" });
  });

  it("sets the colour scheme's ink and a transparent background on every option", async () => {
    renderWithProviders(<EChart option={{ series: [] }} />);
    expect(lastOption()).toMatchObject({
      backgroundColor: "transparent",
      textStyle: { color: DEFAULT_THEME.black },
    });
  });

  it("keeps a chart's own text style beside the scheme's ink", () => {
    renderWithProviders(<EChart option={{ series: [], textStyle: { fontSize: 11 } }} />);

    expect(lastOption()).toMatchObject({ textStyle: { fontSize: 11, color: DEFAULT_THEME.black } });
  });

  it("uses the dark ink when the system prefers dark", async () => {
    vi.stubGlobal("matchMedia", matchMedia({ dark: true }));

    renderWithProviders(<EChart option={{ series: [] }} />);

    await waitFor(() =>
      expect(lastOption()).toMatchObject({ textStyle: { color: DEFAULT_THEME.colors.dark[0] } }),
    );
  });
});
