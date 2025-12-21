import { ContentType } from "../types";

/**
   * 检测内容类型 - 更精细的页面特征判断
   */
export function detectContentType(): ContentType {
    const url = location.href;
    const html = document.documentElement.innerHTML;
    const hostname = location.hostname;

    // 1. 基于URL的快速判断（高置信度）
    const quickType = detectByUrl(hostname, url);
    if (quickType !== ContentType.UNKNOWN) {
        return quickType;
    }

    // 2. 基于DOM结构的详细分析
    return detectByDomStructure(html);
}

/**
 * 基于URL的快速内容类型检测
 */
export function detectByUrl(hostname: string, url: string): ContentType {
    // 代码平台
    const codePlatforms = [
        "github.com",
        "gitlab.com",
        "bitbucket.org",
        "stackoverflow.com",
        "codepen.io",
        "jsfiddle.net",
        "codesandbox.io",
        "repl.it",
        "gitee.com",
        "coding.net",
        "csdn.net",
    ];
    if (codePlatforms.some((platform) => hostname.includes(platform))) {
        return ContentType.CODE;
    }

    // 多媒体平台
    const mediaPlatforms = [
        "youtube.com",
        "vimeo.com",
        "soundcloud.com",
        "spotify.com",
        "bilibili.com",
        "youku.com",
        "iqiyi.com",
        "qq.com",
    ];
    if (mediaPlatforms.some((platform) => hostname.includes(platform))) {
        return ContentType.MULTIMEDIA;
    }

    // 数据/图表平台
    const dataPlatforms = [
        "docs.google.com/spreadsheets",
        "excel",
        "tableau",
        "plotly",
    ];
    if (dataPlatforms.some((platform) => url.includes(platform))) {
        return ContentType.DATA;
    }

    // 文章/博客平台
    const articlePlatforms = [
        "medium.com",
        "zhihu.com",
        "juejin.cn",
        "segmentfault.com",
        "cnblogs.com",
        "wordpress.com",
        "blogspot.com",
    ];
    if (articlePlatforms.some((platform) => hostname.includes(platform))) {
        return ContentType.ARTICLE;
    }

    return ContentType.UNKNOWN;
}

/**
 * 基于DOM结构的内容类型检测
 */
export function detectByDomStructure(html: string): ContentType {
    // 代码相关页面检测
    if (isCodePage(location.href, html)) {
        return ContentType.CODE;
    }

    // 多媒体页面检测
    if (isMultimediaPage(html)) {
        return ContentType.MULTIMEDIA;
    }

    // 数据表格页面检测
    if (isDataPage(html)) {
        return ContentType.DATA;
    }

    // 文章页面检测
    if (isArticlePage(html)) {
        return ContentType.ARTICLE;
    }

    return ContentType.UNKNOWN;
}


/**
    * 检测代码页面
    */
export function isCodePage(url: string, html: string): boolean {
    const codeIndicators = [
        /github\.com/i,
        /gitlab\.com/i,
        /bitbucket\.org/i,
        /stackoverflow\.com/i,
        /codepen\.io/i,
        /jsfiddle\.net/i,
        /<pre[^>]*>|<code[^>]*>/i,
        /class=\"highlight\"/i,
        /syntaxhighlighter/i,
    ];

    return codeIndicators.some(
        (indicator) => indicator.test(url) || indicator.test(html)
    );
}

/**
 * 检测多媒体页面
 */
export function isMultimediaPage(html: string): boolean {
    const mediaIndicators = [
        /<video[^>]*>/i,
        /<audio[^>]*>/i,
        /<canvas[^>]*>/i,
        /youtube\.com/i,
        /vimeo\.com/i,
        /soundcloud\.com/i,
    ];

    return mediaIndicators.some((indicator) => indicator.test(html));
}

/**
 * 检测数据页面
 */
export function isDataPage(html: string): boolean {
    const dataIndicators = [
        /<table[^>]*>/i,
        /class=\"table\"/i,
        /data-grid/i,
        /chart/i,
        /graph/i,
        /dataset/i,
    ];

    return dataIndicators.some((indicator) => indicator.test(html));
}

/**
 * 检测文章页面
 */
export function isArticlePage(html: string): boolean {
    const articleIndicators = [
        /<article[^>]*>/i,
        /class=\"article\"/i,
        /blog-post/i,
        /news-article/i,
        /entry-content/i,
    ];

    return articleIndicators.some((indicator) => indicator.test(html));
}


export function shouldStoreRawDom(contentType: ContentType): boolean {
    // 只在文章页面和未知页面存储原始DOM
    return (
        contentType === ContentType.ARTICLE || contentType === ContentType.UNKNOWN
    );
}