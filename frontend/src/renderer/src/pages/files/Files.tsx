// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useEffect } from 'react'
import { Button, Typography, Modal, Upload, Grid, Tag, Input } from '@arco-design/web-react'
import { IconClose, IconLoading, IconCheckCircleFill } from '@arco-design/web-react/icon'
import uploadIcon from '@renderer/assets/images/files/upload.png'
import aiIcon from '@renderer/assets/icons/ai.svg'
import { useFiles } from '@renderer/hooks/use-files'
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
    <div className="mt-5 h-screen overflow-y-auto m-5 p-5 border-4 border-transparent rounded-[20px] bg-clip-padding-box relative before:content-[''] before:absolute before:top-0 before:left-0 before:right-0 before:bottom-0 before:z-[-1] before:m-[-4px] before:rounded-[24px] before:bg-gradient-to-br before:from-blue-400 before:via-purple-400 before:to-blue-400 p-5 bg-white h-full scrollbar-hide">
      <div className="bg-white rounded-2xl p-6 m-1 h-[calc(100%-8px)] shadow-[0_8px_32px_rgba(102,126,234,0.1)]">
        <div className="flex justify-between items-start mb-3 px-2 max-md:flex-col max-md:items-stretch">
          <div className="w-3/5 max-md:w-full">
            <Title heading={3} style={{ marginTop: 5, fontWeight: 700, fontSize: 24 }}>
              Upload Your Files
            </Title>
            <Text type="secondary" style={{ width: 519, fontSize: 12 }}>
              Upload screenshots and docs—MineContext auto-organizes tasks and generates summaries. Simplify work
              reviews and planning, and save your energy for what truly matters ✨
            </Text>
          </div>
          <div className="flex items-center ml-6 max-md:ml-0 max-md:mt-4 max-md:justify-end"></div>
        </div>

        {/* Upload area */}
        <div className="mt-5">
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
            className="mb-0 max-w-[1200px] mx-auto flex-1 flex flex-col [&_.arco-upload-list]:hidden"
            style={{ height: '180px', fontSize: 12 }}>
            <div className="border-2 border-dashed border-gray-300 rounded-xl p-[30px] bg-gray-50 transition-all duration-300 flex-1 flex flex-col max-h-[600px] h-[200px] cursor-pointer hover:border-blue-400 hover:bg-blue-50">
              <div className="flex items-center justify-center flex-1">
                <div className="text-center flex flex-col items-center justify-center">
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

        <div className="mt-[50px]">
          <Title heading={5} style={{ marginTop: 5, fontWeight: 700, fontSize: 24 }}>
            Analyzed Documents
          </Title>
          <Row gutter={[24, 24]} style={{ marginTop: 20 }}>
            {analyzedDocs.map((doc, index) => (
              <Col span={8} key={index}>
                <div className="bg-white rounded-lg p-4 items-center border border-gray-200 cursor-pointer hover:shadow-lg transition-shadow">
                  <div style={{ display: 'flex' }}>
                    <div style={{ marginRight: 8 }}>
                      <img
                        src={doc.icon}
                        alt="document icon"
                        style={{ width: 36, height: 36, maxWidth: 36, maxHeight: 36 }}
                      />
                    </div>
                    <div className="flex flex-col flex-grow overflow-hidden" style={{ overflow: 'hidden' }}>
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
                  <div
                    className={`flex items-center text-xs mt-2 px-2 py-1 rounded-md w-fit ${
                      doc.status === 'Analyzing' ? 'text-blue-600 bg-blue-50' : 'text-green-600 bg-green-50'
                    }`}>
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
        closeIcon={<IconClose style={{ fontSize: 20, color: '#86909C' }} />}
        className="[&_.arco-modal-title]:font-semibold">
        {selectedDoc && (
          <div>
            <div className="bg-gray-50 rounded-md p-3 flex items-center border border-gray-200">
              <div style={{ marginRight: 12 }}>
                <img
                  src={selectedDoc.icon}
                  alt="document icon"
                  style={{ width: 36, height: 36, maxWidth: 36, maxHeight: 36 }}
                />
              </div>
              <div className="flex flex-col">
                <Text style={{ fontSize: 12, color: '#0C0D0E' }}>{selectedDoc.name}</Text>
                <Text style={{ fontSize: 12, color: '#86909C' }}>{selectedDoc.source}</Text>
              </div>
            </div>
            <div className="mt-4 relative">
              <Input.TextArea
                placeholder="Input your desired analyze prompt (Quickly select from below)"
                value={prompt}
                onChange={setPrompt}
                autoSize={{ minRows: 3, maxRows: 5 }}
                style={{ fontSize: 12 }}
              />
              <div className="absolute bottom-3 left-3 flex gap-2">
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
