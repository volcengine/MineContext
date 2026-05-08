import { Chart, CodeBlock, DataPoint, MediaElement } from "../types";

/**
   * 检测图表
   */
export function detectCharts(): Chart[] {
    const charts: Chart[] = [];

    // 查找常见的图表容器
    const chartSelectors = [
        "canvas",
        ".chart",
        ".graph",
        "[data-chart]",
        ".plotly-graph-div",
        ".highcharts-container",
        ".chart-container",
    ];

    chartSelectors.forEach((selector) => {
        const elements = document.querySelectorAll(selector);
        elements.forEach((element, index) => {
            const chartType = inferChartType(element);
            charts.push({
                type: chartType,
                data: extractChartData(element),
                title: extractChartTitle(element),
            });
        });
    });

    return charts;
}

/**
 * 推断图表类型
 */
export function inferChartType(element: Element): string {
    const className = element.className;
    const id = element.id;

    if (className.includes("pie") || id.includes("pie")) return "pie";
    if (className.includes("bar") || id.includes("bar")) return "bar";
    if (className.includes("line") || id.includes("line")) return "line";
    if (className.includes("scatter") || id.includes("scatter"))
        return "scatter";
    if (element.tagName.toLowerCase() === "canvas") return "canvas";

    return "unknown";
}

/**
 * 提取图表数据（简化实现）
 */
export function extractChartData(element: Element): any {
    // 这里可以实现更复杂的数据提取逻辑
    // 简化实现：返回元素的基本信息
    return {
        elementType: element.tagName,
        className: element.className,
        id: element.id,
        textContent: element.textContent?.trim().slice(0, 100),
    };
}

/**
 * 提取图表标题
 */
export function extractChartTitle(element: Element): string | undefined {
    // 查找附近的标题元素
    const titleSelectors = [
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        ".title",
        ".chart-title",
    ];

    let current: Element | null = element;
    while (current) {
        const parent = current.parentElement as any;
        if (parent) {
            for (const selector of titleSelectors) {
                const titleElement = parent.querySelector(selector);
                if (titleElement) {
                    return titleElement.textContent?.trim();
                }
            }
        }
        current = parent;
    }

    return undefined;
}

/**
 * 提取数据点
 */
export function extractDataPoints(): DataPoint[] {
    const dataPoints: DataPoint[] = [];

    // 从表格中提取数据点
    const tables = document.querySelectorAll("table");
    tables.forEach((table) => {
        const rows = table.querySelectorAll("tr");
        rows.forEach((row, rowIndex) => {
            if (rowIndex === 0) return; // 跳过表头

            const cells = row.querySelectorAll("td");
            cells.forEach((cell, cellIndex) => {
                const text = cell.textContent?.trim();
                if (text) {
                    const number = parseFloat(text.replace(/[^\d.-]/g, ""));
                    if (!isNaN(number)) {
                        dataPoints.push({
                            type: "table_numeric",
                            value: number,
                            unit: extractUnit(text),
                        });
                    }
                }
            });
        });
    });

    // 从页面文本中提取数值
    const numberRegex = /(-?\d+(?:\.\d+)?)\s*([a-zA-Z%°]+)?/g;
    const textContent = document.body.textContent || "";
    let match;

    while ((match = numberRegex.exec(textContent)) !== null) {
        const value = parseFloat(match[1]);
        const unit = match[2];

        dataPoints.push({
            type: "text_numeric",
            value: value,
            unit: unit,
        });
    }

    return dataPoints;
}

/**
 * 提取单位
 */
export function extractUnit(text: string): string | undefined {
    const unitMatch = text.match(/[a-zA-Z%°]+$/);
    return unitMatch ? unitMatch[0] : undefined;
}

/**
 * 估算媒体时长
 */
export function estimateMediaDuration(mediaElements: MediaElement[]): number {
    if (mediaElements.length === 0) return 0;

    // 计算所有媒体元素的平均时长
    const validDurations = mediaElements
        .map((element) => element.duration)
        .filter((duration) => duration !== undefined && duration > 0) as number[];

    if (validDurations.length === 0) return 0;

    return Math.round(
        validDurations.reduce((sum, duration) => sum + duration, 0) /
        validDurations.length
    );
}

/**
 * 提取转录文本（简化实现）
 */
export function extractTranscript(): string | undefined {
    // 查找页面中的转录文本或字幕
    const transcriptSelectors = [
        ".transcript",
        ".subtitle",
        ".caption",
        "[data-transcript]",
        ".video-transcript",
        ".audio-transcript",
    ];

    for (const selector of transcriptSelectors) {
        const element = document.querySelector(selector);
        if (element) {
            return element.textContent?.trim();
        }
    }

    // 如果没有找到专门的转录文本，尝试提取页面主要内容作为转录
    const mainContent = document.querySelector(
        "main, article, .content, .main-content"
    );
    if (mainContent) {
        const text = mainContent.textContent?.trim();
        return text
            ? text.slice(0, 1000) + (text.length > 1000 ? "..." : "")
            : undefined;
    }

    return undefined;
}

export function analyzeCodeLanguages(
    codeBlocks: CodeBlock[]
): Record<string, number> {
    const stats: Record<string, number> = {};

    codeBlocks.forEach((block) => {
        const lang = block.language || "unknown";
        stats[lang] = (stats[lang] || 0) + 1;
    });

    return stats;
}