import { ContentType } from "../types";
import { extractFirstParagraph } from "./contentExtractor";

/**
 * 生成摘要
 */
export function generateSummary(contentType: ContentType) {
    const description = document
        .querySelector('meta[name="description"]')
        ?.getAttribute("content");

    if (description) return description;

    // 根据内容类型生成不同摘要
    switch (contentType) {
        case ContentType.ARTICLE:
            return extractFirstParagraph();
        case ContentType.CODE:
            return "代码页面，包含多个代码片段";
        case ContentType.MULTIMEDIA:
            return "多媒体内容页面";
        case ContentType.DATA:
            return "数据表格页面";
        default:
            return document.title;
    }
}




/**
 * 创建页面预览（降级方案）
 */
export function createPagePreview() {
    // 创建一个简化的页面预览
    const canvas = document.createElement("canvas");
    canvas.width = 400;
    canvas.height = 300;

    const ctx = canvas.getContext("2d");
    if (!ctx) return "";

    // 白色背景
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 页面标题
    ctx.fillStyle = "#333333";
    ctx.font = "16px Arial";
    ctx.fillText(document.title.slice(0, 30), 20, 40);

    // URL
    ctx.fillStyle = "#666666";
    ctx.font = "12px Arial";
    ctx.fillText(location.hostname, 20, 70);

    // 内容预览
    const contentPreview =
        document.body.textContent?.slice(0, 200) || "No content";
    ctx.fillStyle = "#444444";
    ctx.font = "10px Arial";

    const lines = contentPreview.split("\n").slice(0, 5);
    lines.forEach((line, index) => {
        ctx.fillText(line.slice(0, 50), 20, 100 + index * 15);
    });

    // 时间戳
    ctx.fillStyle = "#999999";
    ctx.font = "10px Arial";
    ctx.fillText(new Date().toLocaleString(), 20, 270);

    return canvas.toDataURL("image/png");
}