import { createApi } from "@reduxjs/toolkit/query/react";

import { createAuthBaseQuery } from "../auth/createAuthBaseQuery";

const unwrapEnvelope = (payload) => (payload && typeof payload === "object" && "data" in payload ? payload.data : payload);
const normalizeError = (response) => response?.data || response || {};

export const chatApi = createApi({
  reducerPath: "chatApi",
  baseQuery: createAuthBaseQuery("/api/core/chat/"),
  tagTypes: ["ChatConversations", "ChatMessages"],
  endpoints: (builder) => ({
    getConversations: builder.query({
      query: (scope = "") => ({
        url: "conversations/",
        params: scope ? { scope } : {},
      }),
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: ["ChatConversations"],
    }),
    startConversation: builder.mutation({
      query: (body) => ({
        url: "conversations/start/",
        method: "POST",
        body,
      }),
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      invalidatesTags: ["ChatConversations"],
    }),
    getMessages: builder.query({
      query: (conversationId) => `conversations/${conversationId}/messages/`,
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      providesTags: (_result, _error, conversationId) => [{ type: "ChatMessages", id: conversationId }],
    }),
    updateMessage: builder.mutation({
      query: ({ conversationId, messageId, content }) => ({
        url: `conversations/${conversationId}/messages/${messageId}/`,
        method: "PATCH",
        body: { content },
      }),
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      invalidatesTags: (_result, _error, { conversationId }) => [
        "ChatConversations",
        { type: "ChatMessages", id: conversationId },
      ],
    }),
    deleteMessage: builder.mutation({
      query: ({ conversationId, messageId }) => ({
        url: `conversations/${conversationId}/messages/${messageId}/`,
        method: "DELETE",
      }),
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      invalidatesTags: (_result, _error, { conversationId }) => [
        "ChatConversations",
        { type: "ChatMessages", id: conversationId },
      ],
    }),
    markConversationRead: builder.mutation({
      query: (conversationId) => ({
        url: `conversations/${conversationId}/read/`,
        method: "POST",
      }),
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      invalidatesTags: (_result, _error, conversationId) => [
        "ChatConversations",
        { type: "ChatMessages", id: conversationId },
      ],
    }),
    sendVoiceMessage: builder.mutation({
      query: ({ conversationId, formData }) => ({
        url: `conversations/${conversationId}/voice/`,
        method: "POST",
        body: formData,
      }),
      transformResponse: unwrapEnvelope,
      transformErrorResponse: normalizeError,
      invalidatesTags: (_result, _error, { conversationId }) => [
        "ChatConversations",
        { type: "ChatMessages", id: conversationId },
      ],
    }),
  }),
});

export const {
  useGetConversationsQuery,
  useStartConversationMutation,
  useGetMessagesQuery,
  useUpdateMessageMutation,
  useDeleteMessageMutation,
  useMarkConversationReadMutation,
  useSendVoiceMessageMutation,
} = chatApi;
