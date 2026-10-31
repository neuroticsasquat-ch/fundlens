import { useEffect, useMemo, useRef } from "react";
import type { CSSProperties } from "react";
import { init } from "./echarts";
import type { ChartOption, ECElementEvent } from "./echarts";
import { useChartTheme } from "./theme";

type ECharts = ReturnType<typeof init>;

/**
 * Mounts an ECharts instance on a div and keeps it showing `option`, replacing (not merging) the
 * previous one on every change, and calls `onClick` with a clicked mark's event. The text colour
 * and background follow the colour scheme, so no chart sets them (a chart's other `textStyle`
 * settings are kept). The div needs a size from
 * `className` or `style`.
 */
function EChart({
  option,
  onClick,
  className,
  style,
}: {
  option: ChartOption;
  onClick?: (event: ECElementEvent) => void;
  className?: string;
  style?: CSSProperties;
}) {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<ECharts | null>(null);
  // Read through a ref, so the handler bound once at mount always calls the latest `onClick`.
  const click = useRef(onClick);
  const { ink, background } = useChartTheme();
  const themed = useMemo(
    () => ({
      ...option,
      backgroundColor: background,
      // ECharts types an option's `textStyle` as `unknown`, through its option index signature.
      textStyle: { ...(option.textStyle as object | undefined), color: ink },
    }),
    [option, ink, background],
  );

  useEffect(() => {
    click.current = onClick;
  }, [onClick]);

  useEffect(() => {
    const element = container.current!;
    const instance = init(element);
    chart.current = instance;
    instance.on("click", (event) => click.current?.(event));
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(element);
    return () => {
      observer.disconnect();
      instance.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    chart.current?.setOption(themed, { notMerge: true });
  }, [themed]);

  return <div ref={container} className={className} style={style} />;
}

export default EChart;
