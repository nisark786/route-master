# Vercel Deploy Notes

This frontend can use Vercel as the public URL while the backend stays on EKS.

## Public URL

- Frontend: Vercel project URL
- API proxy target: `https://13-232-122-203.nip.io`

`vercel.json` rewrites these paths to the EKS backend:

- `/api/*`
- `/media/*`

## Required Vercel Environment Variables

Set these in the Vercel project:

- `VITE_API_URL=/api/`
- `VITE_WS_BASE_URL=wss://13-232-122-203.nip.io`
- `VITE_DIRECT_MEDIA_UPLOAD=true`

## Important Note About WebSockets

WebSocket traffic should go directly to the backend host.
Do not rely on Vercel rewrites for `/ws/*`.

The frontend uses `VITE_WS_BASE_URL` for:

- chat socket
- live tracking socket

## Result

Users open the Vercel URL, and normal HTTP API requests stay on that public URL through rewrites.
WebSockets still connect to the backend host directly.
