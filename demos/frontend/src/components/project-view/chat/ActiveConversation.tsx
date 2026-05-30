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
  Checkbox,
  ImageList,
  ImageListItem,
  ImageListItemBar,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AddCommentIcon from '@mui/icons-material/AddComment';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import PhotoLibraryIcon from '@mui/icons-material/PhotoLibrary';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import MarkdownRenderer from '../../shared/MarkdownRenderer';
import type { ChatMessage, ProjectAsset, Canvas } from '../../../data/types';
import chatService from '../../../services/chatService';
import PipelineProgress from './PipelineProgress';
import { getPipelineStatus } from '../../../services/api/pipeline';
import { STEP_LABELS } from '../../../data/types/pipeline';

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
  const [chatFiles, setChatFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatMessagesRef = useRef<HTMLDivElement>(null);
  const thinkingRef = useRef<HTMLDivElement>(null);
  const initializedRef = useRef(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pipelineProgress, setPipelineProgress] = useState<{
    message: string;
    step: string;
    progressPct: number | null;
  } | null>(null);
  const [assetPickerOpen, setAssetPickerOpen] = useState(false);
  const [selectedAssetIds, setSelectedAssetIds] = useState<Set<string>>(new Set());
  const [selectedAssets, setSelectedAssets] = useState<ProjectAsset[]>([]);
  const location = useLocation();
  const navigate = useNavigate();

  // Poll pipeline status while thinking to show progress
  useEffect(() => {
    if (!isThinking) return;

    const interval = setInterval(async () => {
      try {
        const statuses = await getPipelineStatus(projectId);
        const current = statuses.find((s) => s.session_id === sessionId);
        if (current) {
          const stepLabel =
            STEP_LABELS[current.pipeline_step] || current.pipeline_step;
          setPipelineProgress({
            message: stepLabel,
            step: current.pipeline_step,
            progressPct: null,
          });
        }
      } catch {
        // Ignore polling errors
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [isThinking, projectId, sessionId]);

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

  const handleRemoveFile = (index: number) => {
    setChatFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleRemoveSelectedAsset = (assetId: string) => {
    setSelectedAssetIds((prev) => {
      const next = new Set(prev);
      next.delete(assetId);
      return next;
    });
    setSelectedAssets((prev) => prev.filter((a) => a.id !== assetId));
  };

  const handleAssetPickerConfirm = () => {
    const chosen = projectAssets.filter((a) => selectedAssetIds.has(a.id));
    setSelectedAssets(chosen);
    setAssetPickerOpen(false);
  };

  const handleAssetToggle = (assetId: string) => {
    setSelectedAssetIds((prev) => {
      const next = new Set(prev);
      if (next.has(assetId)) {
        next.delete(assetId);
      } else {
        next.add(assetId);
      }
      return next;
    });
  };

  const fetchAssetAsFile = async (asset: ProjectAsset): Promise<File> => {
    const response = await fetch(asset.url);
    const blob = await response.blob();
    const extension = asset.fileName?.split('.').pop() || 'png';
    const mimeType = blob.type || `image/${extension}`;
    return new File([blob], asset.fileName || `asset_${asset.id}.${extension}`, {
      type: mimeType,
    });
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
          // Check if this is a pipeline progress event via custom metadata
          const metadata = partialMsg.customMetadata;
          if (metadata?.event_type === 'pipeline_progress') {
            setPipelineProgress({
              message: partialMsg.text || '',
              step: (metadata.step as string) || '',
              progressPct: (metadata.progress_pct as number) ?? null,
            });
            return;
          }

          if (partialMsg.text) {
            setPipelineProgress(null);
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
            setPipelineProgress(null);
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
        setPipelineProgress(null);
        // Reload messages from the session to catch any that the SSE missed
        try {
          const msgs = await chatService.getChatSessionMessages(
            projectId, appName, sessionId, true,
          );
          if (msgs.length > 0) {
            setCurrentChatMessages(msgs);
          }
        } catch {
          // Ignore reload errors
        }
      }
    },
    [appName, projectId, sessionId, onRefreshProject],
  );

  const handleSendMessage = async () => {
    const filesToSend = [...chatFiles];
    const assetsToSend = [...selectedAssets];
    // Clear input state immediately
    setNewMessage('');
    setChatFiles([]);
    setSelectedAssets([]);
    setSelectedAssetIds(new Set());

    // Convert selected assets to File objects
    const assetFiles = await Promise.all(
      assetsToSend.map((asset) => fetchAssetAsFile(asset)),
    );
    const allFiles = [...filesToSend, ...assetFiles];

    await performSendMessage(newMessage, allFiles);
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
        <Button
          startIcon={<ArrowBackIcon />}
          size="small"
          onClick={onBack}
          sx={{ color: 'text.secondary' }}
        >
          Back
        </Button>
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
            <PipelineProgress
              message={pipelineProgress?.message || ''}
              step={pipelineProgress?.step || ''}
              progressPct={pipelineProgress?.progressPct ?? null}
              visible={isThinking && !!pipelineProgress}
            />
            <Collapse in={isThinking && !pipelineProgress}>
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
        {(chatFiles.length > 0 || selectedAssets.length > 0) && (
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
                key={`file-${i}`}
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
            {selectedAssets.map((asset) => (
              <Chip
                key={`asset-${asset.id}`}
                label={asset.fileName || asset.id}
                onDelete={() => handleRemoveSelectedAsset(asset.id)}
                color="primary"
                variant="outlined"
                avatar={
                  asset.type === 'image' ? (
                    <img
                      src={asset.thumbnailUrl || asset.url}
                      alt={asset.fileName || ''}
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
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <input
            type="file"
            multiple
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={handleFileSelect}
            accept="image/*,video/*,audio/*"
          />
          <IconButton
            onClick={() => fileInputRef.current?.click()}
            sx={{ mr: 0.5 }}
            title="Upload files"
          >
            <AttachFileIcon />
          </IconButton>
          <IconButton
            onClick={() => {
              setSelectedAssetIds(new Set(selectedAssets.map((a) => a.id)));
              setAssetPickerOpen(true);
            }}
            sx={{ mr: 1 }}
            title="Choose from assets"
            disabled={projectAssets.length === 0}
          >
            <PhotoLibraryIcon />
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
                      (newMessage.trim() === '' &&
                        chatFiles.length === 0 &&
                        selectedAssets.length === 0)
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

      <Dialog
        open={assetPickerOpen}
        onClose={() => setAssetPickerOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Choose Assets</DialogTitle>
        <DialogContent>
          {projectAssets.filter((a) => a.type === 'image').length === 0 ? (
            <Typography color="text.secondary">No image assets available.</Typography>
          ) : (
            <ImageList cols={3} gap={8} sx={{ mt: 1 }}>
              {projectAssets
                .filter((a) => a.type === 'image')
                .map((asset) => (
                  <ImageListItem
                    key={asset.id}
                    onClick={() => handleAssetToggle(asset.id)}
                    sx={{
                      cursor: 'pointer',
                      border: selectedAssetIds.has(asset.id)
                        ? '3px solid'
                        : '3px solid transparent',
                      borderColor: selectedAssetIds.has(asset.id)
                        ? 'primary.main'
                        : 'transparent',
                      borderRadius: 1,
                      overflow: 'hidden',
                      position: 'relative',
                    }}
                  >
                    <img
                      src={asset.thumbnailUrl || asset.url}
                      alt={asset.fileName || asset.id}
                      loading="lazy"
                      style={{
                        height: 160,
                        width: '100%',
                        objectFit: 'cover',
                      }}
                    />
                    <Checkbox
                      checked={selectedAssetIds.has(asset.id)}
                      sx={{
                        position: 'absolute',
                        top: 4,
                        right: 4,
                        bgcolor: 'rgba(0,0,0,0.5)',
                        borderRadius: 1,
                        '&:hover': { bgcolor: 'rgba(0,0,0,0.7)' },
                      }}
                      size="small"
                    />
                    <ImageListItemBar
                      title={asset.fileName || asset.id}
                      sx={{ '& .MuiImageListItemBar-title': { fontSize: 12 } }}
                    />
                  </ImageListItem>
                ))}
            </ImageList>
          )}
        </DialogContent>
        <DialogActions>
          <Typography variant="body2" sx={{ flexGrow: 1, ml: 2 }}>
            {selectedAssetIds.size} selected
          </Typography>
          <Button onClick={() => setAssetPickerOpen(false)}>Cancel</Button>
          <Button
            onClick={handleAssetPickerConfirm}
            variant="contained"
            disabled={selectedAssetIds.size === 0}
          >
            Attach Selected
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
