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

import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stepper,
  Step,
  StepLabel,
  CircularProgress,
  Alert,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import {
  getPipelineStatus,
  approvePipeline,
  revisePipeline,
} from '../../../services/api/pipeline';
import {
  PIPELINE_STEPS,
  STEP_LABELS,
  isAwaitingStep,
} from '../../../data/types/pipeline';
import type { PipelineStatusResponse } from '../../../data/types/pipeline';

const SUMMARY_STEPS = [
  'AWAITING_BRIEF',
  'INITIALIZING_MAB',
  'RUNNING_CREATIVE_BRIEF',
  'RUNNING_STORYLINE_TO_STORYBOARD',
  'RUNNING_KEYFRAMES',
  'RUNNING_VIDEO_AND_AUDIO',
  'RUNNING_POST_PRODUCTION',
  'RUNNING_REPORT',
  'PIPELINE_COMPLETE',
];

function getStepIndex(currentStep: string): number {
  const idx = PIPELINE_STEPS.indexOf(currentStep as typeof PIPELINE_STEPS[number]);
  if (idx === -1) return 0;
  let summaryIdx = 0;
  for (const s of SUMMARY_STEPS) {
    const sIdx = PIPELINE_STEPS.indexOf(s as typeof PIPELINE_STEPS[number]);
    if (sIdx <= idx) summaryIdx++;
  }
  return Math.min(summaryIdx, SUMMARY_STEPS.length);
}

function getStepColor(step: string): 'warning' | 'info' | 'success' | 'default' {
  if (isAwaitingStep(step)) return 'warning';
  if (step === 'PIPELINE_COMPLETE') return 'success';
  return 'info';
}

interface PipelineDashboardProps {
  projectId: string;
}

export default function PipelineDashboard({ projectId }: PipelineDashboardProps) {
  const [pipelines, setPipelines] = useState<PipelineStatusResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revisionDialog, setRevisionDialog] = useState<{
    sessionId: string;
    gateName: string;
  } | null>(null);
  const [revisionFeedback, setRevisionFeedback] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getPipelineStatus(projectId);
      setPipelines(data);
      setError(null);
    } catch (err) {
      setError('Failed to load pipeline status.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleApprove = async (sessionId: string) => {
    setActionLoading(sessionId);
    // Fire and forget -- the backend runs the agent asynchronously
    approvePipeline(projectId, sessionId)
      .catch((err) => {
        setError('Failed to approve.');
        console.error(err);
      })
      .finally(() => fetchStatus());
    // Immediate UI feedback
    setTimeout(() => {
      setActionLoading(null);
      fetchStatus();
    }, 1000);
  };

  const handleRevisionSubmit = async () => {
    if (!revisionDialog) return;
    const { sessionId, gateName } = revisionDialog;
    const feedback = revisionFeedback;
    // Close dialog immediately
    setRevisionDialog(null);
    setRevisionFeedback('');
    setActionLoading(sessionId);
    // Fire and forget
    revisePipeline(projectId, sessionId, gateName, feedback)
      .catch((err) => {
        setError('Failed to request revision.');
        console.error(err);
      })
      .finally(() => fetchStatus());
    // Immediate UI feedback
    setTimeout(() => {
      setActionLoading(null);
      fetchStatus();
    }, 1000);
  };

  const getGateNameFromStep = (step: string): string => {
    const map: Record<string, string> = {
      AWAITING_CREATIVE_APPROVAL: 'creative_direction',
      AWAITING_BRIEF_APPROVAL: 'creative_brief',
      AWAITING_KEYFRAME_APPROVAL: 'keyframes',
      AWAITING_VIDEO_APPROVAL: 'video',
    };
    return map[step] || '';
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (pipelines.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="body1" color="text.secondary">
          No active pipelines. Start a conversation with the Ads Co-Director agent to
          begin a new campaign pipeline.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
      {error && (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {pipelines.map((pipeline) => (
        <Card key={pipeline.session_id} variant="outlined">
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
              <Box>
                <Typography variant="subtitle1" fontWeight="bold">
                  Session: {pipeline.session_id.slice(0, 8)}...
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Iteration {Math.max(0, pipeline.mab_iteration + 1)} of{' '}
                  {pipeline.num_target_iterations}
                </Typography>
              </Box>
              <Chip
                label={STEP_LABELS[pipeline.pipeline_step] || pipeline.pipeline_step}
                color={getStepColor(pipeline.pipeline_step)}
                icon={
                  pipeline.pipeline_step === 'PIPELINE_COMPLETE' ? (
                    <CheckCircleIcon />
                  ) : isAwaitingStep(pipeline.pipeline_step) ? (
                    <HourglassEmptyIcon />
                  ) : (
                    <PlayArrowIcon />
                  )
                }
              />
            </Box>

            <Stepper
              activeStep={getStepIndex(pipeline.pipeline_step)}
              alternativeLabel
              sx={{ mb: 2 }}
            >
              {SUMMARY_STEPS.map((step) => (
                <Step key={step}>
                  <StepLabel>
                    <Typography variant="caption">
                      {STEP_LABELS[step] || step}
                    </Typography>
                  </StepLabel>
                </Step>
              ))}
            </Stepper>

            {pipeline.pending_approval && pipeline.pending_approval.summary && (
              <Box sx={{ mb: 2, p: 2, bgcolor: 'action.hover', borderRadius: 1 }}>
                <Typography variant="body2" fontWeight="bold" gutterBottom>
                  Pending Review: {pipeline.pending_approval.gate as string}
                </Typography>
                <Typography
                  variant="body2"
                  sx={{ whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto' }}
                >
                  {pipeline.pending_approval.summary as string}
                </Typography>
              </Box>
            )}

            {isAwaitingStep(pipeline.pipeline_step) && (
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="contained"
                  color="success"
                  size="small"
                  onClick={() => handleApprove(pipeline.session_id)}
                  disabled={actionLoading === pipeline.session_id}
                >
                  {actionLoading === pipeline.session_id ? (
                    <CircularProgress size={20} />
                  ) : (
                    'Approve'
                  )}
                </Button>
                <Button
                  variant="outlined"
                  color="warning"
                  size="small"
                  onClick={() =>
                    setRevisionDialog({
                      sessionId: pipeline.session_id,
                      gateName: getGateNameFromStep(pipeline.pipeline_step),
                    })
                  }
                  disabled={actionLoading === pipeline.session_id}
                >
                  Request Revision
                </Button>
              </Box>
            )}

            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Last updated: {new Date(pipeline.last_update_time * 1000).toLocaleString()}
            </Typography>
          </CardContent>
        </Card>
      ))}

      <Dialog
        open={!!revisionDialog}
        onClose={() => setRevisionDialog(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Request Revision</DialogTitle>
        <DialogContent>
          <Typography variant="body2" gutterBottom>
            Provide feedback for the{' '}
            <strong>{revisionDialog?.gateName}</strong> gate:
          </Typography>
          <TextField
            autoFocus
            multiline
            rows={4}
            fullWidth
            value={revisionFeedback}
            onChange={(e) => setRevisionFeedback(e.target.value)}
            placeholder="Describe what changes you'd like..."
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRevisionDialog(null)}>Cancel</Button>
          <Button
            onClick={handleRevisionSubmit}
            variant="contained"
            disabled={!revisionFeedback.trim()}
          >
            Submit Revision
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
