import {
    Heading,
    Paragraph,
    CodeBlock,
    Image,
    MediaElement,
    Table,
} from "../types";

import { countWords } from "./common";

/**
  * 提取meta标签
  */
export function extractMetaTags(): Record<string, string> {
    const metaTags: Record<string, string> = {};
    const metaElements = document.querySelectorAll("meta");

    metaElements.forEach((meta) => {
        const name = meta.getAttribute("name") || meta.getAttribute("property");
        const content = meta.getAttribute("content");

        if (name && content) {
            metaTags[name] = content;
        }
    });

    return metaTags;
}

/**
   * 提取标题
   */
export function extractHeadings(): Heading[] {
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
export function extractParagraphs(): Paragraph[] {
    const paragraphs: Paragraph[] = [];
    const paragraphElements = document.querySelectorAll('p');

    paragraphElements.forEach(p => {
        const text = p.textContent?.trim();
        if (text && text.length > 10) {
            paragraphs.push({
                text,
                wordCount: countWords(text)
            });
        }
    });

    return paragraphs;
}

export function extractFirstParagraph() {
    const firstP = document.querySelector("p");
    return firstP?.textContent?.trim().slice(0, 200) + "..." || "";
}

/**
 * 提取图片
 */
export function extractImages(): Image[] {
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
export function extractCodeBlocks(): CodeBlock[] {
    const codeBlocks: CodeBlock[] = [];
    const codeElements = document.querySelectorAll('pre code, code');

    codeElements.forEach(code => {
        const language = detectCodeLanguage(code);
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
export function extractMediaElements(): MediaElement[] {
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
export function extractTables(): Table[] {
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



export function detectCodeLanguage(code: Element): string | undefined {
    const className = code.className;
    if (className.includes('language-')) {
        return className.split('language-')[1]?.split(' ')[0];
    }
    return undefined;
}