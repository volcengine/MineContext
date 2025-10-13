// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

// TODO: 优化上传图片功能，不能存bloburl到数据库中，只能存本地file url地址
import { Crepe } from "@milkdown/crepe";
import { Milkdown, MilkdownProvider, useEditor } from "@milkdown/react";
import "@milkdown/crepe/theme/common/style.css";
import "@milkdown/crepe/theme/frame.css";
import "./index.css";

const CrepeEditor: React.FC<{ defaultValue: string, onChange: (value: string) => void }> = ({ defaultValue, onChange }) => {
  useEditor((root) => {
    const crepe = new Crepe({ root, defaultValue });
    // 监听内容变化
    crepe.on((listener) => {
      listener.markdownUpdated((_, markdown) => {
        onChange(markdown);
      });
    });
    return crepe;
  });

  return <Milkdown />;
};

const MarkdownEditor = (props: { defaultValue: string, onChange: (value: string) => void }) => {
  return (
    <MilkdownProvider>
      <CrepeEditor {...props} />
    </MilkdownProvider>
  )
}

export default MarkdownEditor
