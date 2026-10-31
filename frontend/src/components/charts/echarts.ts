import { BarChart, LineChart } from "echarts/charts";
import type { BarSeriesOption, LineSeriesOption } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import type {
  GridComponentOption,
  LegendComponentOption,
  TooltipComponentOption,
} from "echarts/components";
import { init, use as register } from "echarts/core";
import type { ComposeOption, ECElementEvent } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";

// The one place ECharts is imported (spec §8: the only charting library). Registering just the
// series and components the charts draw keeps the rest of ECharts out of the bundle, and tests mock
// this module's `init` to read the option a chart sets. A page that draws another series or
// component registers it here.

// `use` renamed, as the linter takes a top-level `use()` for React's hook.
register([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

export type ChartOption = ComposeOption<
  | BarSeriesOption
  | LineSeriesOption
  | GridComponentOption
  | LegendComponentOption
  | TooltipComponentOption
>;

export { init };
export type { ECElementEvent };
