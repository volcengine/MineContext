export function generateContextId() {
    return `${location.href}_${Date.now()}`;
}

export function countWords(text: string): number {
    return text.split(/\s+/).filter(word => word.length > 0).length;
}