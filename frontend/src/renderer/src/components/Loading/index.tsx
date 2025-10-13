// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { Typography, Progress } from '@arco-design/web-react'
import { useState, useEffect } from 'react'
const { Title, Text } = Typography;
import logo from '/src/assets/images/logo.png'

export type BackendStatus = 'starting' | 'running' | 'stopped' | 'error';

const LoadingComponent = ({ backendStatus }: { backendStatus: BackendStatus }) => {
  const [progress, setProgress] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);

  // 根据后端状态计算目标进度
  const getProgressByStatus = (status: BackendStatus): number => {
    switch (status) {
      case 'stopped':
        return 10; // 初始状态
      case 'starting':
        return 99; // 启动中最多 99%
      case 'running':
        return 100; // 完成
      case 'error':
        return 0; // 错误状态
      default:
        return 0;
    }
  };

  useEffect(() => {
    if (backendStatus === 'starting' && startTime === null) {
      setStartTime(Date.now());
    }

    const targetProgress = getProgressByStatus(backendStatus);

    const interval = setInterval(() => {
      setProgress(prev => {
        if (backendStatus === 'starting') {
          // 根据时间推进，20s 内最多推到 99%
          const elapsedTime = startTime ? Date.now() - startTime : 0;
          const timeProgress = Math.min(elapsedTime / 20000, 1); // 0 ~ 1
          const dynamicTarget = Math.min(10 + timeProgress * 89, 99); // 从10平滑到99

          return prev < dynamicTarget ? prev + 1 : prev;
        }

        if (backendStatus === 'running') {
          // running 状态直接推到 100
          return prev < 100 ? prev + 1 : 100;
        }

        return targetProgress;
      });
    }, 200);

    return () => clearInterval(interval);
  }, [backendStatus, startTime]);

  return (
    <div className="flex flex-col justify-center items-center h-screen text-black" style={{ background: 'linear-gradient(165.9deg, rgb(209, 192, 211) -3.95%, rgb(217, 218, 233) 3.32%, rgb(242, 242, 242) 23.35%, rgb(253, 252, 248) 71.67%, rgb(249, 250, 236) 76.64%, rgb(255, 236, 221) 83.97%)'}}>
        <img
          src={logo}
          alt="Logo"
          className="w-[100px] h-[100px]"
        />
        <Title className="text-white text-[32px] font-bold" style={{ marginBottom: '40px', marginTop: '24px' }}>
          Welcome to MineContext
        </Title>

        {/* 动态进度条 */}
        <Progress
          percent={progress}
          width={400}
          color={'#000'}
          animation={backendStatus === 'starting' || backendStatus === 'running'}
          showText={true}
          formatText={(percent) => `${Math.round(percent || 0)}%`}
        />

        <Text className="text-gray-600 text-14" style={{ marginTop: '16px' }}>
          It may take a few seconds to awaken your Context-Aware AI partner
        </Text>
    </div>
  );
};

export default LoadingComponent;
