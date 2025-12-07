import {
    BrowserContext,
    ContentType,
    PageMetadata,
    StructuredContent,
    ArticleContent,
    CodeContent,
    MultimediaContent,
    DataContent,
    Heading,
    Paragraph,
    Image,
    CodeBlock,
    MediaElement,
    Table,
} from "../types";
import browser from 'webextension-polyfill';

/**
 * 浏览器上下文提取器
 * 负责从当前页面提取结构化内容
 */
export class BrowserContextExtractor {

    /**
     * 提取完整的浏览器上下文
     */
    async extractContext(): Promise<BrowserContext> {
        const contentType = this.detectContentType();
        const metadata = this.extractMetadata(contentType);
        const structuredContent = this.extractStructuredContent(contentType);

        return {
            id: this.generateContextId(),
            url: location.href,
            title: document.title,
            timestamp: Date.now(),
            metadata,
            structuredContent,
            rawDom: this.shouldStoreRawDom(contentType) ? document.body.innerHTML : undefined,
        };
    }

    /**
     * 检测内容类型
     */
    public detectContentType(): ContentType {
        const url = location.href;
        const html = document.documentElement.innerHTML;

        // 代码相关页面检测
        if (this.isCodePage(url, html)) {
            return ContentType.CODE;
        }

        // 多媒体页面检测
        if (this.isMultimediaPage(html)) {
            return ContentType.MULTIMEDIA;
        }

        // 数据表格页面检测
        if (this.isDataPage(html)) {
            return ContentType.DATA;
        }

        // 文章页面检测
        if (this.isArticlePage(html)) {
            return ContentType.ARTICLE;
        }

        return ContentType.UNKNOWN;
    }

    /**
     * 提取页面元数据
     */
    public extractMetadata(contentType?: ContentType): PageMetadata {
        contentType = contentType || this.detectContentType();

        const metaTags = this.extractMetaTags();
        const wordCount = this.countWords(document.body.textContent || '');

        return {
            domain: location.hostname,
            language: document.documentElement.lang || 'en',
            description: metaTags.description || '',
            keywords: metaTags.keywords ? metaTags.keywords.split(',').map(k => k.trim()) : [],
            author: metaTags.author || '',
            publishedTime: metaTags['article:published_time'] || metaTags.publishDate || '',
            modifiedTime: metaTags['article:modified_time'] || metaTags.modifiedDate || '',
            wordCount,
            contentType,
            metaTags
        };
    }

    /**
     * 提取结构化内容
     */
    private extractStructuredContent(contentType: ContentType): StructuredContent {
        const title = document.title;
        const summary = this.generateSummary(contentType);

        const structuredContent: StructuredContent = {
            title,
            summary,
            contentType
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
        const headings = this.extractHeadings();
        const paragraphs = this.extractParagraphs();
        const images = this.extractImages();

        return {
            headings,
            paragraphs,
            images,
        };
    }

    /**
     * 提取代码内容
     */
    private extractCodeContent(): CodeContent {
        const codeBlocks = this.extractCodeBlocks();
        const languageStats = this.analyzeCodeLanguages(codeBlocks);

        return {
            codeBlocks,
            languageStats,
            fileStructure: [] // 简化实现
        };
    }

    /**
     * 提取多媒体内容
     */
    // TODO: 实现提取多媒体内容的逻辑
    private extractMultimediaContent(): MultimediaContent {
        const mediaElements = this.extractMediaElements();

        return {
            mediaElements,
            duration: undefined,
            transcript: undefined
        };
    }

    /**
     * 提取数据内容
     * todo: 实现提取数据内容的逻辑
     */
    private extractDataContent(): DataContent {
        const tables = this.extractTables();

        return {
            tables,
            charts: [], // 简化实现
            dataPoints: [] // 简化实现
        };
    }

    /**
     * 检测代码页面
     */
    private isCodePage(url: string, html: string): boolean {
        const codeIndicators = [
            /github\.com/i,
            /gitlab\.com/i,
            /bitbucket\.org/i,
            /stackoverflow\.com/i,
            /codepen\.io/i,
            /jsfiddle\.net/i,
            /<pre[^>]*>|<code[^>]*>/i,
            /class=\"highlight\"/i,
            /syntaxhighlighter/i
        ];

        return codeIndicators.some(indicator => indicator.test(url) || indicator.test(html));
    }

    /**
     * 检测多媒体页面
     */
    private isMultimediaPage(html: string): boolean {
        const mediaIndicators = [
            /<video[^>]*>/i,
            /<audio[^>]*>/i,
            /<canvas[^>]*>/i,
            /youtube\.com/i,
            /vimeo\.com/i,
            /soundcloud\.com/i
        ];

        return mediaIndicators.some(indicator => indicator.test(html));
    }

    /**
     * 检测数据页面
     */
    private isDataPage(html: string): boolean {
        const dataIndicators = [
            /<table[^>]*>/i,
            /class=\"table\"/i,
            /data-grid/i,
            /chart/i,
            /graph/i,
            /dataset/i
        ];

        return dataIndicators.some(indicator => indicator.test(html));
    }

    /**
     * 检测文章页面
     */
    private isArticlePage(html: string): boolean {
        const articleIndicators = [
            /<article[^>]*>/i,
            /class=\"article\"/i,
            /blog-post/i,
            /news-article/i,
            /entry-content/i
        ];

        return articleIndicators.some(indicator => indicator.test(html));
    }

    /**
     * 提取meta标签
     */
    public extractMetaTags(): Record<string, string> {
        const metaTags: Record<string, string> = {};
        const metaElements = document.querySelectorAll('meta');

        metaElements.forEach(meta => {
            const name = meta.getAttribute('name') || meta.getAttribute('property');
            const content = meta.getAttribute('content');

            if (name && content) {
                metaTags[name] = content;
            }
        });

        return metaTags;
    }

    /**
     * 生成摘要
     */
    private generateSummary(contentType: ContentType): string {
        const description = document.querySelector('meta[name="description"]')?.getAttribute('content');

        if (description) return description;

        // 根据内容类型生成不同摘要
        switch (contentType) {
            case ContentType.ARTICLE:
                return this.extractFirstParagraph();
            case ContentType.CODE:
                return '代码页面，包含多个代码片段';
            case ContentType.MULTIMEDIA:
                return '多媒体内容页面';
            case ContentType.DATA:
                return '数据表格页面';
            default:
                return document.title;
        }
    }

    /**
     * 提取标题
     */
    private extractHeadings(): Heading[] {
        const headings: Heading[] = [];
        const headingElements = document.querySelectorAll('h1, h2, h3, h4, h5, h6');

        headingElements.forEach(heading => {
            const level = parseInt(heading.tagName.charAt(1));
            headings.push({
                level,
                text: heading.textContent?.trim() || '',
                id: heading.id || undefined
            });
        });

        return headings;
    }

    /**
     * 提取段落
     */
    private extractParagraphs(): Paragraph[] {
        const paragraphs: Paragraph[] = [];
        const paragraphElements = document.querySelectorAll('p');

        paragraphElements.forEach(p => {
            const text = p.textContent?.trim();
            if (text && text.length > 10) {
                paragraphs.push({
                    text,
                    wordCount: this.countWords(text)
                });
            }
        });

        return paragraphs;
    }

    /**
     * 提取图片
     */
    private extractImages(): Image[] {
        const images: Image[] = [];
        const imgElements = document.querySelectorAll('img');

        imgElements.forEach(img => {
            images.push({
                src: img.src,
                alt: img.alt,
                title: img.title || undefined
            });
        });

        return images;
    }

    /**
     * 提取代码块
     */
    private extractCodeBlocks(): CodeBlock[] {
        const codeBlocks: CodeBlock[] = [];
        const codeElements = document.querySelectorAll('pre code, code');

        codeElements.forEach(code => {
            const language = this.detectCodeLanguage(code);
            codeBlocks.push({
                language,
                code: code.textContent?.trim() || ''
            });
        });

        return codeBlocks;
    }

    /**
     * 提取媒体元素
     */
    private extractMediaElements(): MediaElement[] {
        const mediaElements: MediaElement[] = [];

        // 视频元素
        document.querySelectorAll('video').forEach(video => {
            mediaElements.push({
                type: 'video',
                src: video.src,
                duration: video.duration || undefined,
                width: video.videoWidth,
                height: video.videoHeight
            });
        });

        // 音频元素
        document.querySelectorAll('audio').forEach(audio => {
            mediaElements.push({
                type: 'audio',
                src: audio.src,
                duration: audio.duration || undefined
            });
        });

        return mediaElements;
    }

    /**
     * 提取表格
     */
    private extractTables(): Table[] {
        const tables: Table[] = [];
        const tableElements = document.querySelectorAll('table');

        tableElements.forEach(table => {
            const headers: string[] = [];
            const rows: string[][] = [];

            // 提取表头
            table.querySelectorAll('th').forEach(th => {
                headers.push(th.textContent?.trim() || '');
            });

            // 提取行数据
            table.querySelectorAll('tr').forEach(tr => {
                const row: string[] = [];
                tr.querySelectorAll('td').forEach(td => {
                    row.push(td.textContent?.trim() || '');
                });
                if (row.length > 0) rows.push(row);
            });

            if (headers.length > 0 || rows.length > 0) {
                tables.push({
                    headers,
                    rows,
                    caption: table.querySelector('caption')?.textContent?.trim() || undefined
                });
            }
        });

        return tables;
    }

    /**
     * 辅助方法
     */
    private countWords(text: string): number {
        return text.split(/\s+/).filter(word => word.length > 0).length;
    }

    private detectCodeLanguage(code: Element): string | undefined {
        const className = code.className;
        if (className.includes('language-')) {
            return className.split('language-')[1]?.split(' ')[0];
        }
        return undefined;
    }

    private analyzeCodeLanguages(codeBlocks: CodeBlock[]): Record<string, number> {
        const stats: Record<string, number> = {};

        codeBlocks.forEach(block => {
            const lang = block.language || 'unknown';
            stats[lang] = (stats[lang] || 0) + 1;
        });

        return stats;
    }

    private extractFirstParagraph(): string {
        const firstP = document.querySelector('p');
        return firstP?.textContent?.trim().slice(0, 200) + '...' || '';
    }

    private generateContextId(): string {
        return `${location.href}_${Date.now()}`;
    }

    private shouldStoreRawDom(contentType: ContentType): boolean {
        // 只在文章页面和未知页面存储原始DOM
        return contentType === ContentType.ARTICLE || contentType === ContentType.UNKNOWN;
    }

    // need update: 更新实现方案
    private async captureScreenshot(): Promise<string | undefined> {
        // 简化实现 - 实际应该使用chrome.tabs.captureVisibleTab

        return undefined
    }
}