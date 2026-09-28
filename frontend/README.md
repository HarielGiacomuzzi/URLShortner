# URL Shortener Frontend

Next.js app for the URL shortener.

## Development

```bash
npm install
```

Create `.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

```bash
npm run dev
```

## Tests

```bash
npm test
```

## Deploy (Vercel)

Set the project's Root Directory to `frontend`, and set the
`NEXT_PUBLIC_API_URL` environment variable to the backend URL.

`NEXT_PUBLIC_API_URL` is inlined into the build at build time: set it
before the first build, and redeploy after changing it. If it's missing,
the app falls back to `http://localhost:8000` and shows "Could not reach
the server".
