/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  TextField,
  IconButton,
  Paper,
  InputAdornment,
  Button,
  Chip,
  keyframes,
  Collapse,
  CircularProgress,
  Snackbar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Card,
  CardMedia,
  CardActionArea,
  CardContent,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AddCommentIcon from '@mui/icons-material/AddComment';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import MarkdownRenderer from '../../shared/MarkdownRenderer';
import type { ChatMessage, ProjectAsset, Canvas } from '../../../data/types';
import chatService from '../../../services/chatService';
import mediaService from '../../../services/mediaService';


const bounce = keyframes`
  0%, 80%, 100% { 
    transform: scale(0);
  } 
  40% { 
    transform: scale(1);
  } 
`;

interface ActiveConversationProps {
  projectId: string;
  sessionId: string;
  appName: string;
  projectAssets: readonly ProjectAsset[];
  projectCanvases?: readonly Canvas[];
  onBack: () => void;
  onNewChat: () => void;
  onRefreshProject?: () => void;
  autoGreeting?: string;
}

export default function ActiveConversation({
  projectId,
  sessionId,
  appName,
  projectAssets,
  projectCanvases,
  onBack,
  onNewChat,
  onRefreshProject,
  autoGreeting,
}: ActiveConversationProps) {
  const [currentChatMessages, setCurrentChatMessages] = useState<ChatMessage[]>(
    [],
  );
  const [newMessage, setNewMessage] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [currentStep, setCurrentStep] = useState<string>('START');
  const [pendingSignals, setPendingSignals] = useState<string[]>([]);
  const [isApproving, setIsApproving] = useState(false);
  const [isApprovingKeyframes, setIsApprovingKeyframes] = useState(false);
  const [isAssetDialogOpen, setIsAssetDialogOpen] = useState(false);
  const [isFetchingAsset, setIsFetchingAsset] = useState(false);
  const [selectedAssetIds, setSelectedAssetIds] = useState<string[]>([]);
  const [chatFiles, setChatFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatMessagesRef = useRef<HTMLDivElement>(null);
  const thinkingRef = useRef<HTMLDivElement>(null);
  const initializedRef = useRef(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

  // Poll campaign status for stateful approvals
  useEffect(() => {
    if (!sessionId || !projectId || appName !== 'ads_codirector') return;

    const pollStatus = async () => {
      try {
        const status = await mediaService.getCampaignStatus(projectId, sessionId);
        setCurrentStep(status.current_step);
        setPendingSignals(status.pending_signals);
      } catch (err) {
        console.error('Failed to poll campaign status:', err);
      }
    };

    // Poll immediately
    pollStatus();

    const intervalId = setInterval(pollStatus, 5000); // Poll every 5 seconds
    return () => clearInterval(intervalId);
  }, [projectId, sessionId, appName]);

  const handleApproveStoryboard = async () => {
    setIsApproving(true);
    try {
      await mediaService.approveStoryboard(projectId, sessionId);
      // Optimistically update state
      setPendingSignals([]);
      setCurrentStep('APPROVED');
      // Trigger a refresh of the project canvases/assets to show new progress
      onRefreshProject?.();
    } catch (err: any) {
      console.error('Failed to approve storyboard:', err);
      setError(err.message || 'Failed to approve storyboard');
    } finally {
      setIsApproving(false);
    }
  };

  const handleApproveKeyframes = async () => {
    setIsApprovingKeyframes(true);
    try {
      await mediaService.approveKeyframes(projectId, sessionId);
      // Optimistically update state
      setPendingSignals([]);
      setCurrentStep('KEYFRAME_PROMPTS_APPROVED');
      onRefreshProject?.();
    } catch (err: any) {
      console.error('Failed to approve keyframe prompts:', err);
      setError(err.message || 'Failed to approve keyframe prompts');
    } finally {
      setIsApprovingKeyframes(false);
    }
  };


  // Scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }
  }, [currentChatMessages]);

  // Scroll to thinking indicator when it appears
  useEffect(() => {
    if (isThinking) {
      // Scroll immediately to show it starting to appear
      setTimeout(() => {
        if (thinkingRef.current) {
          thinkingRef.current.scrollIntoView({
            behavior: 'smooth',
            block: 'nearest',
          });
        }
      }, 50);

      // Scroll again after the collapse animation (300ms) finishes to ensure full visibility
      setTimeout(() => {
        if (thinkingRef.current) {
          thinkingRef.current.scrollIntoView({
            behavior: 'smooth',
            block: 'nearest',
          });
        }
      }, 350);
    }
  }, [isThinking]);

  useEffect(() => {
    if (sessionId && appName) {
      // Force refresh only if it's a new session or explicitly requested by a parent component.
      // Otherwise, chatService will return cached messages.
      setIsLoading(true);
      chatService
        .getChatSessionMessages(projectId, appName, sessionId)
        .then((messages) => setCurrentChatMessages(messages))
        .catch((err) => console.error('Failed to load messages', err))
        .finally(() => setIsLoading(false));
    }
  }, [projectId, appName, sessionId]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setChatFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
    }
  };

  const handleToggleAssetSelection = (assetId: string) => {
    setSelectedAssetIds((prev) =>
      prev.includes(assetId)
        ? prev.filter((id) => id !== assetId)
        : [...prev, assetId]
    );
  };

  const handleAttachSelectedAssets = async () => {
    const idsToAttach = [...selectedAssetIds];
    setSelectedAssetIds([]);
    setIsAssetDialogOpen(false);
    setIsFetchingAsset(true);

    try {
      const attachPromises = idsToAttach.map(async (id) => {
        const asset = projectAssets.find((a) => a.id === id);
        if (!asset) return null;

        const response = await fetch(asset.url);
        if (!response.ok) {
          throw new Error(`Failed to fetch asset: ${response.statusText}`);
        }
        const blob = await response.blob();
        return new File([blob], asset.fileName || 'unnamed_asset', { type: blob.type });
      });

      const files = await Promise.all(attachPromises);
      const validFiles = files.filter((f): f is File => f !== null);
      setChatFiles((prev) => [...prev, ...validFiles]);
    } catch (err: any) {
      console.error('Failed to attach project assets:', err);
      setError(err.message || 'Failed to attach project assets');
    } finally {
      setIsFetchingAsset(false);
    }
  };

  const handleRemoveFile = (index: number) => {
    setChatFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const performSendMessage = useCallback(
    async (text: string, files: File[], userMessageForCache?: ChatMessage) => {
      if (text.trim() === '' && files.length === 0) return;
      if (!appName) return;

      const attachments = files.map((file) => ({
        type: file.type.startsWith('image/')
          ? 'image'
          : ('file' as 'image' | 'file'),
        url: URL.createObjectURL(file),
        name: file.name,
      }));

      const userMessage: ChatMessage = userMessageForCache || {
        id: `msg-${Date.now()}`,
        sender: 'user',
        text: text,
        timestamp: new Date().toISOString(),
        attachments: attachments,
      };

      try {
        setIsThinking(true);
        // Optimistic update for the UI, chatService will also update its internal cache
        setCurrentChatMessages((prev) => [...prev, userMessage]);

        const onPartialUpdate = (partialMsg: ChatMessage, isFinal: boolean) => {
          if (partialMsg.text) {
            setCurrentChatMessages((prev) => {
              const existingIndex = prev.findIndex(
                (m) => m.id === partialMsg.id,
              );
              if (existingIndex >= 0) {
                const newMessages = [...prev];
                newMessages[existingIndex] = partialMsg;
                return newMessages;
              } else {
                return [...prev, partialMsg];
              }
            });
          }
          if (isFinal) {
            onRefreshProject?.();
          }
        };

        await chatService.sendMessage(
          projectId,
          appName,
          sessionId,
          userMessage, // Pass the constructed userMessage
          files,
          onPartialUpdate,
        );
      } catch (error: unknown) {
        console.error('Failed to send message', error);
        const errorMessage =
          error instanceof Error ? error.message : 'Failed to send message';
        setError(errorMessage);
        // On error, revert optimistic update if necessary
        setCurrentChatMessages((prev) =>
          prev.filter((msg) => msg.id !== userMessage.id),
        );
      } finally {
        setIsThinking(false);
      }
    },
    [appName, projectId, sessionId, onRefreshProject],
  );

  const handleSendMessage = async () => {
    const filesToSend = [...chatFiles];
    // Clear input state immediately
    setNewMessage('');
    setChatFiles([]);

    await performSendMessage(newMessage, filesToSend);
  };

  // Effect to auto-send greeting
  useEffect(() => {
    if (
      autoGreeting &&
      appName && // Ensure appName is available
      !initializedRef.current &&
      currentChatMessages.length === 0
    ) {
      initializedRef.current = true;
      // Clear location state to prevent re-greeting on refresh/re-render
      navigate(location.pathname, { replace: true, state: {} });
      const greetingMessage: ChatMessage = {
        id: `msg-${Date.now()}-auto-greeting`,
        sender: 'user',
        text: autoGreeting,
        timestamp: new Date().toISOString(),
        attachments: [],
      };
      performSendMessage(autoGreeting, [], greetingMessage);
    }
  }, [
    autoGreeting,
    appName, // Add appName to dependencies
    currentChatMessages.length,
    performSendMessage,
    navigate,
    location.pathname,
  ]);

  const handleCanvasLinkClick = () => {};

  return (
    <>
      <Box
        sx={{
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 2,
          p: 1.5,
          borderBottom: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Button
            startIcon={<ArrowBackIcon />}
            size="small"
            onClick={onBack}
            sx={{ color: 'text.secondary' }}
          >
            Back
          </Button>
          {currentStep !== 'START' && (
            <Chip
              label={currentStep.replace('_', ' ')}
              size="small"
              color="primary"
              variant="outlined"
              sx={{ fontSize: '0.7rem' }}
            />
          )}
        </Box>
        <Button
          variant="outlined"
          size="small"
          startIcon={<AddCommentIcon />}
          onClick={onNewChat}
        >
          New Chat
        </Button>
      </Box>

      <Box
        sx={{
          flexGrow: 1,
          overflowY: 'auto',
          mb: 2,
          display: 'flex',
          flexDirection: 'column',
          px: 1,
        }}
        ref={chatMessagesRef}
      >
        {isLoading ? (
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              height: '100%',
            }}
          >
            <CircularProgress />
          </Box>
        ) : (
          <>
            {currentChatMessages.map((message, index) => {
              // Skip rendering the first message if it's "Hi" from the user
              if (
                index === 0 &&
                message.sender === 'user' &&
                message.text.toLowerCase() === 'hi'
              ) {
                return null;
              }

              const canvas =
                message.canvasId && projectCanvases
                  ? projectCanvases.find((c) => c.id === message.canvasId)
                  : undefined;

              const asset =
                message.assetId && projectAssets
                  ? projectAssets.find((a) => a.id === message.assetId)
                  : undefined;

              return (
                <Box
                  key={message.id}
                  sx={{
                    mb: 3,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems:
                      message.sender === 'user' ? 'flex-end' : 'flex-start',
                  }}
                >
                  {message.sender === 'user' ? (
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        maxWidth: '85%',
                        borderRadius: 2,
                        bgcolor: 'grey.800',
                        color: 'text.primary',
                      }}
                    >
                      {message.attachments &&
                        message.attachments.length > 0 && (
                          <Box
                            sx={{
                              display: 'flex',
                              flexWrap: 'wrap',
                              gap: 1,
                              mb: message.text ? 1 : 0,
                            }}
                          >
                            {message.attachments.map((att, i) => (
                              <Box
                                key={i}
                                sx={{ borderRadius: 1, overflow: 'hidden' }}
                              >
                                {att.type === 'image' ? (
                                  <img
                                    src={att.url}
                                    alt={att.name}
                                    style={{
                                      height: 100,
                                      width: 'auto',
                                      display: 'block',
                                    }}
                                  />
                                ) : (
                                  <Box
                                    sx={{
                                      display: 'flex',
                                      alignItems: 'center',
                                      bgcolor: 'rgba(255,255,255,0.1)',
                                      p: 1,
                                      borderRadius: 1,
                                    }}
                                  >
                                    <InsertDriveFileIcon
                                      fontSize="small"
                                      sx={{ mr: 1 }}
                                    />
                                    <Typography variant="caption">
                                      {att.name}
                                    </Typography>
                                  </Box>
                                )}
                              </Box>
                            ))}
                          </Box>
                        )}
                      <ReactMarkdown components={MarkdownRenderer}>
                        {message.text}
                      </ReactMarkdown>
                    </Paper>
                  ) : (
                    <Box sx={{ width: '100%', pr: 2 }}>
                      <ReactMarkdown components={MarkdownRenderer}>
                        {message.text}
                      </ReactMarkdown>
                      {canvas && (
                        <Box sx={{ mt: 1.5 }}>
                          <Button
                            variant="outlined"
                            size="small"
                            component={RouterLink}
                            to={`/project/${projectId}/?contentTab=canvas&canvasId=${canvas.id}`}
                            onClick={handleCanvasLinkClick}
                          >
                            {canvas.name}
                          </Button>
                        </Box>
                      )}
                      {asset && (
                        <Box sx={{ mt: 1.5 }}>
                          <Button
                            variant="outlined"
                            size="small"
                            component={RouterLink}
                            to={`/project/${projectId}/?contentTab=assets&assetId=${asset.id}`}
                          >
                            {asset.url.split('/').pop()}
                          </Button>
                        </Box>
                      )}
                    </Box>
                  )}
                </Box>
              );
            })}
            <Collapse in={isThinking}>
              <Box
                ref={thinkingRef}
                sx={{
                  mb: 3,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  width: '100%',
                }}
              >
                <Box
                  data-testid="thinking-indicator"
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    p: 2,
                    bgcolor: 'action.hover',
                    borderRadius: 2,
                    width: 'fit-content',
                  }}
                >
                  {' '}
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      bgcolor: 'text.secondary',
                      borderRadius: '50%',
                      animation: `${bounce} 1.4s infinite ease-in-out both`,
                      animationDelay: '-0.32s',
                    }}
                  />
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      bgcolor: 'text.secondary',
                      borderRadius: '50%',
                      animation: `${bounce} 1.4s infinite ease-in-out both`,
                      animationDelay: '-0.16s',
                    }}
                  />
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      bgcolor: 'text.secondary',
                      borderRadius: '50%',
                      animation: `${bounce} 1.4s infinite ease-in-out both`,
                    }}
                  />
                </Box>
              </Box>
            </Collapse>
          </>
        )}
      </Box>
      <Box sx={{ flexShrink: 0 }}>
        {chatFiles.length > 0 && (
          <Box
            sx={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 1,
              mb: 1,
              p: 1,
              bgcolor: 'background.default',
              borderRadius: 1,
            }}
          >
            {chatFiles.map((file, i) => (
              <Chip
                key={i}
                label={file.name}
                onDelete={() => handleRemoveFile(i)}
                avatar={
                  file.type.startsWith('image/') ? (
                    <img
                      src={URL.createObjectURL(file)}
                      alt={file.name}
                      style={{ width: 24, height: 24, borderRadius: '50%' }}
                    />
                  ) : (
                    <InsertDriveFileIcon />
                  )
                }
                size="small"
              />
            ))}
          </Box>
        )}
        {pendingSignals.includes('keyframes_approved') && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              p: 2,
              mb: 2,
              bgcolor: 'info.dark',
              borderRadius: 1,
              border: 1,
              borderColor: 'info.main',
            }}
          >
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'info.contrastText' }}>
                Keyframe Prompts Ready for Review
              </Typography>
              <Typography variant="caption" sx={{ color: 'info.contrastText', opacity: 0.8 }}>
                Review and edit visual prompts in the Canvases tab before generating images.
              </Typography>
            </Box>
            <Button
              variant="contained"
              color="info"
              size="small"
              onClick={handleApproveKeyframes}
              disabled={isApprovingKeyframes}
              startIcon={isApprovingKeyframes ? <CircularProgress size={16} color="inherit" /> : null}
            >
              {isApprovingKeyframes ? 'Approving...' : 'Approve Prompts & Start Production'}
            </Button>
          </Box>
        )}
        {pendingSignals.includes('storyboard_approved') && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              p: 2,
              mb: 2,
              bgcolor: 'success.dark',
              borderRadius: 1,
              border: 1,
              borderColor: 'success.main',
            }}
          >
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'success.contrastText' }}>
                Storyboard & Script Ready
              </Typography>
              <Typography variant="caption" sx={{ color: 'success.contrastText', opacity: 0.8 }}>
                Review the generated storyboard in the canvases tab.
              </Typography>
            </Box>
            <Button
              variant="contained"
              color="success"
              size="small"
              onClick={handleApproveStoryboard}
              disabled={isApproving}
              startIcon={isApproving ? <CircularProgress size={16} color="inherit" /> : null}
            >
              {isApproving ? 'Approving...' : 'Approve & Generate Video'}
            </Button>
          </Box>
        )}
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <input
            type="file"
            multiple
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
          <IconButton
            onClick={() => fileInputRef.current?.click()}
            sx={{ mr: 1 }}
            title="Attach Local File"
          >
            <AttachFileIcon />
          </IconButton>
          <IconButton
            onClick={() => setIsAssetDialogOpen(true)}
            sx={{ mr: 1 }}
            title="Attach Project Asset"
            disabled={isFetchingAsset || !projectAssets || projectAssets.length === 0}
          >
            {isFetchingAsset ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              <FolderOpenIcon />
            )}
          </IconButton>
          <TextField
            placeholder={`Message ${appName || 'Agent'}...`}
            fullWidth
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !isThinking) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            disabled={isThinking}
            multiline
            minRows={1}
            maxRows={4}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    aria-label="Send"
                    onClick={handleSendMessage}
                    disabled={
                      isThinking ||
                      (newMessage.trim() === '' && chatFiles.length === 0)
                    }
                  >
                    <SendIcon />
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
        </Box>
        <Typography
          variant="caption"
          sx={{
            color: 'text.secondary',
            mt: 1,
            textAlign: 'center',
            display: 'block',
          }}
        >
          Agents can make mistakes, so double check it.
        </Typography>
      </Box>
      <Dialog
        open={isAssetDialogOpen}
        onClose={() => { setSelectedAssetIds([]); setIsAssetDialogOpen(false); }}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Select Project Assets to Attach</DialogTitle>
        <DialogContent dividers>
          {projectAssets && projectAssets.length > 0 ? (
            <Grid container spacing={2}>
              {projectAssets
                .filter((asset) => asset.type === 'image')
                .map((asset) => {
                  const isSelected = selectedAssetIds.includes(asset.id);
                  return (
                    <Grid size={{ xs: 6, sm: 4, md: 3 }} key={asset.id}>
                      <Card
                        variant="outlined"
                        sx={{
                          borderColor: isSelected ? 'primary.main' : 'divider',
                          borderWidth: isSelected ? 2 : 1,
                          bgcolor: isSelected ? 'action.selected' : 'background.paper',
                          position: 'relative',
                        }}
                      >
                        <CardActionArea onClick={() => handleToggleAssetSelection(asset.id)}>
                          <CardMedia
                            component="img"
                            height="120"
                            image={asset.url}
                            alt={asset.fileName || 'Asset'}
                            sx={{ objectFit: 'contain', p: 1, bgcolor: 'grey.900' }}
                          />
                          <CardContent sx={{ p: 1 }}>
                            <Typography
                              variant="caption"
                              noWrap
                              display="block"
                              sx={{ textAlign: 'center', fontWeight: isSelected ? 'bold' : 'normal' }}
                            >
                              {asset.fileName || 'Unnamed'}
                            </Typography>
                          </CardContent>
                        </CardActionArea>
                      </Card>
                    </Grid>
                  );
                })}
            </Grid>
          ) : (
            <Typography variant="body2" color="text.secondary" align="center">
              No image assets found in this project. Upload some in the Assets tab first!
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setSelectedAssetIds([]); setIsAssetDialogOpen(false); }}>Cancel</Button>
          <Button
            variant="contained"
            color="primary"
            onClick={handleAttachSelectedAssets}
            disabled={selectedAssetIds.length === 0}
          >
            Attach Selected ({selectedAssetIds.length})
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!error}
        autoHideDuration={null}
        onClose={() => setError(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setError(null)}
          severity="error"
          sx={{ width: '100%' }}
        >
          {error}
        </Alert>
      </Snackbar>
    </>
  );
}
