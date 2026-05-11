# CES Frontend

React webapp for the Canadian Energy Service internal tool. Dashboard for viewing insights, reports, and managing extracted data.

## Stack

- React 19 + TypeScript
- Vite
- Tailwind CSS 4
- React Router 7
- Radix UI (shadcn primitives)
- Vitest + Testing Library

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Login | `/login` | Authentication |
| Dashboard | `/` | Overview & insights |
| Reports | `/reports` | Generated reports |
| History | `/history` | Activity history |
| Keywords | `/keywords` | Keyword management |
| Query | `/query` | Data querying |
| Monitor | `/monitor` | System monitoring |

## Setup

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Tests

```bash
npm run test
```
