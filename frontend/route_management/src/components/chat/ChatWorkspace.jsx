import { useEffect, useMemo, useRef, useState } from "react";
import { Check, CheckCheck, LoaderCircle, MessageSquare, Mic, Pencil, SendHorizontal, Square, Trash2, UserRound, X } from "lucide-react";
import { useSelector } from "react-redux";
import { toast } from "react-toastify";

import {
  useDeleteMessageMutation,
  useGetConversationsQuery,
  useGetMessagesQuery,
  useMarkConversationReadMutation,
  useSendVoiceMessageMutation,
  useStartConversationMutation,
  useUpdateMessageMutation,
} from "../../features/chats/chatApi";
import { extractApiErrorMessage } from "../../utils/adminUi";
import { getRuntimeConfig } from "../../config/runtimeConfig";

function isTokenUsable(token) {
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    if (!payload?.exp) return true;
    return payload.exp * 1000 > Date.now() + 5000;
  } catch {
    return false;
  }
}

function formatMessageTime(value) {
  const parsed = value ? new Date(value) : null;
  if (!parsed || Number.isNaN(parsed.getTime())) {
    return "";
  }
  return parsed.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function formatDayLabel(value) {
  const parsed = value ? new Date(value) : null;
  if (!parsed || Number.isNaN(parsed.getTime())) {
    return "";
  }

  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const startOfMessageDay = new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate());
  const diffDays = Math.round((startOfToday - startOfMessageDay) / 86400000);

  if (diffDays === 0) {
    return "Today";
  }
  if (diffDays === 1) {
    return "Yesterday";
  }
  return parsed.toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" });
}

function getContactLabel(contact) {
  if (!contact) return "Conversation";
  return contact.display_name || contact.email || contact.mobile_number || contact.id;
}

function getCounterpart(conversation, currentUserId) {
  return (conversation?.participants || []).find((participant) => participant.user_id !== currentUserId) || null;
}

function buildConversationMap(conversations, currentUserId) {
  const map = new Map();
  conversations.forEach((conversation) => {
    const counterpartUserId = conversation?.counterpart_user_id || getCounterpart(conversation, currentUserId)?.user_id;
    if (counterpartUserId) {
      map.set(counterpartUserId, conversation);
    }
  });
  return map;
}

function buildDisplayedMessages(baseMessages, liveMessages, updatedMessages, deletedMessageIds) {
  const updatedMap = new Map(updatedMessages.map((item) => [item.id, item]));
  const deletedSet = new Set(deletedMessageIds);
  const mergedBase = baseMessages
    .filter((item) => !deletedSet.has(item.id))
    .map((item) => updatedMap.get(item.id) || item);
  const seen = new Set(mergedBase.map((item) => item.id));
  const mergedLive = liveMessages
    .filter((item) => !seen.has(item.id) && !deletedSet.has(item.id))
    .map((item) => updatedMap.get(item.id) || item);
  return [...mergedBase, ...mergedLive];
}

function buildMessageFeed(messages) {
  const items = [];
  let lastDayLabel = "";

  messages.forEach((message) => {
    const dayLabel = formatDayLabel(message.created_at);
    if (dayLabel && dayLabel !== lastDayLabel) {
      items.push({ type: "day", key: `day-${dayLabel}-${message.id}`, label: dayLabel });
      lastDayLabel = dayLabel;
    }
    items.push({ type: "message", key: message.id, message });
  });

  return items;
}

function getMessageDeliveryStatus(message) {
  const recipientCount = Number(message?.recipient_count || 0);
  const deliveredCount = Number(message?.delivered_count || 0);
  const seenCount = Number(message?.seen_count || 0);

  if (recipientCount > 0 && seenCount >= recipientCount) {
    return "seen";
  }
  if (recipientCount > 0 && deliveredCount >= recipientCount) {
    return "delivered";
  }
  return "sent";
}

function formatLastSeen(value) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  return `Last seen ${parsed.toLocaleString([], { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" })}`;
}

function TypingIndicator() {
  return (
    <span className="inline-flex items-center gap-1">
      <span>Typing</span>
      <span className="inline-flex items-center gap-1">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-400 [animation-delay:0ms]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-400 [animation-delay:180ms]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-slate-400 [animation-delay:360ms]" />
      </span>
    </span>
  );
}

function formatRecordingTime(value) {
  const ms = Math.max(0, Number(value || 0));
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function resolveAudioUrl(url) {
  if (!url) {
    return null;
  }
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  return `${window.location.origin}${url}`;
}

export default function ChatWorkspace({
  title,
  subtitle,
  scope,
  conversationType,
  emptyContactsLabel,
}) {
  const token = useSelector((state) => state.auth.token);
  const currentUserId = useMemo(() => {
    if (!token) return "";
    try {
      const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
      return payload.user_id || "";
    } catch {
      return "";
    }
  }, [token]);

  const {
    data,
    isLoading: isLoadingConversations,
    error: conversationsError,
    refetch: refetchConversations,
  } = useGetConversationsQuery(scope);
  const [startConversation, { isLoading: isStartingConversation, error: startConversationError }] =
    useStartConversationMutation();
  const [markConversationRead] = useMarkConversationReadMutation();
  const [updateMessage] = useUpdateMessageMutation();
  const [deleteMessage] = useDeleteMessageMutation();
  const [sendVoiceMessage] = useSendVoiceMessageMutation();

  const conversations = useMemo(() => data?.conversations || [], [data?.conversations]);
  const contacts = useMemo(() => data?.contacts || [], [data?.contacts]);
  const conversationByContact = useMemo(
    () => buildConversationMap(conversations, currentUserId),
    [conversations, currentUserId]
  );

  const [selectedContactId, setSelectedContactId] = useState("");
  const [selectedConversationId, setSelectedConversationId] = useState("");
  const [draft, setDraft] = useState("");
  const [editingMessageId, setEditingMessageId] = useState("");
  const [editingDraft, setEditingDraft] = useState("");
  const [selectedMessageIds, setSelectedMessageIds] = useState([]);
  const [socketStatus, setSocketStatus] = useState("idle");
  const [liveMessages, setLiveMessages] = useState([]);
  const [updatedMessages, setUpdatedMessages] = useState([]);
  const [deletedMessageIds, setDeletedMessageIds] = useState([]);
  const [contactPresence, setContactPresence] = useState({});
  const [typingByUserId, setTypingByUserId] = useState({});
  const [recordingByUserId, setRecordingByUserId] = useState({});
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDurationMs, setRecordingDurationMs] = useState(0);
  const [pendingVoiceUploads, setPendingVoiceUploads] = useState(0);
  const wsRef = useRef(null);
  const bottomRef = useRef(null);
  const typingStopTimerRef = useRef(null);
  const recordingStopTimerRef = useRef(null);
  const recordingTickerRef = useRef(null);
  const recordingStartedAtRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const recordingChunksRef = useRef([]);
  const shouldDiscardRecordingRef = useRef(false);
  const stoppedDurationMsRef = useRef(0);
  const remoteTypingTimerRef = useRef({});
  const remoteRecordingTimerRef = useRef({});
  const isLocalTypingRef = useRef(false);
  const isLocalRecordingRef = useRef(false);
  const effectiveSelectedContactId = selectedContactId || contacts[0]?.id || "";
  const effectiveSelectedConversationId =
    selectedConversationId || conversationByContact.get(effectiveSelectedContactId)?.id || "";
  const selectedContact = useMemo(
    () => contacts.find((contact) => contact.id === effectiveSelectedContactId) || null,
    [contacts, effectiveSelectedContactId]
  );

  const {
    data: fetchedMessages,
    isLoading: isLoadingMessages,
    error: messagesError,
    refetch: refetchMessages,
  } = useGetMessagesQuery(effectiveSelectedConversationId, { skip: !effectiveSelectedConversationId });
  const displayedMessages = useMemo(() => {
    return buildDisplayedMessages(fetchedMessages || [], liveMessages, updatedMessages, deletedMessageIds);
  }, [fetchedMessages, liveMessages, updatedMessages, deletedMessageIds]);
  const messageFeed = useMemo(() => buildMessageFeed(displayedMessages), [displayedMessages]);
  const selectedMessages = useMemo(
    () => displayedMessages.filter((message) => selectedMessageIds.includes(message.id)),
    [displayedMessages, selectedMessageIds]
  );
  const hasSelectedMessages = selectedMessageIds.length > 0;
  const selectedOwnMessages = useMemo(
    () => selectedMessages.filter((message) => message.sender_id === currentUserId),
    [selectedMessages, currentUserId]
  );
  const canDeleteSelected = hasSelectedMessages && selectedOwnMessages.length === selectedMessages.length;
  const canEditSelected =
    selectedMessageIds.length === 1 &&
    selectedMessages.length === 1 &&
    selectedMessages[0].sender_id === currentUserId &&
    selectedMessages[0].message_type === "TEXT";

  useEffect(() => {
    if (!effectiveSelectedConversationId) return;
    markConversationRead(effectiveSelectedConversationId).catch(() => {});
  }, [effectiveSelectedConversationId, markConversationRead]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [displayedMessages]);

  const feedback = useMemo(
    () =>
      extractApiErrorMessage(conversationsError) ||
      extractApiErrorMessage(startConversationError) ||
      extractApiErrorMessage(messagesError),
    [conversationsError, startConversationError, messagesError]
  );

  useEffect(() => {
    if (feedback) {
      toast.error(feedback, { toastId: `chat-workspace-${feedback}` });
    }
  }, [feedback]);

  useEffect(() => {
    const nextPresence = {};
    contacts.forEach((contact) => {
      nextPresence[contact.id] = {
        is_online: Boolean(contact.is_online),
        last_seen_at: contact.last_seen_at || null,
      };
    });
    setContactPresence(nextPresence);
  }, [contacts]);

  useEffect(() => {
    if (!effectiveSelectedConversationId || !isTokenUsable(token)) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return undefined;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsBase = getRuntimeConfig(
      "VITE_WS_BASE_URL",
      import.meta.env.VITE_WS_BASE_URL || `${protocol}//${window.location.host}`
    );
    const socket = new WebSocket(
      `${wsBase}/ws/chat/conversations/${effectiveSelectedConversationId}/?token=${encodeURIComponent(token)}`
    );
    let refreshTimer = null;
    const queueConversationRefresh = () => {
      if (refreshTimer) return;
      refreshTimer = window.setTimeout(() => {
        refreshTimer = null;
        refetchConversations();
      }, 300);
    };
    wsRef.current = socket;

    socket.onopen = () => setSocketStatus("connected");
    socket.onclose = () => setSocketStatus("closed");
    socket.onerror = () => setSocketStatus("error");
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload?.event !== "message" || payload?.conversation_id !== effectiveSelectedConversationId) {
          if (payload?.conversation_id !== effectiveSelectedConversationId) {
            return;
          }
          if (payload?.event === "message_updated" && payload?.message) {
            setUpdatedMessages((prev) => {
              const remaining = prev.filter((item) => item.id !== payload.message.id);
              return [...remaining, payload.message];
            });
            queueConversationRefresh();
            return;
          }
          if (payload?.event === "message_deleted" && payload?.message_id) {
            setDeletedMessageIds((prev) => (prev.includes(payload.message_id) ? prev : [...prev, payload.message_id]));
            setLiveMessages((prev) => prev.filter((item) => item.id !== payload.message_id));
            setUpdatedMessages((prev) => prev.filter((item) => item.id !== payload.message_id));
            setSelectedMessageIds((prev) => prev.filter((item) => item !== payload.message_id));
            setEditingMessageId((current) => (current === payload.message_id ? "" : current));
            setEditingDraft("");
            queueConversationRefresh();
            return;
          }
          if (payload?.event === "presence" && payload?.user_id) {
            setContactPresence((prev) => ({
              ...prev,
              [payload.user_id]: {
                is_online: Boolean(payload.is_online),
                last_seen_at: payload.last_seen_at || null,
              },
            }));
            return;
          }
          if (payload?.event === "typing" && payload?.user_id) {
            if (payload.user_id === currentUserId) {
              return;
            }
            const userId = payload.user_id;
            const isTyping = Boolean(payload.is_typing);
            setTypingByUserId((prev) => ({ ...prev, [userId]: isTyping }));
            if (remoteTypingTimerRef.current[userId]) {
              window.clearTimeout(remoteTypingTimerRef.current[userId]);
            }
            if (isTyping) {
              remoteTypingTimerRef.current[userId] = window.setTimeout(() => {
                setTypingByUserId((prev) => ({ ...prev, [userId]: false }));
              }, 3000);
            }
            return;
          }
          if (payload?.event === "recording" && payload?.user_id) {
            if (payload.user_id === currentUserId) {
              return;
            }
            const userId = payload.user_id;
            const isRecordingNow = Boolean(payload.is_recording);
            setRecordingByUserId((prev) => ({ ...prev, [userId]: isRecordingNow }));
            if (remoteRecordingTimerRef.current[userId]) {
              window.clearTimeout(remoteRecordingTimerRef.current[userId]);
            }
            if (isRecordingNow) {
              remoteRecordingTimerRef.current[userId] = window.setTimeout(() => {
                setRecordingByUserId((prev) => ({ ...prev, [userId]: false }));
              }, 3000);
            }
            return;
          }
          return;
        }
        const incomingMessage = payload.message;
        setLiveMessages((prev) => {
          if (prev.some((item) => item.id === incomingMessage.id)) {
            return prev;
          }
          return [...prev, incomingMessage];
        });
        queueConversationRefresh();
      } catch {
        // ignore malformed websocket messages
      }
    };

    return () => {
      if (refreshTimer) {
        window.clearTimeout(refreshTimer);
      }
      if (typingStopTimerRef.current) {
        window.clearTimeout(typingStopTimerRef.current);
      }
      if (recordingStopTimerRef.current) {
        window.clearTimeout(recordingStopTimerRef.current);
      }
      if (recordingTickerRef.current) {
        window.clearInterval(recordingTickerRef.current);
        recordingTickerRef.current = null;
      }
      if (isLocalRecordingRef.current && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ event: "recording", is_recording: false }));
        isLocalRecordingRef.current = false;
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        shouldDiscardRecordingRef.current = true;
        mediaRecorderRef.current.stop();
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      }
      socket.close();
      if (wsRef.current === socket) {
        wsRef.current = null;
      }
    };
  }, [effectiveSelectedConversationId, token, refetchConversations, currentUserId]);

  const displaySocketStatus =
    effectiveSelectedConversationId && token && socketStatus === "idle" ? "connecting" : socketStatus;
  const selectedContactPresence = selectedContact ? contactPresence[selectedContact.id] : null;
  const selectedContactIsTyping = selectedContact ? Boolean(typingByUserId[selectedContact.id]) : false;
  const selectedContactIsRecording = selectedContact ? Boolean(recordingByUserId[selectedContact.id]) : false;

  const emitTyping = (isTyping) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || !effectiveSelectedConversationId) {
      return;
    }
    wsRef.current.send(JSON.stringify({ event: "typing", is_typing: isTyping }));
  };

  const emitRecording = (isRecordingNow) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || !effectiveSelectedConversationId) {
      return;
    }
    wsRef.current.send(JSON.stringify({ event: "recording", is_recording: isRecordingNow }));
  };

  const handleDraftChange = (event) => {
    const nextValue = event.target.value;
    setDraft(nextValue);
    const hasText = Boolean(nextValue.trim());
    if (hasText && !isLocalTypingRef.current) {
      emitTyping(true);
      isLocalTypingRef.current = true;
    }
    if (!hasText && isLocalTypingRef.current) {
      emitTyping(false);
      isLocalTypingRef.current = false;
    }
    if (typingStopTimerRef.current) {
      window.clearTimeout(typingStopTimerRef.current);
    }
    if (hasText) {
      typingStopTimerRef.current = window.setTimeout(() => {
        if (isLocalTypingRef.current) {
          emitTyping(false);
          isLocalTypingRef.current = false;
        }
      }, 1400);
    }
  };

  const stopLocalRecordingIndicator = () => {
    if (recordingTickerRef.current) {
      window.clearInterval(recordingTickerRef.current);
      recordingTickerRef.current = null;
    }
    if (recordingStopTimerRef.current) {
      window.clearTimeout(recordingStopTimerRef.current);
      recordingStopTimerRef.current = null;
    }
    if (isLocalRecordingRef.current) {
      emitRecording(false);
      isLocalRecordingRef.current = false;
    }
    setIsRecording(false);
    setRecordingDurationMs(0);
    recordingStartedAtRef.current = null;
  };

  const sendVoiceBlob = (blob, durationMs) => {
    if (!effectiveSelectedConversationId || !blob) {
      return;
    }
    const localMessageId = `local-voice-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const localAudioUrl = URL.createObjectURL(blob);
    const localMessage = {
      id: localMessageId,
      message_type: "VOICE",
      content: "",
      audio_url: localAudioUrl,
      duration_ms: durationMs,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      sender_id: currentUserId,
      sender_email: "",
      sender_role: "",
      recipient_count: 1,
      delivered_count: 0,
      seen_count: 0,
      _local_pending: true,
    };
    setLiveMessages((prev) => [...prev, localMessage]);
    const file = new File([blob], `voice-${Date.now()}.webm`, { type: blob.type || "audio/webm" });
    const formData = new FormData();
    formData.append("audio", file);
    formData.append("duration_ms", String(durationMs));
    setPendingVoiceUploads((prev) => prev + 1);
    sendVoiceMessage({ conversationId: effectiveSelectedConversationId, formData })
      .unwrap()
      .then((sentMessage) => {
        URL.revokeObjectURL(localAudioUrl);
        setLiveMessages((prev) => {
          const withoutLocal = prev.filter((item) => item.id !== localMessageId);
          if (withoutLocal.some((item) => item.id === sentMessage.id)) {
            return withoutLocal;
          }
          return [...withoutLocal, sentMessage];
        });
        setDraft("");
        refetchConversations();
      })
      .catch((error) => {
        URL.revokeObjectURL(localAudioUrl);
        setLiveMessages((prev) => prev.filter((item) => item.id !== localMessageId));
        toast.error(extractApiErrorMessage(error) || "Unable to send voice message.");
      })
      .finally(() => {
        setPendingVoiceUploads((prev) => Math.max(0, prev - 1));
      });
  };

  const stopRecording = ({ discard = false } = {}) => {
    shouldDiscardRecordingRef.current = discard;
    if (recordingStartedAtRef.current) {
      stoppedDurationMsRef.current = Date.now() - recordingStartedAtRef.current;
    }
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    stopLocalRecordingIndicator();
  };

  const startRecording = async () => {
    if (!effectiveSelectedConversationId) {
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      toast.error("Voice recording is not supported in this browser.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaStreamRef.current = stream;
      mediaRecorderRef.current = recorder;
      recordingChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          recordingChunksRef.current.push(event.data);
        }
      };
      recorder.onstop = () => {
        const durationMs = Math.max(1000, stoppedDurationMsRef.current || 0);
        stoppedDurationMsRef.current = 0;
        const voiceBlob = new Blob(recordingChunksRef.current, { type: recorder.mimeType || "audio/webm" });
        recordingChunksRef.current = [];
        const shouldDiscard = shouldDiscardRecordingRef.current;
        shouldDiscardRecordingRef.current = false;
        if (!shouldDiscard && voiceBlob.size > 0) {
          sendVoiceBlob(voiceBlob, durationMs);
        }
      };
      recorder.start(300);
      setIsRecording(true);
      setRecordingDurationMs(0);
      stoppedDurationMsRef.current = 0;
      recordingStartedAtRef.current = Date.now();
      emitRecording(true);
      isLocalRecordingRef.current = true;
      recordingTickerRef.current = window.setInterval(() => {
        if (!recordingStartedAtRef.current) {
          return;
        }
        setRecordingDurationMs(Date.now() - recordingStartedAtRef.current);
      }, 200);
      recordingStopTimerRef.current = window.setTimeout(() => {
        stopRecording();
      }, 2 * 60 * 1000);
    } catch (error) {
      toast.error("Microphone access is required to record voice.");
    }
  };

  const handleContactSelect = async (contact) => {
    if (isRecording) {
      stopRecording({ discard: true });
    }
    setSelectedContactId(contact.id);
    setLiveMessages([]);
    setUpdatedMessages([]);
    setDeletedMessageIds([]);
    setEditingMessageId("");
    setEditingDraft("");
    setSelectedMessageIds([]);
    const existingConversation = conversationByContact.get(contact.id);
    if (existingConversation) {
      setSelectedConversationId(existingConversation.id);
      return;
    }

    try {
      const conversation = await startConversation({
        conversation_type: conversationType,
        target_user_id: contact.id,
      }).unwrap();
      setSelectedConversationId(conversation.id);
      refetchConversations();
    } catch {
      // handled by RTK error state
    }
  };

  const handleEditStart = (message) => {
    setEditingMessageId(message.id);
    setEditingDraft(message.content || "");
    setSelectedMessageIds([]);
  };

  const handleEditCancel = () => {
    setEditingMessageId("");
    setEditingDraft("");
  };

  const handleEditSave = async () => {
    const content = editingDraft.trim();
    if (!content || !effectiveSelectedConversationId || !editingMessageId) {
      return;
    }

    try {
      const updated = await updateMessage({
        conversationId: effectiveSelectedConversationId,
        messageId: editingMessageId,
        content,
      }).unwrap();
      setUpdatedMessages((prev) => {
        const remaining = prev.filter((item) => item.id !== updated.id);
        return [...remaining, updated];
      });
      setEditingMessageId("");
      setEditingDraft("");
      setSelectedMessageIds([]);
      refetchConversations();
    } catch (error) {
      toast.error(extractApiErrorMessage(error) || "Unable to update message.");
    }
  };

  const handleDelete = async (messageId, { skipConfirm = false } = {}) => {
    if (!effectiveSelectedConversationId || !messageId) {
      return;
    }
    if (!skipConfirm && !window.confirm("Delete this message?")) {
      return;
    }

    try {
      await deleteMessage({
        conversationId: effectiveSelectedConversationId,
        messageId,
      }).unwrap();
      setDeletedMessageIds((prev) => (prev.includes(messageId) ? prev : [...prev, messageId]));
      setLiveMessages((prev) => prev.filter((item) => item.id !== messageId));
      setUpdatedMessages((prev) => prev.filter((item) => item.id !== messageId));
      setSelectedMessageIds((prev) => prev.filter((item) => item !== messageId));
      if (editingMessageId === messageId) {
        setEditingMessageId("");
        setEditingDraft("");
      }
      refetchConversations();
    } catch (error) {
      toast.error(extractApiErrorMessage(error) || "Unable to delete message.");
    }
  };

  const handleSelectionStart = (event, message) => {
    if (message.sender_id !== currentUserId || editingMessageId) {
      return;
    }
    event.preventDefault();
    setSelectedMessageIds((prev) => (prev.includes(message.id) ? prev : [...prev, message.id]));
  };

  const handleMessageClick = (message) => {
    if (!hasSelectedMessages || editingMessageId) {
      return;
    }
    if (message.sender_id !== currentUserId) {
      return;
    }
    setSelectedMessageIds((prev) =>
      prev.includes(message.id) ? prev.filter((item) => item !== message.id) : [...prev, message.id]
    );
  };

  const clearSelectedMessages = () => {
    setSelectedMessageIds([]);
  };

  const handleEditSelected = () => {
    if (!canEditSelected) {
      return;
    }
    handleEditStart(selectedMessages[0]);
  };

  const handleDeleteSelected = async () => {
    if (!canDeleteSelected || !effectiveSelectedConversationId) {
      return;
    }
    if (!window.confirm(`Delete ${selectedMessageIds.length} selected message(s)?`)) {
      return;
    }

    for (const messageId of selectedMessageIds) {
      // Sequential delete keeps state predictable and uses existing endpoint contracts.
      // eslint-disable-next-line no-await-in-loop
      await handleDelete(messageId, { skipConfirm: true });
    }
    setSelectedMessageIds([]);
  };

  const handleSend = async (event) => {
    event.preventDefault();
    const content = draft.trim();
    if (!content || !effectiveSelectedConversationId) {
      return;
    }
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      toast.error("Chat socket is not connected yet.");
      return;
    }

    wsRef.current.send(JSON.stringify({ content }));
    setDraft("");
    if (typingStopTimerRef.current) {
      window.clearTimeout(typingStopTimerRef.current);
    }
    if (isLocalTypingRef.current) {
      emitTyping(false);
      isLocalTypingRef.current = false;
    }
  };

  return (
    <div className="flex h-[calc(100vh-64px)] flex-col overflow-hidden p-4 lg:p-6">
      <div className="mb-4">
        <h1 className="text-3xl font-black tracking-tight text-slate-900">{title}</h1>
        {subtitle ? <p className="mt-1 font-medium text-slate-500">{subtitle}</p> : null}
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm xl:grid-cols-[340px_1fr]">
        <aside className="flex min-h-0 flex-col border-b border-slate-200 xl:border-b-0 xl:border-r xl:border-r-slate-200">
          <div className="border-b border-slate-200 bg-slate-50/70 px-5 py-5">
            <h2 className="text-lg font-black text-slate-900">{scope === "drivers" ? "Drivers" : "Administration"}</h2>
            <p className="mt-1 text-sm font-medium text-slate-500">
              {scope === "drivers" ? "Select a driver to chat." : "Select an admin conversation."}
            </p>
          </div>

          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-4">
            {isLoadingConversations ? <p className="text-sm text-slate-500">Loading contacts...</p> : null}
            {!isLoadingConversations && !contacts.length ? (
              <p className="rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
                {emptyContactsLabel}
              </p>
            ) : null}
            {contacts.map((contact) => {
              const conversation = conversationByContact.get(contact.id);
              const isActive = effectiveSelectedContactId === contact.id;
              return (
                <button
                  key={contact.id}
                  type="button"
                  onClick={() => handleContactSelect(contact)}
                  className={`w-full rounded-2xl border px-4 py-4 text-left transition-all ${
                    isActive
                      ? "border-blue-600 bg-blue-50"
                      : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-black text-slate-900">{getContactLabel(contact)}</p>
                      <p className="mt-1 flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-slate-400">
                        <span>{contact.role}</span>
                        <span
                          className={`h-2 w-2 rounded-full ${
                            contactPresence[contact.id]?.is_online ? "bg-emerald-500" : "bg-slate-300"
                          }`}
                        />
                      </p>
                      <p className="mt-2 line-clamp-2 text-xs font-semibold text-slate-500">
                        {conversation?.last_message
                          ? conversation.last_message.message_type === "VOICE"
                            ? "Voice message"
                            : conversation.last_message.content
                          : "No messages yet."}
                      </p>
                    </div>
                    {conversation?.unread_count ? (
                      <span className="rounded-full bg-blue-600 px-2 py-1 text-[10px] font-black text-white">
                        {conversation.unread_count}
                      </span>
                    ) : null}
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        <section className="flex min-h-0 flex-col">
          <div className="border-b border-slate-200 bg-slate-50/70 px-6 py-4">
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                {hasSelectedMessages ? (
                  <>
                    <h2 className="truncate text-lg font-black text-slate-900">{selectedMessageIds.length} selected</h2>
                    <p className="mt-1 text-xs font-semibold uppercase tracking-widest text-slate-400">
                      Right click your messages, then click to select more
                    </p>
                  </>
                ) : (
                  <>
                    <h2 className="truncate text-lg font-black text-slate-900">
                      {selectedContact ? getContactLabel(selectedContact) : "Select a contact"}
                    </h2>
                    {selectedContact ? (
                      <p className="mt-1 text-xs font-semibold uppercase tracking-widest text-slate-400">
                        {selectedContactIsRecording
                          ? "Recording..."
                          : selectedContactIsTyping
                          ? <TypingIndicator />
                          : selectedContactPresence?.is_online
                            ? "Online"
                            : formatLastSeen(selectedContactPresence?.last_seen_at) || selectedContact.role}
                      </p>
                    ) : null}
                  </>
                )}
              </div>
              {hasSelectedMessages ? (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleEditSelected}
                    disabled={!canEditSelected}
                    className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-[11px] font-black uppercase tracking-widest text-slate-700 disabled:opacity-40"
                  >
                    <Pencil size={14} />
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={handleDeleteSelected}
                    disabled={!canDeleteSelected}
                    className="inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-[11px] font-black uppercase tracking-widest text-rose-600 disabled:opacity-40"
                  >
                    <Trash2 size={14} />
                    Delete
                  </button>
                  <button
                    type="button"
                    onClick={clearSelectedMessages}
                    className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-[11px] font-black uppercase tracking-widest text-slate-600"
                  >
                    <X size={14} />
                    Cancel
                  </button>
                </div>
              ) : null}
            </div>
          </div>

          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto bg-slate-50/30 px-6 py-6">
            {!selectedContact ? (
              <div className="flex h-full items-center justify-center">
                <div className="max-w-md rounded-[2rem] border border-dashed border-slate-300 bg-white px-8 py-10 text-center">
                  <MessageSquare className="mx-auto mb-4 text-slate-300" size={40} />
                  <h3 className="text-lg font-black text-slate-900">Select a conversation</h3>
                  <p className="mt-2 text-sm font-medium text-slate-500">
                    Choose a contact from the left to start or continue chatting.
                  </p>
                </div>
              </div>
            ) : isLoadingMessages && effectiveSelectedConversationId ? (
              <p className="text-sm text-slate-500">Loading messages...</p>
            ) : (
              <>
                {messageFeed.map((item) => {
                  if (item.type === "day") {
                    return (
                      <div key={item.key} className="flex justify-center py-2">
                        <span className="rounded-full border border-slate-200 bg-white px-4 py-1 text-[11px] font-black uppercase tracking-widest text-slate-500 shadow-sm">
                          {item.label}
                        </span>
                      </div>
                    );
                  }

                  const message = item.message;
                  const isMine = message.sender_id === currentUserId;
                  const isEditing = editingMessageId === message.id;
                  const isSelected = selectedMessageIds.includes(message.id);
                  const deliveryStatus = getMessageDeliveryStatus(message);
                  return (
                    <div
                      key={message.id}
                      onContextMenu={(event) => handleSelectionStart(event, message)}
                      onClick={() => handleMessageClick(message)}
                      className={`flex ${isMine ? "justify-end" : "justify-start"} ${hasSelectedMessages ? "cursor-pointer" : ""}`}
                    >
                      <div
                        className={`max-w-[70%] rounded-3xl px-4 py-3 shadow-sm ${
                          isMine ? "bg-blue-600 text-white" : "border border-slate-200 bg-white text-slate-900"
                        } ${
                          isSelected ? "ring-2 ring-slate-900 ring-offset-2 ring-offset-slate-50" : ""
                        } ${
                          message.message_type === "VOICE" ? "min-w-[280px] sm:min-w-[340px]" : ""
                        }`}
                      >
                        {!isMine ? (
                          <div className="mb-1 flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-400">
                            <UserRound size={12} />
                            {selectedContact ? getContactLabel(selectedContact) : message.sender_email || message.sender_role || "Participant"}
                          </div>
                        ) : null}
                        {isEditing ? (
                          <div className="space-y-3">
                            <textarea
                              rows={3}
                              value={editingDraft}
                              onChange={(event) => setEditingDraft(event.target.value)}
                              className="w-full resize-none rounded-2xl border border-white/40 bg-white/15 px-3 py-2 text-sm font-semibold text-white outline-none placeholder:text-blue-100"
                            />
                            <div className="flex justify-end gap-2">
                              <button
                                type="button"
                                onClick={handleEditCancel}
                                className="inline-flex items-center gap-1 rounded-full border border-white/30 px-3 py-1 text-[11px] font-black uppercase tracking-widest text-white/90"
                              >
                                <X size={12} />
                                Cancel
                              </button>
                              <button
                                type="button"
                                onClick={handleEditSave}
                                disabled={!editingDraft.trim()}
                                className="inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 text-[11px] font-black uppercase tracking-widest text-blue-700 disabled:opacity-50"
                              >
                                <Check size={12} />
                                Save
                              </button>
                            </div>
                          </div>
                        ) : message.message_type === "VOICE" ? (
                          <div className="space-y-2">
                            <p className={`text-xs font-black uppercase tracking-widest ${isMine ? "text-blue-100" : "text-slate-500"}`}>
                              Voice message
                            </p>
                            {message._local_pending ? (
                              <p className={`inline-flex items-center gap-2 text-xs font-bold ${isMine ? "text-blue-100" : "text-slate-500"}`}>
                                <LoaderCircle size={12} className="animate-spin" />
                                Uploading voice...
                              </p>
                            ) : (
                              <audio controls preload="none" src={resolveAudioUrl(message.audio_url)} className="w-full" />
                            )}
                            {message.duration_ms ? (
                              <p className={`text-[10px] font-black ${isMine ? "text-blue-100" : "text-slate-400"}`}>
                                {formatRecordingTime(message.duration_ms)}
                              </p>
                            ) : null}
                          </div>
                        ) : (
                          <p className="whitespace-pre-wrap text-sm font-semibold">{message.content}</p>
                        )}
                        {isMine ? (
                          <div className="mt-2 flex items-center justify-end gap-1 text-[10px] font-black text-blue-100">
                            <span>{formatMessageTime(message.created_at)}</span>
                            {deliveryStatus === "sent" ? (
                              <Check size={12} />
                            ) : null}
                            {deliveryStatus === "delivered" ? (
                              <CheckCheck size={12} />
                            ) : null}
                            {deliveryStatus === "seen" ? (
                              <CheckCheck size={12} className="text-cyan-200" />
                            ) : null}
                          </div>
                        ) : (
                          <p className="mt-2 text-[10px] font-black text-slate-400">
                            {formatMessageTime(message.created_at)}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
                {!displayedMessages.length ? (
                  <div className="flex h-full items-center justify-center">
                    <div className="rounded-[2rem] border border-dashed border-slate-300 bg-white px-8 py-10 text-center">
                      <MessageSquare className="mx-auto mb-4 text-slate-300" size={36} />
                      <h3 className="text-lg font-black text-slate-900">No messages yet</h3>
                      <p className="mt-2 text-sm font-medium text-slate-500">
                        Send the first message to open this chat thread.
                      </p>
                    </div>
                  </div>
                ) : null}
                <div ref={bottomRef} />
              </>
            )}
          </div>

          <form onSubmit={handleSend} className="border-t border-slate-200 bg-white px-6 py-4">
            <div className="flex items-end gap-3">
              <div className="flex-1 space-y-2">
                <textarea
                  rows={2}
                  value={draft}
                  onChange={handleDraftChange}
                  placeholder={selectedContact ? "Type your message..." : "Select a contact first"}
                  disabled={!selectedContact || isStartingConversation || isRecording}
                  className="min-h-[58px] w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold outline-none transition-all focus:border-blue-500 focus:bg-white"
                />
                {isRecording ? (
                  <div className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-rose-600">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-rose-500" />
                    Recording {formatRecordingTime(recordingDurationMs)}
                  </div>
                ) : null}
              </div>
              {isRecording ? (
                <div className="inline-flex h-[58px] items-center gap-2">
                  <button
                    type="button"
                    onClick={() => stopRecording({ discard: true })}
                    className="inline-flex h-[58px] items-center gap-2 rounded-2xl border border-slate-300 bg-white px-4 text-xs font-black uppercase tracking-[0.2em] text-slate-700 hover:bg-slate-50"
                  >
                    <X size={14} />
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => stopRecording({ discard: false })}
                    className="inline-flex h-[58px] items-center gap-2 rounded-2xl bg-rose-600 px-5 text-xs font-black uppercase tracking-[0.2em] text-white hover:bg-rose-700"
                  >
                    <Square size={14} />
                    Send
                  </button>
                </div>
              ) : draft.trim() ? (
                <button
                  type="submit"
                  disabled={!effectiveSelectedConversationId || displaySocketStatus !== "connected"}
                  className="inline-flex h-[58px] items-center gap-2 rounded-2xl bg-slate-900 px-5 text-xs font-black uppercase tracking-[0.2em] text-white hover:bg-black disabled:opacity-50"
                >
                  <SendHorizontal size={14} />
                  Send
                </button>
              ) : (
                <button
                  type="button"
                  onClick={startRecording}
                  disabled={!selectedContact || isStartingConversation || displaySocketStatus !== "connected"}
                  className="inline-flex h-[58px] items-center gap-2 rounded-2xl bg-slate-900 px-5 text-xs font-black uppercase tracking-[0.2em] text-white hover:bg-black disabled:opacity-50"
                >
                  <Mic size={14} />
                  Record
                </button>
              )}
            </div>
            {pendingVoiceUploads > 0 ? (
              <p className="mt-2 text-[11px] font-bold uppercase tracking-widest text-slate-400">
                <LoaderCircle size={12} className="mr-1 inline-block animate-spin" />
                Uploading {pendingVoiceUploads} voice message{pendingVoiceUploads > 1 ? "s" : ""} in background
              </p>
            ) : null}
          </form>
        </section>
      </div>
    </div>
  );
}
