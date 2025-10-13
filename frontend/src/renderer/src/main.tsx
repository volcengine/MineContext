// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import '@arco-design/web-react/es/_util/react-19-adapter'
import { createRoot } from 'react-dom/client'
import { loggerService } from '@logger'
import App from './App'

loggerService.initWindowSource('MainWindow')

createRoot(document.getElementById('root')!).render(<App />)
