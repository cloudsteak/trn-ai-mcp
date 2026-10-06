FROM node:22-bookworm-slim AS nodejs

FROM python:3.13-slim-bookworm

COPY --from=nodejs /usr/local/bin/node /usr/local/bin/node
COPY --from=nodejs /usr/local/lib/node_modules /usr/local/lib/node_modules

WORKDIR /opt/externals
COPY package.json package-lock.json ./
RUN ln -sf ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -sf ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && npm ci --omit=dev \
 && ln -sf /opt/externals/node_modules/.bin/exchange-rate-mcp /usr/local/bin/exchange-rate-mcp

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY externals.cloudrun.json /app/externals.cloudrun.json

RUN pip install --no-cache-dir .

ENV MCP_TRANSPORT=streamable-http
ENV MCP_EXTERNALS=/app/externals.cloudrun.json
ENV HOST=0.0.0.0
ENV PORT=8080

EXPOSE 8080

CMD ["python", "-m", "fejlett_mcp_szerver"]
