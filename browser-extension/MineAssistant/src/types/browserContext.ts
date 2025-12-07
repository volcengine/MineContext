export enum ContentType {
    ARTICLE = 'article',
    CODE = 'code',
    MULTIMEDIA = 'multimedia',
    DATA = 'data',
    UNKNOWN = 'unknown'
}

export enum ExtractionMode {
    SMART = 'smart',    // 智能模式 - 提取结构化数据+截屏
    BASIC = 'basic'     // 基础模式 - 只提取基础信息+rawContext
}

// 核心类型定义
export interface BrowserContext {
    id: string;
    url: string;
    title: string;
    timestamp: number;
    metadata: PageMetadata;
    structuredContent: StructuredContent;
    rawDom?: string; // 可选：存储body的innerHTML
    screenshot?: string; // 可选：Base64缩略图
    extractionMode: ExtractionMode; // 提取模式
}

export interface PageMetadata {
    domain: string;
    language: string;
    description: string;
    keywords: string[];
    author: string;
    publishedTime?: string;
    modifiedTime?: string;
    wordCount: number;
    contentType: ContentType;
    // 从meta标签提取的关键信息
    metaTags: Record<string, string>;
}

// 通用结构化内容
export interface StructuredContent {
    title: string;
    summary?: string;
    contentType: ContentType;

    // 按类型分化的内容（互斥）
    articleContent?: ArticleContent;
    codeContent?: CodeContent;
    multimediaContent?: MultimediaContent;
    dataContent?: DataContent;
}

// 文章类型内容
export interface ArticleContent {
    headings: Heading[];
    paragraphs: Paragraph[];
    images: Image[];
}

// 代码类型内容
export interface CodeContent {
    codeBlocks: CodeBlock[];
    languageStats: Record<string, number>;
    fileStructure?: FileStructure[];
}

// 多媒体类型内容
export interface MultimediaContent {
    mediaElements: MediaElement[];
    duration?: number;
    transcript?: string;
}

// 数据表格类型内容
export interface DataContent {
    tables: Table[];
    charts: Chart[];
    dataPoints: DataPoint[];
}

export interface Heading {
    level: number;
    text: string;
    id?: string;
}

export interface Paragraph {
    text: string;
    wordCount: number;
}

export interface Link {
    text: string;
    href: string;
    title?: string;
}

export interface Image {
    src: string;
    alt: string;
    title?: string;
}

export interface Table {
    headers: string[];
    rows: string[][];
    caption?: string;
}

export interface List {
    type: 'ordered' | 'unordered';
    items: string[];
}

export interface CodeBlock {
    language?: string;
    code: string;
}

export interface FileStructure {
    type: string;
    name: string;
    path?: string;
}

export interface MediaElement {
    type: 'video' | 'audio' | 'canvas';
    src?: string;
    duration?: number;
    width?: number;
    height?: number;
}

export interface Chart {
    type: string;
    data: any;
    title?: string;
}

export interface DataPoint {
    type: string;
    value: number;
    unit?: string;
}
