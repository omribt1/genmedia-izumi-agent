/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { Box, LinearProgress, Typography, Fade } from '@mui/material';
import AutorenewIcon from '@mui/icons-material/Autorenew';

interface PipelineProgressProps {
  message: string;
  step: string;
  progressPct: number | null;
  visible: boolean;
}

export default function PipelineProgress({
  message,
  step,
  progressPct,
  visible,
}: PipelineProgressProps) {
  return (
    <Fade in={visible}>
      <Box
        sx={{
          display: visible ? 'flex' : 'none',
          alignItems: 'center',
          gap: 1.5,
          px: 2,
          py: 1,
          mx: 2,
          mb: 1,
          borderRadius: 1,
          bgcolor: 'action.hover',
          border: '1px solid',
          borderColor: 'divider',
        }}
      >
        <AutorenewIcon
          fontSize="small"
          color="primary"
          sx={{
            '@keyframes spin': {
              from: { transform: 'rotate(0deg)' },
              to: { transform: 'rotate(360deg)' },
            },
            animation: 'spin 2s linear infinite',
          }}
        />
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="body2" color="text.primary">
            {message}
          </Typography>
          {step && (
            <Typography variant="caption" color="text.secondary">
              Step: {step}
            </Typography>
          )}
          {progressPct !== null && (
            <LinearProgress
              variant="determinate"
              value={progressPct}
              sx={{ mt: 0.5, borderRadius: 1 }}
            />
          )}
        </Box>
      </Box>
    </Fade>
  );
}
