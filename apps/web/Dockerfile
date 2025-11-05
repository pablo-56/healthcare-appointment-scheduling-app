# ---- base ----
FROM node:20-alpine AS base
WORKDIR /web

# Copy lock FIRST for better caching
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./

# Install deps (npm/pnpm/yarn; whichever you use)
RUN if [ -f package-lock.json ]; then npm ci; \
    elif [ -f pnpm-lock.yaml ]; then npm i -g pnpm && pnpm i; \
    elif [ -f yarn.lock ]; then yarn install --frozen-lockfile; \
    else npm i; fi

# Copy source
COPY . .

# ---- dev server image ----
FROM base AS dev
ENV HOST=0.0.0.0
EXPOSE 5173
# Important: bind to 0.0.0.0 and pin port for HMR
CMD ["npm","run","dev","--","--host","0.0.0.0","--port","5173"]

# ---- preview image (static build) ----
FROM base AS preview
RUN npm run build
ENV HOST=0.0.0.0
EXPOSE 5173
CMD ["npm","run","preview","--","--host","0.0.0.0","--port","5173"]
