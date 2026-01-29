import {
    BrowserContext,
    ContentType,
    ExtractionMode,
    PageMetadata,
    StructuredContent,
    ArticleContent,
    CodeContent,
    MultimediaContent,
    DataContent,
} from "../types";
import browser from "webextension-polyfill";
import {
    countWords,
    extractCodeBlocks,
    extractHeadings,
    extractImages,
    extractMediaElements,
    extractParagraphs,
    extractTables,
    estimateMediaDuration,
    extractTranscript,
    detectCharts,
    extractDataPoints,
    generateSummary,
    detectContentType,
    extractMetaTags,
    analyzeCodeLanguages,
    shouldStoreRawDom,
    createPagePreview,
    generateContextId
} from "../utils";

/**
 * 浏览器上下文提取器
 * 负责从当前页面提取结构化内容
 * 支持两种提取模式：
 * - SMART模式：提取结构化数据+截屏+详细分析
 * - BASIC模式：只提取基础信息+rawContext
 */
export class BrowserContextExtractor {
    /**
     * 提取完整的浏览器上下文
     * @param mode 提取模式，默认为智能模式
     */
    async extractContext(
        mode: ExtractionMode = ExtractionMode.SMART
    ): Promise<BrowserContext> {
        const contentType = detectContentType();
        const metadata = this.extractMetadata(contentType);

        let structuredContent: StructuredContent;
        let screenshot: string | undefined;
        let rawDom: string | undefined;

        if (mode === ExtractionMode.SMART) {
            // 智能模式：提取结构化内容+截屏+详细分析
            structuredContent = this.extractStructuredContent(contentType);
            screenshot = await this.captureScreenshot();
            rawDom = shouldStoreRawDom(contentType)
                ? document.body.innerHTML
                : undefined;
        } else {
            // 基础模式：只提取基础信息+rawContext
            structuredContent = this.extractBasicStructuredContent(contentType);
            screenshot = undefined;
            rawDom = document.body.innerHTML; // 基础模式总是存储rawContext
        }

        return {
            id: generateContextId(),
            url: location.href,
            title: document.title,
            timestamp: Date.now(),
            metadata,
            structuredContent,
            rawDom,
            screenshot,
            extractionMode: mode,
        };
    }

    /**
     * 提取页面元数据
     */
    public extractMetadata(contentType?: ContentType): PageMetadata {
        contentType = contentType || detectContentType();

        const metaTags = extractMetaTags();
        const wordCount = countWords(document.body.textContent || "");

        return {
            domain: location.hostname,
            language: document.documentElement.lang || "en",
            description: metaTags.description || "",
            keywords: metaTags.keywords
                ? metaTags.keywords.split(",").map((k) => k.trim())
                : [],
            author: metaTags.author || "",
            publishedTime:
                metaTags["article:published_time"] || metaTags.publishDate || "",
            modifiedTime:
                metaTags["article:modified_time"] || metaTags.modifiedDate || "",
            wordCount,
            contentType,
            metaTags,
        };
    }

    /**
     * 提取基础结构化内容（基础模式使用）
     */
    private extractBasicStructuredContent(
        contentType: ContentType
    ): StructuredContent {
        const title = document.title;
        const summary = generateSummary(contentType);

        return {
            title,
            summary,
            contentType,
            // 基础模式不提取详细的结构化内容
        };
    }

    /**
     * 提取结构化内容（智能模式使用）
     */
    private extractStructuredContent(
        contentType: ContentType
    ): StructuredContent {
        const title = document.title;
        const summary = generateSummary(contentType);

        const structuredContent: StructuredContent = {
            title,
            summary,
            contentType,
        };

        // 根据内容类型提取特定内容
        switch (contentType) {
            case ContentType.ARTICLE:
                structuredContent.articleContent = this.extractArticleContent();
                break;
            case ContentType.CODE:
                structuredContent.codeContent = this.extractCodeContent();
                break;
            case ContentType.MULTIMEDIA:
                structuredContent.multimediaContent = this.extractMultimediaContent();
                break;
            case ContentType.DATA:
                structuredContent.dataContent = this.extractDataContent();
                break;
        }

        return structuredContent;
    }

    /**
     * 提取文章内容
     */
    private extractArticleContent(): ArticleContent {
        const headings = extractHeadings();
        const paragraphs = extractParagraphs();
        const images = extractImages();

        return {
            headings,
            paragraphs,
            images,
        };
    }

    /**
     * 提取代码内容
     */
    // todo: 完善代码内容提取，包括文件结构分析
    private extractCodeContent(): CodeContent {
        const codeBlocks = extractCodeBlocks();
        const languageStats = analyzeCodeLanguages(codeBlocks);

        return {
            codeBlocks,
            languageStats,
            fileStructure: [],
        };
    }

    /**
     * 提取多媒体内容 - 完善的多媒体内容提取
     */
    private extractMultimediaContent(): MultimediaContent {
        const mediaElements = extractMediaElements();
        const duration = estimateMediaDuration(mediaElements);
        const transcript = extractTranscript();

        return {
            mediaElements,
            duration,
            transcript,
        };
    }

    /**
     * 提取数据内容 - 完善的数据内容提取
     */
    private extractDataContent(): DataContent {
        const tables = extractTables();
        const charts = detectCharts();
        const dataPoints = extractDataPoints();

        return {
            tables,
            charts,
            dataPoints,
        };
    }







    /**
     * 捕获屏幕截图
     */
    private async captureScreenshot(): Promise<string | undefined> {
        try {
            // 检查是否在浏览器扩展环境中
            if (browser?.tabs?.captureVisibleTab) {
                const dataUrl = await browser.tabs.captureVisibleTab(undefined, {
                    format: "png",
                    quality: 80,
                });
                return dataUrl;
            }

            // 检查是否支持 HTML2Canvas 或其他截图库
            // if (typeof (window as any).html2canvas !== 'undefined') {
            //     const canvas = await (window as any).html2canvas(document.body, {
            //         scale: 0.5, // 降低分辨率以减少数据大小
            //         useCORS: true,
            //         logging: false
            //     });
            //     return canvas.toDataURL('image/png', 0.8);
            // }

            // 降级方案：使用浏览器原生 API
            if (
                "mediaDevices" in navigator &&
                "getDisplayMedia" in navigator.mediaDevices
            ) {
                try {
                    const stream = await navigator.mediaDevices.getDisplayMedia({
                        video: true,
                        // todo: figure out there option
                        //{ mediaSource: 'screen' },
                        audio: false,
                    });

                    const video = document.createElement("video");
                    video.srcObject = stream;
                    video.play();

                    return new Promise((resolve) => {
                        video.onloadedmetadata = () => {
                            const canvas = document.createElement("canvas");
                            canvas.width = Math.min(video.videoWidth, 800); // 限制宽度
                            canvas.height = Math.min(video.videoHeight, 600); // 限制高度

                            const ctx = canvas.getContext("2d");
                            ctx?.drawImage(video, 0, 0, canvas.width, canvas.height);

                            const dataUrl = canvas.toDataURL("image/png", 0.7);

                            // 停止媒体流
                            stream.getTracks().forEach((track: any) => track.stop());

                            resolve(dataUrl);
                        };
                    });
                } catch (error) {
                    console.warn("屏幕捕获失败:", error);
                }
            }

            // 最后降级：创建页面预览
            return createPagePreview();
        } catch (error) {
            console.error("截图捕获失败:", error);
            return undefined;
        }
    }


}
