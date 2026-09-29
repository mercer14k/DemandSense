import { useEffect, useRef } from "react";
import { init, use as registerCharts } from "echarts/core";
import { LineChart, type LineSeriesOption } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  MarkAreaComponent,
  LegendComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { Run, Scenario } from "./types";
registerCharts([
  LineChart,
  GridComponent,
  TooltipComponent,
  MarkAreaComponent,
  LegendComponent,
  CanvasRenderer,
]);
export function ForecastChart({
  run,
  backtest = false,
  scenario,
}: {
  run: Run;
  backtest?: boolean;
  scenario?: Scenario | null;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = init(ref.current, undefined, { renderer: "canvas" });
    const history = run.history.slice(-70);
    const dates = backtest
      ? run.backtest.map((x) => x.date)
      : [...history.map((x) => x.date), ...run.forecast.map((x) => x.date)];
    const actual = backtest
      ? run.backtest.map((x) => x.actual)
      : [...history.map((x) => x.demand), ...run.forecast.map(() => null)];
    const pad = backtest ? [] : history.map(() => null);
    const future = backtest ? run.backtest : run.forecast;
    const series: LineSeriesOption[] = [
      {
        name: "80% lower",
        type: "line",
        data: [...pad, ...future.map((x) => x.lower80)],
        stack: "band",
        symbol: "none",
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
        silent: true,
        tooltip: { show: false },
      },
      {
        name: "80% interval",
        type: "line",
        data: [...pad, ...future.map((x) => x.upper80 - x.lower80)],
        stack: "band",
        symbol: "none",
        lineStyle: { opacity: 0 },
        areaStyle: { color: "#4de1b0", opacity: 0.17 },
        silent: true,
        tooltip: { show: false },
      },
      {
        name: "Observed demand",
        type: "line",
        data: actual,
        symbol: "none",
        lineStyle: { color: "#aab9ca", width: 2 },
        itemStyle: { color: "#aab9ca" },
      },
      {
        name: backtest ? "Held-out forecast" : "Baseline forecast",
        type: "line",
        data: [...pad, ...future.map((x) => x.point)],
        symbol: "none",
        lineStyle: {
          color: "#55e3b8",
          width: 2.5,
          type: backtest ? "solid" : "dashed",
        },
        itemStyle: { color: "#55e3b8" },
      },
    ];
    if (scenario && !backtest)
      series.push({
        name: "Scenario",
        type: "line",
        data: [...pad, ...scenario.forecast.map((x) => x.point)],
        symbol: "none",
        lineStyle: { color: "#d4acff", width: 2.5 },
        itemStyle: { color: "#d4acff" },
      });
    chart.setOption({
      animation: false,
      backgroundColor: "transparent",
      textStyle: { fontFamily: "system-ui" },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#1a2430",
        borderColor: "#3b4a5b",
        textStyle: { color: "#eef5fa" },
        valueFormatter: (v: unknown) =>
          typeof v === "number" ? v.toFixed(1) : "—",
      },
      grid: { left: 50, right: 18, top: 20, bottom: 45 },
      xAxis: {
        type: "category",
        data: dates,
        axisLine: { lineStyle: { color: "#26313e" } },
        axisTick: { show: false },
        axisLabel: {
          color: "#8b9bac",
          fontSize: 12,
          formatter: (v: string) =>
            new Date(v + "T00:00:00").toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            }),
        },
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "#202a35", type: "dashed" } },
        axisLabel: { color: "#8b9bac", fontSize: 12 },
      },
      series,
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [run, backtest, scenario]);
  return (
    <div
      className="chart"
      ref={ref}
      role="img"
      aria-label={`${backtest ? "Held-out backtest" : "Daily demand and forecast"} with 80 percent empirical prediction interval. Exact values available in the data table below.`}
    />
  );
}
