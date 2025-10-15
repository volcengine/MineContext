// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import './Files.css'
import React, { useState, useEffect } from 'react'
import { Button, Typography, Modal, Upload, Grid, Tag, Input } from '@arco-design/web-react'
import { IconClose, IconLoading, IconCheckCircleFill } from '@arco-design/web-react/icon'
import uploadIcon from '@renderer/assets/images/files/upload.png'
import aiIcon from '@renderer/assets/icons/ai.svg'
import { useFiles } from '@renderer/hooks/useFiles'
import { typeIconMap } from '@renderer/utils/file'

const { Title, Text } = Typography
const { Row, Col } = Grid

const Files: React.FC = () => {
  const [analyzeVisible, setAnalyzeVisible] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState<any>(null)
  const [prompt, setPrompt] = useState('')
  const { analyzedDocs, addFile, saveFile } = useFiles()

  useEffect(() => {
    // Simulate analyzing documents
    if (analyzedDocs.some((doc) => doc.status === 'Analyzing')) {
      setTimeout(() => {}, 3000)
    }
  }, [analyzedDocs])

  const uploadFile = async (file) => {
    if (!file.originFile) {
      return
    }

    const fileType = file.name.split('.').pop()
    const newDoc = {
      name: file.name,
      source: `${fileType.toUpperCase()} · ${(file.originFile.size / 1024 / 1024).toFixed(2)}MB`,
      file: file.originFile,
      icon: typeIconMap[fileType]
    }
    setSelectedDoc(newDoc)
    setAnalyzeVisible(true)
  }

  const analyzeDocument = async () => {
    if (!selectedDoc?.file) return

    const reader = new FileReader()
    reader.onload = async (e) => {
      const fileData = e.target?.result
      if (fileData) {
        try {
          const result = await saveFile(selectedDoc.name, new Uint8Array(fileData as ArrayBuffer))
          if (result.success) {
            const docToAnalyze = {
              ...selectedDoc,
              filePath: result.filePath,
              status: 'Analyzing',
              prompt: prompt
            }
            delete docToAnalyze.file
            addFile(docToAnalyze) // Use addFile from the hook
            setAnalyzeVisible(false)
          } else {
            console.error('Error saving file:', result.error)
          }
        } catch (error) {
          console.error('Error saving file:', error)
        }
      }
    }
    reader.readAsArrayBuffer(selectedDoc.file)
  }

  return (
    <div className="files-container">
      <div className="files-header">
        <div className="files-header-left">
          <Title heading={3} style={{ marginTop: 5, fontWeight: 700, fontSize: 24 }}>
            Upload Your Files
          </Title>
          <Text type="secondary" style={{ width: 519, fontSize: 12 }}>
            Upload screenshots and docs—MineContext auto-organizes tasks and generates summaries. Simplify work reviews
            and planning, and save your energy for what truly matters ✨
          </Text>
        </div>
      </div>

      {/* Upload area */}
      <div className="page-container">
        <Upload
          drag
          accept=".ppt,.pptx,.pdf,.docx,.doc,.xls,.xlsx,.csv,.txt,.md,.markdown,.faq"
          showUploadList={false}
          onChange={(_, file) => {
            if (file.status === 'init') {
              uploadFile(file)
            }
          }}
          action="/"
          className="upload-area-container"
          style={{ height: '180px', fontSize: 12 }}>
          <div className="upload-area-dashed">
            <div className="upload-area-content">
              <div className="upload-placeholder">
                <img src={uploadIcon} alt="Screen recording" style={{ width: 214 }} />
                <Text style={{ color: '#0C0D0E', fontSize: 14, fontWeight: 700, marginTop: 10 }}>
                  Drop or select your files here
                </Text>
                <Text style={{ color: '#6C7191', fontSize: 13, marginTop: 6 }}>ppt, pdf, pptx, word</Text>
              </div>
            </div>
          </div>
        </Upload>
      </div>

      <div className="page-container" style={{ marginTop: 50 }}>
        <Title heading={5} style={{ marginTop: 5, fontWeight: 700, fontSize: 24 }}>
          Analyzed Documents
        </Title>
        <Row gutter={[24, 24]} style={{ marginTop: 20 }}>
          {analyzedDocs.map((doc, index) => (
            <Col span={8} key={index}>
              <div className="document-card">
                <div style={{ display: 'flex' }}>
                  <div style={{ marginRight: 8 }}>
                    <img
                      src={doc.icon}
                      alt="document icon"
                      style={{ width: 36, height: 36, maxWidth: 36, maxHeight: 36 }}
                    />
                  </div>
                  <div className="document-info" style={{ overflow: 'hidden' }}>
                    <Text
                      style={{
                        fontSize: 12,
                        color: '#0C0D0E',
                        whiteSpace: 'nowrap',
                        textOverflow: 'ellipsis',
                        overflow: 'hidden'
                      }}>
                      {doc.name}
                    </Text>
                    <Text
                      type="secondary"
                      style={{
                        fontSize: 12,
                        color: '#6C7191',
                        whiteSpace: 'nowrap',
                        textOverflow: 'ellipsis',
                        overflow: 'hidden'
                      }}>
                      {doc.prompt}
                    </Text>
                  </div>
                </div>
                <div className={`status ${doc.status.replace(/\s+/g, '-').toLowerCase()}`}>
                  {doc.status === 'Analyzing' ? (
                    <>
                      <IconLoading style={{ marginRight: 6 }} />
                      <span>Analyzing</span>
                    </>
                  ) : (
                    <>
                      <IconCheckCircleFill style={{ marginRight: 6, color: '#00B42A' }} />
                      <span>Analysis successful</span>
                    </>
                  )}
                </div>
              </div>
            </Col>
          ))}
        </Row>
      </div>

      {/* Analyze document modal */}
      <Modal
        title="Analyze ducument"
        visible={analyzeVisible}
        autoFocus={false}
        focusLock={true}
        onCancel={() => setAnalyzeVisible(false)}
        footer={
          <>
            <Button onClick={() => setAnalyzeVisible(false)} style={{ fontSize: 12 }}>
              Cancel
            </Button>
            <Button type="primary" onClick={() => analyzeDocument()}>
              <img src={aiIcon} alt="AI icon" style={{ marginRight: 5 }} />
              Smart analyze
            </Button>
          </>
        }
        closeIcon={<IconClose style={{ fontSize: 20, color: '#86909C' }} />}>
        {selectedDoc && (
          <div>
            <div className="file-info-card">
              <div style={{ marginRight: 12 }}>
                <img
                  src={selectedDoc.icon}
                  alt="document icon"
                  style={{ width: 36, height: 36, maxWidth: 36, maxHeight: 36 }}
                />
              </div>
              <div className="file-details">
                <Text style={{ fontSize: 12, color: '#0C0D0E' }}>{selectedDoc.name}</Text>
                <Text style={{ fontSize: 12, color: '#86909C' }}>{selectedDoc.source}</Text>
              </div>
            </div>
            <div className="prompt-area">
              <Input.TextArea
                placeholder="Input your desired analyze prompt (Quickly select from below)"
                value={prompt}
                onChange={setPrompt}
                autoSize={{ minRows: 3, maxRows: 5 }}
                style={{ fontSize: 12 }}
              />
              <div className="quick-prompts">
                <Tag onClick={() => setPrompt('Summary')} style={{ cursor: 'pointer', fontSize: 12 }}>
                  Summary
                </Tag>
                <Tag onClick={() => setPrompt('Work Output')} style={{ cursor: 'pointer', fontSize: 12 }}>
                  Work Output
                </Tag>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default Files
